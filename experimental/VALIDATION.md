# Experimental validation — 2026-11-03

This is an SDR PNG command-line prototype, not an updated Flame installer.
No installed Flame files, Matchbox files, or EZ-CorridorKey environment changed.
No model assets or generated sample imagery are included in this repository.

## Reproducible runtime

- Community runtime: `peterteravskis/corridorkey-v2-mlx`, commit
  `74065491ebd2eddea494ab34c15a6d84d7415353`.
- Apply `patches/mlx-cpu-reconstruction.patch` to that separate source checkout.
  Run `git apply --check /path/to/mlx-cpu-reconstruction.patch` before applying.
  The patch changes the reconstruction projection to CPU FP32; it retains the
  existing Metal overlap-add. It is a local numerical workaround, not an upstream fix.
- Build/install that patched source in a new Python 3.12 environment. Installing
  before applying the patch leaves an unpatched wheel; rebuild afterward.
- Tested: CPython 3.12.13, MLX/MLX Metal 0.32.4, PyTorch 2.9.1,
  NumPy 1.26.4, OpenCV 4.11.0.86, safetensors 0.8.0.
- Hardware: Apple M5 Ultra, 96 GB unified memory, macOS 27.0.1.
  **M1 Ultra and other Macs have not been tested.** They are intended future
  targets, not certified compatibility. CPU transfers may affect speed.

The patch contains context from Apache-2.0 community source. Its license and
NOTICE are retained under `third_party/`; modified lines are marked in the patch.
Model terms remain separate and unchanged.

## Weight-free checks

- Adapter: 9 tests passed, including preserving the venv Python symlink path.
- Community unpatched source: 20/21 tests passed. Reconstruction parity failed.
- Synthetic diagnostics localized errors to GPU FP32 matrix projection: up to
  0.0014 absolute projection error versus a float64 NumPy oracle. CPU projection
  was within approximately 1.1e-7. Underlying MLX/driver cause is unresolved.
- Generic GPU reference mode did not pass all six diagnostic cases, so simply
  disabling graph optimizations is not a verified fallback.
- Patched source: all 21 community tests passed. All six targeted reconstruction
  cases passed compiled and uncompiled, maximum absolute error 2.38e-7.

These checks validate synthetic operations, not all neural network numerics.

## Authorized isolated inference

Model repository: `cdelta/CorridorKey-v2-MLX-fp32`, revision
`7bb9a4443d5f1b4b696bcc0547d49ae0ac5e5f7e`.
Downloaded only `768x1280-t1/` and accompanying licenses/manifests (about 5.07 GB).
All 17 downloaded files listed in SHA256SUMS matched. SHA256SUMS itself was
retrieved at the pinned revision and is not self-hashed. No t4, FP16, or Q8
profiles were downloaded.

Input: the community repository's synthetic squirrel example, resized with
aspect ratio preserved and padded with its corner screen color to 1280×720.
This deliberate test-fixture preparation does not add resizing to the adapter.
One still, FP32, Hann 1/1, compiled graph, patched CPU projection.

The first attempt caught a venv-executable symlink resolution bug at preflight;
no inference occurred. The adapter was corrected and regression-tested.
The second attempt completed successfully:

| Pass | Decoded shape | Precision | Pixel range |
| --- | --- | --- | --- |
| FG | 720×1280×3 | uint16 | 0–65535 |
| Matte | 720×1280×3 | uint16 | 0–65535 |
| Comp | 720×1280×3 | uint16 | 0–65243 |
| Processed | 720×1280×4 | uint16 | 0–65535 |

All four frames fully decoded with OpenCV, had expected sizes, and the matte
was nonconstant. The checker preview was visually inspected and showed the
subject separated from the screen. This is a smoke check using a synthetic
fixture, not a ground-truth accuracy assessment or model parity result.

## Still unvalidated

- M1 Ultra / M2 / M3 / M4 compatibility and memory requirements.
- Real production footage, motion, long clips, temporal t4 profiles, and blue-screen quality.
- Full-model agreement with official CUDA output, and effects of other M5 GPU operations.
- Throughput and CPU projection overhead.
- Flame import, source timing, Matchbox compositing, color transforms and premultiplication.
- HDR EXR, ACEScg/log inputs, arbitrary production resolutions and source metadata.

Do not replace the existing backend or build a release installer from this result.

Reproduce the synthetic fallback diagnostic with the patched runtime Python:

```bash
/path/to/isolated/.venv/bin/python experimental/verify_reconstruction.py
```

It tests six shapes/bias cases against PyTorch CPU and an independent float64
NumPy oracle and exits nonzero if compiled or uncompiled reconstruction fails.
The generic GPU reference results are reported separately, not used as a passing
substitute for the patched reconstruction path.
