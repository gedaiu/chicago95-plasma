.pragma library

const LOOK_1995_BUTTON_WIDTH = 95;
const LATER_LOOKS_BUTTON_WIDTH = 160;
const LUNA_BUTTON_WIDTH = 160;

function maxButtonWidth(configuredWidth, look) {
  if (configuredWidth > 0) return configuredWidth;

  return look === "1995" ? LOOK_1995_BUTTON_WIDTH : LATER_LOOKS_BUTTON_WIDTH;
}

const SUPERBAR_BUTTON_WIDTH = 60; // Windows 7's buttons are icons only: always one TASKITEM wide

function styledButtonWidth(lookWidth, configuredWidth, taskbarStyle, referenceDpi) {
  if (taskbarStyle === "aero") return SUPERBAR_BUTTON_WIDTH;
  if (!(configuredWidth > 0) && referenceDpi === 120) return 128; // 160 device pixels in the 120-DPI guests

  return taskbarStyle === "luna" && !(configuredWidth > 0) ? LUNA_BUTTON_WIDTH : lookWidth;
}
