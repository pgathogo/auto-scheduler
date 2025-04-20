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
    QHeaderView,
    QComboBox
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

from data_config import DataConfiguration


widget, base = uic.loadUiType('schedule_dialog.ui')

class ScheduleDialog(widget, base):
    def __init__(self, template: Template, tracks: OrderedDict):
        super(ScheduleDialog, self).__init__()
        self.setupUi(self)

        self._template = template
        self._tracks = tracks
        self._folder_tracks = {}
        self.selected_date_str = ""

        self._schedule_items = OrderedDict()
        self._daily_schedule = {}

        self.db_config = DataConfiguration("data/templates.db")
        self.mssql_conn = self._make_mssql_connection()

        self.btnGenerate.clicked.connect(self.on_generate_schedule)
        self.btnSave.clicked.connect(self.on_save_schedule)

        self.spMain.setSizes([200, 800])

        self._setup_defaults()
        self._initialize_schedule_table()

        self.twDates.itemClicked.connect(self.on_date_clicked)
        self.cbHours.stateChanged.connect(self.on_state_changed)
        self.cbHours.setCheckState(Qt.CheckState.Checked)
        
        self._initialize_dates_table()
        self.spVert.setSizes([300, 700])

        self.setWindowTitle(f"Template: {self._template.name()} - Days of Week: {self.dow_text(self._template.dow())}")

    def dow_text(self, dow: list) -> str:
        dow_text = {
            1: "Mon",
            2: "Tue",
            3: "Wed",
            4: "Thu",
            5: "Fri",
            6: "Sat",
            7: "Sun"
        }
        return ", ".join([dow_text[d] for d in dow])

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
    

    def _make_mssql_connection(self):
        server = MSSQL_CONN['server']
        database = MSSQL_CONN['database']
        username = MSSQL_CONN['username']  
        password = MSSQL_CONN['password']
        return MSSQLData(server, database, username, password)

    def _initialize_dates_table(self):
        self.twDates.clear()
        self.twDates.setRowCount(0)
        self.twDates.setColumnCount(2)
        self.twDates.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.twDates.setSizeAdjustPolicy(QTableWidget.AdjustToContents)
        self.twDates.setColumnWidth(0, 200)
        self.twDates.setColumnWidth(1, 200)
        self.twDates.setHorizontalHeaderLabels(["Date", "Hours"])

    def _add_date_to_table(self, date:QDate):
        row = self.twDates.rowCount()
        self.twDates.insertRow(row)

        date_item = QTableWidgetItem(self._display_date_str(date))
        date_item.setData(Qt.ItemDataRole.UserRole, self._db_date_str(date))

        self.twDates.setItem(row, 0, date_item)

        hour_widget = QComboBox(self)
        self.twDates.setCellWidget(row, 1, hour_widget)

    def on_date_clicked(self, item: QTableWidgetItem):
        date_text = item.data(Qt.ItemDataRole.UserRole)
        items = self._daily_schedule[date_text]
        if not items:
            return
        selected_hours = self._get_selected_hours()
        filtered_items = {key: item for key, item in items.items() if item.hour() in selected_hours}
        self._populate_schedule_table(filtered_items)

        self.selected_date_str = date_text

    def _display_date_str(self, date: QDate=None)-> str:
        # Return date as string of DD-MM-YYYY format for display
        if date is None:
            return QDate.currentDate().toString("dd-MM-yyyy")
        return date.toString("dd-MM-yyyy")

    def _db_date_str(self, date: QDate=None)-> str:
        # Return date as string of YYYY-MM-DD format for database storage
        if date is None:
            return QDate.currentDate().toString("yyyy-MM-dd")
        return date.toString("yyyy-MM-dd")

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

    def on_state_changed(self, state: int):
        # Check if the checkbox is checked or unchecked
        if state == Qt.CheckState.Checked:
            # Checkbox is checked, show all hours
            for i in range(self.lwHours.count()):
                item = self.lwHours.item(i)
                item.setCheckState(Qt.CheckState.Checked)
        else:
            # Checkbox is unchecked, hide all hours
            for i in range(self.lwHours.count()):
                item = self.lwHours.item(i)
                item.setCheckState(Qt.CheckState.Unchecked)
        self.on_hour_clicked(None)

    def on_hour_clicked(self, item: QListWidgetItem):
        selected_hours = self._get_selected_hours()
        self._show_selected_hours(selected_hours)

    def _get_selected_hours(self):
        selected_hours = []
        # Selected hours are the items that are checked
        for i in range(self.lwHours.count()):
            item = self.lwHours.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                selected_hours.append(item.data(Qt.ItemDataRole.UserRole))
        return selected_hours

    def _show_selected_hours(self, hours: list = []):
        schedule_items = self._daily_schedule.get(self.selected_date_str, {})
        fi = {key: item for key, item in schedule_items.items() if item.hour() in hours}
        self._populate_schedule_table(fi)

    def _setup_table_widget(self):
        # Set up the table widget with 5 columns and example row count
        self.tableWidget = QTableWidget(self)
        self.tableWidget.setColumnCount(5)
        self.tableWidget.setRowCount(10)  # Example row count
        self.tableWidget.setHorizontalHeaderLabels(["Time", "Title", "Artist", "Duration", "Actions"])

    def on_generate_schedule(self):
        start_date = self.edtStartDate.date()
        dflt_start_date = start_date
        end_date = self.edtEndDate.date()

        dow = self._template.dow()

        while start_date <= end_date:

            if start_date.dayOfWeek() not in dow:
                start_date = start_date.addDays(1)
                continue

            comm_breaks = self.fetch_comm_break(start_date, self._template.hours())
            comm_break_items = self._make_comm_break_items(comm_breaks)
            template_items = list(self._template.template_items().values())

            # Remove empty items
            schedule_items = [item for item in template_items if item.item_type() != ItemType.EMPTY]

            processed_items = self._convert_category_to_track(schedule_items)
            appended_list = self._append_comm_breaks(comm_break_items, processed_items)

            self._cache_generated_schedule(start_date, appended_list)
            self._add_date_to_table(start_date)
            start_date = start_date.addDays(1)

        sdate = self._db_date_str(dflt_start_date)
        if sdate not in self._daily_schedule:
            return
        items = self._daily_schedule[sdate]
        self._populate_schedule_table(items)

        self.selected_date_str = sdate


        
    def _populate_schedule_table(self, items: dict):
        # sdate = sched_date.toString("yyyy-MM-dd")
        # if sdate not in self._daily_schedule:
        #     return
        # processed_items = self._daily_schedule[sdate]

        self._initialize_schedule_table()

        for key, item in items.items():
            row = self.twSchedule.rowCount()
            self.twSchedule.insertRow(row)
            self._add_schedule_item(item, row)

    def _cache_generated_schedule(self, sched_date: QDate, items: list):
        schedule_items = OrderedDict()
        for item in items:
            schedule_items[item.item_identifier()] = item

        self._daily_schedule[self._db_date_str(sched_date)] = schedule_items
        

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


    def fetch_comm_break(self, s_date, hrs: list):
        # Fetch the commercial breaks from Traffik database
        dbconn = MSSQLData(MSSQL_CONN['server'], MSSQL_CONN['database'],
                       MSSQL_CONN['username'], MSSQL_CONN['password'])

        s1 = self._db_date_str(s_date)

        # e_date = s_date.toString('yyyy-MM-dd')
        # s2 = e_date.toString('yyyy-MM-dd')
        # hours = ', '.join(map(str, self._template.hours()))

        hours = ', '.join(map(str, hrs))

        if dbconn.connect():
            sql = (f"Select ScheduleDate, ScheduleTime, ScheduleHour, BookedSpots"
                   f" from schedule  "
                   f" where scheduledate = '{s1}' "
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

    def get_schedule_ref(self) -> int:
        schedule_ref_found = True
        schedule_ref = -1

        while schedule_ref_found:
            schedule_ref = "".join(map(str, random.choices(range(1000), k=12)))[0:9]
            schedule_ref_found = self.db_config.record_exists(
                f"Select schedule_ref from schedule where schedule_ref = {schedule_ref};"
            )

        return int(schedule_ref)
        
    def on_save_schedule(self):
       if len(self._daily_schedule) == 0:
           return
    
       schedule_ref = self.get_schedule_ref()

       mssql_stmts = []
       sqlite_stmts = []

       for sched_date, schedule_items in self._daily_schedule.items():
           mssql_seq = 0
           sqlite_seq = 0
           for key, item in schedule_items.items():

               if item.item_type() == ItemType.EMPTY:
                   continue

               if item.item_type() == ItemType.COMMERCIAL_BREAK:
                   continue

               if item.item_type() == ItemType.HEADER:
                   sqlite_seq += 1
                   sqlite_schedule_record = self._make_sqlite_schedule_record(sched_date, schedule_ref,  item, sqlite_seq)
                   sqlite_stmts.append(sqlite_schedule_record)
                   continue

               mssql_seq += 1
               mssql_schedule_record = self._make_mssql_schedule_record(sched_date, schedule_ref, item, mssql_seq)
               mssql_stmts.append(mssql_schedule_record)

               sqlite_seq += 1
               sqlite_schedule_record = self._make_sqlite_schedule_record(sched_date, schedule_ref,  item, sqlite_seq)
               sqlite_stmts.append(sqlite_schedule_record)


       # MSSQL supports multiple statment execution
       mssql_all = "".join(mssql_stmts)
       self.mssql_conn.execute_non_query(mssql_all)
    
       # SQLite supports single statement execution
       for stmt in sqlite_stmts:
           self.db_config.execute_query(stmt)

    def _make_mssql_schedule_record(self, sched_date: str, schedule_ref: int, item, seq: int):
        status = 'CUED'
        item_source = 'SONG'
        comm_audio = 'AUDIO'

        ins_stmt = (f" Insert into schedule (ScheduleService, ScheduleLineRef, ScheduleDate, "
                    f" ScheduleTime, ScheduleHour, ScheduleHourTime, ScheduleTrackReference, "
                    f" ScheduledFadeIn, ScheduledFadeOut, ScheduledFadeDelay, PlayStatus, "
                    f" AutoTransition, LiveTransition, ItemSource, ScheduleCommMediaType )"
                    f" VALUES ({1}, {schedule_ref}, CONVERT(DATETIME, '{sched_date}', 102), "
                    f" '{item.start_time().toString('HH:mm:ss')}', {item.hour()}, "
                    f" {seq}, {item.track_id()}, {0}, {0}, {0}, '{status}', {1}, {1}, '{item_source}', '{comm_audio}');"
                    )

        return ins_stmt

    def _make_sqlite_schedule_record(self, sched_date: str, schedule_ref: int, item, seq: int):
        ins_stmt = (f" Insert into schedule ( schedule_ref, schedule_date, template_id, start_time, "
                    f" schedule_hour, item_identifier, item_type, duration, title, artist_id, artist_name, "
                    f" folder_id, folder_name, track_id, filepath, item_row )"
                    f" VALUES ({schedule_ref}, '{sched_date}', {item.template_id()}, "
                    f" '{item.start_time().toString('HH:mm:ss')}', {item.hour()}, "
                    f" '{item.item_identifier()}', {int(item.item_type())}, {item.duration()}, "
                    f" '{item.title()}', {item.artist_id()}, '{item.artist_name()}', "
                    f" {item.folder_id()}, '{item.folder_name()}', {item.track_id()}, "
                    f" '{item.item_path()}', {seq}); ")

        return ins_stmt


        
