#!/usr/bin/env python3
"""Chicago95 graphical setup. Run from any directory in a desktop session."""

import argparse
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

from model import (
    COMPONENTS,
    DESKTOP_CAPTURES,
    FIELDS,
    LIGHT_FIELDS,
    OS_NAMES,
    ROOT,
    backend,
    defaults,
    linux_preferences,
    plan,
    validate,
)
from previews import render, sound_url
from PySide6.QtCore import QProcess, QProcessEnvironment, QSignalBlocker, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QFontDatabase, QIcon, QPainter, QPalette, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QSizePolicy,
    QStyle,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QWizard,
    QWizardPage,
)


class SelectionPage(QWizardPage):
    def __init__(self, title, complete):
        super().__init__()
        self.setTitle(title)
        self.complete = complete

    def isComplete(self):
        return self.complete()


def picture(width=344, height=212):
    label = QLabel()
    label.setAlignment(Qt.AlignCenter)
    label.setFixedSize(width, height)
    label.setObjectName("preview")
    label.setWordWrap(True)
    label.setFrameStyle(QLabel.Panel | QLabel.Sunken)
    label.setTextFormat(Qt.PlainText)
    return label


class SetupCaption(QFrame):
    def __init__(self, wizard):
        super().__init__(wizard)
        self.setObjectName("setupCaption")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(3, 2, 2, 2)
        layout.setSpacing(4)
        layout.addWidget(QLabel(wizard.windowTitle()), 1)
        close = QToolButton()
        close.setObjectName("captionClose")
        close.setAccessibleName("Close")
        close.setIcon(wizard.style().standardIcon(QStyle.SP_TitleBarCloseButton))
        close.setFixedSize(18, 17)
        close.clicked.connect(wizard.close)
        layout.addWidget(close)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.window().windowHandle():
            self.window().windowHandle().startSystemMove()
        else:
            super().mousePressEvent(event)


# The plain backend emits these headings as it enters each step (install.sh, ui_set_steps).
SETUP_STEPS = ("Collecting information about your computer", "Selecting components", "Copying files", "Finishing Setup")


