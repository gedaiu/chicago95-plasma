"use strict";

function moveToTaskbar(window) {
  const minimized = window.minimized;
  const running = window.aeroTaskbarMotion;
  if (running && redirect(running, minimized === window.aeroMovingToTaskbar ? Effect.Forward : Effect.Backward)) {
    return;
  }
  const icon = window.iconGeometry;
  if (!icon.width || !icon.height || effects.hasActiveFullScreenEffect) return;

  const frame = window.geometry;
  const full = { value1: frame.width, value2: frame.height };
  const small = { value1: icon.width, value2: icon.height };
  const offset = {
    value1: icon.x - frame.x + (icon.width - frame.width) / 2,
    value2: icon.y - frame.y + (icon.height - frame.height) / 2,
  };
  const origin = { value1: 0, value2: 0 };
  function track(type, shown, hidden) {
    return { type, from: minimized ? shown : hidden, to: minimized ? hidden : shown };
  }

  window.aeroMovingToTaskbar = minimized;
  window.aeroTaskbarMotion = animate({
    window,
    duration: animationTime(minimized ? 285 : 260),
    curve: minimized ? QEasingCurve.Linear : QEasingCurve.InCubic,
    keepAlive: false,
    animations: [
      track(Effect.Size, full, small),
      track(Effect.Translation, origin, offset),
      track(Effect.Opacity, 1, 0),
    ],
  });
}

function watchWindow(window) {
  window.minimizedChanged.connect(() => moveToTaskbar(window));
}

effect.animationEnded.connect((window, id) => {
  if (window.aeroTaskbarMotion?.includes(id)) delete window.aeroTaskbarMotion;
});
effects.windowAdded.connect(watchWindow);
effects.stackingOrder.forEach(watchWindow);
