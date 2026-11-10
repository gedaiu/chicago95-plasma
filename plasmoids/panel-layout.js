// Builds the Chicago95 taskbar. Run once in the Plasma scripting console
// (System Settings has no entry for it; use `plasma-interactiveconsole`, or
// pass this file's text to org.kde.PlasmaShell.evaluateScript over D-Bus).
// Remove the stock panel first, or this adds a second one.

// The look's taskbar; Setup sets it: 1995 has no Quick Launch and narrower task buttons.
const look = "1995";

const panel = new Panel();
panel.location = "bottom";
panel.height = 28;
panel.floating = false;
panel.hiding = "none";
panel.lengthMode = "fill";

panel.addWidget("org.chicago95.start");
// Start, then the Quick Launch (from 1998 on) and the windows' buttons, all drawn by org.chicago95.tasks.
const tasks = panel.addWidget("org.chicago95.tasks");
tasks.currentConfigGroup = ["General"];
tasks.writeConfig("look", look);
tasks.writeConfig("maxButtonWidth", look === "1995" ? 95 : 160);
tasks.writeConfig("launchers", look === "1995" ? [] : [
    "file://" + userDataPath("applications") + "/chicago95-showdesktop.desktop",
    "applications:firefox.desktop",
    "applications:thunar.desktop",
    "applications:org.kde.konsole.desktop",
]);

// The tray: org.chicago95.trayframe draws the sunken box and places the icons of Plasma's tray, which
// follows it; then the clock, at the box's right end.
const trayframe = panel.addWidget("org.chicago95.trayframe");
trayframe.currentConfigGroup = ["General"];
trayframe.writeConfig("look", look);
panel.addWidget("org.kde.plasma.systemtray");
const clock = panel.addWidget("org.chicago95.clock");
clock.currentConfigGroup = ["General"];
clock.writeConfig("look", look);

panel.reloadConfig();
