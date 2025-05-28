# main_window_relationship_operations.py
# Handles operations related to relationships.

import math
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QPen, QColor
from data_models import Relationship
import copy # For deepcopying column lists
from gui_items import OrthogonalRelationshipPathItem 
from commands import CreateRelationshipCommand, DeleteRelationshipCommand, SetRelationshipVerticalSegmentXCommand # Added SetRelationshipVerticalSegmentXCommand
from dialogs import RelationshipDialog
import constants
from utils import snap_to_grid


def finalize_relationship_drawing_impl(window, source_table_data, source_column_data, dest_table_data, dest_column_data):
    """Finalizes drawing a relationship between two columns."""
    fk_table, fk_col_obj, pk_table, pk_col_obj = None, None, None, None

    if source_column_data.is_pk and not dest_column_data.is_pk:
        pk_table, pk_col_obj = source_table_data, source_column_data
        fk_table, fk_col_obj = dest_table_data, dest_column_data
    elif not source_column_data.is_pk and dest_column_data.is_pk:
        pk_table, pk_col_obj = dest_table_data, dest_column_data
        fk_table, fk_col_obj = source_table_data, source_column_data
    else:
        # Invalid connection: either PK-PK or nonPK-nonPK, or one/both are FKs not suitable.
        msg = "Cannot create relationship: One column must be a Primary Key (PK) and the other a non-PK (which will become the Foreign Key)." # Default

        if source_column_data.is_pk and dest_column_data.is_pk:
            msg = "Cannot connect two Primary Key columns directly. Choose one PK and one non-PK column."
        elif not source_column_data.is_pk and not dest_column_data.is_pk and \
             not source_column_data.is_fk and not dest_column_data.is_fk:
            # This specifically targets two "clean" non-PK, non-FK columns.
            msg = "Cannot connect two non-Primary Key, non-Foreign Key columns. One column must be a Primary Key."
        # For other invalid cases (e.g., FK-FK, or FK to non-PK/non-FK where the non-PK/non-FK isn't becoming the PK),
        # the default message is generally appropriate.
        QMessageBox.warning(window, "Invalid Connection", msg)
        window.reset_drawing_mode()
        return

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

    # Data type validation
    if fk_col_obj.data_type != pk_col_obj.data_type:
        msg_box = QMessageBox(window)
        msg_box.setIcon(QMessageBox.Icon.Question)
        msg_box.setTextFormat(Qt.TextFormat.RichText) # Ensure HTML is rendered
        msg_box.setWindowTitle("Data Type Mismatch")
        msg_box.setText(f"The data types of the selected columns do not match:<br><br>"
                        f"<b>{fk_table.name}.{fk_col_obj.name}</b><br>&nbsp;&nbsp;&nbsp;&nbsp;Type: <b>{fk_col_obj.data_type}</b><br><br>"
                        f"<b>{pk_table.name}.{pk_col_obj.name}</b><br>&nbsp;&nbsp;&nbsp;&nbsp;Type: <b>{pk_col_obj.data_type}</b><br><br>"
                        "Do you want to align the data types?")

        btn_change_fk = msg_box.addButton(f"Modify to\n{pk_col_obj.data_type}", QMessageBox.ButtonRole.YesRole) # To match PK type
        btn_change_pk = msg_box.addButton(f"Modify to\n{fk_col_obj.data_type}", QMessageBox.ButtonRole.YesRole) # To match FK type
        btn_proceed = msg_box.addButton("Don't Modify", QMessageBox.ButtonRole.NoRole)
        btn_cancel = msg_box.addButton(QMessageBox.StandardButton.Cancel)

        msg_box.exec()
        clicked_button = msg_box.clickedButton()

        type_changed = False
        if clicked_button == btn_change_fk:
            window.undo_stack.beginMacro("Change FK Type and Create Relationship") # Start macro
            from commands import EditTableCommand # Local import
            old_props = {"name": fk_table.name, "body_color_hex": fk_table.body_color.name(), "header_color_hex": fk_table.header_color.name(), "columns": copy.deepcopy(fk_table.columns)}
            new_columns_fk = copy.deepcopy(fk_table.columns)
            for col in new_columns_fk:
                if col.name == fk_col_obj.name:
                    col.data_type = pk_col_obj.data_type
                    break
            new_props = {"name": fk_table.name, "body_color_hex": fk_table.body_color.name(), "header_color_hex": fk_table.header_color.name(), "columns": new_columns_fk}
            cmd_edit_fk = EditTableCommand(window, fk_table, old_props, new_props, description=f"Change {fk_col_obj.name} type")
            window.undo_stack.push(cmd_edit_fk)
            # fk_col_obj.data_type is now updated via the command's redo
            type_changed = True
        elif clicked_button == btn_change_pk:
            window.undo_stack.beginMacro("Change PK Type and Create Relationship") # Start macro
            from commands import EditTableCommand # Local import
            old_props = {"name": pk_table.name, "body_color_hex": pk_table.body_color.name(), "header_color_hex": pk_table.header_color.name(), "columns": copy.deepcopy(pk_table.columns)}
            new_columns_pk = copy.deepcopy(pk_table.columns)
            for col in new_columns_pk:
                if col.name == pk_col_obj.name:
                    col.data_type = fk_col_obj.data_type
                    break
            new_props = {"name": pk_table.name, "body_color_hex": pk_table.body_color.name(), "header_color_hex": pk_table.header_color.name(), "columns": new_columns_pk}
            cmd_edit_pk = EditTableCommand(window, pk_table, old_props, new_props, description=f"Change {pk_col_obj.name} type")
            window.undo_stack.push(cmd_edit_pk)
            # pk_col_obj.data_type is now updated via the command's redo
            type_changed = True
        elif clicked_button == btn_proceed:
            pass # Proceed without changing types
        else: # Cancel or closed dialog
            window.reset_drawing_mode()
            return
        
        # After a type change command, the original fk_col_obj/pk_col_obj references might be stale
        # because EditTableCommand replaces the columns list with a deep copy.
        # Re-fetch them if a change occurred to ensure we have the live objects.
        if type_changed:
            fk_col_obj = fk_table.get_column_by_name(fk_col_obj.name)
            pk_col_obj = pk_table.get_column_by_name(pk_col_obj.name)
            if not fk_col_obj or not pk_col_obj: # Should not happen if names didn't change
                QMessageBox.critical(window, "Error", "Column not found after type change. Aborting relationship.")
                window.reset_drawing_mode()
                return

    default_rel_type = "N:1" 
    # New relationships are created with default (auto-calculated) vertical segment X
    command = CreateRelationshipCommand(window, fk_table, pk_table, fk_col_obj.name, pk_col_obj.name, default_rel_type, vertical_segment_x_override=None)
    window.undo_stack.push(command)

    if type_changed: # If a macro was started
        window.undo_stack.endMacro() # End macro
    window.reset_drawing_mode()


