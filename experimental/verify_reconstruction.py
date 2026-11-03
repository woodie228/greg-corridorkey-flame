import json
import mlx.core as mx
import numpy as np
import torch
import torch.nn.functional as F
from corridorkey_mlx.mlx_kernels import reconstruct
from corridorkey_mlx.mlx_graph import execute

torch.manual_seed(582)
results=[]
for batch,h,w,stride,pad in [(1,1,1,4,2),(2,3,5,4,2),(1,5,3,16,8)]:
    x=torch.randn(batch,7,h,w); weight=torch.randn(7,4,2*stride,2*stride)*.1
    for bias in [None,torch.randn(4)]:
        expected=F.conv_transpose2d(x,weight,bias,stride=stride,padding=pad).numpy()
        a=mx.array(x.permute(0,2,3,1).contiguous().numpy()).transpose(0,3,1,2)
        b=mx.array(weight.numpy()); c=None if bias is None else mx.array(bias.numpy())
        variants={
            'optimized':lambda:reconstruct(a,b,c,stride,pad),
            'optimized_compiled':lambda:mx.compile(lambda a,b:reconstruct(a,b,c,stride,pad))(a,b),
            'reference':lambda:execute('aten.conv_transpose2d.input',[a,b,c,[stride,stride],[pad,pad]],{}),
            'reference_compiled':lambda:mx.compile(lambda a,b:execute('aten.conv_transpose2d.input',[a,b,c,[stride,stride],[pad,pad]],{}))(a,b),
        }
        projection_gpu = np.array(a.transpose(0,2,3,1) @ b.reshape(7,-1))
        projection_cpu = np.array(mx.matmul(a.transpose(0,2,3,1), b.reshape(7,-1), stream=mx.cpu))
        projection_oracle = x.permute(0,2,3,1).numpy().astype('float64') @ weight.numpy().reshape(7,-1).astype('float64')
        row={'projection_gpu_vs_fp64':float(np.abs(projection_gpu-projection_oracle).max()), 'projection_cpu_vs_fp64':float(np.abs(projection_cpu-projection_oracle).max()), 'shape':[batch,h,w,stride,pad],'bias':bias is not None}
        for name,fn in variants.items():
            actual=np.array(fn()); delta=np.abs(actual-expected)
            row[name]={'max_abs':float(delta.max()),'passes':bool(np.allclose(actual,expected,atol=3e-6,rtol=2e-5))}
        # Float64 NumPy independent scatter-add oracle.
        oracle=np.zeros(expected.shape,dtype=np.float64)
        for iy in range(h):
            for ix in range(w):
                for ky in range(2*stride):
                    for kx in range(2*stride):
                        oy=iy*stride+ky-pad; ox=ix*stride+kx-pad
                        if 0<=oy<expected.shape[2] and 0<=ox<expected.shape[3]:
                            oracle[:,:,oy,ox] += x.numpy()[:,:,iy,ix].astype('float64') @ weight.numpy()[:,:,ky,kx].astype('float64')
        if bias is not None:oracle += bias.numpy()[None,:,None,None]
        row['torch_vs_fp64']=float(np.abs(expected-oracle).max())
        results.append(row)
print(json.dumps(results,indent=2))
if not all(row[key]['passes'] for row in results for key in ('optimized', 'optimized_compiled')):
    raise SystemExit('Reconstruction parity failed; do not use this runtime as validated')
