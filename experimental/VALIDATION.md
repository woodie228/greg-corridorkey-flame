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

- Adapter: 11 tests passed, including preserving the venv Python symlink path.
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
retrieved at the pinned revision and is not self-hashed. For that initial still test, no t4, FP16, or Q8
profiles were downloaded. A later explicitly authorized t4 test is described below.

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

## Six-frame sequence using the same t1 profile

An additional test used six translated copies of the 720p synthetic plate,
shifting 6 pixels per frame (30 pixels total). No additional profiles were
obtained. The explicit `--framewise` option selected Hann window/stride 1/1;
RVM recurrence remains active in the community pipeline. This is not a t4
Hann-window test and is not a substitute for production moving footage.

All 24 outputs (six each of FG, Matte, Comp and Processed) fully decoded as
1280×720 uint16 PNGs. For every frame:

- Matte RGB channels were exactly equal.
- Processed alpha was exactly equal to the separate Matte channel.
- Processed RGB was exactly equal to FG, consistent with straight-alpha output.
- Matte was nonconstant; output frame names/counts matched the ordered source.

Alpha-weighted horizontal centroid moved from 563.19 to 593.03 pixels, consistent
with the deliberate 30-pixel source translation. First/last checker previews
were visually inspected. Runtime settings confirmed six frames, window/stride
1/1 and stage-two batch one. Settings are now preserved alongside the adapter
receipt, rather than discarded with scratch data. PNG sequence FPS in the
runtime is 24 by default; this does not preserve source timing for Flame.

To reproduce with an authorized supported PNG sequence and the existing profile:

```bash
python3 experimental/corridorkey2_mlx.py \
  --input /path/to/numbered-png-frames \
  --runtime-python /path/to/patched-runtime/.venv/bin/python \
  --model-root /path/to/authorized-fp32-profiles \
  --output-dir /path/to/new-results --framewise \
  --execute --acknowledge-model-terms
```

## User-provided real moving footage — limited excerpt

A subsequent authorized test used the first 24 consecutive frames of a
user-provided 1920×1080 H.264 green-screen clip at 24000/1001 fps. The excerpt
contains multiple people, arm movement and foreground/background subjects.
A workspace-only derivative was explicitly resized to 1280×720 with INTER_AREA
for the already downloaded t1 profile; the original file's SHA256 was unchanged
before and after processing. No extra model profile was downloaded.

Framewise FP32 inference completed with the patched isolated runtime. All 96
pass images decoded as 1280×720 uint16. On every frame, Processed alpha exactly
matched Matte and Processed RGB exactly matched FG; matte RGB channels matched.
Inspected checker previews showed removal of the green screen while retaining
the foreground player, crowd and barrier. A local review video was written at
the source frame rate. Source footage, previews, outputs and identifying source
metadata were not uploaded to this repository.

This is a successful limited real-footage execution/output check, not a
production approval: only 24 of 384 frames were tested, input was downsampled,
no ground-truth matte was available, no quantitative temporal quality claim is
made, and no native 1080p/t4/HDR or Flame import check was performed.

## Temporal t4 excerpt comparison

The matching `768x1280-t4/` profile was subsequently downloaded with explicit
permission at the same model revision. All four t4 files matched SHA256SUMS.
The same 24-frame real-footage excerpt completed at Hann window/stride 4/2.
All 96 t4 output images passed full decoding, dimensions/precision/frame-coverage
checks, and exact Processed alpha/RGB correspondence with Matte/FG.

Mean absolute alpha difference between t1 and t4 was 0.001267 on the 0–1 scale.
The largest local difference was 0.979446 at a source pillarbox edge, so the
small global mean must not be interpreted as uniform pixel agreement. Sampled
side-by-side previews looked broadly similar, retaining the player/crowd/barrier
and removing the screen. A local side-by-side review video was created.

Mean unwarped adjacent-frame alpha difference was 0.005694 for t1 and 0.005656
for t4. This includes real subject motion and is **not** a flicker/accuracy
metric or proof of better quality. Neither output is a ground-truth reference.

The new read-only `validate_outputs.py` reproduces decoding and channel checks
and alpha comparison. Four additional tests cover full decoding, alpha
corruption, wrong precision and mismatched source frames. All 15 repository
tests passed in the isolated environment (11 adapter + 4 decoding-validator).
The four decoding tests skip when OpenCV/NumPy are absent.

