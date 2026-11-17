"""Post-XP boot settings shared by the Control Panel and the frame exporter."""

STYLES = (
    ("Windows Vista", "vista"),
    ("Windows 7", "7"),
    ("Windows 8", "8"),
    ("Windows 8.1", "8.1"),
    ("Windows 10", "10"),
    ("Windows 11", "11"),
)
# Empty text hides it. "default" asks the selected OS for its original value.
FIELDS = {
    "BOOT_LOGO": "logo",
    "BOOT_NAME": "name",
    "BOOT_TEXT": "text",
    "BOOT_FOOTER": "footer",
    "BOOT_BACKGROUND": "background",
    "BOOT_FOREGROUND": "foreground",
    "BOOT_ACCENT": "accent",
    "BOOT_FONT": "font",
    "BOOT_BACKGROUND_IMAGE": "backgroundImage",
    "BOOT_ANIMATION": "animation",
    "BOOT_FRAMES": "frames",
    "BOOT_LOOP_START": "loopStart",
    "BOOT_FPS": "fps",
    "BOOT_LOGO_SIZE": "logoSize",
}


def options(values):
    return {name: values[key] for key, name in FIELDS.items() if key in values}
