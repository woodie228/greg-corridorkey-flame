"""Export SDR-derived scene-linear EXR passes for an explicit Flame handoff.

This converts existing display-referred PNG outputs. It does not recover clipped
HDR values or implement native HDR model inference. Choose input colour space in
Flame deliberately: linear sRGB / Rec.709 primaries, straight alpha.
"""
from __future__ import annotations
import argparse
from fractions import Fraction
import json
import os
from pathlib import Path
os.environ.setdefault('OPENCV_IO_ENABLE_OPENEXR','1')
import cv2
import numpy as np


def linearize(rgb):
    rgb=rgb.astype(np.float32)
    return np.where(rgb<=.04045,rgb/12.92,((rgb+.055)/1.055)**2.4).astype(np.float32)


def write_exr(path,image,*,float32=False):
    if image.dtype!=np.float32 or not np.isfinite(image).all():
        raise ValueError('EXR input must be finite float32')
    kind=cv2.IMWRITE_EXR_TYPE_FLOAT if float32 else cv2.IMWRITE_EXR_TYPE_HALF
    if not cv2.imwrite(str(path),image,[cv2.IMWRITE_EXR_TYPE,kind,cv2.IMWRITE_EXR_COMPRESSION,cv2.IMWRITE_EXR_COMPRESSION_ZIP]):
        raise OSError('EXR write failed: %s'%path)
    actual=cv2.imread(str(path),cv2.IMREAD_UNCHANGED)
    if actual is None or actual.shape!=image.shape or not np.isfinite(actual).all():
        raise ValueError('EXR readback failed: %s'%path)
    if not np.allclose(actual,image,rtol=1e-6 if float32 else 1e-3,atol=1e-7):
        raise ValueError('EXR precision check failed: %s'%path)
    return float(np.max(np.abs(actual-image)))


def export(root,destination,fps,*,float32=False):
    root=Path(root).resolve(strict=True);destination=Path(destination).resolve()
    rate=Fraction(str(fps))
    if rate<=0 or not np.isfinite(float(rate)):raise ValueError('Frame rate must be positive and finite')
    if destination==root or root in destination.parents or destination in root.parents:
        raise ValueError('EXR destination must be separate without nesting')
    receipt=json.loads((root/'experimental-run.json').read_text())
    if receipt['status']!='complete':raise ValueError('Source run is incomplete')
    names=['%06d.png'%i for i in range(len(receipt['source_frames']))]
    if not names:raise ValueError('No frames')
    for key in ('FG','Matte','Comp','Processed'):
        if sorted(p.name for p in (root/key).iterdir())!=names:raise ValueError('Unexpected source frame set')
    if not cv2.haveImageWriter('.exr'):raise RuntimeError('OpenEXR codec unavailable')
    destination.mkdir(parents=True,exist_ok=False)
    for key in ('FG','Matte','Comp','Processed'):(destination/key).mkdir()
    manifest={'status':'running','frames':len(names),'width':receipt['width'],'height':receipt['height'],
              'frame_rate':{'numerator':rate.numerator,'denominator':rate.denominator},
              'colour_space':'scene-linear sRGB / Rec.709 primaries','alpha_association':'straight',
              'dynamic_range':'SDR-derived handoff only; no recovered/clipped HDR data; use the separate linear-EXR runner for floating input/output',
              'pixel_type':'float' if float32 else 'half','source_frame_names':receipt['source_frames'],
              'active_area_xywh':receipt.get('active_area_xywh'),'flame_import_validated':False}
    report=destination/'flame-handoff.json';report.write_text(json.dumps(manifest,indent=2)+'\n');max_error=0.
    try:
        for name in names:
            arrays={key:cv2.imread(str(root/key/name),cv2.IMREAD_UNCHANGED) for key in ('FG','Matte','Comp','Processed')}
            for key,image in arrays.items():
                shape=(receipt['height'],receipt['width'],4 if key=='Processed' else 3)
                if image is None or image.dtype!=np.uint16 or image.shape!=shape:raise ValueError('Unexpected source pass')
            if not np.array_equal(arrays['Processed'][:,:,:3],arrays['FG']) or not np.array_equal(arrays['Processed'][:,:,3],arrays['Matte'][:,:,0]):
                raise ValueError('Source pass contract disagrees')
            fg=linearize(arrays['FG'].astype(np.float32)/65535)
            matte=arrays['Matte'].astype(np.float32)/65535
            output={'FG':fg,'Matte':matte,'Comp':linearize(arrays['Comp'].astype(np.float32)/65535),
                    'Processed':np.dstack((fg,matte[:,:,0]))}
            for key,image in output.items():
                error=write_exr(destination/key/(Path(name).stem+'.exr'),image,float32=float32)
                max_error=max(max_error,error)
        manifest.update(status='complete',max_readback_absolute_error=max_error,
                        import_plan={key:{'sequence_pattern':str(destination/key/('[000000-%06d].exr'%(len(names)-1))),
                                          'interpretation':'coverage data' if key=='Matte' else 'scene-linear sRGB / Rec.709; straight alpha where present'}
                                     for key in ('FG','Matte','Comp','Processed')})
    except Exception as error:
        manifest.update(status='failed',error=str(error));raise
    finally:report.write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('root',type=Path);p.add_argument('destination',type=Path)
    p.add_argument('--fps',required=True,help='Exact source rate, e.g. 24000/1001; never silently assume 24')
    p.add_argument('--float32',action='store_true')
    a=p.parse_args();print(json.dumps(export(a.root,a.destination,a.fps,float32=a.float32),indent=2))


if __name__=='__main__':main()