def create_relationship_impl(window, fk_table_data, pk_table_data, fk_col_name, pk_col_name, rel_type,
                             vertical_segment_x_override=None, # Added for CSV import / command restoration
                             from_undo_redo=False):
    """
    Creates a relationship data object and its graphical representation.
    'vertical_segment_x_override' allows setting a specific X for the vertical segment.
    """
    existing_rel = next((r for r in window.relationships_data if
                         r.table1_name == fk_table_data.name and r.fk_column_name == fk_col_name and
                         r.table2_name == pk_table_data.name and r.pk_column_name == pk_col_name), None)

    fk_col_in_table = fk_table_data.get_column_by_name(fk_col_name)
    if not fk_col_in_table:
        print(f"Error creating relationship: FK column '{fk_col_name}' not found in table '{fk_table_data.name}'.")
        return None

    if existing_rel:
        # print(f"Relationship from {fk_table_data.name}.{fk_col_name} to {pk_table_data.name}.{pk_col_name} already exists. Updating properties.")
        changed = False
        if existing_rel.relationship_type != rel_type:
            existing_rel.relationship_type = rel_type
            changed = True
        
        if existing_rel.vertical_segment_x_override != vertical_segment_x_override:
            existing_rel.vertical_segment_x_override = vertical_segment_x_override
            changed = True

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
            existing_rel.graphic_item.update_tooltip_and_paint() 
            update_relationship_graphic_path_impl(window, existing_rel) 
        return existing_rel

    relationship = Relationship(fk_table_data.name, pk_table_data.name, fk_col_name, pk_col_name, rel_type)
    relationship.vertical_segment_x_override = vertical_segment_x_override # Set if provided

    window.relationships_data.append(relationship)

    line_item = OrthogonalRelationshipPathItem(relationship) 
    default_line_color = QColor(70,70,110) 
    line_color_from_theme = window.current_theme_settings.get("relationship_line_color", default_line_color)

    if isinstance(line_color_from_theme, str):
        line_color_to_use = QColor(line_color_from_theme)
    elif isinstance(line_color_from_theme, QColor):
        line_color_to_use = line_color_from_theme
    else:
        line_color_to_use = default_line_color

    line_item.setPen(QPen(line_color_to_use, 1.8))
    window.scene.addItem(line_item)
    relationship.graphic_item = line_item 

    update_relationship_graphic_path_impl(window, relationship) 

    fk_col_in_table.is_fk = True
    fk_col_in_table.references_table = pk_table_data.name
    fk_col_in_table.references_column = pk_col_name
    fk_col_in_table.fk_relationship_type = rel_type 
    if fk_table_data.graphic_item:
        fk_table_data.graphic_item.update() 

    if not from_undo_redo and not window.undo_stack.isActive(): 
        window.populate_diagram_explorer()

    return relationship


