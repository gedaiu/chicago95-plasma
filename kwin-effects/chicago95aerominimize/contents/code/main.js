"use strict";

const MINIMIZE_MS = 235;
const RESTORE_MS = 210;

function watchWindow(window) {
  window.minimizedChanged.connect(() => moveToTaskbar(window));
}

function moveToTaskbar(window) {
  const minimized = window.minimized;
  const running = window.aeroTaskbarMotion;

  if (running && resumeTaskbarMotion(window, running)) {
    return;
  }

  const icon = window.iconGeometry;
  if (!icon.width || !icon.height || effects.hasActiveFullScreenEffect) return;

  window.aeroMovingToTaskbar = minimized;
  window.aeroTaskbarMotion = playTaskbarAnimation(window, icon, minimized);
}

function resumeTaskbarMotion(window, running) {
  const direction = window.minimized === window.aeroMovingToTaskbar ? Effect.Forward : Effect.Backward;

  return redirect(running, direction);
}

function playTaskbarAnimation(window, icon, minimized) {
  return animate({
    window,
    duration: animationTime(minimized ? MINIMIZE_MS : RESTORE_MS),
    curve: minimized ? QEasingCurve.Linear : QEasingCurve.InCubic,
    keepAlive: false,
    animations: taskbarTracks(window.geometry, icon, minimized),
  });
}

function taskbarTracks(frame, icon, minimized) {
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

  return [
    track(Effect.Size, full, small),
    track(Effect.Translation, origin, offset),
    track(Effect.Opacity, 1, 0),
  ];
}

effect.animationEnded.connect((window, id) => {
  if (window.aeroTaskbarMotion?.includes(id)) delete window.aeroTaskbarMotion;
});
effects.windowAdded.connect(watchWindow);
effects.stackingOrder.forEach(watchWindow);
