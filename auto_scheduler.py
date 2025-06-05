import sys
from PyQt5.QtWidgets import (
   QApplication, 
   QDialog,
   QMdiArea,
   QAction,
   QTextEdit
)

from PyQt5.QtCore import (
    Qt,
    QSize
)

from PyQt5.QtGui import (
    QIcon
) 

from PyQt5 import uic

from template_config import TemplateConfiguration
from schedule_dialog import ScheduleDialog
from view_schedule_dialog import ViewScheduleDialog

widget, base = uic.loadUiType('auto_scheduler.ui')

class MdiChild(QDialog):
    def __init__(self, title: str):
        super(MdiChild, self).__init__()
        self.setWindowTitle(title)

class AutoScheduler(widget, base):
    def __init__(self):
        super(AutoScheduler, self).__init__()
        self.mdi_area = QMdiArea()
        self.mdi_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.mdi_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setCentralWidget(self.mdi_area)

        self.create_actions()
        self.create_toolbar()
        self.create_statusbar()

        self.setWindowTitle("Auto-Scheduler")
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Ready")

    def create_actions(self):
        temp_icon = QIcon('icons/createbreak.bmp')
        self.on_template_act = QAction(temp_icon, "&Template Designer", self)
        self.on_template_act.triggered.connect(self.on_template)

        sch_icon = QIcon('icons/booking.bmp')
        self.on_schedule_act = QAction(sch_icon, "&View Schedule", self)
        self.on_schedule_act.triggered.connect(self.on_view_schedule)

    def create_mdi_child(self, title: str):
        child = MdiChild(title)
        self.mdi_area.addSubWindow(child)
        return child

    def on_template(self):
        clock_template = TemplateConfiguration(self)
        self.mdi_area.addSubWindow(clock_template)
        clock_template.showMaximized()
        self.status_bar.showMessage(f"Tracks Database: {clock_template.mssql_conn.database()}")

    def on_view_schedule(self):
        view_schedule = ViewScheduleDialog(self)
        self.mdi_area.addSubWindow(view_schedule)
        view_schedule.showMaximized()

    def create_toolbar(self):
        self.main_toolbar = self.addToolBar('Main')
        self.main_toolbar.setMovable(False)
        self.main_toolbar.setFloatable(False)
        self.main_toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        self.main_toolbar.setIconSize(QSize(52, 52))
        self.main_toolbar.setOrientation(Qt.Orientation.Horizontal)
        self.main_toolbar.addAction(self.on_template_act)
        self.main_toolbar.addAction(self.on_schedule_act)
        pass

    def create_statusbar(self):
        pass


app = QApplication(sys.argv)
auto_scheduler = AutoScheduler()
auto_scheduler.show()
sys.exit(app.exec_())   