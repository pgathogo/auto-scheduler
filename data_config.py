import time
import csv

from PyQt5.QtCore import (
    QDate
)

from collections import OrderedDict

import sqlite3

from data_types import (
    DBAction,
    TemplateColumns,
    TemplateItemColumns,
    ItemType,
    ScheduleColumns
)

from template import Template

from template_item import (
    TemplateItem, 
    HeaderItem,
    BlankItem,
    FolderItem,
    SongItem
)
from schedule import Schedule

from track import Track


class DataConfiguration:
    def __init__(self, db_name: str):
        self._database = "data/templates.db"

    def _connect(self):
        return sqlite3.connect(self._database)

    def save(self,  data: dict) -> bool:
        for template_name, template in data.items():

            template_id = -1

            if template.db_action() == DBAction.CREATE:
                template_id = self._create_template(template)

            if template.db_action() == DBAction.UPDATE:
                template_id = self._update_template(template)

            if template.db_action() == DBAction.DELETE:
                self._delete_template_items(template)
                self._delete_template(template)
                continue

            if template.db_action() == DBAction.NONE:
                template_id = template.id()

            print(f'save template items...{len(template.items())}')
            self._save_template_items(template.items(), template_id)

        print(f"Saving templates...Done.")

    def _create_template(self, template) -> int:
        con = self._connect()
        curs = con.cursor()

        hours = ",".join([str(i) for i in template.hours()])
        dow = ",".join([str(i) for i in template.dow()])
        
        ins_stmt = (f"Insert into templateheader ('name', 'desc', 'hours', 'dow') " 
                    f" Values ('{template.name()}','{template.description()}','{hours}', '{dow}') RETURNING id;"
                    )

        print(f'Creating template {template.name()}...')
        new_id =  -1
        try:
            curs.execute(ins_stmt)
            new_id = curs.fetchone()[0]
        except:
            print(f"Error creating template {template.name()}")
        finally:
            con.commit()
            con.close()
            return new_id

    def _update_template(self, template) -> int:
        con = self._connect()
        curs = con.cursor()

        hours = ",".join([str(i) for i in template.hours()])
        dow = ",".join([str(i) for i in template.dow()])
        

        upd_stmt = (f"Update templateheader set name='{template.name()}', "
                    f" desc='{template.description()}', hours='{hours}', dow='{dow}' "
                    f" Where id={template.id()};"
                    )

        print(f'Updating template `{template.name()}`...')
        try:
            curs.execute(upd_stmt)
        except:
            print(f"Error creating template {template.name()}")
        finally:
            con.commit()
            con.close()
            return template.id()

    def _delete_template_items(self, template):
        con = self._connect()
        curs = con.cursor()

        del_stmt = f'Delete from templateitem Where template_id={template.id()};'
        print(f'Deleting template items for {template.name()}...')

        try:
            curs.execute(del_stmt)
        except:
            print(f"Error deleting template items for {template.name()}")
        finally:
            con.commit()
            con.close()

    def _delete_template(self, template):
        con = self._connect()
        curs = con.cursor()

        del_stmt = f'Delete from templateheader Where id={template.id()};'
        print(f'Deleting template {template.name()}...')

        try:
            curs.execute(del_stmt)
        except:
            print(f"Error deleting template {template.name()}")
        finally:
            con.commit()
            con.close()


    def _save_template_items(self, template_items: dict, template_id: int):

        for identifier, item in template_items.items():
            if item.item_type() == ItemType.EMPTY:
                continue

            if item.db_action() == DBAction.CREATE:
                new_id = self._create_template_item(item, template_id)

            if item.db_action() == DBAction.UPDATE:
                self._update_template_item(item)

            if item.db_action() == DBAction.DELETE:
                self._delete_template_item(item)

        print(f"Creating template items...Done")

            
    def _create_template_item(self, item, template_id: int) -> int:
            con = self._connect()
            curs = con.cursor()

            item_type = int(item.item_type())

            start_time = item.start_time().toString("hh:mm:ss")
            hour = item.hour()
            duration = item.duration()
            title = item.title()
            artist_id = item.artist_id()
            artist_name = item.artist_name()
            folder_id = item.folder_id()
            item_path = item.item_path()
            track_id = item.track_id()
            item_row = item.item_row()
            item_identifier = item.item_identifier()
            folder_name = item.folder_name()
            rotation = item.rotation()
            genre = item.genre() if item.genre() is not None else -1

            print(f"Title: {title}: Rotation: {rotation} - Genre: {genre}")
            
            ins_stmt = (f'Insert into templateitem ("item_type", "start_time", "hour", "duration", "title","artist_name", "artist_id", '
                   f'"folder_id", "item_path", "item_id", "item_row", "item_identifier", "template_id", "folder_name", "rotation", "genre") VALUES '
                   f' ({item_type},"{start_time}",{hour},{duration},"{title}","{artist_name}", {artist_id},{folder_id}, '
                   f' "{item_path}",{track_id}, {item_row},"{item_identifier}", {template_id}, "{folder_name}", '
                   f' "{rotation}", {genre}) RETURNING id;' )

            new_id = -1
            try:
                curs.execute(ins_stmt)
                new_id = curs.fetchone()[0]
            except:
                print(f"Error creating template item {item.title()}")
            finally:
                con.commit()
                con.close()
                return new_id

    def _update_template_item(self, item):
        con = self._connect()
        curs = con.cursor()


        start_time = item.start_time().toString("hh:mm:ss")
        item_row = item.item_row()

        print(f"Start Time {start_time}: Item Title: {item.title()} - Rotation: {item.rotation()}")

        upd_stmt = (f'Update templateitem set "start_time"="{start_time}", '
                    f' "item_row"={item_row}, '
                    f' "rotation"="{item.rotation()}" '
                    f'Where id={item.id()};'
                )

        print(f'Updating template {item.title()}...')
        
        try:
            curs.execute(upd_stmt)
        except:
            print(f"Error updating template {item.title()}")
        finally:
            con.commit()
            con.close()

    def _delete_template_item(self, item):
        con = self._connect()
        curs = con.cursor()

        del_stmt = f'Delete from templateitem Where id={item.id()};'
        print(f'Deleting template item {item.title()}...')

        try:
            curs.execute(del_stmt)
        except:
            print(f"Error deleting template item {item.title()}")
        finally:
            con.commit()
            con.close()

    def delete_schedule_by_date(self, sched_date, sched_refs: list) ->bool:
        
        pass

    def execute_query(self, sql_stmt: str) -> bool:
        con = self._connect()
        curs = con.cursor()
        result = True
        try:
            curs.execute(sql_stmt)
            result = True
        except:
            print(f"Error executing query {sql_stmt}")
            result = False
        finally:
            con.commit()
            con.close()
            return result

    def fetch_data(self, sql_stmt: str) -> list:
        con = self._connect()
        curs = con.cursor()

        try:
            curs.execute(sql_stmt)
        except:
            print(f"Error executing query {sql_stmt}")
            con.close()
            return []

        rows = curs.fetchall()
        con.close()

        return rows

    def fetch_all_templates(self) ->dict:
        templates = {}

        con = self._connect()
        curs = con.cursor()

        sel_stmt = f"Select id, name, desc, hours, dow From templateheader;"
        curs.execute(sel_stmt)

        rows = curs.fetchall()

        for row in rows:
            template = self._make_template(row)
            items = self.fetch_template_items(template)


            items_with_blanks = self._insert_blank_rows(items)
            template.assign_items(items_with_blanks)

            templates[template.name()] = template

        con.close

        return templates

    def fetch_template_items(self, template) ->OrderedDict:
        items = OrderedDict()
        con = self._connect()
        curs = con.cursor()

        sel_stmt = (f"Select id, item_type, start_time, hour, duration, title, "
                    f" artist_id, artist_name, folder_id, item_path, item_id, "
                    f" item_row, item_identifier, template_id, folder_name, rotation, genre "
                    f" From templateitem Where template_id = {template.id()} order by hour, item_row;")

        curs.execute(sel_stmt)

        rows = curs.fetchall()

        for row in rows:
            item = self._make_template_item(row)

            if item is None:
                continue
                
            items[item.item_identifier()] = item
            #template.add_item(item)
        con.close

        return items


    def record_exists(self, sql_stmt: str):
        con = self._connect()
        curs = con.cursor()

        curs.execute(sql_stmt)
        
        rows = curs.fetchall()
        con.close

        return True if len(rows) > 0 else False


    def _make_template_item(self, db_record):
        id = int(db_record[int(TemplateItemColumns.ID)])
        item_type = ItemType(db_record[int(TemplateItemColumns.ITEM_TYPE)])
        start_time = db_record[int(TemplateItemColumns.START_TIME)]
        hour = int(db_record[int(TemplateItemColumns.HOUR)])
        duration = int(db_record[int(TemplateItemColumns.DURATION)])
        title = db_record[int(TemplateItemColumns.TITLE)]
        artist_id = int(db_record[int(TemplateItemColumns.ARTIST_ID)])
        artist_name = db_record[int(TemplateItemColumns.ARTIST_NAME)]
        folder_id = int(db_record[int(TemplateItemColumns.FOLDER_ID)])
        item_path = db_record[int(TemplateItemColumns.ITEM_PATH)]
        track_id = int(db_record[int(TemplateItemColumns.TRACK_ID)])
        item_row = int(db_record[int(TemplateItemColumns.ITEM_ROW)])
        item_identifier = db_record[int(TemplateItemColumns.ITEM_IDENTIFIER)]
        template_id = int(db_record[int(TemplateItemColumns.TEMPLATE_ID)])
        folder_name = db_record[int(TemplateItemColumns.FOLDER_NAME)]
        rotation = db_record[int(TemplateItemColumns.ROTATION)]
        genre = db_record[int(TemplateItemColumns.GENRE)]

        template_item = None

        if item_type == ItemType.HEADER:
            template_item = HeaderItem(title)

        if item_type == ItemType.EMPTY:
            template_item = BlankItem()

        if item_type == ItemType.FOLDER:
            template_item = FolderItem(title)

        if item_type == ItemType.SONG:
            template_item = SongItem(title)

        if template_item is None:
            return None

        template_item.set_id(id)
        template_item.set_start_time(start_time)
        template_item.set_hour(hour)
        template_item.set_duration(duration)
        template_item.set_title(title)
        template_item.set_artist_id(artist_id)
        template_item.set_artist_name(artist_name)
        template_item.set_folder_id(folder_id)
        template_item.set_item_path(item_path)
        template_item.set_track_id(track_id)
        template_item.set_item_row(item_row)
        template_item.set_item_identifier(item_identifier)
        template_item.set_template_id(template_id)
        template_item.set_folder_name(folder_name)
        template_item.set_db_action(DBAction.NONE)
        template_item.set_item_type(item_type)
        template_item.set_rotation(rotation)
        template_item.set_genre(genre)

        return template_item


    def _make_template(self, db_record):
        id = db_record[int(TemplateColumns.ID)]
        name = db_record[int(TemplateColumns.NAME)]
        desc = db_record[int(TemplateColumns.DESC)]
        hours_str = db_record[(TemplateColumns.HOURS)]
        dow_str = db_record[(TemplateColumns.DOW)]

        template = Template(name)

        template.set_id(id)
        template.set_name(name)
        template.set_description(desc)

            
        hours = [int(h) for h in hours_str.split(',')]
        template.set_hours(hours)

        if dow_str is not None:
            dow = [int(d) for d in dow_str.split(',')]
            template.set_dow(dow)

        return template

    def _insert_blank_rows(self, t_items: OrderedDict) -> OrderedDict:
        items = OrderedDict()

        prev_item = None

        for key, item in t_items.items():

            if prev_item is None:
                items[item.item_identifier()] = item
                prev_item = item

            elif prev_item.item_type() == ItemType.HEADER and item.item_type() == ItemType.HEADER:

                blank_item = self._make_blank_item()
                items[blank_item.item_identifier()] = blank_item
                items[item.item_identifier()] = item

                prev_item = item

            elif prev_item.item_type() == ItemType.SONG and item.item_type() == ItemType.HEADER:
                blank_item = self._make_blank_item()

                items[blank_item.item_identifier()] =  blank_item
                items[item.item_identifier()] = item

                prev_item = item

            elif prev_item.item_type() == ItemType.FOLDER and item.item_type() == ItemType.HEADER:
                blank_item = self._make_blank_item()

                items[blank_item.item_identifier()] =  blank_item
                items[item.item_identifier()] = item

                prev_item = item

            else:
                items[item.item_identifier()] = item
                prev_item = item

            #time.sleep(0.05)

        last_blank = self._make_blank_item()
        items[last_blank.item_identifier()] = last_blank

        return items


    def fetch_schedule_by_date(self, date: QDate) ->list:
        schedule_items = []
        con = self._connect()
        curs = con.cursor()

        sel_stmt = (f"SELECT id, schedule_ref, schedule_date, template_id, start_time, "
                    f" schedule_hour, item_identifier, item_type, duration, title, "
	                f" artist_id, artist_name, folder_id, folder_name, track_id, filepath, item_row "
                    f" FROM schedule "
                    f" WHERE schedule_date = '{date.toString('yyyy-MM-dd')}' "
                    )
        curs.execute(sel_stmt)

        rows = curs.fetchall()

        for row in rows:
            schedule_item = self._make_schedule_item(row)

            if schedule_item is None:
                continue

            schedule_items.append(schedule_item)

        con.close()

        return schedule_items


    def fetch_schedule_by_template_and_date_range(self, template_id: int, start_date: QDate, end_date: QDate) -> list:
        schedule_items = []
        con = self._connect()
        curs = con.cursor() 

        if end_date is None:
            date_filter = f" AND schedule_date >= '{start_date.toString('yyyy-MM-dd')}' "
        else:
            date_filter = (f" AND schedule_date BETWEEN '{start_date.toString('yyyy-MM-dd')}' "
                           f" AND '{end_date.toString('yyyy-MM-dd')}' ")

        sel_stmt = (f"SELECT id, schedule_ref, schedule_date, template_id, start_time, "
                    f" schedule_hour, item_identifier, item_type, duration, title, "
                    f" artist_id, artist_name, folder_id, folder_name, track_id, filepath, item_row "
                    f" FROM schedule "
                    f" WHERE template_id = {template_id} "
                    f" {date_filter}"
                    )
        curs.execute(sel_stmt)

        rows = curs.fetchall()

        for row in rows:
            schedule_item = self._make_schedule_item(row)

            if schedule_item is None:
                continue

            schedule_items.append(schedule_item)

        con.close()

        return schedule_items

    def _make_schedule_item(self, db_record):
        id = int(db_record[int(ScheduleColumns.ID)])
        schedule_ref = db_record[int(ScheduleColumns.SCHEDULE_REF)]
        schedule_date = db_record[int(ScheduleColumns.SCHEDULE_DATE)]
        template_id = int(db_record[int(ScheduleColumns.TEMPLATE_ID)])
        start_time = db_record[int(ScheduleColumns.START_TIME)]
        schedule_hour = int(db_record[int(ScheduleColumns.SCHEDULE_HOUR)])
        item_identifier = db_record[int(ScheduleColumns.ITEM_IDENTIFIER)]
        item_type = int(db_record[int(ScheduleColumns.ITEM_TYPE)])
        duration = int(db_record[int(ScheduleColumns.DURATION)])
        title = db_record[int(ScheduleColumns.TITLE)]
        artist_id = int(db_record[int(ScheduleColumns.ARTIST_ID)])
        artist_name = db_record[int(ScheduleColumns.ARTIST_NAME)]
        folder_id = int(db_record[int(ScheduleColumns.FOLDER_ID)])
        folder_name = db_record[int(ScheduleColumns.FOLDER_NAME)]
        track_id = int(db_record[int(ScheduleColumns.TRACK_ID)])
        filepath = db_record[int(ScheduleColumns.FILEPATH)]
        item_row = int(db_record[int(ScheduleColumns.ITEM_ROW)])

        schedule_item = None
        if item_type == ItemType.HEADER:
            schedule_item = HeaderItem(title)

        if item_type == ItemType.EMPTY:
            schedule_item = BlankItem()

        if item_type == ItemType.FOLDER:
            schedule_item = FolderItem(title)

        if item_type == ItemType.SONG:
            schedule_item = SongItem(title)

        if schedule_item is None:
            return None

        schedule_item.set_id(id)
        schedule_item.set_start_time(start_time)
        schedule_item.set_hour(schedule_hour)
        schedule_item.set_duration(duration)
        schedule_item.set_title(title)
        schedule_item.set_artist_id(artist_id)
        schedule_item.set_artist_name(artist_name)
        schedule_item.set_folder_id(folder_id)
        schedule_item.set_item_path(filepath)
        schedule_item.set_track_id(track_id)
        schedule_item.set_item_row(item_row)
        schedule_item.set_item_identifier(item_identifier)
        schedule_item.set_template_id(template_id)
        schedule_item.set_folder_name(folder_name)
        schedule_item.set_db_action(DBAction.NONE)
        schedule_item.set_item_type(item_type)
        schedule_item.set_schedule_ref(schedule_ref)
        schedule_item.set_schedule_date(QDate.fromString(schedule_date, "yyyy-MM-dd"))

        return schedule_item


    def _make_blank_item(self):
        blank = BlankItem()
        blank.set_start_time("")
        return blank

    def _print_template_items(self, titems:OrderedDict):
        for key, item in titems.items():
            print(item)


        

