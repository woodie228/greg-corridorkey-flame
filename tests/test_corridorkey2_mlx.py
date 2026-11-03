import importlib.util
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib

spec = importlib.util.spec_from_file_location("adapter", Path(__file__).resolve().parents[1] / "experimental/corridorkey2_mlx.py")
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)


def png(path, width=1280, height=720, depth=16, color=2):
    def chunk(name, data):
        return struct.pack(">I", len(data)) + name + data + struct.pack(">I", zlib.crc32(name + data))
    channels = {0: 1, 2: 3, 4: 2, 6: 4}[color]
    row = b'\0' * (1 + width * channels * depth // 8)
    path.write_bytes(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, depth, color, 0, 0, 0))
                     + chunk(b'IDAT', zlib.compress(row * height)) + chunk(b'IEND', b''))


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / 'source'
        self.source.mkdir()
        self.models = self.root / 'models'
        self.models.mkdir()
        png(self.source / '0100.png')

    def job(self):
        return adapter.plan(self.source, sys.executable, self.models, self.root / 'result')

    def test_plan_does_not_create_output_and_uses_single_frame_window(self):
        job = self.job()
        self.assertFalse(Path(job['destination']).exists())
        self.assertEqual(job['profile_hw'], [768, 1280])
        self.assertEqual(job['command'][job['command'].index('--hann-chunk') + 1], '1')

    def test_four_frames_enable_temporal_window(self):
        for i in range(101, 104):
            png(self.source / ('%04d.png' % i))
        command = self.job()['command']
        self.assertEqual(command[command.index('--hann-chunk') + 1], '4')

    def test_reject_gap_exr_and_unsupported_size(self):
        png(self.source / '0102.png')
        with self.assertRaisesRegex(ValueError, 'missing'):
            self.job()
        (self.source / '0102.png').unlink()
        png(self.source / '0100.png', width=1920, height=1080)
        with self.assertRaisesRegex(ValueError, 'Unsupported'):
            self.job()
        (self.source / 'plate.exr').write_text('not a PNG')
        with self.assertRaises(ValueError):
            self.job()

    def test_protect_existing_and_nested_directories(self):
        with self.assertRaises(ValueError):
            adapter.plan(self.source, sys.executable, self.models, self.source / 'results')
        (self.root / 'result').mkdir()
        with self.assertRaises(ValueError):
            self.job()

    def test_model_terms_required_before_writes(self):
        job = self.job()
        with self.assertRaisesRegex(ValueError, 'licenses'):
            adapter.run(job)
        self.assertFalse(Path(job['destination']).exists())

    def fake_runtime(self, command, check):
        self.assertTrue(check)
        if '--check' in command:
            return
        raw = Path(command[command.index('--output-dir') + 1])
        for name in adapter.OUTPUTS:
            (raw / name).mkdir(parents=True)
            png(raw / name / '000000.png', color=6 if name == 'cutout' else 2)

    def test_contract_mapping_and_owned_scratch_cleanup(self):
        job = self.job()
        out = adapter.run(job, acknowledge_model_terms=True, runner=self.fake_runtime)
        self.assertEqual(sorted(p.name for p in out.iterdir()), ['Comp', 'FG', 'Matte', 'Processed', 'experimental-run.json'])
        self.assertTrue((out / 'Processed/000000.png').exists())
        self.assertIn('complete', (out / 'experimental-run.json').read_text())
        self.assertTrue((self.source / '0100.png').exists())

    def test_runtime_failure_has_receipt_and_no_results(self):
        def fail(command, check):
            raise subprocess.CalledProcessError(1, command)
        job = self.job()
        with self.assertRaises(subprocess.CalledProcessError):
            adapter.run(job, acknowledge_model_terms=True, runner=fail)
        out = Path(job['destination'])
        self.assertEqual([p.name for p in out.iterdir()], ['experimental-run.json'])
        self.assertIn('failed', (out / 'experimental-run.json').read_text())

    def test_bad_output_is_rejected_before_mapping(self):
        def wrong(command, check):
            self.fake_runtime(command, check)
            if '--check' not in command:
                raw = Path(command[command.index('--output-dir') + 1])
                png(raw / 'cutout/000000.png', color=2)
        job = self.job()
        with self.assertRaisesRegex(ValueError, 'RGBA'):
            adapter.run(job, acknowledge_model_terms=True, runner=wrong)
        self.assertFalse((Path(job['destination']) / 'FG').exists())


if __name__ == '__main__':
    unittest.main()
