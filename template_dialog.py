from PyQt5.QtWidgets import QListWidgetItem
from PyQt5 import uic

from PyQt5.QtWidgets import (
    QMessageBox
)

from PyQt5.QtCore import (
    Qt
)

widget, base = uic.loadUiType('template_dialog.ui')

class TemplateDialog(widget, base):
    def __init__(self, template=None):
        super(TemplateDialog, self).__init__()
        self.setupUi(self)
        self._template = template

        self.selected_hours = []
        self.selected_dow = []

        self.btnOk.clicked.connect(self.accept)
        self.btnCancel.clicked.connect(self.reject)

        self.populate_hours()
        self._check_uncheck_dow(Qt.CheckState.Checked)

        self._initialize_values(self._template)
        
    def _initialize_values(self, template):
        if template is not None:
            self.txtName.setText(template.name())
            self.txtDescription.setText(template.description())
            for hour in template.hours():
                self.lstHours.item(hour).setCheckState(Qt.CheckState.Checked)
            
            self._check_dow(template.dow())

    def get_name(self) -> str:
        return self.txtName.text()
    
    def get_description(self) -> str:
        return self.txtDescription.text()
    
    def get_hours(self) -> list:
        return self.lstHours.selectedItems()

    def get_dow(self) ->list:
        return self.selected_dow

    def populate_hours(self):
        # Populate the list of hours using the range 0-23 of QListWidgetItems formatted as 00:00 - 23:00
        for i in range(0, 24):
            item = QListWidgetItem(f"{i:02d}:00")
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            item.setData(Qt.ItemDataRole.UserRole, i)
            self.lstHours.addItem(item)

    def _check_uncheck_dow(self, state):
        self.cbMon.setCheckState(state)
        self.cbTue.setCheckState(state)
        self.cbWed.setCheckState(state)
        self.cbThu.setCheckState(state)
        self.cbFri.setCheckState(state)
        self.cbSat.setCheckState(state)
        self.cbSun.setCheckState(state)

    def _check_dow(self, dow:list):
        self._check_uncheck_dow(Qt.CheckState.Unchecked)
        for day in dow:
            if day == 1:
                self.cbMon.setCheckState(Qt.CheckState.Checked)

            if day == 2:
                self.cbTue.setCheckState(Qt.CheckState.Checked)
                
            if day == 3:
                self.cbWed.setCheckState(Qt.CheckState.Checked)

            if day == 4:
                self.cbThu.setCheckState(Qt.CheckState.Checked)

            if day == 5:
                self.cbFri.setCheckState(Qt.CheckState.Checked)

            if day == 6:
                self.cbSat.setCheckState(Qt.CheckState.Checked) 

            if day == 7:
                self.cbSun.setCheckState(Qt.CheckState.Checked)
                

    def get_selected_hours(self) -> list:
        selected_hours = []
        # Selected hours are the items that are checked
        for i in range(self.lstHours.count()):
            item = self.lstHours.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                selected_hours.append(item.data(Qt.ItemDataRole.UserRole))
        return selected_hours

    def get_selected_dow(self) -> list:
        selected_dow = []
        if self.cbMon.isChecked():
            selected_dow.append(1)

        if self.cbTue.isChecked():
            selected_dow.append(2)

        if self.cbWed.isChecked():
            selected_dow.append(3)

        if self.cbThu.isChecked():
            selected_dow.append(4)

        if self.cbFri.isChecked():
            selected_dow.append(5)

        if self.cbSat.isChecked():
            selected_dow.append(6)

        if self.cbSun.isChecked():
            selected_dow.append(7)

        return selected_dow
        

    def accept(self):
        if self.get_name() == "":
            self.show_message("Name is required")
            return

        self.selected_hours = self.get_selected_hours()

        self.selected_dow = self.get_selected_dow()
        

        if len(self.selected_hours) == 0:
            self.show_message("At least one hour must be selected")
            return
        
        super(TemplateDialog, self).accept()

    def reject(self):
        super(TemplateDialog, self).reject()

    def show_message(self, message:str):
        msg_box = QMessageBox()
        msg_box.setText(message)
        msg_box.exec_()
        


