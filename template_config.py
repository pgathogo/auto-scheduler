import time
import csv

from PyQt5.QtWidgets import (
   QApplication, 
   QDialog,
   QMdiArea,
   QAction,
   QTextEdit,
   QTableWidgetItem,
   QHeaderView,
   QTreeWidgetItem,
   QAbstractScrollArea,
   QMessageBox,
)

from PyQt5.QtCore import (
    Qt,
    QSize,
    QTime,
    QObject,
    QItemSelectionModel
)

from PyQt5.QtGui import (
    QIcon,
    QFont
) 

from PyQt5 import uic

from template_dialog import TemplateDialog
from template import Template

from template_item import (
    HeaderItem,
    BlankItem,
    ItemType,
    FolderItem,
    SongItem,
    BaseTableWidgetItem,
    FirstColumnTableWidgetItem,
    DBAction
)

from data_config import DataConfiguration
from csvdata import CSVData

from search_widget import SearchWidget
from tree_config import TreeConfig
from mssql_data import MSSQLData
from schedule_dialog import ScheduleDialog

from data_types import (
    read_registry, 
    MSSQL_CONN,
    TrackColumns
)

from track import Track

from template_stats import TemplateStatistics


widget, base = uic.loadUiType('template_config.ui')

class ItemTableKeyFilter(QObject):
    def __init__(self, parent):
        super(ItemTableKeyFilter, self).__init__()
        self._parent = parent
    def eventFilter(self, obj, event):
        if event.type() == event.KeyPress  and event.key() == Qt.Key.Key_Delete:
            selected = obj.selectedItems()
            if len(selected) > 0:
                self._parent.on_delete_template_item()
        return super().eventFilter(obj, event)


