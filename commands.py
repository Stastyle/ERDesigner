# commands.py
# This file will contain QUndoCommand subclasses for implementing undo/redo functionality.

from PyQt6.QtGui import QUndoCommand, QColor
from PyQt6.QtCore import QPointF, QRectF
from data_models import Table, Column, Relationship
# from gui_items import TableGraphicItem, OrthogonalRelationshipPathItem, GroupGraphicItem # Keep as local imports
import copy
import constants
from utils import snap_to_grid # Import constants for GRID_SIZE

# print("commands.py loaded") # DEBUG

class AddTableCommand(QUndoCommand):
    def __init__(self, main_window, table_data, description="Add Table"):
        super().__init__(description)
        self.main_window = main_window
        self.table_data_copy = copy.deepcopy(table_data)
        self.table_name = table_data.name
        self.table_graphic_item_instance = table_data.graphic_item if table_data.graphic_item else None # Store instance if it exists

    def redo(self):
        from gui_items import TableGraphicItem 
        self.main_window.tables_data[self.table_name] = self.table_data_copy

        # If graphic_item doesn't exist or isn't in a scene, create/add it.
        if not self.table_data_copy.graphic_item or not self.table_data_copy.graphic_item.scene():
            # Try to reuse the stored instance if it's not in a scene
            if self.table_graphic_item_instance and not self.table_graphic_item_instance.scene():
                self.table_data_copy.graphic_item = self.table_graphic_item_instance
            else:
                # Create a new graphic item if needed
                self.table_graphic_item_instance = TableGraphicItem(self.table_data_copy) 
                self.table_data_copy.graphic_item = self.table_graphic_item_instance
        
        self.table_data_copy.graphic_item.setPos(self.table_data_copy.x, self.table_data_copy.y)
        if not self.table_data_copy.graphic_item.scene(): # Ensure it's added to the scene
            self.main_window.scene.addItem(self.table_data_copy.graphic_item)

        if self.table_data_copy.graphic_item:
            self.table_data_copy.graphic_item.update()

        self.main_window.update_all_relationships_graphics()
        self.main_window.update_window_title()
        self.main_window.populate_diagram_explorer()


    def undo(self):
        if not self.table_graphic_item_instance and self.table_name in self.main_window.tables_data:
            live_table_data = self.main_window.tables_data[self.table_name]
            if live_table_data.graphic_item:
                self.table_graphic_item_instance = live_table_data.graphic_item # Store for redo

        if self.table_name in self.main_window.tables_data:
            table_to_remove_data = self.main_window.tables_data.pop(self.table_name)
            # Use the stored graphic item instance for removal
            if self.table_graphic_item_instance:
                if self.table_graphic_item_instance.parentItem(): 
                    self.table_graphic_item_instance.setParentItem(None)
                if self.table_graphic_item_instance.scene():
                    self.main_window.scene.removeItem(self.table_graphic_item_instance)
            
            if table_to_remove_data:
                 # Nullify graphic_item on the data model that was live
                 table_to_remove_data.graphic_item = None
            if self.table_data_copy is not table_to_remove_data:
                 # Also nullify on our copy if it's a different instance
                 self.table_data_copy.graphic_item = None

        self.main_window.update_all_relationships_graphics()
        self.main_window.update_window_title()
        self.main_window.populate_diagram_explorer()

