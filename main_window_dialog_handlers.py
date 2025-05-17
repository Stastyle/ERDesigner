# main_window_dialog_handlers.py
# Manages the opening and handling of various dialogs.

from PyQt6.QtWidgets import QMessageBox
from dialogs import ( # Assuming dialogs.py is accessible and contains these
    DefaultColorsDialog, CanvasSettingsDialog, DataTypeSettingsDialog
)
import constants # Assuming constants.py is accessible

def open_default_colors_dialog_handler(window):
    """Opens the dialog for setting default table colors."""
    # Pass current user defaults and the main window instance (for theme access and parent)
    dialog = DefaultColorsDialog(window, window) # Parent, main_app_window
    if dialog.exec(): # Dialog was accepted
        # The dialog should have updated window.user_default_table_body_color and window.user_default_table_header_color
        # And then it should call window.update_theme_settings() and window.set_theme(window.current_theme, force_update_tables=True)
        # For simplicity, we assume the dialog handles applying changes or the main window does it based on dialog signals.
        # If dialog only sets the values on `window`, then:
        window.update_theme_settings() # Re-calculate current_theme_settings with new user defaults
        window.set_theme(window.current_theme, force_update_tables=True) # Re-apply theme to all elements
        window.save_app_settings() # Persist the new default colors


def open_canvas_settings_dialog_handler(window):
    """Opens the dialog for setting canvas dimensions."""
    current_w = constants.current_canvas_dimensions["width"]
    current_h = constants.current_canvas_dimensions["height"]
    dialog = CanvasSettingsDialog(current_w, current_h, window) # Parent

    if dialog.exec(): # Dialog was accepted
        new_w, new_h = dialog.get_dimensions()
        if new_w != current_w or new_h != current_h:
            constants.current_canvas_dimensions["width"] = new_w
            constants.current_canvas_dimensions["height"] = new_h
            if window.scene: # Check if scene exists
                window.scene.setSceneRect(0, 0, new_w, new_h)
            window.save_app_settings() # Persist new dimensions
            QMessageBox.information(window, "Canvas Settings", "Canvas dimensions updated. You may need to adjust zoom/scroll to see changes.")
            # Optionally, auto-adjust view here, e.g., window.view.fitInView(window.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)


def open_datatype_settings_dialog_handler(window):
    """Opens the dialog for managing editable column data types."""
    # Pass a copy of the current list of data types to the dialog
    current_types = list(constants.editable_column_data_types)
    dialog = DataTypeSettingsDialog(current_types, window) # Parent

    if dialog.exec(): # Dialog was accepted
        new_types = dialog.get_data_types()
        # Check if the list of types actually changed
        if set(new_types) != set(constants.editable_column_data_types) or len(new_types) != len(constants.editable_column_data_types):
            constants.editable_column_data_types = new_types
            window.save_app_settings() # Persist new data types
            print(f"Updated column data types: {constants.editable_column_data_types}")
            QMessageBox.information(window, "Data Types Updated", "The list of available column data types has been updated.")
        else:
            print("Column data types remain unchanged.")
