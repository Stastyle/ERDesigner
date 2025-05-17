# main_window_relationship_operations.py
# Handles operations related to relationships.

import math
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QPen
from data_models import Relationship # Assuming data_models.py is accessible
from gui_items import OrthogonalRelationshipLine # Assuming gui_items.py is accessible
from commands import CreateRelationshipCommand, DeleteRelationshipCommand # Assuming commands.py is accessible
from dialogs import RelationshipDialog # Assuming dialogs.py is accessible
import constants
from utils import snap_to_grid


def finalize_relationship_drawing_impl(window, source_table_data, source_column_data, dest_table_data, dest_column_data):
    """Finalizes drawing a relationship between two columns."""
    # Determine which is FK and which is PK based on their properties
    fk_table, fk_col_obj, pk_table, pk_col_obj = None, None, None, None

    if source_column_data.is_pk and not dest_column_data.is_pk:
        # Source is PK, Dest will be FK
        pk_table, pk_col_obj = source_table_data, source_column_data
        fk_table, fk_col_obj = dest_table_data, dest_column_data
    elif not source_column_data.is_pk and dest_column_data.is_pk:
        # Dest is PK, Source will be FK
        pk_table, pk_col_obj = dest_table_data, dest_column_data
        fk_table, fk_col_obj = source_table_data, source_column_data
    else:
        # Invalid connection (e.g., PK-PK or nonPK-nonPK)
        msg = "Cannot create relationship: One column must be a Primary Key (PK) and the other a non-PK (which will become the Foreign Key)."
        if source_column_data.is_pk and dest_column_data.is_pk:
            msg = "Cannot connect two Primary Key columns directly. Choose one PK and one non-PK column."
        elif not source_column_data.is_pk and not dest_column_data.is_pk:
            msg = "Cannot connect two non-Primary Key columns. One column must be a Primary Key."
        QMessageBox.warning(window, "Invalid Connection", msg)
        window.reset_drawing_mode() # reset_drawing_mode should be on window
        return

    # Check if the chosen FK column is already an FK to a different PK
    if fk_col_obj.is_fk and \
       (fk_col_obj.references_table != pk_table.name or fk_col_obj.references_column != pk_col_obj.name):
        confirm_msg = (f"Column '{fk_col_obj.name}' in table '{fk_table.name}' is already a Foreign Key "
                       f"referencing '{fk_col_obj.references_table}.{fk_col_obj.references_column}'.\n\n"
                       f"Do you want to change it to reference '{pk_table.name}.{pk_col_obj.name}' instead?")
        reply = QMessageBox.question(window, "Confirm FK Change", confirm_msg,
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.No:
            window.reset_drawing_mode()
            return
            
    # Default relationship type, can be changed later via properties dialog
    default_rel_type = "N:1" # Or constants.DEFAULT_RELATIONSHIP_TYPE

    # Use CreateRelationshipCommand for undo/redo
    command = CreateRelationshipCommand(window, fk_table, pk_table, fk_col_obj.name, pk_col_obj.name, default_rel_type)
    window.undo_stack.push(command)
    window.reset_drawing_mode()


def create_relationship_impl(window, fk_table_data, pk_table_data, fk_col_name, pk_col_name, rel_type, manual_bend_x=None, from_undo_redo=False):
    """
    Creates a relationship data object and its graphical representation.
    This is called by CreateRelationshipCommand's redo() and potentially by import logic.
    Returns the Relationship object or None if creation fails.
    """
    # Check if this exact relationship already exists
    existing_rel = next((r for r in window.relationships_data if
                         r.table1_name == fk_table_data.name and r.fk_column_name == fk_col_name and
                         r.table2_name == pk_table_data.name and r.pk_column_name == pk_col_name), None)

    fk_col_in_table = fk_table_data.get_column_by_name(fk_col_name)
    if not fk_col_in_table:
        print(f"Error creating relationship: FK column '{fk_col_name}' not found in table '{fk_table_data.name}'.")
        return None # Should not happen if command is well-formed

    if existing_rel:
        # This might happen during an import if FKs are defined in columns AND explicitly in relationships section.
        # Or if a command tries to re-create an existing one without proper checks.
        # For now, let's assume we update its properties if types differ or bend point changes.
        print(f"Relationship from {fk_table_data.name}.{fk_col_name} to {pk_table_data.name}.{pk_col_name} already exists. Checking for updates.")
        changed = False
        if existing_rel.relationship_type != rel_type:
            existing_rel.relationship_type = rel_type
            changed = True
        if manual_bend_x is not None and existing_rel.manual_bend_offset_x != manual_bend_x:
            existing_rel.manual_bend_offset_x = manual_bend_x
            changed = True
        
        # Ensure the FK column properties are correctly set (as this function might be the source of truth)
        if not fk_col_in_table.is_fk or \
           fk_col_in_table.references_table != pk_table_data.name or \
           fk_col_in_table.references_column != pk_col_name or \
           fk_col_in_table.fk_relationship_type != rel_type:
            
            fk_col_in_table.is_fk = True
            fk_col_in_table.references_table = pk_table_data.name
            fk_col_in_table.references_column = pk_col_name
            fk_col_in_table.fk_relationship_type = rel_type # Store type on FK as well
            if fk_table_data.graphic_item: fk_table_data.graphic_item.update() # Redraw table to show FK
            changed = True # Mark as changed if FK properties were updated

        if changed and existing_rel.graphic_item:
            existing_rel.graphic_item.update_tooltip_and_paint()
            update_orthogonal_path_impl(window, existing_rel) # Recalculate path
        return existing_rel

    # Create new relationship data object
    relationship = Relationship(fk_table_data.name, pk_table_data.name, fk_col_name, pk_col_name, rel_type)
    if manual_bend_x is not None:
        relationship.manual_bend_offset_x = manual_bend_x
    window.relationships_data.append(relationship)

    # Create graphical item for the relationship
    line_item = OrthogonalRelationshipLine(relationship) # Pass the data object
    line_item.setPen(QPen(window.current_theme_settings.get("relationship_line_color"), 1.8)) # Apply theme color
    window.scene.addItem(line_item)
    relationship.graphic_item = line_item # Link data and graphic item

    update_orthogonal_path_impl(window, relationship) # Calculate and set initial path

    # Update the FK column in the source table data
    fk_col_in_table.is_fk = True
    fk_col_in_table.references_table = pk_table_data.name
    fk_col_in_table.references_column = pk_col_name
    fk_col_in_table.fk_relationship_type = rel_type # Store relationship type on FK column as well
    if fk_table_data.graphic_item:
        fk_table_data.graphic_item.update() # Redraw table to show FK indicator

    if not from_undo_redo and not window.undo_stack.isActive(): # Avoid during macro or direct undo/redo
        window.populate_diagram_explorer()
        # window.update_window_title() will be handled by undo_stack signals
    
    return relationship


def update_orthogonal_path_impl(window, relationship_data):
    """Updates the path of an orthogonal relationship line."""
    if not relationship_data.graphic_item:
        return

    table1_obj = window.tables_data.get(relationship_data.table1_name) # FK table
    table2_obj = window.tables_data.get(relationship_data.table2_name) # PK table

    if not (table1_obj and table1_obj.graphic_item and table2_obj and table2_obj.graphic_item):
        # One or both tables/graphics don't exist, hide the line or set a dummy path
        if isinstance(relationship_data.graphic_item, OrthogonalRelationshipLine):
            relationship_data.graphic_item.set_path_points(QPointF(), QPointF(), QPointF(), QPointF()) # Effectively hides it
        return

    t1_graphic = table1_obj.graphic_item
    t2_graphic = table2_obj.graphic_item

    # Get attachment points based on column names
    p1 = t1_graphic.get_attachment_point(t2_graphic, relationship_data.fk_column_name) # From FK
    p2 = t2_graphic.get_attachment_point(t1_graphic, relationship_data.pk_column_name) # To PK

    bend1, bend2 = QPointF(), QPointF() # Intermediate points for orthogonal line

    # Determine the X coordinate for the vertical segment
    vertical_segment_x = relationship_data.manual_bend_offset_x

    if vertical_segment_x is None: # Auto-calculate
        t1_rect = t1_graphic.sceneBoundingRect()
        t2_rect = t2_graphic.sceneBoundingRect()
        
        # Heuristic for default bend position:
        # If tables significantly overlap horizontally, push the vertical segment outside.
        horizontal_center_diff = abs(t1_rect.center().x() - t2_rect.center().x())
        min_gap_for_between = constants.GRID_SIZE * 2 # Min gap to consider placing vertical segment between tables

        if horizontal_center_diff < (t1_graphic.width / 2 + t2_graphic.width / 2 - min_gap_for_between):
            # Tables are somewhat overlapping or very close horizontally
            is_t1_left_of_t2_center = t1_rect.center().x() < t2_rect.center().x()
            
            # Check if one is clearly above the other (allows for vertical routing between them if far apart enough)
            is_t1_above_t2 = t1_rect.bottom() < t2_rect.top() + constants.GRID_SIZE # t1 fully above t2
            is_t2_above_t1 = t2_rect.bottom() < t1_rect.top() + constants.GRID_SIZE # t2 fully above t1

            if is_t1_above_t2 or is_t2_above_t1: # One is above the other, can route between if X allows
                 vertical_segment_x = (p1.x() + p2.x()) / 2.0
            else: # Side-by-side or overlapping vertically, route outside
                if p1.x() < t1_rect.center().x(): # p1 is on the left of t1
                    # Route to the left of both tables
                    vertical_segment_x = min(t1_rect.left(), t2_rect.left()) - constants.MIN_HORIZONTAL_SEGMENT - constants.GRID_SIZE
                else: # p1 is on the right of t1
                    # Route to the right of both tables
                    vertical_segment_x = max(t1_rect.right(), t2_rect.right()) + constants.MIN_HORIZONTAL_SEGMENT + constants.GRID_SIZE
        else: # Tables are horizontally separated enough
            vertical_segment_x = (p1.x() + p2.x()) / 2.0
        
        vertical_segment_x = snap_to_grid(vertical_segment_x, constants.GRID_SIZE)

    # Define bend points
    bend1 = QPointF(vertical_segment_x, p1.y())
    bend2 = QPointF(vertical_segment_x, p2.y())

    # Ensure minimum horizontal segment length from tables to the vertical segment
    if p1.x() != bend1.x(): # If there's a horizontal segment from p1
        if abs(p1.x() - bend1.x()) < constants.MIN_HORIZONTAL_SEGMENT:
            bend1.setX(p1.x() + math.copysign(constants.MIN_HORIZONTAL_SEGMENT, bend1.x() - p1.x()))
            bend2.setX(bend1.x()) # Keep vertical segment aligned

    if p2.x() != bend2.x(): # If there's a horizontal segment to p2
         if abs(p2.x() - bend2.x()) < constants.MIN_HORIZONTAL_SEGMENT:
            if relationship_data.manual_bend_offset_x is None: # Only adjust if auto-calculating
                new_bend_x_for_p2 = p2.x() + math.copysign(constants.MIN_HORIZONTAL_SEGMENT, bend2.x() - p2.x())
                # This adjustment should ideally shift the entire vertical segment if it was auto-calculated
                # For simplicity, we might just adjust p2's connection point if it's too close,
                # or better, ensure the vertical_segment_x calculation respected this from the start.
                # For now, let's assume vertical_segment_x is dominant if manually set.
                # If auto, and this happens, it implies the initial vertical_segment_x was too close to p2.
                # A more robust solution would re-evaluate vertical_segment_x if this condition is met.
                # Quick fix: if auto, and p2 is too close, shift the vertical segment.
                bend2.setX(new_bend_x_for_p2)
                bend1.setX(new_bend_x_for_p2) # Shift entire vertical line

    if isinstance(relationship_data.graphic_item, OrthogonalRelationshipLine):
        relationship_data.graphic_item.set_path_points(p1, bend1, bend2, p2)
        relationship_data.graphic_item.update_tooltip_and_paint()


def update_all_relationships_graphics_impl(window):
    """Updates the graphics for all relationships."""
    for rel_data in window.relationships_data:
        update_orthogonal_path_impl(window, rel_data)


def update_relationship_table_names_impl(window, old_table_name, new_table_name):
    """Updates table names within relationship data objects when a table is renamed."""
    for rel in window.relationships_data:
        if rel.table1_name == old_table_name:
            rel.table1_name = new_table_name
        if rel.table2_name == old_table_name:
            rel.table2_name = new_table_name
    
    # This function primarily updates the Relationship objects.
    # The main ERDCanvasWindow.update_fk_references_to_table handles updating Column objects.
    # Both are needed.

    update_all_relationships_graphics_impl(window) # Redraw lines as names might affect tooltips
    window.populate_diagram_explorer()


def update_fk_references_to_pk_impl(window, pk_table_name, old_pk_col_name, new_pk_col_name):
    """
    Updates FK column references and relationship data when a PK column name changes or is deleted.
    If new_pk_col_name is None, it implies the PK was removed, so related FKs should be cleared.
    """
    print(f"REL_OPS: update_fk_references_to_pk for table '{pk_table_name}', old PK: '{old_pk_col_name}', new PK: '{new_pk_col_name}'")
    
    # Update Column objects that were FKs to the old PK
    for table_data in window.tables_data.values(): # Iterate through all tables
        for column in table_data.columns:
            if column.is_fk and column.references_table == pk_table_name and column.references_column == old_pk_col_name:
                if new_pk_col_name: # PK name changed
                    column.references_column = new_pk_col_name
                    print(f"  Updated FK '{column.name}' in table '{table_data.name}' to reference new PK '{new_pk_col_name}'")
                else: # PK was deleted
                    print(f"  Clearing FK '{column.name}' in table '{table_data.name}' as PK '{old_pk_col_name}' was deleted.")
                    column.is_fk = False
                    column.references_table = None
                    column.references_column = None
                    column.fk_relationship_type = None # Clear relationship type too
                    
                    # Find and mark the corresponding Relationship object for removal
                    # This part is tricky because the DeleteRelationshipCommand should handle the actual removal.
                    # For now, we'll just update the column data. The command that deleted the PK
                    # should also be responsible for creating DeleteRelationshipCommands for affected relationships.
                    # However, if this is called directly after a PK is modified by EditTableCommand,
                    # we might need to queue up relationship deletions here.

                if table_data.graphic_item:
                    table_data.graphic_item.update() # Redraw table to reflect FK change

    # Update Relationship objects
    rels_to_remove_if_pk_deleted = []
    for rel in window.relationships_data:
        if rel.table2_name == pk_table_name and rel.pk_column_name == old_pk_col_name:
            if new_pk_col_name: # PK name changed
                rel.pk_column_name = new_pk_col_name
                print(f"  Updated Relationship object: FK {rel.table1_name}.{rel.fk_column_name} now points to PK {rel.table2_name}.{new_pk_col_name}")
            else: # PK was deleted, this relationship is now invalid
                print(f"  Marking Relationship object for removal: FK {rel.table1_name}.{rel.fk_column_name} to PK {rel.table2_name}.{old_pk_col_name}")
                rels_to_remove_if_pk_deleted.append(rel)

    # If PK was deleted, actually remove the relationship objects and their graphics
    # This should ideally be done via DeleteRelationshipCommand for undo/redo.
    # This function is more of a direct data updater.
    if not new_pk_col_name and rels_to_remove_if_pk_deleted:
        print(f"  Attempting to remove {len(rels_to_remove_if_pk_deleted)} relationships due to PK deletion.")
        for rel_to_remove in rels_to_remove_if_pk_deleted:
            if rel_to_remove.graphic_item and rel_to_remove.graphic_item.scene():
                window.scene.removeItem(rel_to_remove.graphic_item)
            if rel_to_remove in window.relationships_data:
                window.relationships_data.remove(rel_to_remove)
                print(f"    Removed relationship: {rel_to_remove.table1_name}.{rel_to_remove.fk_column_name} -> {rel_to_remove.table2_name}.{rel_to_remove.pk_column_name}")


    update_all_relationships_graphics_impl(window) # Redraw all lines
    window.populate_diagram_explorer()


def remove_relationships_for_table_impl(window, table_name, old_columns_of_table=None):
    """
    Removes relationships connected to a table, typically when the table is being deleted
    or when its columns that formed relationships are modified/deleted.

    If old_columns_of_table is provided, it's used to identify FKs that existed on this table
    and might need their relationships removed if those FKs are no longer valid.
    """
    rels_to_remove = []

    # Case 1: Removing relationships because the table `table_name` is being deleted.
    # Collect all relationships where `table_name` is either table1 (FK side) or table2 (PK side).
    for rel in window.relationships_data:
        if rel.table1_name == table_name or rel.table2_name == table_name:
            if rel not in rels_to_remove:
                rels_to_remove.append(rel)

    # Case 2: If `old_columns_of_table` is provided, it means we are checking FKs
    # defined *within* the table `table_name` that might have been removed or changed.
    # This is usually called from EditTableCommand's undo/redo or before applying changes.
    if old_columns_of_table:
        current_table_obj = window.tables_data.get(table_name) # Get current state if exists
        for old_col_data in old_columns_of_table:
            if old_col_data.is_fk and old_col_data.references_table and old_col_data.references_column:
                # Check if this FK still exists and is valid in the current table definition
                is_fk_still_valid = False
                if current_table_obj:
                    current_col_version = current_table_obj.get_column_by_name(old_col_data.name)
                    if current_col_version and current_col_version.is_fk and \
                       current_col_version.references_table == old_col_data.references_table and \
                       current_col_version.references_column == old_col_data.references_column:
                        is_fk_still_valid = True
                
                if not is_fk_still_valid: # The FK was removed or changed
                    rel_based_on_old_fk = next((r for r in window.relationships_data if
                                                r.table1_name == table_name and r.fk_column_name == old_col_data.name and
                                                r.table2_name == old_col_data.references_table and
                                                r.pk_column_name == old_col_data.references_column), None)
                    if rel_based_on_old_fk and rel_based_on_old_fk not in rels_to_remove:
                        rels_to_remove.append(rel_based_on_old_fk)
                        print(f"  Marking relationship for removal due to FK change in '{table_name}': {old_col_data.name}")


    # Perform the removal (this part should ideally be wrapped in DeleteRelationshipCommand by the caller)
    for rel_to_remove in rels_to_remove:
        if rel_to_remove.graphic_item and rel_to_remove.graphic_item.scene():
            window.scene.removeItem(rel_to_remove.graphic_item)
        if rel_to_remove in window.relationships_data:
            window.relationships_data.remove(rel_to_remove)
            print(f"Relationship removed: {rel_to_remove.table1_name}.{rel_to_remove.fk_column_name} -> {rel_to_remove.table2_name}.{rel_to_remove.pk_column_name}")

    if rels_to_remove: # If any relationships were actually removed
        update_all_relationships_graphics_impl(window) # Update remaining lines
        window.populate_diagram_explorer()
        # Caller should handle undo stack if this is part of a larger operation


def edit_relationship_properties_impl(window, relationship_data):
    """Opens a dialog to edit properties of an existing relationship."""
    if not relationship_data:
        return

    # Store original state for potential undo (though dialog might handle its own command)
    original_type = relationship_data.relationship_type
    original_bend_x = relationship_data.manual_bend_offset_x

    dialog = RelationshipDialog(relationship_data, window) # Pass main window as parent
    if dialog.exec():
        # The dialog itself (or its OK action) should have updated relationship_data
        # and ideally pushed an EditRelationshipCommand to the undo stack.
        # If not, we need to detect changes and push a command here.

        new_type = relationship_data.relationship_type # Fetched from dialog's changes to object
        new_bend_x = relationship_data.manual_bend_offset_x

        # Check if anything actually changed to avoid unnecessary undo steps or updates
        changed = False
        if new_type != original_type or new_bend_x != original_bend_x:
            changed = True
            # If dialog doesn't handle undo, an EditRelationshipCommand would be created here.
            # For now, assume dialog updates the object directly.
            print(f"Relationship properties updated for: {relationship_data.table1_name}.{relationship_data.fk_column_name}")

        if changed:
            # Update the FK column's stored relationship type if it changed
            fk_table = window.tables_data.get(relationship_data.table1_name)
            if fk_table:
                fk_col = fk_table.get_column_by_name(relationship_data.fk_column_name)
                if fk_col and fk_col.is_fk:
                    if fk_col.fk_relationship_type != new_type:
                        fk_col.fk_relationship_type = new_type
                        if fk_table.graphic_item: fk_table.graphic_item.update()


            update_orthogonal_path_impl(window, relationship_data) # Redraw with new properties
            window.populate_diagram_explorer()
            window.undo_stack.setClean(False) # Mark as dirty if changes were made
            window.update_window_title()
    else:
        # Dialog was cancelled, revert any temporary changes if RelationshipDialog modifies object live
        relationship_data.relationship_type = original_type
        relationship_data.manual_bend_offset_x = original_bend_x
