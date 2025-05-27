# main_window_actions.py
# Contains implementations for various actions like New, Save, Delete, etc.

import os
from PyQt6.QtWidgets import QMessageBox, QFileDialog, QGraphicsView
from PyQt6.QtCore import Qt
from gui_items import TableGraphicItem, OrthogonalRelationshipPathItem
from commands import DeleteRelationshipCommand, DeleteTableCommand
import constants

def new_diagram_action(window):
    """Clears the current diagram and starts a new one."""
    window.scene.clearSelection()

    for item in list(window.scene.items()): 
        if isinstance(item, (TableGraphicItem, OrthogonalRelationshipPathItem)): 
            window.scene.removeItem(item)

    window.tables_data.clear()
    window.relationships_data.clear()

    window.undo_stack.clear()
    window.current_file_path = None

    window.scene.setSceneRect(0, 0, constants.current_canvas_dimensions["width"], constants.current_canvas_dimensions["height"])

    window.update_window_title()
    window.populate_diagram_explorer()
    # print("New diagram created.")


def save_file_action(window):
    """Saves the current diagram to its existing path, or calls Save As if no path."""
    if window.current_file_path:
        window.export_to_csv(window.current_file_path) 
        window.undo_stack.setClean()
        window.update_window_title()
    else:
        save_file_as_action(window)


def save_file_as_action(window):
    """Saves the current diagram to a new file path chosen by the user."""
    suggested_path = window.current_file_path or os.path.join(os.getcwd(), "untitled.erd") 
    
    path, _ = QFileDialog.getSaveFileName(window, "Save ERD File", suggested_path, "ERD CSV Files (*.csv);;All Files (*)")
    if path:
        window.export_to_csv(path) 
        window.current_file_path = path 
        window.undo_stack.setClean() 
        window.update_window_title() 


def delete_selected_items_action(window):
    """Deletes selected items (tables, relationships, or groups) from the canvas."""
    selected_graphics = window.scene.selectedItems()
    if not selected_graphics:
        return

    # Separate items by type for processing order and command creation
    selected_tables_graphics = [item for item in selected_graphics if isinstance(item, TableGraphicItem)]
    selected_relationships_graphics = [item for item in selected_graphics if isinstance(item, OrthogonalRelationshipPathItem)]

    # Data objects to be passed to commands
    tables_to_delete_data = [item.table_data for item in selected_tables_graphics]

    # Filter out relationships connected to tables that will be deleted
    all_tables_being_deleted_names = set(t.name for t in tables_to_delete_data)

    rels_to_delete_directly_data = []
    for rel_item in selected_relationships_graphics:
        if not (rel_item.relationship_data.table1_name in all_tables_being_deleted_names or \
                rel_item.relationship_data.table2_name in all_tables_being_deleted_names):
            rels_to_delete_directly_data.append(rel_item.relationship_data)
    
    if not tables_to_delete_data and not rels_to_delete_directly_data:
        return # Nothing to delete after filtering

    # --- Build confirmation message ---
    delete_message_parts = []
    if tables_to_delete_data:
        delete_message_parts.append(f"{len(tables_to_delete_data)} table(s)")
    if rels_to_delete_directly_data:
        delete_message_parts.append(f"{len(rels_to_delete_directly_data)} relationship(s)")
    
    confirm_msg = f"Are you sure you want to delete {', '.join(delete_message_parts)}?"

    reply = QMessageBox.question(window, "Confirm Deletion", confirm_msg,
                                 QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                 QMessageBox.StandardButton.No)

    if reply == QMessageBox.StandardButton.No:
        return

    window.undo_stack.beginMacro(f"Delete: {', '.join(delete_message_parts)}")
    
    # Order of deletion: Relationships first, then tables
    for rel_data in rels_to_delete_directly_data:
        if rel_data in window.relationships_data: 
             window.undo_stack.push(DeleteRelationshipCommand(window, rel_data))

    for table_data in tables_to_delete_data:
        if table_data.name in window.tables_data: 
            window.undo_stack.push(DeleteTableCommand(window, table_data))

    window.undo_stack.endMacro()
    window.populate_diagram_explorer() # Update explorer after commands are executed


def toggle_relationship_mode_action_impl(window, checked):
    """Toggles the relationship drawing mode."""
    window.drawing_relationship_mode = checked

    if hasattr(window, 'actionDrawRelationship') and window.actionDrawRelationship.isChecked() != checked:
        window.actionDrawRelationship.setChecked(checked)

    if checked:
        window.view.setDragMode(QGraphicsView.DragMode.NoDrag) 
    else:
        if not window.drawing_group_mode_active: 
            window.view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag) 
        if window.scene.line_in_progress:
            window.scene.removeItem(window.scene.line_in_progress)
            window.scene.line_in_progress = None
        window.scene.start_item_for_line = None
        window.scene.start_column_for_line = None


def reset_drawing_mode_impl(window):
    """Resets the drawing mode, typically called after a relationship is drawn or cancelled."""
    if window.drawing_relationship_mode:
        toggle_relationship_mode_action_impl(window, False)
