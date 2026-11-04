# Native-pixel 1080p tile experiment

The pinned public FP32 bundle at revision
`7bb9a4443d5f1b4b696bcc0547d49ae0ac5e5f7e` contains 768×1280 and
1024×1536 profiles only. The public repository was checked again for this test;
it has no 1152×1920 padded profile for full-frame native 1920×1080 inference.
Changing graph shape declarations alone is not a verified model conversion.

The isolated alternative feeds overlapping **original-resolution crops** to the
existing 768×1280 model, then assembles a 1920×1080 result. This is native-pixel
tiled inference, **not** a full-frame 1080p model profile and not an enlarged
720p RGB result. Independent foundation/RVM/temporal context can change a tile's
matte. Broad overlap reduces visible joins but does not prove identical global
segmentation or motion consistency; artist review remains necessary.

## Tested clip recipe

The source has a confirmed 1620×1080 visible image at x=150 within its
1920×1080 canvas. Empty side margins are excluded explicitly, as in the 720p
active-area test. Do not reuse these coordinates on unrelated footage.

- Four native 1280×720 crops at (150,0), (490,0), (150,360), (490,360).
- Each is reflect-padded to 768×1280 without resizing source RGB.
- Existing FP32 t4/Hann 4/2 inference, explicit full-sequence hints, carry disabled,
  CPU reconstruction projection fix, independent recurrent state per tile.
- The reviewed 720p matte is linearly enlarged only as a conditioning reference;
  `rough_hint` evaluates source colours at native resolution. Semantic decisions
  inherited from that reference can therefore still limit the result.
- `native_tiles.assemble` blends distance-weighted coverage and linear-light
  premultiplied RGB, then returns straight SDR RGB. Transparent black does not
  darken opaque foreground in overlapping tiles. Every active pixel must be
  covered; gaps and invalid/nonfinite inputs fail. Empty margins have zero alpha.
- FG, Matte, Comp and straight RGBA Processed are 16-bit PNG at 1920×1080.
  A separate H.264 review is lossy; inspect PNGs for precise edge assessment.

Use `corridorkey2_mlx.py` separately on each crop sequence (1280×720 plates and
matching hints), with `--temporal --hint-sequence ... --execute
--acknowledge-model-terms`. All four runs use the existing downloaded model,
not a new model download or modified weights. Assemble matching FG/Matte frames
with `native_tiles.assemble(tiles, (1080,1920), (150,0,1620,1080))`, where each tile
is `(x, y, straight_rgb_float_0_to_1, coverage_float_0_to_1)`.

This is an SDR experiment. The assembler deliberately accepts [0,1] SDR RGB;
it is not the floating HDR runner. No Flame installation, project edit, import
or render is part of this test. Full-frame profile conversion, broader motion
and shot validation, native HDR and M1 Ultra remain separate work.

## Completed test and comparison

All 384 original 1920×1080 frames completed. Sixteen representative crop
comparisons against the decoded original proved exact native source-pixel
identity. All 1,536 assembled 16-bit PNG pass images decoded with matching
FG/RGBA RGB and matte/alpha. Empty-margin alpha was exactly zero throughout.
Four inference passes took 219.20, 223.54, 223.99 and 223.56 seconds: 890.29
seconds total (14.84 minutes, 0.431 assembled frames/second), excluding source
preparation, PNG assembly, validation and review encoding, on the existing
M5 Ultra environment. This is not a benchmark of a full-frame 1080p graph.

The 384-frame H.264 review is 1920×1080 at exact 24000/1001 fps (16.016 seconds),
18,204,936 bytes, with no audio. Every encoded frame decoded successfully.
Its name is `test1-reviewed-native-tiles-1080p.mp4`; it is kept locally with
private test outputs, not in Git. The original source hash is unchanged.

A 16-frame contact sheet spanning the shot and matching close-up comparisons
were inspected. Hair/fabric detail is finer than the 720p result enlarged to
1080p; source motion blur remains. No obvious tile join or earlier retained
backdrop outline was seen in those samples. Blue-core alpha averaged 0.999918
(minimum per-frame mean 0.999882); screen-core alpha averaged 0.000306, with
no green-dominant composite pixels in those conservative cores. These are
source-colour proxies, not ground truth. The published 720p diagnostics were
0.999921 and 0.000363 respectively, with slightly different sampling masks.
Do not interpret the small numerical differences as a proven quality ranking.

Against the same 720p matte enlarged for comparison, boundary alpha differs by
0.0522 on average: native inference changes the edge, not simply the container
size. At worst 0.0029% of previously opaque reference pixels became <0.9 alpha;
these are change diagnostics, not correctness judgments. Conditioning still
inherits semantic decisions from the 720p reference. Broad motion consistency,
other footage, M1 Ultra and a real Flame round trip remain unvalidated.

All 38 repository tests pass, including four native assembly checks. No new
models were downloaded and no production installation was changed.