class DeleteTableCommand(QUndoCommand):
    def __init__(self, main_window, table_data_to_delete, description="Delete Table"):
        super().__init__(description)
        self.main_window = main_window
        self.table_graphic_item_instance = table_data_to_delete.graphic_item
        self.table_data_copy = copy.deepcopy(table_data_to_delete)
        self.table_name = table_data_to_delete.name
        self.deleted_relationships_with_graphics = []
        self.affected_fk_columns_original_states = [] # To restore FKs that pointed to this table


        for rel in list(self.main_window.relationships_data):
            if rel.table1_name == self.table_name or rel.table2_name == self.table_name:
                rel_graphic_instance = rel.graphic_item
                rel_data_copy = copy.deepcopy(rel)
                self.deleted_relationships_with_graphics.append((rel_data_copy, rel_graphic_instance))
                if rel.table2_name == self.table_name:
                    other_table_name = rel.table1_name
                    fk_col_name_in_other = rel.fk_column_name
                    other_table_obj = self.main_window.tables_data.get(other_table_name)
                    if other_table_obj:
                        fk_col_obj = other_table_obj.get_column_by_name(fk_col_name_in_other)
                        if fk_col_obj and fk_col_obj.is_fk and \
                           fk_col_obj.references_table == self.table_name and \
                           fk_col_obj.references_column == rel.pk_column_name:
                            self.affected_fk_columns_original_states.append({
                                "table_name": other_table_name, "column_name": fk_col_name_in_other,
                                "is_fk": True, "references_table": self.table_name,
                                "references_column": rel.pk_column_name,
                                "fk_relationship_type": fk_col_obj.fk_relationship_type
                            })

    def redo(self):
        for rel_data_copy, rel_graphic_instance in self.deleted_relationships_with_graphics:
            if rel_graphic_instance and rel_graphic_instance.scene():
                self.main_window.scene.removeItem(rel_graphic_instance)

            live_rel_to_remove = next((r_live for r_live in self.main_window.relationships_data
                                       if r_live.table1_name == rel_data_copy.table1_name and
                                          r_live.fk_column_name == rel_data_copy.fk_column_name and
                                          r_live.table2_name == rel_data_copy.table2_name and
                                          r_live.pk_column_name == rel_data_copy.pk_column_name), None)
            if live_rel_to_remove:
                self.main_window.relationships_data.remove(live_rel_to_remove)

            if rel_data_copy.table2_name == self.table_name: 
                other_table_obj = self.main_window.tables_data.get(rel_data_copy.table1_name) 
                if other_table_obj:
                    fk_col = other_table_obj.get_column_by_name(rel_data_copy.fk_column_name)
                    if fk_col and fk_col.is_fk and fk_col.references_table == self.table_name:
                        is_still_fk_by_other_rel = any(
                            r.table1_name == other_table_obj.name and r.fk_column_name == fk_col.name
                            for r in self.main_window.relationships_data
                        )
                        if not is_still_fk_by_other_rel:
                            fk_col.is_fk = False
                            fk_col.references_table = None
                            fk_col.references_column = None
                        if other_table_obj.graphic_item: other_table_obj.graphic_item.update()

        if self.table_name in self.main_window.tables_data:
            if self.table_graphic_item_instance:
                if self.table_graphic_item_instance.parentItem(): 
                    self.table_graphic_item_instance.setParentItem(None)
                if self.table_graphic_item_instance.scene():
                    self.main_window.scene.removeItem(self.table_graphic_item_instance)
            del self.main_window.tables_data[self.table_name]

        self.main_window.update_window_title()
        self.main_window.populate_diagram_explorer()
        self.main_window.scene.update()

    def undo(self):
        if self.table_name not in self.main_window.tables_data:
            self.main_window.tables_data[self.table_name] = self.table_data_copy
            if self.table_graphic_item_instance: 
                self.table_data_copy.graphic_item = self.table_graphic_item_instance
                if self.table_graphic_item_instance.parentItem() is not None: # Should be None after redo
                    self.table_graphic_item_instance.setParentItem(None)
                self.table_graphic_item_instance.setPos(self.table_data_copy.x, self.table_data_copy.y)
                if not self.table_graphic_item_instance.scene():
                    self.main_window.scene.addItem(self.table_graphic_item_instance)
                self.table_graphic_item_instance.update()

        for fk_state in self.affected_fk_columns_original_states:
            other_table_obj = self.main_window.tables_data.get(fk_state["table_name"])
            if other_table_obj:
                fk_col_obj = other_table_obj.get_column_by_name(fk_state["column_name"])
                if fk_col_obj:
                    fk_col_obj.is_fk = fk_state["is_fk"]
                    fk_col_obj.references_table = fk_state["references_table"]
                    fk_col_obj.references_column = fk_state["references_column"]
                    fk_col_obj.fk_relationship_type = fk_state["fk_relationship_type"]
                    if other_table_obj.graphic_item: other_table_obj.graphic_item.update()

        for rel_data_copy, rel_graphic_instance in self.deleted_relationships_with_graphics:
            is_duplicate_content = any(
                r.table1_name == rel_data_copy.table1_name and r.fk_column_name == rel_data_copy.fk_column_name and
                r.table2_name == rel_data_copy.table2_name and r.pk_column_name == rel_data_copy.pk_column_name
                for r in self.main_window.relationships_data
            )
            if not is_duplicate_content:
                self.main_window.relationships_data.append(rel_data_copy)

            if rel_graphic_instance:
                rel_data_copy.graphic_item = rel_graphic_instance
                if not rel_graphic_instance.scene():
                    self.main_window.scene.addItem(rel_graphic_instance)

        self.main_window.update_all_relationships_graphics()
        self.main_window.update_window_title()
        self.main_window.populate_diagram_explorer()
        self.main_window.scene.update()


