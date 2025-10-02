from collections import Counter

from PyQt5.QtWidgets import (
    QApplication,
    QTableWidget,
    QTableWidgetItem,
    QMessageBox,
    QWidget,
    QPushButton,
    QHBoxLayout,
)

from PyQt5 import uic

from PyQt5.QtCore import (
    Qt,
    QThread,
    QDate,
    QDateTime
)

from mssql_data import MSSQLData
from data_config import DataConfiguration

from data_types import (
    MSSQL_CONN
)

from schedule_validator import ScheduleValidator

widget, base = uic.loadUiType('schedule_summary.ui')


class CellWidget(QWidget):
    def __init__(self, left_value:int, right_value:int, parent=None):
        super().__init__(parent)
        self.left_value = left_value
        self.right_value = right_value
        self._left_button, self._right_button = self._make_buttons(left_value, right_value)

        hl = QHBoxLayout()
        hl.setContentsMargins(0,0,0,0)
        hl.setSpacing(0)
        hl.addWidget(self._left_button)
        hl.addWidget(self._right_button)
        self.setLayout(hl)

    def _make_button(self, button_value: int):
        style_for_zero_value = "color: white; background-color: red; font-weight: bold;"
        button = QPushButton(str(button_value))
        button.setFixedSize(50, 30)
        if button_value == 0:
            button.setStyleSheet(style_for_zero_value)
        return button

    def _make_buttons(self, lvalue: int, rvalue: int) -> tuple:
        style_left_button = "background-color: rgb(245, 255, 206); border-radius:1px; " \
                            " min-width: 50px; min-height: 30px"
        style_right_button = "background-color: rgb(198, 214, 255); border-radius:1px;" \
                            "min-width: 50px; min-height: 30px;"
        style_zero_lvalue = "color: white; background-color: red; font-weight: bold;" \
                            "border-radius:1px;min-width: 50px; min-height:30px; "
        style_zero_rvalue = "color: white; background-color: red; font-weight: bold;" \
                            "border-radius:1px;min-width: 50px; min-height:30px; "
        style_lvalue_less_rvalue = "color: red; background-color: rgb(245, 255, 206);" \
                            " font-weight: bold; border-radius: 1px;" \
                            " min-width: 50px; min-height: 30px;"
        style_rvalue_less_lvalue = "color: red;  background-color: rgb(198, 214,255);" \
                            "font-weight: bold; border-radius:1px;" \
                            "min-width: 50px; min-height: 30px;"

        left_button = QPushButton(str(lvalue))
        left_button.setStyleSheet(style_left_button)
        right_button = QPushButton(str(rvalue))
        right_button.setStyleSheet(style_right_button)

        if lvalue < rvalue:
            left_button.setStyleSheet(style_lvalue_less_rvalue)
        if rvalue < lvalue:
            right_button.setStyleSheet(style_rvalue_less_lvalue)
        if lvalue == 0:
            left_button.setStyleSheet(style_zero_lvalue)
        if rvalue == 0:
            right_button.setStyleSheet(style_zero_rvalue)

        return left_button, right_button

    def left_button(self) -> QPushButton:
        return self._left_button
    
    def right_button(self) -> QPushButton:
        return self._right_button


