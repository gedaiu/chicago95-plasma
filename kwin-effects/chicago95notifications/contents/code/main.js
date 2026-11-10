"use strict";

// Durations are fixed on purpose: the desktop runs with AnimationDurationFactor=0
// (instant, like the classic desktop), and animationTime() would scale these to nothing too.
const SLIDE_IN_MS = 340;
const SLIDE_OUT_MS = 220;
const RESTACK_MS = 240;
const EDGE_GAP = 24;

function isNotification(window) {
    return window.notification || window.criticalNotification;
}

function slideDistance(window) {
    const screenArea = (window.screen && window.screen.geometry) || effects.virtualScreenGeometry;
    const fromRightEdge = window.geometry.x + window.geometry.width / 2 > screenArea.x + screenArea.width / 2;
    const distance = window.geometry.width + EDGE_GAP;
    return fromRightEdge ? distance : -distance;
}

function cancelAll(window) {
    for (const name of ["slideInAnimation", "restackAnimation"]) {
        if (window[name]) {
            cancel(window[name]);
            delete window[name];
        }
    }
}

const notificationMotion = {
    onWindowAdded(window) {
        if (!isNotification(window) || !window.visible || effects.hasActiveFullScreenEffect) {
            return;
        }
        if (!effect.grab(window, Effect.WindowAddedGrabRole)) {
            return;
        }
        window.windowFrameGeometryChanged.connect(notificationMotion.onGeometryChanged);
        window.slideInAnimation = animate({
            window: window,
            duration: SLIDE_IN_MS,
            animations: [{
                type: Effect.Translation,
                from: { value1: slideDistance(window), value2: 0 },
                to: { value1: 0, value2: 0 },
                curve: QEasingCurve.OutBack
            }, {
                type: Effect.Opacity,
                from: 0.0,
                to: 1.0,
                curve: QEasingCurve.OutCubic
            }]
        });
    },

    onWindowClosed(window) {
        if (!isNotification(window) || !window.visible || window.skipsCloseAnimation || effects.hasActiveFullScreenEffect) {
            return;
        }
        if (!effect.grab(window, Effect.WindowClosedGrabRole)) {
            return;
        }
        cancelAll(window);
        animate({
            window: window,
            duration: SLIDE_OUT_MS,
            animations: [{
                type: Effect.Translation,
                from: { value1: 0, value2: 0 },
                to: { value1: slideDistance(window), value2: 0 },
                curve: QEasingCurve.InCubic
            }, {
                type: Effect.Opacity,
                from: 1.0,
                to: 0.0,
                curve: QEasingCurve.InQuad
            }]
        });
    },

    // The popup stack is re-laid out whenever one notification closes or grows;
    // glide each popup from where it was instead of jumping.
    onGeometryChanged(window, oldGeometry) {
        if (!window.visible || window.slideInAnimation) {
            return;
        }
        const deltaX = oldGeometry.x - window.geometry.x;
        const deltaY = oldGeometry.y - window.geometry.y;
        if (deltaX === 0 && deltaY === 0) {
            return;
        }
        if (window.restackAnimation) {
            cancel(window.restackAnimation);
        }
        window.restackAnimation = animate({
            window: window,
            duration: RESTACK_MS,
            animations: [{
                type: Effect.Translation,
                from: { value1: deltaX, value2: deltaY },
                to: { value1: 0, value2: 0 },
                curve: QEasingCurve.OutCubic
            }]
        });
    },

    onAnimationEnded(window, animation) {
        if (animation === window.slideInAnimation) {
            delete window.slideInAnimation;
        } else if (animation === window.restackAnimation) {
            delete window.restackAnimation;
        }
    },

    init() {
        effects.windowAdded.connect(notificationMotion.onWindowAdded);
        effects.windowClosed.connect(notificationMotion.onWindowClosed);
        effect.animationEnded.connect(notificationMotion.onAnimationEnded);
    }
};

notificationMotion.init();
