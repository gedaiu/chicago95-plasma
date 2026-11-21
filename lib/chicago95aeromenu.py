"""Two-column Aero launcher, sized from the 96 DPI all-programs reference."""

import ctypes
import functools
import json
import sys
from pathlib import Path

import chicago95animations
import chicago95recent
from PySide6.QtCore import (
    QAbstractListModel,
    QEasingCurve,
    QEvent,
    QPoint,
    QProcess,
    QRectF,
    QSettings,
    QSignalBlocker,
    QSize,
    Qt,
    QTimer,
    QVariantAnimation,
)
from PySide6.QtDBus import QDBusConnection, QDBusMessage, QDBusPendingCallWatcher, QDBusVariant
from PySide6.QtGui import QColor, QGuiApplication, QIcon, QPainter, QPainterPath, QPixmap, QRegion
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListView,
    QMenu,
    QPushButton,
    QScrollBar,
    QStyle,
    QStyleFactory,
    QStyleOptionSlider,
    QVBoxLayout,
    QWidget,
)


@functools.cache
def blur_behind_function():
    # KF6 takes Qt objects by pointer/reference. PySide owns both for the duration of the call.
    try:
        library = ctypes.CDLL("libKF6WindowSystem.so.6")
        enable = library._ZN14KWindowEffects16enableBlurBehindEP7QWindowbRK7QRegion
    except (OSError, AttributeError):
        return None
    enable.argtypes = (ctypes.c_void_p, ctypes.c_bool, ctypes.c_void_p)
    enable.restype = None
    return enable


class ProgramScrollBar(QScrollBar):
    def paintEvent(self, event):
        super().paintEvent(event)
        option = QStyleOptionSlider()
        self.initStyleOption(option)
        thumb = self.style().subControlRect(QStyle.CC_ScrollBar, option, QStyle.SC_ScrollBarSlider, self)
        if thumb.height() < 12:
            return
        center = thumb.center()
        painter = QPainter(self)
        for offset in (-3, 0, 3):
            y = center.y() + offset
            painter.setPen(QColor("#888888"))
            painter.drawLine(center.x() - 2, y, center.x() + 3, y)
            painter.setPen(QColor("#ffffff"))
            painter.drawLine(center.x() - 2, y + 1, center.x() + 3, y + 1)


class ProgramModel(QAbstractListModel):
    def __init__(self, view, icon):
        super().__init__(view)
        self.entries = []
        self.row_size = QSize()
        self.icon = icon
        self.icons = {}
        self.pending = {}
        blank = QPixmap(32, 32)
        blank.fill(Qt.transparent)
        self.placeholder = QIcon(blank)
        self.loader = QTimer(self)
        self.loader.setSingleShot(True)
        self.loader.timeout.connect(self.load_icon)

    def show_entries(self, entries, row_height):
        self.loader.stop()
        self.pending.clear()
        self.beginResetModel()
        self.entries = entries
        self.row_size = QSize(1, row_height)
        self.endResetModel()

    def rowCount(self, parent=None):
        return 0 if parent is not None and parent.isValid() else len(self.entries)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        app = self.entries[index.row()]
        if role == Qt.DisplayRole:
            return app["name"]
        if role in (Qt.ToolTipRole, Qt.AccessibleDescriptionRole):
            return app.get("file")
        if role == Qt.SizeHintRole:
            return self.row_size
        if role == Qt.UserRole:
            return app
        if role == Qt.DecorationRole:
            name = app["icon"]
            if name in self.icons:
                return self.icons[name]
            self.pending.setdefault(name, set()).add(index.row())
            if not self.loader.isActive():
                self.loader.start(0)
            return self.placeholder
        return None

    def load_icon(self):
        # Resolve only requested rows, yielding to input and paint between theme lookups.
        name = next(iter(self.pending))
        rows = self.pending.pop(name)
        self.icons[name] = self.icon(name)
        for row in rows:
            index = self.index(row)
            self.dataChanged.emit(index, index, [Qt.DecorationRole])
        if self.pending:
            self.loader.start(0)


