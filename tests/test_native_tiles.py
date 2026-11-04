import importlib.util
from pathlib import Path
import unittest
try:
    import numpy as np
except ImportError:
    np=None

@unittest.skipIf(np is None,'Tile assembly tests require NumPy in the isolated runtime')
class NativeTileTests(unittest.TestCase):
    def setUp(self):
        global m
        s=importlib.util.spec_from_file_location('native_tiles',Path(__file__).parents[1]/'experimental/native_tiles.py')
        m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
    def test_overlap_preserves_constant_and_black_foreground(self):
        rgb=np.full((4,6,3),.5,np.float32);rgb[:,0]=0
        a=np.ones((4,6),np.float32)
        f,alpha=m.assemble([(1,0,rgb,a),(1,0,rgb,a)],(4,8),(1,0,6,4),2)
        np.testing.assert_allclose(f[:,1:7],rgb,atol=1e-6)
        np.testing.assert_equal(alpha[:,1:7],1)
        np.testing.assert_equal(alpha[:,[0,7]],0)
        np.testing.assert_allclose(f[:,7],rgb[:,-1],atol=1e-6)
    def test_transparent_black_does_not_darken_opaque_foreground(self):
        white=np.ones((4,6,3),np.float32);a=np.ones((4,6),np.float32)
        rgb,alpha=m.assemble([(0,0,white,a),(0,0,white*0,a*0)],(4,6),(0,0,6,4))
        np.testing.assert_allclose(rgb,1,atol=1e-6)
        np.testing.assert_allclose(alpha,.5)
    def test_coverage_gaps_rejected(self):
        with self.assertRaisesRegex(ValueError,'uncovered'):
            m.assemble([], (4,6),(0,0,6,4))
    def test_no_outside_content_or_nonfinite(self):
        rgb=np.ones((4,6,3),np.float32);a=np.ones((4,6),np.float32)
        with self.assertRaises(ValueError):m.assemble([(0,0,rgb,a)],(4,8),(1,0,6,4))
        rgb[0,0]=np.nan
        with self.assertRaises(ValueError):m.assemble([(0,0,rgb,a)],(4,6),(0,0,6,4))
