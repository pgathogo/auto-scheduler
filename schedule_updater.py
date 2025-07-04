import time
import random

from PyQt5.QtCore import (
   QObject,
   pyqtSignal,
   QDate
)

from data_config import DataConfiguration
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

    def __init__(self, daily_schedule: dict, parent=None):
        QObject.__init__(self, parent)
        self.schedule = daily_schedule
        self.db_config = DataConfiguration("")
        self.mssql_conn = self._make_mssql_connection()

    def exec_(self):
        self.update_started.emit()

        mssql_stmts  = []
        sqlite_stmts = []

        schedule_ref = self.get_schedule_ref()
        msg = f"Saving schedule reference: {schedule_ref}"
        self.update_progress.emit(0, msg)

        unique_hours_per_date = self.extract_unique_hours_per_date(self.schedule)
        
        self.remove_existing_hours(unique_hours_per_date)

        for sched_date, schedule_items in self.schedule.items():
           mssql_seq = 0
           sqlite_seq = 0

           sd = QDate.fromString(sched_date, "yyyy-MM-dd")
           sched_date_fmtd = sd.toString("dd-MM-yyyy")

           msg = f"Saving schedule for date: {sched_date_fmtd}"
           self.update_progress.emit(0, msg)

           count = 0
           for key, item in schedule_items.items():

               count += 1

               msg = f"Processing schedule for date {sched_date_fmtd}. Record {count} of {len(schedule_items)}"
               self.update_progress.emit(0, msg)

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

        msg = f"Creating data in Sedric database..."
        self.update_progress.emit(0, msg)

        # MSSQL supports multiple statment execution
        mssql_all = "".join(mssql_stmts)
        self.mssql_conn.execute_non_query(mssql_all)

        msg = f"Creating data schedule locally..."
        self.update_progress.emit(0, msg)

        # SQLite supports single statement execution
        for stmt in sqlite_stmts:
           self.db_config.execute_query(stmt)

        self.schedule_is_saved = True

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
        for date, hours in hours_per_date.items():
            hrs = list(hours.keys())

            hr_refs = self._get_schedule_ref(date, hrs)
            if len(hr_refs[date]) == 0:
                continue
            
            del_stmt_mssql = self._make_delete_statement_mssql(date, hr_refs[date])

            del_stmt_sqlite = self._make_delete_statement_sqlite(date, hr_refs[date])

            # Execute statements
            if self.mssql_conn.execute_non_query(del_stmt_mssql):
                msg = f"Deleted {len(hrs)} hours from date {date} in Sedric database"
                self.update_progress.emit(0, msg)

                if not self.db_config.execute_query(del_stmt_sqlite):
                    msg = f"Error deleting {len(hrs)} hours from date {date} in local database"
                    self.update_progress.emit(0, msg)
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


    def _make_delete_statement_mssql(self, date: str, hr_ref: list) ->str:
        refs = list(hr_ref.values())
        sched_refs = ",".join(str(r) for r in refs)

        del_stmt = (f"DELETE from Schedule "
                    f"WHERE ScheduleDate = '{date}'"
                    f" AND ScheduleLineRef in ({sched_refs});")
        return del_stmt

    def _make_delete_statement_sqlite(self, date: str, hr_refs: list) ->str:
        hrs = list(hr_refs.keys())
        hr_str = ",".join(str(h) for h in hrs)

        del_stmt = (f"DELETE from Schedule "
                    f"WHERE schedule_date = '{date}'"
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