# main_window_relationship_operations.py
# Handles operations related to relationships.

import math
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QPen, QColor
from data_models import Relationship
from gui_items import OrthogonalRelationshipPathItem # Updated import
from commands import CreateRelationshipCommand, DeleteRelationshipCommand
from dialogs import RelationshipDialog
import constants
from utils import snap_to_grid


def finalize_relationship_drawing_impl(window, source_table_data, source_column_data, dest_table_data, dest_column_data):
    """Finalizes drawing a relationship between two columns."""
    fk_table, fk_col_obj, pk_table, pk_col_obj = None, None, None, None

    # Determine which column is PK and which will become FK
    if source_column_data.is_pk and not dest_column_data.is_pk:
        pk_table, pk_col_obj = source_table_data, source_column_data
        fk_table, fk_col_obj = dest_table_data, dest_column_data
    elif not source_column_data.is_pk and dest_column_data.is_pk:
        pk_table, pk_col_obj = dest_table_data, dest_column_data
        fk_table, fk_col_obj = source_table_data, source_column_data
    else:
        msg = "Cannot create relationship: One column must be a Primary Key (PK) and the other a non-PK (which will become the Foreign Key)."
        if source_column_data.is_pk and dest_column_data.is_pk:
            msg = "Cannot connect two Primary Key columns directly. Choose one PK and one non-PK column."
        elif not source_column_data.is_pk and not dest_column_data.is_pk:
            msg = "Cannot connect two non-Primary Key columns. One column must be a Primary Key."
        QMessageBox.warning(window, "Invalid Connection", msg)
        window.reset_drawing_mode()
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

    default_rel_type = "N:1" # Default relationship type

    # New relationships are created without initial anchor points (straight or simple orthogonal)
    command = CreateRelationshipCommand(window, fk_table, pk_table, fk_col_obj.name, pk_col_obj.name, default_rel_type, initial_anchor_points=[])
    window.undo_stack.push(command)
    window.reset_drawing_mode()


def create_relationship_impl(window, fk_table_data, pk_table_data, fk_col_name, pk_col_name, rel_type,
                             initial_anchor_points=None, # Expecting a list of QPointF, e.g., [A1, A2, B1, B2]
                             from_undo_redo=False):
    """
    Creates a relationship data object and its graphical representation.
    'initial_anchor_points' is a list of QPointF for pre-defined anchors.
    """
    # Check if relationship already exists
    existing_rel = next((r for r in window.relationships_data if
                         r.table1_name == fk_table_data.name and r.fk_column_name == fk_col_name and
                         r.table2_name == pk_table_data.name and r.pk_column_name == pk_col_name), None)

    fk_col_in_table = fk_table_data.get_column_by_name(fk_col_name)
    if not fk_col_in_table:
        print(f"Error creating relationship: FK column '{fk_col_name}' not found in table '{fk_table_data.name}'.")
        return None

    if existing_rel:
        print(f"Relationship from {fk_table_data.name}.{fk_col_name} to {pk_table_data.name}.{pk_col_name} already exists. Updating properties.")
        changed = False
        if existing_rel.relationship_type != rel_type:
            existing_rel.relationship_type = rel_type
            changed = True

        # Update anchor points if provided and different
        new_anchors = [QPointF(p) for p in initial_anchor_points] if initial_anchor_points else []
        if existing_rel.anchor_points != new_anchors: # Compare lists of QPointF
            existing_rel.anchor_points = new_anchors
            changed = True

        # Ensure FK column properties are correctly set/updated
        if not fk_col_in_table.is_fk or \
           fk_col_in_table.references_table != pk_table_data.name or \
           fk_col_in_table.references_column != pk_col_name or \
           fk_col_in_table.fk_relationship_type != rel_type:

            fk_col_in_table.is_fk = True
            fk_col_in_table.references_table = pk_table_data.name
            fk_col_in_table.references_column = pk_col_name
            fk_col_in_table.fk_relationship_type = rel_type
            if fk_table_data.graphic_item: fk_table_data.graphic_item.update()
            changed = True

        if changed and existing_rel.graphic_item:
            existing_rel.graphic_item.update_tooltip_and_paint() # Triggers repaint
            update_custom_orthogonal_path_impl(window, existing_rel) # Recalculate path with new anchors/type
        return existing_rel

    # Create new relationship if it doesn't exist
    relationship = Relationship(fk_table_data.name, pk_table_data.name, fk_col_name, pk_col_name, rel_type)

    # Assign anchor points if provided
    relationship.anchor_points = [QPointF(p) for p in initial_anchor_points] if initial_anchor_points else []

    window.relationships_data.append(relationship)

    # Create graphical item
    line_item = OrthogonalRelationshipPathItem(relationship) # Use updated class name
    default_line_color = QColor(70,70,110) # Fallback
    line_color_from_theme = window.current_theme_settings.get("relationship_line_color", default_line_color)

    if isinstance(line_color_from_theme, str):
        line_color_to_use = QColor(line_color_from_theme)
    elif isinstance(line_color_from_theme, QColor):
        line_color_to_use = line_color_from_theme
    else:
        line_color_to_use = default_line_color

    line_item.setPen(QPen(line_color_to_use, 1.8))
    window.scene.addItem(line_item)
    relationship.graphic_item = line_item # Link data to graphic item

    update_custom_orthogonal_path_impl(window, relationship) # Build initial path

    # Update FK column in the data model
    fk_col_in_table.is_fk = True
    fk_col_in_table.references_table = pk_table_data.name
    fk_col_in_table.references_column = pk_col_name
    fk_col_in_table.fk_relationship_type = rel_type # Store relationship type on FK column as well
    if fk_table_data.graphic_item:
        fk_table_data.graphic_item.update() # Redraw table to show FK indicator

    if not from_undo_redo and not window.undo_stack.isActive(): # Avoid double population during command execution
        window.populate_diagram_explorer()

    return relationship


