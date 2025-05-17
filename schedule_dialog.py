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
    QComboBox,
    QMessageBox
)

from PyQt5.QtCore import (
    QDate,
    Qt,
    QTime,
    QSize,
    QThread,
    QCoreApplication
)

from PyQt5.QtGui import (
    QIcon,
    QPalette
)

from template import Template
from mssql_data import MSSQLData

from data_types import (
    MSSQL_CONN,
    ItemType,
    CommercialColumn
)

from template_item import (
    CommercialBreakItem,
    BaseTableWidgetItem,
    SongItem
)

from data_config import DataConfiguration

from schedule_updater import ScheduleUpdater


widget, base = uic.loadUiType('schedule_dialog.ui')

class ScheduleDialog(widget, base):
    def __init__(self, template: Template, tracks: OrderedDict):
        super(ScheduleDialog, self).__init__()
        self.setupUi(self)

        self._template = template
        self._tracks = tracks
        self._folder_tracks = {}
        self.selected_date_str = ""
        self.schedule_is_saved = False

        self._schedule_items = OrderedDict()
        self._daily_schedule = {}

        self.db_config = DataConfiguration("data/templates.db")
        self.mssql_conn = self._make_mssql_connection()

        icon = QIcon('icons/generate.png')
        self.btnGenerate.setIcon(icon)
        self.btnGenerate.setIconSize(QSize(35, 35))

        icon = QIcon('icons/save.png')
        self.btnSave.setIcon(icon)
        self.btnSave.setIconSize(QSize(35, 35))

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

        self.lblProgresText.setVisible(False)


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

        self.clear_generated_schedule()

        print("Generating schedule...")
        print(f"Cache size - BEFORE: {len(self._daily_schedule)}")

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
        print(f"Cache size - AFTER: {len(self._daily_schedule)}")

    def clear_generated_schedule(self):
        self._daily_schedule.clear()
        self._initialize_schedule_table()
        self._initialize_dates_table()
        self._setup_table_widget()

        
    def _populate_schedule_table(self, items: dict):
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
        if folder_id not in self._tracks:
            return None
        tracks = self._tracks[folder_id]
        if len(tracks) == 0:
            return None
        track_id = random.choice(list(tracks.keys()))
        track = tracks[track_id]
        if track.duration() == 0:
            return None
        return track


    def _convert_category_to_track(self, schedule_items):
        s_items = []
        for item in schedule_items:

            if item.item_type() != ItemType.FOLDER:
                s_items.append(item)
            else:

                track = self._pick_a_random_track(item.folder_id())

                # TODO: Check if track is None and handle it
                # appropriately (e.g., log a message, skip the item, etc.)
                if track is None:
                    continue

                print(f"Track: {track.title()}")

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

            mixed_items = items + hour_comm_breaks
            self._compute_hourly_start_times(mixed_items)

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

        hours = ', '.join(map(str, hrs))

        if dbconn.connect():
            sql = (f"Select Schedule.ScheduleDate, Schedule.ScheduleTime, Schedule.ScheduleHour, "
                    f"Schedule.BookedSpots,   sum(Spots.SpotBookedDuration) SpotBookedDuration "
                    f"from schedule, SpotBookings, Spots  "
                    f"where Schedule.ScheduleReference = SpotBookings.SpotBookingBreakRef "
                    f"and Spots.SpotRef = SpotBookings.SpotBookingSpot "
                    f"and scheduledate = '{s1}' "
                    f"and ScheduleHour in ({hours}) "
                    f"and ItemSource = 'COMMS' "
                    f"and SpotBookingPlayStatus <> 'CANCEL' "
                    f"Group By Schedule.ScheduleDate, Schedule.ScheduleTime, Schedule.ScheduleHour, "
                    f"Schedule.BookedSpots "
                    f"order by ScheduleHour, ScheduleTime")

            rows = dbconn.execute_query(sql)
            dbconn.disconnect()
            return rows
        else:
            return []

    def _make_comm_break_items(self, comm_breaks):
        breaks = []
        for comm_break in comm_breaks:
            date = comm_break[CommercialColumn.SCHEDULE_DATE]
            break_time = comm_break[CommercialColumn.SCHEDULE_TIME].strftime('%H:%M:%S')
            hour = comm_break[CommercialColumn.SCHEDULE_HOUR]
            booked_spots = comm_break[CommercialColumn.BOOKED_SPOTS]
            booked_duration = comm_break[CommercialColumn.BOOKED_DURATION]

            # Create a new CommercialBreakItem instance
            title = f"{break_time} - Commercial Break ({booked_spots} spot{'' if booked_spots == 1 else 's'})"

            comm_item = CommercialBreakItem(title)
            comm_item.set_hour(hour)
            comm_item.set_start_time(QTime.fromString(break_time, "HH:mm:ss"))
            comm_item.set_booked_spots(booked_spots)
            comm_item.set_booked_duration(booked_duration*1000)

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

       if self.schedule_is_saved:
           self.show_message("Schedule already saved!")
           return

       if len(self._daily_schedule) == 0:
           self.show_message("No schedule to save!")
           return

       if not self.confirm_save():
           return

       self.schedule_updater = ScheduleUpdater(self._daily_schedule)
       self.updater_thread = QThread(self)
       self.schedule_updater.moveToThread(self.updater_thread)

       # Connect updater signals
       self.schedule_updater.update_started.connect(self.schedule_update_started)
       self.schedule_updater.update_progress.connect(self.schedule_update_progress)
       self.schedule_updater.update_completed.connect(self.schedule_update_completed)

       self.updater_thread.started.connect(self.updater_thread_started)
       self.updater_thread.finished.connect(self.updater_thread.deleteLater)

       self.updater_thread.start()


    def confirm_save(self) ->bool:
        msgbox = QMessageBox(self)
        msgbox.setWindowTitle("Generate Schedule")
        msgbox.setText(f"Generate schedule will be save permanently.")
        msgbox.setInformativeText("Do you want to continue?")
        msgbox.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msgbox.setDefaultButton(QMessageBox.No)

        ret = msgbox.exec_()

        if ret == QMessageBox.Yes:
            return True
        else:
            return False

    def updater_thread_started(self):
        self.schedule_updater.exec_()

    def schedule_update_started(self):
        self.btnSave.setEnabled(False)
        self.lblProgresText.setVisible(True)
        self.lblProgresText.setText("Saving started.")
        print("Saving started.")

        QCoreApplication.processEvents()


    def schedule_update_progress(self, info_id, msg):
        if info_id == 0: # Information
            self.lblProgresText.setStyleSheet("color: black")

        if info_id == 1: # Warning
            self.lblProgresText.setStypeSheet("color: yellow")

        if info_id == 2: # Error
            self.lblProgresText.setStyleSheet("color: red")

        self.lblProgresText.setText(msg)
        QCoreApplication.processEvents()


    def schedule_update_completed(self, status: bool):
        self.btnSave.setEnabled(True)
        self.lblProgresText.setVisible(False)
        if status:
            self.lblProgresText.setText("Schedule saved successfully!")
            self.show_message("Schedule saved successfully!")
        else:
            self.lblProgresText.setText("Schedule save failed!")

    def show_message(self, message:str):
        msg = QMessageBox(self)
        msg.setText(message)
        msg.setWindowTitle("Message")
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec_()

        
