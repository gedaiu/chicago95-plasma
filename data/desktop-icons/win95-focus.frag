#version 440

layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;

layout(std140, binding = 0) uniform Params {
    mat4 qt_Matrix;
    float qt_Opacity;
    vec2 edge;
};
layout(binding = 1) uniform sampler2D source;

void main()
{
    vec2 distanceToEdge = min(qt_TexCoord0, 1.0 - qt_TexCoord0);
    if (all(greaterThanEqual(distanceToEdge, edge))) {
        fragColor = vec4(0.0);
    } else {
        vec4 wallpaper = texture(source, qt_TexCoord0);
        fragColor = vec4(wallpaper.a - wallpaper.rgb, wallpaper.a) * qt_Opacity;
    }
}
