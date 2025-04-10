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
   QAbstractScrollArea
)

from PyQt5.QtCore import (
    Qt,
    QSize,
    QTime,
    QObject
)

from PyQt5.QtGui import (
    QIcon
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


widget, base = uic.loadUiType('template_config.ui')

class Track:
    def __init__(self, track_id: int, title: str, artist_name: str, 
                 duration: int, artist_id:int, folder_id: int, file_path: str = ""):
        self._track_id = track_id
        self._title = title
        self._artist_name = artist_name
        self._duration = duration
        self._artist_id = artist_id
        self._folder_id = folder_id
        self._file_path = file_path

    def track_id(self) -> int:
        return self._track_id
    def title(self) -> str:
        return self._title
    def artist_name(self) -> str:
        return self._artist_name
    def duration(self) -> str:
        return self._duration
    def artist_id(self) -> int:
        return self._artist_id
    def folder_id(self) -> int:
        return self._folder_id
    def file_path(self) -> str:
        return self._file_path
    def formatted_track_id(self) ->str:
        return(f"{self._track_id:08d}")

class ItemTableKeyFilter(QObject):
    def __init__(self, parent):
        super(ItemTableKeyFilter, self).__init__()
        self._parent = parent
    def eventFilter(self, obj, event):
        if event.type() == event.KeyPress  and event.key() == Qt.Key.Key_Delete:
            selected = obj.selectedItems()
            if len(selected) > 0:
                self._parent.on_delete_item()
                # item_identifier = selected[0].data(Qt.ItemDataRole.UserRole)
                # item = self._parent.current_template.item(item_identifier)
                # if item.item_type() == ItemType.HEADER or item.item_type() == ItemType.EMPTY:
                #      return False
                # self._parent.current_template.item(item_identifier).set_db_action(DBAction.DELETE)
                # # self._parent.current_template.remove_item(item_identifier)
                # obj.removeRow(selected[0].row())

        return super().eventFilter(obj, event)



class TemplateConfiguration(widget, base):
    def __init__(self, parent):
        super(TemplateConfiguration, self).__init__()
        self.setupUi(self)
        
        self.main_window = parent

        self.templates = {}
        self.item_clicked = ""
        self.current_template = None

        self.current_folder = None
        self.current_track = None

        self.db_config = DataConfiguration("data/templates.db")

        self.set_template_table()

        self.csv_data = CSVData()
        self.tracks = self.csv_data.load_tracks()

        #self.load_tracks()

        self.btnNew.clicked.connect(self.on_new)
        self.btnSave.clicked.connect(self.on_save)
        self.btnSearch.clicked.connect(self.on_search)
        self.btnDeleteTemplate.clicked.connect(self.on_delete_template)
        self.btnDeleteItem.clicked.connect(self.on_delete_item)

        self.btnSchedule.clicked.connect(self.on_create_schedule)

        self.wigSearch.hide()
        self.twMedia.setHeaderLabels(["Media"])
        
        self.spTemplate.setSizes([200, 800])
        self.spMedia.setSizes([200, 800])

        self.twMedia.itemClicked.connect(self.on_media_item_clicked)
        self.twTracks.itemClicked.connect(self.on_track_clicked)

        self.twItems.itemDoubleClicked.connect(self.on_item_double_clicked)

        self.create_media_folders()

        self.twTemplates.itemSelectionChanged.connect(self.on_template_selected)

        self.itf = ItemTableKeyFilter(self)
        self.twItems.installEventFilter(self.itf)

        #self.test_new_template()
        # self.test_load_template_items_from_db()
        self.load_templates_from_db()
        #self.test_folders()

    def on_template_selected(self):
        selected = self.twTemplates.selectedItems()
        if len(selected) > 0:
            name = selected[0].text()
            template = self.templates[name]
            self.current_template = template
            self.display_template_items(template)

            self.compute_start_times()

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
        print(template_items)

        for key, item in template_items.items():
            row = self.twItems.rowCount()
            self.twItems.insertRow(row)

            if item.item_type() == ItemType.HEADER:
                item.set_item_row(row)

            if item.db_action() == DBAction.DELETE:
                continue

            self.add_template_item(row, item)

    def _add_blank_rows(self, t_items: dict):
        prev_item = None
        items = {}
        for key, item in t_items.items():
            print(f"PREV_ITEM: {prev_item.item_type() if prev_item is not None else 'None'}")
            print(f"ITEM: {item.item_type()}")
            if prev_item is None:
                prev_item = item
                items[key] = item
            elif prev_item.item_type() == ItemType.HEADER and item.item_type() == ItemType.HEADER:
                print('HEADER - HEADER')
                blank_item = self.make_blank_item()
                items[blank_item.item_identifier()] = blank_item
                items[key] = item
                prev_item = item
            elif prev_item.item_type() == ItemType.SONG and item.item_type() == ItemType.HEADER:
                blank_item = self.make_blank_item()
                items[blank_item.item_identifier()] = blank_item
                items[key] = item
                prev_item = item
            elif prev_item.item_type() == ItemType.FOLDER and item.item_type() == ItemType.HEADER:
                print('FOLDER - HEADER')
                blank_item = self.make_blank_item()
                items[blank_item.item_identifier()] = blank_item
                items[key] = item
                prev_item = item
            else:
                items[key] = item
                prev_item = item
        return items
                

    def compute_start_times(self):
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


    def set_template_table(self):
        self.twTemplates.clear()
        self.twTemplates.setRowCount(0)
        self.twTemplates.setColumnCount(2)
        self.twTemplates.setHorizontalHeaderLabels(["Name", "Description"])
        self.twTemplates.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

    def on_new(self):
        dialog = TemplateDialog()
        result = dialog.exec_()

        if result == QDialog.Accepted:
            template = Template(dialog.get_name())
            template.set_description(dialog.get_description())
            template.set_hours(dialog.get_selected_hours())

            self.templates[template.name()] = template

            self.add_template_to_table(template)
            self.create_hourly_headers(template)

    def test_get_test_template(self)->Template:
        template = Template("Test Template")
        template.set_description("This is a test template")
        template.set_hours([2,3,4])
        template.set_db_action(DBAction.CREATE)
        return template

    def test_new_template(self):
        template = self.test_get_test_template()
        self.templates[template.name()] = template
        self.add_template_to_table(template)
        self.create_hourly_headers(template)

    def test_load_template_items_from_db(self):
        self.current_template = self.test_get_test_template()

        ti = self.db_config.fetch_template_items(1111)
        self._setup_items_table()
        items = self._add_blank_rows(ti)

        self._populate_items_table(items)
        self.compute_start_times()

    def load_templates_from_db(self):
        self.templates = self.db_config.fetch_all_templates()

        self.show_templates(self.templates)

    def show_templates(self, templates: dict):
        self.set_template_table()
        for name, template in templates.items():
            if template.db_action() == DBAction.DELETE:
                continue
            self.add_template_to_table(template)

    def add_template_to_table(self, template:Template):
        row = self.twTemplates.rowCount()
        self.twTemplates.insertRow(row)
        self.twTemplates.setItem(row, 0, QTableWidgetItem(template.name()))
        self.twTemplates.setItem(row, 1, QTableWidgetItem(template.description()))


    def create_hourly_headers(self, template:Template):
        for hour in template.hours():
            header = HeaderItem()
            header.set_hour(hour)
            header.set_start_time(QTime(hour, 0, 0))
            header.set_db_action(DBAction.CREATE)

            template.add_item(header)
            blank_item = self.make_blank_item()
            template.add_item(blank_item)
            time.sleep(0.05)

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

    def on_delete_item(self):
        selected = self.twItems.selectedItems()
        if len(selected) > 0:
            item_identifier = selected[0].data(Qt.ItemDataRole.UserRole)
            item = self.current_template.item(item_identifier)

            if item.item_type() == ItemType.HEADER or item.item_type() == ItemType.EMPTY:
                return

            self.current_template.item(item_identifier).set_db_action(DBAction.DELETE)
            # self.current_template.remove_item(item_id)
            print(f'Item DB ID: {self.current_template.item(item_identifier).id()}')
            self.twItems.removeRow(selected[0].row())

    def create_media_folders(self):
        tc = TreeConfig('data/tree.txt')
        tree = tc.read_tree_file()
        root_item = self.build_tree(tree)
        self.twMedia.insertTopLevelItem(0, root_item)

    def build_tree(self, tree, item=None):
        for node in tree:
            if item is None:
                item = QTreeWidgetItem([node.name])
                item.setData(0, Qt.ItemDataRole.UserRole, node.node_id)
                self.build_tree(node.children, item)
            else:
                child = QTreeWidgetItem([node.name])
                child.setData(0, Qt.ItemDataRole.UserRole, node.node_id)
                item.addChild(child)
                if len(node.children) > 0:
                    self.build_tree(node.children, child)
        return item

    # def load_tracks(self):
    #     with open('data/tracks.csv',  newline='', encoding="utf-8-sig") as csvfile:
    #         reader = csv.reader(csvfile, delimiter=',', quotechar='"')
    #         for row in reader:
    #             track_id, title, artist_name, duration, artist_id, folder_id, file_path = row
    #             track = Track(int(track_id), title, artist_name, int(duration), 
    #                           int(artist_id), int(folder_id), file_path )
    #             self.tracks[int(track_id)] = track

    def on_media_item_clicked(self, item:QTreeWidgetItem):
        node_id = item.data(0, Qt.ItemDataRole.UserRole)
        text = item.text(0)
        self.item_clicked = "folder"
        self.current_folder = {'id': node_id, 'name':text}

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
       #self.twTracks.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

       tracks = dict(filter(lambda x: x[1].folder_id() == folder_id, self.tracks.items()))

       for key, track in tracks.items():
           row = self.twTracks.rowCount()
           self.twTracks.insertRow(row)
           track_title_twi = QTableWidgetItem(track.title())
           track_title_twi.setData(Qt.ItemDataRole.UserRole, track.track_id())
           self.twTracks.setItem(row, 0, track_title_twi)
           self.twTracks.setItem(row, 1, QTableWidgetItem(track.artist_name()))
           self.twTracks.setItem(row, 2, QTableWidgetItem(str(track.duration())))
           self.twTracks.setItem(row, 3, QTableWidgetItem(track.formatted_track_id()))
           self.twTracks.setItem(row, 4, QTableWidgetItem(track.file_path()))

    def on_track_clicked(self):
        selected = self.twTracks.selectedItems()
        if len(selected) > 0:
            self.item_clicked = "track"
            track_id = selected[0].data(Qt.ItemDataRole.UserRole)
            self.current_track = self.tracks[track_id]

    def on_item_double_clicked(self, item:QTableWidgetItem):
        new_item = None

        if self.item_clicked == "folder":
            new_item = FolderItem(self.twMedia.currentItem().text(0))
            new_item.set_folder_id(self.current_folder['id'])
            new_item.set_folder_name(self.current_folder['name'])
            new_item.set_item_row(item.row())


        if self.item_clicked == "track":
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

    def add_template_item(self, row: int, item: "TemplateItem"):

        if item.item_type() not in BaseTableWidgetItem.widget_register:
            return

        WidgetItem = BaseTableWidgetItem.widget_register[item.item_type()]

        twiTime = WidgetItem(item.formatted_time())
        twiTime.setData(Qt.ItemDataRole.UserRole, item.item_identifier())
        self.twItems.setItem(row, 0, twiTime)

        self.twItems.setItem(row, 1, WidgetItem((item.formatted_duration())))
        self.twItems.setItem(row, 2, WidgetItem(item.title()))
        self.twItems.setItem(row, 3, WidgetItem(item.artist_name()))
        self.twItems.setItem(row, 4, WidgetItem(item.folder_name()))

        if (item.track_id() == 0):
            self.twItems.setItem(row, 5, WidgetItem(""))
        else:
            self.twItems.setItem(row, 5, WidgetItem(((item.formatted_track_id()))))

        self.twItems.setItem(row, 6, WidgetItem(item.item_path()))

        self.current_template.add_item(item)

    def on_create_schedule(self):
        if self.current_template is None:
            return
        schedule_dlg = ScheduleDialog(self.current_template, self.tracks)
        self.main_window.mdi_area.addSubWindow(schedule_dlg)
        schedule_dlg.showMaximized()

    def test_fetch_commercial_breaks(self):
        server = 'localhost'
        database = 'citizenfm'
        username = 'sa'
        password = 'abc123'

        mssql =  MSSQLData(server, database, username, password)
        if mssql.connect():
            sql = (f"Select ScheduleDate, ScheduleTime, ScheduleHour, BookedSpots"
                   f" from schedule  "
                   f" where scheduledate = '2025-04-07' "
                   f" and ItemSource = 'COMMS' "
                   f" order by ScheduleHour, ScheduleTime ")
            rows = mssql.execute_query(sql)
            for row in rows:
                print(row)


    def test_folders(self):
        new_item = FolderItem("Folder")

        
            
