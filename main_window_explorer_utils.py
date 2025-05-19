# main_window_explorer_utils.py
# Contains utility functions for the diagram explorer.

from PyQt6.QtWidgets import QTreeWidgetItem, QHeaderView 
from PyQt6.QtCore import Qt

# Define item types for the explorer tree
ITEM_TYPE_TABLE = QTreeWidgetItem.ItemType.UserType + 1
ITEM_TYPE_COLUMN = QTreeWidgetItem.ItemType.UserType + 2
ITEM_TYPE_RELATIONSHIP = QTreeWidgetItem.ItemType.UserType + 3
ITEM_TYPE_CATEGORY = QTreeWidgetItem.ItemType.UserType + 4 
ITEM_TYPE_GROUP = QTreeWidgetItem.ItemType.UserType + 5 # NEW: For Group items
ITEM_TYPE_GROUP_TABLE = QTreeWidgetItem.ItemType.UserType + 6 # NEW: For tables listed under a group

def populate_diagram_explorer_util(window):
    """Populates the diagram explorer tree with current tables, relationships, and groups."""
    if not hasattr(window, 'diagram_explorer_tree') or not window.diagram_explorer_tree:
        return 

    window.diagram_explorer_tree.clear()
    window.diagram_explorer_tree.setAlternatingRowColors(True) # Ensure this is set

    # --- Groups Category ---
    if hasattr(window, 'groups_data') and window.groups_data:
        groups_category_item = QTreeWidgetItem(window.diagram_explorer_tree, ["Groups", "Category"])
        groups_category_item.setData(0, Qt.ItemDataRole.UserRole, ITEM_TYPE_CATEGORY)
        
        sorted_group_names = sorted(window.groups_data.keys())
        for group_name in sorted_group_names:
            group_data = window.groups_data[group_name]
            group_item_explorer = QTreeWidgetItem(groups_category_item, [group_data.name, "Group"])
            group_item_explorer.setData(0, Qt.ItemDataRole.UserRole, ITEM_TYPE_GROUP)
            group_item_explorer.setData(1, Qt.ItemDataRole.UserRole, group_data.name) # Store group name for identification

            # Add tables belonging to this group as children
            tables_in_group_names = sorted(group_data.table_names)
            if not tables_in_group_names: # If group is empty
                 empty_node = QTreeWidgetItem(group_item_explorer, ["(No tables in group)", "Info"])
                 empty_node.setDisabled(True) # Make it non-interactive
            else:
                for table_name_in_group in tables_in_group_names:
                    table_data_ref = window.tables_data.get(table_name_in_group)
                    if table_data_ref:
                        # Display table name; could add more info like "(grouped)" if needed
                        table_child_item = QTreeWidgetItem(group_item_explorer, [table_data_ref.name, "Table (in group)"])
                        table_child_item.setData(0, Qt.ItemDataRole.UserRole, ITEM_TYPE_GROUP_TABLE) # Special type for grouped table
                        table_child_item.setData(1, Qt.ItemDataRole.UserRole, table_data_ref.name) # Store table name
                    # else: table might have been deleted but not yet removed from group_data.table_names

    # --- Tables Category (for ungrouped tables or all tables view) ---
    tables_category_item = QTreeWidgetItem(window.diagram_explorer_tree, ["All Tables", "Category"])
    tables_category_item.setData(0, Qt.ItemDataRole.UserRole, ITEM_TYPE_CATEGORY) 
    
    sorted_table_names = sorted(window.tables_data.keys())
    if not sorted_table_names:
        empty_tables_node = QTreeWidgetItem(tables_category_item, ["(No tables in diagram)", "Info"])
        empty_tables_node.setDisabled(True)
    else:
        for table_name in sorted_table_names:
            table_data = window.tables_data[table_name]
            # Display table name and its group if it belongs to one
            display_name = table_data.name
            if table_data.group_name:
                display_name += f" (in Group: {table_data.group_name})"
            
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

    if item_type == ITEM_TYPE_TABLE or item_type == ITEM_TYPE_GROUP_TABLE: # Handle both top-level and grouped tables
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
    
    elif item_type == ITEM_TYPE_GROUP: # NEW: Handle double-click on a group
        group_name = identifier # Identifier is the group name
        if hasattr(window, 'groups_data') and group_name in window.groups_data:
            group_data = window.groups_data[group_name]
            if group_data.graphic_item:
                graphic_item_to_focus = group_data.graphic_item

    if graphic_item_to_focus:
        window.scene.clearSelection() 
        graphic_item_to_focus.setSelected(True) 
        window.view.centerOn(graphic_item_to_focus) 


def toggle_diagram_explorer_util(window, checked):
    """Shows or hides the diagram explorer dock widget."""
    if hasattr(window, 'diagram_explorer_dock'):
        window.diagram_explorer_dock.setVisible(checked)
