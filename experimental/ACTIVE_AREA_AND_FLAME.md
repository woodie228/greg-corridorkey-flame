# Confirmed empty margins and Flame handoff

## Fringe diagnosis and tested correction

The authorized clip's visible image is in columns 100–1179 of the 1280×720
test derivative. Across all 384 frames, neighbouring outside columns contain
only dark pillarbox data and compression ringing (peak 35/255); actual image
columns reach 254/255. The rough hints could mark those dark border pixels as
foreground, and black padding also contaminated boundary predictions.

The opt-in `--active-area 100 0 1080 720` path:

1. Crops only that explicitly confirmed source area, with no resize.
2. Reflect-pads the active image to the existing 768×1280 model profile.
3. Runs inference and crops its padding.
4. Restores the result to the original 1280×720 canvas at the original position.
   The excluded margins have zero alpha. RGB is edge-extended there for later
   straight-alpha sampling. No active-image pixels are eroded or rescaled.

Restoration checks every active RGB/matte pixel against the raw cropped model
result. The model still determines active-image alpha; this is not a global
choke or a rule deleting dark foreground. Tests retain black props on the active
boundary. Only use this option for confirmed empty margins: a wrong rectangle
would discard real content. It is never enabled automatically.

Apply the runtime patches in order to a fresh separate pinned source checkout:

- `mlx-cpu-reconstruction.patch`
- `mlx-temporal-hint-control.patch`
- `mlx-active-area.patch`

Check each with `git apply --check`, apply it, then rebuild the isolated wheel.
All three patches reproduce the tested source. All 27 community weight-free
tests pass. Do not modify the installed Flame/EZ-CorridorKey environment.

## Foreground/background conditioning refinement

An initial active-area test removed the vertical fringe but revealed that broad
chroma hints also retain a black studio backdrop. A dark-only reference removed
that patch but left a contour. The final tested helper can explicitly use
`--reference-mattes` from a matching reviewed/model matte sequence:

- Source-green-dominant pixels (G - max(R,B) > 0.04) retain the reference decision.
- Dark neutral pixels (maximum channel < 0.25 and spread < 0.06) retain it too.
- Other pixels use the rough chroma holdout, restoring the coloured barrier.

Thus a black helmet and black backdrop can follow different semantic matte
values; neither border connectivity nor colour alone decides to erase them.
Matching names/count/dimensions are required. This is a reviewed two-pass control,
not a universally correct automatic segmentation rule. Green wardrobe decisions
can be preserved from the reference rather than forcibly deleted. Tests exercise
that case. Source/reference quality still requires artist review.

The final tested recipe used the existing no-hint t4/no-carry Matte as reference,
then explicit t4 conditioning with carry disabled and the confirmed active area.
The original source was unchanged. No footage, hints, previews or weights are
included here.

## EXR handoff from the validated SDR output

```bash
/path/to/isolated/python experimental/export_flame_exr.py \
  /path/to/results /path/to/new-exr-handoff --fps 24000/1001
```

This writes/readback-verifies half-float ZIP OpenEXR sequences in FG, Matte,
Comp and Processed folders. `--float32` selects float instead. Foreground and
composite RGB are decoded from sRGB to scene-linear sRGB/Rec.709 primaries;
matte coverage is not gamma converted. Processed is straight RGB + alpha.
The manifest records the exact frame-rate fraction and assumptions. This path
is **SDR-derived**, and cannot recover HDR clipped by a PNG stage.

In a designated Flame test project/reel, import the sequences at the recorded
frame rate and assign colour deliberately: linear sRGB/Rec.709 for RGB, data
coverage for Matte. Do not silently label RGB as ACEScg. The installed original
hook's import helper can import the named folders, but actual rate/colour/alpha
interpretation must be checked in Flame; it is not certified by file readback.
No automatic project edits or installed hook changes are performed here.

## Linear Matchbox

The existing production Matchbox's despill function clamps RGB to [0,1], even
when using floating inputs. Do not use it to assess preservation of HDR/negative
RGB. `matchbox_linear/GregCorridorKey2Linear.mx` is a separate minimal companion:

1. Linear foreground RGB.
2. Matte RGB (red channel is coverage).
3. Optional linear background.

It outputs straight RGBA by default, with straight composite, premultiplied FG
and matte views. RGB is not clamped or display encoded. No despill, colour
transform, erosion or scaling is applied. Alpha alone is bounded to [0,1]. The
shader requests Float32 output. It compiled and packaged successfully with
Autodesk's 2025.2.2 shader_builder using Metal; the package has not been rendered
inside Flame. It is not installed and does not replace the existing Matchbox.

Flame surface inspection was cancelled; no import/render/project-edit commands
were sent to the app. A designated test project and renewed in-app validation
are still needed before calling this a finished Flame roundtrip or installer.