class ScheduleSummaryDialog(widget, base):
    def __init__(self, **kwargs):
        super(ScheduleSummaryDialog, self).__init__(kwargs.get('parent', None))
        self.setupUi(self)

        self.current_template = kwargs.get('current_template', None)
        self.dates = kwargs.get('dates', [])
        self.schedule_items = kwargs.get('schedule_items', [])
        self.run_immediately = kwargs.get('run_immediately', False) 
        self.logger = kwargs.get('logger', None)

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
        self.btnDelete.clicked.connect(self.on_delete_scheduled)
        self.btnDeleteAll.clicked.connect(self.on_delete_all)
        self.btnClose.clicked.connect(self.close)

        self.cbSelectAll.setCheckState(Qt.CheckState.Checked)
        self.cbSelectAll.stateChanged.connect(self.on_select_all_changed)

        self.lblTemplateName.setText(self.current_template.name())
        hour_str = ', '.join(map(str, self.current_template.hours()))
        self.lblHours.setText(hour_str)

        dows = self._get_dow_names(self.current_template.dow())
        self.lblDows.setText(dows)

        self.setWindowTitle(f"Schedule Summary - {self.current_template.name()}")


    def showEvent(self, event):
        if self.run_immediately:
            self.on_run_check()

    def on_select_all_changed(self, state: Qt.CheckState):
        for row in range(self.twSummary.rowCount()):
            check_item = self.twSummary.item(row, 0)
            if check_item:
                check_item.setData(Qt.CheckStateRole, state)

    def _prepare_summary_table(self, hours: list[int]):
        columns = ["Select", "Date"]
        for hour in hours:
            columns.append(f"HR:{str(hour)}")
        columns.append("Total")

        self.twSummary.clear()
        self.twSummary.setRowCount(0)
        self.twSummary.setColumnCount(len(columns))
        self.twSummary.setHorizontalHeaderLabels(columns)
        self.twSummary.setSizeAdjustPolicy(QTableWidget.AdjustToContents)

    def add_summary_itemsXX(self,auto_schedule: dict, oats_schedule:dict):
        self._prepare_summary_table(self.current_template.hours())
        for date, count in auto_schedule.items():
            row = self.twSummary.rowCount()
            self.twSummary.insertRow(row)
            select_item = QTableWidgetItem()
            select_item.setFlags(select_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            select_item.setData(Qt.CheckStateRole, Qt.CheckState.Checked)
            select_item.setTextAlignment(Qt.AlignCenter)

            self.twSummary.setItem(row, 0, select_item)
            self.twSummary.setItem(row, 1, QTableWidgetItem(date))
            self.twSummary.setItem(row, 2, QTableWidgetItem(str(count)))
            self.twSummary.setItem(row, 3, QTableWidgetItem(str(oats_schedule.get(date, 0))))
    
    def add_summary_items(self, auto_schedule: dict, oats_schedule: dict, hours: list[int]):
        self._prepare_summary_table(self.current_template.hours())
        if len(oats_schedule) == 0:
            return
        for date, hours_count in auto_schedule.items():
            row = self.twSummary.rowCount()
            self.twSummary.insertRow(row)
            select_item = QTableWidgetItem()
            select_item.setFlags(select_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            select_item.setData(Qt.CheckStateRole, Qt.CheckState.Checked)
            self.twSummary.setItem(row, 0, select_item)
            self.twSummary.setItem(row, 1, QTableWidgetItem(date))
            col = 2
            for hour in hours:
                oats_value = oats_schedule[date].get(hour, 0)
                cell_value = f"{str(hours_count.get(hour, 0))},{oats_value}"

                cell_widget = CellWidget(hours_count.get(hour, 0),
                                         oats_schedule[date].get(hour, 0))
                self.twSummary.setCellWidget(row, col, cell_widget)
                col += 1

            auto_total = sum(auto_schedule[date].values())
            oats_total = sum(oats_schedule[date].values())
            cell_widget = CellWidget(auto_total, oats_total)

            cell_widget.left_button().setStyleSheet(self._total_button_style())
            cell_widget.right_button().setStyleSheet(self._total_button_style())
            
            self.twSummary.setCellWidget(row, col, cell_widget)

    def _total_button_style(self):
         return "background-color: rgb(245, 255, 206); border-radius:1px; " \
                    " min-width: 50px; min-height: 30px; font-weight: bold;"

    def on_run_check(self):
        self.validator_thread.start()

    def re_run_check(self):
        #self.validator_thread.start()
        gen_schedule = self.group_schedule_by_datetime(self.schedule_items, self.dates)
        # #oats_sched = self.fetch_oats_schedule()
        self.schedule_validator.clear_schedule()
        self.schedule_validator.fetch_data()
        oats_sched = self.schedule_validator.get_schedule()
        print("Re-running the check....")
        self.add_summary_items(gen_schedule, oats_sched, self.current_template.hours())

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
            if check_item.checkState() == Qt.CheckState.Checked:
                date_item = self.twSummary.item(row, 1)
                dates.append(date_item.text())

        if len(dates) == 0:
            self.show_message("No valid schedules selected for creation.")
            return False

        current_datetime = QDateTime.currentDateTime().toString('dd-MM-yyyy HH:mm')
        self.logger.log_info(f"Create Schedule. Start time: {current_datetime}")
        self.logger.log_info(f"Create schedule for template: `{self.current_template.name()}`")
        self.logger.log_info(f"Create schedule date range: {dates}")

        insert_stmts = self._make_insert_statements(dates, self.current_template.hours())
        self._execute_insert_statement(insert_stmts)

        self.logger.log_info(f"Schedule creation completed successfully.")

        return True

    def on_delete_scheduled(self):
        if self.twSummary.rowCount() == 0:
            return
        if QMessageBox.question(self, "Confirm Delete", "Are you sure you want to delete the selected schedules?",
                                 QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            if self._delete_scheduled_data():
                self.show_message("Schedule deleted successfully.")
                self.re_run_check()

    def _get_delete_dates(self) -> list:
        dates = []
        todays_date = QDate.currentDate().toString("yyyy-MM-dd")

        for row in range(self.twSummary.rowCount()):
            check_item = self.twSummary.item(row, 0)
            if check_item.checkState() == Qt.CheckState.Checked:
                date_item = self.twSummary.item(row, 1)
                # Only future dates can be deleted
                if date_item.text() >= todays_date:
                    dates.append(date_item.text())
        return dates

    def _delete_scheduled_data(self) -> bool:
        dates = self._get_delete_dates()
        if len(dates) == 0:
            self.show_message("No valid schedules selected for deletion.")
            return False

        current_datetime = QDateTime.currentDateTime().toString('dd-MM-yyyy HH:mm')
        self.logger.log_info(f"Delete Scheduled data only. Start time: {current_datetime}")
        self.logger.log_info(f"Deleting schedule for template: `{self.current_template.name()}`")
        self.logger.log_info(f"Delete date range: {dates}")

        delete_stmt = self._make_delete_stmt_for_scheduled_data(dates, self.current_template.hours())
        self._execute_delete_statement(delete_stmt)
        
        self.logger.log_info(f"Delete Scheduled data. End.")

        return True

    def on_delete_all(self):
        if self.twSummary.rowCount() == 0:
            return
        if QMessageBox.question(self, "Confirm Delete", "Are you sure you want to delete ALL selected schedules?",
                                 QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            if self._delete_all_data():
                self.show_message("All selected schedules deleted successfully.")
                self.re_run_check()

    def _delete_all_data(self) -> bool:
        dates = self._get_delete_dates()
        if len(dates) == 0:
            self.show_message("No valid schedules selected for deletion.")
            return False

        current_datetime = QDateTime.currentDateTime().toString('dd-MM-yyyy HH:mm')
        self.logger.log_info(f"Delete ALL. Start time: {current_datetime}")
        self.logger.log_info(f"Deleting schedule for template: `{self.current_template.name()}`")
        self.logger.log_info(f"Delete date range: {dates}")

        # Delete from MSSQL database
        delete_stmt = self._make_delete_stmt_for_scheduled_data(dates, self.current_template.hours())

        self.logger.log_info(f"MSSQL:Deleting scheduled data with statement: {delete_stmt}")

        status, msg = self._execute_delete_statement(delete_stmt)

        if not status:
            log_msg = f"Error deleting scheduled data: {msg}"
            self.show_message(log_msg)
            self.logger.log_error(log_msg)
            return False

        self.logger.log_info(f"Deleted scheduled from MSSQL successfully.")

        # Delete from SQLite database

        delete_stmt = self._make_delete_stmt_for_generated_data(dates, self.current_template.hours())
        dc = DataConfiguration("")

        self.logger.log_info(f"LOCAL:Deleting all data with statement: {delete_stmt}")
        result = dc.execute_query(delete_stmt)
        if not result:
            log_msg = "Error deleting all scheduled data from local database."
            self.show_message(log_msg)
            self.logger.log_error(log_msg)
            return False

        # Delete from local cache
        self.schedule_items = [si for si in self.schedule_items if si.schedule_date().toString("yyyy-MM-dd") not in dates]
        self.logger.log_info(f"Deleted all scheduled data from local cache successfully.")
        self.logger.log_info(f"Delete all. End.")

        return True


    def group_schedule_items_by_date(self, schedule_items:list, dates: list) -> dict:
        dates = [si.schedule_date().toString("yyyy-MM-dd") for si in schedule_items
                  if si.schedule_date() in dates]
        date_count = Counter(dates)
        return date_count

    def group_schedule_by_datetime(self, schedule_items: list, dates: list) -> dict:
        grouped_schedule = {}
        for date in dates:
            date_schedule_items = [si for si in schedule_items if si.schedule_date() == date]
            time_items = [si.hour() for si in date_schedule_items]
            time_count = Counter(time_items)
            grouped_schedule[date.toString("yyyy-MM-dd")] = time_count
        return grouped_schedule
            

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

    def _make_delete_stmt_for_scheduled_data(self, dates: list, hours: list) -> str:
        date_str = ', '.join([f"'{date}'" for date in dates])
        hour_str = ', '.join(map(str, hours))

        delete_stmt = f"""
        DELETE FROM Schedule
        WHERE scheduleDate IN ({date_str})
          AND scheduleHour in  ({hour_str})
          AND ItemSource <> 'COMMS'
          AND (PlayStatus = 'CUED' or PlayStatus = '')
        """
        return delete_stmt

    def _make_delete_stmt_for_generated_data(self, dates: list, hours: list) -> str:
        date_str = ', '.join([f"'{date}'" for date in dates])
        hour_str = ', '.join(map(str, hours))

        delete_stmt = f"""
        DELETE FROM Schedule
        WHERE schedule_date IN ({date_str})
          AND schedule_hour in  ({hour_str})
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

        status = False
        msg = "Failed to Connect."
        if dbconn.connect():
            status, msg = dbconn.execute_non_query(statement)
            dbconn.disconnect()
        return status, msg

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
        self.btnDeleteAll.setEnabled(False)
        self.lblStatus.setText("Validation started...")

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
        self.btnDeleteAll.setEnabled(False)
        self.lblStatus.setText("Update started...")
        self.lblStatus.repaint()

    def on_update_completed(self, success, message: str):
        self.btnRunCheck.setEnabled(True)
        self.btnCreate.setEnabled(True)
        self.btnDelete.setEnabled(True)
        self.btnClose.setEnabled(True)
        self.btnDeleteAll.setEnabled(True)
        self.progressBar.setVisible(False)
        if success:
            msg = f"Validation completed successfully: {message}"
            self.lblStatus.setText(msg)
            oats_sched = self.schedule_validator.get_schedule()
            gen_schedule = self.group_schedule_by_datetime(self.schedule_items, self.dates)
            self.add_summary_items(gen_schedule, oats_sched, self.current_template.hours())
        else:
            self.lblStatus.setText("Validation failed.")

        self.lblStatus.repaint()

    def on_update_progress(self, percent: int, message: str):
        self.lblStatus.setText(f"Validation in progress... {percent}%")
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
