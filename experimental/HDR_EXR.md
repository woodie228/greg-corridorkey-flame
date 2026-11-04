# Experimental unclipped linear EXR inference

There are two different EXR paths:

- `export_flame_exr.py`: SDR-derived PNG-to-linear EXR conversion for handoff.
  It does not recover clipped HDR data.
- `infer_linear_exr.py`: separate floating-point input, neural inference and
  unclamped float EXR output, bypassing the PNG stage.

The second path uses the pinned community model/pipeline with an independent
linear encoder and floating renderer/writer bound only inside the isolated
process. The original functions are restored after execution. Model weights
are unchanged. It is an experimental private-API integration, not an upstream
claim of support or a production-tested camera-HDR workflow.

Input must already be finite three-channel scene-linear RGB EXR, with
sRGB/Rec.709 primaries. No ACEScg, camera-log, PQ/HLG or gamut/metadata conversion
is automatic. The current runner uses the downloaded 768×1280 profile; native
images must fit it, optionally with an explicitly confirmed active area.
There is no hidden resize and no arbitrary native-1080p/4K support.

The model receives signed-asinh linear values. Only the foundation models get a
bounded SDR proxy. Foreground predictions are decoded to linear float without
[0,1] colour clipping; negative values survive. Alpha is bounded coverage.
Raw foreground, Matte, straight RGBA and checker composite go to FG, Matte,
Processed and Comp EXR folders. **Despill is deliberately disabled** in this
runner; apply an HDR-safe downstream operation if required. The new linear
Matchbox can assemble the passes, but is not a despill or colour-management tool.

```bash
/path/to/isolated/python experimental/infer_linear_exr.py \
  --input /path/to/linear-exr-plates --output-dir /path/to/new-hdr-output \
  --model-root /path/to/authorized-profiles --fps 24000/1001 \
  --hint-sequence /path/to/reviewed-png-mattes --temporal --float32 \
  --acknowledge-model-terms
```

Half-float is available by omitting `--float32`; values beyond finite half range
are rejected on readback rather than silently clipped. Model numerical accuracy
is not improved by choosing a wider output container. The pipeline still uses
the model interface's BF16 input rounding.

## Bounded validation

Unit checks cover signed HDR encoding, bounded foundation proxies, unclipped
negative/above-one float rendering, straight alpha and active-image preservation.
The EXR codec also roundtrips a negative/HDR/alpha sentinel independently.

Actual neural inference completed on one still and a four-frame Hann 4/2
sequence. Fixtures were made by decoding the authorized SDR plate to linear and
multiplying exposure by four; they are **synthetic HDR exercises**, not recovered
camera HDR detail. The float32 still output included negative RGB and values
above 1.0, with zero EXR readback error. These tests establish unclipped data
flow at a supported profile, not ground-truth colour/matte accuracy, photometric
parity with official CUDA, long HDR clips or real camera-HDR validation.

The existing legacy Matchbox clamps RGB and must not be used for this range
check. See ACTIVE_AREA_AND_FLAME.md for the separately compiled linear companion
and the still-unperformed Flame render/colour/alpha checks. M1 Ultra validation
and native-resolution profile work remain release gates.
