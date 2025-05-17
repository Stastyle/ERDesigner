# main_window_actions.py
# Contains implementations for various actions like New, Save, Delete, etc.

import os
from PyQt6.QtWidgets import QMessageBox, QFileDialog, QGraphicsView
from PyQt6.QtCore import Qt
from gui_items import TableGraphicItem, OrthogonalRelationshipLine # For type checking
from commands import DeleteRelationshipCommand, DeleteTableCommand # Assuming commands.py is accessible
import constants # Assuming constants.py is accessible

def new_diagram_action(window):
    """Clears the current diagram and starts a new one."""
    # Clear selection on the scene first
    window.scene.clearSelection()

    # Remove all table graphics from the scene
    for table_data in list(window.tables_data.values()): # Iterate over a copy if modifying dict
        if table_data.graphic_item and table_data.graphic_item.scene():
            window.scene.removeItem(table_data.graphic_item)
            # table_data.graphic_item = None # Optional: nullify reference

    # Remove all relationship graphics from the scene
    for rel_data in list(window.relationships_data): # Iterate over a copy
        if rel_data.graphic_item and rel_data.graphic_item.scene():
            window.scene.removeItem(rel_data.graphic_item)
            # rel_data.graphic_item = None # Optional

    # Clear data structures
    window.tables_data.clear()
    window.relationships_data.clear()

    # Reset undo stack and file path
    window.undo_stack.clear()
    window.current_file_path = None

    # Reset scene rectangle to default or configured dimensions
    window.scene.setSceneRect(0, 0, constants.current_canvas_dimensions["width"], constants.current_canvas_dimensions["height"])

    # Update UI elements
    window.update_window_title()
    window.populate_diagram_explorer() # Assuming this method exists on window
    print("New diagram created.")


def save_file_action(window):
    """Saves the current diagram to its existing path, or calls Save As if no path."""
    if window.current_file_path:
        window.export_to_csv(window.current_file_path) # export_to_csv should be on window
        window.undo_stack.setClean() # Mark as saved
        window.update_window_title() # Update title to remove asterisk
    else:
        save_file_as_action(window)


def save_file_as_action(window):
    """Saves the current diagram to a new file path chosen by the user."""
    # Suggest current file path or directory if available
    suggested_path = window.current_file_path or "" # Or os.getcwd() for a default directory
    
    path, _ = QFileDialog.getSaveFileName(window, "Save ERD File", suggested_path, "CSV Files (*.csv);;All Files (*)")
    if path:
        window.export_to_csv(path) # export_to_csv should be on window
        window.current_file_path = path # Update current file path
        window.undo_stack.setClean() # Mark as saved
        window.update_window_title() # Update title


def delete_selected_items_action(window):
    """Deletes selected items (tables or relationships) from the canvas."""
    selected_graphics = window.scene.selectedItems()
    if not selected_graphics:
        return

    tables_to_delete_data_for_command = []
    rels_to_delete_data_for_command = []
    delete_message_parts = []

    # Identify selected tables first to handle cascading relationship deletions correctly
    selected_table_datas = [item.table_data for item in selected_graphics if isinstance(item, TableGraphicItem)]

    for item in selected_graphics:
        if isinstance(item, OrthogonalRelationshipLine):
            rel_data = item.relationship_data
            # Only add relationship for direct deletion if neither of its connected tables are also selected for deletion
            # (as deleting a table will automatically handle its connected relationships)
            if not any(t.name == rel_data.table1_name for t in selected_table_datas) and \
               not any(t.name == rel_data.table2_name for t in selected_table_datas):
                if rel_data not in rels_to_delete_data_for_command: # Avoid duplicates
                    rels_to_delete_data_for_command.append(rel_data)
                    delete_message_parts.append(f"Relationship '{rel_data.table1_name}.{rel_data.fk_column_name} -> {rel_data.table2_name}.{rel_data.pk_column_name}'")
        elif isinstance(item, TableGraphicItem):
            if item.table_data not in tables_to_delete_data_for_command: # Avoid duplicates
                tables_to_delete_data_for_command.append(item.table_data)
                delete_message_parts.append(f"Table '{item.table_data.name}'")
    
    if not delete_message_parts: # Nothing to delete (e.g. only parts of items selected)
        return
        
    confirm_msg = f"Are you sure you want to delete {', '.join(delete_message_parts)}?"
    if tables_to_delete_data_for_command: # Add warning if tables are being deleted
        confirm_msg += "\n(Relationships connected to deleted tables will also be removed.)"

    reply = QMessageBox.question(window, "Confirm Deletion", confirm_msg,
                                 QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                 QMessageBox.StandardButton.No)

    if reply == QMessageBox.StandardButton.No:
        return

    window.undo_stack.beginMacro(f"Delete selected: {', '.join(delete_message_parts)}")
    # Important: Delete standalone relationships first
    for rel_data in rels_to_delete_data_for_command:
        # Ensure the relationship still exists (might have been removed by a table delete command if logic is complex)
        if rel_data in window.relationships_data:
             window.undo_stack.push(DeleteRelationshipCommand(window, rel_data))
    
    # Then delete tables (which will also handle their connected relationships)
    for table_data in tables_to_delete_data_for_command:
        # Ensure table still exists
        if table_data.name in window.tables_data:
            window.undo_stack.push(DeleteTableCommand(window, table_data))
    window.undo_stack.endMacro()

    window.populate_diagram_explorer()
    # window.update_window_title() will be called by undo_stack.cleanChanged signal


def toggle_relationship_mode_action_impl(window, checked):
    """Toggles the relationship drawing mode."""
    window.drawing_relationship_mode = checked
    
    # Ensure the menu action reflects the state
    if hasattr(window, 'actionDrawRelationship') and window.actionDrawRelationship.isChecked() != checked:
        window.actionDrawRelationship.setChecked(checked)
        
    # Also update the floating button menu's corresponding action if it's separate
    # (This might require finding the action in the dynamically created menu or having a persistent reference)

    if checked:
        window.view.setDragMode(QGraphicsView.DragMode.NoDrag) # Prevent scrolling while drawing
        # Potentially change cursor too: QApplication.setOverrideCursor(Qt.CursorShape.CrossCursor)
    else:
        window.view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag) # Restore normal drag mode
        # QApplication.restoreOverrideCursor()
        # Clean up any line-in-progress if mode is turned off
        if window.scene.line_in_progress:
            window.scene.removeItem(window.scene.line_in_progress)
            window.scene.line_in_progress = None
        window.scene.start_item_for_line = None
        window.scene.start_column_for_line = None


def reset_drawing_mode_impl(window):
    """Resets the drawing mode, typically called after a relationship is drawn or cancelled."""
    # This effectively means turning off the relationship drawing mode.
    toggle_relationship_mode_action_impl(window, False)

