from PyQt5 import uic

from PyQt5.QtWidgets import (
    QTableWidget,
    QListWidgetItem
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

        self.edtFrom.setDate(QDate.currentDate())
        self.edtTo.setDate(QDate.currentDate())

        self.schedule_items = []
        self.templates = {}

        # self.edtFrom.dateChanged.connect(self.on_date_changed)
        # self.edtTo.dateChanged.connect(self.on_date_changed)

        self._populate_range_combo()
        self.cbRange.currentIndexChanged.connect(self.on_range_changed)
        self.cbRange.setCurrentIndex(0)

        self.lwTemplates.currentItemChanged.connect(self.on_template_changed)

        self._populate_template_list()

        # self.show_schedule_by_date(self.edtFrom.date())

    def on_date_changed(self, date: QDate):
        self.show_schedule_by_date(date)

    def show_schedule_by_date(self, date):
        self._initilize_schedule_table()
        self._load_schedule_by_date(date)

    def _populate_range_combo(self):
        self.cbRange.addItem("To")
        self.cbRange.addItem("Future")

    def _populate_template_list(self):
        self.templates = self.db_config.fetch_all_templates()
        self._show_templates(self.templates)

    def _show_templates(self, templates: dict):
        for name, template in templates.items():
            item = QListWidgetItem(name)
            item.setData(Qt.ItemDataRole.UserRole, template.id())
            self.lwTemplates.addItem(item)

    def _show_dates(self, dates: set):
        self.lwDates.clear()
        for date in dates:
            item = QListWidgetItem(date)
            self.lwDates.addItem(item)

    def on_range_changed(self, index: int):
        if index == 0:  # "To" is selected
            self.edtTo.setEnabled(True)
        else:  # "Future" is selected
            self.edtTo.setEnabled(False)

    def on_template_changed(self, current: QListWidgetItem, previous: QListWidgetItem):
        if current:
            template_id = current.data(Qt.ItemDataRole.UserRole)

            if self.cbRange.currentIndex() == 0:
                self._load_schedule_by_template_and_date_range(template_id,
                                                            self.edtFrom.date(), self.edtTo.date())
            else:
                self._load_schedule_by_template_and_date_range(template_id,
                                                            self.edtFrom.date(), None)

    def _load_schedule_by_date(self, date):
        self.schedule_items = self.db_config.fetch_schedule_by_date(date)

        for item in self.schedule_items:
            self._add_schedule_item(item)

    def _load_schedule_by_template_and_date_range(self, template_id: int, start_date: QDate, end_date: QDate):
        self.schedule_items = self.db_config.fetch_schedule_by_template_and_date_range(template_id, start_date, end_date)

        self._initilize_schedule_table()

        dates = set()
        for item in self.schedule_items:
            added_item = self._add_schedule_item(item)

            if added_item:
                dates.add(added_item.formatted_date())

        sorted_dates = sorted(dates)
        self._show_dates(dates)

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

        return s_item


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

        date = self.edtFrom.date().toString("yyyy-MM-dd")

        if not date:
            return


        self.db_config.delete_schedule_by_date(date, schedule_refs)

