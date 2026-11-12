.pragma library

// The Quick Launch band between its two separators; the QML and tests/test_quick_launch_band.py read these sizes.
const METRICS = {
  cellWidth: 23,
  iconInset: 3,
  chevronWidth: 16,
  separatorLead: 2,
  separatorLeadAfterStart2000: 3,
  separatorBody: 11,
  gapBeforeRightSeparator: 2,
  gapWithoutQuickLaunch: 4,
  taskButtonGap: 3,
};
const LUNA_METRICS = Object.assign({}, METRICS, {
  chevronWidth: 13,
  separatorLead: 4,
  separatorBody: 10,
});
const FIT = -1;

function metrics(taskbarStyle) {
  return taskbarStyle === "luna" ? LUNA_METRICS : METRICS;
}

// The band's size when it fits every launcher, for QML: a library's constants are not visible there.
function fitAll() {
  return FIT;
}

// `size` is the band's width in pixels between its separators, or FIT for as wide as all its launchers.
// eslint-disable-next-line max-params -- QML and its tests pass the taskbar's geometry positionally
function layout(width, contentX, lead, count, size, dock, metrics = METRICS) {
  if (count === 0) {
    return {
      leftSeparatorX: -1,
      cellsX: -1,
      shown: 0,
      firstShown: 0,
      chevronX: -1,
      rightSeparatorX: -1,
      tasksX: contentX + metrics.gapWithoutQuickLaunch,
      tasksEnd: width,
    };
  }

  const taskbar = { width: width, contentX: contentX, lead: lead, count: count, size: size };

  return dock === "right" ? rightDockedLayout(taskbar, metrics) : leftDockedLayout(taskbar, metrics);
}

function dockAfterDrag(gripX, width) {
  return gripX < width / 2 ? "left" : "right";
}

// The inner separator's band reaches it; the band never gets narrower than its chevron nor wider than half the taskbar.
// eslint-disable-next-line max-params -- as layout()
function sizeAfterDrag(gripX, width, contentX, lead, dock, metrics = METRICS) {
  const reached =
    dock === "right"
      ? restingBandEnd(width, metrics) - gripX - separatorWidth(metrics.separatorLead, metrics)
      : gripX - metrics.gapBeforeRightSeparator - contentX - separatorWidth(lead, metrics);

  return Math.max(metrics.chevronWidth, Math.min(Math.floor(width / 2), reached));
}

// eslint-disable-next-line max-params -- as layout()
function carriedShift(gripX, shape, dock, width, contentX, metrics = METRICS) {
  const leftmost = contentX - shape.leftSeparatorX;
  const rightmost = width - shape.rightSeparatorX - separatorWidth(metrics.separatorLead, metrics);

  return Math.max(leftmost, Math.min(rightmost, gripX - shape[outerSeparator(dock)]));
}

function outerSeparator(dock) {
  return dock === "right" ? "rightSeparatorX" : "leftSeparatorX";
}

// The chevron sits at the band's far end from its dock (band: {count, size, dock}): docked right, the first launchers.
function chevronLaunchers(band, metrics = METRICS) {
  const chevronCount = band.count - shownCount(band.count, band.size, metrics);
  const first = band.dock === "right" ? 0 : band.count - chevronCount;
  const launchers = [];

  for (let index = first; index < first + chevronCount; index++) launchers.push(index);

  return launchers;
}

function leftDockedLayout(taskbar, metrics) {
  const shown = shownCount(taskbar.count, taskbar.size, metrics);
  const bandX = taskbar.contentX + separatorWidth(taskbar.lead, metrics);
  const bandEnd = bandX + bandWidth(taskbar.count, taskbar.size, metrics);
  const rightSeparatorX = bandEnd + metrics.gapBeforeRightSeparator;

  return {
    leftSeparatorX: taskbar.contentX,
    cellsX: bandX,
    shown: shown,
    firstShown: 0,
    chevronX: shown < taskbar.count ? bandEnd - metrics.chevronWidth : -1,
    rightSeparatorX: rightSeparatorX,
    tasksX: rightSeparatorX + separatorWidth(metrics.separatorLead, metrics),
    tasksEnd: taskbar.width,
  };
}

function rightDockedLayout(taskbar, metrics) {
  const shown = shownCount(taskbar.count, taskbar.size, metrics);
  const chevron = shown < taskbar.count;
  const bandX = restingBandEnd(taskbar.width, metrics) - bandWidth(taskbar.count, taskbar.size, metrics);
  const leftSeparatorX = bandX - separatorWidth(metrics.separatorLead, metrics);

  return {
    leftSeparatorX: leftSeparatorX,
    cellsX: bandX + (chevron ? metrics.chevronWidth : 0),
    shown: shown,
    firstShown: taskbar.count - shown,
    chevronX: chevron ? bandX : -1,
    rightSeparatorX: taskbar.width - separatorWidth(metrics.separatorLead, metrics),
    tasksX: taskbar.contentX + metrics.gapWithoutQuickLaunch,
    tasksEnd: leftSeparatorX,
  };
}

function restingBandEnd(width, metrics) {
  return width - separatorWidth(metrics.separatorLead, metrics) - metrics.gapBeforeRightSeparator;
}

function bandWidth(count, size, metrics) {
  return knownSize(size) === FIT ? cellsWidth(count, metrics) : size;
}

// All the launchers when the band holds them, else as many as fit beside the chevron.
function shownCount(count, size, metrics = METRICS) {
  if (knownSize(size) === FIT || size >= cellsWidth(count, metrics)) return count;

  return Math.max(0, Math.floor((size - metrics.chevronWidth) / metrics.cellWidth));
}

function separatorWidth(lead, metrics = METRICS) {
  return lead + metrics.separatorBody;
}

function cellsWidth(count, metrics = METRICS) {
  return count * metrics.cellWidth;
}

// Right after Setup, Plasma can hand over a setting it has not loaded yet: anything but a number fits every launcher.
function knownSize(size) {
  return typeof size === "number" && Number.isFinite(size) ? size : FIT;
}
