import time
import random

from PyQt5.QtCore import (
   QObject,
   pyqtSignal,
   QDate
)

from data_config import DataConfiguration
from logging_handlers import EventLogger
from template_item import ItemType
from mssql_data import MSSQLData
from data_types import MSSQL_CONN


class ScheduleUpdater(QObject):
    """
    Updates the database with the generated schedule
    """

    update_started = pyqtSignal()

    update_progress = pyqtSignal(int, str)

    update_completed = pyqtSignal(bool)

    INFORMATION, WARNING, ERROR = range(0, 3)

    def __init__(self, daily_schedule: dict, logger: EventLogger, parent=None):
        QObject.__init__(self, parent)
        self.schedule = daily_schedule
        self.db_config = DataConfiguration("")
        self.mssql_conn = self._make_mssql_connection()
        self._logger = logger

    def _log_info(self, msg: str):
        self._logger.log_info(msg)

    def _log_error(self, msg: str):
        self._logger.log_error(msg)

    def _batch_log(self, logs: list):
        for log in logs:
            self._log_info(log)

    def exec_(self):
        self.update_started.emit()

        mssql_stmts  = []
        sqlite_stmts = []
        logs = []

        schedule_ref = self.get_schedule_ref()
        msg = f"Saving schedule reference: {schedule_ref}"
        self.update_progress.emit(0, msg)

        unique_hours_per_date = self.extract_unique_hours_per_date(self.schedule)
        
        if not self.remove_existing_hours(unique_hours_per_date):
            return

        for sched_date, schedule_items in self.schedule.items():
           mssql_seq = 0
           sqlite_seq = 0

           sd = QDate.fromString(sched_date, "yyyy-MM-dd")
           sched_date_fmtd = sd.toString("dd-MM-yyyy")

           msg = f"Preparing schedulel to save for date: {sched_date_fmtd}"
           self.update_progress.emit(0, msg)

           count = 0
           for key, item in schedule_items.items():

               count += 1

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
               mssql_schedule_insert_stmt = self._make_mssql_insert_statement(sched_date, schedule_ref, item, mssql_seq)
               if mssql_schedule_insert_stmt == "":
                   continue

               mssql_stmts.append(mssql_schedule_insert_stmt)

               sqlite_seq += 1
               sqlite_schedule_record = self._make_sqlite_schedule_record(sched_date, schedule_ref,  item, sqlite_seq)
               sqlite_stmts.append(sqlite_schedule_record)

        msg = f"Creating data in Sedric database..."
        self.update_progress.emit(0, msg)

        msg = f"Total MSSQL statements to execute: {len(mssql_stmts)}"
        self.update_progress.emit(0, msg)

        # MSSQL supports multiple statment execution
        mssql_all = "".join(mssql_stmts)

        msg = "Executing MSSQL statements..."
        self.update_progress.emit(0, msg)

        status, msg = self.mssql_conn.execute_non_query(mssql_all)

        if not status:
            msg = f"Error creating schedule in Sedric database. {msg}"
            self.update_progress.emit(0, msg)
            # self._log_error(msg)
            self.update_completed.emit(False)
            return
        
        msg = "MSSQL statements executed successfully."
        self.update_progress.emit(0, msg)

        msg = f"Creating schedule locally..."
        self.update_progress.emit(0, msg)
        #self._log_info(msg)
        msg = f"Total SQLite statements to execute: {len(sqlite_stmts)}"  
        self.update_progress.emit(0, msg)

        # SQLite supports single statement execution
        for stmt in sqlite_stmts:
           self.db_config.execute_query(stmt)

        self.schedule_is_saved = True

        msg = "Local schedule created successfully."
        self.update_progress.emit(0, msg)

        msg = "Schedule saved successfully."
        self.update_progress.emit(0, msg)

        self.update_completed.emit(True)

    def get_schedule_ref(self) -> int:
        schedule_ref_found = True
        schedule_ref = -1

        while schedule_ref_found:
            schedule_ref = "".join(map(str, random.choices(range(1000), k=12)))[0:9]
            schedule_ref_found = self.db_config.record_exists(
                f"Select schedule_ref from schedule where schedule_ref = {schedule_ref};"
            )

        return int(schedule_ref)


    def extract_unique_hours_per_date(self, schedule: dict):
        dates = {}
        for sched_date, schedule_items in schedule.items():
            hours = {}
            for key, items in schedule_items.items():
                if items.hour() in hours:
                    hours[items.hour()] += 1
                else:
                    hours[items.hour()] = 0
            dates[sched_date] = hours
        return dates


    def remove_existing_hours(self, hours_per_date: dict) -> bool:
        dates = []
        unique_hours = set()
        for date, hours in hours_per_date.items():
            hrs = list(hours.keys())

            dates.append(date)
            unique_hours.update(hrs)

        del_stmt_mssql = self._make_delete_statement_mssql(dates, unique_hours)

        del_stmt_sqlite = self._make_delete_statement_sqlite(dates, unique_hours)

        # Execute statements
        status, msg =  self.mssql_conn.execute_non_query(del_stmt_mssql)
        if status:
            msg = f"Deleted {len(unique_hours)} hours from dates {dates} in Sedric database"
            self.update_progress.emit(0, msg)
            self._log_info(msg)

            if not self.db_config.execute_query(del_stmt_sqlite):
                msg = f"Error deleting {len(unique_hours)} hours from dates {dates} in local database"
                self.update_progress.emit(0, msg)
                self._log_error(msg)
                return False

        return True


    def _get_schedule_ref(self, date: str, hrs: list) -> dict:
        # Fetch data from sqlite table schedule and retun a dict of
        # {date: {hour: schedule_ref}}
        sql = (f"SELECT schedule_ref, schedule_hour "
               f"FROM schedule WHERE schedule_date = '{date}' "
               f" AND schedule_hour in ({','.join(str(h) for h in hrs)});" )
        
        SCHED_REF = 0
        SCHED_HOUR = 1

        rows = self.db_config.fetch_data(sql)

        if not rows:
            return {date: {}}

        schedule_ref = {}

        for row in rows:
            if row[SCHED_HOUR] not in schedule_ref:
                schedule_ref[row[SCHED_HOUR]] = row[SCHED_REF]
            else:
                continue
        return {date: schedule_ref}


    def _make_delete_statement_mssql(self, dates: list, hours: set) ->str:
        date_str = ",".join(f"'{d}'" for d in dates)
        hours_str = ",".join(str(h) for h in hours)

        del_stmt = (f"DELETE from Schedule "
                    f"WHERE ItemSource = 'SONG'"
                    f" AND PlayStatus = 'CUED'"
                    f" AND ScheduleDate in ({date_str})"
                    f" AND ScheduleHour in ({hours_str});")
        return del_stmt

    def _make_delete_statement_sqlite(self, dates: list, hours: list) ->str:
        date_str = ",".join(f"'{d}'" for d in dates)
        hr_str = ",".join(str(h) for h in hours)

        del_stmt = (f"DELETE from Schedule "
                    f"WHERE schedule_date in ({date_str})"
                    f" AND Schedule_hour in ({hr_str});")
        return del_stmt

    def _make_mssql_connection(self):
        server = MSSQL_CONN['server']
        database = MSSQL_CONN['database']
        username = MSSQL_CONN['username']  
        password = MSSQL_CONN['password']
        return MSSQLData(server, database, username, password)

    def _make_sqlite_schedule_record(self, sched_date: str, schedule_ref: int, item, seq: int):
        st = item.start_time().toString('HH:mm:ss')

        ins_stmt = (f' Insert into schedule ( schedule_ref, schedule_date, template_id, start_time, '
                    f' schedule_hour, item_identifier, item_type, duration, title, artist_id, artist_name, '
                    f' folder_id, folder_name, track_id, filepath, item_row )'
                    f' VALUES ({schedule_ref}, "{sched_date}", {item.template_id()}, '
                    f' "{st}", {item.hour()}, '
                    f' "{item.item_identifier()}", {int(item.item_type())}, {item.duration()}, '
                    f' "{item.title()}", {item.artist_id()}, "{item.artist_name()}", '
                    f'  {item.folder_id()}, "{item.folder_name()}", {item.track_id()}, '
                    f' "{item.item_path()}", {seq}); ')

        return ins_stmt

    def _make_mssql_insert_statement(self, sched_date: str, schedule_ref: int, item, seq: int):
        status = 'CUED'
        item_source = 'SONG'
        comm_audio = 'AUDIO'

        start_time = item.start_time()
        if start_time is None:
            return ""

        ins_stmt = (f" Insert into schedule (ScheduleService, ScheduleLineRef, ScheduleDate, "
                    f" ScheduleTime, ScheduleHour, ScheduleHourTime, ScheduleTrackReference, "
                    f" ScheduledFadeIn, ScheduledFadeOut, ScheduledFadeDelay, PlayStatus, "
                    f" AutoTransition, LiveTransition, ItemSource, ScheduleCommMediaType )"
                    f" VALUES ({1}, {schedule_ref}, CONVERT(DATETIME, '{sched_date}', 102), "
                    f" '{start_time.toString('HH:mm:ss')}', {item.hour()}, "
                    f" {seq}, {item.track_id()}, {0}, {0}, {0}, '{status}', {1}, {1}, '{item_source}', '{comm_audio}');"
                    )

        return ins_stmt
