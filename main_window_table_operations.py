# main_window_table_operations.py
# Handles operations related to tables like adding and editing.

from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QColor
from data_models import Table # Assuming data_models.py is accessible
from dialogs import TableDialog # Assuming dialogs.py is accessible
from commands import AddTableCommand, EditTableCommand # Assuming commands.py is accessible
import constants
from utils import snap_to_grid

def handle_add_table_button_impl(window, table_props=None, from_undo_redo=False, interactive_pos=None):
    """
    Handles the logic for adding a new table, either via dialog or programmatically (e.g., CSV import, undo/redo).
    'table_props' is a dictionary for programmatic addition, expected to contain keys like
    'name', 'columns', 'pos', 'width', 'body_color_hex', 'header_color_hex'.
    'interactive_pos' is an optional QPointF to suggest initial position for interactive dialog-based addition.
    Returns the created/retrieved Table object or None.
    """
    table_data_result = None
    
    # Variables to hold the final properties for the Table object
    name_for_table_creation = ""
    columns_for_table_creation = []
    body_hex_for_table_creation = None
    header_hex_for_table_creation = None
    pos_for_table_creation = None # QPointF
    width_for_table_creation = constants.DEFAULT_TABLE_WIDTH

    if not from_undo_redo:
        if table_props: # Programmatic addition (e.g., CSV import or direct call with properties)
            name_for_table_creation = table_props.get("name", "")
            columns_for_table_creation = table_props.get("columns", [])
            pos_for_table_creation = table_props.get("pos")
            width_from_props = table_props.get("width")
            width_for_table_creation = width_from_props if width_from_props is not None else constants.DEFAULT_TABLE_WIDTH

            # Determine Body Color
            # Priority: 1. Props, 2. User Default, 3. App Default (via Table constructor if None)
            prop_body_color_hex = table_props.get("body_color_hex")
            if prop_body_color_hex and QColor.isValidColor(prop_body_color_hex):
                body_hex_for_table_creation = prop_body_color_hex
            elif window.user_default_table_body_color and window.user_default_table_body_color.isValid():
                body_hex_for_table_creation = window.user_default_table_body_color.name()
            # else body_hex_for_table_creation remains None, Table constructor handles app default

            # Determine Header Color
            # Priority: 1. Props, 2. User Default, 3. App Default (via Table constructor if None)
            prop_header_color_hex = table_props.get("header_color_hex")
            if prop_header_color_hex and QColor.isValidColor(prop_header_color_hex):
                header_hex_for_table_creation = prop_header_color_hex
            elif window.user_default_table_header_color and window.user_default_table_header_color.isValid():
                header_hex_for_table_creation = window.user_default_table_header_color.name()
            # else header_hex_for_table_creation remains None, Table constructor handles app default

            # print(f"Programmatic add_table for '{name_for_table_creation}' with pos: {pos_for_table_creation}")
            if not name_for_table_creation:
                print("Error: Programmatic table add attempt with no name.")
                return None

        else: # Interactive call (no table_props)
            pos_for_table_creation = interactive_pos # From double-click or button press context
            width_for_table_creation = constants.DEFAULT_TABLE_WIDTH # New interactive tables get default width
            
            # Determine initial QColor for TableDialog (User Default -> None)
            initial_dialog_body_qcolor = None
            if window.user_default_table_body_color and window.user_default_table_body_color.isValid():
                initial_dialog_body_qcolor = window.user_default_table_body_color
            
            initial_dialog_header_qcolor = None
            if window.user_default_table_header_color and window.user_default_table_header_color.isValid():
                initial_dialog_header_qcolor = window.user_default_table_header_color
            
            # TableDialog constructor expects QColor objects or None.
            # If None, TableDialog itself falls back to constants.current_theme_settings.
            dialog = TableDialog(window, "", None, initial_dialog_body_qcolor, initial_dialog_header_qcolor)
            if not dialog.exec():
                return None # Dialog cancelled
            
            # Get data from dialog. These are the final values for interactive creation.
            name_for_table_creation, columns_for_table_creation, body_hex_for_table_creation, header_hex_for_table_creation, newly_picked_custom_colors = dialog.get_table_data()

            # Handle newly picked custom colors (if any)
            if newly_picked_custom_colors:
                made_changes_to_global_custom_list = False
                current_saved_hex = {c.name() for c in constants.user_saved_custom_colors}
                basic_hex = {QColor(bc_hex).name() for bc_hex in constants.BASIC_COLORS_HEX}
                for color_hex in newly_picked_custom_colors:
                    if color_hex not in current_saved_hex and color_hex not in basic_hex:
                        constants.user_saved_custom_colors.append(QColor(color_hex))
                        made_changes_to_global_custom_list = True
                if made_changes_to_global_custom_list:
                    constants.user_saved_custom_colors = constants.user_saved_custom_colors[-constants.MAX_SAVED_CUSTOM_COLORS:]
                    window.save_app_settings()

            if not name_for_table_creation:
                QMessageBox.warning(window, "Warning", "Table name cannot be empty.")
                return None
            if name_for_table_creation in window.tables_data:
                QMessageBox.warning(window, "Warning", f"Table with name '{name_for_table_creation}' already exists.")
                return None

        # Determine position for the new table
        default_x, default_y = 0, 0
        if pos_for_table_creation: # Provided position
            default_x = snap_to_grid(pos_for_table_creation.x(), constants.GRID_SIZE)
            default_y = snap_to_grid(pos_for_table_creation.y(), constants.GRID_SIZE)
            # print(f"  Using provided pos for '{name_for_table_creation}': ({default_x}, {default_y})")
        else: # Default position (center of view)
            visible_rect_center = window.view.mapToScene(window.view.viewport().rect().center())
            table_width_for_centering = width_for_table_creation
            default_x = snap_to_grid(visible_rect_center.x() - table_width_for_centering / 2, constants.GRID_SIZE)
            default_y = snap_to_grid(visible_rect_center.y() - constants.TABLE_HEADER_HEIGHT / 2, constants.GRID_SIZE) # Approx center Y
            # print(f"  Using default/view center pos for '{name_for_table_creation}': ({default_x}, {default_y})")
        
        # Create Table data object
        table_data = Table(name=name_for_table_creation,
                           x=default_x, y=default_y,
                           width=width_for_table_creation,
                           body_color_hex=body_hex_for_table_creation,
                           header_color_hex=header_hex_for_table_creation)
        for col_data in columns_for_table_creation:
            table_data.add_column(col_data)
        
        # print(f"  Table data object for '{table_data.name}' created with x={table_data.x}, y={table_data.y}, w={table_data.width}")
        
        # Use AddTableCommand for undo/redo
        command = AddTableCommand(window, table_data) # Pass the main window instance
        window.undo_stack.push(command)
        
        # After command execution, the table should be in window.tables_data
        table_data_result = window.tables_data.get(name_for_table_creation)
        if table_data_result:
             # print(f"  Table '{table_data_result.name}' added/updated via command. Final pos in tables_data: ({table_data_result.x}, {table_data_result.y})")
             if table_data_result.graphic_item:
                 window.update_sql_preview_pane() # Update SQL after table add
                 # print(f"    Graphic item scenePos: {table_data_result.graphic_item.scenePos()}")
        else:
            print(f"  Error: Table '{name_for_table_creation}' not found in tables_data after AddTableCommand.")
            # This case should ideally not happen if AddTableCommand works correctly.

    else: # from_undo_redo is True, means the command itself is calling this (or a similar internal method)
          # The command's redo/undo logic should handle re-populating window.tables_data and scene directly.
          # This path might not be strictly necessary if commands are self-contained.
          # If table_props is passed during undo/redo, it should contain the name.
        table_name_for_retrieval = table_props.get("name") if table_props else None
        if not table_name_for_retrieval:
            print(f"Undo/Redo Error: No table name provided to retrieve.")
            return None
        table_data_result = window.tables_data.get(table_name_for_retrieval)
        if table_data_result:
            print(f"Undo/Redo: Retrieved table '{table_name_for_retrieval}'")
        else:
            print(f"Undo/Redo Error: Could not retrieve table '{table_name_for_retrieval}'")

    return table_data_result


# edit_table_impl could be added here if needed, using EditTableCommand
# def handle_edit_table_impl(window, table_to_edit_data):
#     pass
