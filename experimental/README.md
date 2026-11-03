# CorridorKey 2 MLX adapter — experimental, not a release

This is a separate, opt-in prototype for the community
[peterteravskis/corridorkey-v2-mlx](https://github.com/peterteravskis/corridorkey-v2-mlx)
CLI (package version 0.1.0). It is not a new model implementation or an official
Corridor Digital plugin. It does not alter the installed Flame hook, Matchbox,
installer, EZ-CorridorKey checkout, or current 1.x backend. It is not included in
the macOS installer. No model code or weights are bundled.

## Current scope

The adapter accepts a display-referred sRGB RGB/RGBA PNG still or contiguous,
equally zero-padded numeric PNG sequence. It uses FP32, chooses Hann 4/2 for
four or more frames and 1/1 for shorter inputs, and refuses unsupported padded
shapes. Published profile shapes are height × width 768×1280 and 1024×1536.
There is no resizing. 1/1 loses temporal-window context.

The current Flame roundtrip exports OpenEXR. Those exports **cannot be passed
directly to this prototype**. This adapter does not convert EXR, ACEScg, log,
HDR, primaries, transfer functions, or footage metadata. PNG export clips the
HDR workflow to an SDR representation; do not treat it as a production EXR
replacement. A supported PNG plate must be prepared separately with deliberate
color management. Keep original footage untouched.

Outputs are mapped to existing Flame pass names:

| Community output | Folder | Interpretation |
| --- | --- | --- |
| fg | FG | Despilled display-referred foreground |
| alpha | Matte | Coverage matte repeated into RGB |
| checker | Comp | Checkerboard preview |
| cutout | Processed | Straight RGB plus alpha |

Upstream PNG sequences start at zero. A JSON receipt retains the ordered source
filenames; the adapter does not preserve source timecode or set Flame frame rate.
Outputs are not automatically imported. Manually import sequences at the source
frame rate, then connect FG and Matte to Matchbox. Verify premultiplication and
color interpretation visually before relying on results.

## Separate runtime and model prerequisites

Inspect and pin the community source before provisioning an independent
Python 3.12 environment, outside the existing EZ-CorridorKey environment.
The community package pins MLX 0.32.4 and PyTorch 2.9.1; PyTorch is used for CPU
preparation. The port's published hardware validation used M4 Pro / 48 GiB.
Do not infer a minimum memory requirement or support for all Macs from that.

Review the [Corridor Key Licence 2.0](https://github.com/nikopueringer/CorridorKey2.0/blob/master/LICENSE)
and foundation licenses before downloading profiles or running inference.
The source runtime's Apache 2.0 license does not grant extra rights to model
assets. Commercial image/video processing is permitted subject to the additional
terms; redistribution, commercial software incorporation, paid inference, and
organizations above $20M annual gross revenue have additional restrictions.
Do not bundle weights or assume this wrapper resolves licensing eligibility.

After confirming eligibility, obtain only the required authorized FP32 profiles
and their manifests from the community model publisher. No downloads or setup
are performed by this adapter. The user must supply both an existing runtime
Python and a model-root directory. An isolated test environment and a single authorized model profile were used
for the smoke test documented in [VALIDATION.md](VALIDATION.md). They are not distributed here.

## Plan first

```bash
python3 experimental/corridorkey2_mlx.py \
  --input /path/to/srgb-png-sequence \
  --runtime-python /path/to/separate-runtime/.venv/bin/python \
  --model-root /path/to/authorized-fp32-profiles \
  --output-dir /path/to/new-results
```

The default only prints a plan. To run, add `--execute
--acknowledge-model-terms`. This acknowledgement confirms that the caller has
reviewed applicable terms; it does not grant a license. The adapter runs the
community CLI's `--check` before inference, requests 16-bit PNG output, checks
frame names/counts and PNG IHDR dimensions/depth (and RGBA for Processed), then
maps the output folders. Header checks are not full PNG decoding or numerical
image-quality validation. Existing destinations are rejected. Scratch is owned
by this run and removed after ordinary exceptions; the receipt remains on failure.
An interrupted process can leave scratch. Do not delete another run's files.

## Verification and remaining gates

```bash
python3 -m unittest discover -s tests -v
```

Nine adapter tests pass using generated valid PNG fixtures and a simulated
runtime. These test invocation contracts, temporal selection, frame mapping,
shape rejection, overwrite protection, license acknowledgement and failure
cleanup. A separate authorized still-inference smoke test passed on M5 Ultra with the
patched runtime; see [VALIDATION.md](VALIDATION.md). Neither the unit tests nor
the smoke test establish model parity, production matte quality, M1 compatibility,
arbitrary resolution, HDR preservation, performance, or Flame import.

Before publishing an installer or enabling this in the Flame right-click action:

1. Use the pinned runtime and CPU projection patch documented in VALIDATION.md;
   rebuild its wheel after applying the patch. Keep authorized profiles separate.
2. Provision an isolated environment; run upstream tests and `--check` on each target Mac.
3. Run a supported FP32 still and real moving green/blue sequence; inspect
   matte range, foreground interpretation, temporal quality and memory.
4. Verify source frame correspondence, frame rate and color on manual Flame
   import, then composite with the existing Matchbox.
5. Design and validate arbitrary-shape profiles and HDR EXR input/output before
   replacing any existing production workflow.

Official CUDA source inspected at `485f5e9ab759ead6138cc990776184b59d6ea971`.
Community API inspected on 2026-11-03: `corridorkey_mlx/cli.py` blob
`c89eca9c0b81b18797a3f2e877f967dca8e9d3fc`.
The official older `nikopueringer/corridorkey-mlx` Hiera model is not CorridorKey 2.
