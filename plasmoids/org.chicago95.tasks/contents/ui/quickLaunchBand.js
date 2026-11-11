.pragma library

// The Quick Launch band and the window buttons (tests/test_quick_launch_band.py). Each band leads with a
// separator; the band shows `cells` launchers (-1: all of them) and a chevron for the rest. Docked left it
// follows the Start button, chevron last; docked right it ends the taskbar, chevron first, beside its
// separator, so its first launchers are the hidden ones. The QML and the tests read their sizes here.

const METRICS = {
  cellWidth: 23, // a Quick Launch button
  iconInset: 3, // its 16px icon's gap from the cell's left and top
  chevronWidth: 16, // the "»" that opens the launchers the band has no room for
  separatorLead: 2, // the gap before a separator's etched line; 3 after 2000's wider Start button
  separatorLeadAfterStart2000: 3,
  separatorBody: 11, // the etched line, 2px of face, the 3px grip and 4px after it
  gapBeforeTaskSeparator: 2,
  gapWithoutQuickLaunch: 4,
  taskButtonGap: 3,
};

function metrics() {
  return METRICS;
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

function bandWidth(count, cells) {
  const shown = shownCount(count, cells);

  return cellsWidth(shown) + (shown < count ? METRICS.chevronWidth : 0);
}

// eslint-disable-next-line max-params -- QML and its tests pass the taskbar's geometry positionally
function layout(width, contentX, lead, count, cells, dock) {
  if (count === 0) {
    return {
      quickLaunchGripX: -1, cellsX: -1, shown: 0, firstShown: 0, chevronX: -1, taskGripX: -1,
      tasksX: contentX + METRICS.gapWithoutQuickLaunch, tasksEnd: width,
    };
  }
  const shown = shownCount(count, cells);
  const chevron = shown < count;

  if (dock === "right") {
    const cellsX = width - cellsWidth(shown);
    const quickLaunchGripX = width - bandWidth(count, cells) - separatorWidth(METRICS.separatorLead);

    return {
      quickLaunchGripX: quickLaunchGripX, cellsX: cellsX, shown: shown, firstShown: count - shown,
      chevronX: chevron ? cellsX - METRICS.chevronWidth : -1,
      taskGripX: contentX, tasksX: contentX + separatorWidth(lead), tasksEnd: quickLaunchGripX,
    };
  }
  const cellsX = contentX + separatorWidth(lead);
  const taskGripX = cellsX + bandWidth(count, cells) + METRICS.gapBeforeTaskSeparator;

  return {
    quickLaunchGripX: contentX, cellsX: cellsX, shown: shown, firstShown: 0,
    chevronX: chevron ? cellsX + cellsWidth(shown) : -1,
    taskGripX: taskGripX, tasksX: taskGripX + separatorWidth(METRICS.separatorLead), tasksEnd: width,
  };
}

// The cells a band as wide as `space` shows: all when they fit, else as many as fit beside the chevron.
function cellsFitting(space, count) {
  if (space >= cellsWidth(count)) return -1;

  return Math.max(0, Math.min(count - 1, Math.round((space - METRICS.chevronWidth) / METRICS.cellWidth)));
}

// eslint-disable-next-line max-params -- as layout()
function quickLaunchGripReleased(gripX, width, contentX, lead, count, cells, dock) {
  if (gripX < width / 2) return { dock: "left", cells: cells };
  if (dock === "left") return { dock: "right", cells: cells };

  return { dock: "right", cells: cellsFitting(width - gripX - separatorWidth(METRICS.separatorLead), count) };
}

// eslint-disable-next-line max-params -- as layout()
function taskGripReleased(gripX, width, contentX, lead, count, cells, dock) {
  if (dock === "right") return { dock: dock, cells: cells };
  const cellsX = contentX + separatorWidth(lead);

  return { dock: dock, cells: cellsFitting(gripX - METRICS.gapBeforeTaskSeparator - cellsX, count) };
}

function hiddenLaunchers(count, cells, dock) {
  const hiddenCount = count - shownCount(count, cells);
  const first = dock === "right" ? 0 : count - hiddenCount;
  const hidden = [];

  for (let index = first; index < first + hiddenCount; index++) hidden.push(index);

  return hidden;
}