class EditTableCommand(QUndoCommand):
    def __init__(self, main_window, table_data_object, old_properties, new_properties, description="Edit Table"):
        super().__init__(description)
        self.main_window = main_window
        self.table_data_object = table_data_object 

        self.old_name = old_properties["name"]
        self.new_name = new_properties["name"]
        self.old_body_color_hex = old_properties["body_color_hex"]
        self.new_body_color_hex = new_properties["body_color_hex"]
        self.old_header_color_hex = old_properties["header_color_hex"]
        self.new_header_color_hex = new_properties["header_color_hex"]
        
        self.old_columns_data = copy.deepcopy(old_properties["columns"])
        self.new_columns_data = copy.deepcopy(new_properties["columns"])
    def redo(self):
        self._apply_properties(self.new_name, self.new_body_color_hex, self.new_header_color_hex, self.new_columns_data)

    def undo(self):
        self._apply_properties(self.old_name, self.old_body_color_hex, self.old_header_color_hex, self.old_columns_data)

    def _apply_properties(self, name_to_apply, body_color_hex_to_apply, header_color_hex_to_apply, columns_to_apply_list):
        original_name_of_live_object = self.table_data_object.name 
        name_changed = original_name_of_live_object != name_to_apply

        if name_changed:
            if name_to_apply in self.main_window.tables_data and self.main_window.tables_data[name_to_apply] is not self.table_data_object:
                # This case should ideally be prevented by dialog validation
                print(f"Error: Target name '{name_to_apply}' already exists and is a different object.")
                return False 
            
            # Update the tables_data dictionary key
            if original_name_of_live_object in self.main_window.tables_data:
                del self.main_window.tables_data[original_name_of_live_object]
            self.main_window.tables_data[name_to_apply] = self.table_data_object
            
            # Update the table object's name
            self.table_data_object.name = name_to_apply 
            
            # Update relationships and FK references in other tables
            self.main_window.update_relationship_table_names(original_name_of_live_object, name_to_apply)
            self.main_window.update_fk_references_to_table(original_name_of_live_object, name_to_apply)

        # Apply color changes
        self.table_data_object.body_color = QColor(body_color_hex_to_apply)
        self.table_data_object.header_color = QColor(header_color_hex_to_apply)

        # Determine which set of columns represents the state *before* these properties are applied
        # For redo, old_columns_data is "before". For undo, new_columns_data is "before".
        columns_state_before_this_apply = self.old_columns_data if name_to_apply == self.new_name else self.new_columns_data

        # Handle PK changes: if a PK is removed or renamed, update FKs in other tables that reference it.
        old_pk_map = {col.name: col for col in columns_state_before_this_apply if col.is_pk}
        new_pk_map = {col.name: col for col in columns_to_apply_list if col.is_pk}

        for old_pk_name, old_pk_col_obj in old_pk_map.items():
            if old_pk_name not in new_pk_map or not new_pk_map[old_pk_name].is_pk : # PK removed or no longer PK
                # Check if it was renamed to another PK
                is_renamed_and_still_pk = False
                if len(old_pk_map) == 1 and len(new_pk_map) == 1: 
                    new_pk_name_check = list(new_pk_map.keys())[0]
                    if old_pk_name != new_pk_name_check : # Renamed
                        is_renamed_and_still_pk = True 
                
                if not is_renamed_and_still_pk: # Truly removed or changed to non-PK
                     self.main_window.update_fk_references_to_pk(name_to_apply, old_pk_name, None) # Pass current table name

        for new_pk_name, new_pk_col_obj in new_pk_map.items():
            original_old_pk_name_for_this_new_pk = None
            if new_pk_name not in old_pk_map: # New PK or renamed PK
                if len(old_pk_map) == 1 and len(new_pk_map) == 1: # Potentially renamed
                     original_old_pk_name_for_this_new_pk = list(old_pk_map.keys())[0]
            
            if original_old_pk_name_for_this_new_pk and original_old_pk_name_for_this_new_pk != new_pk_name:
                # This PK was renamed from original_old_pk_name_for_this_new_pk
                self.main_window.update_fk_references_to_pk(name_to_apply, original_old_pk_name_for_this_new_pk, new_pk_name)
        
        # Remove relationships that are no longer valid due to FK changes *within this table*
        # The modified remove_relationships_for_table will only remove relationships if FKs in
        # columns_state_before_this_apply are no longer valid in columns_to_apply_list.
        # If only colors changed, columns_state_before_this_apply will be structurally identical
        # to columns_to_apply_list, and no relationships will be removed by this call.
        self.main_window.remove_relationships_for_table(name_to_apply, columns_state_before_this_apply)

        # Apply the new column structure to the table data object
        self.table_data_object.columns = copy.deepcopy(columns_to_apply_list) 

        # Recreate/update relationships based on current FKs in the table
        for col in self.table_data_object.columns:
            if col.is_fk and col.references_table and col.references_column:
                target_table_obj = self.main_window.tables_data.get(col.references_table)
                if target_table_obj:
                    target_pk_col_obj = target_table_obj.get_column_by_name(col.references_column)
                    if target_pk_col_obj and target_pk_col_obj.is_pk: 
                        # Try to find if this relationship (or a very similar one) existed before
                        # to preserve its vertical_segment_x_override.
                        # Search in main_window.relationships_data as it reflects the state *after*
                        # potential removals by remove_relationships_for_table.
                        existing_rel_data = next((r for r in self.main_window.relationships_data if
                                                  r.table1_name == self.table_data_object.name and r.fk_column_name == col.name and
                                                  r.table2_name == target_table_obj.name and r.pk_column_name == col.references_column), None)
                        
                        override_x = existing_rel_data.vertical_segment_x_override if existing_rel_data else None

                        # create_relationship will update the existing one if found, or create a new one.
                        # It handles preserving the vertical_segment_x_override if 'override_x' is passed.
                        self.main_window.create_relationship(
                            self.table_data_object, target_table_obj, 
                            col.name, col.references_column,           
                            col.fk_relationship_type,                  
                            vertical_segment_x_override=override_x, 
                            from_undo_redo=True                        
                        )
                    else: # Target PK column not found or not PK, invalidate this FK
                        col.is_fk = False; col.references_table = None; col.references_column = None
                else: # Target table not found, invalidate this FK
                    col.is_fk = False; col.references_table = None; col.references_column = None
        
        # Update the table's graphical representation
        if self.table_data_object.graphic_item:
            self.table_data_object.graphic_item.prepareGeometryChange()
            self.table_data_object.graphic_item._calculate_height() # Recalculate height based on new columns
            self.table_data_object.graphic_item.update() # Repaint

        # Update all relationship graphics (paths might change due to table resize/column changes)
        self.main_window.update_all_relationships_graphics() 
        self.main_window.update_window_title()
        self.main_window.populate_diagram_explorer()
        return True


