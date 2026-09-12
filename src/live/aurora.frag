#version 440
// Borealis live wallpaper: animated aurora curtains (Qt 6 ShaderEffect).
// Output is premultiplied: alpha 0 at night = additive light over the sky,
// real alpha at dawn = soft veils over a light sky.
layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;
layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
    float time;
    float intensity;
    float dawn;
};

float hash(vec2 p) {
    p = fract(p * vec2(123.34, 456.21));
    p += dot(p, p + 45.32);
    return fract(p.x * p.y);
}

float noise(vec2 p) {
    vec2 i = floor(p);
    vec2 f = fract(p);
    vec2 u = f * f * (3.0 - 2.0 * f);
    return mix(mix(hash(i), hash(i + vec2(1.0, 0.0)), u.x),
               mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), u.x), u.y);
}

float fbm(vec2 p, int octaves) {
    float v = 0.0;
    float a = 0.5;
    for (int i = 0; i < 4; i++) {
        if (i >= octaves) break;
        v += a * noise(p);
        p = p * 2.03 + 11.7;
        a *= 0.5;
    }
    return v / (1.0 - pow(0.5, float(octaves)));
}

// one curtain; returns premultiplied colour (rgb) and coverage (a)
vec4 curtain(vec2 uv, float t, float y0, float rise, float amp, float height,
             float strength, float seed, float x0, float x1) {
    float x = uv.x;
    float xf = x + 0.03 * sin(6.2831 * (x * 2.2 + seed) + t * 0.09);
    float wob = fbm(vec2(xf * 2.2 + seed, t * 0.018), 3);
    float yb = y0 - rise * x
             + amp * sin(xf * 5.0 + t * 0.06 + seed * 3.1)
             + amp * 0.45 * sin(xf * 11.0 - t * 0.09 + seed)
             + (wob - 0.5) * amp * 1.5;
    float d = yb - uv.y;                       // > 0 above the lower edge
    float env = smoothstep(x0, x0 + 0.3, x) * (1.0 - smoothstep(x1 - 0.3, x1, x));
    float lowf = 0.45 + 0.55 * fbm(vec2(xf * 1.6 + seed * 2.0, t * 0.012), 2);
    // broad glow around the ribbon (cheap, always evaluated)
    float glow = exp(-abs(d - 0.05) / 0.09) * 0.3 * lowf * env * strength;
    vec3 glowC = mix(vec3(0.16, 0.55, 0.62), vec3(0.28, 0.33, 0.78), clamp(d * 3.0, 0.0, 1.0));
    if (d < -0.06 || d > height * 2.6 || env <= 0.001) {
        return vec4(glowC * glow, glow);
    }
    float rays = fbm(vec2(xf * 42.0 + seed * 7.0, t * 0.07), 3);
    rays = 0.3 + 0.7 * pow(clamp((rays - 0.25) / 0.75, 0.0, 1.0), 1.6);
    float fine = noise(vec2(xf * 260.0, t * 0.3));
    float tall = 0.6 + 0.8 * pow(fbm(vec2(xf * 9.0 - seed, t * 0.025), 2), 2.0);
    float h = height * tall;
    float cover = strength * rays * lowf * env * (0.85 + 0.15 * fine);
    // continuous profile: soft rise through the lower edge, slow decay upwards
    float edge = 0.014;
    float a = smoothstep(-0.022, edge, d) * exp(-max(d - edge, 0.0) / (h * 0.5)) * cover;
    float band = exp(-abs(d - 0.004) / 0.012) * cover;   // bright lower rim
    float k = clamp(d / h, 0.0, 1.0);
    vec3 edgeC = vec3(0.50, 0.95, 0.82);
    vec3 coreC = vec3(0.20, 0.84, 0.69);
    vec3 midC = vec3(0.30, 0.42, 0.94);
    vec3 topC = vec3(0.60, 0.42, 1.00);
    vec3 c = mix(edgeC, coreC, smoothstep(0.0, 0.10, k));
    c = mix(c, midC, smoothstep(0.10, 0.45, k));
    c = mix(c, topC, smoothstep(0.45, 0.85, k));
    vec3 light = c * a * 1.45 + edgeC * band * 0.55;
    return vec4(light + glowC * glow, a + band * 0.5 + glow);
}

void main() {
    vec2 uv = qt_TexCoord0;
    float t = time;
    vec4 c1 = curtain(uv, t, 0.64, 0.30, 0.06, 0.30, 1.0, 0.0, -0.25, 1.25);
    vec4 c2 = curtain(uv, t * 1.15, 0.42, 0.12, 0.03, 0.20, 0.5, 5.0, 0.2, 1.3);
    vec4 c = (c1 + c2) * intensity;
    if (dawn > 0.5) {
        // pastel veils over a light sky: normal (non-additive) blending
        float a = clamp(c.a * 0.55, 0.0, 0.85);
        vec3 hue = c.a > 0.0 ? c.rgb / c.a : vec3(0.0);
        hue = mix(hue, vec3(0.72, 0.76, 0.98), 0.25);
        fragColor = vec4(hue * a, a) * qt_Opacity;
    } else {
        fragColor = vec4(c.rgb, 0.0) * qt_Opacity;
    }
}