class SetupWizard(QWizard):
    def __init__(self, program=None, dry_only=False):
        super().__init__()
        self.dry_only = dry_only
        self.program = str(program or ROOT / "install.sh")
        self.saved = Path.home() / ".config/chicago95/setup.conf"
        self.overrides = {}
        self.key = "look"
        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.MergedChannels)
        self.process.readyReadStandardOutput.connect(self.read_output)
        self.process.finished.connect(self.backend_finished)
        self.process.errorOccurred.connect(self.process_error)
        self.settings_dir = None
        self.player = None
        self.saver_process = QProcess(self)
        self.busy = False
        self.dry = False
        w, h, scale = backend.detect_screen(os.environ)
        self.machine = {
            "screen": f"{w}x{h}@{scale}",
            "explorer": "thunar" if shutil.which("thunar") else "dolphin",
            "cursor": "48" if float(scale) > 1 else "32",
            "task-button-width": "0",
            "branding": "distro",
            "font": "MS W98 UI",
        }
        config = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
        self.linux_defaults = linux_preferences(config)
        screen = QApplication.primaryScreen()
        if screen and QApplication.platformName() in ("wayland", "xcb"):
            size = screen.geometry().size()
            self.linux_defaults["screen"] = f"{size.width()}x{size.height()}@{screen.devicePixelRatio():g}"
        self.setWindowTitle("Chicago95 Setup")
        self.setWindowIcon(QIcon(str(ROOT / "data/desktop-icons/native/1995/computer.png")))
        self.setWizardStyle(QWizard.ModernStyle)
        self.setOption(QWizard.NoCancelButton)
        self.setButtonText(QWizard.BackButton, "< Back")
        self.setButtonText(QWizard.NextButton, "Next >")
        self.setOption(QWizard.IndependentPages)
        self.setButtonText(QWizard.FinishButton, "Close")
        self.resize(810, 496)
        self.setSizeGripEnabled(True)
        palette = self.palette()
        for role, colour in (
            (QPalette.Window, "#c0c0c0"),
            (QPalette.Button, "#c0c0c0"),
            (QPalette.Light, "#ffffff"),
            (QPalette.Midlight, "#dfdfdf"),
            (QPalette.Dark, "#808080"),
            (QPalette.Shadow, "#000000"),
            (QPalette.Highlight, "#000080"),
            (QPalette.HighlightedText, "#ffffff"),
            (QPalette.Base, "#ffffff"),
        ):
            palette.setColor(role, QColor(colour))
        for role in (QPalette.WindowText, QPalette.ButtonText, QPalette.Text):
            palette.setColor(role, Qt.black)
            palette.setColor(QPalette.Disabled, role, Qt.darkGray)
        self.setPalette(palette)
        for family in ("Chicago95 Windows 95", "MS Sans Serif", "MS W98 UI", "Liberation Sans"):
            if QFontDatabase.hasFamily(family):
                font = QFont(family)
                font.setPixelSize(11)
                self.setFont(font)
                break
        self.setPixmap(QWizard.LogoPixmap, QPixmap(str(ROOT / "installer/art/header.png")))
        self.add_bookend(False)
        self.add_components()
        self.add_customization()
        self.add_review()
        self.installed = False
        self.completion_id = self.add_bookend(True)
        self.currentIdChanged.connect(self.page_changed)

    def add_bookend(self, completion):
        welcome = QWizardPage()
        welcome.setObjectName("completionPage" if completion else "welcomePage")
        welcome.setStyleSheet(
            "QWizardPage#welcomePage, QWizardPage#completionPage { background: white; color: black; }"
        )
        layout = QHBoxLayout(welcome)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        illustration = QLabel()
        illustration.setObjectName("welcomeArt")
        illustration.setFixedWidth(180)
        illustration.setStyleSheet("background: #090953;")
        illustration.setAlignment(Qt.AlignBottom | Qt.AlignHCenter)
        illustration.setPixmap(QPixmap(str(ROOT / "installer/art/watermark.png")))
        illustration.setScaledContents(True)
        illustration.setMinimumHeight(0)
        illustration.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Ignored)
        layout.addWidget(illustration)
        copy = QVBoxLayout()
        copy.setContentsMargins(0, 19, 18, 16)
        title = QLabel(("Completing" if completion else "Welcome to") + " the Chicago95\nSetup Wizard")
        title.setStyleSheet("font: bold 21px 'Sans Serif'; color: black;")
        copy.addWidget(title)
        copy.addSpacing(14)
        message = QLabel(
            "Setup has finished installing Chicago95 for KDE Plasma."
            if completion
            else "This wizard installs Chicago95 for KDE Plasma. Choose a Windows theme or your Linux setup, "
            "then customize the components, appearance and sounds for your computer."
        )
        message.setWordWrap(True)
        copy.addWidget(message)
        copy.addSpacing(12)
        copy.addWidget(QLabel("Click Finish to close Setup." if completion else "Click Next to continue with Setup."))
        if completion:
            details = QPushButton("Show installation log")
            details.setCheckable(True)
            details.setAutoDefault(False)
            copy.addWidget(details, alignment=Qt.AlignLeft)
            self.completion_log = QPlainTextEdit()
            self.completion_log.setReadOnly(True)
            self.completion_log.hide()
            details.toggled.connect(self.completion_log.setVisible)
            details.toggled.connect(
                lambda shown: details.setText("Hide installation log" if shown else "Show installation log")
            )
            copy.addWidget(self.completion_log)
        copy.addStretch()
        layout.addLayout(copy, 1)
        return self.addPage(welcome)

    def selected(self):
        return [key for i, key in enumerate(COMPONENTS) if self.components.item(i).checkState() == Qt.Checked]

    def add_components(self):
        page = SelectionPage("Select Components", lambda: bool(self.selected()))
        page.setSubTitle("Select the components you want Setup to install.")
        self.component_id = self.addPage(page)
        layout = QHBoxLayout(page)
        self.components = QListWidget()
        layout.addWidget(self.components, 1)
        side = QVBoxLayout()
        layout.addLayout(side)
        image = picture()
        description = QLabel()
        description.setWordWrap(True)
        description.setFixedWidth(344)
        side.addWidget(image)
        side.addWidget(description)
        side.addStretch()
        saved = backend.read_key_values(self.saved) if self.saved.is_file() else {}
        picked = saved.get("COMPONENTS", "base look taskbar startmenu controlpanel sounds background desktop").split()
        for key in COMPONENTS:
            item = QListWidgetItem(key, self.components)
            item.setCheckState(Qt.Checked if key in picked else Qt.Unchecked)

        def refresh(item):
            info, path = COMPONENTS[item.text()]
            if item.text() == "icons":
                state = defaults(self.saved, self.active_overrides(), self.machine)
                try:
                    image.setPixmap(render("icons", state["icons"], state))
                except ValueError as error:
                    image.setText(str(error))
            else:
                if item.text() in ("desktop", "background"):
                    state = defaults(self.saved, self.active_overrides(), self.machine)
                    path = DESKTOP_CAPTURES.get(state["look"], path)
                image.setPixmap(
                    QPixmap(str(ROOT / path)).scaled(image.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                )
            description.setText(
                ("Selected. " + info) if item.checkState() == Qt.Checked else ("Skip this component. " + info)
            )
            page.completeChanged.emit()

        self.components.currentItemChanged.connect(lambda item, _: refresh(item) if item else None)
        self.components.itemChanged.connect(lambda item: (self.components.setCurrentItem(item), refresh(item)))
        self.currentIdChanged.connect(
            lambda _: refresh(self.components.currentItem()) if self.currentPage() == page else None
        )
        self.components.setCurrentRow(0)

    def active_overrides(self):
        keys = self.route_fields()
        edited = {k: v for k, v in self.overrides.items() if k == "look" or k in keys}
        return self.profile_defaults() | edited

    def profile_defaults(self):
        return self.linux_defaults if self.os_picker.currentData() == "linux" else {}

    def route_fields(self):
        return tuple(self.field_pages) if self.full.isChecked() else LIGHT_FIELDS

    def nextId(self):
        current = self.currentId()
        if hasattr(self, "review_id") and current == self.review_id:
            return self.completion_id if self.installed else -1
        if hasattr(self, "review_id") and (current == self.mode_id or current in self.field_pages.values()):
            route = [self.mode_id, *(self.field_pages[k] for k in self.route_fields()), self.review_id]
            return route[route.index(current) + 1]
        return super().nextId()

    def issue(self, key):
        try:
            plan(self.selected(), {key: self.overrides[key]} if key in self.overrides else {})
        except ValueError as error:
            return str(error)
        return ""

    def add_customization(self):
        os_page = QWizardPage()
        os_page.setTitle("Choose a starting point")
        os_page.setSubTitle("Choose a Windows theme or start with preferences from this Linux desktop.")
        layout = QVBoxLayout(os_page)
        preview = picture(446, 246)
        layout.addWidget(preview, alignment=Qt.AlignCenter)
        self.os_picker = QComboBox()
        self.os_picker.setAccessibleName("Customization starting point")
        for key, name in OS_NAMES.items():
            self.os_picker.addItem(name, key)
        self.os_picker.addItem("My Linux setup", "linux")
        remembered = defaults(self.saved, {})["look"]
        self.os_picker.setCurrentIndex(max(0, self.os_picker.findData(remembered)))
        layout.addWidget(self.os_picker)

        def choose_os():
            look = self.os_picker.currentData()
            if look == "linux":
                self.overrides.pop("look", None)
                rows = [f"{FIELDS[k].label}: {v}" for k, v in self.linux_defaults.items() if k != "branding"]
                preview.setText(
                    "Current Linux preferences\n\n" + "\n".join([*rows, "System branding: Linux distribution"])
                )
                return
            self.overrides["look"] = look
            preview.setPixmap(
                QPixmap(str(ROOT / DESKTOP_CAPTURES[look])).scaled(
                    preview.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
            )

        self.os_picker.currentIndexChanged.connect(choose_os)
        choose_os()
        self.os_id = self.addPage(os_page)

        mode = QWizardPage()
        mode.setTitle("Choose how to customize")
        mode.setSubTitle("Choose which settings to review for your chosen starting point.")
        layout = QHBoxLayout(mode)
        layout.setContentsMargins(18, 14, 18, 14)
        choices = QVBoxLayout()
        layout.addLayout(choices, 1)
        self.light = QRadioButton("Lightly customize")
        self.full = QRadioButton("Customize all")
        self.light.setChecked(True)
        for button, description in (
            (self.light, "Choose icons, taskbar height, pointer size, Start text and sounds."),
            (self.full, "Edit every setting, from window frames to login screens."),
        ):
            choices.addWidget(button)
            explanation = QLabel(description)
            explanation.setIndent(20)
            explanation.setWordWrap(True)
            choices.addWidget(explanation)
            choices.addSpacing(14)
        choices.addStretch()
        scope = QGroupBox("Settings you’ll review")
        scope_layout = QVBoxLayout(scope)
        self.scope_list = QListWidget()
        self.scope_list.setAccessibleName(scope.title())
        scope_layout.addWidget(self.scope_list)
        layout.addWidget(scope, 1)
        self.full.toggled.connect(self.refresh_scope)
        self.mode_id = self.addPage(mode)
        self.field_pages = {}
        for key, field in FIELDS.items():
            if key == "look":
                continue
            page = SelectionPage(field.label, lambda k=key: not self.issue(k))
            QVBoxLayout(page)
            self.field_pages[key] = self.addPage(page)

        self.refresh_scope()
        self.controls = QWidget()
        columns = QHBoxLayout(self.controls)
        columns.setSpacing(16)
        preview_box = QGroupBox("Preview")
        preview_layout = QVBoxLayout(preview_box)
        self.image = picture()
        preview_layout.addWidget(self.image, alignment=Qt.AlignCenter)
        columns.addWidget(preview_box, alignment=Qt.AlignTop)
        side = QVBoxLayout()
        columns.addLayout(side, 1)
        self.setting_label = QLabel()
        side.addWidget(self.setting_label)
        self.editor = QComboBox()
        self.editor.setInsertPolicy(QComboBox.NoInsert)
        self.editor.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.editor.setMinimumContentsLength(12)
        self.setting_label.setBuddy(self.editor)
        side.addWidget(self.editor)
        self.default_value = QLabel()
        self.default_value.setWordWrap(True)
        self.default_value.setTextFormat(Qt.PlainText)
        side.addWidget(self.default_value)
        actions = QVBoxLayout()
        side.addLayout(actions)
        self.browse = QPushButton("Browse…")
        self.play = QPushButton("Play sample")
        reset = QPushButton("Restore default")
        for button in (self.browse, self.play, reset):
            actions.addWidget(button, alignment=Qt.AlignLeft)
        self.note = QLabel()
        self.note.setWordWrap(True)
        self.note.setTextFormat(Qt.PlainText)
        side.addWidget(self.note)
        side.addStretch()

        self.editor.currentTextChanged.connect(self.edit)
        self.browse.clicked.connect(self.pick_image)
        self.play.clicked.connect(self.play_sample)
        reset.clicked.connect(self.reset_field)

    def refresh_scope(self):
        self.scope_list.clear()
        self.scope_list.addItems([FIELDS[key].label for key in self.route_fields()])

    def load_field(self, key):
        self.key = key
        if self.player:
            self.player.stop()
        field = FIELDS[key]
        state = defaults(self.saved, self.active_overrides(), self.machine)
        inherited = {k: v for k, v in self.active_overrides().items() if k != key}
        default = defaults(self.saved, self.profile_defaults() | inherited, self.machine)[key]
        source = "Linux preference" if key in self.profile_defaults() else "Theme default"
        self.default_value.setText(f"{source}: {default}")
        self.setting_label.setText(field.label)
        with QSignalBlocker(self.editor):
            self.editor.clear()
            self.editor.setEditable(field.kind != "menu")
            self.editor.addItems(field.choices)
            if self.editor.findText(state[key]) < 0:
                self.editor.addItem(state[key])
            self.editor.setCurrentText(state[key])
            self.editor.setAccessibleName(field.label)
        self.browse.setVisible(field.kind == "image")
        self.play.setVisible(key in ("sounds", "saver"))
        self.play.setText("Play sample" if key == "sounds" else "Run screensaver")
        self.refresh_preview(state)

    def edit(self, value):
        self.overrides.pop(self.key, None)
        inherited = defaults(self.saved, self.active_overrides(), self.machine)
        if value != inherited[self.key]:
            self.overrides[self.key] = value
        self.refresh_preview(inherited | {self.key: value})

    def reset_field(self):
        self.overrides.pop(self.key, None)
        self.load_field(self.key)

    def refresh_preview(self, state):
        value = state[self.key]
        try:
            if self.key in self.overrides:
                validate(self.key, value)
            self.image.setPixmap(render(self.key, value, state))
            note = "Linux preference" if self.key in self.profile_defaults() else "Theme default"
            if self.key in self.overrides:
                note = "Custom choice"
            if self.key == "sounds":
                url = sound_url(value)
                available = not url.isEmpty()
                self.play.setEnabled(available)
                if not available:
                    note += " · Audio unavailable."
                elif not url.isLocalFile():
                    note += " · Play sample streams the original login sound."
            elif self.key == "saver":
                self.play.setEnabled(not self.saver_process.state() == QProcess.Running)
            self.note.setText(self.issue(self.key) or f"{note} · {value}")
        except (ValueError, KeyError) as error:
            self.image.setText("Preview unavailable")
            self.note.setText(str(error))
            self.play.setEnabled(False)
        self.page(self.field_pages[self.key]).completeChanged.emit()

    def pick_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select image", "", "Images (*.png *.svg *.jpg *.jpeg *.bmp)")
        if path:
            self.editor.setEditText(path)

    def play_sample(self):
        if self.key == "saver":
            self.saver_process.setProgram(sys.executable)
            self.saver_process.setArguments(
                [str(ROOT / "bin/chicago95-screensaver"), "--hack", self.editor.currentText()]
            )
            self.saver_process.start()
            return
        try:
            from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
        except ImportError:
            self.note.setText("Install the PySide6 QtMultimedia module to play the audio preview.")
            return

        if not self.player:
            self.player = QMediaPlayer(self)
            self.audio = QAudioOutput(self)
            self.player.setAudioOutput(self.audio)
            self.player.errorOccurred.connect(lambda _, message: self.note.setText(message))
        sample = sound_url(self.editor.currentText())
        if not sample.isEmpty():
            self.player.setSource(sample)
            self.player.play()

    def add_review(self):
        page = QWizardPage()
        page.setTitle("Review and Install")
        page.setSubTitle("Review your choices before Setup installs the selected components.")
        self.review_id = self.addPage(page)
        layout = QVBoxLayout(page)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(1200)
        layout.addWidget(self.log)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(18)
        self.progress.setStyleSheet(
            "QProgressBar { background:#c0c0c0; border:2px inset #dfdfdf; } QProgressBar::chunk { background:#000080; }"
        )
        self.progress.hide()
        self.partial_line = ""
        self.status = QLabel()
        self.status.setWordWrap(True)
        self.copy_icon = QLabel()
        self.copy_icon.setPixmap(self.windowIcon().pixmap(32, 32))
        self.copy_icon.hide()
        line = QHBoxLayout()
        line.addWidget(self.copy_icon)
        line.addWidget(self.status, 1)
        layout.addLayout(line)
        self.tasks = QLabel()
        self.tasks.hide()
        layout.addWidget(self.tasks)
        layout.addWidget(self.progress)
        buttons = QHBoxLayout()
        self.test_button = QPushButton("Dry run")
        self.install_button = QPushButton("Install")
        self.install_button.setEnabled(not self.dry_only)
        buttons.addWidget(self.test_button)
        buttons.addWidget(self.install_button)
        buttons.addStretch()
        layout.addLayout(buttons)
        self.test_button.clicked.connect(lambda: self.run_backend(True))
        self.install_button.clicked.connect(lambda: self.run_backend(False))

    def page_changed(self, page):
        if page < 0:
            return
        if self.player:
            self.player.stop()
        if page == self.completion_id:
            self.setButtonText(QWizard.FinishButton, "Finish")
            self.setOption(QWizard.NoBackButtonOnLastPage)
            self.completion_log.setPlainText(self.log.toPlainText())
        elif page == self.review_id:
            summary = [self.os_picker.currentText(), "", *(COMPONENTS[key][0] for key in self.selected())]
            summary.extend(
                f"{FIELDS[key].label}: {value}" for key, value in self.active_overrides().items() if key != "look"
            )
            self.log.setPlainText("\n".join(summary))
            self.status.setText("Dry run lists the planned operations. Install applies them to this computer.")
        elif page in self.field_pages.values():
            key = next(key for key, pid in self.field_pages.items() if pid == page)
            steps = self.route_fields()
            self.currentPage().setSubTitle(
                f"{self.os_picker.currentText()} · Setting {steps.index(key) + 1} of {len(steps)}"
            )
            self.currentPage().layout().addWidget(self.controls)
            self.controls.show()
            self.load_field(key)

    def set_busy(self, busy):
        self.busy = busy
        page = self.page(self.review_id)
        page.setTitle(
            ("Checking installation plan" if self.dry else "Installing components") if busy else "Review and Install"
        )
        page.setSubTitle(
            "Setup is processing the components you selected."
            if busy
            else "Review your choices before Setup installs the selected components."
        )
        page.layout().setContentsMargins(*((40, 22, 40, 48) if busy else (9, 9, 9, 9)))
        self.tasks.setVisible(busy)
        if busy:
            self.show_step(-1)
        self.copy_icon.setVisible(busy)
        self.progress.setVisible(busy)
        self.log.setVisible(not busy)
        self.test_button.setVisible(not busy)
        self.install_button.setVisible(not busy)
        for button in (
            self.test_button,
            self.install_button,
            self.button(QWizard.BackButton),
            self.button(QWizard.FinishButton),
            self.button(QWizard.CancelButton),
        ):
            button.setEnabled(not busy and (button != self.install_button or not self.dry_only))

    def run_backend(self, dry):
        if self.busy or self.currentId() != self.review_id or (self.dry_only and not dry):
            return
        try:
            choices = self.active_overrides()
            state = defaults(self.saved, choices, self.machine)
            args, settings = plan(self.selected(), {"panel": state["panel"], "branding": state["branding"]} | choices)
        except ValueError as error:
            self.status.setText(str(error))
            return
        if settings:
            self.settings_dir = tempfile.TemporaryDirectory(prefix="chicago95-setup-")
            path = Path(self.settings_dir.name) / "choices.conf"
            path.write_text("".join(f"{k}={v}\n" for k, v in settings.items()))
            args.append(f"--settings={path}")
        if dry:
            args.append("--dry-run")
        self.dry = dry
        self.set_busy(True)
        self.log.clear()
        self.progress.setRange(0, 0)
        self.progress.show()
        self.partial_line = ""
        self.status.setText("Checking installation plan…" if dry else "Installing Chicago95…")
        env = QProcessEnvironment.systemEnvironment()
        env.insert("SUDO_ASKPASS", str(ROOT / "bin/chicago95-askpass"))
        self.process.setProcessEnvironment(env)
        self.process.setWorkingDirectory(str(ROOT))
        self.process.start(self.program, args)
        self.process.closeWriteChannel()

    def read_output(self):
        self.append_output(bytes(self.process.readAllStandardOutput()).decode(errors="replace"))

    def show_step(self, current):
        rows = []
        for index, step in enumerate(SETUP_STEPS):
            marker = "✓" if index < current else "▶" if index == current else "  "
            rows.append(f"{marker} {step}")
        self.tasks.setText("\n".join(rows))
        if current == len(SETUP_STEPS) - 1:
            self.page(self.review_id).setTitle("Performing Final Tasks")
            self.progress.setRange(0, 0)

    def append_output(self, text):
        from PySide6.QtGui import QTextCursor

        *lines, self.partial_line = (self.partial_line + text).split("\n")
        for line in lines:
            if self.busy and line.startswith("== ") and line[3:] in SETUP_STEPS:
                self.show_step(SETUP_STEPS.index(line[3:]))
            match = re.match(r"^   \((\d{1,9})/(\d{1,9})\) ", line)
            if match:
                done, total = map(int, match.groups())
                if 0 < done <= total:
                    self.progress.setRange(0, total)
                    self.progress.setValue(done)
        self.log.moveCursor(QTextCursor.End)
        self.log.insertPlainText(text)

    def end_run(self, message):
        if self.settings_dir:
            self.settings_dir.cleanup()
            self.settings_dir = None
        self.progress.hide()
        self.status.setText(message)
        self.set_busy(False)

    def backend_finished(self, code, exit_status):
        self.read_output()
        if code or exit_status != QProcess.NormalExit:
            self.end_run(f"Setup failed (exit {code}). See the output above.")
        else:
            self.end_run(
                "Dry run complete." if self.dry else "Setup finished. Check the output for skipped components."
            )

            if not self.dry:
                self.installed = True
                self.next()

    def process_error(self, error):
        if error == QProcess.FailedToStart:
            self.end_run("Setup failed to start. " + self.process.errorString())

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape and not self.isWindow():
            event.accept()
            return
        super().keyPressEvent(event)

    def accept(self):
        if self.busy:
            return
        if not self.isWindow() and not self.installed:
            self.window().close()
        else:
            super().accept()

    def reject(self):
        if self.busy:
            return
        if not self.isWindow():
            self.window().close()
        else:
            super().reject()

    def closeEvent(self, event):
        if self.busy:
            event.ignore()
        else:
            super().closeEvent(event)


class SetupWindow(QWidget):
    def __init__(self, wizard):
        super().__init__(None, Qt.Window | Qt.FramelessWindowHint)
        self.wizard = wizard
        self.exit_alert = None
        self.exit_confirmed = False
        self.setWindowTitle(wizard.windowTitle())
        self.setWindowIcon(wizard.windowIcon())
        self.setPalette(wizard.palette())
        self.setFont(wizard.font())
        available = self.screen().availableGeometry()
        self.resize(min(850, available.width()), min(575, available.height()))
        layout = QVBoxLayout(self)
        margin = 38 if available.width() >= 800 and available.height() >= 560 else 16
        layout.setContentsMargins(margin, margin, margin, margin)
        self.dialog = QFrame()
        self.dialog.setAutoFillBackground(True)
        self.dialog.setFrameStyle(QFrame.WinPanel | QFrame.Raised)
        layout.addWidget(self.dialog)
        body = QVBoxLayout(self.dialog)
        body.setContentsMargins(3, 3, 3, 3)
        body.setSpacing(0)
        self.caption = SetupCaption(self)
        self.caption.setFixedHeight(21)
        self.caption.setStyleSheet(
            "QFrame#setupCaption { background: #000080; } QLabel { color: white; font-weight: bold; }"
        )
        body.addWidget(self.caption)
        wizard.setParent(self, Qt.Widget)
        body.addWidget(wizard, 1)
        wizard.finished.connect(self.close)
        wizard.restart()

    def closeEvent(self, event):
        if self.wizard.installed or self.exit_confirmed:
            super().closeEvent(event)
            return
        event.ignore()
        if self.wizard.busy:
            return
        if self.exit_alert is None:
            alert = QMessageBox(self)
            alert.setWindowTitle("Exit Chicago95 Setup")
            alert.setIcon(QMessageBox.Warning)
            alert.setText("Exit before completing installation?")
            alert.setInformativeText("Choose Continue Setup to return to your selections.")
            alert.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            alert.button(QMessageBox.Yes).setText("Exit Setup")
            alert.button(QMessageBox.No).setText("Continue Setup")
            alert.setDefaultButton(QMessageBox.No)
            alert.setEscapeButton(QMessageBox.No)
            alert.finished.connect(self.exit_answered)
            self.exit_alert = alert
        if not self.exit_alert.isVisible():
            self.exit_alert.open()

    def exit_answered(self, result):
        if result == QMessageBox.Yes and not self.wizard.busy:
            self.exit_confirmed = True
            self.close()

    def paintEvent(self, event):
        super().paintEvent(event)
        with QPainter(self) as painter:
            painter.fillRect(self.rect(), QColor("#7894bc"))
            painter.fillRect(self.rect(), QBrush(QColor("#355d9a"), Qt.BDiagPattern))
            for x, y, width, height, colour in (
                (self.width() * 7 // 10, -35, 120, 63, "#31568d"),
                (15, self.height() // 3, 110, self.height() // 2, "#74989c"),
                (self.width() * 4 // 5, self.height() * 2 // 3, 200, self.height() // 4, "#294f86"),
                (self.dialog.x() - 7, self.dialog.y() - 7, 76, 84, "#e79325"),
            ):
                painter.setPen(QPen(QColor(colour), 4))
                painter.drawRect(x, y, width, height)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chicago95 graphical installer for KDE Plasma")
    parser.add_argument("--dry-run", action="store_true", help="preview the installation without applying changes")
    args = parser.parse_args()
    if not any(os.getenv(k) for k in ("DISPLAY", "WAYLAND_DISPLAY", "QT_QPA_PLATFORM")):
        parser.error("Open graphical Setup from a desktop session, or run ./install.sh --plain.")
    app = QApplication(sys.argv)
    app.setStyle("Windows")
    app.setPalette(app.style().standardPalette())
    window = SetupWindow(SetupWizard(dry_only=args.dry_run))
    window.show()
    sys.exit(app.exec())
