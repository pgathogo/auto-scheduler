from PyQt5.QtWidgets import (
    QTableWidgetItem
)

from PyQt5.QtGui import (
    QColor
)

from PyQt5.QtCore import (
    Qt,
    QTime
)

import datetime
from enum import Enum

from data_types import (
    DBAction,
    ItemType
)

class TemplateItem():
    def __init__(self, item_title: str=""):
        self._id = -1
        self._item_type = ItemType.EMPTY
        self._start_time = QTime()
        self._formatted_time = ""
        self._hour = -1
        self._duration = 0
        self._title = ""
        self._artist_id = -1
        self._artist_name = ""
        self._folder_name = ""
        self._folder_id = -1
        self._item_path=""
        self._track_id = 0
        self._item_row = -1
        self._item_title = item_title
        self._time_stamp = self.generate_time_stamp()    
        self._db_action = DBAction.NONE
        self._item_identifier = ""
        self._template_id = -1

        self.make_item_identifier()


    def set_start_time(self, time:QTime):
        self._start_time = time

    def start_time(self) -> str:
        return self._start_time

    def formatted_start_time(self) ->str:
        return self._start_time.toString("HH:mm:ss")
        
    def set_formatted_start_time(self, stime:QTime):
        self._formatted_time = stime

    def formatted_time(self) -> str:
        return self._formatted_time

    def set_formatted_time(self, hr:int):
        hour_str = f"{hr:02d}:00:00"
        self._formatted_time = hour_str

    def set_hour(self, hour:int):
        self._hour = hour
        self.set_formatted_time(hour)

    def hour(self) -> int:
        return self._hour

    def item_row(self) -> int:
        return self._item_row
    
    def set_item_row(self, row:int):
        self._item_row = row

    def set_duration(self, length:int):
        self._duration = length

    def duration(self) -> int:
        return self._duration

    def formatted_duration(self) -> str:
        return ""

    def set_title(self, title:str):
        self._title = title

    def title(self) -> str:
        return self._title

    def set_artist_name(self, artist:str):
        self._artist_name = artist

    def artist_name(self) -> str:
        return self._artist_name

    def set_artist_id(self, id:int):
        self._artist_id = id

    def artist_id(self) -> int:
        return self._artist_id

    def set_folder_name(self, folder_name: str):
        self._folder_name = folder_name

    def folder_name(self)-> str:
        return self._folder_name

    def set_folder_id(self, id: int):
        self._folder_id = id

    def folder_id(self)-> int:
        return self._folder_id

    def set_track_id(self, id: int):
        self._track_id = id

    def track_id(self)->int:
        return self._track_id

    def item_type(self) -> ItemType:
        return self._item_type

    def set_item_type(self, item_type: ItemType):
        self._item_type = item_type

    def set_item_path(self, ip: str):
        self._item_path = ip

    def item_path(self)->str:
        return self._item_path

    def generate_time_stamp(self) -> str:
        dt = datetime.datetime.now()
        print(f"TemplateItem: {dt}")
        return f"{dt.day}{dt.month}{dt.year}{dt.hour}{dt.minute}{dt.second}{dt.microsecond}"

    def time_stamp(self):
        return self._time_stamp

    def item_identifier(self) -> str:
        return self._item_identifier

    def set_item_identifier(self, identifier: str):
        self._item_identifier = identifier

    def template_id(self) -> int:
        return self._template_id

    def set_template_id(self, id: int):
        self._template_id = id

    def make_item_identifier(self) ->str:
        raise NotImplementedError()

    def id(self) -> int:
        return self._id
    
    def set_id(self, i : int):
        self._id = i

    def db_action(self) -> DBAction:
        return self._db_action
    
    def set_db_action(self, action: DBAction):
        self._db_action = action

    def formatted_track_id(self) ->str:
        return(f"{self._track_id:08d}")
        

class HeaderItem(TemplateItem):
    def __init__(self, item_title: str=""):
        super(HeaderItem, self).__init__(item_title)
        self._title = "HEADER"
        self._item_type = ItemType.HEADER

    def make_item_identifier(self) -> str:
        ts = self.time_stamp()
        self._item_identifier = f"HEADER{ts}"

    def title(self) -> str:
        return self._title

    def artist_name(self) ->str:
        return self._title

