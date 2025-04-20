from PyQt5.QtCore import (
    QDate,
    QTime
    )

from data_types import (
    ItemType
)

class Schedule():
    def __init__(self):
        self._id = -1
        self._schedule_ref = ""
        self._schedule_date = QDate(0,0,0)
        self._template_id = -1
        self._start_time = QTime(0,0,0)
        self._schedule_hour = -1
        self._item_identifier = "" 
        self._item_type = ItemType.EMPTY
        self._duration = 0
        self._title = ""
        self._artist_id = -1
        self._artist_name = ""
        self._folder_id = -1
        self._folder_name = ""
        self._track_id = -1
        self._filepath = ""
        self._item_row = -1

    def id(self) -> int:
        return self._id

    def set_id(self, id: int):
        self._id = id

    def schedule_ref(self) -> str:
        return self._schedule_ref

    def set_schedule_ref(self, ref: str):
        self._schedule_ref = ref

    def schedule_date(self) -> QDate:
        return self._schedule_date

    def set_schedule_date(self, date: QDate):
        self._schedule_date = date

    def template_id(self) -> int:
        return self._template_id

    def set_template_id(self, id: int):
        self._template_id = id

    def start_time(self) -> QTime:
        return self._start_time

    def set_start_time(self, time: QTime):
        self._start_time = time

    def schedule_hour(self) -> int:
        return self._schedule_hour

    def set_schedule_hour(self, hour: int):
        self._schedule_hour = hour

    def item_identifier(self) -> str:
        return self
    
    def set_item_identifier(self, identifier: str):
        self._item_identifier = identifier

    def item_type(self) -> ItemType:
        return self._item_type

    def set_item_type(self, item_type: ItemType):
        self._item_type = item_type

    def duration(self) -> int:
        return self._duration

    def set_duration(self, duration: int):
        self._duration = duration

    def title(self) -> str:
        return self._title

    def set_title(self, title: str):
        self._title = title

    def artist_id(self) -> int:
        return self._artist_id

    def set_artist_id(self, artist_id: int):
        self._artist_id = artist_id

    def artist_name(self) -> str:
        return self._artist_name

    def set_artist_name(self, artist_name: str):
        self._artist_name = artist_name

    def folder_id(self) -> int:
        return self._folder_id

    def set_folder_id(self, folder_id: int):
        self._folder_id = folder_id

    def folder_name(self) -> str:
        return self._folder_name

    def set_folder_name(self, folder_name: str):
        self._folder_name = folder_name

    def track_id(self) -> int:
        return self._track_id

    def set_track_id(self, track_id: int):
        self._track_id = track_id

    def filepath(self) -> str:
        return self._filepath

    def set_filepath(self, filepath: str):
        self._filepath = filepath

    def item_row(self) -> int:
        return self._item_row

    def set_item_row(self, item_row: int):
        self._item_row = item_row
