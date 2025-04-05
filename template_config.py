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
    QTime
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

from search_widget import SearchWidget
from tree_config import TreeConfig

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


class TemplateConfiguration(widget, base):
    def __init__(self):
        super(TemplateConfiguration, self).__init__()
        self.setupUi(self)

        self.templates = {}
        self.tracks = {}
        self.item_clicked = ""
        self.current_template = None

        self.current_folder = None
        self.current_track = None

        self.db_config = DataConfiguration("templates.db")

        self.set_template_table()
        self.load_tracks()

        self.btnNew.clicked.connect(self.on_new)
        self.btnSave.clicked.connect(self.on_save)
        self.btnSearch.clicked.connect(self.on_search)

        self.wigSearch.hide()
        self.twMedia.setHeaderLabels(["Media"])
        
        self.spTemplate.setSizes([200, 800])
        self.spMedia.setSizes([200, 800])

        self.twMedia.itemClicked.connect(self.on_media_item_clicked)
        self.twTracks.itemClicked.connect(self.on_track_clicked)

        self.twItems.itemDoubleClicked.connect(self.on_item_double_clicked)

        self.create_media_folders()

        self.twTemplates.itemSelectionChanged.connect(self.on_template_selected)

        #self.test_new_template()
        self.test_load_template_items_from_db()
        # self.load_templates_from_db()
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
        for key, item in template_items.items():
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
                items[blank_item.item_identifier()] = blank_item
                items[key] = item
                prev_item = item
            elif prev_item.item_type() == ItemType.SONG and item.item_type() == ItemType.HEADER:
                blank_item = self.make_blank_item()
                items[blank_item.item_identifier()] = blank_item
                items[key] = item
                prev_item = item
            elif prev_item.item_type() == ItemType.FOLDER and item.item_type() == ItemType.HEADER:
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

            item_id = column1.data(Qt.ItemDataRole.UserRole)
            #item_id = self.twItems.item(row, 0).data(Qt.ItemDataRole.UserRole)

            #item_id = column1.data(Qt.ItemDataRole.UserRole)
            item = self.current_template.item(item_id)

            if item.item_type() == ItemType.EMPTY:
                continue

            if item.item_type() == ItemType.HEADER:
                prev_hr = item.hour()
                prev_start_time = QTime(prev_hr, 0, 0)
                prev_dur = item.duration()
                item.set_item_row(row)
                continue

            # If item has no ID, mark it for creation
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

        ti = self.db_config.fetch_all_template_items(1111)
        self._setup_items_table()
        items = self._add_blank_rows(ti)

        print(items)

        self._populate_items_table(items)
        
        self.compute_start_times()


    def load_templates_from_db(self):
        self.templates = self.db_config.fetch_all_templates()

        for name, template in self.templates.items():
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

    def create_media_folders(self):
        tc = TreeConfig('tree.txt')
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

    def load_tracks(self):
        with open('tracks.csv',  newline='', encoding="utf-8-sig") as csvfile:
            reader = csv.reader(csvfile, delimiter=',', quotechar='"')
            for row in reader:
                track_id, title, artist_name, duration, artist_id, folder_id, file_path = row
                track = Track(int(track_id), title, artist_name, int(duration), 
                              int(artist_id), int(folder_id), file_path )
                self.tracks[int(track_id)] = track

    def on_media_item_clicked(self, item:QTreeWidgetItem):
        node_id = item.data(0, Qt.ItemDataRole.UserRole)
        text = item.text(0)
        self.item_clicked = "folder"
        self.current_folder = {'id': node_id, 'name':text}

        self.show_tracks(node_id)

    def show_tracks(self, folder_id: int):
       self.twTracks.clear()
       self.twTracks.setRowCount(0)
       self.twTracks.setColumnCount(4)
       self.twTracks.setColumnWidth(0, 350)
       self.twTracks.setColumnWidth(1, 250)
       self.twTracks.setColumnWidth(2, 80)
       self.twTracks.setColumnWidth(3, 50)
       self.twTracks.setColumnWidth(4, 100)
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
           self.twTracks.setItem(row, 3, QTableWidgetItem(str(track.track_id())))
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
            new_item.set_item_row(item.row())


        if self.item_clicked == "track":
            new_item = SongItem(self.current_track.title())
            new_item.set_duration(self.current_track.duration())
            new_item.set_title(self.current_track.title())
            new_item.set_folder_name(self.current_folder['name'])
            new_item.set_folder_id(self.current_folder['id'])
            new_item.set_item_id(self.current_track.track_id())
            new_item.set_artist_id(self.current_track.artist_id())
            new_item.set_artist_name(self.current_track.artist_name())
            new_item.set_item_path(self.current_track.file_path())

        if new_item is None:
            return

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

        if (item.item_id() == 0):
            self.twItems.setItem(row, 5, WidgetItem(""))
        else:
            self.twItems.setItem(row, 5, WidgetItem((str(item.item_id()))))

        self.twItems.setItem(row, 6, WidgetItem(item.item_path()))

        self.current_template.add_item(item)

    def test_folders(self):
        new_item = FolderItem("Folder")

        
            
