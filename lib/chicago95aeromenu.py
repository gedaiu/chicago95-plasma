"""Two-column Aero launcher, sized from the 96 DPI all-programs reference."""

import ctypes
import functools

from PySide6.QtCore import QAbstractListModel, QPoint, QRectF, QSignalBlocker, QSize, Qt, QTimer
from PySide6.QtDBus import QDBusConnection
from PySide6.QtGui import QColor, QGuiApplication, QIcon, QPainter, QPainterPath, QPixmap, QRegion
from PySide6.QtWidgets import (
    QFrame,
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
    def __init__(self, apps, launch, icon, commands, user, picture=None):
        super().__init__(None, Qt.Window | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setWindowTitle("chicago95-startmenu-root")
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(411, 498)
        self.apps = sorted(apps, key=lambda entry: entry["name"].casefold())
        self.launch = launch
        self.all_programs = False
        frame = QFrame(self)
        frame.setObjectName("glass")
        frame.setGeometry(0, 23, 411, 475)
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
        self.list.activated.connect(self.open_item)
        programs.addWidget(self.list)
        self.toggle = QPushButton("▸   All Programs")
        self.toggle.clicked.connect(self.toggle_programs)
        programs.addWidget(self.toggle)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search programs and files")
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
            ("Computer", "my_computer"),
            ("Control Panel", "control_panel"),
            ("Devices and Printers", "printers"),
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
        for label, key in [("Log off", "log_off"), ("Lock", "lock"), ("Restart", "restart")]:
            if key in commands:
                options.addAction(label, functools.partial(self.run, commands[key]))
        arrow.clicked.connect(
            lambda: options.popup(
                arrow.mapToGlobal(QPoint(arrow.width(), arrow.height() - options.sizeHint().height()))
            )
        )
        avatar = QLabel(self)
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

    def showEvent(self, event):
        super().showEvent(event)
        if QGuiApplication.platformName() in ("wayland", "xcb"):
            enable = blur_behind_function()
            if enable is not None and self.windowHandle() is not None:
                from shiboken6 import getCppPointer

                outline = QPainterPath()
                outline.addRoundedRect(QRectF(self.findChild(QFrame, "glass").geometry()), 6, 6)
                region = QRegion(outline.toFillPolygon().toPolygon())
                enable(getCppPointer(self.windowHandle())[0], True, getCppPointer(region)[0])
        QDBusConnection.sessionBus().registerService("org.chicago95.StartMenuOpen")

    def hideEvent(self, event):
        QDBusConnection.sessionBus().unregisterService("org.chicago95.StartMenuOpen")
        super().hideEvent(event)

    def toggle_programs(self):
        self.all_programs = not self.all_programs
        with QSignalBlocker(self.search):
            self.search.clear()
        self.populate()

    def populate(self):
        query = self.search.text().casefold().strip()
        expanded = self.all_programs or bool(query)
        self.toggle.setText("◂   Back" if self.all_programs else "▸   All Programs")
        entries = self.apps if expanded else self.apps[:10]
        if query:
            entries = [app for app in entries if query in app["name"].casefold()]
        side = 16 if expanded else 32
        self.list.setIconSize(QSize(side, side))
        self.model.show_entries(entries, max(side, self.list.fontMetrics().height()) + 3)
        self.list.setCurrentIndex(self.model.index(0))
        self.list.scrollToTop()

    def open_item(self, index):
        if index.isValid() and self.isVisible():
            self.run(index.data(Qt.UserRole))

    def open_first(self):
        index = self.list.currentIndex()
        if index.isValid():
            self.run(index.data(Qt.UserRole))

    def run(self, target):
        self.hide()
        self.launch(target)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.hide()
        else:
            super().keyPressEvent(event)
