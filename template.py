from collections import OrderedDict

from data_types import DBAction

class Template:
    def __init__(self, name:str):
        self._id = -1
        self._name = name
        self._description = ""
        self._hours = []
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

    def add_item(self,  item:"TemplateItem"):
        self._template_items[item.item_identifier()] = item

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