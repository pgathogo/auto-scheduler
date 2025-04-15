import time
import csv

from collections import OrderedDict

import sqlite3

from data_types import (
    DBAction,
    TemplateColumns,
    TemplateItemColumns,
    ItemType
)

from template import Template

from template_item import (
    TemplateItem, 
    HeaderItem,
    BlankItem,
    FolderItem,
    SongItem
)

from track import Track


class DataConfiguration:
    def __init__(self, db_name: str):
        self._database = db_name

    def _connect(self):
        return sqlite3.connect(self._database)

    def save(self,  data: dict):
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

        ins_stmt = (f"Insert into templateheader ('name', 'desc', 'hours') " 
                    f" Values ('{template.name()}','{template.description()}','{hours}') RETURNING id;"
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

        upd_stmt = (f"Update templateheader set name='{template.name()}', desc='{template.description()}', hours='{hours}' "
                    f" Where id={template.id()};"
                    )

        print(f'Updating template {template.name()}...')
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
            
            ins_stmt = (f'Insert into templateitem ("item_type", "start_time", "hour", "duration", "title","artist_name", "artist_id", '
                   f'"folder_id", "item_path", "item_id", "item_row", "item_identifier", "template_id", "folder_name") VALUES '
                   f' ({item_type},"{start_time}",{hour},{duration},"{title}","{artist_name}", {artist_id},{folder_id}, '
                   f' "{item_path}",{track_id}, {item_row},"{item_identifier}",{template_id}, "{folder_name}" ) RETURNING id;' )

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

        upd_stmt = (f'Update templateitem set "start_time"="{start_time}", "item_row"={item_row}, '
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

    def execute_query(self, sql_stmt: str):
        con = self._connect()
        curs = con.cursor()
        try:
            curs.execute(sql_stmt)
        except:
            print(f"Error executing query {sql_stmt}")
        finally:
            con.commit()
            con.close()

    def fetch_all_templates(self) ->dict:
        templates = {}

        con = self._connect()
        curs = con.cursor()

        sel_stmt = f"Select id, name, desc, hours From templateheader;"
        curs.execute(sel_stmt)

        rows = curs.fetchall()

        for row in rows:
            template = self._make_template(row)
            items = self.fetch_template_items(template)


            print('Adding blank rows...')
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
                    f" item_row, item_identifier, template_id, folder_name "
                    f" From templateitem Where template_id = {template.id()} order by hour, item_row;"
                
        )

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
        

        return template_item


    def _make_template(self, db_record):
        id = db_record[int(TemplateColumns.ID)]
        name = db_record[int(TemplateColumns.NAME)]
        desc = db_record[int(TemplateColumns.DESC)]
        hours_str = db_record[(TemplateColumns.HOURS)]

        template = Template(name)

        template.set_id(id)
        template.set_name(name)
        template.set_description(desc)

        hours = [int(h) for h in hours_str.split(',')]
        template.set_hours(hours)

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

    def _make_blank_item(self):
        blank = BlankItem()
        blank.set_start_time("")
        return blank

    def _print_template_items(self, titems:OrderedDict):
        for key, item in titems.items():
            print(item)


        

