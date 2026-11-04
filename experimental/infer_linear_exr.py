"""Experimental linear EXR inference using the pinned community MLX model.

Unclipped float input/output, linear sRGB/Rec.709 primaries only. No automatic
ACES/log/primaries conversion. Raw foreground; despill belongs downstream.
This is separate from the SDR PNG adapter and must run in its isolated runtime.
"""
from __future__ import annotations
import argparse
from contextlib import ExitStack
from fractions import Fraction
import importlib.util
import json
import math
import os
from pathlib import Path
import tempfile
from unittest.mock import patch
os.environ.setdefault('OPENCV_IO_ENABLE_OPENEXR','1')
import cv2
import numpy as np

KNEE=.008
DENOM=math.asinh(16/KNEE)


def linear_to_srgb(x):
    return np.where(x<=.0031308,x*12.92,1.055*np.maximum(x,.0031308)**(1/2.4)-.055)


def encode_linear(raw,shape):
    import torch
    from corridorkey_mlx.pipeline import pad_image
    if raw.dtype!=np.float32 or raw.ndim!=3 or raw.shape[2]!=3 or not np.isfinite(raw).all():
        raise ValueError('Expected finite float32 RGB EXR plate (OpenCV BGR order)')
    rgb=pad_image(raw[:,:,::-1].copy(),shape)
    encoded=(np.arcsinh(rgb.astype(np.float64)/KNEE)/DENOM).astype(np.float32)
    proxy=np.clip(linear_to_srgb(np.clip(rgb,0,1)),0,1)
    model=torch.from_numpy(np.ascontiguousarray(encoded.transpose(2,0,1))).bfloat16().float()
    display=torch.from_numpy(np.ascontiguousarray(proxy.transpose(2,0,1))).bfloat16().float()
    return model,display


class LinearSource:
    def __init__(self,path,fps,profile_hw,active_area=None):
        self.path=Path(path).resolve(strict=True)
        self.images=sorted(p for p in self.path.iterdir() if p.is_file() and not p.name.startswith('.')) if self.path.is_dir() else [self.path]
        if not self.images or any(p.suffix.lower()!='.exr' for p in self.images):raise ValueError('Only ordered EXR plates are supported')
        self.count=len(self.images);self.fps=float(Fraction(str(fps)))
        if not np.isfinite(self.fps) or self.fps<=0:raise ValueError('Invalid frame rate')
        first=self._read(self.images[0]);self.raw_hw=tuple(first.shape[:2]);self.height,self.width=self.raw_hw
        self.active_area=active_area
        if active_area is not None:
            x,y,w,h=active_area
            if min(x,y)<0 or min(w,h)<1 or x+w>self.width or y+h>self.height:raise ValueError('Invalid active area')
            self.height,self.width=h,w
        self.padded=tuple(profile_hw)
        if self.padded not in ((768,1280),(1024,1536)) or self.height>self.padded[0] or self.width>self.padded[1]:
            raise ValueError('A matching supported profile must contain the native active image; no resizing')

    @staticmethod
    def _read(path):
        image=cv2.imread(str(path),cv2.IMREAD_UNCHANGED)
        if image is None or image.dtype!=np.float32 or image.ndim!=3 or image.shape[2]!=3 or not np.isfinite(image).all():
            raise ValueError('Expected finite three-channel float EXR: %s'%path)
        return image

    def frames(self):
        for path in self.images:
            image=self._read(path)
            if tuple(image.shape[:2])!=self.raw_hw:raise ValueError('Changing EXR dimensions')
            if self.active_area is not None:
                x,y,w,h=self.active_area;image=image[y:y+h,x:x+w]
            yield image


