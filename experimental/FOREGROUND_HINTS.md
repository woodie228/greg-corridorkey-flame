# Explicit foreground conditioning — experimental

The no-hint model sometimes omits non-green scene elements. In the authorized
shot, a blue/purple barrier disappears during a close-up in both t1 and t4.
Explicit hints can tell the model which regions must remain foreground. Hints
condition the neural inference; this adapter does not copy them into the final
alpha or mask the output by a color rule.

## Artist-provided hints

The adapter accepts:

- `--hint-first-frame /path/to/matte.png`: a grayscale or RGBA PNG, same native
  dimensions as the plate. The RGBA alpha channel is used.
- `--hint-sequence /path/to/numbered-mattes`: grayscale/RGBA PNG frames matching
  the source count and native dimensions. Names must be equally zero-padded,
  numeric and contiguous. Association is by ordered position; the run receipt
  records both file lists. Grayscale white means foreground, black background.

Both may be supplied; the explicit first-frame hint takes precedence on frame
zero. The upstream community runtime currently uses hint confidence 0.95.
Sequence frame counts and dimensions are checked before execution. Artist RGB
mattes should be exported as grayscale/RGBA rather than relying on a color
channel's interpretation. First-frame argument forwarding is unit tested;
actual model experiments here use a full hint sequence.

Example with the separately installed, patched runtime and authorized models:

```bash
python3 experimental/corridorkey2_mlx.py \
  --input /path/to/plates --hint-sequence /path/to/mattes \
  --runtime-python /path/to/patched-runtime/.venv/bin/python \
  --model-root /path/to/authorized-profiles --output-dir /path/to/new-results \
  --temporal --execute --acknowledge-model-terms
```

The temporal path still disables self-generated carry, so explicit hints remain
authoritative instead of being replaced by drifting model predictions.

## Optional rough green-screen hint prototype

`make_green_hints.py` creates **conditioning candidates**, not finished mattes.
It accepts ordered 8/16-bit three-channel SDR PNG plates and writes a new
16-bit grayscale PNG directory. It uses green dominance, with a soft transition
from 0.04 to 0.20 in normalized channel-difference units. Source pixels are not
modified. These thresholds are a tested shot-specific prototype, not calibrated
for every screen, color space or exposure.

```bash
/path/to/isolated/.venv/bin/python experimental/make_green_hints.py \
  /path/to/plates /path/to/new-rough-hints
```

An explicit `--remove-black-columns` option suppresses only uniform full-height
dark columns contiguous with either image edge, for known pillarboxed plates.
It is off by default. Even that rule needs review when a real black foreground
object fills a complete edge column. An earlier flood-fill approach was rejected
because it cut into a dark helmet touching the top edge; it is not shipped.
A regression test preserves such dark props.

Review the hints before using them. Green clothes, green reflections, translucent
materials, blur, screen lighting and dark columns can be mislabeled. Prefer
artist mattes when these rules do not express the intended foreground. Generated
hints are never silently enabled by the adapter or applied to final pixels.

See VALIDATION.md for the real-model tests and unresolved release gates.

## Authorized real-shot validation

The revised helper exactly reproduced the successful 24-frame pilot hints.
The full 384-frame 720p derivative was then processed with t4/Hann 4/2, carry
disabled, and one explicit grayscale hint per source frame. All 1,536 pass images
passed full decoding, precision/dimension/frame coverage and exact pass-channel
checks. Original source SHA256 remained unchanged. A full local review video was
verified at 23.976 fps; media and hints were not uploaded.

At the formerly missing barrier ROI in the failing close-up, mean alpha changed
from 0.000159 without hints to 0.999916 with hints. Helmet ROI alpha remained
0.999904, without the rejected flood-fill holes. Across the shot, an eroded
source-blue foreground-core diagnostic had mean alpha 0.999879 and minimum
per-frame mean 0.999816. This color-core proxy checks the affected barrier/blue
clothing; it is not a complete foreground ground truth.

The conservative screen-core scan detected zero green-dominant composite pixels
at the documented threshold across all 384 frames. However, mean screen-core
alpha increased from 0.000378 to 0.003265 with the rough hints. Some motion edges
and spill can enter that proxy; the increase still needs review rather than
being hidden behind a green-pixel result. Thin dark fringes near the pillarbox
boundary also remain visible. This is an effective tested foreground control,
not a claim of perfect matte quality or a universally safe automatic preset.

All 22 repository tests pass (14 adapter, four output-validator, four hint-helper).
The unchanged patched runtime retains its 25 passing weight-free tests. Artist
hint quality, other wardrobe/screens/exposures, HDR/native resolution, Flame and
M1 Ultra checks remain release gates.

## Selective reviewed reference control

`--reference-mattes /path/to/matching/mattes` on the hint helper can retain
reference decisions in source-green-dominant and dark neutral pixels while
boosting other foreground holdouts. This addresses the black backdrop/contour
retention found when plain chroma hints treated every non-green pixel as
foreground. It preserves semantic green-wardrobe and dark-prop decisions from
the reference. See ACTIVE_AREA_AND_FLAME.md for thresholds, matching requirements,
the final full-shot recipe and limitations. It does not turn the reference into
a ground-truth matte or silently enable a second pass.

The latest reviewed fringe correction supersedes the earlier pillarbox/backdrop
trade-off for the tested clip: use explicit confirmed active-area inference and
selective reference-guided hints. See [the active-area recipe](ACTIVE_AREA_AND_FLAME.md)
and [latest validation](VALIDATION.md). This remains an experimental two-pass
workflow requiring artist review, not a universal automatic foreground rule.
