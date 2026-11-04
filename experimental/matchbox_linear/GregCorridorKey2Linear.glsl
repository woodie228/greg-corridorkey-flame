#version 120
// Straight scene-linear RGB. RGB is deliberately not clamped or display encoded.
uniform sampler2D fg_input;
uniform sampler2D matte_input;
uniform sampler2D bg_input;
uniform float adsk_result_w;
uniform float adsk_result_h;
uniform int output_mode;
void main()
{
    vec2 uv=gl_FragCoord.xy/vec2(adsk_result_w,adsk_result_h);
    vec3 fg=texture2D(fg_input,uv).rgb;
    float a=clamp(texture2D(matte_input,uv).r,0.0,1.0);
    vec4 result=vec4(fg,a);
    if(output_mode==1) {
        vec4 bg=texture2D(bg_input,uv);
        float ba=clamp(bg.a,0.0,1.0);
        float oa=a+ba*(1.0-a);
        vec3 premult=fg*a+bg.rgb*ba*(1.0-a);
        result=vec4(oa>0.000001 ? premult/oa : vec3(0.0),oa);
    } else if(output_mode==2) {
        result=vec4(fg*a,a);
    } else if(output_mode==3) {
        result=vec4(vec3(a),1.0);
    }
    gl_FragColor=result;
}
