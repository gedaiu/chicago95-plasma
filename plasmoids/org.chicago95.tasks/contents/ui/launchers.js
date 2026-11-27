.pragma library
.import "quickLaunchBand.js" as Band

const REMOVE_DISTANCE = 12;

// A launcher let go this far outside the taskbar is removed; dragging along it only sorts (DragSortArea.qml).
// eslint-disable-next-line max-params -- QML passes the point and the taskbar's size positionally
function releasedOffTaskbar(pointX, pointY, width, height) {
  return isBeyondEdge(pointX, width) || isBeyondEdge(pointY, height);
}

// eslint-disable-next-line max-params -- match the pitch of the visible launcher cells
function insertionIndexAt(pointX, quickLaunchX, count, cellWidth = Band.metrics().cellWidth) {
  const gap = Math.round((pointX - quickLaunchX) / cellWidth);

  return Math.max(0, Math.min(count, gap));
}

function isBeyondEdge(position, extent) {
  return position < -REMOVE_DISTANCE || position > extent + REMOVE_DISTANCE;
}
