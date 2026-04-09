import os
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
    QDateTime,
    QSize,
    QThread,
    QCoreApplication
)

from PyQt5.QtGui import (
    QIcon,
    QPalette,
    QPixmap
)

from template import Template
from mssql_data import MSSQLData


from data_types import (
    MSSQL_CONN,
    ItemType,
    CommercialColumn,
    DBAction
)

from template_item import (
    CommercialBreakItem,
    BaseTableWidgetItem,
    SongItem,
    FolderItem
)

from data_config import DataConfiguration
from schedule_updater import ScheduleUpdater
from schedule_summary import ScheduleSummaryDialog

from logging_handlers import (
    EventLogger, 
    FileHandler, 
    StdOutHandler
)

GENRE_ROTATION = {"N": "NONE", "R": "RANDOM"}

widget, base = uic.loadUiType('schedule_dialog.ui')

WAITING = 0
GENERATED = 1
SAVING = 2
SAVED = 3

class ScheduleDialog(widget, base):
    def __init__(self, template: Template, tracks: OrderedDict, folders: dict):
        super(ScheduleDialog, self).__init__()
        self.setupUi(self)

        self._template = template
        self._tracks = tracks
        self._folder_tracks = {}
        self.selected_date_str = ""
        self.schedule_is_saved = False

        self._folders = folders

        self._schedule_items = OrderedDict()
        self._daily_schedule = {}

        # self.db_config = DataConfiguration("")
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

        self.setWindowTitle(f"Create Schedule for Template: {self._template.name()} - Days of Week: {self.dow_text(self._template.dow())}")

        self.lblProgresText.setVisible(False)

        self._logger = self._make_logger()

        self.updater_thread = QThread(self)
        self.schedule_current_status = WAITING
        self.schedule_status(WAITING)


    def _make_logger(self) -> EventLogger:
        dtime = QDateTime.currentDateTime().toString('ddMMyyyy_HHmm')
        logfile = f"schedule_log_{dtime}.log"
        # First check if logs directory exists, if not create it
        if not os.path.exists("logs"):
            os.makedirs("logs")
        FileHandler.set_filepath(f"logs/{logfile}")
        return EventLogger(handler=FileHandler)

    def _log_info(self, msg: str):
        self._logger.log_info(msg)

    def _log_error(self, msg: str):
        self._logger.log_error(msg)

    def schedule_status(self, status:int):
        if status == WAITING:
            self.status_waiting()
        elif status == GENERATED:
            self.status_generated()
            self.schedule_current_status = GENERATED
        elif status == SAVING:
            self.status_saving()
            self.schedule_current_status = SAVING
        elif status == SAVED:
            self.status_saved()
            self.schedule_current_status = SAVED
        else:
            pass

    def status_waiting(self):
        self.lblStatus.setText("WAITING...")
        pixmap = QPixmap("icons/yellow.png")
        self.lblStatusImg.setPixmap(pixmap)

    def status_generated(self):
        self.lblStatus.setText("SCHEDULE GENERATED")
        pixmap = QPixmap("icons/red.png")
        self.lblStatusImg.setPixmap(pixmap)

    def status_saving(self):
        self.lblStatus.setText("SAVING SCHEDULE - Please wait...")
        pixmap = QPixmap("icons/warning_triangle.png")
        self.lblStatusImg.setPixmap(pixmap)

    def status_saved(self):
        self.lblStatus.setText("SCHEDULE SAVED.")
        pixmap = QPixmap("icons/green_2.png")
        self.lblStatusImg.setPixmap(pixmap)

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
        self.twDates.setColumnCount(1)
        self.twDates.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.twDates.setSizeAdjustPolicy(QTableWidget.AdjustToContents)
        self.twDates.setColumnWidth(0, 200)
        self.twDates.setHorizontalHeaderLabels(["Date"])

    def _add_date_to_table(self, date:QDate):
        row = self.twDates.rowCount()
        self.twDates.insertRow(row)

        date_item = QTableWidgetItem(self._display_date_str(date))
        date_item.setData(Qt.ItemDataRole.UserRole, self._db_date_str(date))

        self.twDates.setItem(row, 0, date_item)

    def on_date_clicked(self, item: QTableWidgetItem):
        date_text = item.data(Qt.ItemDataRole.UserRole)
        items = self._daily_schedule[date_text]
        if not items:
            return
        selected_hours = self._get_selected_hours()
        filtered_items = {key: item for key, item in items.items() if item.hour() in selected_hours}
        self._populate_schedule_table(filtered_items)

        self.selected_date_str = date_text
        self.compute_total_time_per_hour(date_text)

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
        self.twHours.itemClicked.connect(self.on_hour_clicked)

    def show_template_time_range(self, hours: list):
        # Add column headers
        self.twHours.clear()
        self.twHours.setRowCount(0)
        self.twHours.setColumnCount(2)
        self.twHours.setSizeAdjustPolicy(QTableWidget.AdjustToContents)
        self.twHours.setHorizontalHeaderLabels(["Hour", "Total Time"])
        self.twHours.itemChanged.connect(self.on_hour_clicked)

        # Add items to the QListWidget for each hour in the list
        for hour in hours:
            row = self.twHours.rowCount()
            self.twHours.insertRow(row)

            item = QTableWidgetItem(f"{hour:02d}:00")
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            item.setData(Qt.ItemDataRole.UserRole, hour)
            self.twHours.setItem(row, 0, item)

            # Column for total time
            item = QTableWidgetItem("00:00:00")
            self.twHours.setItem(row, 1, item)

    
    def show_template_time_range2(self, hours: list):
        # Add items to the QListWidget for each hour in the list
        for hour in hours:
            item = QListWidgetItem(f"{hour:02d}:00")
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            item.setData(Qt.ItemDataRole.UserRole, hour)
            #self.lwHours.addItem(item)

    def on_state_changed(self, state: int):
        # Check if the checkbox is checked or unchecked
        if state == Qt.CheckState.Checked:
            # Checkbox is checked, show all hours
            for i in range(self.twHours.rowCount()):
                item = self.twHours.item(i, 0)
                item.setCheckState(Qt.CheckState.Checked)
        else:
            # Checkbox is unchecked, hide all hours
            for i in range(self.twHours.rowCount()):
                item = self.twHours.item(i, 0)
                item.setCheckState(Qt.CheckState.Unchecked)
        self.on_hour_clicked(None)

    def on_hour_clicked(self, item: QTableWidgetItem):
        selected_hours = self._get_selected_hours()
        self._show_selected_hours(selected_hours)
        if item is not None:
            if item.checkState() == Qt.CheckState.Checked:
                self.twHours.selectRow(item.row())
            else:
                self.twHours.clearSelection()

    def _get_selected_hours(self) ->list[int]:
        selected_hours = []
        # Selected hours are the items that are checked
        for row in range(self.twHours.rowCount()):
            item = self.twHours.item(row, 0)
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
        current_datetime = QDateTime.currentDateTime().toString('dd-MM-yyyy HH:mm')
        self._log_info(f"Start schedule generation process at: {current_datetime}")

        msg = f"Generating schedule for template: `{self._template.name()}`..."
        self._log_info(msg)

        self.clear_generated_schedule()

        start_date = self.edtStartDate.date()
        dflt_start_date = start_date
        end_date = self.edtEndDate.date()

        self._log_info(f"Selected date range: from {self._display_date_str(start_date)} to {self._display_date_str(end_date)}" )

        selected_hours = self._get_selected_hours()

        log_hours = ', '.join(map(str, selected_hours))
        msg = f"Selected hour(s): {log_hours}"
        self._log_info(msg)

        dow = self._template.dow()

        while start_date <= end_date:

            self._log_info(f"Processing date: {self._display_date_str(start_date)}")

            if start_date.dayOfWeek() not in dow:
                start_date = start_date.addDays(1)
                self._log_info(f"Skipping date {self._display_date_str(start_date)} as it is not in template day of week.")
                continue

            str_start_date = self._display_date_str(start_date)
            self._log_info(f"Creating schedule for date: `{str_start_date}`")

            self._log_info(f"Fetching commercaial breaks for date: {str_start_date}")

            for hr in selected_hours:
                generated_list = self._generate_schedule_for_hour(start_date, hr)

                self._cache_generated_schedule(start_date, generated_list)

                self._log_info(f"Schedule generated for date: {self._display_date_str(start_date)} Hour {hr}, Items generated: {len(generated_list)}")
                
            self._add_date_to_table(start_date)
            start_date = start_date.addDays(1)

        sdate = self._db_date_str(dflt_start_date)
        if sdate not in self._daily_schedule:
            return

        items = self._daily_schedule[sdate]
        self._populate_schedule_table(items)

        self.selected_date_str = sdate

        if len(self._daily_schedule) > 0:
            # Click the first date by default
            first_date_item = self.twDates.item(0, 0)
            self.twDates.setCurrentItem(first_date_item)
            self.on_date_clicked(first_date_item)

        self.schedule_status(GENERATED)

    def clear_generated_schedule(self):
        self._daily_schedule.clear()
        self._initialize_schedule_table()
        self._initialize_dates_table()
        self._setup_table_widget()
        
    def compute_total_time_per_hour(self, date_str: str):
        hour_totals = {hour: 0 for hour in self._template.hours()}

        date_schedule = self._daily_schedule.get(date_str, {})
        if not date_schedule:
            return

        for key, item in date_schedule.items():
            hour = item.hour()
            hour_totals[hour] += item.duration()

        for row in range(self.twHours.rowCount()):
            item = self.twHours.item(row, 0)
            hour = item.data(Qt.ItemDataRole.UserRole)
            total_duration = hour_totals.get(hour, 0)

            time = QTime(hour, 0, 0)
            time_duration = time.addMSecs(total_duration).toString("hh:mm:ss")

            total_item = self.twHours.item(row, 1)
            total_item.setText(time_duration)

    def _populate_schedule_table(self, items: dict):
        self._initialize_schedule_table()

        for key, item in items.items():
            status = self._add_schedule_item(item)
            if not status:
                self._log_error(f"Failed to add schedule item: {item.title()} Time {item.start_time()}")

    def _cache_generated_schedule(self, sched_date: QDate, items: list):
        schedule_items = OrderedDict()
        for item in items:
            schedule_items[item.item_identifier()] = item

        if self._db_date_str(sched_date) not in self._daily_schedule:
            self._daily_schedule[self._db_date_str(sched_date)] = schedule_items
        else:
            self._daily_schedule[self._db_date_str(sched_date)].update(schedule_items)

    def _pick_a_random_track(self, folder_id) -> "Track":
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

    def _pick_a_random_track_by_genre(self, item:"TemplateItem") -> "SongItem":
        # Same folder for now
        if item.genre() == -1:
            return item

        tracks = self._tracks[item.folder_id()]

        tracks_same_genre = [track for track in tracks.values() if track.genre() == item.genre()]
        if len(tracks_same_genre) == 0:
            print(f"No tracks found for genre {item.genre()} in folder {item.folder_id()}")
            return item

        track = random.choice(tracks_same_genre)
        if track.duration() == 0:
            print(f"Track {track.title()} has zero duration, skipping.")
            return item

        song_item = self._make_song_item_from_track(track, item)
        return song_item
        

    def _convert_category_to_track(self, schedule_items, template_id: int) -> list:
        s_items = []

        for item in schedule_items:

            if item.item_type() != ItemType.FOLDER:
                # Track - Check rotation based
                if item.item_type() == ItemType.SONG and item.rotation() == "R":
                    track = self._pick_a_random_track_by_genre(item)
                    track.set_template_id(template_id)
                    s_items.append(track)
                else:
                    s_items.append(item)
            else:

                track = self._pick_a_random_track(item.folder_id())

                # TODO: Check if track is None and handle it
                # appropriately (e.g., log a message, skip the item, etc.)
                if track is None:
                    continue

                song_item = self._make_song_item_from_track(track, item)
                song_item.set_template_id(template_id)

                s_items.append(song_item)

        return s_items

    def _generate_schedule_for_hour(self, sched_date: QDate, hour: int) -> list:
        self._log_info(f"Generate schedule for hour: {hour:02d}:00")

        comm_breaks = self.fetch_comm_break(sched_date, hour)

        self._log_info(f"Total commercial breaks found for hour {hour} - {len(comm_breaks)}")

        comm_break_items = self._make_comm_break_items(comm_breaks)

        schedule_items = [item for item in self._template.template_items().values() if item.item_type() != ItemType.EMPTY
                            and item.db_action() != DBAction.DELETE and item.hour() == hour]

        # Maintain the order of items in the template based on how they were inserted
        schedule_items.sort(key=lambda item: item.item_row())

        processed_items = self._convert_category_to_track(schedule_items,self._template.id())

        appended_list = self._append_comm_breaks(comm_break_items, processed_items)

        self._compute_st(appended_list)

        ONE_HOUR_MS = 3600000

        total_duration = sum([item.duration() for item in appended_list if item.hour() == hour])
        if total_duration > ONE_HOUR_MS:
            self._generate_schedule_for_hour(sched_date, hour)

        appended_list = self._tight_fit_hour(hour, appended_list)

        self._compute_st(appended_list)

        # Compute total duration of the appended_list so far
        total_duration = sum([item.duration() for item in appended_list if item.hour() == hour])
        total_time = QTime(hour, 0, 0).addMSecs(total_duration).toString("hh:mm:ss")

        if total_duration > ONE_HOUR_MS:
            msg = f"Total duration for hour {hour} exceeds 1 hour: {total_duration} ms. Retrying generation..."
            self._log_error(msg)
            # Recursively call to regenerate the hour
            appended_list = self._generate_schedule_for_hour(sched_date, hour)

        return appended_list


    def _tight_fit_hour(self, hr: int, schedule_items: list) -> list:
        # Get folder categories from the current template
        folder_items = [item for item in self._template.template_items().values() if item.item_type() == ItemType.FOLDER]

        # Pick a random folder item
        if len(folder_items) == 0:
            return []
        
        # We get the total duration of items in the hour
        hour_total_duration = 0
        ONE_HOUR_MS = 3600000

        for item in schedule_items:
           hour_total_duration += item.duration()

        if hour_total_duration >= ONE_HOUR_MS:
            return schedule_items

        htd = QTime(hr, 0, 0).addMSecs(hour_total_duration).toString("hh:mm:ss")

        last_start_time = schedule_items[-1].start_time()
        last_start_time = last_start_time.addMSecs(schedule_items[-1].duration())

        existing_track_ids = [item.track_id() for item in schedule_items]

        folder_search_index = 0
        SMALL_DURATION_MS = 30000  # 30 seconds

        # If total duration is less than 3600000 ms (1 hour), we need to fill the hour
        while hour_total_duration < ONE_HOUR_MS:
            folder_item = random.choice(folder_items)

            diff_duration = ONE_HOUR_MS - hour_total_duration

            if diff_duration <= SMALL_DURATION_MS and self._template.filler_folder() != -1:
                # Look for small track in filler folder
                track = self._find_track_within_duration_filer_folder(self._template.filler_folder(), diff_duration, existing_track_ids)
                if track is None:
                    break

                # Find folder from folder_items with ID of filler folder
                folder_item = FolderItem(self._folders[self._template.filler_folder()])
                folder_item.set_folder_id(self._template.filler_folder())
                folder_item.set_folder_name(self._folders[self._template.filler_folder()])
                folder_item.set_hour(hr)
            else:
                track = self._find_track_within_duration(folder_item.folder_id(), diff_duration, existing_track_ids)

            if track is None:
                folder_search_index += 1
                if folder_search_index >= len(folder_items):
                    break
                else:
                    continue

            # Check if adding this song exceeds the hour
            htd = hour_total_duration + track.duration()
            if htd > ONE_HOUR_MS:
                folder_search_index += 1
                if folder_search_index >= len(folder_items):
                    break
                continue

            song_item = self._make_song_item_from_track(track, folder_item)
            song_item.set_start_time(last_start_time.addMSecs(track.duration()))

            last_start_time = song_item.start_time()
            # Check if song already exists in the hour
            if song_item.track_id() in existing_track_ids:
                continue
                
            td = QTime(hr, 0, 0).addMSecs(hour_total_duration + track.duration()).toString("hh:mm:ss")

            song_item.set_template_id(self._template.id())
            song_item.set_hour(hr)
            schedule_items.append(song_item)

            existing_track_ids.append(song_item.track_id())

            hour_total_duration += song_item.duration()

        return schedule_items

    def _compute_st(self, schedule_items: list):
        # Group items by hour and compute start times within each hour and update schedule_items
        hourly_groups = {}
        for item in schedule_items:
            hr = item.hour()
            if hr not in hourly_groups:
                hourly_groups[hr] = []
            hourly_groups[hr].append(item)

        # Compute start times for each hour's items
        for hr, items in hourly_groups.items():
            if len(items) == 0:
                continue
            start_time = QTime(hr, 0, 0)
            for item in items:
                item.set_start_time(start_time)
                start_time = start_time.addMSecs(item.duration())
            # Update the schedule_items with the computed start times
            for item in items:
                schedule_items[schedule_items.index(item)] = item

    def _find_track_within_duration_filer_folder(self, folder_id: int, max_duration: int, exclude_track_ids: list) -> "Track":
        if folder_id not in self._tracks:
            return None

        tracks = self._tracks[folder_id]

        # Within the filer folder, find tracks associated with the current template that have duration less than or equal to the max_duration and not in the exclude_track_ids list return a dict
        filtered_tracks, tracks = self._filter_tracks_linked_to_template(self._template.id(), tracks)

        suitable_tracks = []

        if len(filtered_tracks) > 0:
            suitable_tracks = [track for track in filtered_tracks.values() if track.duration() <= max_duration and track.track_id() not in exclude_track_ids]
            if len(suitable_tracks) == 0:
                return None

            if len(suitable_tracks) == 0:
                # Check if you can find any track in the entire folder that is not linked to any template and has duration less than or equal to the max_duration and not in the exclude_track_ids list
                suitable_tracks = [track for track in tracks.values() if track.duration() <= max_duration and track.track_id() not in exclude_track_ids]
                if len(suitable_tracks) == 0:
                    return None
        else:
            suitable_tracks = [track for track in tracks.values() if track.duration() <= max_duration and track.track_id() not in exclude_track_ids]
            if len(suitable_tracks) == 0:
                return None

        track = random.choice(suitable_tracks)
        return track

    def _find_track_within_duration(self, folder_id: int, max_duration: int, exclude_track_ids: list) -> "Track":
        if folder_id not in self._tracks:
            return None

        tracks = self._tracks[folder_id]

        suitable_tracks = [track for track in tracks.values() if track.duration() <= max_duration and track.track_id() not in exclude_track_ids]
        if len(suitable_tracks) == 0:
            return None
        track = random.choice(suitable_tracks)
        return track

    def _filter_tracks_linked_to_template(self, template_id: int, tracks: dict) -> tuple[dict, dict]:
        # Track is linked to template in member using field show, that contains comma separated template IDs. If the field is empty, it means the track is linked to all templates. If the field contains the current template ID, it means the track is linked to the current template.
        all_tracks = {}
        filtered_tracks = {}
        for track_id, track in tracks.items():
            show_field = track.show()
            if show_field == "" or show_field is None:
                all_tracks[track_id] = track
            else:   
                show_template_ids = [int(tid.strip()) for tid in show_field.split(",")]
                if template_id in show_template_ids:
                    filtered_tracks[track_id] = track

        return filtered_tracks, all_tracks
    

    def _make_song_item_from_track(self, track: "Track", item: "TemplateItem") -> "SongItem":
        song_item = SongItem(track.title())
        song_item.set_artist_id(track.artist_id())
        song_item.set_duration(track.duration())
        song_item.set_title(track.title())
        song_item.set_track_id(track.track_id())
        song_item.set_artist_name(track.artist_name())
        song_item.set_item_path(track.file_path())

        song_item.set_folder_name(item.folder_name())
        song_item.set_folder_id(item.folder_id())
        song_item.set_hour(item.hour())
        song_item.set_start_time(item.start_time())

        return song_item


    def _append_comm_breaks(self, comm_break_items: list, processed_items: list) ->list:
        appended_list = []
        for hour in self._template.hours():

            hour_comm_breaks = [comm_break for comm_break in comm_break_items if comm_break.hour() == hour]

            items = []
            for item in processed_items:
                if item.start_time() is None:
                    continue
                if item.hour() == hour and item.start_time().toString("hh:mm:ss") != "":
                    items.append(item)

            if len(items) > 0:
                header_item = items.pop(0)

                mixed_items = items + hour_comm_breaks
                
                mixed_items.sort(key=lambda x: x.start_time())

                #self._compute_hourly_start_times(mixed_items)
                self._clip_overflow_times(mixed_items)
                clean_items = [item for item in mixed_items if item.start_time() != None ]

                #mixed_items.insert(0, header_item)
                #appended_list += mixed_items
                clean_items.insert(0, header_item)
                appended_list += clean_items

        return appended_list


    def _print_mixed_items(self, items):
        for item in items:
            print(f"{item.start_time()} {item.start_time().toString('hh:mm:ss')} - {item.title()}")

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
    

    def _add_schedule_item(self, s_item) ->bool:
        item = s_item

        if item.start_time() is None:
            return False

        if s_item.item_type() not in BaseTableWidgetItem.widget_register:
            return False

        row = self.twSchedule.rowCount()
        self.twSchedule.insertRow(row)

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
        return True


    def _compute_start_timesX(self):
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

    def _clip_overflow_times(self, schedule_items: list):
        hr = -1
        for idx, item in enumerate(schedule_items):
            if hr != item.hour():
                hr = item.hour()
            if item.start_time().hour() > hr:   
                item.set_start_time(None)

                
    def _compute_hourly_start_times(self, schedule_items: list):
        prev_start_time = None
        hr = -1
        for idx, item in enumerate(schedule_items):
            if hr != item.hour():
                hr = item.hour()
                prev_start_time = QTime(hr, 0, 0)
                item.set_start_time(prev_start_time)
            else:
                # Add previous item's duration to previous item's start time
                prev_item = schedule_items[idx - 1]
                if prev_item.start_time() != None:
                    prev_start_time = prev_item.start_time().addMSecs(prev_item.duration())
                    item.set_start_time(prev_start_time)
                # else:
                #     item.set_start_time(None)
                #     continue

            # Check and clip items that exceed their hour
            if item.start_time().hour() > hr:   #item.hour():
                item.set_start_time(None)


    def fetch_comm_break(self, s_date, hr: int) ->list:
        # Fetch the commercial breaks from Traffik database
        dbconn = MSSQLData(MSSQL_CONN['server'], MSSQL_CONN['database'],
                       MSSQL_CONN['username'], MSSQL_CONN['password'])

        s1 = self._db_date_str(s_date)

        # hours = ', '.join(map(str, hrs))

        if dbconn.connect():
            sql = (f"Select Schedule.ScheduleDate, Schedule.ScheduleTime, Schedule.ScheduleHour, "
                    f"Schedule.BookedSpots,   sum(Spots.SpotBookedDuration) SpotBookedDuration "
                    f"from schedule, SpotBookings, Spots  "
                    f"where Schedule.ScheduleReference = SpotBookings.SpotBookingBreakRef "
                    f"and Spots.SpotRef = SpotBookings.SpotBookingSpot "
                    f"and scheduledate = '{s1}' "
                    f"and ScheduleHour = {hr} "
                    f"and ItemSource = 'COMMS' "
                    f"and SpotBookingPlayStatus <> 'CANCEL' "
                    f"Group By Schedule.ScheduleDate, Schedule.ScheduleTime, Schedule.ScheduleHour, "
                    f"Schedule.BookedSpots "
                    f"order by ScheduleHour, ScheduleTime")

            rows = dbconn.execute_query(sql)
            dbconn.disconnect()
            return rows

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
            # schedule_ref_found = self.db_config.record_exists(
            #     f"Select schedule_ref from schedule where schedule_ref = {schedule_ref};"
            # )

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

       self.schedule_status(SAVING)

       current_datetime = QDateTime.currentDateTime().toString('dd-MM-yyyy HH:mm')
       self._log_info(f"Saving procedure started. Time: {current_datetime}")
       self._log_info(f"Saving schedule for template: `{self._template.name()}`")

       self.schedule_updater = ScheduleUpdater(self._daily_schedule, self._logger)
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
        msgbox.setText(f"Generate schedule will be saved permanently.\n Any existing schedules will be overwritten.")
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
        self.btnGenerate.setEnabled(False)
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

        self._log_info(msg)

        QCoreApplication.processEvents()


    def schedule_update_completed(self, status: bool):
        self.btnGenerate.setEnabled(True)
        self.btnSave.setEnabled(True)
        self.lblProgresText.setVisible(False)
        if status:
            self.lblProgresText.setText("Schedule saved successfully!")
            self.show_message("Schedule saved successfully. See summary window for details.")
        else:
            self.lblProgresText.setText("Schedule save failed!")

        self.schedule_status(SAVED)
        start_date = self.edtStartDate.date()
        end_date = self.edtEndDate.date()
        date_range = self._get_date_range(start_date, end_date)
        # scheduled_items = self.db_config.fetch_schedule_by_template_and_date_range(self._template.id(), 
        #                                                                            start_date, end_date)
        scheduled_items = self.mssql_conn.fetch_schedule_by_template_and_date_range(self._template.id(), 
                                                                                    start_date, end_date)

        # Remove dates in the date_range that are not in the template's DOW
        date_range = [date for date in date_range if date.dayOfWeek() in self._template.dow()]

        summary = ScheduleSummaryDialog(
            current_template=self._template, 
            dates=date_range, 
            schedule_items=scheduled_items, 
            run_immediately=True, 
            logger=self._logger,
            parent=self
        )
        summary.exec_()

    def _get_date_range(self, start_date, end_date):
        dates = []
        while start_date <= end_date:
            dates.append(start_date)
            start_date = start_date.addDays(1)
        return dates

    def show_message(self, message:str):
        msg = QMessageBox(self)
        msg.setText(message)
        msg.setWindowTitle("Message")
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec_()

    def closeEvent(self, event):
        if (self.schedule_current_status == GENERATED):
            if not self.close_without_saving():
                event.ignore()
                return
        self.updater_thread.quit()
        self.updater_thread.wait()
        event.accept()

    def close_without_saving(self) ->bool:
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Confirmation")
        msg_box.setText("Are you sure you want to close without saving the schedule?")
        # msg_box.setInformativeText("Do you want to close without saving schedule?")
        msg_box.setStandardButtons(QMessageBox.Yes|QMessageBox.No)
        msg_box.setDefaultButton(QMessageBox.No)

        ret = msg_box.exec_()

        return True if ret == QMessageBox.Yes else False

