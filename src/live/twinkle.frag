#version 440
// Makes the stars of the sky texture twinkle: brightens/dims bright pixels
// per ~4px cell with a slow, per-star phase.
layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;
layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
    float time;
    float amount;
    vec2 cells;
};
layout(binding = 1) uniform sampler2D source;

float hash(vec2 p) {
    p = fract(p * vec2(234.34, 435.345));
    p += dot(p, p + 34.23);
    return fract(p.x * p.y);
}

void main() {
    vec4 s = texture(source, qt_TexCoord0);
    float lum = dot(s.rgb, vec3(0.299, 0.587, 0.114));
    float star = smoothstep(0.22, 0.6, lum);
    vec2 cell = floor(qt_TexCoord0 * cells);
    float ph = hash(cell) * 6.2831;
    float rate = 0.6 + 1.6 * hash(cell + 7.1);
    float tw = 1.0 + amount * star * sin(time * rate + ph);
    fragColor = vec4(s.rgb * tw, s.a) * qt_Opacity;
}
