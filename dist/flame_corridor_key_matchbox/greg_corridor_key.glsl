#version 120

uniform sampler2D fg_input;
uniform sampler2D matte_input;
uniform sampler2D bg_input;
uniform sampler2D plate_input;

uniform float adsk_result_w;
uniform float adsk_result_h;

uniform int output_mode;
uniform int matte_channel;
uniform bool fg_srgb_to_linear;
uniform bool premultiply_output;
uniform bool invert_matte;
uniform float matte_black;
uniform float matte_white;
uniform float matte_gamma;
uniform float matte_blur;
uniform float matte_choke;
uniform float despill_strength;
uniform float edge_restore;
uniform float bg_mix;
uniform float mix_amount;
uniform float transform_x;
uniform float transform_y;
uniform float transform_scale;

float saturate(float value)
{
    return clamp(value, 0.0, 1.0);
}

vec3 saturate(vec3 value)
{
    return clamp(value, vec3(0.0), vec3(1.0));
}

vec4 sample_clamped(sampler2D tex, vec2 uv)
{
    return texture2D(tex, clamp(uv, vec2(0.0), vec2(1.0)));
}

vec4 sample_black(sampler2D tex, vec2 uv)
{
    if (uv.x < 0.0 || uv.x > 1.0 || uv.y < 0.0 || uv.y > 1.0) {
        return vec4(0.0);
    }
    return texture2D(tex, uv);
}

vec2 transformed_uv(vec2 uv)
{
    vec2 resolution = vec2(max(adsk_result_w, 1.0), max(adsk_result_h, 1.0));
    vec2 offset = vec2(transform_x, transform_y) / resolution;
    vec2 center = vec2(0.5);
    float scale = max(transform_scale, 0.001);
    return ((uv - center - offset) / scale) + center;
}

float luminance(vec3 color)
{
    return dot(color, vec3(0.2126, 0.7152, 0.0722));
}

vec3 srgb_to_linear(vec3 color)
{
    return pow(max(color, vec3(0.0)), vec3(2.2));
}

float matte_from_sample(vec4 matte_sample)
{
    if (matte_channel == 1) {
        return matte_sample.r;
    }
    if (matte_channel == 2) {
        return matte_sample.g;
    }
    if (matte_channel == 3) {
        return matte_sample.b;
    }
    if (matte_channel == 4) {
        return luminance(matte_sample.rgb);
    }
    return matte_sample.a;
}

float raw_matte(vec2 uv)
{
    float matte = matte_from_sample(sample_clamped(matte_input, uv));
    if (invert_matte) {
        matte = 1.0 - matte;
    }
    return matte;
}

float shaped_matte_at(vec2 uv)
{
    float matte = raw_matte(uv);
    matte = (matte - matte_black) / max(matte_white - matte_black, 0.0001);
    matte = saturate(matte);
    matte = pow(matte, max(matte_gamma, 0.001));
    return matte;
}

float soft_matte(vec2 uv)
{
    float blur_px = max(matte_blur, 0.0);
    if (blur_px <= 0.001) {
        return shaped_matte_at(uv);
    }

    vec2 pixel = vec2(1.0 / max(adsk_result_w, 1.0), 1.0 / max(adsk_result_h, 1.0));
    vec2 offset = pixel * blur_px;

    float matte = shaped_matte_at(uv) * 0.28;
    matte += shaped_matte_at(uv + vec2( offset.x,  0.0)) * 0.09;
    matte += shaped_matte_at(uv + vec2(-offset.x,  0.0)) * 0.09;
    matte += shaped_matte_at(uv + vec2( 0.0,  offset.y)) * 0.09;
    matte += shaped_matte_at(uv + vec2( 0.0, -offset.y)) * 0.09;
    matte += shaped_matte_at(uv + vec2( offset.x,  offset.y)) * 0.09;
    matte += shaped_matte_at(uv + vec2(-offset.x,  offset.y)) * 0.09;
    matte += shaped_matte_at(uv + vec2( offset.x, -offset.y)) * 0.09;
    matte += shaped_matte_at(uv + vec2(-offset.x, -offset.y)) * 0.09;

    return saturate(matte);
}

