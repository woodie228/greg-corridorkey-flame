import importlib.util
from pathlib import Path
import tempfile
import unittest
try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = np = None


@unittest.skipIf(cv2 is None, 'Hint generation checks need isolated environment OpenCV/NumPy')
class HintGenerationTests(unittest.TestCase):
    def setUp(self):
        p = Path(__file__).resolve().parents[1] / 'experimental/make_green_hints.py'
        spec = importlib.util.spec_from_file_location('hints', p)
        self.hints = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.hints)

    def test_green_background_is_low_and_non_green_is_high(self):
        image = np.array([[[0,255,0],[0,0,255],[255,0,0]]],dtype=np.uint8)
        np.testing.assert_array_equal(self.hints.rough_hint(image),[[0,65535,65535]])

    def test_black_prop_touching_frame_is_preserved(self):
        image = np.full((4,5,3),127,dtype=np.uint8)
        image[:,0]=0
        image[0,2:4]=0  # A dark prop touches the top, but not an entire column.
        result = self.hints.rough_hint(image,remove_black_columns=True)
        self.assertTrue(np.all(result[:,0]==0))
        self.assertTrue(np.all(result[0,2:4]==65535))
        self.assertTrue(np.all(self.hints.rough_hint(image)[:,0]==65535))

    def test_dark_reference_removes_backdrop_but_preserves_dark_foreground(self):
        image=np.array([[[0,0,0],[0,0,0],[180,70,70]]],dtype=np.uint8)
        reference=np.array([[0,65535,0]],dtype=np.uint16)
        result=self.hints.rough_hint(image,reference_matte=reference)
        np.testing.assert_array_equal(result,[[0,65535,65535]])

    def test_reference_preserves_green_wardrobe_and_removes_neutral_backdrop(self):
        image=np.array([[[0,255,0],[0,255,0],[45,45,45],[60,20,20]]],dtype=np.uint8)
        reference=np.array([[0,65535,0,0]],dtype=np.uint16)
        result=self.hints.rough_hint(image,reference_matte=reference)
        np.testing.assert_array_equal(result,[[0,65535,0,65535]])

    def test_dark_reference_dimension_mismatch_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'dimensions'):
            self.hints.rough_hint(np.zeros((2,3,3),dtype=np.uint8),reference_matte=np.zeros((1,3),dtype=np.uint16))

    def test_existing_output_is_never_replaced(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'source';source.mkdir();output=root/'hints';output.mkdir()
            cv2.imwrite(str(source/'0000.png'),np.zeros((2,3,3),dtype=np.uint8))
            marker=output/'keep.txt';marker.write_text('user data')
            with self.assertRaises(FileExistsError):self.hints.generate(source,output)
            self.assertEqual(marker.read_text(),'user data')

    def test_missing_source_frames_fail_before_output_creation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'source';source.mkdir();output=root/'hints'
            for name in ['0000.png','0002.png']:
                cv2.imwrite(str(source/name),np.zeros((2,3,3),dtype=np.uint8))
            with self.assertRaisesRegex(ValueError,'missing'):self.hints.generate(source,output)
            self.assertFalse(output.exists())


if __name__=='__main__':unittest.main()
