// Builds the Chicago95 taskbar. Run once in the Plasma scripting console
// (System Settings has no entry for it; use `plasma-interactiveconsole`, or
// pass this file's text to org.kde.PlasmaShell.evaluateScript over D-Bus).
// Remove the stock panel first, or this adds a second one.

const panel = new Panel();
panel.location = "bottom";
panel.height = 28;
panel.floating = false;
panel.hiding = "none";
panel.lengthMode = "fill";

panel.addWidget("org.chicago95.start");
panel.addWidget("org.chicago95.grip");

const quicklaunch = panel.addWidget("org.kde.plasma.quicklaunch");
quicklaunch.currentConfigGroup = ["General"];
quicklaunch.writeConfig("launcherUrls", [
    "file://" + userDataPath("applications") + "/chicago95-showdesktop.desktop",
    "applications:firefox.desktop",
    "applications:thunar.desktop",
    "applications:org.kde.konsole.desktop",
]);
quicklaunch.writeConfig("showLauncherNames", false);
quicklaunch.writeConfig("maxSectionCount", 1);

panel.addWidget("org.chicago95.grip");

const tasks = panel.addWidget("org.kde.plasma.taskmanager");
tasks.currentConfigGroup = ["General"];
tasks.writeConfig("iconSpacing", 2);
tasks.writeConfig("maxTextLines", 1);
tasks.writeConfig("groupingStrategy", 0);
tasks.writeConfig("showToolTips", true);
tasks.writeConfig("fill", true);

panel.addWidget("org.kde.plasma.marginsseparator");
panel.addWidget("org.chicago95.trayframe");
panel.addWidget("org.kde.plasma.systemtray");

const clock = panel.addWidget("org.kde.plasma.digitalclock");
clock.currentConfigGroup = ["Appearance"];
clock.writeConfig("showDate", false);
clock.writeConfig("showSeconds", 0);
clock.writeConfig("autoFontAndSize", false);
clock.writeConfig("fontFamily", "MS W98 UI");
clock.writeConfig("fontSize", 9);
clock.writeConfig("fontWeight", 400);

const spacer = panel.addWidget("org.kde.plasma.panelspacer");
spacer.currentConfigGroup = ["General"];
spacer.writeConfig("expanding", false);
spacer.writeConfig("length", 6);

panel.reloadConfig();
