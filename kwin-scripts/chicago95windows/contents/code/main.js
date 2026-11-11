// The taskbar menu's arrangements, measured from tests/references/win98cascade.png, win98tilev.png and win98tileh.png.
var CASCADE_STEP = { right: 22, down: 21 };
var CASCADE_SHARE = 0.875;
var GRID_FROM = 5;
var COLUMNS = { along: "width", across: "height" };
var ROWS = { along: "height", across: "width" };
var undo = null;

if (typeof registerShortcut === "function") {
  registerShortcut("Chicago95CascadeWindows", "Cascade Windows", "", cascadeWindows);
  registerShortcut("Chicago95TileWindowsHorizontally", "Tile Windows Horizontally", "", tileWindowsHorizontally);
  registerShortcut("Chicago95TileWindowsVertically", "Tile Windows Vertically", "", tileWindowsVertically);
  registerShortcut("Chicago95MinimizeAllWindows", "Minimize All Windows", "", minimizeAllWindows);
  registerShortcut("Chicago95UndoArrangement", "Undo Minimize All, Cascade or Tile", "", undoArrangement);
}

function cascadeWindows() {
  arrange(cascadeGeometry);
}

function tileWindowsVertically() {
  arrange(function (area, slot) {
    return tileGeometry(area, slot, COLUMNS);
  });
}

function tileWindowsHorizontally() {
  arrange(function (area, slot) {
    return tileGeometry(area, slot, ROWS);
  });
}

function minimizeAllWindows() {
  var windows = taskbarWindows().filter(function (window) {
    return !window.minimized && window.minimizable;
  });

  if (windows.length === 0) return;

  remember(windows);
  windows.forEach(function (window) {
    window.minimized = true;
  });
}

function undoArrangement() {
  if (undo === null) return;

  var remembered = undo;
  var present = workspace.windowList();

  undo = null;
  remembered.forEach(function (entry) {
    if (present.indexOf(entry.window) === -1) return;

    entry.window.minimized = entry.minimized;

    if (!entry.minimized) entry.window.frameGeometry = entry.geometry;
  });
}

function arrange(geometryOf) {
  var windows = taskbarWindows().filter(arrangeable);

  if (windows.length === 0) return;

  remember(windows);

  var area = workArea();

  windows.forEach(function (window, index) {
    // eslint-disable-next-line re-lint/no-flag-params -- KWin's setMaximize(vertically, horizontally)
    if (typeof window.setMaximize === "function") window.setMaximize(false, false);

    window.frameGeometry = geometryOf(area, { count: windows.length, index: index });
  });
}

function taskbarWindows() {
  return workspace
    .windowList()
    .filter(function (window) {
      return window.normalWindow && !window.skipTaskbar && onCurrentDesktop(window);
    })
    .sort(function (lower, upper) {
      return lower.stackingOrder - upper.stackingOrder;
    });
}

function arrangeable(window) {
  return !window.minimized && window.moveable && window.resizeable;
}

function remember(windows) {
  undo = windows.map(function (window) {
    return { window: window, geometry: window.frameGeometry, minimized: window.minimized };
  });
}

function workArea() {
  return workspace.clientArea(KWin.WorkArea, workspace.activeOutput, workspace.currentDesktop);
}

function onCurrentDesktop(window) {
  return (
    window.onAllDesktops || window.desktops.length === 0 || window.desktops.indexOf(workspace.currentDesktop) !== -1
  );
}

function cascadeGeometry(area, slot) {
  var stagger = slot.count - 1;

  return rectangle(
    area.x + slot.index * CASCADE_STEP.right,
    area.y + slot.index * CASCADE_STEP.down,
    Math.round((area.width - stagger * CASCADE_STEP.right) * CASCADE_SHARE),
    Math.round((area.height - stagger * CASCADE_STEP.down) * CASCADE_SHARE),
  );
}

// Windows fill lines along the axis (columns or rows), equal cells, a grid past GRID_FROM; the last line is stretched.
function tileGeometry(area, slot, axis) {
  var perLine = slot.count < GRID_FROM ? slot.count : Math.ceil(Math.sqrt(slot.count));
  var lines = Math.ceil(slot.count / perLine);
  var line = Math.floor(slot.index / perLine);
  var inLine = Math.min(perLine, slot.count - line * perLine);
  var place = slot.index - line * perLine;
  var along = span(area[axis.along], inLine, place);
  var across = span(area[axis.across], lines, line);

  return axis === COLUMNS
    ? rectangle(area.x + along.start, area.y + across.start, along.size, across.size)
    : rectangle(area.x + across.start, area.y + along.start, across.size, along.size);
}

function span(extent, parts, part) {
  var start = edge(extent, parts, part);

  return { start: start, size: edge(extent, parts, part + 1) - start };
}

function edge(extent, parts, part) {
  return Math.round((extent * part) / parts);
}

// eslint-disable-next-line max-params -- a geometry is its four numbers
function rectangle(left, top, width, height) {
  // eslint-disable-next-line id-length -- KWin names a geometry's corner x and y
  return { x: left, y: top, width: width, height: height };
}