def update_custom_orthogonal_path_impl(window, relationship_data):
    """Updates the path of a custom orthogonal relationship line."""
    if not relationship_data.graphic_item or not isinstance(relationship_data.graphic_item, OrthogonalRelationshipPathItem):
        return

    table1_obj = window.tables_data.get(relationship_data.table1_name) # FK side
    table2_obj = window.tables_data.get(relationship_data.table2_name) # PK side

    if not (table1_obj and table1_obj.graphic_item and table2_obj and table2_obj.graphic_item):
        relationship_data.graphic_item.set_attachment_points(QPointF(), QPointF()) # Clear path if tables missing
        return

    t1_graphic = table1_obj.graphic_item
    t2_graphic = table2_obj.graphic_item

    # Get attachment points from tables based on column names
    p1 = t1_graphic.get_attachment_point(t2_graphic, from_column_name=relationship_data.fk_column_name)
    p2 = t2_graphic.get_attachment_point(t1_graphic, to_column_name=relationship_data.pk_column_name)

    # The OrthogonalRelationshipPathItem will use its relationship_data.anchor_points
    # in its _build_path method, which is called by set_attachment_points.
    relationship_data.graphic_item.set_attachment_points(p1, p2)
    # update_tooltip_and_paint also triggers a repaint which calls _build_path via set_attachment_points or update()
    relationship_data.graphic_item.update_tooltip_and_paint()


def update_all_relationships_graphics_impl(window):
    """Updates the graphics for all relationships."""
    for rel_data in window.relationships_data:
        update_custom_orthogonal_path_impl(window, rel_data)


def update_relationship_table_names_impl(window, old_table_name, new_table_name):
    """Updates table names in relationship data when a table is renamed."""
    for rel in window.relationships_data:
        if rel.table1_name == old_table_name:
            rel.table1_name = new_table_name
        if rel.table2_name == old_table_name:
            rel.table2_name = new_table_name
    update_all_relationships_graphics_impl(window)
    window.populate_diagram_explorer()


def update_fk_references_to_pk_impl(window, pk_table_name, old_pk_col_name, new_pk_col_name):
    """Updates FK references when a PK column name changes or is deleted."""
    print(f"REL_OPS: update_fk_references_to_pk for table '{pk_table_name}', old PK: '{old_pk_col_name}', new PK: '{new_pk_col_name}'")

    for table_data in window.tables_data.values(): # Iterate through all tables
        for column in table_data.columns:
            if column.is_fk and column.references_table == pk_table_name and column.references_column == old_pk_col_name:
                if new_pk_col_name: # PK was renamed
                    column.references_column = new_pk_col_name
                    print(f"  Updated FK '{column.name}' in table '{table_data.name}' to reference new PK '{new_pk_col_name}'")
                else: # PK was deleted (new_pk_col_name is None)
                    print(f"  Clearing FK '{column.name}' in table '{table_data.name}' as PK '{old_pk_col_name}' was deleted.")
                    column.is_fk = False
                    column.references_table = None
                    column.references_column = None
                    # column.fk_relationship_type = None #  Decide if type should be cleared
                if table_data.graphic_item:
                    table_data.graphic_item.update() # Redraw table

    # Update relationship data objects as well
    rels_to_remove_if_pk_deleted = []
    for rel in window.relationships_data:
        if rel.table2_name == pk_table_name and rel.pk_column_name == old_pk_col_name:
            if new_pk_col_name: # PK renamed
                rel.pk_column_name = new_pk_col_name
                print(f"  Updated Relationship object: FK {rel.table1_name}.{rel.fk_column_name} now points to PK {rel.table2_name}.{new_pk_col_name}")
            else: # PK deleted
                print(f"  Marking Relationship object for removal: FK {rel.table1_name}.{rel.fk_column_name} to PK {rel.table2_name}.{old_pk_col_name}")
                rels_to_remove_if_pk_deleted.append(rel)

    if not new_pk_col_name and rels_to_remove_if_pk_deleted:
        print(f"  Attempting to remove {len(rels_to_remove_if_pk_deleted)} relationships due to PK deletion.")
        for rel_to_remove in rels_to_remove_if_pk_deleted:
            if rel_to_remove.graphic_item and rel_to_remove.graphic_item.scene():
                window.scene.removeItem(rel_to_remove.graphic_item)
            if rel_to_remove in window.relationships_data:
                window.relationships_data.remove(rel_to_remove)
                print(f"    Removed relationship: {rel_to_remove.table1_name}.{rel_to_remove.fk_column_name} -> {rel_to_remove.table2_name}.{rel_to_remove.pk_column_name}")

    update_all_relationships_graphics_impl(window)
    window.populate_diagram_explorer()