# Removed AddOrthogonalBendCommand, MoveOrthogonalBendCommand, DeleteOrthogonalBendCommand, MoveCentralVerticalSegmentCommand

class SetRelationshipVerticalSegmentXCommand(QUndoCommand):
    def __init__(self, main_window, relationship_data_ref, old_x_override, new_x_override, description="Set Vertical Segment X"):
        super().__init__(description)
        self.main_window = main_window
        self.relationship_data_ref = relationship_data_ref # Direct reference
        self.old_x_override = old_x_override # Can be float or None
        self.new_x_override = new_x_override # Can be float or None

    def _apply_override(self, x_override_to_apply):
        self.relationship_data_ref.vertical_segment_x_override = x_override_to_apply
        if self.relationship_data_ref.graphic_item:
            # This will internally call set_attachment_points and _build_path after recalculating points
            self.main_window.update_relationship_graphic_path(self.relationship_data_ref)
            # The update_relationship_graphic_path calls graphic_item.update_tooltip_and_paint() which includes an update()
        self.main_window.update_window_title()

    def redo(self):
        self._apply_override(self.new_x_override)

    def undo(self):
        self._apply_override(self.old_x_override)


class CreateRelationshipCommand(QUndoCommand):
    def __init__(self, main_window, fk_table_data, pk_table_data, fk_col_name, pk_col_name, rel_type, 
                 vertical_segment_x_override=None, # Added for consistency, though usually None on creation
                 description="Create Relationship"):
        super().__init__(description)
        self.main_window = main_window
        self.fk_table_name = fk_table_data.name
        self.pk_table_name = pk_table_data.name
        self.fk_col_name = fk_col_name
        self.pk_col_name = pk_col_name
        self.rel_type = rel_type
        self.vertical_segment_x_override = vertical_segment_x_override # Store this

        fk_table_obj = self.main_window.tables_data.get(self.fk_table_name)
        fk_col_obj = fk_table_obj.get_column_by_name(self.fk_col_name) if fk_table_obj else None
        self.original_fk_col_is_fk = fk_col_obj.is_fk if fk_col_obj else False
        self.original_fk_col_refs_table = fk_col_obj.references_table if fk_col_obj else None
        self.original_fk_col_refs_col = fk_col_obj.references_column if fk_col_obj else None
        self.original_fk_col_rel_type = fk_col_obj.fk_relationship_type if fk_col_obj else "N:1" 

        self.created_relationship_data_copy = None 

    def redo(self):
        fk_table = self.main_window.tables_data.get(self.fk_table_name)
        pk_table = self.main_window.tables_data.get(self.pk_table_name)

        if not fk_table or not pk_table:
            return

        created_rel = self.main_window.create_relationship(
            fk_table, pk_table, self.fk_col_name, self.pk_col_name,
            self.rel_type, 
            vertical_segment_x_override=self.vertical_segment_x_override, # Pass it here
            from_undo_redo=True
        )
        if created_rel:
            self.created_relationship_data_copy = copy.deepcopy(created_rel)
            if created_rel.graphic_item and not self.created_relationship_data_copy.graphic_item:
                self.created_relationship_data_copy.graphic_item = created_rel.graphic_item


        self.main_window.update_all_relationships_graphics()
        self.main_window.populate_diagram_explorer()
        self.main_window.update_window_title()

    def undo(self):
        if not self.created_relationship_data_copy:
            return

        rel_to_remove = next((r for r in self.main_window.relationships_data if
                              r.table1_name == self.created_relationship_data_copy.table1_name and
                              r.fk_column_name == self.created_relationship_data_copy.fk_column_name and
                              r.table2_name == self.created_relationship_data_copy.table2_name and
                              r.pk_column_name == self.created_relationship_data_copy.pk_column_name), None)

        if rel_to_remove:
            if rel_to_remove.graphic_item and rel_to_remove.graphic_item.scene():
                self.main_window.scene.removeItem(rel_to_remove.graphic_item)
            self.main_window.relationships_data.remove(rel_to_remove)

        fk_table_obj = self.main_window.tables_data.get(self.fk_table_name)
        if fk_table_obj:
            fk_col_obj = fk_table_obj.get_column_by_name(self.fk_col_name)
            if fk_col_obj:
                fk_col_obj.is_fk = self.original_fk_col_is_fk
                fk_col_obj.references_table = self.original_fk_col_refs_table
                fk_col_obj.references_column = self.original_fk_col_refs_col
                fk_col_obj.fk_relationship_type = self.original_fk_col_rel_type
                if fk_table_obj.graphic_item: 
                    fk_table_obj.graphic_item.update()

        self.main_window.update_all_relationships_graphics()
        self.main_window.populate_diagram_explorer()
        self.main_window.update_window_title()
        self.created_relationship_data_copy = None 