def update_relationship_graphic_path_impl(window, relationship_data): # Renamed from update_custom_orthogonal_path_impl
    """Updates the path of a simplified orthogonal relationship line."""
    if not relationship_data.graphic_item or not isinstance(relationship_data.graphic_item, OrthogonalRelationshipPathItem):
        return

    table1_obj = window.tables_data.get(relationship_data.table1_name) 
    table2_obj = window.tables_data.get(relationship_data.table2_name) 

    if not (table1_obj and table1_obj.graphic_item and table2_obj and table2_obj.graphic_item):
        relationship_data.graphic_item.set_attachment_points(QPointF(), QPointF()) 
        return

    t1_graphic = table1_obj.graphic_item
    t2_graphic = table2_obj.graphic_item

    # Step 1: Get initial attachment points (without hint, based on relative table positions)
    p1_initial = t1_graphic.get_attachment_point(t2_graphic, from_column_name=relationship_data.fk_column_name)
    p2_initial = t2_graphic.get_attachment_point(t1_graphic, to_column_name=relationship_data.pk_column_name)

    # Step 2: Calculate intermediate_x_scene
    intermediate_x_scene = 0.0
    if relationship_data.vertical_segment_x_override is not None:
        intermediate_x_scene = relationship_data.vertical_segment_x_override
    else:
        min_h_seg = constants.MIN_HORIZONTAL_SEGMENT
        # Determine default exit direction based on table centers if tables are horizontally very close
        s_exits_right_default = t1_graphic.sceneBoundingRect().center().x() < t2_graphic.sceneBoundingRect().center().x()

        calc_inter_x = 0.0
        if abs(p1_initial.x() - p2_initial.x()) < min_h_seg * 1.5:
            calc_inter_x = p1_initial.x() + (min_h_seg if s_exits_right_default else -min_h_seg)
        else:
            # Use table centers for "far apart" case to make vertical segment placement more neutral
            calc_inter_x = (t1_graphic.sceneBoundingRect().center().x() + t2_graphic.sceneBoundingRect().center().x()) / 2.0
        intermediate_x_scene = snap_to_grid(calc_inter_x, constants.GRID_SIZE / 2)

    # Step 3: Get final attachment points using the calculated intermediate_x_scene as a hint
    p1_final = t1_graphic.get_attachment_point(t2_graphic, 
                                               from_column_name=relationship_data.fk_column_name, 
                                               hint_intermediate_x=intermediate_x_scene)
    p2_final = t2_graphic.get_attachment_point(t1_graphic, 
                                               to_column_name=relationship_data.pk_column_name, 
                                               hint_intermediate_x=intermediate_x_scene)

    relationship_data.graphic_item.set_attachment_points(p1_final, p2_final)
    relationship_data.graphic_item.update_tooltip_and_paint() 


