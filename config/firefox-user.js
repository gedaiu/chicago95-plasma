// Chicago95: make Firefox take selection, widget and form colours from the GTK theme
// instead of its own built-in palette, so page text selection is navy on white.
user_pref("browser.display.use_system_colors", true);
user_pref("widget.non-native-theme.use-theme-accent", true);
user_pref("widget.gtk.theme-scrollbar-colors.enabled", true);
user_pref("widget.gtk.overlay-scrollbars.enabled", false);
user_pref("widget.gtk.non-native-titlebar-buttons.enabled", false);
user_pref("browser.tabs.inTitlebar", 0);
user_pref("layout.css.prefers-color-scheme.content-override", 1);
user_pref("browser.theme.content-theme", 1);
user_pref("browser.theme.toolbar-theme", 1);