float adjusted_matte(vec2 uv)
{
    float matte = soft_matte(uv);
    if (abs(matte_choke) <= 0.001) {
        return matte;
    }

    vec2 pixel = vec2(1.0 / max(adsk_result_w, 1.0), 1.0 / max(adsk_result_h, 1.0));
    vec2 offset = pixel * max(abs(matte_choke), 0.001);

    float neighbor = soft_matte(uv + vec2( offset.x,  0.0));
    neighbor = max(neighbor, soft_matte(uv + vec2(-offset.x,  0.0)));
    neighbor = max(neighbor, soft_matte(uv + vec2( 0.0,  offset.y)));
    neighbor = max(neighbor, soft_matte(uv + vec2( 0.0, -offset.y)));
    neighbor = max(neighbor, soft_matte(uv + vec2( offset.x,  offset.y)));
    neighbor = max(neighbor, soft_matte(uv + vec2(-offset.x,  offset.y)));
    neighbor = max(neighbor, soft_matte(uv + vec2( offset.x, -offset.y)));
    neighbor = max(neighbor, soft_matte(uv + vec2(-offset.x, -offset.y)));

    float eroded = min(matte, 1.0 - (neighbor - matte));
    float dilated = max(matte, neighbor);

    if (matte_choke > 0.0) {
        return saturate(eroded);
    }
    return saturate(dilated);
}

vec3 despill(vec3 fg, vec3 plate, float matte)
{
    float screen = max(plate.g - max(plate.r, plate.b), 0.0);
    float edge = 1.0 - abs(matte * 2.0 - 1.0);
    float amount = saturate(despill_strength) * mix(0.35, 1.0, edge);

    vec3 cleaned = fg;
    cleaned.g = min(cleaned.g, max(cleaned.r, cleaned.b) + screen * (1.0 - amount));

    float restore = screen * edge * edge_restore * saturate(despill_strength);
    cleaned.r += restore * 0.35;
    cleaned.b += restore * 0.65;
    return saturate(cleaned);
}

void main()
{
    vec2 resolution = vec2(max(adsk_result_w, 1.0), max(adsk_result_h, 1.0));
    vec2 uv = gl_FragCoord.xy / resolution;
    vec2 fg_uv = transformed_uv(uv);

    vec4 fg_sample = sample_black(fg_input, fg_uv);
    vec4 bg_sample = sample_clamped(bg_input, uv);
    vec4 plate_sample = sample_black(plate_input, fg_uv);

    vec3 fg = fg_sample.rgb;
    if (fg_srgb_to_linear) {
        fg = srgb_to_linear(fg);
    }

    float matte = adjusted_matte(fg_uv);
    vec3 keyed_fg = despill(fg, plate_sample.rgb, matte);
    vec3 premult_fg = keyed_fg * matte;
    vec3 composite = mix(premult_fg, keyed_fg * matte + bg_sample.rgb * (1.0 - matte), saturate(bg_mix));

    vec2 pixel = vec2(1.0 / max(adsk_result_w, 1.0), 1.0 / max(adsk_result_h, 1.0));
    float edge_x = abs(adjusted_matte(fg_uv + vec2(pixel.x, 0.0)) - adjusted_matte(fg_uv - vec2(pixel.x, 0.0)));
    float edge_y = abs(adjusted_matte(fg_uv + vec2(0.0, pixel.y)) - adjusted_matte(fg_uv - vec2(0.0, pixel.y)));
    float edge = saturate((edge_x + edge_y) * 4.0);

    vec4 result = vec4(composite, matte);
    if (output_mode == 1) {
        result = vec4(premultiply_output ? premult_fg : keyed_fg, matte);
    } else if (output_mode == 2) {
        result = vec4(keyed_fg, 1.0);
    } else if (output_mode == 3) {
        result = vec4(vec3(matte), 1.0);
    } else if (output_mode == 4) {
        result = vec4(vec3(edge), 1.0);
    } else if (output_mode == 5) {
        result = vec4(abs(fg - keyed_fg) * 4.0, 1.0);
    }

    vec4 original = vec4(fg_sample.rgb, fg_sample.a);
    gl_FragColor = mix(original, result, saturate(mix_amount));
}