class AeroMenu(QWidget):
    def __init__(
        self,
        apps,
        launch,
        icon,
        commands,
        user,
        picture=None,
        *,
        usage_path=None,
        folder_for=None,
        search_tool=None,
        recent_files=(),
        search_history=False,
        power_probes=None,
    ):
        super().__init__(None, Qt.Window | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setWindowTitle("chicago95-startmenu-root")
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(411, 498)
        self.apps = sorted(apps, key=lambda entry: entry["name"].casefold())
        self.usage = QSettings(str(usage_path), QSettings.IniFormat) if usage_path else None
        self.folder_for = folder_for
        self.folder_rows = {}
        self.groups = {}
        self.ungrouped = []
        for app in self.apps:
            if folder_for and app.get("categories"):
                self.groups.setdefault(folder_for(app), []).append(app)
            else:
                self.ungrouped.append(app)
        self.open_folders = set()
        self.search_tool = search_tool
        self.recent_files = recent_files
        self.search_history = search_history
        self.search_processes = set()
        self.search_delay = QTimer(self)
        self.search_delay.setSingleShot(True)
        self.search_delay.setInterval(150)
        self.search_delay.timeout.connect(self.find_files)
        self.surface = QWidget(self)
        self.surface.resize(self.size())
        self.opacity = QGraphicsOpacityEffect(self.surface)
        self.opacity.setEnabled(False)
        self.surface.setGraphicsEffect(self.opacity)
        self.opening = QVariantAnimation(self)
        self.opening.setStartValue(0.0)
        self.opening.setEndValue(1.0)
        self.opening.setEasingCurve(QEasingCurve.OutCubic)
        self.opening.valueChanged.connect(self.draw_opening)
        self.motion = "none"
        self.launch = launch
        self.all_programs = False
        frame = QFrame(self.surface)
        frame.setObjectName("glass")
        frame.setGeometry(0, 23, 411, 475)
        outline = QPainterPath()
        outline.addRoundedRect(QRectF(frame.geometry()), 6, 6)
        self.glass_region = QRegion(outline.toFillPolygon().toPolygon())
        columns = QHBoxLayout(frame)
        columns.setContentsMargins(7, 7, 6, 7)
        columns.setSpacing(5)
        left = QFrame()
        left.setObjectName("programs")
        left.setFixedWidth(252)
        columns.addWidget(left)
        programs = QVBoxLayout(left)
        programs.setContentsMargins(4, 4, 4, 8)
        self.list = QListView()
        self.model = ProgramModel(self.list, icon)
        self.list.setModel(self.model)
        self.list.setUniformItemSizes(True)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list.setTextElideMode(Qt.ElideRight)
        self.list.setWordWrap(False)
        self.list.setResizeMode(QListView.Adjust)
        scrollbar = ProgramScrollBar(Qt.Vertical)
        self.list.setVerticalScrollBar(scrollbar)
        scroll_style = QStyleFactory.create("Fusion")
        scroll_style.setParent(scrollbar)
        scrollbar.setStyle(scroll_style)
        self.list.clicked.connect(self.open_item)
        self.list.installEventFilter(self)
        programs.addWidget(self.list)
        self.toggle = QPushButton("▸   All Programs")
        self.toggle.clicked.connect(self.toggle_programs)
        programs.addWidget(self.toggle)
        self.search = QLineEdit()
        self.search.installEventFilter(self)
        self.search.setPlaceholderText("Search programs and files")
        self.search.addAction(
            QIcon.fromTheme("edit-find", self.style().standardIcon(QStyle.SP_FileDialogContentsView)),
            QLineEdit.TrailingPosition,
        )
        self.search.textChanged.connect(self.populate)
        self.search.returnPressed.connect(self.open_first)
        programs.addWidget(self.search)
        links = QVBoxLayout()
        links.setSpacing(1)
        links.setContentsMargins(7, 0, 6, 0)
        columns.addLayout(links)
        links.addSpacing(25)
        places = [
            (user, "home"),
            ("Documents", "my_documents"),
            ("Pictures", "my_pictures"),
            ("Music", "my_music"),
            ("Games", "games"),
            ("Computer", "my_computer"),
            ("Control Panel", "control_panel"),
            ("Devices and Printers", "printers"),
            ("Default Programs", "defaults"),
            ("Help and Support", "help"),
        ]
        for title, command in places:
            if command in commands:
                if command in ("my_computer", "control_panel"):
                    separator = QFrame()
                    separator.setObjectName("linkSeparator")
                    separator.setFixedHeight(2)
                    links.addWidget(separator)
                button = QPushButton(title)
                button.clicked.connect(functools.partial(self.run, commands[command]))
                links.addWidget(button)
        links.addStretch()
        power = QWidget(frame)
        power.setObjectName("power")
        power.setGeometry(267, frame.height() - 42, 94, 22)
        shutdown = QPushButton("Shut down", power)
        shutdown.setObjectName("shutdown")
        shutdown.setGeometry(0, 0, 72, 22)
        if "shut_down" in commands:
            shutdown.clicked.connect(functools.partial(self.run, commands["shut_down"]))
        arrow = QPushButton("▸", power)
        arrow.setObjectName("powerArrow")
        arrow.setGeometry(71, 0, 23, 22)
        arrow.setAccessibleName("Shut-down options")
        options = QMenu(self)
        for label, key in [
            ("Switch user", "switch_user"),
            ("Log off", "log_off"),
            ("Lock", "lock"),
            ("Restart", "restart"),
            ("Sleep", "sleep"),
            ("Hibernate", "hibernate"),
        ]:
            if key in commands:
                if key in ("restart", "sleep") and options.actions():
                    options.addSeparator()
                action = options.addAction(label, functools.partial(self.run, commands[key]))
                if power_probes and key in power_probes:
                    self.check_capability(action, *power_probes[key])
        arrow.clicked.connect(
            lambda: options.popup(
                arrow.mapToGlobal(QPoint(arrow.width(), arrow.height() - options.sizeHint().height()))
            )
        )
        avatar = QLabel(self.surface)
        avatar.setObjectName("avatar")
        avatar.setGeometry(307, 0, 58, 58)
        avatar.setAlignment(Qt.AlignCenter)
        portrait = QIcon(str(picture)) if picture else QIcon()
        if portrait.isNull():
            portrait = icon("user-identity")
        avatar.setPixmap(portrait.pixmap(48, 48))
        self.setStyleSheet("""
            * { font-family: "Segoe UI", "Noto Sans"; font-size: 12px; color: #172838; }
            #glass { border: 1px solid #263b50; border-radius: 6px;
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                stop:0 rgba(130,163,184,185), stop:0.37 rgba(31,51,68,185), stop:0.5 rgba(15,24,32,185),
                stop:0.82 rgba(13,22,29,185), stop:1 rgba(110,141,159,185)); }
            #avatar { border: 2px solid #c1d6e3; border-radius: 5px; background: #5b859c; }
            #programs { background: white; border: 1px solid #8192a2; border-radius: 4px; }
            QListView { background: white; border: none; outline: none; }
            QListView::item:selected, QListView::item:hover { background: #def0fc; color: #172838; }
            QPushButton { text-align: left; padding: 6px; border: 1px solid transparent; color: white; }
            QPushButton:hover, QPushButton:focus { background: #597e9b; border: 1px solid #a2bece; }
            #linkSeparator { border: none; border-top: 1px solid rgba(0,0,0,45);
                border-bottom: 1px solid rgba(255,255,255,35); }
            #shutdown, #powerArrow { text-align: center; color: white; padding: 0; border: 1px solid #294d69;
                border-radius: 2px; background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                stop:0 rgba(255,255,255,180), stop:0.07 rgba(255,255,255,130),
                stop:0.47 rgba(255,255,255,28), stop:0.5 rgba(0,0,0,28),
                stop:0.92 rgba(255,255,255,6), stop:1 rgba(255,255,255,95)); }
            #shutdown:hover, #powerArrow:hover, #shutdown:focus, #powerArrow:focus { border-color: #b1dff9; }
            #shutdown:pressed, #powerArrow:pressed { background: #345773; }
            QScrollBar:vertical { width: 16px; }
            #programs QPushButton { color: #172838; border-top: 1px solid #d4dce3; }
            #programs QPushButton:hover { background: #def0fc; }
            QLineEdit { background: white; border: 1px solid #8497a8; padding: 3px; }
        """)
        self.populate()
        self.search.setFocus()

    def check_capability(self, action, service, path, interface, method, arguments):
        action.setVisible(False)
        request = QDBusMessage.createMethodCall(service, path, interface, method)
        request.setArguments(arguments)
        watcher = QDBusPendingCallWatcher(QDBusConnection.systemBus().asyncCall(request, 1500), self)

        def finished():
            reply = watcher.reply()
            if reply.type() == QDBusMessage.ReplyMessage and reply.arguments():
                value = reply.arguments()[0]
                if isinstance(value, QDBusVariant):
                    value = value.variant()
                action.setVisible(value is True or value in ("yes", "challenge"))
            watcher.deleteLater()

        watcher.finished.connect(finished)

    def showEvent(self, event):
        super().showEvent(event)
        if self.usage and not self.all_programs and not self.search.text():
            self.populate()
        self.motion, duration = chicago95animations.own_animation(
            chicago95animations.live_state(), "ANIM_MENUS", "fade", 120
        )
        if self.motion in ("slide", "fade", "both") and duration > 0:
            self.opening.setDuration(duration)
            self.draw_opening(0.0)
            self.opening.start()
        else:
            self.draw_opening(1.0)
        QDBusConnection.sessionBus().registerService("org.chicago95.StartMenuOpen")

    def draw_opening(self, progress):
        # Keep KWin's root window anchored. Move the contents up from the panel inside that window.
        sliding = self.motion in ("slide", "both")
        offset = round(self.height() * (1 - progress)) if sliding else 0
        self.surface.move(0, offset)
        fading = self.motion in ("fade", "both") and progress < 1
        self.opacity.setEnabled(fading)
        if fading:
            self.opacity.setOpacity(progress)
        if QGuiApplication.platformName() in ("wayland", "xcb") and self.windowHandle():
            enable = blur_behind_function()
            if enable is not None:
                from shiboken6 import getCppPointer

                region = self.glass_region.translated(0, offset).intersected(QRegion(self.rect()))
                enable(
                    getCppPointer(self.windowHandle())[0],
                    progress > 0 and not region.isEmpty(),
                    getCppPointer(region)[0],
                )

    def hideEvent(self, event):
        self.stop_search()
        self.opening.stop()
        self.surface.move(0, 0)
        self.opacity.setEnabled(False)
        QDBusConnection.sessionBus().unregisterService("org.chicago95.StartMenuOpen")
        super().hideEvent(event)

    def toggle_programs(self):
        if self.opening.state() != QVariantAnimation.Stopped:
            self.opening.stop()
            self.draw_opening(1.0)
        self.all_programs = not self.all_programs
        with QSignalBlocker(self.search):
            self.search.clear()
        self.populate()
        (self.list if self.all_programs else self.search).setFocus()

    def populate(self):
        query = self.search.text().casefold().strip()
        expanded = self.all_programs or bool(query)
        self.toggle.setText("◂   Back" if self.all_programs else "▸   All Programs")
        self.stop_search()
        self.folder_rows.clear()
        if query:
            entries = [app for app in self.apps if query in app["name"].casefold()]
            entries.extend(self.file_entry(path) for path in self.recent_files if query in Path(path).name.casefold())
            if self.search_tool or self.search_history:
                self.search_delay.start()
        elif self.all_programs:
            entries = list(self.ungrouped)
            for folder, children in sorted(self.groups.items()):
                self.folder_rows[folder] = len(entries)
                entries.append(
                    {
                        "name": folder,
                        "folder": folder,
                        "icon": "folder-open" if folder in self.open_folders else "folder",
                    }
                )
                if folder in self.open_folders:
                    entries.extend(children)
        else:
            entries = self.apps
            if self.usage:
                entries = sorted(entries, key=lambda app: -self.usage.value(app["path"], 0, type=int))
            entries = entries[:10]
        side = 16 if expanded else 32
        self.list.setIconSize(QSize(side, side))
        self.model.show_entries(entries, max(side, self.list.fontMetrics().height()) + 3)
        self.list.setCurrentIndex(self.model.index(0))
        self.list.scrollToTop()

    def stop_search(self):
        self.search_delay.stop()
        while self.search_processes:
            self.search_processes.pop().kill()

    @staticmethod
    def file_entry(path):
        return {"name": Path(path).name, "file": str(path), "icon": "text-x-generic"}

    def find_files(self):
        query = self.search.text().strip()
        if self.search_history:
            self.start_search(sys.executable, [chicago95recent.__file__, query], json.loads)
        if self.search_tool:
            self.start_search(self.search_tool, ["--limit", "30", "--", "filename:" + query], str.splitlines)

    def start_search(self, program, arguments, parse):
        process = QProcess(self)
        self.search_processes.add(process)

        def finished():
            if process in self.search_processes:
                self.search_processes.remove(process)
                known = {entry.get("file") for entry in self.model.entries}
                files = []
                output = bytes(process.readAllStandardOutput()).decode(errors="replace")
                paths = parse(output) if process.exitCode() == 0 and output else []
                for path in paths:
                    if Path(path).is_absolute() and path not in known and Path(path).exists():
                        files.append(self.file_entry(path))
                        known.add(path)
                if files:
                    first = len(self.model.entries)
                    self.model.beginInsertRows(self.list.rootIndex(), first, first + len(files) - 1)
                    self.model.entries.extend(files)
                    self.model.endInsertRows()
                    if first == 0:
                        self.list.setCurrentIndex(self.model.index(0))
            process.deleteLater()

        def failed(error):
            if error == QProcess.FailedToStart:
                self.search_processes.discard(process)
                process.deleteLater()

        process.errorOccurred.connect(failed)
        process.finished.connect(finished)
        process.start(program, arguments)

    def eventFilter(self, watched, event):
        if event.type() == QEvent.KeyPress and event.modifiers() in (Qt.NoModifier, Qt.KeypadModifier):
            key = event.key()
            if watched is self.search and key in (Qt.Key_Up, Qt.Key_Down):
                count = self.model.rowCount()
                if count:
                    step = 1 if key == Qt.Key_Down else -1
                    row = max(0, min(count - 1, self.list.currentIndex().row() + step))
                    self.list.setCurrentIndex(self.model.index(row))
                return True
            if watched is self.list:
                if key in (Qt.Key_Return, Qt.Key_Enter):
                    self.open_first()
                    return True
                if self.folder_rows and key in (Qt.Key_Left, Qt.Key_Right):
                    self.navigate_folder(key)
                    return True
        return super().eventFilter(watched, event)

    def navigate_folder(self, key):
        current = self.list.currentIndex()
        if not current.isValid():
            return
        entry = current.data(Qt.UserRole)
        if folder := entry.get("folder"):
            expanded = folder in self.open_folders
            if key == Qt.Key_Right and expanded:
                self.list.setCurrentIndex(self.model.index(current.row() + 1))
            elif key == Qt.Key_Right or expanded:
                self.run(entry)
        elif key == Qt.Key_Left and self.folder_for and entry.get("categories"):
            self.list.setCurrentIndex(self.model.index(self.folder_rows[self.folder_for(entry)]))

    def open_item(self, index):
        if index.isValid() and self.isVisible():
            self.run(index.data(Qt.UserRole))

    def open_first(self):
        index = self.list.currentIndex()
        if index.isValid():
            self.run(index.data(Qt.UserRole))

    def run(self, target):
        if isinstance(target, dict):
            if group := target.get("open_group"):
                self.all_programs = True
                self.open_folders.add(group)
                with QSignalBlocker(self.search):
                    self.search.clear()
                self.populate()
                if group in self.folder_rows:
                    index = self.model.index(self.folder_rows[group])
                    self.list.setCurrentIndex(index)
                    self.list.scrollTo(index, QListView.PositionAtTop)
                self.list.setFocus()
                return
            if folder := target.get("folder"):
                self.open_folders.symmetric_difference_update({folder})
                self.populate()
                self.list.setCurrentIndex(self.model.index(self.folder_rows[folder]))
                return
            if "file" in target:
                target = ["xdg-open", target["file"]]
            elif self.usage and "path" in target:
                key = target["path"]
                self.usage.setValue(key, self.usage.value(key, 0, type=int) + 1)
        self.hide()
        self.launch(target)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.hide()
        else:
            super().keyPressEvent(event)
