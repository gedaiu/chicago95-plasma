"use strict";

// In the compositor, so wallpaper and panels grey too; set() holds the grey until Cancel.
const FADE_MS = 2000;

// "Log Off Windows", or the branded system's name ("Log Off Fedora Linux").
function isShutdownDialog(window) {
  const caption = String(window.caption);

  return (
    (caption === "Turn off computer" || caption.startsWith("Log Off ")) &&
    String(window.windowClass).split(" ").includes("chicago95-shutdown")
  );
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
    this.protectBackdrop(window);
    // Wayland can announce a window before its final title or visibility arrives.
    if (window.captionChanged) window.captionChanged.connect(() => this.shown(window));

    if (window.visibleChanged) {
      window.visibleChanged.connect(() => (window.visible ? this.shown(window) : this.removed(window)));
    }

    this.shown(window);
  }

  protectBackdrop(window) {
    if (
      window.caption !== "Chicago95 shutdown backdrop" ||
      !String(window.windowClass).split(" ").includes("chicago95-shutdown")
    )
      return;
    // Grabbed before scale/fade effects animate it: KWin ignores a role that arrives late.
    effect.grab(window, Effect.WindowAddedGrabRole);
    effect.grab(window, Effect.WindowClosedGrabRole);
  }

  shown(window) {
    this.protectBackdrop(window);
    if (!window.visible) return;

    if (isShutdownDialog(window)) {
      this.dialogs.add(window);
      effects.stackingOrder.forEach((background) => this.fade(background));

      return;
    }

    if (this.dialogs.size) this.fade(window);
  }

  fade(window) {
    if (!window.visible || isShutdownDialog(window) || window.chicago95ShutdownFade) return;
    window.chicago95ShutdownFade = set({
      window: window,
      duration: animationTime(FADE_MS),
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
