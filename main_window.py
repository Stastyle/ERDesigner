# main_window.py
# Contains the ERDCanvasWindow class, the main application window.

import sys
import os
# import configparser # Not directly used here anymore, handled by main_window_config
import copy # Keep copy if it's used elsewhere, though not directly in this snippet

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QGraphicsView, QMessageBox, QFileDialog,
    QWidget, QHBoxLayout, QDockWidget, QTreeWidget, QTreeWidgetItem,
    QPushButton, QStyle, QMenu, QHeaderView, QInputDialog 
)
from PyQt6.QtCore import Qt, QPointF, QSize, QSizeF, QEvent, QTimer, QByteArray 
from PyQt6.QtGui import (
    QColor, QBrush, QAction, QIcon, QKeySequence, QPixmap, QPainter,
    QActionGroup, QUndoStack, QPen
)

# Import from other modules
import constants
from utils import get_standard_icon, snap_to_grid
from data_models import Table, Column, Relationship
from gui_items import TableGraphicItem, OrthogonalRelationshipPathItem
from canvas_scene import ERDGraphicsScene
from commands import (
    AddTableCommand, DeleteRelationshipCommand, CreateRelationshipCommand,
    DeleteTableCommand, EditTableCommand, SetRelationshipVerticalSegmentXCommand
    # Removed: AddOrthogonalBendCommand, MoveOrthogonalBendCommand, DeleteOrthogonalBendCommand
    # Removed: MoveCentralVerticalSegmentCommand (replaced by SetRelationshipVerticalSegmentXCommand)
)

