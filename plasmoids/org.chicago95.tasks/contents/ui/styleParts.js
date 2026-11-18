.pragma library

// The taskbar parts each style draws itself; any other part is the classic one. Luna draws them all.
const OWN_PARTS = {
  aero: ["TaskButton.qml", "QuickLaunchButton.qml"],
};

function path(taskbarStyle, part) {
  if (taskbarStyle === "luna") return "luna/" + part;

  return (OWN_PARTS[taskbarStyle] ?? []).includes(part) ? taskbarStyle + "/" + part : part;
}
