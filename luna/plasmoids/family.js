.pragma library

function uiFontFamily(taskbarStyle) {
  return isLuna(taskbarStyle) ? "Tahoma" : "MS W98 UI";
}

function isLuna(taskbarStyle) {
  return taskbarStyle === "luna";
}
