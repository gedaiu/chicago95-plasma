.pragma library
.import "Layout.js" as Layout

function metrics(borderSize, buttonSize, scale) {
    const theme = Object.assign({}, Layout.values)
    // Aurorae clamps the theme's SVG margins to the user's KWin border preset.
    const limits = [[0, 0], [1, 4], [1, 4], [4, 6], [6, 8], [8, 12], [12, 20], [23, 30], [36, 48]]
    const [minimum, maximum] = limits[borderSize] ?? limits[3]
    for (const edge of ["Left", "Right", "Bottom"]) {
        const key = "border" + edge
        theme[key] = borderSize === 1 && edge !== "Bottom" ? 0
            : Math.min(maximum, Math.max(minimum, theme[key]))
        theme[key + "Maximized"] = 0
    }
    theme.horizontalAlignment = Qt.AlignLeft
    theme.verticalAlignment = Qt.AlignVCenter
    theme.buttonSizeFactor = [0.8, 1, 1.2, 1.4, 1.6, 1.8, 2][buttonSize] ?? 1
    // The 144 DPI guest paints adjacent 45, 40 and 75 pixel buttons.
    if (scale >= 1.5) {
        theme.buttonSpacing = 0
        theme.buttonWidthMaximizeRestore = 40 / 1.5
    } else {
        // Half a logical pixel of overlap aligns all three glyphs on the 96 DPI grid.
        theme.buttonSpacing = -0.5
    }
    theme.buttonMarginTopMaximized = 0
    const height = Math.max(theme.titleHeight, theme.buttonHeight * theme.buttonSizeFactor + theme.buttonMarginTop)
    theme.borderTop = height + theme.titleEdgeTop + theme.titleEdgeBottom
    theme.borderTopMaximized = height + theme.titleEdgeTopMaximized + theme.titleEdgeBottomMaximized
    // Raise the optical centre of the lettering one pixel within the full glass frame.
    theme.titleHeight -= 2
    return theme
}
