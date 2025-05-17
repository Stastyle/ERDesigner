# main_window_table_operations.py
# Handles operations related to tables like adding and editing.

from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtCore import QPointF
from data_models import Table # Assuming data_models.py is accessible
from dialogs import TableDialog # Assuming dialogs.py is accessible
from commands import AddTableCommand, EditTableCommand # Assuming commands.py is accessible
import constants
from utils import snap_to_grid

def handle_add_table_button_impl(window, table_name_prop=None, columns_prop=None, pos=None, width_prop=None, body_color_hex=None, header_color_hex=None, from_undo_redo=False):
    """
    Handles the logic for adding a new table, either via dialog or programmatically (e.g., CSV import, undo/redo).
    Returns the created/retrieved Table object or None.
    """
    table_data_result = None

    if not from_undo_redo:
        dialog_table_name = ""
        dialog_columns = []
        dialog_body_color_hex = None
        dialog_header_color_hex = None

        if table_name_prop: # Programmatic addition (e.g., CSV import)
            dialog_table_name = table_name_prop
            dialog_columns = columns_prop if columns_prop else []
            dialog_body_color_hex = body_color_hex
            dialog_header_color_hex = header_color_hex
            print(f"Programmatic add_table for '{dialog_table_name}' with pos: {pos}")
            if not dialog_table_name:
                print("Error: Programmatic table add attempt with no name.")
                return None
            # The AddTableCommand will handle if the table already exists (for replacement or error)
        else: # Interactive addition via dialog
            # Use theme defaults or user-set defaults for initial dialog colors
            initial_body_color = window.user_default_table_body_color or window.current_theme_settings["default_table_body_color"]
            initial_header_color = window.user_default_table_header_color or window.current_theme_settings["default_table_header_color"]
            
            dialog = TableDialog(window, "", None, initial_body_color, initial_header_color) # Parent is main window
            if not dialog.exec():
                return None # Dialog cancelled
            dialog_table_name, dialog_columns, dialog_body_color_hex, dialog_header_color_hex = dialog.get_table_data()

            if not dialog_table_name:
                QMessageBox.warning(window, "Warning", "Table name cannot be empty.")
                return None
            if dialog_table_name in window.tables_data:
                QMessageBox.warning(window, "Warning", f"Table with name '{dialog_table_name}' already exists.")
                return None

        # Determine position for the new table
        default_x, default_y = 0, 0
        if pos: # Provided position (e.g., from CSV or specific placement)
            default_x = snap_to_grid(pos.x(), constants.GRID_SIZE)
            default_y = snap_to_grid(pos.y(), constants.GRID_SIZE)
            print(f"  Using provided pos for '{dialog_table_name}': ({default_x}, {default_y})")
        else: # Default position (center of view)
            visible_rect_center = window.view.mapToScene(window.view.viewport().rect().center())
            table_width_for_centering = width_prop if width_prop is not None else constants.DEFAULT_TABLE_WIDTH
            default_x = snap_to_grid(visible_rect_center.x() - table_width_for_centering / 2, constants.GRID_SIZE)
            default_y = snap_to_grid(visible_rect_center.y() - constants.TABLE_HEADER_HEIGHT / 2, constants.GRID_SIZE) # Approx center Y
            print(f"  Using default/view center pos for '{dialog_table_name}': ({default_x}, {default_y})")

        table_width_to_use = width_prop if width_prop is not None else constants.DEFAULT_TABLE_WIDTH
        
        # Create Table data object
        table_data = Table(name=dialog_table_name,
                           x=default_x, y=default_y,
                           width=table_width_to_use,
                           body_color_hex=dialog_body_color_hex,
                           header_color_hex=dialog_header_color_hex)
        for col_data in dialog_columns: # col_data should be Column objects or dicts that Column can take
            table_data.add_column(col_data)
        
        print(f"  Table data object for '{table_data.name}' created with x={table_data.x}, y={table_data.y}, w={table_data.width}")
        
        # Use AddTableCommand for undo/redo
        command = AddTableCommand(window, table_data) # Pass the main window instance
        window.undo_stack.push(command)
        
        # After command execution, the table should be in window.tables_data
        table_data_result = window.tables_data.get(dialog_table_name)
        if table_data_result:
             print(f"  Table '{table_data_result.name}' added/updated via command. Final pos in tables_data: ({table_data_result.x}, {table_data_result.y})")
             if table_data_result.graphic_item:
                 print(f"    Graphic item scenePos: {table_data_result.graphic_item.scenePos()}")
        else:
            print(f"  Error: Table '{dialog_table_name}' not found in tables_data after AddTableCommand.")
            # This case should ideally not happen if AddTableCommand works correctly.

    else: # from_undo_redo is True, means the command itself is calling this (or a similar internal method)
          # The command's redo/undo logic should handle re-populating window.tables_data and scene directly.
          # This path might not be strictly necessary if commands are self-contained.
          # However, if AddTableCommand's redo calls a method like this, it would retrieve the existing object.
        table_data_result = window.tables_data.get(table_name_prop)
        if table_data_result:
            print(f"Undo/Redo: Retrieved table '{table_name_prop}'")
        else:
            print(f"Undo/Redo Error: Could not retrieve table '{table_name_prop}'")


    return table_data_result


# edit_table_impl could be added here if needed, using EditTableCommand
# def handle_edit_table_impl(window, table_to_edit_data):
#     pass