class LinearRenderer:
    def __init__(self,source):self.source=source
    def __call__(self,meta,outputs,checker,logits):
        if meta.get('despill_strength',0)!=0:raise ValueError('HDR runner exports raw linear foreground; despill downstream')
        values=np.array(logits,dtype=np.float32)
        h,w=meta['output_hw'];left,_,top,_=meta['pad'];values=values[...,top:top+h,left:left+w]
        if not np.isfinite(values).all():raise FloatingPointError('Non-finite predictions')
        alpha=np.clip(values[:,:1],0,1).transpose(0,2,3,1)
        linear=np.sinh(values[:,1:4].astype(np.float64)*DENOM)*KNEE
        if not np.isfinite(linear).all() or np.max(np.abs(linear))>np.finfo(np.float32).max:
            raise FloatingPointError("Decoded linear output exceeds finite float32 range")
        linear=linear.astype(np.float32)
        fg=linear[:,[2,1,0]].transpose(0,2,3,1)  # Float BGR for OpenEXR writer.
        if self.source.active_area is not None:
            x,y,aw,ah=self.source.active_area;ch,cw=self.source.raw_hw
            fg=np.stack([cv2.copyMakeBorder(a,y,ch-y-ah,x,cw-x-aw,cv2.BORDER_REPLICATE) for a in fg])
            restored=np.zeros((len(alpha),ch,cw,1),np.float32);restored[:,y:y+ah,x:x+aw]=alpha;alpha=restored
        h,w=fg.shape[1:3];yy,xx=np.indices((h,w));bg=np.where(((xx//64+yy//64)%2)==0,.75,.5).astype(np.float32)
        bg=np.where(bg<=.04045,bg/12.92,((bg+.055)/1.055)**2.4)[None,:,:,None]
        result={}
        for name in outputs:
            if name=='alpha':image=np.repeat(alpha,3,axis=3)
            elif name=='fg':image=fg
            elif name=='cutout':image=np.concatenate((fg,alpha),axis=3)
            elif name=='checker':image=fg*alpha+bg*(1-alpha)
            else:raise ValueError(name)
            if not np.isfinite(image).all():raise FloatingPointError('Non-finite linear output')
            result[name]=image.astype(np.float32)
        return result


EXR_FOLDERS={"alpha":"Matte","fg":"FG","checker":"Comp","cutout":"Processed"}


class FloatWriter:
    def __init__(self,destination,names,source,png,*,float32=False):
        self.root=Path(destination);self.names=names;self.float32=float32;self.max_error=0.
        p=Path(__file__).with_name('export_flame_exr.py');s=importlib.util.spec_from_file_location('greg_float_writer',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);self.write_exr=m.write_exr
        for name in names:(self.root/EXR_FOLDERS[name]).mkdir(parents=True,exist_ok=True)
    def write(self,index,rendered):
        for name in self.names:
            image=rendered[name][0]
            self.max_error=max(self.max_error,self.write_exr(self.root/EXR_FOLDERS[name]/('%06d.exr'%index),image,float32=self.float32))
    def close(self):pass


def run(input_path,output,model_root,fps,*,temporal=False,active_area=None,hint_sequence=None,first_hint=None,float32=False):
    from corridorkey_mlx import pipeline
    from corridorkey_mlx.mlx_backend import MLXModel
    output=Path(output).resolve();input_path=Path(input_path).resolve(strict=True)
    if output==input_path or output in input_path.parents or input_path in output.parents:raise ValueError('Input/output must be separate')
    source=LinearSource(input_path,fps,(768,1280),active_area)
    output.mkdir(parents=True,exist_ok=False)
    report={'status':'running','experimental':True,'input_encoding':'scene-linear sRGB / Rec.709 primaries',
            'output_encoding':'unclamped scene-linear float; raw foreground; straight alpha',
            'native_hdr_inference_reference_validated':False,'frames':source.count,'canvas_hw':list(source.raw_hw),
            'active_area_xywh':active_area,'fps':str(fps),'synthetic_hdr_fixture_is_not_camera_hdr_validation':True,
            'source_files':[p.name for p in source.images], 'first_hint':str(first_hint) if first_hint else None,
            'hint_sequence':str(hint_sequence) if hint_sequence else None}
    path=output/'hdr-run.json';path.write_text(json.dumps(report,indent=2)+'\n')
    try:
        model=MLXModel(model_root,768,1280,True)
        model._render_predictions=LinearRenderer(source)
        hints=pipeline.Source(hint_sequence,active_area=active_area,profile_hw=source.padded if active_area else None) if hint_sequence else None
        writers=[]
        def writer(*args):
            w=FloatWriter(*args,float32=float32);writers.append(w);return w
        with ExitStack() as stack:
            stack.enter_context(patch.object(pipeline,'encode_frame',encode_linear))
            stack.enter_context(patch.object(pipeline,'Outputs',writer))
            scratch=stack.enter_context(tempfile.TemporaryDirectory(prefix='.hdr-scratch-',dir=output))
            pipeline.run(model,source,output,scratch,window=4 if temporal and source.count>=4 else 1,
                         stride=2 if temporal and source.count>=4 else 1,outputs=('alpha','fg','checker','cutout'),
                         png=True,despill=0.,first_hint=first_hint,hint_source=hints,carry_hint=False)
        settings_path=output/'settings.json';settings=json.loads(settings_path.read_text())
        settings.update(engine='greg-experimental-linear-exr-mlx',input_color='scene-linear sRGB / Rec.709 primaries',output_format='exr',output_colour='unclamped scene-linear raw foreground')
        settings_path.write_text(json.dumps(settings,indent=2)+'\n')
        report.update(status='complete',max_readback_absolute_error=max(w.max_error for w in writers))
    except Exception as error:
        report.update(status='failed',error=str(error));raise
    finally:path.write_text(json.dumps(report,indent=2)+'\n')
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',required=True);p.add_argument('--output-dir',required=True);p.add_argument('--model-root',required=True);p.add_argument('--fps',required=True)
    p.add_argument('--active-area',type=int,nargs=4);p.add_argument('--hint-sequence');p.add_argument('--hint-first-frame');p.add_argument('--temporal',action='store_true');p.add_argument('--float32',action='store_true')
    p.add_argument('--acknowledge-model-terms',action='store_true');a=p.parse_args()
    if not a.acknowledge_model_terms:p.error('Review model and foundation terms before inference')
    print(json.dumps(run(a.input,a.output_dir,a.model_root,a.fps,temporal=a.temporal,active_area=a.active_area,
                         hint_sequence=a.hint_sequence,first_hint=a.hint_first_frame,float32=a.float32),indent=2))


if __name__=='__main__':main()
