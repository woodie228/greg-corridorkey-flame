import importlib.util
from pathlib import Path
import tempfile
import unittest
try:
    import cv2
    import numpy as np
except ImportError:
    cv2=np=None


@unittest.skipIf(cv2 is None,'EXR tests require isolated OpenCV/NumPy')
class EXRHandoffTests(unittest.TestCase):
    def setUp(self):
        p=Path(__file__).resolve().parents[1]/'experimental/export_flame_exr.py'
        spec=importlib.util.spec_from_file_location('exr',p);self.m=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.m)

    def test_transfer_function_reference_points(self):
        a=self.m.linearize(np.array([0,.04045,.5,1],dtype=np.float32))
        np.testing.assert_allclose(a,[0,.0031308,.21404114,1],rtol=1e-5,atol=1e-7)

    def test_exr_codec_preserves_hdr_negative_values_and_alpha(self):
        # Container capability only; model inference remains SDR-derived.
        with tempfile.TemporaryDirectory() as tmp:
            a=np.array([[[2.,-.25,.5,.25],[4.,.125,1.,1.]]],dtype=np.float32)
            self.m.write_exr(Path(tmp)/'sentinel.exr',a)
            actual=cv2.imread(str(Path(tmp)/'sentinel.exr'),-1)
            np.testing.assert_array_equal(actual,a)

    def test_handoff_does_not_gamma_convert_alpha_and_records_exact_rate(self):
        import json
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'source';root.mkdir();output=Path(tmp)/'output'
            (root/'experimental-run.json').write_text(json.dumps({'status':'complete','source_frames':['0000.png'],'width':2,'height':2}))
            rgb=np.full((2,2,3),32768,dtype=np.uint16);alpha=np.full((2,2,3),32768,dtype=np.uint16)
            for key in ('FG','Matte','Comp','Processed'):
                (root/key).mkdir()
                a=np.dstack((rgb,alpha[:,:,0])) if key=='Processed' else (alpha if key=='Matte' else rgb)
                cv2.imwrite(str(root/key/'000000.png'),a)
            report=self.m.export(root,output,'24000/1001')
            matte=cv2.imread(str(output/'Matte/000000.exr'),-1)
            foreground=cv2.imread(str(output/'FG/000000.exr'),-1)
            self.assertAlmostEqual(float(matte[0,0,0]),.5,places=3)
            self.assertAlmostEqual(float(foreground[0,0,0]),.214,places=3)
            self.assertEqual(report['frame_rate'],{'numerator':24000,'denominator':1001})
