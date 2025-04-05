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


class DataConfiguration:
    def __init__(self, db_name: str):
        self._database = db_name

    def _connect(self):
        return sqlite3.connect(self._database)

    def save(self,  data: dict):

        for template_name, template in data.items():

            if template.db_action() == DBAction.NONE:
                continue

            if template.db_action() == DBAction.CREATE:
                self._create_template(template)


    def _create_template(self, template):
        con = self._connect()
        curs = con.cursor()

        hours = ",".join([str(i) for i in template.hours()])

        ins_stmt = (f"Insert into templateheader ('name', 'desc', 'hours') " 
                    f" Values ('{template.name()}','{template.description()}','{hours}') RETURNING id;"
                    )

        print(f'Creating template {template.name()}...')

        # curs.execute(ins_stmt)
        # new_id = curs.fetchone()[0]

        new_id = 1111
        
        print(f'Creating template items...{len(template.items())}')
        self._create_template_items(template.items(), new_id, con)

        con.commit()
        con.close()

    def _create_template_items(self, template_items: dict, template_id: int, con: sqlite3.Connection):

        curs = con.cursor()

        for identifier, item in template_items.items():
            if item.item_type() == ItemType.EMPTY:
                continue

            item_type = int(item.item_type())

            start_time = item.start_time().toString("hh:mm:ss")
            hour = item.hour()
            duration = item.duration()
            title = item.title()
            artist_id = item.artist_id()
            artist_name = item.artist_name()
            folder_id = item.folder_id()
            item_path = item.item_path()
            item_id = item.item_id()
            item_row = item.item_row()
            item_identifier = item.item_identifier()
            folder_name = item.folder_name()
            
            ins_stmt = (f'Insert into templateitem ("item_type", "start_time", "hour", "duration", "title","artist_name", "artist_id", '
                   f'"folder_id", "item_path", "item_id", "item_row", "item_identifier", "template_id", "folder_name") VALUES '
                   f' ({item_type},"{start_time}",{hour},{duration},"{title}","{artist_name}", {artist_id},{folder_id}, '
                   f' "{item_path}",{item_id}, {item_row},"{item_identifier}",{template_id}, "{folder_name}" )' )

            print(ins_stmt)
            curs.execute(ins_stmt)
            con.commit()

    def fetch_all_templates(self) ->dict:
        templates = {}

        con = self._connect()
        curs = con.cursor()

        sel_stmt = f"Select id, name, desc, hours From templateheader;"
        curs.execute(sel_stmt)

        rows = curs.fetchall()

        for row in rows:
            template = self._make_template(row)
            templates[template.name()] = template

        con.close

        return templates

    def fetch_all_template_items(self, template_id: int) ->dict:
        items = {}

        con = self._connect()
        curs = con.cursor()

        sel_stmt = (f"Select id, item_type, start_time, hour, duration, title, "
                    f" artist_id, artist_name, folder_id, item_path, item_id, "
                    f" item_row, item_identifier, template_id, folder_name "
                    f" From templateitem Where template_id = {template_id} order by item_row;"
                
        )

        print(sel_stmt)
        curs.execute(sel_stmt)

        rows = curs.fetchall()

        for row in rows:
            item = self._make_template_item(row)

            if item is None:
                continue
                
            items[item.item_identifier()] = item

        con.close

        return items

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
        item_id = int(db_record[int(TemplateItemColumns.ITEM_ID)])
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
        template_item.set_item_id(item_id)
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

        template.hour = hours

        return template




        

