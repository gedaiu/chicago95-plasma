# Boot artwork sources

- `seven.png` packs 105 frames into a 15-column, seven-row sprite sheet, in
  row-major order. Each cell derives from the original 200×200
  Windows 7 boot frames in [PlymouthVista](https://github.com/furkrn/PlymouthVista),
  commit `e2b9605a7b4d649bb0e314cce8bbe9912633cfef`, `images/flag0.png`–`flag104.png`.
  The black matte is converted to alpha (RGB divided by max(R,G,B)); on a black
  background this reconstructs the original RGB within integer rounding. This
  also lets a custom background show behind the glow. `vista-progress.png` is
  that project's original `images/progress.png` bitmap.
- `SpinnerPaths.qml` contains only the 117 loading-dot glyph outlines U+E052–U+E0C6
  extracted from Windows 10's `segoe_slboot.ttf` in
  [SegoeBootSemilight](https://github.com/Diax170/SegoeBootSemilight), commit
  `fe017fe82a0f854ef33dcbcd53ef34db054e7558`. The font itself is not bundled or
  installed. The same dotted spinner appears in all four modern segments of the
  user-supplied video. The five additional empty glyphs after E0C6 are excluded:
  117 frames at 30 fps give the measured 3.9-second loop.
- `seven-text.png`, `seven-footer.png`, `vista-footer.png` are small crops of
  [Evolution of Windows Startup and Shutdown](https://www.youtube.com/watch?v=Z1ZHVuCi14E),
  supplied by the user. At 1920×1080: 338.5s, rectangles (800,720,320,80) and
  (800,1000,320,48); 296s, rectangle (800,864,320,48). They preserve stock
  typography without installing Microsoft's fonts; all customized text is live.
- Windows 8–11 logo geometry and gradients are independently drawn in QML using
  the supplied reference's measured bounds. They are not AI-generated pictures.

The Windows assets and marks belong to Microsoft. PlymouthVista labels its code
MIT and its resources Microsoft-owned; that code license does not relicense
these resources. The font-outline source likewise identifies the font as a
Microsoft resource. This project's code license does not claim ownership of
these assets. Keep these source notices with copies of the theme.

Regenerate imported assets from local source copies:

```sh
python setup/make_post_xp_boot.py \
  --vista /path/to/PlymouthVista \
  --font /path/to/SegoeBootSemilight/Win10/segoe_slboot.ttf \
  --video /path/to/Z1ZHVuCi14E.mp4
```

The optional video must be the 1920×1080 rendition. Inputs are read as data;
upstream installers and executables are never run. Python dependencies are
FontTools and Pillow; FFmpeg is needed only for the three video text crops.

Windows 7's native frame layout/rate is also documented by
[Coder for Life's BootRes tools](https://www.coderforlife.com/projects/win7boot/extras/):
105 200×200 frames at 15 fps. The loop starts at frame 60, as independently
confirmed by PlymouthVista's `boot7.sp`. Rendering tests check video geometry,
original lettering, animation wraparound and parity between QML and exported
Plymouth frames; they do not claim pixel identity on every hardware renderer.
