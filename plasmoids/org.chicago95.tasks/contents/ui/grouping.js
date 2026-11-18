.pragma library

// Windows 7's "Group similar taskbar buttons"; "auto" follows the style: the superbar combines, older taskbars never did.
const MODES = ["always", "full", "never"];

function mode(setting, taskbarStyle) {
  if (MODES.indexOf(setting) >= 0) return setting;

  return taskbarStyle === "aero" ? "always" : "never";
}

// TasksModel.groupingWindowTasksThreshold (-1: never); "full" waits for more windows than fit, letting one stand.
function threshold(groupingMode, fittingButtons) {
  if (groupingMode === "always") return 0;
  if (groupingMode === "full") return Math.max(1, fittingButtons);

  return -1;
}

// A click cycles a combined button's windows, as Windows 7's Ctrl+click: the one after the focused window, or the first.
function nextWindow(focused) {
  const current = focused.findIndex((isFocused) => isFocused);

  return current < 0 ? 0 : (current + 1) % focused.length;
}
