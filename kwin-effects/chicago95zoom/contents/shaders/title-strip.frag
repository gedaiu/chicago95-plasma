#version 140

uniform sampler2D sampler;
uniform vec4 modulation;
uniform float animationProgress;
uniform float canvasX, canvasY, canvasWidth, canvasHeight;
uniform float sourceWidth, sourceHeight;
uniform float stripX, stripY, stripWidth, stripHeight;
uniform float taskX, taskY, taskWidth, minimizing;

#include "colormanagement.glsl"
#include "saturation.glsl"

in vec2 texcoord0;
out vec4 fragColor;

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
        result = strip + result * (1.0 - strip.a);
    }
    fragColor = nitsToDestinationEncoding(adjustSaturation(sourceEncodingToNitsInDestinationColorspace(result)) * modulation);
}
