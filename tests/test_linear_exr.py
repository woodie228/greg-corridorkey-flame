import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest
try:
    import cv2
    import numpy as np
    import torch
except ImportError:
    cv2=np=torch=None


@unittest.skipIf(torch is None,'Linear EXR tests require isolated runtime dependencies')
class LinearEXRTests(unittest.TestCase):
    def setUp(self):
        p=Path(__file__).resolve().parents[1]/'experimental/infer_linear_exr.py'
        s=importlib.util.spec_from_file_location('hdr',p);self.m=importlib.util.module_from_spec(s);s.loader.exec_module(self.m)

    def test_linear_encoder_preserves_hdr_and_negative_model_values(self):
        raw=np.empty((2,3,3),np.float32);raw[:]=[2.,-.25,4.]
        model,proxy=self.m.encode_linear(raw,(128,128))
        center=model.numpy()[:,63:65,62:65]
        decoded=(np.sinh(center*self.m.DENOM)*self.m.KNEE).transpose(1,2,0)[:,:,::-1]
        np.testing.assert_allclose(decoded,raw,rtol=.02,atol=1e-4)
        self.assertLess(decoded[:,:,1].max(),0)
        self.assertGreater(decoded[:,:,2].min(),1)
        self.assertTrue(torch.all((proxy>=0)&(proxy<=1)).item())

    def test_float_renderer_preserves_hdr_negative_rgb_and_straight_alpha(self):
        logits=np.zeros((1,4,128,128),np.float32);logits[:,0]=1
        for c,value in enumerate([4.,-.25,2.]):logits[:,c+1]=np.arcsinh(value/self.m.KNEE)/self.m.DENOM
        render=self.m.LinearRenderer(SimpleNamespace(active_area=None))
        result=render({'output_hw':(2,3),'pad':(62,0,63,0),'despill_strength':0},('fg','alpha','cutout'),None,logits)
        np.testing.assert_allclose(result['fg'][0,0,0],[2.,-.25,4.],rtol=1e-6)
        np.testing.assert_array_equal(result['cutout'][:,:,:,:3],result['fg'])
        self.assertTrue(np.all(result['cutout'][:,:,:,3]==1))

    def test_float_active_area_does_not_clip_foreground(self):
        logits=np.zeros((1,4,128,128),np.float32);logits[:,0]=1
        logits[:,1]=np.arcsinh(4/self.m.KNEE)/self.m.DENOM
        render=self.m.LinearRenderer(SimpleNamespace(active_area=(1,1,3,2),raw_hw=(4,5)))
        result=render({'output_hw':(2,3),'pad':(62,0,63,0),'despill_strength':0},('cutout',),None,logits)['cutout'][0]
        self.assertEqual(result.shape,(4,5,4))
        self.assertTrue(np.all(result[1:3,1:4,3]==1))
        self.assertTrue(np.all(result[0,:,3]==0))
        self.assertGreater(result[1,1,2],1)
