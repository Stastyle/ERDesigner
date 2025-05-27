# main_window_explorer_utils.py
# Contains utility functions for the diagram explorer.

from PyQt6.QtWidgets import QTreeWidgetItem, QHeaderView 
from PyQt6.QtCore import Qt

# Define item types for the explorer tree
ITEM_TYPE_TABLE = QTreeWidgetItem.ItemType.UserType + 1
ITEM_TYPE_COLUMN = QTreeWidgetItem.ItemType.UserType + 2
ITEM_TYPE_RELATIONSHIP = QTreeWidgetItem.ItemType.UserType + 3
ITEM_TYPE_CATEGORY = QTreeWidgetItem.ItemType.UserType + 4 

def populate_diagram_explorer_util(window):
    """Populates the diagram explorer tree with current tables, relationships, and groups."""
    if not hasattr(window, 'diagram_explorer_tree') or not window.diagram_explorer_tree:
        return 

    window.diagram_explorer_tree.clear()
    window.diagram_explorer_tree.setAlternatingRowColors(True) # Ensure this is set

    # --- Tables Category (for ungrouped tables or all tables view) ---
    tables_category_item = QTreeWidgetItem(window.diagram_explorer_tree, ["Tables", "Category"])
    tables_category_item.setData(0, Qt.ItemDataRole.UserRole, ITEM_TYPE_CATEGORY) 
    
    sorted_table_names = sorted(window.tables_data.keys())
    if not sorted_table_names:
        empty_tables_node = QTreeWidgetItem(tables_category_item, ["(No tables in diagram)", "Info"])
        empty_tables_node.setDisabled(True)
    else:
        for table_name in sorted_table_names:
            table_data = window.tables_data[table_name]
            display_name = table_data.name
            
            table_item_explorer = QTreeWidgetItem(tables_category_item, [display_name, "Table"])
            table_item_explorer.setData(0, Qt.ItemDataRole.UserRole, ITEM_TYPE_TABLE) 
            table_item_explorer.setData(1, Qt.ItemDataRole.UserRole, table_data.name) # Store actual table name

            if not table_data.columns:
                empty_cols_node = QTreeWidgetItem(table_item_explorer, ["(No columns)", "Info"])
                empty_cols_node.setDisabled(True)
            else:
                for col in table_data.columns:
                    col_display_name = col.get_display_name() 
                    col_item_explorer = QTreeWidgetItem(table_item_explorer, [col_display_name, col.data_type])
                    col_item_explorer.setData(0, Qt.ItemDataRole.UserRole, ITEM_TYPE_COLUMN) 
                    # Store full identifier: "TableName.ColumnName"
                    col_item_explorer.setData(1, Qt.ItemDataRole.UserRole, f"{table_data.name}.{col.name}")
    
    # --- Relationships Category ---
    rels_category_item = QTreeWidgetItem(window.diagram_explorer_tree, ["Relationships", "Category"])
    rels_category_item.setData(0, Qt.ItemDataRole.UserRole, ITEM_TYPE_CATEGORY)
    
    if not window.relationships_data:
        empty_rels_node = QTreeWidgetItem(rels_category_item, ["(No relationships)", "Info"])
        empty_rels_node.setDisabled(True)
    else:
        sorted_relationships = sorted(window.relationships_data, key=lambda r: (r.table1_name, r.fk_column_name, r.table2_name, r.pk_column_name))
        for i, rel_data in enumerate(sorted_relationships):
            rel_name = f"{rel_data.table1_name}.{rel_data.fk_column_name} -> {rel_data.table2_name}.{rel_data.pk_column_name}"
            rel_item_explorer = QTreeWidgetItem(rels_category_item, [rel_name, rel_data.relationship_type])
            rel_item_explorer.setData(0, Qt.ItemDataRole.UserRole, ITEM_TYPE_RELATIONSHIP) 
            try: # Store original index in relationships_data list for identification
                original_index = window.relationships_data.index(rel_data)
                rel_item_explorer.setData(1, Qt.ItemDataRole.UserRole, original_index)
            except ValueError: # Should not happen if data is consistent
                 rel_item_explorer.setData(1, Qt.ItemDataRole.UserRole, -1) # Error case

    window.diagram_explorer_tree.expandAll()
    
    for i in range(window.diagram_explorer_tree.columnCount()):
        window.diagram_explorer_tree.resizeColumnToContents(i)


def on_explorer_item_double_clicked_util(window, item: QTreeWidgetItem, column: int):
    """Handles double-click events on items in the diagram explorer."""
    item_type = item.data(0, Qt.ItemDataRole.UserRole) 
    identifier = item.data(1, Qt.ItemDataRole.UserRole) # This usually stores the name or index

    graphic_item_to_focus = None

    if item_type == ITEM_TYPE_TABLE:
        table_name = identifier # Identifier is the table name
        if table_name in window.tables_data and window.tables_data[table_name].graphic_item:
            graphic_item_to_focus = window.tables_data[table_name].graphic_item
    
    elif item_type == ITEM_TYPE_RELATIONSHIP:
        try:
            rel_index = int(identifier) # Identifier is the original index
            if 0 <= rel_index < len(window.relationships_data):
                relationship_data = window.relationships_data[rel_index]
                if relationship_data.graphic_item:
                    graphic_item_to_focus = relationship_data.graphic_item
        except (ValueError, TypeError):
            # print(f"Error identifying relationship from explorer: Invalid identifier '{identifier}'")
            pass 

    elif item_type == ITEM_TYPE_COLUMN:
        # Identifier is "TableName.ColumnName"
        if isinstance(identifier, str) and '.' in identifier:
            table_name, _ = identifier.split('.', 1)
            if table_name in window.tables_data and window.tables_data[table_name].graphic_item:
                graphic_item_to_focus = window.tables_data[table_name].graphic_item # Focus on the table
    
    if graphic_item_to_focus:
        window.scene.clearSelection() 
        graphic_item_to_focus.setSelected(True) 
        window.view.centerOn(graphic_item_to_focus) 


def toggle_diagram_explorer_util(window, checked):
    """Shows or hides the diagram explorer dock widget."""
    if hasattr(window, 'diagram_explorer_dock'):
        window.diagram_explorer_dock.setVisible(checked)
