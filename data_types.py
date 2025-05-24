import winreg

from enum import (
    Enum,
    IntEnum
)

from PyQt5.QtWidgets import (
    QComboBox
)

class ItemType(IntEnum):
    EMPTY = -1
    HEADER = 0
    SONG = 1
    FOLDER = 2
    FIRST_COLUMN=3
    COMMERCIAL_BREAK=4
    SCHEDULE_ITEM=5

class DBAction(IntEnum):
    NONE = 0
    CREATE = 1
    UPDATE = 2
    DELETE = 3


class TemplateColumns(IntEnum):
    ID = 0
    NAME = 1
    DESC = 2
    HOURS = 3
    DOW = 4

class TemplateItemColumns(IntEnum):
    ID = 0
    ITEM_TYPE = 1
    START_TIME = 2
    HOUR = 3
    DURATION=4
    TITLE=5
    ARTIST_ID=6
    ARTIST_NAME=7
    FOLDER_ID=8
    ITEM_PATH=9
    TRACK_ID=10
    ITEM_ROW=11
    ITEM_IDENTIFIER=12
    TEMPLATE_ID=13
    FOLDER_NAME=14
    ROTATION=15
    GENRE=16

class ScheduleColumns(IntEnum):
    ID = 0
    SCHEDULE_REF = 1
    SCHEDULE_DATE = 2
    TEMPLATE_ID = 3
    START_TIME = 4
    SCHEDULE_HOUR = 5
    ITEM_IDENTIFIER = 6
    ITEM_TYPE = 7
    DURATION = 8
    TITLE = 9
    ARTIST_ID = 10
    ARTIST_NAME = 11
    FOLDER_ID = 12
    FOLDER_NAME = 13
    TRACK_ID = 14
    FILEPATH = 15
    ITEM_ROW = 16

class TrackColumns(IntEnum):
    TRACK_REFERENCE = 0
    TRACK_TITLE = 1
    ARTIST_SEARCH = 2
    DURATION = 3
    ARTISTID_1 = 4
    FOLDER_ID = 5
    FILEPATH = 6
    GENRE = 7

class CommercialColumn(IntEnum):
    SCHEDULE_DATE = 0
    SCHEDULE_TIME = 1
    SCHEDULE_HOUR = 2
    BOOKED_SPOTS = 3
    BOOKED_DURATION = 4


class RotationComboBox(QComboBox):
    def __init__(self, item: "TemplateItem"):
        super(RotationComboBox, self).__init__()
        self.add_items()
        self.set_current_index(item.rotation())
        self.item = item

    def add_items(self):
        self.addItem("None", "N")
        self.addItem("Random", "R")

    def set_current_index(self, rotation: str):
        index = self.findData(rotation)
        self.setCurrentIndex(index)

    def on_current_index_changed(self, index: int):
        if index == 0:
            self.item.set_rotation("N")
        elif index == 1:
            self.item.set_rotation("R")


def read_registry()->dict:
    access_reg = winreg.ConnectRegistry(None, winreg.HKEY_LOCAL_MACHINE)
    access_key = winreg.OpenKey(access_reg, "SOFTWARE\Proxima\StudioONE\Data")
    conn_str = winreg.QueryValueEx(access_key, "ConnectionString")
    tokens = conn_str[0].split(";")
    for tok in tokens:
        if tok.strip().lower().startswith("password"):
            password = tok.split("=")[1]
        if tok.strip().lower().startswith("data"):
            server = tok.split("=")[1]
        if tok.strip().lower().startswith("initial"):
            database = tok.split("=")[1]
        if tok.strip().lower().startswith("user"):
            username = tok.split("=")[1]

    conn = {
        "server": server,
        "database": database,
        "username": username,
        "password": password
    } 
    return conn


MSSQL_CONN = read_registry()



    
    