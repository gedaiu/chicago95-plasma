.pragma library

// The originals' system menu greys out each item that does not apply to the window as it is.
function windowState(roles) {
  return {
    minimized: roles.IsMinimized === true,
    maximized: roles.IsMaximized === true,
    movable: roles.IsMovable === true,
    resizable: roles.IsResizable === true,
    minimizable: roles.IsMinimizable === true,
    maximizable: roles.IsMaximizable === true,
    closable: roles.IsClosable === true,
  };
}

function enabledItems(state) {
  const restored = !state.minimized && !state.maximized;

  return {
    restore: !restored,
    move: restored && state.movable,
    size: restored && state.resizable,
    minimize: !state.minimized && state.minimizable,
    maximize: !state.maximized && state.maximizable,
    close: state.closable,
  };
}
