.pragma library

const CELL_WIDTH = 23;
const REMOVE_DISTANCE = 12;

// eslint-disable-next-line max-params -- QML and its tests pass the drag geometry positionally
function dragResult(fromIndex, pointX, pointY, width, height, quickLaunchX, count) {
  if (isBeyondEdge(pointX, width) || isBeyondEdge(pointY, height)) return { action: "remove", to: -1 };

  const gap = insertionIndexAt(pointX, quickLaunchX, count);
  const to = gap > fromIndex ? gap - 1 : gap;

  return to === fromIndex ? { action: "none", to: -1 } : { action: "move", to: to };
}

function insertionIndexAt(pointX, quickLaunchX, count) {
  const gap = Math.round((pointX - quickLaunchX) / CELL_WIDTH);

  return Math.max(0, Math.min(count, gap));
}

function isBeyondEdge(position, extent) {
  return position < -REMOVE_DISTANCE || position > extent + REMOVE_DISTANCE;
}
