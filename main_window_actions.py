# main_window_actions.py
# Contains implementations for various actions like New, Save, Delete, etc.

import copy
import os
from PyQt6.QtWidgets import QMessageBox, QFileDialog, QGraphicsView
from PyQt6.QtCore import Qt, QPointF
from gui_items import TableGraphicItem, OrthogonalRelationshipPathItem
from commands import DeleteRelationshipCommand, DeleteTableCommand
import constants

def new_diagram_action(window):
    """Clears the current diagram and starts a new one."""
    if not window.prompt_to_save_if_dirty():
        return # User cancelled or save failed

    # Proceed with creating a new diagram
    window.scene.clearSelection()

    for item in list(window.scene.items()): 
        if isinstance(item, (TableGraphicItem, OrthogonalRelationshipPathItem)): 
            window.scene.removeItem(item)

    window.tables_data.clear()
    window.relationships_data.clear()
    window.diagram_notes = "" # Clear notes
    window.copied_table_data = None # Clear copy buffer

    window.undo_stack.clear()
    window.current_file_path = None

    if hasattr(window, 'notes_text_edit') and window.notes_text_edit:
        window.notes_text_edit.setPlainText("") # Clear notes UI

    window.scene.setSceneRect(0, 0, constants.current_canvas_dimensions["width"], constants.current_canvas_dimensions["height"])

    window.update_window_title()
    window.populate_diagram_explorer()
    window.update_sql_preview_pane() # Update SQL preview for new diagram
    # print("New diagram created.")


def save_file_action(window):
    """Saves the current diagram to its existing path, or calls Save As if no path."""
    if window.current_file_path:
        window.export_to_erd(window.current_file_path) 
        window.undo_stack.setClean()
        window.update_window_title()
        return True # Indicate success
    else:
        return save_file_as_action(window) # Delegate and return its result


def save_file_as_action(window):
    """Saves the current diagram to a new file path chosen by the user."""
    suggested_path = window.current_file_path or os.path.join(os.getcwd(), "untitled.erd") # Default to .erd
    
    path, _ = QFileDialog.getSaveFileName(window, "Save ERD File As", suggested_path, "ERD Files (*.erd);;All Files (*)")
    if path:
        window.export_to_erd(path) 
        window.current_file_path = path 
        window.undo_stack.setClean() 
        window.update_window_title() 
        return True # Indicate success
    return False # Indicate cancellation or no path chosen


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
    window.update_sql_preview_pane() # Update SQL preview


def paste_copied_table_action(window, pos=None):
    """Pastes the copied table data as a new table."""
    if not window.copied_table_data:
        QMessageBox.information(window, "Paste Table", "No table data copied.")
        return

    # Create a new table data object from the copied data
    new_table_data = copy.deepcopy(window.copied_table_data)
    
    # Generate a unique name for the pasted table
    base_name = new_table_data.name
    pasted_table_name = base_name
    counter = 1
    while pasted_table_name in window.tables_data:
        pasted_table_name = f"{base_name}_copy{counter}"
        counter += 1
    new_table_data.name = pasted_table_name

    # Determine position for the new table
    paste_pos = pos if pos else QPointF(new_table_data.x + 50, new_table_data.y + 50) # Offset from original or use click pos
    new_table_data.x = paste_pos.x()
    new_table_data.y = paste_pos.y()

    # Use the existing add table logic which handles command and UI update
    # Call the wrapper in main_window.py with individual props
    window.handle_add_table_button(
        table_name_prop=new_table_data.name,
        columns_prop=new_table_data.columns,
        pos=QPointF(new_table_data.x, new_table_data.y),
        width_prop=new_table_data.width,
        body_color_hex=new_table_data.body_color.name(),
        header_color_hex=new_table_data.header_color.name()
    )

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