def update_all_relationships_graphics_impl(window):
    """Updates the graphics for all relationships."""
    for rel_data in window.relationships_data:
        update_relationship_graphic_path_impl(window, rel_data)


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
    # print(f"REL_OPS: update_fk_references_to_pk for table '{pk_table_name}', old PK: '{old_pk_col_name}', new PK: '{new_pk_col_name}'")

    for table_data in window.tables_data.values(): 
        for column in table_data.columns:
            if column.is_fk and column.references_table == pk_table_name and column.references_column == old_pk_col_name:
                if new_pk_col_name: 
                    column.references_column = new_pk_col_name
                    # print(f"  Updated FK '{column.name}' in table '{table_data.name}' to reference new PK '{new_pk_col_name}'")
                else: 
                    # print(f"  Clearing FK '{column.name}' in table '{table_data.name}' as PK '{old_pk_col_name}' was deleted.")
                    column.is_fk = False
                    column.references_table = None
                    column.references_column = None
                if table_data.graphic_item:
                    table_data.graphic_item.update() 

    rels_to_remove_if_pk_deleted = []
    for rel in window.relationships_data:
        if rel.table2_name == pk_table_name and rel.pk_column_name == old_pk_col_name:
            if new_pk_col_name: 
                rel.pk_column_name = new_pk_col_name
                # print(f"  Updated Relationship object: FK {rel.table1_name}.{rel.fk_column_name} now points to PK {rel.table2_name}.{new_pk_col_name}")
            else: 
                # print(f"  Marking Relationship object for removal: FK {rel.table1_name}.{rel.fk_column_name} to PK {rel.table2_name}.{old_pk_col_name}")
                rels_to_remove_if_pk_deleted.append(rel)

    if not new_pk_col_name and rels_to_remove_if_pk_deleted:
        # print(f"  Attempting to remove {len(rels_to_remove_if_pk_deleted)} relationships due to PK deletion.")
        for rel_to_remove in rels_to_remove_if_pk_deleted:
            if rel_to_remove.graphic_item and rel_to_remove.graphic_item.scene():
                window.scene.removeItem(rel_to_remove.graphic_item)
            if rel_to_remove in window.relationships_data:
                window.relationships_data.remove(rel_to_remove)
                # print(f"    Removed relationship: {rel_to_remove.table1_name}.{rel_to_remove.fk_column_name} -> {rel_to_remove.table2_name}.{rel_to_remove.pk_column_name}")

    update_all_relationships_graphics_impl(window)
    window.populate_diagram_explorer()


