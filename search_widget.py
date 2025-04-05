
from PyQt5.QtWidgets import (
    QWidget,
    QGridLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QFormLayout
)

class SearchWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_controls()

    def setup_controls(self):
        layout = QGridLayout()
        row1 = 0
        col1 = 0
        row2 = 1
        col2 = 1
        row3 = 2

        dlg_layout = QVBoxLayout()

        form_layout = QFormLayout()
        form_layout.addRow(QLabel("Title"), QLineEdit())
        form_layout.addRow(QLabel("Artist"), QLineEdit())
        form_layout.addRow(QPushButton("Search"))
        dlg_layout.addLayout(form_layout)
        self.setLayout(dlg_layout)

        # layout.addWidget(QLabel("Title"), row1, col1)
        # layout.addWidget(QLineEdit(), row1, col2)
        # layout.addWidget(QLabel("Artist"), row2, col1)
        # layout.addWidget(QLineEdit(), row2, col2)
        # layout.addWidget(QPushButton("Search"), row3, col2)
        # self.setLayout(layout)