"use strict";

// Setup turns each event on through kwinrc [Effect-chicago95zoom] Minimize and Maximize (setup/animations.conf).
const METRICS = { titleBarHeight: 18, durationMs: 260 };
const UNCHOSEN = false;

class ZoomEffect {
  constructor() {
    effect.configChanged.connect(() => this.loadConfig());
    effect.animationEnded.connect((window, animation) => this.continueZoom(window, animation));
    effects.windowAdded.connect((window) => this.manage(window));
    effects.stackingOrder.forEach((window) => this.manage(window));
    this.loadConfig();
  }

  loadConfig() {
    this.duration = animationTime(METRICS.durationMs);
    this.zoomsMinimize = effect.readConfig("Minimize", UNCHOSEN);
    this.zoomsMaximize = effect.readConfig("Maximize", UNCHOSEN);
  }

  manage(window) {
    window.minimizedChanged.connect(() => (window.minimized ? this.zoomToButton(window) : this.zoomFromButton(window)));
    window.windowMaximizedStateAboutToChange.connect((changing) => {
      changing.zoomFrom = Object.assign({}, changing.geometry);
    });
    window.windowMaximizedStateChanged.connect((changed) => this.zoomBetweenFrames(changed));
  }

  zoomToButton(window) {
    if (!this.zoomsMinimize || !hasButton(window) || effects.hasActiveFullScreenEffect) return;
    this.play(window, minimizeKeyframes(window.geometry, window.iconGeometry), QEasingCurve.InCubic);
  }

  zoomFromButton(window) {
    if (!this.zoomsMinimize || !hasButton(window) || effects.hasActiveFullScreenEffect) return;
    this.play(window, restoreKeyframes(window.geometry, window.iconGeometry), QEasingCurve.OutCubic);
  }

  zoomBetweenFrames(window) {
    if (!this.zoomsMaximize || !window.visible || !window.zoomFrom) return;
    this.play(window, maximizeKeyframes(window.zoomFrom, window.geometry), QEasingCurve.OutCubic);
  }

  play(window, keyframes, curve) {
    if (window.zoomAnimation) cancel(window.zoomAnimation);
    window.zoomSteps = segments(keyframes, window.geometry, this.duration);
    window.zoomCurve = curve;
    this.startStep(window);
  }

  // Each step holds its last frame until the next one starts, so the window never flashes back between them.
  startStep(window) {
    const step = window.zoomSteps.shift();

    window.zoomAnimation = animate({
      window: window,
      duration: step.duration,
      curve: window.zoomCurve,
      keepAlive: window.zoomSteps.length > 0,
      animations: [
        { type: Effect.Size, from: step.from.size, to: step.to.size },
        { type: Effect.Translation, from: step.from.translation, to: step.to.translation },
      ],
    });
  }

  continueZoom(window, animation) {
    if (!window.zoomSteps || firstAnimation(window.zoomAnimation) !== animation) return;
    const finished = window.zoomAnimation;

    if (window.zoomSteps.length === 0) {
      delete window.zoomAnimation;

      return;
    }

    this.startStep(window);
    cancel(finished);
  }
}

function metrics() {
  return METRICS;
}

function hasButton(window) {
  return window.iconGeometry.width > 0 && window.iconGeometry.height > 0;
}

function minimizeKeyframes(frame, button) {
  return [frame, titleBar(frame), button];
}

function restoreKeyframes(frame, button) {
  return [button, titleBar(frame), frame];
}

function maximizeKeyframes(oldFrame, newFrame) {
  return [oldFrame, titleBar(oldFrame), titleBar(newFrame), newFrame];
}

// Equal steps between keyframes, each as the Size and Translation KWin draws the window's frame with.
function segments(keyframes, frame, duration) {
  const steps = keyframes.length - 1;

  return keyframes.slice(1).map((target, index) => ({
    from: placement(keyframes[index], frame),
    to: placement(target, frame),
    duration: Math.round(duration / steps),
  }));
}

function firstAnimation(animation) {
  return Array.isArray(animation) ? animation[0] : animation;
}

function titleBar(rect) {
  return Object.assign({}, rect, { height: Math.min(METRICS.titleBarHeight, rect.height) });
}

// KWin scales a window about its centre, so the translation moves that centre onto the rect's.
function placement(rect, frame) {
  return {
    size: { value1: rect.width, value2: rect.height },
    translation: {
      value1: rect.x - frame.x - (frame.width - rect.width) / 2,
      value2: rect.y - frame.y - (frame.height - rect.height) / 2,
    },
  };
}

new ZoomEffect();
