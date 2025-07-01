from PyQt5 import uic

from PyQt5.QtWidgets import (
    QTableWidget
)

from PyQt5.QtCore import (
    Qt,
    QDate,
)

from data_config import DataConfiguration

from template_item import (
    BaseTableWidgetItem,
    ItemType
)

widget, base = uic.loadUiType('view_schedule_dialog.ui')

class ViewScheduleDialog(widget, base):
    def __init__(self, parent):
        super(ViewScheduleDialog, self).__init__()
        self.setupUi(self)

        self.db_config = DataConfiguration("")

        self.edtDate.setDate(QDate.currentDate())

        self.schedule_items = []

        self.edtDate.dateChanged.connect(self.on_date_changed)
        self.show_schedule_by_date(self.edtDate.date())

    def on_date_changed(self, date: QDate):
        self.show_schedule_by_date(date)

    def show_schedule_by_date(self, date):
        self._initilize_schedule_table()
        self._load_schedule_by_date(date)

    def _load_schedule_by_date(self, date):
        self.schedule_items = self.db_config.fetch_schedule_by_date(date)

        for item in self.schedule_items:
            self._add_schedule_item(item)

    def _add_schedule_item(self, s_item):
        row = self.twViewSchedule.rowCount()
        self.twViewSchedule.insertRow(row)

        if s_item.item_type() not in BaseTableWidgetItem.widget_register:
            return

        WidgetItem = BaseTableWidgetItem.widget_register[s_item.item_type()]

        if s_item.item_type() == ItemType.HEADER:
            twiDate = WidgetItem("")
            twiTime = WidgetItem("")
        else:
            twiDate = WidgetItem(s_item.formatted_date())
            twiDate.setData(Qt.ItemDataRole.UserRole, s_item.item_identifier())
            twiTime = WidgetItem(s_item.start_time())

        self.twViewSchedule.setItem(row, 0, twiDate)
        self.twViewSchedule.setItem(row, 1, twiTime)
        self.twViewSchedule.setItem(row, 2, WidgetItem((s_item.formatted_duration())))
        self.twViewSchedule.setItem(row, 3, WidgetItem(s_item.title()))
        self.twViewSchedule.setItem(row, 4, WidgetItem(s_item.artist_name()))
        self.twViewSchedule.setItem(row, 5, WidgetItem(s_item.folder_name()))

        if (s_item.track_id() == 0):
            self.twViewSchedule.setItem(row, 6, WidgetItem(""))
        else:
            self.twViewSchedule.setItem(row, 6, WidgetItem(((s_item.formatted_track_id()))))

        self.twViewSchedule.setItem(row, 7, WidgetItem(s_item.item_path()))


    def _initilize_schedule_table(self):
        self.twViewSchedule.clear()
        self.twViewSchedule.setRowCount(0)
        self.twViewSchedule.setColumnCount(8)
        self.twViewSchedule.setSizeAdjustPolicy(
            QTableWidget.AdjustToContents
        )
        
        self.twViewSchedule.setColumnWidth(0, 150)
        self.twViewSchedule.setColumnWidth(1, 100)
        self.twViewSchedule.setColumnWidth(2, 100)
        self.twViewSchedule.setColumnWidth(3, 400)
        self.twViewSchedule.setColumnWidth(4, 400)
        self.twViewSchedule.setColumnWidth(5, 300)
        self.twViewSchedule.setColumnWidth(6, 200)
        self.twViewSchedule.setColumnWidth(7, 250)

        self.twViewSchedule.setHorizontalHeaderLabels(["Date", "Start", "Length", "Title", "Artist", "Category", "Filename", "Path" ])

    def on_delete_all_clicked(self):
        """ Delete all schedule items for the selected date and schedule ref"""
        # Extract all schedule reference from the schedule items
        if not self.schedule_items:
            return

        schedule_refs = {item.schedule_ref() for item in self.schedule_items}

        if not schedule_refs:
            return

        date = self.edtDate.date().toString("yyyy-MM-dd")

        if not date:
            return


        self.db_config.delete_schedule_by_date(date, schedule_refs)

