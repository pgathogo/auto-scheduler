from collections import Counter

from PyQt5.QtWidgets import (
    QApplication,
    QTableWidget,
    QTableWidgetItem,
    QMessageBox
)

from PyQt5 import uic

from PyQt5.QtCore import (
    Qt,
    QThread
)

from mssql_data import MSSQLData
from data_config import DataConfiguration

from data_types import (
    MSSQL_CONN
)

from schedule_validator import ScheduleValidator


widget, base = uic.loadUiType('schedule_summary.ui')

class ScheduleSummaryDialog(widget, base):
    def __init__(self, current_template:'Template', dates:list, schedule_items:list, parent=None):
        super(ScheduleSummaryDialog, self).__init__(parent)
        self.setupUi(self)

        self.current_template = current_template
        self.dates = dates
        self.schedule_items = schedule_items

        # ---- thread
        self.schedule_validator = ScheduleValidator(self.current_template, self.dates)
        self.schedule_validator.update_started.connect(self.on_update_started)
        self.schedule_validator.update_progress.connect(self.on_update_progress)
        self.schedule_validator.update_completed.connect(self.on_update_completed)

        self.validator_thread = QThread()
        self.schedule_validator.moveToThread(self.validator_thread)
        self.validator_thread.started.connect(self.on_validation_started)
        self.validator_thread.finished.connect(self.validator_thread.deleteLater)
        # -----

        self.progressBar.setVisible(False)

        self.btnRunCheck.clicked.connect(self.on_run_check)
        self.btnCreate.clicked.connect(self.on_create)
        self.btnDelete.clicked.connect(self.on_delete)
        self.btnClose.clicked.connect(self.close)

        self.cbSelectAll.setCheckState(Qt.CheckState.Checked)
        self.cbSelectAll.stateChanged.connect(self.on_select_all_changed)

        self.lblTemplateName.setText(self.current_template.name())
        hour_str = ', '.join(map(str, self.current_template.hours()))
        self.lblHours.setText(hour_str)

        dows = self._get_dow_names(self.current_template.dow())
        self.lblDows.setText(dows)

        self.setWindowTitle(f"Schedule Summary - {self.current_template.name()}")


    def on_select_all_changed(self, state: Qt.CheckState):
        for row in range(self.twSummary.rowCount()):
            check_item = self.twSummary.item(row, 0)
            if check_item:
                check_item.setData(Qt.CheckStateRole, state)

    def _prepare_summary_table(self):
        self.twSummary.setRowCount(0)
        self.twSummary.setColumnCount(4)
        self.twSummary.setHorizontalHeaderLabels(["Select","Date", "Generated Items",
                                                   "Scheduled Items"])
        self.twSummary.setSizeAdjustPolicy(QTableWidget.AdjustToContents)

    def add_summary_items(self,auto_schedule: dict, oats_schedule:dict):
        self._prepare_summary_table()
        for date, count in auto_schedule.items():
            row = self.twSummary.rowCount()
            self.twSummary.insertRow(row)
            select_item = QTableWidgetItem()
            select_item.setFlags(select_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            #oats_count = oats_schedule.get(date, 0)
            select_item.setData(Qt.CheckStateRole, Qt.CheckState.Checked)
            self.twSummary.setItem(row, 0, select_item)
            self.twSummary.setItem(row, 1, QTableWidgetItem(date))
            self.twSummary.setItem(row, 2, QTableWidgetItem(str(count)))
            self.twSummary.setItem(row, 3, QTableWidgetItem(str(oats_schedule.get(date, 0))))

    def on_run_check(self):
        self.validator_thread.start()

    def re_run_check(self):
        gen_schedule = self.group_schedule_items_by_date(self.schedule_items, self.dates)
        oats_sched = self.fetch_oats_schedule()
        self.add_summary_items(gen_schedule, oats_sched)

    def on_create(self):
        if self.twSummary.rowCount() == 0:
            return
        if QMessageBox.question(self, "Confirm Create", "Are you sure you want to create the selected schedules?",
                                 QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            if self._create_schedule():
                self.show_message("Schedule created successfully.")
                self.re_run_check()

    def _create_schedule(self) -> bool:
        dates = []
        for row in range(self.twSummary.rowCount()):
            check_item = self.twSummary.item(row, 0)
            oats_count = int(self.twSummary.item(row, 3).text())
            if check_item.checkState() == Qt.CheckState.Checked and oats_count == 0:
                date_item = self.twSummary.item(row, 1)
                dates.append(date_item.text())

        if len(dates) == 0:
            self.show_message("No valid schedules selected for creation.")
            return False

        insert_stmts = self._make_insert_statements(dates, self.current_template.hours())
        self._execute_insert_statement(insert_stmts)
        return True

    def on_delete(self):
        if self.twSummary.rowCount() == 0:
            return
        if QMessageBox.question(self, "Confirm Delete", "Are you sure you want to delete the selected schedules?",
                                 QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            if self._delete_data():
                self.show_message("Schedule deleted successfully.")
                self.re_run_check()

    def _delete_data(self) -> bool:
        dates = []
        for row in range(self.twSummary.rowCount()):
            check_item = self.twSummary.item(row, 0)
            oats_count = int(self.twSummary.item(row, 3).text())
            if check_item.checkState() == Qt.CheckState.Checked and oats_count > 0:
                date_item = self.twSummary.item(row, 1)
                dates.append(date_item.text())

        if len(dates) == 0:
            self.show_message("No valid schedules selected for deletion.")
            return False

        delete_stmt = self._make_delete_statement(dates, self.current_template.hours())
        self._execute_delete_statement(delete_stmt)
        return True

    def group_schedule_items_by_date(self, schedule_items:list, dates: list) -> dict:
        dates = [si.schedule_date().toString("yyyy-MM-dd") for si in schedule_items
                  if si.schedule_date() in dates]
        date_count = Counter(dates)
        return date_count

    def _make_insert_statements(self, dates: list, hours: list) -> dict:
        date_str = ', '.join([f"'{date}'" for date in dates])
        hour_str = ', '.join(map(str, hours))

        query = f"""
        SELECT 1 AS ScheduleService, schedule_ref AS ScheduleLineRef,
            schedule_date AS ScheduleDate, start_time AS ScheduleTime, 
            schedule_hour AS ScheduleHour, item_row AS ScheduleHourTime, 
            track_id AS ScheduleTrackReference, 0 AS ScheduleFadeIn,
            0 AS ScheduleFadeOut, 0 AS ScheduleFadeDelay, 
            'CUED' AS PlayStatus, 1 AS AutoTransition, 
            1 AS LiveTransition, 'SONG' AS ItemSource, 
            'AUDIO' AS ScheduleCommMediaType
        FROM Schedule 
        WHERE schedule_date IN ({date_str})
        AND schedule_hour in  ({hour_str})
        AND duration > 0
        ORDER BY schedule_date, schedule_hour
        """
        data_config = DataConfiguration("")
        conn = data_config._connect()
        curs = conn.cursor()

        curs.execute(query)
        results = curs.fetchall()
        insert_stmts = {}

        for result in results:
            ScheduleService = result[0]
            ScheduleLineRef = result[1]
            ScheduleDate = result[2]
            ScheduleTime = result[3]
            ScheduleHour = result[4]
            ScheduleHourTime = result[5]
            ScheduleTrackReference = result[6]
            ScheduleFadeIn = result[7]
            ScheduleFadeOut = result[8]
            ScheduleFadeDelay = result[9]
            PlayStatus = result[10]
            AutoTransition = result[11]
            LiveTransition = result[12]
            ItemSource = result[13]
            ScheduleCommMediaType = result[14]

            insert_stmt = f"""
            INSERT INTO Schedule (ScheduleService, ScheduleLineRef, ScheduleDate, 
                                  ScheduleTime, ScheduleHour, ScheduleHourTime, 
                                  ScheduleTrackReference, ScheduledFadeIn, ScheduledFadeOut,
                                  ScheduledFadeDelay, PlayStatus, AutoTransition, 
                                  LiveTransition, ItemSource, ScheduleCommMediaType)
            VALUES ({ScheduleService}, {ScheduleLineRef}, '{ScheduleDate}', '{ScheduleTime}', 
                     {ScheduleHour}, {ScheduleHourTime}, {ScheduleTrackReference}, 
                     {ScheduleFadeIn}, {ScheduleFadeOut}, {ScheduleFadeDelay}, 
                     '{PlayStatus}', {AutoTransition}, {LiveTransition}, 
                     '{ItemSource}', '{ScheduleCommMediaType}');
            """

            if ScheduleDate in insert_stmts:
                insert_stmts[ScheduleDate].append(insert_stmt)
            else:
                insert_stmts[ScheduleDate] = [insert_stmt]

        conn.close()

        return insert_stmts

    def _make_delete_statement(self, dates: list, hours: list) -> str:
        date_str = ', '.join([f"'{date}'" for date in dates])
        hour_str = ', '.join(map(str, hours))

        delete_stmt = f"""
        DELETE FROM Schedule
        WHERE scheduleDate IN ({date_str})
          AND scheduleHour in  ({hour_str})
          AND ItemSource = 'SONG'
          AND PlayStatus = 'CUED'
        """
        return delete_stmt


    def fetch_oats_schedule(self) -> dict:
        dbconn =  MSSQLData(
            MSSQL_CONN['server'], 
            MSSQL_CONN['database'], 
            MSSQL_CONN['username'], 
            MSSQL_CONN['password'])

        hours = ', '.join(map(str, self.current_template.hours()))

        dates = ', '.join([f"'{date.toString('yyyy-MM-dd')}'" for date in self.dates])

        if dbconn.connect():
            query = f"""
                SELECT ScheduleDate, count(*) AS cnt
                FROM Schedule
                WHERE ScheduleDate IN ({dates})
                AND ScheduleHour IN ({hours})
                AND ItemSource <> 'COMMS'
                GROUP BY ScheduleDate
                ORDER BY ScheduleDate
            """

            results = dbconn.execute_query(query)
            schedule = {}
            for row in results:
                sched_date = row[0].strftime("%Y-%m-%d")
                schedule[sched_date] = row[1]
            dbconn.disconnect()
            return schedule

    def _execute_insert_statement(self, statements: dict):
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

    def _execute_delete_statement(self, statement: str):
        dbconn =  MSSQLData(
            MSSQL_CONN['server'], 
            MSSQL_CONN['database'], 
            MSSQL_CONN['username'], 
            MSSQL_CONN['password'])

        if dbconn.connect():
            dbconn.execute_non_query(statement)
            dbconn.disconnect()

    def _get_dow_names(self, dow: list):
        dow_names = []
        for day in dow:
            if day == 1:
                dow_names.append("Mon")
            elif day == 2:
                dow_names.append("Tue")
            elif day == 3:
                dow_names.append("Wed")
            elif day == 4:
                dow_names.append("Thu")
            elif day == 5:
                dow_names.append("Fri") 
            elif day == 6:
                dow_names.append("Sat")
            elif day == 7:
                dow_names.append("Sun")
        return ", ".join(dow_names)

    def on_validation_started(self):
        self.btnRunCheck.setEnabled(False)
        self.btnCreate.setEnabled(False)
        self.btnDelete.setEnabled(False)
        self.btnClose.setEnabled(False)
        self.lblStatus.setText("Check started...")

        self.progressBar.setVisible(True)
        self.progressBar.reset()
        self.lblStatus.repaint()
        QApplication.processEvents()

        self.schedule_validator.fetch_data()
    
    def on_update_started(self):
        self.btnRunCheck.setEnabled(False)
        self.btnCreate.setEnabled(False)
        self.btnDelete.setEnabled(False)
        self.btnClose.setEnabled(False)
        self.lblStatus.setText("Update started...")
        self.lblStatus.repaint()

    def on_update_completed(self, success):
        self.btnRunCheck.setEnabled(True)
        self.btnCreate.setEnabled(True)
        self.btnDelete.setEnabled(True)
        self.btnClose.setEnabled(True)
        self.progressBar.setVisible(False)
        if success:
            self.lblStatus.setText("Check completed successfully.")
            oats_sched = self.schedule_validator.get_schedule()
            gen_schedule = self.group_schedule_items_by_date(self.schedule_items, self.dates)
            self.add_summary_items(gen_schedule, oats_sched)
        else:
            self.lblStatus.setText("Check failed.")

        self.lblStatus.repaint()

    def on_update_progress(self, percent: int, message: str):
        self.lblStatus.setText(f"Check in progress... {percent}%")
        self.lblStatus.repaint()

    def closeEvent(self, event):
        self.validator_thread.quit()
        self.validator_thread.wait()
        event.accept()

    def show_message(self, message:str):
        msg = QMessageBox(self)
        msg.setText(message)
        msg.setWindowTitle("Message")
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec_()