class TemplateConfiguration(widget, base):
    def __init__(self, parent):
        super(TemplateConfiguration, self).__init__()
        self.setupUi(self)
        
        self.main_window = parent

        self.templates = {}
        self.item_clicked = ""
        self.current_template = None

        self._hour_headers = {}

        self.current_folder = None
        self.current_track = None

        self.db_config = DataConfiguration("data/templates.db")
        self.mssql_conn = self._make_mssql_connection()

        self.set_template_table()

        # self.csv_data = CSVData()
        # self.tracks = self.csv_data.load_tracks()

        self.btnNew.clicked.connect(self.on_new)
        self.btnEdit.clicked.connect(self.on_edit)
        self.btnStats.clicked.connect(self.on_stats)
        self.btnSave.clicked.connect(self.on_save)
        self.btnSearch.clicked.connect(self.on_search)
        self.btnDeleteTemplate.clicked.connect(self.on_delete_template)
        self.btnDeleteItem.clicked.connect(self.on_delete_template_item)

        self.btnSchedule.clicked.connect(self.on_create_schedule)

        self.wigSearch.hide()
        self.twMedia.setHeaderLabels(["Media"])

        self.wigStats.hide()
        
        self.spTemplate.setSizes([200, 800])
        self.spMedia.setSizes([200, 800])
        self.spStats.setSizes([800, 200])

        self.twMedia.itemClicked.connect(self.on_media_item_clicked)
        self.twTracks.itemClicked.connect(self.on_track_clicked)

        self.twItems.itemDoubleClicked.connect(self.on_item_double_clicked)

        self.tracks = self.load_tracks()
        self.tracks_avg = {}
        self.create_media_folders()

        self.twTemplates.itemSelectionChanged.connect(self.on_template_selected)

        self.itf = ItemTableKeyFilter(self)
        self.twItems.installEventFilter(self.itf)

        self.load_templates_from_db()

        self.template_stats = TemplateStatistics(self.twStats)   


    def _make_mssql_connection(self):
        server = MSSQL_CONN['server']
        database = MSSQL_CONN['database']
        username = MSSQL_CONN['username']  
        password = MSSQL_CONN['password']
        return MSSQLData(server, database, username, password)

    def on_template_selected(self):
        if len(self.twTemplates.selectionModel().selectedRows()) > 1:
            return
        selected = self.twTemplates.selectedItems()

        if len(selected) > 0:
            name = selected[0].text()
            template = self.templates[name]
            self.current_template = template
            self.display_template_items(template)
            self.compute_start_times()
            self.template_stats.compute_stats(template)

    def display_template_items(self, template:Template):
        self._setup_items_table()
        self._populate_items_table(template.template_items())

    def _setup_items_table(self):
        self.twItems.clear()
        self.twItems.setRowCount(0)
        self.twItems.setColumnCount(7)

        self.twItems.setSizeAdjustPolicy(
            QAbstractScrollArea.AdjustToContents)
        self.twItems.resizeColumnsToContents()

        self.twItems.setRowHeight(0, 10)
        self.twItems.setRowHeight(1, 10)
        self.twItems.setRowHeight(2, 10)
        self.twItems.setRowHeight(3, 10)
        self.twItems.setRowHeight(4, 10)
        self.twItems.setRowHeight(5, 10)
        self.twItems.setRowHeight(6, 10)

        self.twItems.setHorizontalHeaderLabels(["Start", "Length", "Title", "Artist", "Category", "Filename", "Path"])
        self.twItems.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    
    def _populate_items_table(self, template_items: dict):
        for key, item in template_items.items():
            if item.db_action() == DBAction.DELETE:
                continue

            row = self.twItems.rowCount()
            self.twItems.insertRow(row)

            if item.item_type() == ItemType.HEADER:
                item.set_item_row(row)

            self.add_template_item(row, item)

    def _add_blank_rows(self, t_items: dict):
        prev_item = None
        items = {}
        for key, item in t_items.items():
            if prev_item is None:
                prev_item = item
                items[key] = item
            elif prev_item.item_type() == ItemType.HEADER and item.item_type() == ItemType.HEADER:
                blank_item = self.make_blank_item()
                blank_item.set_hour(item.hour())
                items[blank_item.item_identifier()] = blank_item
                items[key] = item
                prev_item = item
            elif prev_item.item_type() == ItemType.SONG and item.item_type() == ItemType.HEADER:
                blank_item = self.make_blank_item()
                blank_item.set_hour(item.hour())
                items[blank_item.item_identifier()] = blank_item
                items[key] = item
                prev_item = item
            elif prev_item.item_type() == ItemType.FOLDER and item.item_type() == ItemType.HEADER:
                blank_item = self.make_blank_item()
                blank_item.set_hour(item.hour())
                items[blank_item.item_identifier()] = blank_item
                items[key] = item
                prev_item = item
            else:
                items[key] = item
                prev_item = item
        return items
                

    def compute_start_times(self):
        current_hour = -1
        total_hour_duration = 0
        total_hour_time = QTime(0, 0, 0)

        for row in range(self.twItems.rowCount()):

            column1 = self.twItems.item(row, 0)
            if column1 is None:
                continue

            item_identifier = column1.data(Qt.ItemDataRole.UserRole)
            #item_id = self.twItems.item(row, 0).data(Qt.ItemDataRole.UserRole)

            #item_id = column1.data(Qt.ItemDataRole.UserRole)
            item = self.current_template.item(item_identifier)

            if item.item_type() == ItemType.EMPTY:
                continue

            if item.item_type() == ItemType.HEADER:
                prev_hr = item.hour()
                prev_start_time = QTime(prev_hr, 0, 0)
                prev_dur = item.duration()
                item.set_item_row(row)
                item.set_start_time(prev_start_time)

                current_hour = item.hour()
                total_hour_duration = 0
                total_hour_time = QTime(item.hour(), 0, 0)
                continue

            # If item has no ID (id = -1), mark it for creation, else update
            if item.id() == -1:
                item.set_db_action(DBAction.CREATE)
            else:
                item.set_db_action(DBAction.UPDATE) 

            start_time = prev_start_time.addMSecs(prev_dur)
            item.set_start_time(start_time)
            item.set_item_row(row)
            
            self.twItems.item(row, 0).setText(item.formatted_start_time())

            prev_start_time = start_time
            prev_dur = item.duration()

            total_hour_duration += item.duration()
            total_hour_time = total_hour_time.addMSecs(item.duration())
            self._hour_headers[current_hour].setText(total_hour_time.toString("HH:mm:ss"))


    def set_template_table(self):
        self.twTemplates.clear()
        self.twTemplates.setRowCount(0)
        self.twTemplates.setColumnCount(3)
        self.twTemplates.setHorizontalHeaderLabels(["Name", "Hours", "DOW"])
        self.twTemplates.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

    def on_new(self):
        dialog = TemplateDialog()
        result = dialog.exec_()

        if result == QDialog.Accepted:
            template = Template(dialog.get_name())
            template.set_description(dialog.get_description())
            template.set_hours(dialog.get_selected_hours())
            template.set_dow(dialog.get_dow())
            template.set_db_action(DBAction.CREATE)

            self.templates[template.name()] = template

            twi_name = self.add_template_to_table(template)
            headers = self.create_hourly_headers(template.hours())
            for header in headers:
                template.add_item(header)

            self.twTemplates.setCurrentItem(twi_name, QItemSelectionModel.SelectCurrent)
                

    def on_edit(self):
        dialog = TemplateDialog(self.current_template)
        result = dialog.exec_()

        if result == QDialog.Accepted:
            self.templates[self.current_template.name()].set_name(dialog.get_name())
            self.templates[self.current_template.name()].set_description(dialog.get_description())
            self.templates[self.current_template.name()].set_dow(dialog.get_dow())

            updated_hours = dialog.get_selected_hours()

            # Get the difference between current template hours and updated hours
            diff_hours = list(set(self.current_template.hours()) ^ set(updated_hours))

            for hour in diff_hours:
                # If hour is in the current template, it means it was removed
                if hour in self.current_template.hours():
                    items = self.templates[self.current_template.name()].get_items_for_hour(hour)
                    for item in items:
                        item.set_db_action(DBAction.DELETE)
                    self.templates[self.current_template.name()].mark_items_for_deletion(hour)
                else:
                    header_and_blank = self.create_hourly_headers([hour])
                    self.templates[self.current_template.name()].insert_header(header_and_blank)

            self.templates[self.current_template.name()].set_hours(updated_hours)
            self.templates[self.current_template.name()].set_db_action(DBAction.UPDATE)

            self.show_templates(self.templates)
            self.display_template_items(self.current_template)
            self.template_stats.compute_stats(self.current_template)

    def on_stats(self):
        if self.btnStats.isChecked():
            self.wigStats.show()
        else:
            self.wigStats.hide()


    def load_templates_from_db(self):
        self.templates = self.db_config.fetch_all_templates()
        self.show_templates(self.templates)

    def show_templates(self, templates: dict):
        self.set_template_table()
        for name, template in templates.items():
            if template.db_action() == DBAction.DELETE:
                continue
            self.add_template_to_table(template)

    def add_template_to_table(self, template:Template) -> QTableWidgetItem:
        row = self.twTemplates.rowCount()
        self.twTemplates.insertRow(row)
        twi_name = QTableWidgetItem(template.name())
        self.twTemplates.setItem(row, 0, twi_name)

        hours = ", ".join(map(str, template.hours()))
        self.twTemplates.setItem(row, 1, QTableWidgetItem(hours))
        dow = self._get_dow_names(template.dow())
        self.twTemplates.setItem(row, 2, QTableWidgetItem(dow))

        return twi_name

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

    def create_hourly_headers(self, hours:list) ->list:
        headers = []
        for hour in hours:
            header = HeaderItem()
            header.set_hour(hour)
            header.set_start_time(QTime(hour, 0, 0))
            header.set_db_action(DBAction.CREATE)

            headers.append(header)
            blank_item = self.make_blank_item()
            blank_item.set_hour(hour)
            headers.append(blank_item)

        return headers

    def make_blank_item(self):
        blank = BlankItem()
        blank.set_start_time("")
        return blank

    def print_items(self, template:Template):
        for key, item in template._template_items.items():
            print(f"{key} - {item.title()} - {item.time()}")

    def on_save(self):
        # Add try catch 
        self.db_config.save(self.templates)

    def on_search(self):
        if self.btnSearch.isChecked():
            self.wigSearch.show()
        else:
            self.wigSearch.hide()

    def on_delete_template(self):
        selected = self.twTemplates.selectedItems()
        if len(selected) > 0:
            name = selected[0].text()
            template = self.templates[name]
            template.set_db_action(DBAction.DELETE)
            #self.db_config.delete_template(template.id())
            #del self.templates[name]
            self.twTemplates.removeRow(selected[0].row())
            self.show_templates(self.templates)

    def on_delete_template_item(self):
        selected = self.twItems.selectedItems()
        if len(selected) > 0:
            item_identifier = selected[0].data(Qt.ItemDataRole.UserRole)
            item = self.current_template.item(item_identifier)

            if item.item_type() == ItemType.HEADER or item.item_type() == ItemType.EMPTY:
                return

            self.current_template.item(item_identifier).set_db_action(DBAction.DELETE)
            # self.current_template.remove_item(item_id)
            self.twItems.removeRow(selected[0].row())

            self.compute_start_times()

    def create_media_folders(self):
        #records = self.read_tree_from_file('data/tree.txt')
        records = self.read_tree_from_db()
        tc = TreeConfig(records)
        tree = tc.make_tree()
        root_item = self.build_tree(tree)
        self.twMedia.insertTopLevelItem(0, root_item)

    def read_tree_from_file(self, file:str) -> list[tuple]:
        records = []
        with open(file, 'r') as f:
            for line in f:
                record = tuple(line.strip().split('|'))
                records.append(record)
        return records

    def read_tree_from_db(self):
        records = []

        server = MSSQL_CONN['server']
        database = MSSQL_CONN['database']
        username = MSSQL_CONN['username']  
        password = MSSQL_CONN['password']

        mssql =  MSSQLData(server, database, username, password)
        if mssql.connect():
            sql = (f"Select NodeID, NodeName, NodeParent "
                   f" from tree "
                   f" order by NodeID ")
            rows = mssql.execute_query(sql)

            for row in rows:
                records.append(row)

        return records

    def build_tree(self, tree, item=None):
        for node in tree:
            if item is None:
                node_name = f"{node.name} ({self.track_count(node.node_id)})"
                item = QTreeWidgetItem([node_name])

                #item = QTreeWidgetItem([node.name])
                item.setData(0, Qt.ItemDataRole.UserRole, node.node_id)
                self.build_tree(node.children, item)
            else:
                node_name = f"{node.name} ({self.track_count(node.node_id)})"

                child = QTreeWidgetItem([node_name])
                child.setData(0, Qt.ItemDataRole.UserRole, node.node_id)
                item.addChild(child)
                if len(node.children) > 0:
                    self.build_tree(node.children, child)
        return item

    def on_media_item_clicked(self, item:QTreeWidgetItem):
        node_id = item.data(0, Qt.ItemDataRole.UserRole)
        text = item.text(0)
        text = text.split('(')[0].strip()
        self.item_clicked = "folder"
        self.current_folder = {
            'id': node_id, 
            'name':text,
            'avg_duration': self.track_avg_duration(node_id),
            'track_count': self.track_count(node_id)
            }
        self.show_tracks(node_id)

    def show_tracks(self, folder_id: int):
       self.twTracks.clear()
       self.twTracks.setRowCount(0)
       self.twTracks.setColumnCount(5)
       self.twTracks.setColumnWidth(0, 450)
       self.twTracks.setColumnWidth(1, 450)
       self.twTracks.setColumnWidth(2, 160)
       self.twTracks.setColumnWidth(3, 160)
       self.twTracks.setColumnWidth(4, 300)
       self.twTracks.setHorizontalHeaderLabels(["Title", "Artist", "Duration", "Track ID", "FilePath"])

       if folder_id not in self.tracks:
           return

       tracks = self.tracks[folder_id]
       if len(tracks) == 0:
              return

       for track_ref, track in tracks.items():
           row = self.twTracks.rowCount()
           self.twTracks.insertRow(row)
           track_title_twi = QTableWidgetItem(track.title())
           track_title_twi.setData(Qt.ItemDataRole.UserRole, track.track_id())
           self.twTracks.setItem(row, 0, track_title_twi)
           self.twTracks.setItem(row, 1, QTableWidgetItem(track.artist_name()))
           self.twTracks.setItem(row, 2, QTableWidgetItem(str(track.formatted_duration())))
           self.twTracks.setItem(row, 3, QTableWidgetItem(track.formatted_track_id()))
           self.twTracks.setItem(row, 4, QTableWidgetItem(track.file_path()))

    def on_track_clicked(self):
        selected = self.twTracks.selectedItems()
        if len(selected) > 0:
            self.item_clicked = "track"
            track_id = selected[0].data(Qt.ItemDataRole.UserRole)
            self.current_track = self.tracks[self.current_folder['id']][track_id]

    def on_item_double_clicked(self, item:QTableWidgetItem):
        new_item = None

        if self.item_clicked == "folder":
            # Check if folder has tracks
            fid = self.current_folder['id']
            if fid not in self.tracks:
                self.show_message("No tracks in folder")
                return

            if len(self.tracks[fid]) == 0:
                self.show_message("No tracks in folder")
                return

            new_item = FolderItem(self.current_folder['name'])

            #new_item = FolderItem(self.twMedia.currentItem().text(0))

            new_item.set_duration(self.current_folder['avg_duration'])
            new_item.set_folder_id(self.current_folder['id'])
            new_item.set_folder_name(self.current_folder['name'])
            new_item.set_item_row(item.row())

        if self.item_clicked == "track":
            if self.current_track.duration() == 0:
                return
            new_item = SongItem(self.current_track.title())
            new_item.set_duration(self.current_track.duration())
            new_item.set_title(self.current_track.title())
            new_item.set_folder_name(self.current_folder['name'])
            new_item.set_folder_id(self.current_folder['id'])
            new_item.set_track_id(self.current_track.track_id())
            new_item.set_artist_id(self.current_track.artist_id())
            new_item.set_artist_name(self.current_track.artist_name())
            new_item.set_item_path(self.current_track.file_path())

        if new_item is None:
            return

        new_item.set_db_action(DBAction.CREATE)

        selected = self.twItems.selectedItems()
        item_identifier = selected[0].data(Qt.ItemDataRole.UserRole)
        template_item = self.current_template.item(item_identifier)

        if template_item.item_type() == ItemType.HEADER:
            return

        # Get previous item - to retriev hour
        prev_item_id = self.twItems.item(item.row()-1, 0).data(Qt.ItemDataRole.UserRole)
        prev_item = self.current_template.item(prev_item_id)
        hour = prev_item.hour()

        new_item.set_hour(hour)
    
        new_row = item.row()
        prev_row = item.row()-1
        
        new_item.set_item_row(new_row)

        # Create a blank row in the table widget
        self.twItems.insertRow(new_row) 

        # New item is inserted in the previous row 
        self.add_template_item(new_row, new_item)

        self.compute_start_times()

        self.template_stats.update_stats(hour, self.current_template)

        

    def add_template_item(self, row: int, item: "TemplateItem"):

        if item.item_type() not in BaseTableWidgetItem.widget_register:
            return

        WidgetItem = BaseTableWidgetItem.widget_register[item.item_type()]

        twiTime = WidgetItem(item.formatted_time())
        twiTime.setData(Qt.ItemDataRole.UserRole, item.item_identifier())
        self.twItems.setItem(row, 0, twiTime)

        wi_duration = WidgetItem(item.formatted_duration())

        self.twItems.setItem(row, 1, wi_duration)
        self.twItems.setItem(row, 2, WidgetItem(item.title()))
        self.twItems.setItem(row, 3, WidgetItem(item.artist_name()))
        self.twItems.setItem(row, 4, WidgetItem(item.folder_name()))

        if (item.track_id() == 0):
            self.twItems.setItem(row, 5, WidgetItem(""))
        else:
            self.twItems.setItem(row, 5, WidgetItem(((item.formatted_track_id()))))

        self.twItems.setItem(row, 6, WidgetItem(item.item_path()))

        self.current_template.add_item(item)

        if item.item_type() == ItemType.HEADER:
            wi_duration.setFont(QFont("Times", 10, QFont.Bold))
            self._hour_headers[item.hour()] = wi_duration


    def on_create_schedule(self):
        if self.current_template is None:
            return
        schedule_dlg = ScheduleDialog(self.current_template, self.tracks)
        self.main_window.mdi_area.addSubWindow(schedule_dlg)
        schedule_dlg.showMaximized()

    def load_tracks(self) -> dict:
        folders = {}

        server = MSSQL_CONN['server']
        database = MSSQL_CONN['database']
        username = MSSQL_CONN['username']  
        password = MSSQL_CONN['password']

        mssql =  MSSQLData(server, database, username, password)
        if mssql.connect():
            sql = (f"Select TrackReference, TrackTitle, ArtistSearch, Duration, ArtistID_1, FolderID, FilePath "
                   f" from Tracks "
                   f" where ArtistID_1 is not Null"
                   f" order by TrackReference ")

            rows = mssql.execute_query(sql)
            for row in rows:
                track_reference = int(row[int(TrackColumns.TRACK_REFERENCE)])
                track = Track(track_reference)
                track.set_title(row[TrackColumns.TRACK_TITLE])
                track.set_artist_name(row[TrackColumns.ARTIST_SEARCH])
                track.set_duration(int(row[TrackColumns.DURATION]))

                track.set_artist_id(int(row[TrackColumns.ARTISTID_1]))

                folder_id = int(row[TrackColumns.FOLDER_ID])
                track.set_folder_id(folder_id)
                track.set_file_path(row[TrackColumns.FILEPATH])

                if folder_id in folders:
                    folders[folder_id][track_reference] = track
                else:
                     folders[folder_id] = {}
                     folders[folder_id][track_reference] = track
        return folders

    def track_count(self, folder_id:int) -> int:
        if folder_id not in self.tracks:
            return 0
        return len(self.tracks[folder_id])

    def track_avg_duration(self, folder_id:int) -> int:
        if folder_id not in self.tracks:
            return 0
        total_duration = 0
        for track in self.tracks[folder_id].values():
            total_duration += track.duration()
        return total_duration // len(self.tracks[folder_id])

    def show_message(self, message:str):
        msg = QMessageBox(self)
        msg.setText(message)
        msg.setWindowTitle("Message")
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec_()


        
            
