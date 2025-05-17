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
        self.db_config = DataConfiguration("data/templates.db")
        self.mssql_conn = self._make_mssql_connection()

    def exec_(self):
        self.update_started.emit()

        mssql_stmts  = []
        sqlite_stmts = []

        schedule_ref = self.get_schedule_ref()
        msg = f"Saving schedule reference: {schedule_ref}"
        self.update_progress.emit(0, msg)

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

    def _make_mssql_connection(self):
        server = MSSQL_CONN['server']
        database = MSSQL_CONN['database']
        username = MSSQL_CONN['username']  
        password = MSSQL_CONN['password']
        return MSSQLData(server, database, username, password)

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