# Import refactored modules
from main_window_config import (
    load_app_settings, save_app_settings
)
from main_window_ui_setup import (
    create_menus, create_diagram_explorer_widget,
    create_main_floating_action_button_widget,
    create_sql_preview_widget, create_notes_widget, # Added create_notes_widget
    show_floating_button_menu_widget, # Keep this
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
# main_window_group_operations will be created later
from main_window_relationship_operations import (
    finalize_relationship_drawing_impl, create_relationship_impl, 
    update_relationship_graphic_path_impl, # Renamed from update_custom_orthogonal_path_impl
    update_all_relationships_graphics_impl,
    update_relationship_table_names_impl,
    update_fk_references_to_pk_impl,
    remove_relationships_for_table_impl,
    edit_relationship_properties_impl
)
from main_window_event_handlers import (
    keyPressEvent_handler, view_wheel_event_handler
)
from main_window_file_operations import (
    handle_import_erd_button_impl, export_to_erd_impl, # Changed CSV to ERD
    handle_import_sql_button_impl # Keep SQL import as is
)
from main_window_explorer_utils import (
    populate_diagram_explorer_util, on_explorer_item_double_clicked_util,
    toggle_diagram_explorer_util, ITEM_TYPE_TABLE, ITEM_TYPE_COLUMN, ITEM_TYPE_RELATIONSHIP, ITEM_TYPE_CATEGORY
)
from main_window_dialog_handlers import ( # Keep this
    open_default_colors_dialog_handler, open_canvas_settings_dialog_handler,
    open_datatype_settings_dialog_handler
)
from sql_generator import generate_sql_for_diagram # Added

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

        app_icon_path = "icon.ico" 
        app_icon = QIcon(app_icon_path)
        if not app_icon.isNull():
            self.setWindowIcon(app_icon)

        self.current_file_path = None
        self.current_theme = "light" 
        self.user_default_table_body_color = None
        self.user_default_table_header_color = None
        self.sql_preview_visible_on_load = True # Default, will be overridden by config
        self.notes_visible_on_load = True # Default for notes visibility
        self.show_cardinality_text = constants.show_cardinality_text_globally
        self.show_cardinality_symbols = constants.show_cardinality_symbols_globally
        self.copied_table_data = None # Variable to store copied table data
        
        self.loaded_window_state = None 

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
        self.diagram_notes = "" # Initialize diagram notes

        self.drawing_group_mode_active = False # Initialize attribute
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
        create_sql_preview_widget(self) 
        create_notes_widget(self) # Create Notes dock

        # Tabify SQL Preview and Notes docks if both exist
        if hasattr(self, 'sql_preview_dock') and hasattr(self, 'notes_dock'):
            self.tabifyDockWidget(self.sql_preview_dock, self.notes_dock)
            self.sql_preview_dock.raise_() # Optionally make SQL preview the default visible tab

        apply_styles_util(self) 
        self.set_theme(self.current_theme) 

        self.undo_stack.indexChanged.connect(self.populate_diagram_explorer) 
        self.undo_stack.indexChanged.connect(self.update_sql_preview_pane) # Update SQL on undo/redo
        self.undo_stack.cleanChanged.connect(self.update_window_title) 

        # Restore window state (including dock visibility)
        # Must be after docks are created.
        if self.loaded_window_state:
            if not self.restoreState(self.loaded_window_state):
                print("Warning: Failed to restore window state.")
        
        if hasattr(self, 'diagram_explorer_dock') and hasattr(self, 'toggleExplorerAction'):
            self.toggleExplorerAction.setChecked(self.diagram_explorer_dock.isVisible())

        # Sync SQL preview action with its dock visibility (after potential restoreState)
        if hasattr(self, 'sql_preview_dock') and hasattr(self, 'toggleSqlPreviewAction'):
            self.toggleSqlPreviewAction.setChecked(self.sql_preview_dock.isVisible())
        
        # Sync Notes action with its dock visibility
        if hasattr(self, 'notes_dock') and hasattr(self, 'toggleNotesAction'):
            self.toggleNotesAction.setChecked(self.notes_dock.isVisible())
        
        # Sync Cardinality Display Mode menu
        if hasattr(self, 'update_cardinality_display_menu_state'):
            self.update_cardinality_display_menu_state()

    def handle_copy_shortcut(self):
        """Handles the global Copy action (e.g., Ctrl+C)."""
        selected_items = self.scene.selectedItems()
        table_graphics_items = [item for item in selected_items if isinstance(item, TableGraphicItem)]
        
        if len(table_graphics_items) == 1:
            # If exactly one table is selected, copy it
            self.copy_selected_table(table_graphics_items[0].table_data)
        elif not table_graphics_items:
            QMessageBox.information(self, "Copy Table", "No table selected to copy.")
        else: # Multiple tables selected, or other items
            QMessageBox.information(self, "Copy Table", "Please select a single table to copy.")

    def copy_selected_table(self, table_data_to_copy): # Renamed parameter for clarity
        """Copies the data of the given table."""
        self.copied_table_data = copy.deepcopy(table_data_to_copy)
        if hasattr(self, 'actionPasteTable'):
            self.actionPasteTable.setEnabled(True) # Enable paste action

    def paste_copied_table(self, pos=None):
        from main_window_actions import paste_copied_table_action # Local import
        paste_copied_table_action(self, pos)

    def prompt_to_save_if_dirty(self):
        """
        Checks if the current diagram has unsaved changes. If so, prompts the user
        to save, discard, or cancel.
        Returns True if the calling action should proceed, False if it should be cancelled.
        """
        if self.undo_stack.isClean():
            return True # No unsaved changes, proceed

        file_name = os.path.basename(self.current_file_path) if self.current_file_path else "Untitled"
        reply = QMessageBox.question(self, "Unsaved Changes",
                                     f"Diagram '{file_name}' has unsaved changes.\n"
                                     "Do you want to save the changes?",
                                     QMessageBox.StandardButton.Save |
                                     QMessageBox.StandardButton.Discard | # "Don't Save"
                                     QMessageBox.StandardButton.Cancel)

        if reply == QMessageBox.StandardButton.Save:
            return self.save_file() # save_file() now returns True on success, False on cancel
        elif reply == QMessageBox.StandardButton.Discard:
            return True # Proceed without saving
        elif reply == QMessageBox.StandardButton.Cancel:
            return False # Cancel the original action
        return False # Default to cancel

    def closeEvent(self, event):
        if self.prompt_to_save_if_dirty():
            self.save_app_settings() # Save app settings (like window state, theme)
            event.accept() # Proceed with closing
        else:
            event.ignore() # User cancelled closing

    def load_app_settings(self): load_app_settings(self)
    def save_app_settings(self): save_app_settings(self)
    def update_theme_settings(self): update_theme_settings_util(self)
    def set_theme(self, theme_name, force_update_tables=False): set_theme_util(self, theme_name, force_update_tables)
    def apply_styles(self): apply_styles_util(self)
    def toggle_diagram_explorer(self, checked):
        toggle_diagram_explorer_util(self, checked)
        QTimer.singleShot(0, self.save_app_settings) 
    def populate_diagram_explorer(self): populate_diagram_explorer_util(self)
    def update_sql_preview_pane(self):
        if hasattr(self, 'sql_preview_text_edit') and self.sql_preview_text_edit:
            sql_code = generate_sql_for_diagram(self.tables_data, self.relationships_data)
            self.sql_preview_text_edit.setPlainText(sql_code)
    def on_notes_changed(self):
        # This method is connected to the textChanged signal of notes_text_edit
        if hasattr(self, 'notes_text_edit') and self.notes_text_edit:
            # Check if signals are blocked (e.g., by an undo/redo command setting the text)
            if self.notes_text_edit.signalsBlocked():
                return

            current_text_in_editor = self.notes_text_edit.toPlainText()
            
            # If the current text in editor is different from our model (self.diagram_notes),
            # it means the user has typed something new.
            # self.diagram_notes should be the state *before* this current edit
            if self.diagram_notes != current_text_in_editor: 
                from commands import EditNotesCommand # Local import
                old_notes_for_command = self.diagram_notes # This is the value *before* the current edit
                
                # IMPORTANT: Update the model *before* pushing the command.
                # The command's initial redo will then see the model as already up-to-date
                # and will skip updating the QTextEdit, thus preserving cursor position.
                self.diagram_notes = current_text_in_editor
                                
                command = EditNotesCommand(self, old_notes_for_command, current_text_in_editor)
                self.undo_stack.push(command)
                # update_window_title is now handled by the command's _apply_notes
    def on_explorer_item_double_clicked(self, item, column): on_explorer_item_double_clicked_util(self, item, column)
    def _update_floating_button_position(self): update_floating_button_position_widget(self)
    def show_floating_button_menu(self): show_floating_button_menu_widget(self)
    
    def new_diagram(self): new_diagram_action(self) 
    def save_file(self): save_file_action(self)
    def save_file_as(self): save_file_as_action(self)

    def export_to_sql_action(self):
        """Exports the current diagram to an SQL file."""
        if not self.tables_data:
            QMessageBox.information(self, "Export SQL", "No tables to export.")
            return

        suggested_filename = "schema.sql"
        if self.current_file_path:
            base, _ = os.path.splitext(os.path.basename(self.current_file_path))
            suggested_filename = f"{base}_schema.sql"
        
        path, _ = QFileDialog.getSaveFileName(self, "Save SQL File", suggested_filename, "SQL Files (*.sql);;All Files (*)")
        if path:
            sql_code = generate_sql_for_diagram(self.tables_data, self.relationships_data)
            try:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(sql_code)
                QMessageBox.information(self, "Export Successful", f"SQL schema saved to {path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Could not save SQL file: {e}")

    def delete_selected_items(self): delete_selected_items_action(self) 
    def toggle_relationship_mode_action(self, checked): toggle_relationship_mode_action_impl(self, checked)
    def reset_drawing_mode(self): reset_drawing_mode_impl(self)
    
    def handle_add_table_button(self, table_name_prop=None, columns_prop=None, pos=None, width_prop=None, body_color_hex=None, header_color_hex=None, from_undo_redo=False):
        """
        Wrapper to call the implementation for adding a table.
        This method maintains the older signature for compatibility with callers like CSV import
        and scene interactions, but bundles arguments appropriately for handle_add_table_button_impl.
        """
        table_props_to_pass = None
        interactive_pos_to_pass = None

        if table_name_prop:  # Indicates a programmatic call (e.g., CSV import)
            table_props_to_pass = {
                "name": table_name_prop,
                "columns": columns_prop if columns_prop is not None else [],
                "pos": pos,  # pos from CSV is the actual desired position
                "width": width_prop,
                "body_color_hex": body_color_hex,
                "header_color_hex": header_color_hex
            }
        elif pos:  # Interactive call with a suggested position (e.g., double-click on canvas)
            interactive_pos_to_pass = pos

        return handle_add_table_button_impl(
            self,
            table_props=table_props_to_pass,
            from_undo_redo=from_undo_redo,
            interactive_pos=interactive_pos_to_pass
        )    

    def finalize_relationship_drawing(self, source_table_data, source_column_data, dest_table_data, dest_column_data):
        finalize_relationship_drawing_impl(self, source_table_data, source_column_data, dest_table_data, dest_column_data)
    
    def create_relationship(self, fk_table_data, pk_table_data, fk_col_name, pk_col_name, rel_type, 
                            vertical_segment_x_override=None, # Added for consistency with CSV/Commands
                            from_undo_redo=False):
        return create_relationship_impl(self, fk_table_data, pk_table_data, fk_col_name, pk_col_name, rel_type, 
                                        vertical_segment_x_override, from_undo_redo)
    
    def update_relationship_graphic_path(self, relationship_data): # Renamed
        update_relationship_graphic_path_impl(self, relationship_data)
    
    def update_all_relationships_graphics(self): update_all_relationships_graphics_impl(self)
    def update_relationship_table_names(self, old_table_name, new_table_name): update_relationship_table_names_impl(self, old_table_name, new_table_name)
    def update_fk_references_to_pk(self, pk_table_name, old_pk_col_name, new_pk_col_name): update_fk_references_to_pk_impl(self, pk_table_name, old_pk_col_name, new_pk_col_name)
    def remove_relationships_for_table(self, table_name, old_columns_of_table=None): remove_relationships_for_table_impl(self, table_name, old_columns_of_table)
    def edit_relationship_properties(self, relationship_data): edit_relationship_properties_impl(self, relationship_data)
    def handle_import_sql_button(self): handle_import_sql_button_impl(self)
    
    def handle_import_erd_button(self): handle_import_erd_button_impl(self) 
    def export_to_erd(self, file_path_to_save=None): export_to_erd_impl(self, file_path_to_save) 
    
    def open_default_colors_dialog(self): open_default_colors_dialog_handler(self)
    def open_canvas_settings_dialog(self): open_canvas_settings_dialog_handler(self)
    def open_datatype_settings_dialog(self): open_datatype_settings_dialog_handler(self)
    def toggle_sql_preview(self, checked):
        if hasattr(self, 'sql_preview_dock'):
            self.sql_preview_dock.setVisible(checked)
            # Save settings when visibility is toggled by user action
            QTimer.singleShot(0, self.save_app_settings)
    def toggle_notes_view(self, checked):
        if hasattr(self, 'notes_dock'):
            self.notes_dock.setVisible(checked)
            # Save settings when visibility is toggled by user action
            QTimer.singleShot(0, self.save_app_settings)

    def toggle_cardinality_text_display(self, checked):
        if self.show_cardinality_text != checked:
            self.show_cardinality_text = checked
            constants.show_cardinality_text_globally = checked
            self.update_all_relationships_graphics()
            self.save_app_settings()
            # self.update_cardinality_display_menu_state() # Action state is auto-managed

    def toggle_cardinality_symbols_display(self, checked):
        if self.show_cardinality_symbols != checked:
            self.show_cardinality_symbols = checked
            constants.show_cardinality_symbols_globally = checked
            self.update_all_relationships_graphics()
            self.save_app_settings()
            # self.update_cardinality_display_menu_state() # Action state is auto-managed

    def update_cardinality_display_menu_state(self):
        # Called after loading settings to set initial check state of menu items
        if hasattr(self, 'actionShowCardinalityText'):
            self.actionShowCardinalityText.setChecked(self.show_cardinality_text)
        if hasattr(self, 'actionShowCardinalitySymbols'):
            self.actionShowCardinalitySymbols.setChecked(self.show_cardinality_symbols)


    def keyPressEvent(self, event): keyPressEvent_handler(self, event)
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
        """Updates FK references in all tables when a table name changes."""
        for table_data in self.tables_data.values():
            if table_data.name == new_table_name and old_table_name != new_table_name:
                 pass # This table is the one being renamed, its own FKs are not affected by its own name change

            for column in table_data.columns:
                if column.is_fk and column.references_table == old_table_name:
                    column.references_table = new_table_name
                    if table_data.graphic_item: 
                        table_data.graphic_item.update()

        self.update_all_relationships_graphics() 
        self.populate_diagram_explorer() 


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = ERDCanvasWindow()
    window.show()
    sys.exit(app.exec())
