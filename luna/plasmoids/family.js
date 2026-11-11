.pragma library

function isLuna(taskbarStyle) {
  return taskbarStyle === "luna";
}

function uiFontFamily(taskbarStyle) {
  return isLuna(taskbarStyle) ? "Tahoma" : "MS W98 UI";
}
