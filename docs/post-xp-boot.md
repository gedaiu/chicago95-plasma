# Vista through Windows 11 boot themes

Choose a style in **Control Panel → Booting Screen → Boot Screen**. Vista, 7, 8,
8.1, 10 and 11 are independent boot choices; the desktop and login style do not
change. **Test boot sequence** previews the selected theme without rebooting.
Applying the page exports that preview to Plymouth and rebuilds the boot image
through Setup's existing administrator-password flow.

The Windows 11 preset follows the **dotted spinner shown in the supplied video**,
not the newer solid-ring variant. The 8, 8.1 and 10 presets share that dotted
animation and the perspective logo; 11 has the square logo.

## Customization

The Vista-and-later groups expose all visible content. `default` means the
selected Windows version's original value. Empty loading/footer/name text hides
that text. The original names and logos do not override your custom choices.

| Setting                 | Content                                                             |
| ----------------------- | ------------------------------------------------------------------- |
| `BOOT_STYLE`            | `vista`, `7`, `8`, `8.1`, `10`, `11`                                |
| `BOOT_LOGO`             | `default`, `none`, or an image/SVG path                             |
| `BOOT_NAME`             | Optional product name                                               |
| `BOOT_TEXT`             | Loading message; `default` or your text (empty hides it)            |
| `BOOT_FOOTER`           | Footer; `default` or your text (empty hides it)                     |
| `BOOT_FONT`             | `default` or a font family installed on the machine                 |
| `BOOT_BACKGROUND`       | Background color                                                    |
| `BOOT_BACKGROUND_IMAGE` | Background picture path, or empty                                   |
| `BOOT_FOREGROUND`       | Text and loading-dot color                                          |
| `BOOT_ACCENT`           | Vista bar / Windows 8–11 logo color, or `default`                   |
| `BOOT_LOGO_SIZE`        | Logo/animation size in the 1920×1080 reference canvas, or `default` |
| `BOOT_ANIMATION`        | Empty for original, `none` to hide, or a vertical sprite-sheet path |
| `BOOT_FRAMES`           | Sprite frame count, or `default`                                    |
| `BOOT_LOOP_START`       | First repeating frame, zero-based, or `default`                     |
| `BOOT_FPS`              | Animation speed (1–60 frames/second), or `default`                  |

A custom Windows 7 logo automatically animates: the original light-only frames
are tinted from four regions of your logo, then reveal it with a repeating glow.
Transparent padding is ignored when sampling colors; monochrome logos work too.
Only the logo needs changing. The original Windows flag never appears in this mode.
Set animation to `none` for a static logo.

For a completely custom animation, select a vertical sprite sheet: equal-size frames
stacked top-to-bottom. Frame count, speed and first repeating frame let it have
a one-time introduction and a separate repeating section. These controls also
work with the other styles. Keep a source copy of custom images; they are read
when previewing and applying, then baked into the generated Plymouth assets.

Settings persist in `~/.config/chicago95/setup.conf`. For example:

```ini
BOOT_STYLE=7
BOOT_LOGO=/home/me/Pictures/my-logo.svg
BOOT_NAME=My OS
BOOT_TEXT=Starting My OS
BOOT_FOOTER=My company
BOOT_BACKGROUND=#101820
BOOT_FOREGROUND=#ffffff
BOOT_FONT=DejaVu Sans
```

Use `./install.sh --settings=/path/to/settings.conf --components=splash,plymouth`
to apply a settings file. `--boot-style=7` selects just the boot style through the
CLI. No additional services delay boot to finish an animation.

## Rendering and accuracy

`PostXpBoot.qml` draws the live preview. `chicago95-post-xp-boot` renders the same
component/settings into one background and small animation-region frames; the
Plymouth script replays those frames at the same rate. This avoids a large
full-screen movie and keeps password/question prompts available. Screen fitting
preserves aspect ratio on wide or tall displays.

Windows 7 stores all 105 original 200×200 frames in one 15×7 sprite sheet
(`postxp/seven.png`, 3000×1400). Playback is 15 fps; frames 60–104 loop.
Plymouth frames are generated only when building a theme, not stored separately
in the repository.
Windows 8–11 dots use the original Segoe Boot glyph outlines U+E052–U+E0C6,
117 frames at 30 fps (3.9 seconds). Vista uses its original bar bitmap and native
12-step-per-second motion. Native logos are scalable geometry measured against
the supplied video. The stock Vista/7 lettering uses small reference crops so
it works without the proprietary UI fonts; changing text, font, background or
foreground switches to editable text. Exact custom lettering requires the
chosen font to be installed; otherwise Qt substitutes an available font.

These are reference-matched recreations, not a claim of byte-for-byte Windows
rendering. Video compression, scaling, font substitution for custom text and
Plymouth's display backend can affect pixels. The source video is used only for
reference/layout, not replayed as the boot screen. No real reboot is part of the
automated tests.

See [asset sources](../splash/chicago95.splashscreen/contents/splash/postxp/SOURCES.md)
for provenance and regeneration instructions.