class BlankItem(TemplateItem):
    def __init__(self, item_title: str=""):
        super(BlankItem, self).__init__(item_title)
        self._title = ""
        self._item_type = ItemType.EMPTY

    def make_item_identifier(self) -> str:
        ts = self.time_stamp()
        self._item_identifier = f"blank{ts}"

    def title(self) -> str:
        return self._title


class FolderItem(TemplateItem):
    def __init__(self, item_title:str=""):
        super(FolderItem, self).__init__(item_title)
        self._item_type = ItemType.FOLDER
        self._title = item_title

    def make_item_identifier(self) -> str:
        ts = self.time_stamp()
        self._item_identifier = f"FOLDER{ts}"

    def title(self) -> str:
        return ""

    # def folder_name(self) ->str:
    #     return self._title

    def artist_name(self) ->str:
        return self._title
    


class SongItem(TemplateItem):
    def __init__(self, item_title:str=""):
        super(SongItem, self).__init__(item_title)
        self._item_type = ItemType.SONG
        self._title = item_title

    def make_item_identifier(self)-> str:
        ts = self.time_stamp()
        self._item_identifier = f"SONG{ts}"

    def title(self)-> str:
        return self._title

    def duration(self):
        return self._duration

    def formatted_duration(self):
        return self.format_audio_len(self.duration())

    def format_audio_len(self, audio_len: int):
        seconds = audio_len // 1000
        hours = seconds // 3600
        seconds %= 3600
        minutes = seconds // 60
        seconds %= 60
    
        # Format as "HH:MM:SS"
        return f"{hours:02}:{minutes:02}:{seconds:02}"

    def artist_name(self) ->str:
        return self._artist_name


class CommercialBreakItem(TemplateItem):
    def __init__(self, item_title:str=""):
        super(CommercialBreakItem, self).__init__(item_title)
        self._item_type = ItemType.COMMERCIAL_BREAK
        self._title = item_title
        self._booked_spots = -1

    def make_item_identifier(self):
        ts = self.time_stamp()
        self._item_identifier = f"COMM{ts}"

    def title(self):
        return self._title

    def set_booked_spots(self, booked_spots:int):
        self._booked_spots = booked_spots

    def booked_spots(self) -> int:
        return self._booked_spots

    # def set_artist_name(self, artist_name:str):
    #     self._artist_name = artist_name
    # def item_id(self):
    #     return self._item_id

# Table Widget Items 

class BaseTableWidgetItem(QTableWidgetItem):
    widget_register = {}
    def __init__(self, text: str):
        super(BaseTableWidgetItem, self).__init__(text)

    @classmethod
    def register(cls):
        BaseTableWidgetItem.widget_register[cls.TYPE_INFO] = cls

class HeaderTableWidgetItem(BaseTableWidgetItem):
    TYPE_INFO = ItemType.HEADER
    def __init__(self, text: str):
        super(HeaderTableWidgetItem, self).__init__(text)
        self.setBackground(QColor(189,189,189))
        self.setTextAlignment(Qt.AlignCenter)
        self.setFlags(Qt.NoItemFlags)

HeaderTableWidgetItem.register()


class BlankTableWidgetItem(BaseTableWidgetItem):
    TYPE_INFO = ItemType.EMPTY
    def __init__(self, text: str):
        super(BlankTableWidgetItem, self).__init__(text)

BlankTableWidgetItem.register()


class FolderTableWidgetItem(BaseTableWidgetItem):
    TYPE_INFO = ItemType.FOLDER
    def __init__(self, text: str):
        super(FolderTableWidgetItem, self).__init__(text)
        self.setBackground(QColor(253,230,224))

FolderTableWidgetItem.register()


class SongTableWidgetItem(BaseTableWidgetItem):
    TYPE_INFO = ItemType.SONG
    def __init__(self, text: str):
        super(SongTableWidgetItem, self).__init__(text)

SongTableWidgetItem.register()

class FirstColumnTableWidgetItem(BaseTableWidgetItem):
    TYPE_INFO = ItemType.FIRST_COLUMN
    def __init__(self, text: str):
        super(FirstColumnTableWidgetItem, self).__init__(text)
        self.setBackground(QColor(245,245,245))

FirstColumnTableWidgetItem.register()


class CommercialBreakTableWidgetItem(BaseTableWidgetItem):
    TYPE_INFO = ItemType.COMMERCIAL_BREAK
    def __init__(self, text: str):
        super(CommercialBreakTableWidgetItem, self).__init__(text)
        self.setBackground(QColor(234, 234, 116))

CommercialBreakTableWidgetItem.register()





    