from enum import (
    Enum,
    IntEnum
)

class ItemType(IntEnum):
    EMPTY = -1
    HEADER = 0
    SONG = 1
    FOLDER = 2
    FIRST_COLUMN=3
    COMMERCIAL_BREAK=4

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

MSSQL_CONN = {
    'server': "localhost",
    'database': "citizenfm",
    'username': "sa",
    'password': "abc123",
}



    
    