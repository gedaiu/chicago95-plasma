// Builds the Chicago95 taskbar: run once in plasma-interactiveconsole, after removing the stock panel.

const panel = new Panel();

panel.location = "bottom";
panel.height = 28;
panel.floating = false;
panel.hiding = "none";
panel.lengthMode = "fill";

panel.addWidget("org.chicago95.start");

// The look's taskbar, set by Setup: 1995 has no Quick Launch and narrower task buttons.
const look = "1995";

// Start, then Quick Launch (1998 on) and the windows' buttons, all drawn by org.chicago95.tasks.
const tasks = panel.addWidget("org.chicago95.tasks");

tasks.currentConfigGroup = ["General"];
tasks.writeConfig("look", look);

// The tray: trayframe draws the sunken box around Plasma's tray icons, then the clock ends it.
const trayframe = panel.addWidget("org.chicago95.trayframe");

trayframe.currentConfigGroup = ["General"];
trayframe.writeConfig("look", look);
panel.addWidget("org.kde.plasma.systemtray");

const clock = panel.addWidget("org.chicago95.clock");

clock.currentConfigGroup = ["General"];
clock.writeConfig("look", look);

panel.reloadConfig();
