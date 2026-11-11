.pragma library

// The dragged item's centre picks its slot: it changes slot when the centre crosses into the next one.
// eslint-disable-next-line max-params -- QML and its tests pass the row geometry positionally
function slotAt(centreX, origin, pitch, count) {
  const slot = Math.floor((centreX - origin) / pitch);

  return Math.max(0, Math.min(count - 1, slot));
}

// eslint-disable-next-line max-params -- QML and its tests pass the row geometry positionally
function draggedX(pointerX, grabOffset, minX, maxX) {
  return Math.max(minX, Math.min(maxX, pointerX - grabOffset));
}

function lastX(origin, pitch, count) {
  return origin + (count - 1) * pitch;
}

// eslint-disable-next-line max-params -- the press and the pointer are passed as plain coordinates
function startsDrag(pressX, pressY, pointerX, pointerY, threshold) {
  return Math.abs(pointerX - pressX) + Math.abs(pointerY - pressY) >= threshold;
}
