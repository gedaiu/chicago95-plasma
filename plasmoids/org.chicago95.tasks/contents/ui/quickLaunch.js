.pragma library

// Quick Launch shows per Setup's "yes" or "no", or for "auto" as the look's own does (1998 on), like quick_launch_shown.
function shown(setting, look) {
  if (setting === "yes") return true;
  if (setting === "no") return false;

  return look !== "1995";
}

// The launchers the task model shows: none while Setup's list has not loaded yet (Plasma hands over undefined
// right after a restart) or when Quick Launch is off.
function launchers(shown, configured) {
  return shown && loaded(configured) ? configured : [];
}

// Whether the model's launchers are worth saving: a list that has not loaded is never overwritten.
function launchersDiffer(saved, current) {
  return loaded(saved) && Array.from(saved).join() !== Array.from(current).join();
}

// Qt hands lists over as arrays or as sequence wrappers, never as undefined once they have loaded.
function loaded(list) {
  return list != null && typeof list.length === "number";
}
