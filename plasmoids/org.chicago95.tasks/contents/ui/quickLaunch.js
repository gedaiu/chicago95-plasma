.pragma library

// Quick Launch shows per Setup's "yes" or "no", or for "auto" as the look's own does (1998 on), like quick_launch_shown.
function shown(setting, look) {
  if (setting === "yes") return true;
  if (setting === "no") return false;

  return look !== "1995";
}
