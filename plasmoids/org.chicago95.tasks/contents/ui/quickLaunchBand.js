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
const FIT = -1;

function metrics() {
  return METRICS;
}

// `size` is the band's width in pixels between its separators, or FIT for as wide as all its launchers.
// eslint-disable-next-line max-params -- QML and its tests pass the taskbar's geometry positionally
function layout(width, contentX, lead, count, size, dock) {
  if (count === 0) {
    return {
      leftSeparatorX: -1,
      cellsX: -1,
      shown: 0,
      firstShown: 0,
      chevronX: -1,
      rightSeparatorX: -1,
      tasksX: contentX + METRICS.gapWithoutQuickLaunch,
      tasksEnd: width,
    };
  }

  const taskbar = { width: width, contentX: contentX, lead: lead, count: count, size: size };

  return dock === "right" ? rightDockedLayout(taskbar) : leftDockedLayout(taskbar);
}

function dockAfterDrag(gripX, width) {
  return gripX < width / 2 ? "left" : "right";
}

// The inner separator's band reaches it; the band never gets narrower than its chevron nor wider than half the taskbar.
// eslint-disable-next-line max-params -- as layout()
function sizeAfterDrag(gripX, width, contentX, lead, dock) {
  const reached =
    dock === "right"
      ? restingBandEnd(width) - gripX - separatorWidth(METRICS.separatorLead)
      : gripX - METRICS.gapBeforeRightSeparator - contentX - separatorWidth(lead);

  return Math.max(METRICS.chevronWidth, Math.min(Math.floor(width / 2), reached));
}

// eslint-disable-next-line max-params -- as layout()
function carriedShift(gripX, shape, dock, width, contentX) {
  const leftmost = contentX - shape.leftSeparatorX;
  const rightmost = width - shape.rightSeparatorX - separatorWidth(METRICS.separatorLead);

  return Math.max(leftmost, Math.min(rightmost, gripX - shape[outerSeparator(dock)]));
}

function outerSeparator(dock) {
  return dock === "right" ? "rightSeparatorX" : "leftSeparatorX";
}

// The chevron sits at the band's far end from its dock, so docked right it holds the first launchers.
function chevronLaunchers(count, size, dock) {
  const chevronCount = count - shownCount(count, size);
  const first = dock === "right" ? 0 : count - chevronCount;
  const launchers = [];

  for (let index = first; index < first + chevronCount; index++) launchers.push(index);

  return launchers;
}

function leftDockedLayout(taskbar) {
  const shown = shownCount(taskbar.count, taskbar.size);
  const bandX = taskbar.contentX + separatorWidth(taskbar.lead);
  const bandEnd = bandX + bandWidth(taskbar.count, taskbar.size);
  const rightSeparatorX = bandEnd + METRICS.gapBeforeRightSeparator;

  return {
    leftSeparatorX: taskbar.contentX,
    cellsX: bandX,
    shown: shown,
    firstShown: 0,
    chevronX: shown < taskbar.count ? bandEnd - METRICS.chevronWidth : -1,
    rightSeparatorX: rightSeparatorX,
    tasksX: rightSeparatorX + separatorWidth(METRICS.separatorLead),
    tasksEnd: taskbar.width,
  };
}

function rightDockedLayout(taskbar) {
  const shown = shownCount(taskbar.count, taskbar.size);
  const chevron = shown < taskbar.count;
  const bandX = restingBandEnd(taskbar.width) - bandWidth(taskbar.count, taskbar.size);
  const leftSeparatorX = bandX - separatorWidth(METRICS.separatorLead);

  return {
    leftSeparatorX: leftSeparatorX,
    cellsX: bandX + (chevron ? METRICS.chevronWidth : 0),
    shown: shown,
    firstShown: taskbar.count - shown,
    chevronX: chevron ? bandX : -1,
    rightSeparatorX: taskbar.width - separatorWidth(METRICS.separatorLead),
    tasksX: taskbar.contentX + METRICS.gapWithoutQuickLaunch,
    tasksEnd: leftSeparatorX,
  };
}

function restingBandEnd(width) {
  return width - separatorWidth(METRICS.separatorLead) - METRICS.gapBeforeRightSeparator;
}

function bandWidth(count, size) {
  return size === FIT ? cellsWidth(count) : size;
}

// All the launchers when the band holds them, else as many as fit beside the chevron.
function shownCount(count, size) {
  if (size === FIT || size >= cellsWidth(count)) return count;

  return Math.max(0, Math.floor((size - METRICS.chevronWidth) / METRICS.cellWidth));
}

function separatorWidth(lead) {
  return lead + METRICS.separatorBody;
}

function cellsWidth(count) {
  return count * METRICS.cellWidth;
}
