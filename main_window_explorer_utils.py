# main_window_explorer_utils.py
# Contains utility functions for the diagram explorer.

from PyQt6.QtWidgets import QTreeWidgetItem
from PyQt6.QtCore import Qt

# Define item types for the explorer tree (can be shared with main_window if needed there too)
ITEM_TYPE_TABLE = QTreeWidgetItem.ItemType.UserType + 1
ITEM_TYPE_COLUMN = QTreeWidgetItem.ItemType.UserType + 2
ITEM_TYPE_RELATIONSHIP = QTreeWidgetItem.ItemType.UserType + 3
ITEM_TYPE_CATEGORY = QTreeWidgetItem.ItemType.UserType + 4 # For "Tables", "Relationships" categories

def populate_diagram_explorer_util(window):
    """Populates the diagram explorer tree with current tables and relationships."""
    if not hasattr(window, 'diagram_explorer_tree') or not window.diagram_explorer_tree:
        return # Explorer not yet created

    window.diagram_explorer_tree.clear()

    # Tables Category
    tables_category_item = QTreeWidgetItem(window.diagram_explorer_tree, ["Tables", "Category"])
    tables_category_item.setData(0, Qt.ItemDataRole.UserRole, ITEM_TYPE_CATEGORY) # Store type
    # Optionally set an icon for categories
    # tables_category_item.setIcon(0, QIcon("path/to/category_icon.png"))

    sorted_table_names = sorted(window.tables_data.keys())
    for table_name in sorted_table_names:
        table_data = window.tables_data[table_name]
        table_item_explorer = QTreeWidgetItem(tables_category_item, [table_data.name, "Table"])
        table_item_explorer.setData(0, Qt.ItemDataRole.UserRole, ITEM_TYPE_TABLE) # Store type
        table_item_explorer.setData(1, Qt.ItemDataRole.UserRole, table_data.name) # Store identifier (table name)
        # Optionally set an icon for tables
        # table_item_explorer.setIcon(0, QIcon("path/to/table_icon.png"))

        for col in table_data.columns:
            col_display_name = col.get_display_name() # Includes PK/FK indicators
            col_item_explorer = QTreeWidgetItem(table_item_explorer, [col_display_name, col.data_type])
            col_item_explorer.setData(0, Qt.ItemDataRole.UserRole, ITEM_TYPE_COLUMN) # Store type
            # Store unique identifier for column, e.g., "TableName.ColumnName"
            col_item_explorer.setData(1, Qt.ItemDataRole.UserRole, f"{table_data.name}.{col.name}")
            # Optionally set an icon for columns
            # col_item_explorer.setIcon(0, QIcon("path/to/column_icon.png"))
    
    # Relationships Category
    rels_category_item = QTreeWidgetItem(window.diagram_explorer_tree, ["Relationships", "Category"])
    rels_category_item.setData(0, Qt.ItemDataRole.UserRole, ITEM_TYPE_CATEGORY)
    # rels_category_item.setIcon(0, QIcon("path/to/category_icon.png"))

    # Sort relationships for consistent display
    # Sorting key can be complex, e.g., by from_table, then from_column
    sorted_relationships = sorted(window.relationships_data, key=lambda r: (r.table1_name, r.fk_column_name, r.table2_name, r.pk_column_name))

    for i, rel_data in enumerate(sorted_relationships):
        # Construct a display name for the relationship
        rel_name = f"{rel_data.table1_name}.{rel_data.fk_column_name} -> {rel_data.table2_name}.{rel_data.pk_column_name}"
        rel_item_explorer = QTreeWidgetItem(rels_category_item, [rel_name, rel_data.relationship_type])
        rel_item_explorer.setData(0, Qt.ItemDataRole.UserRole, ITEM_TYPE_RELATIONSHIP) # Store type
        # Store an identifier for the relationship. Using its index in the original (unsorted) list might be
        # problematic if the list order changes. A unique ID or the tuple of (fromT, fromC, toT, toC) is better.
        # For simplicity, if using index, ensure it's from the main `window.relationships_data`
        try:
            original_index = window.relationships_data.index(rel_data)
            rel_item_explorer.setData(1, Qt.ItemDataRole.UserRole, original_index)
        except ValueError:
             # Fallback if rel_data somehow isn't in the main list (should not happen)
             rel_item_explorer.setData(1, Qt.ItemDataRole.UserRole, -1) # Invalid index

        # Optionally set an icon for relationships
        # rel_item_explorer.setIcon(0, QIcon("path/to/relationship_icon.png"))

    window.diagram_explorer_tree.expandAll()


def on_explorer_item_double_clicked_util(window, item, column):
    """Handles double-click events on items in the diagram explorer."""
    item_type = item.data(0, Qt.ItemDataRole.UserRole) # Get stored type
    identifier = item.data(1, Qt.ItemDataRole.UserRole) # Get stored identifier

    graphic_item_to_focus = None

    if item_type == ITEM_TYPE_TABLE:
        table_name = identifier
        if table_name in window.tables_data and window.tables_data[table_name].graphic_item:
            graphic_item_to_focus = window.tables_data[table_name].graphic_item
    
    elif item_type == ITEM_TYPE_RELATIONSHIP:
        try:
            # Assuming identifier is the index in window.relationships_data
            rel_index = int(identifier)
            if 0 <= rel_index < len(window.relationships_data):
                relationship_data = window.relationships_data[rel_index]
                if relationship_data.graphic_item:
                    graphic_item_to_focus = relationship_data.graphic_item
        except (ValueError, TypeError):
            print(f"Error identifying relationship from explorer: Invalid identifier '{identifier}'")
            pass # Identifier was not a valid index

    elif item_type == ITEM_TYPE_COLUMN:
        # For columns, focus on the parent table
        if item.parent() and item.parent().data(0, Qt.ItemDataRole.UserRole) == ITEM_TYPE_TABLE:
            table_name = item.parent().data(1, Qt.ItemDataRole.UserRole) # Get table name from parent
            if table_name in window.tables_data and window.tables_data[table_name].graphic_item:
                graphic_item_to_focus = window.tables_data[table_name].graphic_item
    
    if graphic_item_to_focus:
        window.scene.clearSelection() # Clear any current selection
        graphic_item_to_focus.setSelected(True) # Select the item
        window.view.centerOn(graphic_item_to_focus) # Center view on the item
        # Optionally, you might want to zoom to fit the item too, or a gentle zoom.


def toggle_diagram_explorer_util(window, checked):
    """Shows or hides the diagram explorer dock widget."""
    if hasattr(window, 'diagram_explorer_dock'):
        window.diagram_explorer_dock.setVisible(checked)
        # The dock's visibilityChanged signal should trigger _update_floating_button_position
