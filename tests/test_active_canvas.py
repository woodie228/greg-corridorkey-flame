import importlib.util
from pathlib import Path
import tempfile
import unittest
try:
    import cv2
    import numpy as np
except ImportError:
    cv2=np=None


@unittest.skipIf(cv2 is None,'Active canvas tests require isolated OpenCV/NumPy')
class ActiveCanvasTests(unittest.TestCase):
    def test_preserves_active_black_prop_and_all_rgb_alpha_without_erosion(self):
        p=Path(__file__).resolve().parents[1]/'experimental/restore_active_canvas.py'
        spec=importlib.util.spec_from_file_location('restore',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            fg=np.array([[[0,0,0],[20000,30000,40000],[65535,20000,10000]],[[1000,2000,3000],[4000,5000,6000],[7000,8000,9000]]],dtype=np.uint16)
            matte=np.full((2,3,3),65535,dtype=np.uint16)
            for folder in ('fg','alpha','checker','cutout'):(root/folder).mkdir()
            cv2.imwrite(str(root/'fg/000000.png'),fg);cv2.imwrite(str(root/'alpha/000000.png'),matte)
            self.assertEqual(m.restore(root,(4,5),(1,1,3,2)),1)
            actual=cv2.imread(str(root/'fg/000000.png'),-1);alpha=cv2.imread(str(root/'alpha/000000.png'),-1)
            np.testing.assert_array_equal(actual[1:3,1:4],fg)
            np.testing.assert_array_equal(alpha[1:3,1:4],matte)
            self.assertEqual(alpha[1,1,0],65535)  # Black foreground is retained.
            outside=np.ones((4,5),bool);outside[1:3,1:4]=False
            self.assertTrue(np.all(alpha[outside]==0))
            rgba=cv2.imread(str(root/'cutout/000000.png'),-1)
            np.testing.assert_array_equal(rgba[:,:,:3],actual)
            np.testing.assert_array_equal(rgba[:,:,3],alpha[:,:,0])
