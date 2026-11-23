#version 140

uniform sampler2D sampler;
uniform vec4 modulation;
uniform float animationProgress;
uniform float canvasX, canvasY, canvasWidth, canvasHeight;
uniform float sourceWidth, sourceHeight;
uniform float stripX, stripY, stripWidth, stripHeight;
uniform float taskX, taskY, taskWidth, minimizing;
uniform float classicStart, classicEnd;

#include "colormanagement.glsl"
#include "saturation.glsl"

in vec2 texcoord0;
out vec4 fragColor;

vec3 unpackRgb(float color)
{
    return mod(floor(color / vec3(65536.0, 256.0, 1.0)), 256.0) / 255.0;
}

vec4 paintClassicStrip(vec2 relative, vec2 origin, vec2 windowSize, vec4 source)
{
    // The native gradient keeps its full caption width as the visible strip is clipped.
    vec3 background = mix(unpackRgb(classicStart), unpackRgb(classicEnd), relative.x / stripWidth);
    if (relative.x >= stripWidth - 54.0)
        return vec4(background, 1.0);

    // The bottom row is clear of the title and buttons. Use it to recover the
    // foreground coverage from the live caption, including its antialiased edges.
    vec2 samplePoint = origin + vec2(relative.x, stripHeight - 1.0);
    vec3 oldBackground = texture(sampler, samplePoint / windowSize).rgb;
    vec3 foreground = minimizing > 0.5 ? vec3(1.0) : vec3(192.0 / 255.0);
    if (relative.x < 18.0) {
        // Preserve the icon's hue while moving its transparent edges onto the new background.
        vec3 darker = source.rgb * background / max(oldBackground, vec3(1.0 / 255.0));
        vec3 lighter = background + (source.rgb - oldBackground) * (1.0 - background)
            / max(1.0 - oldBackground, vec3(1.0 / 255.0));
        return vec4(mix(darker, lighter, greaterThanEqual(source.rgb, oldBackground)), 1.0);
    }
    vec3 contrast = foreground - oldBackground;
    float coverage = clamp(dot(source.rgb - oldBackground, contrast) / max(dot(contrast, contrast), 0.001), 0.0, 1.0);
    return vec4(mix(background, vec3(1.0), coverage), 1.0);
}

void main()
{
    vec2 windowSize = vec2(sourceWidth, sourceHeight);
    vec2 point = vec2(canvasX, canvasY) + texcoord0 * vec2(canvasWidth, canvasHeight);
    float progress = minimizing > 0.5 ? animationProgress : 1.0 - animationProgress;
    vec2 stripOrigin = vec2(stripX, stripY);
    vec2 relative = point - mix(stripOrigin, vec2(taskX, taskY), progress);
    float width = mix(stripWidth, taskWidth, progress);

    vec4 result = vec4(0.0);
    if (minimizing > 0.5 && all(greaterThanEqual(point, vec2(0.0))) && all(lessThan(point, windowSize))) {
        result = texture(sampler, point / windowSize);
    }
    if (all(greaterThanEqual(relative, vec2(0.0))) && all(lessThan(relative, vec2(width, stripHeight)))) {
        vec4 strip = texture(sampler, (stripOrigin + relative) / windowSize);
        if (classicStart >= 0.0)
            strip = paintClassicStrip(relative, stripOrigin, windowSize, strip);
        result = strip + result * (1.0 - strip.a);
    }
    fragColor = nitsToDestinationEncoding(adjustSaturation(sourceEncodingToNitsInDestinationColorspace(result)) * modulation);
}
