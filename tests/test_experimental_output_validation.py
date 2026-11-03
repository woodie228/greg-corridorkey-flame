import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = np = None


@unittest.skipIf(cv2 is None, 'Full decoding tests need the separate MLX environment OpenCV/NumPy')
class OutputValidationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        path = Path(__file__).resolve().parents[1] / 'experimental/validate_outputs.py'
        spec = importlib.util.spec_from_file_location('validator', path)
        self.validator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.validator)

    def make_run(self, name='run'):
        root = self.root / name
        root.mkdir()
        (root / 'experimental-run.json').write_text(json.dumps({
            'status': 'complete', 'source_frames': ['0100.png'], 'height': 2, 'width': 3}))
        rgb = np.full((2, 3, 3), 12345, dtype=np.uint16)
        alpha = np.array([[0, 32768, 65535], [0, 32768, 65535]], dtype=np.uint16)
        for key in self.validator.PASSES:
            (root / key).mkdir()
            image = np.dstack((rgb, alpha)) if key == 'Processed' else (
                np.repeat(alpha[:, :, None], 3, axis=2) if key == 'Matte' else rgb)
            self.assertTrue(cv2.imwrite(str(root / key / '000000.png'), image))
        return root

    def test_full_decode_and_straight_pass_contract(self):
        report = self.validator.validate(self.make_run())
        self.assertEqual(report['decoded_images'], 4)
        self.assertTrue(report['processed_alpha_equals_matte'])

    def test_alpha_corruption_is_rejected(self):
        root = self.make_run()
        path = root / 'Processed/000000.png'
        image = cv2.imread(str(path), -1)
        image[0, 0, 3] = 100
        cv2.imwrite(str(path), image)
        with self.assertRaisesRegex(ValueError, 'alpha disagrees'):
            self.validator.validate(root)

    def test_wrong_precision_is_rejected(self):
        root = self.make_run()
        cv2.imwrite(str(root / 'FG/000000.png'), np.zeros((2, 3, 3), dtype=np.uint8))
        with self.assertRaisesRegex(ValueError, 'uint16'):
            self.validator.validate(root)

    def test_comparison_refuses_different_source_order(self):
        first, second = self.make_run('first'), self.make_run('second')
        path = second / 'experimental-run.json'
        receipt = json.loads(path.read_text())
        receipt['source_frames'] = ['0101.png']
        path.write_text(json.dumps(receipt))
        with self.assertRaisesRegex(ValueError, 'matching source'):
            self.validator.compare_alpha(first, second)


if __name__ == '__main__':
    unittest.main()
