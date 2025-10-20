from PyQt5.QtCore import (
    QObject,
    pyqtSignal,
    QThread
)

from mssql_data import MSSQLData
from data_types import MSSQL_CONN


class ScheduleValidator(QObject):

    update_started = pyqtSignal()
    update_progress = pyqtSignal(int, str)
    update_completed = pyqtSignal(bool, str)

    INFORMATION, WARNING, ERROR = range(3)

    def __init__(self, current_template, dates, parent=None):
        QObject.__init__(self, parent)
        self.schedule = {}
        self.current_template = current_template
        self.dates = dates

    def fetch_data(self):
        dbconn =  MSSQLData(
            MSSQL_CONN['server'], 
            MSSQL_CONN['database'], 
            MSSQL_CONN['username'], 
            MSSQL_CONN['password'])

        if dbconn.connect():
            hours = ', '.join(map(str, self.current_template.hours()))
            dates = ', '.join([f"'{date.toString('yyyy-MM-dd')}'" for date in self.dates])
            query = self._make_query(self.current_template.hours(), dates)

            self.update_started.emit()
            msg =  f"Fetching schedule data for dates: {dates} and hours: {hours}"
            self.update_progress.emit(0, msg)

            results = dbconn.execute_query(query)

            if results is None:
                dbconn.disconnect()
                self.update_completed.emit(False, "Error: Query did not return any results.")
                return

            for row in results:
                sched_date = row[0].strftime("%Y-%m-%d")
                self.update_progress.emit(ScheduleValidator.INFORMATION,
                                           f"Processing schedule for date: {sched_date}")
                for col, hour in enumerate(self.current_template.hours()):
                    h = {hour: row[col+1]}
                    if sched_date not in self.schedule:
                        self.schedule[sched_date] = {}
                    self.schedule[sched_date][hour] = row[col+1]

            dbconn.disconnect()

        msg = f"Fetched {len(self.schedule)} schedule dates."                                                                                       
        self.update_completed.emit(True, msg)
        # return self.schedule

    def _make_query(self, hours: list[int], dates: str) -> str:
        # Build the CASE statements
        case_statements = [
            f"SUM(CASE WHEN ScheduleHour = {hour} THEN 1 ELSE 0 END) AS \"{hour}\""
            for hour in hours
        ]

        # Build the IN clause
        hour_list = ','.join(map(str, hours))

        # Construct the full query
        query = f"""
        SELECT 
            ScheduleDate,
            {', '.join(case_statements)},
            COUNT(*) AS Total
        FROM Schedule
        WHERE ScheduleDate IN ({dates})
            AND ScheduleHour IN ({hour_list})
            AND ItemSource <> 'COMMS'
        GROUP BY ScheduleDate
        ORDER BY ScheduleDate
        """

        return query

    def clear_schedule(self):
        self.schedule = {}

    def get_schedule(self):
        return self.schedule

    def insert_data(self, statements: dict):
        dbconn =  MSSQLData(
            MSSQL_CONN['server'], 
            MSSQL_CONN['database'], 
            MSSQL_CONN['username'], 
            MSSQL_CONN['password'])

        if dbconn.connect():
            for date, stmts in statements.items():
                mssql_inserts = "".join(stmts)
                dbconn.execute_non_query(mssql_inserts)
            dbconn.disconnect()
