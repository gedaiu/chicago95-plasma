.pragma library

// Windows 7's superbar pages whole buttons: a page holds what fits beside the up and down arrows, at least one.
function layout(count, band) {
  const pitch = band.buttonWidth + band.gap;
  if (count * pitch - band.gap <= band.room) return { perPage: count, pages: 1 };
  const perPage = Math.max(1, Math.floor((band.room - band.arrowWidth) / pitch));

  return { perPage: perPage, pages: Math.ceil(count / perPage) };
}

function clamped(page, pages) {
  return Math.min(Math.max(page, 0), pages - 1);
}
