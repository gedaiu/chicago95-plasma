from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QWidget


class LunaDialogFrame(QDialog):
    def __init__(self, title, style, body_size, body_inset=0, help_button=False):
        super().__init__()
        self.setWindowTitle(title)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, help_button)
        self.body = QWidget(self)
        self.resize_body(*body_size)

    def resize_body(self, width, height):
        self.setFixedSize(width, height)
        self.body.setGeometry(0, 0, width, height)