def remove_relationships_for_table_impl(window, table_name, old_columns_of_table=None):
    """
    Removes relationships connected to a given table name.
    If old_columns_of_table is provided (from EditTableCommand), it also checks
    if FKs defined in that old state are no longer valid in the new state and removes their relationships.
    """
    rels_to_remove = []
    # Find relationships where the table is either FK side or PK side
    for rel in window.relationships_data:
        if rel.table1_name == table_name or rel.table2_name == table_name:
            if rel not in rels_to_remove:
                rels_to_remove.append(rel)

    # If old_columns_of_table is provided, it means we are in an EditTable context.
    # We need to check if any FKs that *existed* in old_columns_of_table
    # are no longer present or valid in the *current* state of the table,
    # and if so, remove their corresponding relationships.
    if old_columns_of_table:
        current_table_obj = window.tables_data.get(table_name) # Get current state of the table
        for old_col_data in old_columns_of_table:
            if old_col_data.is_fk and old_col_data.references_table and old_col_data.references_column:
                # Check if this old FK is still valid in the current table's columns
                is_fk_still_valid_in_current_table = False
                if current_table_obj:
                    current_col_version = current_table_obj.get_column_by_name(old_col_data.name)
                    if current_col_version and current_col_version.is_fk and \
                       current_col_version.references_table == old_col_data.references_table and \
                       current_col_version.references_column == old_col_data.references_column and \
                       current_col_version.fk_relationship_type == old_col_data.fk_relationship_type:
                        is_fk_still_valid_in_current_table = True

                if not is_fk_still_valid_in_current_table:
                    # The FK defined in old_columns_of_table is no longer a valid FK.
                    # Find the relationship object that corresponded to this old FK.
                    rel_based_on_old_fk = next((r for r in window.relationships_data if
                                                r.table1_name == table_name and r.fk_column_name == old_col_data.name and
                                                r.table2_name == old_col_data.references_table and
                                                r.pk_column_name == old_col_data.references_column), None)
                    if rel_based_on_old_fk and rel_based_on_old_fk not in rels_to_remove:
                        rels_to_remove.append(rel_based_on_old_fk)
                        print(f"  Marking relationship for removal due to FK change/removal in '{table_name}': {old_col_data.name} -> {old_col_data.references_table}.{old_col_data.references_column}")

    if rels_to_remove:
        for rel_to_remove in rels_to_remove:
            if rel_to_remove.graphic_item and rel_to_remove.graphic_item.scene():
                window.scene.removeItem(rel_to_remove.graphic_item)
            if rel_to_remove in window.relationships_data:
                window.relationships_data.remove(rel_to_remove)
                print(f"Relationship removed: {rel_to_remove.table1_name}.{rel_to_remove.fk_column_name} -> {rel_to_remove.table2_name}.{rel_to_remove.pk_column_name}")

        update_all_relationships_graphics_impl(window)
        window.populate_diagram_explorer()


def edit_relationship_properties_impl(window, relationship_data):
    """Opens a dialog to edit relationship properties (like type)."""
    if not relationship_data:
        return

    original_type = relationship_data.relationship_type
    # Anchor points are not edited by this dialog currently, but could be stored if dialog was extended
    original_anchor_points = [QPointF(p) for p in relationship_data.anchor_points]


    dialog = RelationshipDialog(relationship_data, window) # Pass main window for theme access
    if dialog.exec():
        new_type = relationship_data.relationship_type # Dialog modifies relationship_data directly

        changed = False
        if new_type != original_type:
            changed = True
            print(f"Relationship properties updated for: {relationship_data.table1_name}.{relationship_data.fk_column_name}")

        # If anchor points were editable in dialog, check for changes here:
        # if relationship_data.anchor_points != original_anchor_points:
        #     changed = True

        if changed:
            # Update FK column's relationship type if it changed
            fk_table = window.tables_data.get(relationship_data.table1_name)
            if fk_table:
                fk_col = fk_table.get_column_by_name(relationship_data.fk_column_name)
                if fk_col and fk_col.is_fk:
                    if fk_col.fk_relationship_type != new_type:
                        fk_col.fk_relationship_type = new_type
                        if fk_table.graphic_item: fk_table.graphic_item.update()

            update_custom_orthogonal_path_impl(window, relationship_data) # Redraw with new type/anchors
            window.populate_diagram_explorer()
            # TODO: Implement EditRelationshipPropertiesCommand
            window.undo_stack.setClean() # Mark as dirty for now
            window.update_window_title()
    else: # Dialog was cancelled, revert any direct changes made by dialog (if any)
        relationship_data.relationship_type = original_type
        relationship_data.anchor_points = original_anchor_points # Restore anchors if dialog could change them
        # If dialog only returns values, this else block might not be needed.
