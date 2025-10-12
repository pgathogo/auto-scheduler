import pyodbc

from PyQt5.QtCore import QDate

from collections import OrderedDict

from data_types import (
    DBAction,
    TemplateColumns,
    TemplateItemColumns,
    ItemType,
    ScheduleColumns
)

from template import (
    Template 
)

from template_item import (
    HeaderItem,
    BlankItem,
    FolderItem,
    SongItem
)

from data_types import MSSQL_CONN


class MSSQLData:
    def __init__(self, server, database, username, password):
        self._server = server      
        self._database = database  
        self._username = username  
        self._password = password  
        self._sql_driver ="{ODBC Driver 18 for SQL Server}"

        self.conn_str = (f"DRIVER={self._sql_driver};"
                        f"TrustServerCertificate=yes;"
                        f"SERVER={self._server};"
                        f"DATABASE={self._database};"
                        f"UID={self._username};"
                        f"PWD={self._password};"
                        )

        self.conn = None

    def database(self):
        return self._database
    
    def server(self):
        return self._server

    def connect(self):
        try:
            self.conn = pyodbc.connect(self.conn_str)
            return True
        except pyodbc.Error as ex:
            sqlstate = ex.args[0]
            print(f"Error connecting to database: {sqlstate}")
            return False

    def disconnect(self):
        if self.conn:
            self.conn.close()
            self.conn = None

    def execute_query(self, query: str):
        if not self.conn:
            if not self.connect():
                return None
        cursor = self.conn.cursor()
        try:
            cursor.execute(query)
            rows = cursor.fetchall()
            return rows
        except pyodbc.Error as ex:
            sqlstate = ex.args[0]
            print(f"Error executing query: {sqlstate}")
            return None

    def execute_non_query(self, query) ->tuple:
        if not self.conn:
            if not self.connect():
                return False
        cursor = self.conn.cursor()
        try:
            cursor.execute(query)
            self.conn.commit()
        except pyodbc.Error as ex:
            sqlstate = ex.args[0]
            msg = f"Error executing non-query: {sqlstate}"
            return False,msg

        return True,"OK"

    def execute_insert(self, query) ->int:
        if not self.conn:
            if not self.connect():
                return -1
        cursor = self.conn.cursor()
        new_id = -1
        try:
            cursor.execute(query)
            new_id = cursor.fetchval()
            self.conn.commit()
        except pyodbc.Error as ex:
            sqlstate = ex.args[0]
            print(f"Error executing insert: {sqlstate}")
            return -1

        return new_id

    def fetch_all_templates(self) ->dict:
        templates = {}

        sel_stmt = f"Select id, name, description, hours, dow From templateheader;"
        rows = self.execute_query(sel_stmt)

        if rows is None:
            return templates

        for row in rows:
            template = self._make_template(row)
            items = self.fetch_template_items(template)

            items_with_blanks = self._insert_blank_rows(items)
            template.assign_items(items_with_blanks)

            templates[template.name()] = template

        return templates

    def fetch_template_items(self, template) ->OrderedDict:
            items = OrderedDict()

            sel_stmt = (f"Select id, item_type, start_time, hour, duration, title, "
                        f" artist_id, artist_name, folder_id, item_path, item_id, "
                        f" item_row, item_identifier, template_id, folder_name, rotation, genre "
                        f" From templateitem Where template_id = {template.id()} order by hour, item_row;")

            rows = self.execute_query(sel_stmt)

            for row in rows:
                item = self._make_template_item(row)

                if item is None:
                    continue
                    
                items[item.item_identifier()] = item

            return items

    def fetch_schedule_by_template_and_date_range(self, template_id: int, start_date: QDate, end_date: QDate) -> list:
        self.mssql_conn = self._make_mssql_connection()

        schedule_items = []

        if end_date is None:
            date_filter = f" AND schedule_date >= '{start_date.toString('yyyy-MM-dd')}' "
        else:
            date_filter = (f" AND schedule_date BETWEEN '{start_date.toString('yyyy-MM-dd')}' "
                           f" AND '{end_date.toString('yyyy-MM-dd')}' ")

        sel_stmt = (f"SELECT id, schedule_ref, CAST(schedule_date AS DATE) AS schedule_date, template_id, start_time, "
                    f" schedule_hour, item_identifier, item_type, duration, title, "
                    f" artist_id, artist_name, folder_id, folder_name, track_id, filepath, item_row "
                    f" FROM AutoSchedule "
                    f" WHERE template_id = {template_id} "
                    f" {date_filter}"
                    f" AND duration > 0"
                    f" ORDER BY schedule_date"
                    )

        rows = self.execute_query(sel_stmt)

        for row in rows:
            schedule_item = self._make_schedule_item(row)

            if schedule_item is None:
                continue

            schedule_items.append(schedule_item)

        return schedule_items

    def _make_mssql_connection(self):
        server = MSSQL_CONN['server']
        database = MSSQL_CONN['database']
        username = MSSQL_CONN['username']  
        password = MSSQL_CONN['password']
        return MSSQLData(server, database, username, password)

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
        template.set_db_action(DBAction.NONE)
            
        hours = [int(h) for h in hours_str.split(',')]
        template.set_hours(hours)

        if dow_str is not None:
            dow = [int(d) for d in dow_str.split(',')]
            template.set_dow(dow)

        return template 

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

        schedule_item.set_schedule_date(QDate.fromString(schedule_date.strftime("%Y-%m-%d"), "yyyy-MM-dd"))

        return schedule_item

    def _make_blank_item(self):
        blank = BlankItem()
        blank.set_start_time("")
        return blank


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

    def save(self,  data: dict) -> bool:
        for template_name, template in data.items():

            template_id = -1

            if template.db_action() == DBAction.CREATE:
                template_id = self._create_template(template)
                if (template_id == -1):
                    print(f'Error creating template {template.name()}')
                    continue
                template.set_id(template_id)
                template.set_db_action(DBAction.NONE)
                print(f'Created template {template.name()} with id {template_id}')

            if template.db_action() == DBAction.UPDATE:
                template_id = self._update_template(template)
                template.set_db_action(DBAction.NONE)

            if template.db_action() == DBAction.DELETE:
                self._delete_template_items(template)
                self._delete_template(template)
                template.set_db_action(DBAction.NONE)
                continue

            if template.db_action() == DBAction.NONE:
                template_id = template.id()

            print(f'save template items...{len(template.items())}')
            self._save_template_items(template.items(), template_id)

        print(f"Saving templates...Done.")

    def _create_template(self, template) -> int:
        hours = ",".join([str(i) for i in template.hours()])
        dow = ",".join([str(i) for i in template.dow()])
        
        ins_stmt = (f"Insert into TemplateHeader (name, description, hours, dow) " 
                    f"OUTPUT INSERTED.id "
                    f" Values ('{template.name()}','{template.description()}','{hours}', '{dow}')"
                    )

        print(f'Creating template {template.name()}...')
        new_id =  self.execute_insert(ins_stmt)

        print(f'Created template {template.name()} with id {new_id}')
        return new_id

    def _update_template(self, template) -> int:
        hours = ",".join([str(i) for i in template.hours()])
        dow = ",".join([str(i) for i in template.dow()])

        upd_stmt = (f"Update TemplateHeader set name='{template.name()}', "
                    f" description='{template.description()}', hours='{hours}', dow='{dow}' "
                    f" Where id={template.id()};"
                    )

        print(f'Updating template `{template.name()}`...')
        self.execute_non_query(upd_stmt)
        return template.id()

    def _delete_template_items(self, template):
        print(f'Deleting items for template {template.name()} - {template.id()}...')

        del_stmt = f'Delete from TemplateItem Where template_id={template.id()};'
        self.execute_non_query(del_stmt)

    def _delete_template(self, template):
        print(f'Deleting template {template.name()} - {template.id()}...')

        del_stmt = f'Delete from TemplateHeader Where id={template.id()};'
        self.execute_non_query(del_stmt)

    def _save_template_items(self, template_items: dict, template_id: int):

        for identifier, item in template_items.items():
            if item.item_type() == ItemType.EMPTY:
                continue

            if item.db_action() == DBAction.CREATE:
                new_id = self._create_template_item(item, template_id)
                item.set_db_action(DBAction.NONE)
                item.set_id(new_id)
                item.set_template_id(template_id)

            if item.db_action() == DBAction.UPDATE:
                self._update_template_item(item)
                item.set_db_action(DBAction.NONE)

            if item.db_action() == DBAction.DELETE:
                self._delete_template_item(item)
                item.set_db_action(DBAction.NONE)

        print(f"Creating template items...Done")

    def _create_template_item(self, item, template_id: int) -> int:

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

            ins_stmt = (f"Insert into TemplateItem (item_type, start_time, hour, duration, title, artist_name, artist_id, "
                   f"folder_id, item_path, item_id, item_row, item_identifier, template_id, folder_name, rotation, genre) "
                   f" OUTPUT INSERTED.id "
                   f" VALUES "
                   f"({item_type},'{start_time}',{hour},{duration},'{title}','{artist_name}', {artist_id},{folder_id}, "
                   f"'{item_path}',{track_id}, {item_row},'{item_identifier}', {template_id}, '{folder_name}', "
                   f"'{rotation}', {genre});" )

            new_id = -1
            print(f'Creating template item {item.title()}...')
            new_id = self.execute_insert(ins_stmt)
            return new_id

    def _update_template_item(self, item):
        start_time = item.start_time().toString("hh:mm:ss")
        item_row = item.item_row()

        print(f"Start Time {start_time}: Item Title: {item.title()} - Rotation: {item.rotation()}")

        upd_stmt = (f'Update templateitem set "start_time"="{start_time}", '
                    f' "item_row"={item_row}, '
                    f' "rotation"="{item.rotation()}" '
                    f'Where id={item.id()};'
                )

        print(f'Updating template {item.title()}...')

        self.execute_non_query(upd_stmt)

    def _delete_template_item(self, item):

        del_stmt = f'Delete from templateitem Where id={item.id()};'
        print(f'Deleting template item {item.title()}...')

        self.execute_non_query(del_stmt)
