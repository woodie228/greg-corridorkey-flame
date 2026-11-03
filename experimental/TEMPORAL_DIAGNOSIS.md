# Temporal retained-screen defect: diagnosis and control

The original t4 run failed the key: it retained a rectangular screen region.
A successful file export is not sufficient validation. This document records
the controlled investigation, not a claim that every model output is correct.

## Isolated variable

A 200-frame prefix retained chronological state from the original shot start
and included the previously failing midpoint. The control changed only whether
self-generated auxiliary alpha predictions were fed into overlapping Hann
windows as trusted hints. The following stayed constant:

- Original decoded/resized frames, order and native test dimensions.
- t4 model graphs/weights, foundation models and RVM recurrence.
- Reflect padding/cropping, Hann 4/2 windows and taper calculation.
- FP32 precision policy, compilation, optimizations and CPU reconstruction patch.

There is no external image-tiling step in this runtime. The Hann taper matches
the official runtime's formula. Those facts, together with the controlled
feedback toggle, do not support fixing this by cropping/padding or changing tile
sizes. They also do not establish CUDA/MLX parity or rule out numerical error as
a possible seed of feedback drift.

## Prefix result

Disabling self-generated carry removed the visible rectangle at the matching
midpoint. In a conservative source-green screen-core mask, mean midpoint alpha
was 0.067590 with carry enabled and 0.000101 with carry disabled; the t1 result
was 0.000110. The mask used the largest connected green-dominant region eroded
by four pixels to exclude most edges. It is a diagnostic proxy, not a labeled
matte or a rule for deleting green foreground objects.

This identifies self-generated hint feedback as the trigger for the observed
failure on this shot. It does not prove whether the seed error originates in the
learned model, conversion, or another runtime numerical difference. Determining
that deeper origin requires comparison against the official runtime.

## Local runtime change

`patches/mlx-temporal-hint-control.patch` adds `--no-carry-hint` to the pinned
community CLI. It stops using and storing self-generated overlap hints while
preserving explicit first-frame and full-frame hints. This follows an inference
choice already present in the official CorridorKey runtime; weights, model
outputs and input pixels are not modified. It is not a despill-only workaround
or a painted-out output mask.

Apply both runtime patches to a fresh separate checkout of commit
`74065491ebd2eddea494ab34c15a6d84d7415353`, then rebuild its isolated wheel.
Both patches were checked against the pinned source and reproduce the tested
source files. Do not apply them to the installed Flame/EZ-CorridorKey environment.
The community source's Apache license and NOTICE remain under `third_party/`.

The adapter retains t1 as default. `--temporal` now always supplies
`--no-carry-hint`; there is no adapter switch to re-enable the failing feedback
path. An unpatched CLI rejects the flag during preflight, before model loading.
The run receipt and runtime settings record the selected policy.

Four local upstream regression tests cover disabling feedback, preserving
explicit hints, retaining the original enabled behavior, and CLI forwarding.
All 25 community weight-free tests passed with both runtime patches. All 15
repository tests passed, including asserting that temporal plans disable carry.

See VALIDATION.md for full-shot verification and remaining release gates.

## Full-shot verification of the fix

The actual updated adapter completed all 384 frames with t4/Hann 4/2 and
`carry_hint: false`. All 1,536 output images passed full decoding, shape/precision,
coverage and exact FG/Matte/Processed channel checks. Selected common frames
(including the failed midpoint) exactly matched the 200-frame control, excluding
run truncation as the explanation. Original source SHA256 was unchanged.

Across all 384 frames, mean framewise screen-core alpha was:

| Mode | Mean screen-core alpha |
| --- | ---: |
| t1 control | 0.000382 |
| t4 with self-generated carry (failed) | 0.027119 |
| t4 with carry disabled | 0.000378 |

The corrected composites contained zero green-dominant pixels in those screen
cores under the diagnostic threshold G-R > 0.02 and G-B > 0.02 in normalized
output values. Previously failing frames and mattes were visually inspected,
including the midpoint and the later largest-difference section. The retained
rectangle was absent. A local 384-frame corrected review video was verified at
23.976 fps. No media or weights were uploaded.

These are bounded checks, not an assertion of perfectly zero alpha at every
background pixel or perfect foreground preservation. Some source-green core
pixels still have alpha above 0.1 (up to 2.88% in one frame), comparable to t1;
motion edges and the heuristic mask require review. More importantly, **both t1
and corrected t4 omit part of a non-green barrier in a later close-up**. That is
a separate no-hint subject-selection/foreground-preservation problem. It must
not be hidden by declaring the entire shot production-ready. Explicit artist
or carefully validated full-frame hints are a possible next control; they have
not yet been tested on this shot.

The observed rectangular screen failure is resolved by the controlled feedback
policy on this shot. The deeper source of the initial auxiliary prediction error
(model behavior versus conversion/runtime differences) remains unproven without
an official-runtime comparison. Native resolution/HDR, Flame, M1 Ultra and wider
footage validation remain independent release gates.
