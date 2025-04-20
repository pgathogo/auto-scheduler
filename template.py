from collections import OrderedDict

from data_types import DBAction

class Template:
    def __init__(self, name:str):
        self._id = -1
        self._name = name
        self._description = ""
        self._hours = []
        self._dow = []
        self._template_items = OrderedDict()
        self._db_action = DBAction.NONE

    def id(self):
        return self._id
    
    def set_id(self, i):
        self._id = i

    def set_description(self, description:str):
        self._description = description

    def description(self) -> str:
        return self._description

    def name(self) -> str:
        return self._name

    def set_name(self, name: str):
        self._name = name

    def set_hours(self, hours:list):
        self._hours = hours

    def hours(self) -> list:
        return self._hours

    def dow(self) -> list:
        return self._dow

    def set_dow(self, dow:list):
        self._dow = dow

    def add_item(self,  item:"TemplateItem"):
        self._template_items[item.item_identifier()] = item

    def insert_header(self, header_and_blank: list):
        header = header_and_blank[0]
        blank = header_and_blank[1]
        temp_dict = OrderedDict()
        inserted = False
        for key, item in self._template_items.items():
            if isinstance(item.start_time(), str):
                temp_dict[key] = item
                continue    
            if header.start_time() < item.start_time():
                temp_dict[header.item_identifier()] = header
                temp_dict[blank.item_identifier()] = blank
                temp_dict[key] = item
                inserted = True
            else:
                temp_dict[key] = item

        if not inserted:
            temp_dict[header.item_identifier()] = header
            temp_dict[blank.item_identifier()] = blank

        self._template_items = temp_dict

    def assign_items(self, items: OrderedDict):
        self._template_items = items

    def template_items(self) -> OrderedDict:
        return self._template_items

    def item(self, item_id:str) -> "TemplateItem":
        return self._template_items[item_id]

    def items(self):
        return self._template_items

    def db_action(self) ->DBAction:
        return self._db_action
    
    def set_db_action(self, action: DBAction):
        self._db_action = action

    def get_items_for_hour(self, hour)->list:
        items = [item for item in self._template_items.values() if item.hour() == hour]
        return items

    def mark_items_for_deletion(self, hour):
        for item in self._template_items.values():
            if item.hour() == hour:
                item.set_db_action(DBAction.DELETE)
