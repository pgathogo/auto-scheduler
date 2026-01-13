from PyQt5.QtWidgets import (
    QComboBox, 
    QTreeView
)

from PyQt5.QtGui import (
    QStandardItemModel, 
    QStandardItem
)
from PyQt5.QtCore import (
    Qt
)

class TreeComboBox(QComboBox):
    """A QComboBox that displays items in a tree structure"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Make the combo box editable to allow setting custom text
        self.setEditable(True)
        self.lineEdit().setReadOnly(True)
        
        # Create a tree view for the dropdown
        self.tree_view = QTreeView(self)
        self.tree_view.setHeaderHidden(True)
        self.tree_view.setEditTriggers(QTreeView.NoEditTriggers)
        
        # Set the tree view as the combo box view
        self.setView(self.tree_view)
        
        # Create a standard item model
        self.model = QStandardItemModel()
        self.setModel(self.model)
        
        # Connect selection signal
        self.tree_view.clicked.connect(self.on_item_clicked)
        
    def on_item_clicked(self, index):
        """Handle item click - only allow selection of leaf items"""
        item = self.model.itemFromIndex(index)
        
        # If item has children, expand/collapse it instead of selecting
        if item.hasChildren():
            if self.tree_view.isExpanded(index):
                self.tree_view.collapse(index)
            else:
                self.tree_view.expand(index)
        else:
            # It's a leaf item, so allow selection
            self.hidePopup()
            self.setEditText(item.text())
    
    def add_tree_item(self, text, parent_item=None):
        """Add an item to the tree"""
        item = QStandardItem(text)
        
        if parent_item is None:
            self.model.appendRow(item)
        else:
            parent_item.appendRow(item)
        
        return item
    
    def populate_from_tree_widget(self, tree_widget):
        """Populate the combo box from a QTreeWidget"""
        self.model.clear()
        
        # Iterate through top-level items
        for i in range(tree_widget.topLevelItemCount()):
            tree_item = tree_widget.topLevelItem(i)
            self._add_tree_widget_item(tree_item, None)
    
    def data_with_index(self, index):
        """Get the data associated with the item at the given index"""
        item = self.model.itemFromIndex(index)
        if item:
            return item.data(Qt.UserRole)
        return None

    def get_data_at_index(self, index: int):
        """Get the data associated with the item at the given combo box index"""
        model_index = self.model.index(index, 0)
        item = self.model.itemFromIndex(model_index)
        print("Getting data at index:", index, "Item:", item)
        if item:
            return item.data(Qt.UserRole)
        return None

    def get_data_with_text(self, text) -> any:
        """Get the data associated with the item with the given text"""
        return self._find_data_by_text(self.model.invisibleRootItem(), text)

    def _find_data_by_text(self, parent_item, text) -> any:
        """
        Recursively search for an item with matching text.
        
        Args:
            parent_item: The parent QStandardItem to search under
            text: The text to match
            
        Returns:
            The data associated with the matching item, or None if not found
        """
        for row in range(parent_item.rowCount()):
            item = parent_item.child(row)
            if item is None:
                item = self.model.item(row)
            
            # Check if this item's text matches
            if item.text() == text:
                return item.data(Qt.UserRole)
            
            # Recursively search children
            if item.hasChildren():
                result = self._find_data_by_text(item, text)
                if result is not None:
                    return result
        
        return None

    def get_index_with_data(self, data):
        """Get the QModelIndex of the item with the given data"""
        return self._find_item_by_data(self.model.invisibleRootItem(), data)

    def set_default(self, data):
        """
        Set the default/current item by searching for matching data.
        
        Args:
            data: The value to search for in Qt.UserRole data
        """
        index = self._find_item_by_data(self.model.invisibleRootItem(), data)
        if index is not None:
            self.tree_view.setCurrentIndex(index)
            # Update the displayed text in the combo box
            item = self.model.itemFromIndex(index)
            if item:
                self.setEditText(item.text())
            return True
        return False
    
    def _find_item_by_data(self, parent_item, data):
        """
        Recursively search for an item with matching data.
        
        Args:
            parent_item: The parent QStandardItem to search under
            data: The value to match against Qt.UserRole
            
        Returns:
            QModelIndex of the matching item, or None if not found
        """
        for row in range(parent_item.rowCount()):
            item = parent_item.child(row)
            if item is None:
                item = self.model.item(row)
            
            # Check if this item's data matches
            item_data = item.data(Qt.UserRole)
            if item_data == data:
                return item.index()
            
            # Recursively search children
            if item.hasChildren():
                result = self._find_item_by_data(item, data)
                if result is not None:
                    return result
        
        return None
    
    def _add_tree_widget_item(self, tree_widget_item, parent_standard_item):
        """Recursively add items from QTreeWidget to the model"""
        text = tree_widget_item.text(0)
        standard_item = QStandardItem(text)
        
        # Transfer data from QTreeWidgetItem
        # Copy user data (Qt.UserRole and custom roles)
        data = tree_widget_item.data(0, Qt.UserRole)
        if data is not None:
            standard_item.setData(data, Qt.UserRole)
        
        # Copy additional columns if they exist
        column_count = tree_widget_item.columnCount()
        for col in range(1, column_count):
            col_text = tree_widget_item.text(col)
            if col_text:
                standard_item.setData(col_text, Qt.UserRole + col)
        
        # Copy icon if it exists
        icon = tree_widget_item.icon(0)
        if not icon.isNull():
            standard_item.setIcon(icon)
        
        # Copy tooltip
        tooltip = tree_widget_item.toolTip(0)
        if tooltip:
            standard_item.setToolTip(tooltip)
        
        # Copy foreground color
        foreground = tree_widget_item.foreground(0)
        standard_item.setForeground(foreground)
        
        # Copy background color
        background = tree_widget_item.background(0)
        standard_item.setBackground(background)

        # Copy font
        font = tree_widget_item.font(0)
        standard_item.setFont(font)
        
        if parent_standard_item is None:
            self.model.appendRow(standard_item)
        else:
            parent_standard_item.appendRow(standard_item)
        
        # Recursively add children
        for i in range(tree_widget_item.childCount()):
            child = tree_widget_item.child(i)
            self._add_tree_widget_item(child, standard_item)
