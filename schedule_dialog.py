import time
import random
from collections import OrderedDict

from PyQt5 import uic

from PyQt5.QtWidgets import (
    QTableWidgetItem,
    QTableWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
    QHeaderView
)

from PyQt5.QtCore import (
    QDate,
    Qt,
    QTime
)

from template import Template
from mssql_data import MSSQLData

from data_types import (
    MSSQL_CONN,
    ItemType
)

from template_item import (
    CommercialBreakItem,
    BaseTableWidgetItem,
    SongItem

)


widget, base = uic.loadUiType('schedule.ui')

class ScheduleDialog(widget, base):
    def __init__(self, template: Template, tracks: OrderedDict):
        super(ScheduleDialog, self).__init__()
        self.setupUi(self)

        self._template = template
        self._tracks = tracks
        self._folder_tracks = {}

        self._schedule_items = OrderedDict()

        self.btnGenerate.clicked.connect(self.on_generate_schedule)
        self.btnSave.clicked.connect(self.on_save_schedule)

        self.spMain.setSizes([200, 800])

        self._setup_defaults()
        self._initialize_schedule_table()


    def _initialize_schedule_table(self):
        self.twSchedule.clear()
        self.twSchedule.setRowCount(0)
        self.twSchedule.setColumnCount(7)
        self.twSchedule.setSizeAdjustPolicy(
            QTableWidget.AdjustToContents
        )
        #self.twSchedule.resizeColumnsToContents()

        self.twSchedule.setColumnWidth(0, 100)
        self.twSchedule.setColumnWidth(1, 100)
        self.twSchedule.setColumnWidth(2, 400)
        self.twSchedule.setColumnWidth(3, 400)
        self.twSchedule.setColumnWidth(4, 300)
        self.twSchedule.setColumnWidth(5, 100)
        self.twSchedule.setColumnWidth(6, 200)
        
        self.twSchedule.setHorizontalHeaderLabels(["Start", "Length", "Title", "Artist", "Category", "Filename", "Path" ])
    
        #self.twSchedule.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)


    def _setup_defaults(self):
        self.edtStartDate.setDate(QDate.currentDate())
        self.edtEndDate.setDate(QDate.currentDate())

        self.show_template_time_range(self._template.hours())
        self.lwHours.itemClicked.connect(self.on_hour_clicked)

    
    def show_template_time_range(self, hours: list):
        # Add items to the QListWidget for each hour in the list
        for hour in hours:
            item = QListWidgetItem(f"{hour:02d}:00")
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            item.setData(Qt.ItemDataRole.UserRole, hour)
            self.lwHours.addItem(item)

    def on_hour_clicked(self, item: QListWidgetItem):
        # Toggle the check state of the clicked item
        # if item.checkState() == Qt.CheckState.Checked:
        #     item.setCheckState(Qt.CheckState.Unchecked)
        # else:
        #     item.setCheckState(Qt.CheckState.Checked)

        self._show_selected_hours()

    def _show_selected_hours(self):
        selected_hours = []
        # Selected hours are the items that are checked
        for i in range(self.lwHours.count()):
            item = self.lwHours.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                selected_hours.append(item.data(Qt.ItemDataRole.UserRole))

        print(selected_hours)
        # Filter items from self._schedule_items based on selected hours
        for key, item in self._schedule_items.items():
            print(item)


        filtered_items = [item for item in self._schedule_items.values() if item.hour() in selected_hours]
        print(f'Filtered: {filtered_items}')
        self._populate_schedule_table(filtered_items)

    def _setup_table_widget(self):
        # Set up the table widget with 5 columns and example row count
        self.tableWidget = QTableWidget(self)
        self.tableWidget.setColumnCount(5)
        self.tableWidget.setRowCount(10)  # Example row count
        self.tableWidget.setHorizontalHeaderLabels(["Time", "Title", "Artist", "Duration", "Actions"])

    def on_generate_schedule(self):
        start_date = self.edtStartDate.date()
        end_date = self.edtEndDate.date()

        comm_breaks = self.fetch_comm_break(start_date, end_date)
        comm_break_items = self._make_comm_break_items(comm_breaks)
        template_items = list(self._template.template_items().values())

        # Remove empty items
        schedule_items = [item for item in template_items if item.item_type() != ItemType.EMPTY]
        processed_items = self._convert_category_to_track(schedule_items)
        appended_list = self._append_comm_breaks(comm_break_items, processed_items)

        self._populate_schedule_table(appended_list)
        self._cache_generated_schedule(appended_list)

        
    def _populate_schedule_table(self, processed_items: list):
        self._initialize_schedule_table()

        for i, item in enumerate(processed_items):
            row = self.twSchedule.rowCount()
            self.twSchedule.insertRow(row)
            self._add_schedule_item(item, row)

    def _cache_generated_schedule(self, items: list):
        for item in items:
            print(item.item_identifier())
            self._schedule_items[item.item_identifier()] = item
        

    def _pick_a_random_track(self, folder_id):
        tracks = dict(filter(lambda x: x[1].folder_id() == folder_id, self._tracks.items()))
        track_id = random.choice(list(tracks.keys()))
        track = tracks[track_id]
        return track


    def _convert_category_to_track(self, schedule_items):
        s_items = []
        for item in schedule_items:

            if item.item_type() != ItemType.FOLDER:
                s_items.append(item)
            else:
                track = self._pick_a_random_track(item.folder_id())
                track_item = SongItem(track.title())
                track_item.set_artist_id(track.artist_id())
                track_item.set_duration(track.duration())
                track_item.set_title(track.title())

                track_item.set_folder_name(item.folder_name())
                track_item.set_folder_id(item.folder_id())

                track_item.set_track_id(track.track_id())
                track_item.set_artist_id(track.artist_id())
                track_item.set_artist_name(track.artist_name())
                track_item.set_item_path(track.file_path())
                track_item.set_hour(item.hour())

                s_items.append(track_item)

        return s_items


    def _append_comm_breaks(self, comm_break_items: list, processed_items: list) ->list:
        appended_list = []
        for hour in self._template.hours():
            hour_comm_breaks = [comm_break for comm_break in comm_break_items if comm_break.hour() == hour]
            items = [item for item in processed_items if item.hour() == hour]
            header_item = items.pop(0)

            self._compute_hourly_start_times(items)
            mixed_items = items + hour_comm_breaks

            mixed_items.sort(key=lambda x: x.start_time())
            mixed_items.insert(0, header_item)
            appended_list += mixed_items

        return appended_list


    def _insert_commercial_breaks(self, schedule_items: list, comm_breaks: list):
        insert_locations = OrderedDict()
        prev_slot = -1

        for comm_break in comm_breaks:
            print(f"Comm Break: {comm_break.start_time().toString('hh:mm:ss')}")

            for slot, item in enumerate(schedule_items):
                if slot <= prev_slot:
                    continue

                if item.item_type() == ItemType.HEADER:
                    continue

                if item.start_time() > comm_break.start_time():

                    cbt = comm_break.start_time().toString("hh:mm:ss")

                    insert_locations[cbt] = {
                        'slot': slot-1,
                        'comm_break': comm_break
                    }
                    prev_slot = slot
                    break

        for cbt, cb in insert_locations.items():
            schedule_items.insert(cb['slot'], cb['comm_break'])
    

    def _add_schedule_item(self, s_item, row):

        item = s_item

        if s_item.item_type() not in BaseTableWidgetItem.widget_register:
            return
            

        WidgetItem = BaseTableWidgetItem.widget_register[item.item_type()]

        #twiTime = WidgetItem(item.formatted_time())
        twiTime = WidgetItem(item.start_time().toString("hh:mm:ss"))
        twiTime.setData(Qt.ItemDataRole.UserRole, item.item_identifier())
        self.twSchedule.setItem(row, 0, twiTime)

        self.twSchedule.setItem(row, 1, WidgetItem(item.formatted_duration()))
        self.twSchedule.setItem(row, 2, WidgetItem(item.title()))
        self.twSchedule.setItem(row, 3, WidgetItem(item.artist_name()))
        self.twSchedule.setItem(row, 4, WidgetItem(item.folder_name()))

        if (item.track_id() == 0):
            self.twSchedule.setItem(row, 5, WidgetItem(""))
        else:
            self.twSchedule.setItem(row, 5, WidgetItem(item.formatted_track_id()))
            
        self.twSchedule.setItem(row, 6, WidgetItem(item.item_path()))


    def _compute_start_times(self):
        for row in range(self.twSchedule.rowCount()):

            column1 = self.twSchedule.item(row, 0)
            if column1 is None:
                continue

            item_identifier = column1.data(Qt.ItemDataRole.UserRole)
            #item_id = self.twItems.item(row, 0).data(Qt.ItemDataRole.UserRole)

            #item_id = column1.data(Qt.ItemDataRole.UserRole)
            item = self._schedule_items[item_identifier]

            if item.item_type() == ItemType.EMPTY:
                continue

            if item.item_type() == ItemType.HEADER:
                prev_hr = item.hour()
                prev_start_time = QTime(prev_hr, 0, 0)
                prev_dur = item.duration()
                item.set_item_row(row)
                item.set_start_time(prev_start_time)
                continue

            start_time = prev_start_time.addMSecs(prev_dur)
            item.set_start_time(start_time)
            item.set_item_row(row)
            
            self.twSchedule.item(row, 0).setText(item.formatted_start_time())

            prev_start_time = start_time
            prev_dur = item.duration()

    def _compute_hourly_start_times(self, schedule_items: list):
        prev_dur = 0
        prev_start_time = QTime(0, 0, 0) 
        hr = -1
        for item in schedule_items:
            if hr != item.hour():
                hr = item.hour()
                prev_start_time = QTime(hr, 0, 0)
                prev_dur = item.duration()

            start_time = prev_start_time.addMSecs(prev_dur)
            item.set_start_time(start_time)

            prev_start_time = start_time
            prev_dur = item.duration()


    def fetch_comm_break(self, s_date, e_date):
        # Fetch the commercial breaks from Traffik database
        dbconn = MSSQLData(MSSQL_CONN['server'], MSSQL_CONN['database'],
                       MSSQL_CONN['username'], MSSQL_CONN['password'])

        s1 = s_date.toString('yyyy-MM-dd')
        s2 = e_date.toString('yyyy-MM-dd')
        hours = ', '.join(map(str, self._template.hours()))

        if dbconn.connect():
            sql = (f"Select ScheduleDate, ScheduleTime, ScheduleHour, BookedSpots"
                   f" from schedule  "
                   f" where scheduledate between '{s1}' and '{s2}' "
                   f" and ScheduleHour in ({hours}) "
                   f" and ItemSource = 'COMMS' "
                   f" order by ScheduleHour, ScheduleTime ")

            rows = dbconn.execute_query(sql)
            dbconn.disconnect()
            return rows
        else:
            return []

    def _make_comm_break_items(self, comm_breaks):
        breaks = []
        for comm_break in comm_breaks:
            date = comm_break[0]
            break_time = comm_break[1].strftime('%H:%M:%S')
            hour = comm_break[2]
            booked_spots = comm_break[3]

            # Create a new CommercialBreakItem instance
            title = f"{break_time} - Commercial Break ({booked_spots} spots)"
            comm_item = CommercialBreakItem(title)
            comm_item.set_hour(hour)
            comm_item.set_start_time(QTime.fromString(break_time, "HH:mm:ss"))
            comm_item.set_booked_spots(booked_spots)

            # Add the item to the table widget or any other UI element
            breaks.append(comm_item)

        return breaks

    def _append_template_items(self, template_items, schedule_items):
        for key, item in template_items.items():
            # Append each template item to the schedule items
            if item.item_type() == ItemType.EMPTY:
                continue
            schedule_items.append(item)

    def on_save_schedule(self):
       for key, item in self._schedule_items.items():
           print(f'Key: {key}:  {item}')

        



        