## Full 384-frame temporal run

All 384 frames of the same authorized clip were subsequently processed as a
workspace-only 1280×720 derivative with Hann 4/2 and the patched FP32 runtime.
Inference completed, and the read-only validator fully decoded all **1,536**
pass images. Every frame had the expected size, uint16 precision and pass names;
Processed alpha exactly equaled Matte and Processed RGB exactly equaled FG.
Runtime settings confirmed 384 frames, window 4, stride 2 and stage-two batch one.

A 384-frame local review video was written at 24000/1001 fps and verified by
reopening it. Source SHA256 was unchanged. Midpoint and final checker previews
were inspected in addition to the excerpt samples. **The midpoint t4 matte
incorrectly retains a rectangular patch of green screen behind the crowd.**
This is a material visual defect despite all decoding/coverage checks passing;
the output is not production approved. Its source (model decisions, temporal
carry, conversion or runtime numerical behavior) is not yet established. No footage, preview images,
outputs or identifying source metadata were uploaded. This verifies processing
coverage over this approximately 16-second shot; it is not a ground-truth matte
assessment, full playback quality approval, long-form stress test, or a native
1080p/Flame validation.

## Full-shot t1 control comparison

The same 384-frame derivative was then processed with t1/Hann 1/1 as a control.
All 1,536 t1 outputs passed full decoding and exact alpha/RGB channel checks.
Together, the two full runs produced 3,072 verified pass images. Source SHA256
remained unchanged. A separate full-shot t1 review video was written locally at
source frame rate. Neither run modified the original or installed Flame setup.

The matching t1 midpoint matte does not show the rectangular retained-screen
patch seen in t4. Mean absolute alpha difference over the full shot is 0.012280
on the 0–1 scale, with some local differences reaching 1.0. This is substantially
larger than the first-24-frame comparison; that short excerpt was insufficient
to assess later temporal behavior. The cause is unresolved. These observations
support gating t4, not certifying t1 as an accurate ground-truth result.

## Temporal mode is now explicit opt-in

The matching t1 midpoint matte does not show the retained rectangular screen
patch. This narrows the observed defect to the temporal path or its state
handling but does not establish a cause. Because of this evidence, the adapter
now defaults to Hann 1/1 for all sequences. `--temporal` is required to request
Hann 4/2 on sequences of at least four frames. `--framewise` is an explicit
alias for the default. Regression tests ensure longer inputs do not silently
select t4 and conflicting options are rejected. This does not certify t1
production quality; it avoids making the observed t4 defect the default.

## Still unvalidated

- M1 Ultra / M2 / M3 / M4 compatibility and memory requirements.
- Full production-shot quality approval, other temporal shots, long-form footage and blue-screen quality.
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

## Retained-screen fix and remaining foreground issue

Subsequent controlled investigation identified self-generated overlap-hint
feedback as the trigger for the rectangular retained-screen failure. A local
community-runtime patch adds `--no-carry-hint`; the adapter now always supplies
it when `--temporal` is requested. t1 remains the default. Explicit artist hints
are preserved by the runtime control. See TEMPORAL_DIAGNOSIS.md for the isolated
variable, patch instructions and tested evidence.

All 384 frames completed again with t4/Hann 4/2 and carry disabled. All 1,536
corrected passes passed full decoding and channel checks. The failed rectangle
was absent in inspected mattes/composites; the full-shot conservative screen-core
scan found zero green-dominant composite pixels at the documented threshold.
Mean screen-core alpha dropped from 0.027119 to 0.000378 (t1 control: 0.000382).
The full-shot alpha difference from t1 dropped from 0.012280 to 0.000384. Those
statistics are diagnostic comparisons, not ground-truth accuracy scores.

Selected prefix/full outputs agree exactly and source SHA256 remains unchanged.
The corrected review video contains 384 frames at source fps. Both patches apply
cleanly to the pinned community source. All 25 community synthetic tests (21
original plus four hint-policy/CLI checks) and all 15 repository tests pass.

