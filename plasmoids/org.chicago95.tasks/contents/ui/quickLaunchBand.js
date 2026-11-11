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

function metrics() {
  return METRICS;
}

// eslint-disable-next-line max-params -- QML and its tests pass the taskbar's geometry positionally
function layout(width, contentX, lead, count, cells, dock) {
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

  const taskbar = { width: width, contentX: contentX, lead: lead, count: count, cells: cells };

  return dock === "right" ? rightDockedLayout(taskbar) : leftDockedLayout(taskbar);
}

// The left separator docks the band by the half of the taskbar it is let go in.
// eslint-disable-next-line max-params -- as layout()
function leftSeparatorReleased(gripX, width, contentX, lead, count, cells, dock) {
  return { dock: gripX < width / 2 ? "left" : "right", cells: cells };
}

// eslint-disable-next-line max-params -- as layout()
function rightSeparatorReleased(gripX, width, contentX, lead, count, cells, dock) {
  return dock === "right"
    ? { dock: dock, cells: cellsFitting(bandWidth(count, cells) + gripX - restingRightSeparatorX(width), count) }
    : {
        dock: dock,
        cells: cellsFitting(gripX - METRICS.gapBeforeRightSeparator - contentX - separatorWidth(lead), count),
      };
}

// The chevron sits at the band's far end from its dock, so docked right it holds the first launchers.
function chevronLaunchers(count, cells, dock) {
  const chevronCount = count - shownCount(count, cells);
  const first = dock === "right" ? 0 : count - chevronCount;
  const launchers = [];

  for (let index = first; index < first + chevronCount; index++) launchers.push(index);

  return launchers;
}

function leftDockedLayout(taskbar) {
  const shown = shownCount(taskbar.count, taskbar.cells);
  const cellsX = taskbar.contentX + separatorWidth(taskbar.lead);
  const rightSeparatorX = cellsX + bandWidth(taskbar.count, taskbar.cells) + METRICS.gapBeforeRightSeparator;

  return {
    leftSeparatorX: taskbar.contentX,
    cellsX: cellsX,
    shown: shown,
    firstShown: 0,
    chevronX: shown < taskbar.count ? cellsX + cellsWidth(shown) : -1,
    rightSeparatorX: rightSeparatorX,
    tasksX: rightSeparatorX + separatorWidth(METRICS.separatorLead),
    tasksEnd: taskbar.width,
  };
}

function rightDockedLayout(taskbar) {
  const shown = shownCount(taskbar.count, taskbar.cells);
  const rightSeparatorX = restingRightSeparatorX(taskbar.width);
  const bandEnd = rightSeparatorX - METRICS.gapBeforeRightSeparator;
  const bandX = bandEnd - bandWidth(taskbar.count, taskbar.cells);
  const leftSeparatorX = bandX - separatorWidth(METRICS.separatorLead);

  return {
    leftSeparatorX: leftSeparatorX,
    cellsX: bandEnd - cellsWidth(shown),
    shown: shown,
    firstShown: taskbar.count - shown,
    chevronX: shown < taskbar.count ? bandX : -1,
    rightSeparatorX: rightSeparatorX,
    tasksX: taskbar.contentX + METRICS.gapWithoutQuickLaunch,
    tasksEnd: leftSeparatorX,
  };
}

function restingRightSeparatorX(width) {
  return width - separatorWidth(METRICS.separatorLead);
}

// All the cells when the space holds them, else as many as fit beside the chevron.
function cellsFitting(space, count) {
  if (space >= cellsWidth(count)) return -1;

  return Math.max(0, Math.min(count - 1, Math.round((space - METRICS.chevronWidth) / METRICS.cellWidth)));
}

function bandWidth(count, cells) {
  const shown = shownCount(count, cells);

  return cellsWidth(shown) + (shown < count ? METRICS.chevronWidth : 0);
}

function separatorWidth(lead) {
  return lead + METRICS.separatorBody;
}

function cellsWidth(count) {
  return count * METRICS.cellWidth;
}

function shownCount(count, cells) {
  return cells < 0 ? count : Math.min(cells, count);
}