def remove_relationships_for_table_impl(window, table_name, old_columns_of_table=None):
    """
    Removes relationships that were defined by FKs in 'old_columns_of_table' of 'table_name'
    if those FK definitions are no longer valid in the table's current state.
    This is typically called during table edits where columns might change.
    It does NOT unconditionally remove all relationships connected to table_name.
    """
    rels_to_remove = []

    if old_columns_of_table:
        # 'table_name' here is the name of the table *after* any potential rename in the edit command.
        # 'old_columns_of_table' are the columns as they were *before* the edit.
        current_table_obj = window.tables_data.get(table_name)
        
        for old_col_data in old_columns_of_table:
            # We are interested in FKs that *were* in old_columns_of_table and originated from the table being edited.
            if old_col_data.is_fk and old_col_data.references_table and old_col_data.references_column:
                is_fk_still_valid_in_current_table = False
                if current_table_obj:
                    current_col_version = current_table_obj.get_column_by_name(old_col_data.name)
                    if current_col_version and current_col_version.is_fk and \
                       current_col_version.references_table == old_col_data.references_table and \
                       current_col_version.references_column == old_col_data.references_column and \
                       current_col_version.fk_relationship_type == old_col_data.fk_relationship_type:
                        is_fk_still_valid_in_current_table = True

                if not is_fk_still_valid_in_current_table:
                    # This FK from the old column set is no longer valid (e.g., column removed,
                    # no longer an FK, or points to a different target in the new column set).
                    # Find the relationship object that corresponded to this specific old FK definition.
                    rel_based_on_old_fk = next((r for r in window.relationships_data if
                                                r.table1_name == table_name and # Relationship's FK table must match current table name
                                                r.fk_column_name == old_col_data.name and # FK column name matches
                                                r.table2_name == old_col_data.references_table and # Target table matches
                                                r.pk_column_name == old_col_data.references_column), None) # Target column matches
                    if rel_based_on_old_fk and rel_based_on_old_fk not in rels_to_remove:
                        rels_to_remove.append(rel_based_on_old_fk)
                        # print(f"  Marking relationship for removal due to FK change/removal in '{table_name}': {old_col_data.name} -> {old_col_data.references_table}.{old_col_data.references_column}")

    if rels_to_remove:
        for rel_to_remove in rels_to_remove:
            if rel_to_remove.graphic_item and rel_to_remove.graphic_item.scene():
                window.scene.removeItem(rel_to_remove.graphic_item)
            if rel_to_remove in window.relationships_data:
                window.relationships_data.remove(rel_to_remove)
                # print(f"Relationship removed: {rel_to_remove.table1_name}.{rel_to_remove.fk_column_name} -> {rel_to_remove.table2_name}.{rel_to_remove.pk_column_name}")

        update_all_relationships_graphics_impl(window)
        window.populate_diagram_explorer()


def edit_relationship_properties_impl(window, relationship_data):
    """Opens a dialog to edit relationship properties (like type)."""
    if not relationship_data:
        return

    original_type = relationship_data.relationship_type
    # Store original vertical_segment_x_override for potential revert if dialog is cancelled
    original_vertical_x = relationship_data.vertical_segment_x_override


    dialog = RelationshipDialog(relationship_data, window) 
    if dialog.exec():
        new_type = relationship_data.relationship_type # Dialog modifies relationship_data directly

        changed = False
        if new_type != original_type:
            changed = True
            # print(f"Relationship properties updated for: {relationship_data.table1_name}.{relationship_data.fk_column_name}")

        # vertical_segment_x_override is not edited by this dialog currently,
        # but if it were, we would check for changes here.

        if changed:
            fk_table = window.tables_data.get(relationship_data.table1_name)
            if fk_table:
                fk_col = fk_table.get_column_by_name(relationship_data.fk_column_name)
                if fk_col and fk_col.is_fk:
                    if fk_col.fk_relationship_type != new_type:
                        fk_col.fk_relationship_type = new_type
                        if fk_table.graphic_item: fk_table.graphic_item.update()

            update_relationship_graphic_path_impl(window, relationship_data) 
            window.populate_diagram_explorer()
            # TODO: Implement EditRelationshipPropertiesCommand for undo/redo
            window.undo_stack.setClean(False) 
            window.update_window_title()
    else: 
        relationship_data.relationship_type = original_type
        # Restore vertical_segment_x_override if it was part of the dialog and changed
        # relationship_data.vertical_segment_x_override = original_vertical_x
        # (Currently not part of dialog, so no change to revert here for it)
