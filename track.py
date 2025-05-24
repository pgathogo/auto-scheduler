
class Track:
    def __init__(self, track_id: int):
        self._track_id = track_id
        self._title = ""
        self._artist_name = ""
        self._duration = 0
        self._artist_id = -1
        self._folder_id = -1
        self._file_path = ""
        self._genre = -1

    def track_id(self) -> int:
        return self._track_id

    def set_track_id(self, id: int):
        self._track_id = id

    def title(self) -> str:
        return self._title

    def set_title(self, title: str):
        self._title = title

    def artist_name(self) -> str:
        return self._artist_name

    def set_artist_name(self, name: str):
        self._artist_name = name

    def duration(self) -> str:
        return self._duration

    def set_duration(self, dur: int):
        self._duration = dur

    def artist_id(self) -> int:
        return self._artist_id

    def set_artist_id(self, id: int):
        self._artist_id = id

    def folder_id(self) -> int:
        return self._folder_id

    def set_folder_id(self, fid: int):
        self._folder_id = fid

    def file_path(self) -> str:
        return self._file_path

    def set_file_path(self, fpath: str):
        self._file_path = fpath

    def genre(self) -> int:
        return self._genre
    
    def set_genre(self, genre: int):
        self._genre = genre

    def formatted_track_id(self) ->str:
        return(f"{self._track_id:08d}")

    def formatted_duration(self) ->str:
        seconds = self._duration // 1000
        hours = seconds // 3600
        seconds %= 3600
        minutes = seconds // 60
        seconds %= 60
    
        # Format as "HH:MM:SS"
        return f"{hours:02}:{minutes:02}:{seconds:02}"