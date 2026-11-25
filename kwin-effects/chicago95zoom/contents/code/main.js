"use strict";

// kwinrc [Effect-chicago95zoom]: Minimize, Maximize (setup/animations.conf) and TitleBarHeight.
const METRICS = { titleBarHeight: 18, durationMs: 260 };
const CLASSIC_STRIP_INSET = 4;
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
    this.zoomsMaximize = effect.readConfig("Maximize", UNCHOSEN) && !effect.readConfig("InstantMaximize", false);
    this.titleBarHeight = effect.readConfig("TitleBarHeight", METRICS.titleBarHeight);
    this.lunaTitleStrip = effect.readConfig("LunaTitleStrip", false);
    this.classicStripSpeed = effect.readConfig("ClassicStripSpeed", 0);
    this.classicStripMaxMs = effect.readConfig("ClassicStripMaxMs", 0);
    const palette = effect.readConfig("ClassicStripPalette", "");
    this.classicStripPalette = /^(#[0-9a-f]{6})(,#[0-9a-f]{6})?$/i.test(palette)
      ? palette.split(",").map((color) => parseInt(color.slice(1), 16))
      : [];
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
    if (this.playTitleStrip(window, true)) return;
    this.play(
      window,
      minimizeKeyframes(window.geometry, window.iconGeometry, this.titleBarHeight),
      QEasingCurve.InCubic,
    );
  }

  zoomFromButton(window) {
    if (!this.zoomsMinimize || !hasButton(window) || effects.hasActiveFullScreenEffect) return;
    if (this.playTitleStrip(window, false)) return;
    this.play(
      window,
      restoreKeyframes(window.geometry, window.iconGeometry, this.titleBarHeight),
      QEasingCurve.OutCubic,
    );
  }

  zoomBetweenFrames(window) {
    if (!this.zoomsMaximize || !window.visible || !window.zoomFrom) return;
    // Keep one size and translation pair for the resize. Replacing the pair
    // mid-maximize can leave stale parts of the old frame on screen.
    this.play(window, [window.zoomFrom, window.geometry], QEasingCurve.OutCubic);
  }

  playTitleStrip(window, minimizing) {
    if ((!this.lunaTitleStrip && !this.classicStripSpeed) || !window.normalWindow) return false;
    const frame = window.geometry;
    const texture = window.expandedGeometry;
    const inset = this.classicStripSpeed ? CLASSIC_STRIP_INSET : 0;
    if (!texture?.width || !texture.height || frame.width <= 2 * inset || frame.height <= inset) return false;
    if (this.stripShader === undefined) {
      try {
        this.stripShader = effect.addFragmentShader(Effect.MapTexture, "title-strip.frag");
      } catch (error) {
        console.warn("Window title strip shader unavailable:", error);
        this.stripShader = 0;
      }
    }
    if (!this.stripShader) return false;
    if (window.zoomAnimation) cancel(window.zoomAnimation);
    delete window.zoomSteps;

    const { canvas, uniforms } = titleStripGeometry(
      frame, texture, window.iconGeometry, this.titleBarHeight, minimizing, inset,
    );
    const [start = -1, end = start] = inset && window.hasDecoration ? this.classicStripPalette : [];
    uniforms.classicStart = start;
    uniforms.classicEnd = end;
    const outputScale = window.screen?.devicePixelRatio || window.screen?.scale || 1;
    const duration = this.classicStripSpeed
      ? animationTime(classicStripDuration(uniforms, outputScale, this.classicStripSpeed, this.classicStripMaxMs))
      : this.duration;
    const transform = placement(canvas, frame);
    const uniformTracks = Object.entries(uniforms).map(([uniform, value]) => ({
      type: Effect.ShaderUniform,
      from: value,
      to: value,
      uniform,
    }));
    window.zoomAnimation = animate({
      window,
      duration,
      curve: QEasingCurve.Linear,
      fragmentShader: this.stripShader,
      keepAlive: false,
      animations: [
        { type: Effect.Size, from: transform.size, to: transform.size },
        { type: Effect.Translation, from: transform.translation, to: transform.translation },
      ].concat(uniformTracks),
    });
    return true;
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
    if (firstAnimation(window.zoomAnimation) !== animation) return;
    const finished = window.zoomAnimation;

    if (!window.zoomSteps?.length) {
      delete window.zoomAnimation;
      return;
    }

    this.startStep(window);
    cancel(finished);
  }
}

function titleStripGeometry(frame, texture, button, titleHeight, minimizing, inset = 0) {
  const height = Math.min(titleHeight, frame.height - inset, button.height);
  const taskY = button.y + (button.height - height) / 2;
  const left = Math.min(texture.x, button.x);
  const top = Math.min(texture.y, taskY);
  const right = Math.max(texture.x + texture.width, button.x + button.width);
  const bottom = Math.max(texture.y + texture.height, taskY + height);
  const sx = (right - left) / texture.width;
  const sy = (bottom - top) / texture.height;
  return {
    // KWin scales the expanded texture about the frame. Position the frame
    // so the decorated texture, including any shadow, covers the canvas.
    canvas: {
      x: left + (frame.x - texture.x) * sx,
      y: top + (frame.y - texture.y) * sy,
      width: frame.width * sx,
      height: frame.height * sy,
    },
    uniforms: {
      canvasX: left - texture.x,
      canvasY: top - texture.y,
      canvasWidth: right - left,
      canvasHeight: bottom - top,
      sourceWidth: texture.width,
      sourceHeight: texture.height,
      stripX: frame.x + inset - texture.x,
      stripY: frame.y + inset - texture.y,
      stripWidth: frame.width - 2 * inset,
      stripHeight: height,
      taskX: button.x - texture.x,
      taskY: taskY - texture.y,
      taskWidth: button.width,
      minimizing: minimizing ? 1 : 0,
    },
  };
}

function classicStripDuration({ stripX, stripY, taskX, taskY }, scale, speed, maximum = 0) {
  // The native speed is measured on the main axis of travel.
  const distance = Math.max(Math.abs(taskX - stripX), Math.abs(taskY - stripY));
  return Math.max(1, Math.min(maximum || Infinity, Math.round(distance * scale / speed)));
}

function metrics() {
  return METRICS;
}

function hasButton(window) {
  return window.iconGeometry.width > 0 && window.iconGeometry.height > 0;
}

function minimizeKeyframes(frame, button, titleBarHeight = METRICS.titleBarHeight) {
  return [frame, titleBar(frame, titleBarHeight), button];
}

function restoreKeyframes(frame, button, titleBarHeight = METRICS.titleBarHeight) {
  return [button, titleBar(frame, titleBarHeight), frame];
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

function titleBar(rect, titleBarHeight) {
  return Object.assign({}, rect, { height: Math.min(titleBarHeight, rect.height) });
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
