#!/usr/bin/env python3
"""Launch the Chicago95 Setup preview in a desktop window. Requires PySide6."""

import sys
from pathlib import Path

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QLabel, QListWidget, QListWidgetItem, QVBoxLayout, QWizard, QWizardPage

ROOT = Path(__file__).resolve().parents[1]
COMPONENTS = ("Chicago95 base files", "Desktop look", "Taskbar", "Start menu", "Control Panel", "Sound scheme")


def setup_banner(icon):
    banner = QPixmap(155, 300)
    banner.fill(QColor("#000080"))
    with QPainter(banner) as painter:
        painter.drawPixmap(QRect(30, 40, 96, 96), icon, icon.rect())
        painter.setPen(Qt.GlobalColor.white)
        font = painter.font()
        font.setBold(True)
        font.setPixelSize(24)
        painter.setFont(font)
        painter.drawText(16, 183, "Chicago95")
        font.setBold(False)
        font.setPixelSize(16)
        painter.setFont(font)
        painter.drawText(18, 210, "S E T U P")
    return banner


def setup_wizard():
    wizard = QWizard()
    wizard.setWindowTitle("Chicago95 Setup")
    wizard.setWizardStyle(QWizard.WizardStyle.ClassicStyle)
    wizard.setOption(QWizard.WizardOption.IndependentPages)
    icon = QPixmap(str(ROOT / "data/desktop-icons/native/1995/computer.png"))
    wizard.setWindowIcon(QIcon(icon))
    wizard.setPixmap(QWizard.WizardPixmap.WatermarkPixmap, setup_banner(icon))
    wizard.resize(580, 390)

    welcome = QWizardPage()
    welcome.setTitle("Welcome to Chicago95 Setup")
    intro = QVBoxLayout(welcome)
    message = QLabel("This wizard lets you choose the Chicago95 components for your Plasma desktop.")
    message.setWordWrap(True)
    intro.addWidget(message)
    intro.addWidget(QLabel("Preview only. No settings will be changed."))
    intro.addStretch()
    wizard.addPage(welcome)

    components = QWizardPage()
    components.setTitle("Select Components")
    choices = QVBoxLayout(components)
    prompt = QLabel("Choose the &components to include.")
    choices.addWidget(prompt)
    items = QListWidget()
    prompt.setBuddy(items)
    items.setAccessibleName("Components")
    for component in COMPONENTS:
        item = QListWidgetItem(component, items)
        item.setCheckState(Qt.CheckState.Checked)
    items.setCurrentRow(0)
    choices.addWidget(items)
    wizard.addPage(components)
    return wizard


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("Chicago95 Setup")
    app.setStyle("Windows")
    app.setPalette(app.style().standardPalette())
    dialog = setup_wizard()
    dialog.show()
    sys.exit(app.exec())
