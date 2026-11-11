.pragma library

const LOOK_1995_BUTTON_WIDTH = 95;
const LATER_LOOKS_BUTTON_WIDTH = 160;
const LUNA_BUTTON_WIDTH = 160;

function maxButtonWidth(configuredWidth, look) {
  if (configuredWidth > 0) return configuredWidth;

  return look === "1995" ? LOOK_1995_BUTTON_WIDTH : LATER_LOOKS_BUTTON_WIDTH;
}

function styledButtonWidth(lookWidth, configuredWidth, taskbarStyle) {
  return taskbarStyle === "luna" && !(configuredWidth > 0) ? LUNA_BUTTON_WIDTH : lookWidth;
}
