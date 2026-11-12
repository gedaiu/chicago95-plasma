"use strict";

// Run in the compositor: this includes wallpaper and panels on Wayland, and keeps
// the shutdown dialog itself in colour. set() holds the final saturation until Cancel.
function isShutdownDialog(window) {
  return window.caption === "Turn off computer" && String(window.windowClass).split(" ").includes("chicago95-shutdown");
}

class ShutdownEffect {
  constructor() {
    this.dialogs = new Set();
    effects.windowAdded.connect((window) => this.added(window));
    // Older KWin exposes these signals globally; newer versions use window visibility.
    if (effects.windowShown) effects.windowShown.connect((window) => this.shown(window));
    if (effects.windowHidden) effects.windowHidden.connect((window) => this.removed(window));
    effects.windowClosed.connect((window) => this.removed(window));
    effects.windowDeleted.connect((window) => this.removed(window));
    effects.stackingOrder.forEach((window) => this.added(window));
  }

  added(window) {
    if (window.visibleChanged) {
      window.visibleChanged.connect(() => window.visible ? this.shown(window) : this.removed(window));
    }
    this.shown(window);
  }

  shown(window) {
    if (isShutdownDialog(window)) {
      this.dialogs.add(window);
      effects.stackingOrder.forEach((background) => this.fade(background));
    } else if (this.dialogs.size) {
      this.fade(window);
    }
  }

  fade(window) {
    if (!window.visible || isShutdownDialog(window) || window.chicago95ShutdownFade) return;
    window.chicago95ShutdownFade = set({
      window: window,
      duration: animationTime(2000),
      curve: QEasingCurve.Linear,
      keepAlive: false,
      animations: [{ type: Effect.Saturation, from: 1.0, to: 0.0 }],
    });
  }

  removed(window) {
    this.dialogs.delete(window);
    if (this.dialogs.size) return;
    effects.stackingOrder.forEach((background) => {
      if (background.chicago95ShutdownFade) {
        cancel(background.chicago95ShutdownFade);
        delete background.chicago95ShutdownFade;
      }
    });
  }
}

new ShutdownEffect();
