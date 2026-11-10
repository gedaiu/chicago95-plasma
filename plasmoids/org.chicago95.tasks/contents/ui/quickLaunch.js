.pragma library

// Whether the taskbar shows its Quick Launch: Setup's option, "yes" or "no", or "auto": the look's own
// (the originals had one from 1998 on). Setup's quick_launch_shown decides the same way.
function shown(setting, look) {
    if (setting === "yes")
        return true
    if (setting === "no")
        return false
    return look !== "1995"
}