class EditDefaultColorsCommand(QUndoCommand):
    def __init__(self, main_window, old_body_color, old_header_color, new_body_color, new_header_color, description="Edit Default Table Colors"):
        super().__init__(description)
        self.main_window = main_window
        self.old_body_color = QColor(old_body_color) if old_body_color else None
        self.old_header_color = QColor(old_header_color) if old_header_color else None
        self.new_body_color = QColor(new_body_color) if new_body_color else None
        self.new_header_color = QColor(new_header_color) if new_header_color else None

    def _apply_colors(self, body_color, header_color):
        self.main_window.user_default_table_body_color = body_color
        self.main_window.user_default_table_header_color = header_color
        
        self.main_window.update_theme_settings()
        self.main_window.set_theme(self.main_window.current_theme, force_update_tables=True)
        self.main_window.save_app_settings() # Save to config
        self.main_window.update_window_title()

    def redo(self):
        self._apply_colors(self.new_body_color, self.new_header_color)

    def undo(self):
        self._apply_colors(self.old_body_color, self.old_header_color)

class EditNotesCommand(QUndoCommand):
    def __init__(self, main_window, old_notes_text, new_notes_text, description="Edit Notes"):
        super().__init__(description)
        self.main_window = main_window
        self.old_notes = old_notes_text
        self.new_notes = new_notes_text
        self._is_initial_apply = True # Flag for the first redo() call after push

    def _apply_notes(self, notes_to_apply, update_ui_text_edit):
        self.main_window.diagram_notes = notes_to_apply
        if update_ui_text_edit: # Only update editor if not the initial push's redo
            if hasattr(self.main_window, 'notes_text_edit') and self.main_window.notes_text_edit:
                # Block signals to prevent on_notes_changed from firing during programmatic update
                self.main_window.notes_text_edit.blockSignals(True)
                self.main_window.notes_text_edit.setPlainText(notes_to_apply)
                self.main_window.notes_text_edit.blockSignals(False)
        self.main_window.update_window_title()

    def redo(self):
        # If it's the initial apply (due to push), only update the model if needed, don't touch UI.
        # For subsequent redos (user action), update both model and UI.
        update_ui = not self._is_initial_apply
        self._apply_notes(self.new_notes, update_ui_text_edit=update_ui)
        self._is_initial_apply = False # Clear flag after first application

    def undo(self):
        self._apply_notes(self.old_notes, update_ui_text_edit=True) # Undo always updates UI
        self._is_initial_apply = False # If we undo, then redo, it's no longer initial