A separate foreground omission was observed near a later close-up: both t1 and
corrected t4 remove some non-green barrier. No-hint subject selection is therefore
not certified for retaining every non-green scene element. The feedback fix is
validated for the observed rectangle, but the overall key is not production
approved; hint-based foreground control and artist review remain necessary.

## Explicit foreground-hint follow-up

The lost barrier was investigated with full-frame conditioning. A first rough
hint pilot restored it but a border-connected-dark flood-fill incorrectly cut
into a helmet touching the top edge. That method was rejected, not shipped.
The revised optional helper removes only uniform full-height dark border columns
when explicitly requested. A regression test preserves dark props touching the
frame edge. Reviewed artist hints remain preferable to an uncalibrated rule.

A revised 24-frame pilot preserved both barrier and helmet. The actual updated
adapter then processed all 384 frames with the generated full hint sequence,
t4/Hann 4/2 and self-generated carry disabled. All 1,536 pass images passed full
decoding and channel checks; the source hash was unchanged. The formerly missing
barrier ROI alpha increased from 0.000159 to 0.999916, and the helmet ROI remained
0.999904. A source-blue foreground-core proxy stayed near opaque across all
frames (mean 0.999879; minimum per-frame mean 0.999816).

No green-dominant composite pixels were detected in the conservative screen
cores across the shot, but mean screen-core alpha rose from 0.000378 to 0.003265.
Thin dark pillarbox-edge fringes also remain. These are disclosed trade-offs;
there is no production approval or complete ground-truth quality claim. See
FOREGROUND_HINTS.md for exact inputs, methods, test limitations and usage.

Artist first-frame/full-sequence input validation and forwarding are now opt-in
adapter features. The helper only creates conditioning inputs; it never masks
final outputs or modifies source plates. All 22 repository tests pass; the
runtime's existing 25 weight-free tests remain applicable. No footage, hints,
outputs or weights are distributed in this repository.

## Reviewed fringe correction and linear handoff follow-up

The earlier fringe and broad-hint trade-offs above are superseded for this test
recipe by explicit active-area inference and selective reference-guided hints.
See ACTIVE_AREA_AND_FLAME.md for the mechanism and required artist review.
All 384 frames were rerun at the explicit 1280×720 test resolution, retaining
the 1080×720 active image in its original canvas position. All 1,536 PNG pass
images decoded. Excluded pillarbox alpha was exactly zero throughout. No
active-image erosion, fixed roof mask or post-painted foreground was used.

Reviewed frames 0, 192, 255 and 383 no longer show the observed vertical fringe
or studio-backdrop contour; barrier and helmet remain. The source-blue core
proxy mean alpha was 0.999921 (minimum per-frame mean 0.999891). Mean screen-core
alpha was 0.000363; no green-dominant composite pixels were detected in those
conservative cores. These are diagnostic proxies, not ground truth or a claim
of perfect segmentation. The roof region had alpha about 0.000028 when empty
and 0.999861 when occupied by the helmet at frame 255. The original SHA-256
remained cc7c65bbd2ba33a70f61449efd2900a5f772639bdc824215b63e9364a82e1f8e.

The reviewed SDR result was converted into 1,536 half-float linear EXRs, all
readback verified (maximum absolute error 0.000244140625), with exact 24000/1001
fps and straight-alpha metadata. This conversion does not recover HDR detail.
The separate floating inference runner completed a synthetic +2-stop linear
EXR still and four-frame temporal exercise. Float32 foreground ranges were
[-0.00743945, 5.38610506] and [-0.00695781, 6.86033630], respectively; readback
error was zero. These bounded tests preserve negative/above-one data but do not
establish real camera-HDR accuracy or official CUDA photometric parity.

All 34 repository tests and 27 patched community weight-free tests pass. All
three runtime patches applied to a fresh pinned source and reproduced the
tested files. The separate linear Matchbox compiled and packaged successfully
with Autodesk Flame 2025.2.2 shader_builder. It is not installed or rendered in
Flame. A request to inspect the Flame application was cancelled by the user;
no import, render or project-edit command was sent, and inspection was not
retried. Actual Flame colour/alpha/render QA, M1 Ultra validation, native-1080p
profiles and real camera-HDR validation remain release gates. No media or model
assets are committed, and the installed production environment is unchanged.
