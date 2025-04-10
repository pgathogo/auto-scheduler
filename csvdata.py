import csv

from track import Track

class CSVData:
    def __init__(self):
        pass

    def load_tracks(self):
        tracks = {}
        with open('data/tracks.csv',  newline='', encoding="utf-8-sig") as csvfile:
            reader = csv.reader(csvfile, delimiter=',', quotechar='"')
            for row in reader:

                track_id, title, artist_name, duration, artist_id, folder_id, file_path = row

                track = Track(int(track_id))

                track.set_title(title)
                track.set_artist_id(int(artist_id))
                track.set_artist_name(artist_name)
                track.set_folder_id(int(folder_id))
                track.set_file_path(file_path)
                track.set_duration(int(duration))

                tracks[int(track_id)] = track

        return tracks
