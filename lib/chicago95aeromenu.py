"""Two-column Aero launcher, sized from the 96 DPI all-programs reference."""

import functools

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class AeroMenu(QWidget):
    def __init__(self, apps, launch, icon, commands, user, picture=None):
        super().__init__(None, Qt.Window | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setWindowTitle("chicago95-startmenu-root")
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(411, 498)
        self.apps = sorted(apps, key=lambda entry: entry["name"].casefold())
        self.launch = launch
        self.icon = icon
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
        self.list = QListWidget()
        self.list.itemClicked.connect(self.open_item)
        self.list.itemActivated.connect(self.open_item)
        programs.addWidget(self.list)
        self.toggle = QPushButton("▸   All Programs")
        self.toggle.clicked.connect(self.toggle_programs)
        programs.addWidget(self.toggle)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search programs")
        self.search.textChanged.connect(self.populate)
        self.search.returnPressed.connect(self.open_first)
        programs.addWidget(self.search)
        links = QVBoxLayout()
        links.setSpacing(1)
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
                button = QPushButton(title)
                button.clicked.connect(functools.partial(self.run, commands[command]))
                links.addWidget(button)
        links.addStretch()
        shutdown = QPushButton("Shut down")
        shutdown.setObjectName("shutdown")
        if "shut_down" in commands:
            shutdown.clicked.connect(functools.partial(self.run, commands["shut_down"]))
        links.addWidget(shutdown)
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
                stop:0 #739fbd, stop:0.37 #436989, stop:0.5 #344f68, stop:0.82 #263f56, stop:1 #6392b6); }
            #avatar { border: 2px solid #c1d6e3; border-radius: 5px; background: #5b859c; }
            #programs { background: white; border: 1px solid #8192a2; border-radius: 4px; }
            QListWidget { background: white; border: none; outline: none; }
            QListWidget::item:selected, QListWidget::item:hover { background: #def0fc; color: #172838; }
            QPushButton { text-align: left; padding: 6px; border: 1px solid transparent; color: white; }
            QPushButton:hover, QPushButton:focus, #shutdown { background: #597e9b; border: 1px solid #a2bece; }
            #programs QPushButton { color: #172838; border-top: 1px solid #d4dce3; }
            #programs QPushButton:hover { background: #def0fc; }
            QLineEdit { background: white; border: 1px solid #8497a8; padding: 3px; }
        """)
        self.populate()
        self.search.setFocus()

    def toggle_programs(self):
        self.all_programs = not self.all_programs
        self.search.clear()
        self.populate()

    def populate(self):
        query = self.search.text().casefold().strip()
        expanded = self.all_programs or bool(query)
        self.toggle.setText("◂   Back" if self.all_programs else "▸   All Programs")
        entries = self.apps if expanded else self.apps[:10]
        self.list.clear()
        self.list.setIconSize(QSize(16, 16) if expanded else QSize(32, 32))
        for app in entries:
            if query in app["name"].casefold():
                item = QListWidgetItem(self.icon(app["icon"]), app["name"], self.list)
                item.setData(Qt.UserRole, app)
        self.list.setCurrentRow(0)

    def open_item(self, item):
        if item is not None and self.isVisible():
            self.run(item.data(Qt.UserRole))

    def open_first(self):
        if self.list.currentItem():
            self.run(self.list.currentItem().data(Qt.UserRole))

    def run(self, target):
        self.hide()
        self.launch(target)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.hide()
        else:
            super().keyPressEvent(event)
