# main_window.py
# Contains the ERDCanvasWindow class, the main application window.

import sys
import os
import configparser 
import copy 

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QGraphicsView, QMessageBox, QFileDialog,
    QWidget, QHBoxLayout, QDockWidget, QTreeWidget, QTreeWidgetItem,
    QPushButton, QStyle, QMenu
)
from PyQt6.QtCore import Qt, QPointF, QSize, QPoint, QEvent, QTimer # Added QTimer
from PyQt6.QtGui import (
    QColor, QBrush, QAction, QIcon, QKeySequence, QPixmap, QPainter, # QIcon is already here
    QActionGroup, QUndoStack, QPen
)

# Import from other modules
import constants
from utils import get_standard_icon, snap_to_grid
from data_models import Table, Column, Relationship 
from gui_items import TableGraphicItem, OrthogonalRelationshipLine 
from canvas_scene import ERDGraphicsScene
from commands import (
    AddTableCommand, DeleteRelationshipCommand, CreateRelationshipCommand,
    DeleteTableCommand, EditTableCommand
)

# Import refactored modules
from main_window_config import (
    load_app_settings, save_app_settings # CONFIG_FILE is used internally by these
)
from main_window_ui_setup import (
    create_menus, create_diagram_explorer_widget,
    create_main_floating_action_button_widget,
    show_floating_button_menu_widget,
    update_floating_button_position_widget 
)
from main_window_theming import (
    update_theme_settings_util, set_theme_util, apply_styles_util
)
from main_window_actions import (
    new_diagram_action, save_file_action, save_file_as_action,
    delete_selected_items_action, toggle_relationship_mode_action_impl,
    reset_drawing_mode_impl
)
from main_window_table_operations import (
    handle_add_table_button_impl
)
from main_window_relationship_operations import (
    finalize_relationship_drawing_impl, create_relationship_impl,
    update_orthogonal_path_impl, update_all_relationships_graphics_impl,
    update_relationship_table_names_impl,
    update_fk_references_to_pk_impl,
    remove_relationships_for_table_impl,
    edit_relationship_properties_impl
)
from main_window_event_handlers import (
    keyPressEvent_handler, view_wheel_event_handler 
)
from main_window_file_operations import (
    handle_import_csv_button_impl, export_to_csv_impl
)
from main_window_explorer_utils import (
    populate_diagram_explorer_util, on_explorer_item_double_clicked_util,
    toggle_diagram_explorer_util, ITEM_TYPE_TABLE, ITEM_TYPE_COLUMN,
    ITEM_TYPE_RELATIONSHIP, ITEM_TYPE_CATEGORY
)
from main_window_dialog_handlers import (
    open_default_colors_dialog_handler, open_canvas_settings_dialog_handler,
    open_datatype_settings_dialog_handler
)

class CentralWidgetWithResize(QWidget):
    def __init__(self, main_window_ref, parent=None):
        super().__init__(parent)
        self.main_window_ref = main_window_ref 

    def resizeEvent(self, event):
        super().resizeEvent(event) 
        if hasattr(self.main_window_ref, '_update_floating_button_position'):
            self.main_window_ref._update_floating_button_position()


class ERDCanvasWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Set application icon
        # Assuming icon.ico is in the root project directory alongside main.py or main_window.py
        app_icon_path = "icon.ico" 
        app_icon = QIcon(app_icon_path)
        if not app_icon.isNull():
            self.setWindowIcon(app_icon)
        else:
            print(f"Warning: Could not load application icon '{app_icon_path}'. File might be missing or invalid.")

        self.current_file_path = None
        self.current_theme = "light"
        self.user_default_table_body_color = None
        self.user_default_table_header_color = None

        constants.current_canvas_dimensions["width"] = constants.DEFAULT_CANVAS_WIDTH
        constants.current_canvas_dimensions["height"] = constants.DEFAULT_CANVAS_HEIGHT
        constants.editable_column_data_types = constants.DEFAULT_COLUMN_DATA_TYPES[:]

        self.undo_stack = QUndoStack(self)
        self.undo_stack.setUndoLimit(50)

        load_app_settings(self)

        self.current_theme_settings = {}
        update_theme_settings_util(self) 
        self.update_window_title()

        self.setGeometry(100, 100, 1300, 850)

        self.tables_data = {}  
        self.relationships_data = []  
        self.drawing_relationship_mode = False

        self.scene = ERDGraphicsScene(self)
        self.scene.setSceneRect(0, 0,
                                 constants.current_canvas_dimensions["width"],
                                 constants.current_canvas_dimensions["height"])

        self.view = QGraphicsView(self.scene, self)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.view.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.view.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.view.setInteractive(True)
        self.view.wheelEvent = lambda event: view_wheel_event_handler(self, event)

        main_widget = CentralWidgetWithResize(self) 
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.view, 1)
        self.setCentralWidget(main_widget)

        create_menus(self)
        create_diagram_explorer_widget(self) 
        create_main_floating_action_button_widget(self) 

        apply_styles_util(self)
        self.set_theme(self.current_theme) 

        self.undo_stack.indexChanged.connect(self.populate_diagram_explorer)
        self.undo_stack.cleanChanged.connect(self.update_window_title)

    def load_app_settings(self):
        load_app_settings(self)

    def save_app_settings(self):
        save_app_settings(self)

    def update_theme_settings(self):
        update_theme_settings_util(self)

    def set_theme(self, theme_name, force_update_tables=False):
        set_theme_util(self, theme_name, force_update_tables)
        self._update_floating_button_position() 

    def apply_styles(self):
        apply_styles_util(self)

    def create_menus(self):
        create_menus(self)

    def create_diagram_explorer(self):
        create_diagram_explorer_widget(self)

    def toggle_diagram_explorer(self, checked):
        toggle_diagram_explorer_util(self, checked)

    def populate_diagram_explorer(self):
        populate_diagram_explorer_util(self)

    def on_explorer_item_double_clicked(self, item, column):
        on_explorer_item_double_clicked_util(self, item, column)

    def create_main_floating_action_button(self):
        create_main_floating_action_button_widget(self)

    def _update_floating_button_position(self):
        update_floating_button_position_widget(self)

    def show_floating_button_menu(self):
        show_floating_button_menu_widget(self)

    def new_diagram(self):
        new_diagram_action(self)

    def save_file(self):
        save_file_action(self)

    def save_file_as(self):
        save_file_as_action(self)

    def delete_selected_items(self):
        delete_selected_items_action(self)

    def toggle_relationship_mode_action(self, checked):
        toggle_relationship_mode_action_impl(self, checked)

    def reset_drawing_mode(self):
        reset_drawing_mode_impl(self)

    def handle_add_table_button(self, table_name_prop=None, columns_prop=None, pos=None, width_prop=None, body_color_hex=None, header_color_hex=None, from_undo_redo=False):
        return handle_add_table_button_impl(self, table_name_prop, columns_prop, pos, width_prop, body_color_hex, header_color_hex, from_undo_redo)

    def finalize_relationship_drawing(self, source_table_data, source_column_data, dest_table_data, dest_column_data):
        finalize_relationship_drawing_impl(self, source_table_data, source_column_data, dest_table_data, dest_column_data)

    def create_relationship(self, fk_table_data, pk_table_data, fk_col_name, pk_col_name, rel_type, manual_bend_x=None, from_undo_redo=False):
        return create_relationship_impl(self, fk_table_data, pk_table_data, fk_col_name, pk_col_name, rel_type, manual_bend_x, from_undo_redo)

    def update_orthogonal_path(self, relationship_data):
        update_orthogonal_path_impl(self, relationship_data)

    def update_all_relationships_graphics(self):
        update_all_relationships_graphics_impl(self)

    def update_relationship_table_names(self, old_table_name, new_table_name):
        update_relationship_table_names_impl(self, old_table_name, new_table_name)

    def update_fk_references_to_pk(self, pk_table_name, old_pk_col_name, new_pk_col_name):
        update_fk_references_to_pk_impl(self, pk_table_name, old_pk_col_name, new_pk_col_name)

    def remove_relationships_for_table(self, table_name, old_columns_of_table=None):
        remove_relationships_for_table_impl(self, table_name, old_columns_of_table)
        
    def edit_relationship_properties(self, relationship_data):
        edit_relationship_properties_impl(self, relationship_data)

    def handle_import_csv_button(self):
        handle_import_csv_button_impl(self)

    def export_to_csv(self, file_path_to_save=None):
        export_to_csv_impl(self, file_path_to_save)

    def open_default_colors_dialog(self):
        open_default_colors_dialog_handler(self)

    def open_canvas_settings_dialog(self):
        open_canvas_settings_dialog_handler(self)

    def open_datatype_settings_dialog(self):
        open_datatype_settings_dialog_handler(self)

    def keyPressEvent(self, event):
        keyPressEvent_handler(self, event)

    def resizeEvent(self, event):
        super().resizeEvent(event) 
        self._update_floating_button_position()

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(0, self._update_floating_button_position)

    def update_window_title(self):
        title = "ERD Design Tool"
        if self.current_file_path:
            title += f" - {os.path.basename(self.current_file_path)}"
        else:
            title += " - Untitled"
        if not self.undo_stack.isClean():
            title += "*"
        self.setWindowTitle(title)

    def update_fk_references_to_table(self, old_table_name, new_table_name):
        for table_data in self.tables_data.values():
            if table_data.name == new_table_name and old_table_name != new_table_name:
                 pass

            for column in table_data.columns:
                if column.is_fk and column.references_table == old_table_name:
                    column.references_table = new_table_name
                    if table_data.graphic_item:
                        table_data.graphic_item.update() 

        self.update_all_relationships_graphics()
        self.populate_diagram_explorer()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # Set application icon globally (can also be done per window)
    # This is an alternative place to set it if you want it set before the window instance is created.
    # app_icon_path = "icon.ico"
    # global_app_icon = QIcon(app_icon_path)
    # if not global_app_icon.isNull():
    #     app.setWindowIcon(global_app_icon)
    # else:
    #     print(f"Warning: Could not load global application icon '{app_icon_path}'.")

    window = ERDCanvasWindow()
    window.show() 
    sys.exit(app.exec())
