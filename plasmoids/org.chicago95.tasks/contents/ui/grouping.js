.pragma library

// Windows 7's "Group similar taskbar buttons": always combine a program's windows into one button, combine them when
// the taskbar is full, or never. "auto" (and unset) follows the taskbar style: Windows 7's superbar always combines,
// the older taskbars never did.
const MODES = ["always", "full", "never"];

function mode(setting, taskbarStyle) {
  if (MODES.indexOf(setting) >= 0)
    return setting;
  return taskbarStyle === "aero" ? "always" : "never";
}

// Plasma's TasksModel.groupingWindowTasksThreshold: how many windows may be open before a program's windows combine
// (-1: never). Combining when full waits until more windows are open than buttons fit, and lets at least one stand.
function threshold(groupingMode, fittingButtons) {
  if (groupingMode === "always")
    return 0;
  if (groupingMode === "full")
    return Math.max(1, fittingButtons);
  return -1;
}

// A click on a combined button cycles its windows, as Ctrl+click does in Windows 7 (its plain click shows their
// thumbnails, which Plasma's tooltip shows under the pointer): the one after the focused window, or the first.
function nextWindow(focused) {
  const current = focused.indexOf(true);
  return current < 0 ? 0 : (current + 1) % focused.length;
}