class DeleteRelationshipCommand(QUndoCommand):
    def __init__(self, main_window, relationship_data_to_delete, description="Delete Relationship"):
        super().__init__(description)
        self.main_window = main_window
        self.relationship_data_copy = copy.deepcopy(relationship_data_to_delete)
        self.relationship_graphic_item_instance = relationship_data_to_delete.graphic_item

        fk_table_obj = self.main_window.tables_data.get(self.relationship_data_copy.table1_name)
        self.fk_col_name = self.relationship_data_copy.fk_column_name 
        fk_col_obj = fk_table_obj.get_column_by_name(self.fk_col_name) if fk_table_obj else None
        
        self.original_fk_col_is_fk = fk_col_obj.is_fk if fk_col_obj else False
        self.original_fk_col_refs_table = fk_col_obj.references_table if fk_col_obj else None
        self.original_fk_col_refs_col = fk_col_obj.references_column if fk_col_obj else None
        self.original_fk_col_rel_type = fk_col_obj.fk_relationship_type if fk_col_obj else "N:1"


    def redo(self):
        if self.relationship_graphic_item_instance and self.relationship_graphic_item_instance.scene():
            self.main_window.scene.removeItem(self.relationship_graphic_item_instance)

        live_rel_to_remove = next((r for r in self.main_window.relationships_data if
                                   r.table1_name == self.relationship_data_copy.table1_name and
                                   r.fk_column_name == self.relationship_data_copy.fk_column_name and
                                   r.table2_name == self.relationship_data_copy.table2_name and
                                   r.pk_column_name == self.relationship_data_copy.pk_column_name), None)
        if live_rel_to_remove:
            self.main_window.relationships_data.remove(live_rel_to_remove)

        fk_table = self.main_window.tables_data.get(self.relationship_data_copy.table1_name)
        if fk_table:
            fk_col = fk_table.get_column_by_name(self.fk_col_name)
            if fk_col:
                is_still_an_fk = any(
                    r.table1_name == fk_table.name and r.fk_column_name == fk_col.name
                    for r in self.main_window.relationships_data 
                )
                if not is_still_an_fk: 
                    fk_col.is_fk = False
                    fk_col.references_table = None
                    fk_col.references_column = None
                if fk_table.graphic_item: 
                    fk_table.graphic_item.update()

        self.main_window.update_all_relationships_graphics()
        self.main_window.populate_diagram_explorer()
        self.main_window.update_window_title()

    def undo(self):
        is_already_present = any(
            r.table1_name == self.relationship_data_copy.table1_name and
            r.fk_column_name == self.relationship_data_copy.fk_column_name and
            r.table2_name == self.relationship_data_copy.table2_name and
            r.pk_column_name == self.relationship_data_copy.pk_column_name
            for r in self.main_window.relationships_data
        )
        if not is_already_present:
            self.main_window.relationships_data.append(self.relationship_data_copy)
        
        if self.relationship_graphic_item_instance:
            self.relationship_data_copy.graphic_item = self.relationship_graphic_item_instance 
            if not self.relationship_graphic_item_instance.scene():
                self.main_window.scene.addItem(self.relationship_graphic_item_instance)

        fk_table_obj = self.main_window.tables_data.get(self.relationship_data_copy.table1_name)
        if fk_table_obj:
            fk_col_obj = fk_table_obj.get_column_by_name(self.fk_col_name)
            if fk_col_obj:
                fk_col_obj.is_fk = self.original_fk_col_is_fk
                fk_col_obj.references_table = self.original_fk_col_refs_table
                fk_col_obj.references_column = self.original_fk_col_refs_col
                fk_col_obj.fk_relationship_type = self.original_fk_col_rel_type
                if fk_table_obj.graphic_item:
                    fk_table_obj.graphic_item.update()

        self.main_window.update_all_relationships_graphics()
        self.main_window.populate_diagram_explorer()
        self.main_window.update_window_title()
