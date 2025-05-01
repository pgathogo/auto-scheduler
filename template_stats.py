
from template import Template

from PyQt5.QtCore import (
    QTime
)

from PyQt5.QtWidgets import (
    QTableWidget,
    QTableWidgetItem
)

class TemplateStatistics:
    def __init__(self, stats_widget: QTableWidget):
        self._stats_widget = stats_widget
        self.stats = {}

    def compute_stats(self, template: Template):
        self.setup_stats_widget()
        self._stats_widget.setRowCount(len(template.hours()))
        self._stats_widget.setColumnCount(3)

        for i, hour in enumerate(template.hours()):
            item_count = len(template.template_items_by_hour(hour))
            total_duration = sum(item.duration() for item in template.template_items_by_hour(hour))

            hour_item = QTableWidgetItem(str(hour))
            count_item = QTableWidgetItem(str(item_count))

            time = QTime(hour, 0, 0)
            time_duration = time.addMSecs(total_duration).toString("hh:mm:ss")
            time_item = QTableWidgetItem(time_duration)

            self._stats_widget.setItem(i, 0, hour_item)
            self._stats_widget.setItem(i, 1, count_item)
            self._stats_widget.setItem(i, 2, time_item)

            self.stats[hour] = {
                "item_count": item_count,
                "total_duration": total_duration,
                "hour_item": hour_item,
                "count_item": count_item,
                "time_item": time_item
            }


    def setup_stats_widget(self):
        self._stats_widget.clear()
        self._stats_widget.setRowCount(0)
        self._stats_widget.setColumnCount(3)
        self._stats_widget.setHorizontalHeaderLabels(["Hour", "Item Count", "Time"])
        self._stats_widget.setColumnWidth(0, 80)
        self._stats_widget.setColumnWidth(1, 100)
        self._stats_widget.setColumnWidth(2, 100)


    def update_stats(self, hour: int, template: Template):
        item_count = len(template.template_items_by_hour(hour))
        total_duration = sum(item.duration() for item in template.template_items_by_hour(hour))
        time = QTime(hour, 0, 0)
        time_duration = time.addMSecs(total_duration).toString("hh:mm:ss")
        self.stats[hour]["item_count"] = item_count
        self.stats[hour]["total_duration"] = total_duration
        self.stats[hour]["count_item"].setText(str(item_count))
        self.stats[hour]["time_item"].setText(time_duration)

