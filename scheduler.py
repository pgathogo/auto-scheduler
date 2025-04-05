import sys
import pyodbc
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

widget, base = uic.loadUiType('scheduler.ui')

class MdiChild(QDialog):
    def __init__(self, title: str):
        super(MdiChild, self).__init__()
        self.setWindowTitle(title)

class Scheduler(widget, base):
    def __init__(self):
        super(Scheduler, self).__init__()
        self.mdi_area = QMdiArea()
        self.mdi_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.mdi_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setCentralWidget(self.mdi_area)

        #self.mdi_area.subWindowActivated.connect(self.on_sub_window_activated)

        self.create_actions()
        self.create_toolbar()
        self.create_statusbar()

        #self.setupUi(self)

    def create_actions(self):
        temp_icon = QIcon('icons/createbreak.bmp')
        self.on_template_act = QAction(temp_icon, "&Template Designer", self)
        self.on_template_act.triggered.connect(self.on_template)

        sch_icon = QIcon('icons/booking.bmp')
        self.on_schedule_act = QAction(sch_icon, "&Schedule", self)
        self.on_schedule_act.triggered.connect(self.on_schedule)

    def create_mdi_child(self, title: str):
        child = MdiChild(title)
        self.mdi_area.addSubWindow(child)
        return child
    

    def on_template(self):
        clock_template = TemplateConfiguration()
        self.mdi_area.addSubWindow(clock_template)
        clock_template.showMaximized()

    def on_schedule(self):
        child = self.create_mdi_child('Schedule')
        child.show()

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
scheduler = Scheduler()
scheduler.show()
sys.exit(app.exec_())   # This line is not executed when the script is run from the command line