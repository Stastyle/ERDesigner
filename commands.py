# commands.py
# This file will contain QUndoCommand subclasses for implementing undo/redo functionality.

from PyQt6.QtGui import QUndoCommand, QColor
from data_models import Table, Column, Relationship
from gui_items import TableGraphicItem, OrthogonalRelationshipLine
import copy

class AddTableCommand(QUndoCommand):
    def __init__(self, main_window, table_data, description="Add Table"):
        super().__init__(description)
        self.main_window = main_window
        self.table_data_copy = copy.deepcopy(table_data)
        self.table_name = table_data.name
        self.table_graphic_item_instance = None # To store the graphic item instance

    def redo(self):
        print(f"Redo: Adding table '{self.table_name}'")
        # Check if table data already exists (e.g., if undo was called then redo)
        if self.table_name in self.main_window.tables_data:
            # If it exists, we assume it's the same object or should be replaced by our copy.
            # For simplicity, let's ensure our copy is the one in use.
            self.table_data_copy = self.main_window.tables_data[self.table_name]
        else:
            self.main_window.tables_data[self.table_name] = self.table_data_copy

        # Ensure graphic item is created and added if it doesn't exist or isn't in scene
        if not self.table_data_copy.graphic_item or not self.table_data_copy.graphic_item.scene():
            if self.table_graphic_item_instance and not self.table_graphic_item_instance.scene():
                # If we have a stored instance that's not in scene (e.g., after undo), re-add it
                self.main_window.scene.addItem(self.table_graphic_item_instance)
                self.table_data_copy.graphic_item = self.table_graphic_item_instance # Re-link
            else:
                # Create a new graphic item
                self.table_graphic_item_instance = TableGraphicItem(self.table_data_copy)
                self.main_window.scene.addItem(self.table_graphic_item_instance)
                self.table_data_copy.graphic_item = self.table_graphic_item_instance # Link
        
        self.main_window.update_all_relationships_graphics()
        self.main_window.update_window_title()

    def undo(self):
        print(f"Undo: Removing table '{self.table_name}'")
        if self.table_name in self.main_window.tables_data:
            table_to_remove_data = self.main_window.tables_data.pop(self.table_name)
            
            # Use the stored graphic item instance for removal
            if self.table_graphic_item_instance and self.table_graphic_item_instance.scene():
                self.main_window.scene.removeItem(self.table_graphic_item_instance)
            
            # Nullify graphic_item reference in the data objects
            if table_to_remove_data:
                 table_to_remove_data.graphic_item = None
            if self.table_data_copy is not table_to_remove_data: # If they are different objects
                 self.table_data_copy.graphic_item = None
            # The stored self.table_graphic_item_instance remains for redo.
        else:
            print(f"Undo warning: Table '{self.table_name}' not found in data.")
        
        self.main_window.update_all_relationships_graphics()
        self.main_window.update_window_title()

class DeleteRelationshipCommand(QUndoCommand):
    def __init__(self, main_window, relationship_data_instance, description="Delete Relationship"):
        super().__init__(description)
        self.main_window = main_window
        self.relationship_data_copy = copy.deepcopy(relationship_data_instance)
        self.relationship_graphic_item_instance = relationship_data_instance.graphic_item

        self.fk_table_name = relationship_data_instance.table1_name
        self.fk_column_name = relationship_data_instance.fk_column_name
        self.pk_table_name = relationship_data_instance.table2_name
        self.pk_column_name = relationship_data_instance.pk_column_name

        fk_table_obj = self.main_window.tables_data.get(self.fk_table_name)
        self.original_fk_column_state = None
        if fk_table_obj:
            fk_col_obj = fk_table_obj.get_column_by_name(self.fk_column_name)
            if fk_col_obj:
                self.original_fk_column_state = {
                    "is_fk": fk_col_obj.is_fk,
                    "references_table": fk_col_obj.references_table,
                    "references_column": fk_col_obj.references_column,
                    "fk_relationship_type": fk_col_obj.fk_relationship_type
                }

    def redo(self):
        print(f"Redo: Deleting relationship {self.fk_table_name}.{self.fk_column_name} -> {self.pk_table_name}.{self.pk_column_name}")

        if self.relationship_graphic_item_instance and self.relationship_graphic_item_instance.scene():
            self.main_window.scene.removeItem(self.relationship_graphic_item_instance)

        live_rel_to_remove = next((r for r in self.main_window.relationships_data if
                                   r.table1_name == self.fk_table_name and r.fk_column_name == self.fk_column_name and
                                   r.table2_name == self.pk_table_name and r.pk_column_name == self.pk_column_name), None)
        if live_rel_to_remove:
            self.main_window.relationships_data.remove(live_rel_to_remove)
        else:
            print(f"Redo Warning: Live relationship data for {self.fk_table_name}.{self.fk_column_name} not found.")

        fk_table_obj = self.main_window.tables_data.get(self.fk_table_name)
        if fk_table_obj:
            fk_col_obj = fk_table_obj.get_column_by_name(self.fk_column_name)
            if fk_col_obj:
                is_still_fk_by_other_rel = any(
                    r.table1_name == self.fk_table_name and r.fk_column_name == self.fk_column_name
                    for r in self.main_window.relationships_data
                )
                if not is_still_fk_by_other_rel:
                    fk_col_obj.is_fk = False
                    fk_col_obj.references_table = None
                    fk_col_obj.references_column = None
                if fk_table_obj.graphic_item:
                    fk_table_obj.graphic_item.update()
        self.main_window.update_window_title()

    def undo(self):
        print(f"Undo: Restoring relationship {self.fk_table_name}.{self.fk_column_name} -> {self.pk_table_name}.{self.pk_column_name}")
        if self.original_fk_column_state:
            fk_table_obj = self.main_window.tables_data.get(self.fk_table_name)
            if fk_table_obj:
                fk_col_obj = fk_table_obj.get_column_by_name(self.fk_column_name)
                if fk_col_obj:
                    fk_col_obj.is_fk = self.original_fk_column_state["is_fk"]
                    fk_col_obj.references_table = self.original_fk_column_state["references_table"]
                    fk_col_obj.references_column = self.original_fk_column_state["references_column"]
                    fk_col_obj.fk_relationship_type = self.original_fk_column_state["fk_relationship_type"]
                    if fk_table_obj.graphic_item:
                        fk_table_obj.graphic_item.update()
        
        # Add the relationship data back if it's not a duplicate by content
        is_duplicate_content = any(
            r.table1_name == self.relationship_data_copy.table1_name and
            r.fk_column_name == self.relationship_data_copy.fk_column_name and
            r.table2_name == self.relationship_data_copy.table2_name and
            r.pk_column_name == self.relationship_data_copy.pk_column_name
            for r in self.main_window.relationships_data
        )
        if not is_duplicate_content:
            self.main_window.relationships_data.append(self.relationship_data_copy)
        else: # If it is duplicate by content, ensure our copy (with correct graphic_item) is used or updated
            existing_rel = next((r for r in self.main_window.relationships_data if 
                                 r.table1_name == self.relationship_data_copy.table1_name and 
                                 r.fk_column_name == self.relationship_data_copy.fk_column_name and
                                 r.table2_name == self.relationship_data_copy.table2_name and
                                 r.pk_column_name == self.relationship_data_copy.pk_column_name), None)
            if existing_rel and self.relationship_graphic_item_instance:
                existing_rel.graphic_item = self.relationship_graphic_item_instance # Ensure correct graphic item is linked


        if self.relationship_graphic_item_instance:
            # Link our stored copy of relationship data to the graphic item
            self.relationship_data_copy.graphic_item = self.relationship_graphic_item_instance
            if not self.relationship_graphic_item_instance.scene():
                self.main_window.scene.addItem(self.relationship_graphic_item_instance)
            self.main_window.update_orthogonal_path(self.relationship_data_copy)
        self.main_window.update_window_title()


class CreateRelationshipCommand(QUndoCommand):
    def __init__(self, main_window, fk_table_data, pk_table_data, fk_col_name, pk_col_name, rel_type, description="Create Relationship"):
        super().__init__(description)
        self.main_window = main_window
        self.fk_table_name = fk_table_data.name
        self.pk_table_name = pk_table_data.name
        self.fk_col_name = fk_col_name
        self.pk_col_name = pk_col_name
        self.rel_type = rel_type

        self.created_relationship_data_ref = None # Will store the reference from main_window.relationships_data
        self.created_relationship_graphic_item_ref = None # Will store the graphic item from the relationship_data_ref
        self.original_fk_column_state = None
        self.was_newly_created = False # To track if redo actually created a new one or updated

        fk_col_obj = fk_table_data.get_column_by_name(fk_col_name)
        if fk_col_obj:
            self.original_fk_column_state = {
                "is_fk": fk_col_obj.is_fk,
                "references_table": fk_col_obj.references_table,
                "references_column": fk_col_obj.references_column,
                "fk_relationship_type": fk_col_obj.fk_relationship_type
            }

    def redo(self):
        print(f"Redo: CreateRelationshipCommand for {self.fk_table_name}.{self.fk_col_name} -> {self.pk_table_name}.{self.pk_col_name} Type: {self.rel_type}")
        fk_table_obj = self.main_window.tables_data.get(self.fk_table_name)
        pk_table_obj = self.main_window.tables_data.get(self.pk_table_name)

        if not (fk_table_obj and pk_table_obj):
            print("CreateRelationshipCommand.redo: FK or PK table object not found.")
            return

        fk_col_obj = fk_table_obj.get_column_by_name(self.fk_col_name)
        if not fk_col_obj:
            print(f"CreateRelationshipCommand.redo: FK column '{self.fk_col_name}' not found in table '{self.fk_table_name}'.")
            return

        # Store current FK properties before changing them, in case create_relationship fails
        # or if we need to revert just this command's specific changes to an existing relationship.
        # This is slightly different from self.original_fk_column_state which is before the command entirely.
        pre_redo_fk_state = {
            "is_fk": fk_col_obj.is_fk,
            "references_table": fk_col_obj.references_table,
            "references_column": fk_col_obj.references_column,
            "fk_relationship_type": fk_col_obj.fk_relationship_type
        }

        # Update FK column properties
        fk_col_obj.is_fk = True
        fk_col_obj.references_table = self.pk_table_name
        fk_col_obj.references_column = self.pk_col_name
        fk_col_obj.fk_relationship_type = self.rel_type
        if fk_table_obj.graphic_item:
            fk_table_obj.graphic_item.update()

        # Check if the relationship already exists before calling create_relationship
        # This helps determine if `create_relationship` will create a new one or return existing.
        existing_before_call = next((r for r in self.main_window.relationships_data if
                                     r.table1_name == self.fk_table_name and r.fk_column_name == self.fk_col_name and
                                     r.table2_name == self.pk_table_name and r.pk_column_name == self.pk_col_name), None)

        # Call main_window's method. It handles adding to data list and scene.
        # It returns the (potentially new, or existing and updated) Relationship object.
        relationship_instance = self.main_window.create_relationship(
            fk_table_obj, pk_table_obj, self.fk_col_name, self.pk_col_name, self.rel_type,
            from_undo_redo=True # Important for explorer updates via signals
        )

        if not relationship_instance:
            print(f"CreateRelationshipCommand.redo: main_window.create_relationship failed for {self.fk_table_name}.{self.fk_col_name}. Reverting FK column changes.")
            # Revert FK column changes made by this redo
            fk_col_obj.is_fk = pre_redo_fk_state["is_fk"]
            fk_col_obj.references_table = pre_redo_fk_state["references_table"]
            fk_col_obj.references_column = pre_redo_fk_state["references_column"]
            fk_col_obj.fk_relationship_type = pre_redo_fk_state["fk_relationship_type"]
            if fk_table_obj.graphic_item: fk_table_obj.graphic_item.update()
            return

        self.created_relationship_data_ref = relationship_instance
        self.created_relationship_graphic_item_ref = relationship_instance.graphic_item
        
        self.was_newly_created = not bool(existing_before_call) or (existing_before_call is not relationship_instance)


        if self.created_relationship_graphic_item_ref:
            self.main_window.update_orthogonal_path(self.created_relationship_data_ref)
        
        self.main_window.update_window_title()
        print(f"Redo CreateRelationshipCommand: {'Newly created' if self.was_newly_created else 'Updated existing'} relationship.")


    def undo(self):
        print(f"Undo: CreateRelationshipCommand for {self.fk_table_name}.{self.fk_col_name} -> {self.pk_table_name}.{self.pk_col_name}")

        if self.was_newly_created: # If redo created a new relationship
            if self.created_relationship_graphic_item_ref and self.created_relationship_graphic_item_ref.scene():
                self.main_window.scene.removeItem(self.created_relationship_graphic_item_ref)
                print("  Undo: Removed graphic item for newly created relationship.")
            
            if self.created_relationship_data_ref and self.created_relationship_data_ref in self.main_window.relationships_data:
                self.main_window.relationships_data.remove(self.created_relationship_data_ref)
                print("  Undo: Removed data object for newly created relationship.")
        else: # If redo only updated an existing relationship (e.g., type change, or CSV explicit def matched inferred)
            # We might need to revert the type of the existing relationship if it was changed by this command's redo.
            # This requires storing the relationship's type *before* this command's redo modified it.
            # For now, the primary action is reverting the FK column.
            # The `create_relationship` in main_window updates type if different.
            # `original_fk_column_state` contains the original fk_relationship_type.
            print("  Undo: Relationship was pre-existing or updated. Only reverting FK column state based on original_fk_column_state.")


        # Always restore the FK column to its state *before this command was ever executed*
        if self.original_fk_column_state:
            fk_table_obj = self.main_window.tables_data.get(self.fk_table_name)
            if fk_table_obj:
                fk_col_obj = fk_table_obj.get_column_by_name(self.fk_col_name)
                if fk_col_obj:
                    fk_col_obj.is_fk = self.original_fk_column_state["is_fk"]
                    fk_col_obj.references_table = self.original_fk_column_state["references_table"]
                    fk_col_obj.references_column = self.original_fk_column_state["references_column"]
                    fk_col_obj.fk_relationship_type = self.original_fk_column_state["fk_relationship_type"]
                    if fk_table_obj.graphic_item:
                        fk_table_obj.graphic_item.update()
                    print(f"  Undo: Restored FK column '{self.fk_col_name}' in '{self.fk_table_name}'.")
        
        self.main_window.update_all_relationships_graphics() # Redraw lines
        self.main_window.update_window_title()

class DeleteTableCommand(QUndoCommand):
    def __init__(self, main_window, table_data_to_delete, description="Delete Table"):
        super().__init__(description)
        self.main_window = main_window
        self.table_graphic_item_instance = table_data_to_delete.graphic_item
        self.table_data_copy = copy.deepcopy(table_data_to_delete) 
        self.table_name = table_data_to_delete.name
        self.deleted_relationships_with_graphics = []
        self.affected_fk_columns_original_states = []

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
        print(f"Redo: Deleting table '{self.table_name}' and its relationships.")
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
                        fk_col.is_fk = False
                        fk_col.references_table = None
                        fk_col.references_column = None
                        if other_table_obj.graphic_item: other_table_obj.graphic_item.update()
        if self.table_name in self.main_window.tables_data:
            if self.table_graphic_item_instance and self.table_graphic_item_instance.scene():
                self.main_window.scene.removeItem(self.table_graphic_item_instance)
            del self.main_window.tables_data[self.table_name]
        self.main_window.update_window_title()
        self.main_window.scene.update()

    def undo(self):
        print(f"Undo: Restoring table '{self.table_name}' and its relationships.")
        if self.table_name not in self.main_window.tables_data:
            self.main_window.tables_data[self.table_name] = self.table_data_copy
            if self.table_graphic_item_instance:
                self.table_data_copy.graphic_item = self.table_graphic_item_instance 
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
                self.main_window.update_orthogonal_path(rel_data_copy)
        self.main_window.update_all_relationships_graphics() 
        self.main_window.update_window_title()
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


    def _apply_properties(self, name_to_apply, body_color_hex_to_apply, header_color_hex_to_apply, columns_to_apply_list):
        print(f"COMMANDS: _apply_properties for table '{self.table_data_object.name}' (target name: '{name_to_apply}')")
        original_name_of_live_object = self.table_data_object.name
        name_changed = original_name_of_live_object != name_to_apply

        if name_changed:
            if name_to_apply in self.main_window.tables_data and self.main_window.tables_data[name_to_apply] is not self.table_data_object:
                print(f"Error: Cannot rename table to '{name_to_apply}' as it already exists.")
                return False
            if original_name_of_live_object in self.main_window.tables_data:
                del self.main_window.tables_data[original_name_of_live_object]
            self.main_window.tables_data[name_to_apply] = self.table_data_object
            self.table_data_object.name = name_to_apply
            self.main_window.update_relationship_table_names(original_name_of_live_object, name_to_apply)
            self.main_window.update_fk_references_to_table(original_name_of_live_object, name_to_apply)

        self.table_data_object.body_color = QColor(body_color_hex_to_apply)
        self.table_data_object.header_color = QColor(header_color_hex_to_apply)

        columns_before_this_apply = self.old_columns_data if name_to_apply == self.new_name else self.new_columns_data
        self.table_data_object.columns = copy.deepcopy(columns_to_apply_list)
        
        old_pk_map_for_comparison = {col.name: col for col in columns_before_this_apply if col.is_pk}
        current_pk_map_in_live_object = {col.name: col for col in self.table_data_object.columns if col.is_pk}

        for old_pk_name, old_pk_col_obj in old_pk_map_for_comparison.items():
            if old_pk_name not in current_pk_map_in_live_object or not current_pk_map_in_live_object[old_pk_name].is_pk : # Check if still PK by same name
                # This PK was removed or its name changed and it's no longer PK under the old name
                # If it was renamed and is still PK, the next loop will handle updating FKs to new name.
                # Here, we only care if it's GONE as a PK under the old name.
                is_renamed_and_still_pk = False
                for new_pk_name_check, new_pk_col_check in current_pk_map_in_live_object.items():
                    # A heuristic for rename: if an old PK name is gone, and a new PK name appeared,
                    # and they might correspond (e.g. if only one PK). This is not perfect.
                    # A more robust way is needed if columns don't have stable IDs.
                    # For now, if old_pk_name is not in current_pk_map, assume it's gone or renamed.
                    # If it was renamed to new_pk_name_check, update_fk_references_to_pk will be called below.
                    # The critical part is to invalidate FKs pointing to a PK that *no longer exists by that name*.
                    pass # Complex rename logic deferred or simplified.

                # If old_pk_name is truly gone (not just renamed to another PK)
                if not any(new_col.name == old_pk_name and new_col.is_pk for new_col in self.table_data_object.columns):
                     print(f"COMMANDS: PK '{old_pk_name}' in table '{name_to_apply}' is no longer a PK. Updating FKs that pointed to it.")
                     self.main_window.update_fk_references_to_pk(name_to_apply, old_pk_name, None)


        for current_pk_name, current_pk_col_obj in current_pk_map_in_live_object.items():
            original_old_pk_name_for_this_new_pk = None
            # Try to find if this current_pk_name corresponds to an old_pk_name (i.e., a rename)
            # This is heuristic. Assumes if a new PK name appears and an old one disappears, it's a rename.
            if current_pk_name not in old_pk_map_for_comparison: # New PK name
                if len(old_pk_map_for_comparison) == 1 and len(current_pk_map_in_live_object) == 1:
                     original_old_pk_name_for_this_new_pk = list(old_pk_map_for_comparison.keys())[0]
            
            if original_old_pk_name_for_this_new_pk and original_old_pk_name_for_this_new_pk != current_pk_name:
                print(f"COMMANDS: PK in table '{name_to_apply}' renamed from '{original_old_pk_name_for_this_new_pk}' to '{current_pk_name}'. Updating FKs.")
                self.main_window.update_fk_references_to_pk(name_to_apply, original_old_pk_name_for_this_new_pk, current_pk_name)
            # If it's a brand new PK (not a rename of a previous one), no need to update FKs in other tables *to* it yet.

        print(f"COMMANDS: Removing relationships for table '{name_to_apply}' based on its column state *before* this apply.")
        self.main_window.remove_relationships_for_table(name_to_apply, columns_before_this_apply)

        print(f"COMMANDS: Creating relationships for table '{name_to_apply}' based on its column state *after* this apply.")
        for col in self.table_data_object.columns:
            if col.is_fk and col.references_table and col.references_column:
                target_table_obj = self.main_window.tables_data.get(col.references_table)
                if target_table_obj:
                    target_pk_col_obj = target_table_obj.get_column_by_name(col.references_column)
                    if target_pk_col_obj and target_pk_col_obj.is_pk:
                        self.main_window.create_relationship(
                            self.table_data_object, target_table_obj,
                            col.name, col.references_column, col.fk_relationship_type,
                            from_undo_redo=True 
                        )
                    else:
                        col.is_fk = False; col.references_table = None; col.references_column = None
                else:
                    col.is_fk = False; col.references_table = None; col.references_column = None

        if self.table_data_object.graphic_item:
            self.table_data_object.graphic_item.prepareGeometryChange()
            self.table_data_object.graphic_item._calculate_height()
            self.table_data_object.graphic_item.update()

        self.main_window.update_all_relationships_graphics()
        self.main_window.update_window_title()
        print(f"COMMANDS: _apply_properties for table '{name_to_apply}' finished.")
        return True


    def redo(self):
        print(f"COMMANDS: Redo EditTableCommand for table (original name: '{self.old_name}', new name: '{self.new_name}')")
        self._apply_properties(self.new_name, self.new_body_color_hex, self.new_header_color_hex, self.new_columns_data)

    def undo(self):
        print(f"COMMANDS: Undo EditTableCommand for table (current name: '{self.new_name}', reverting to: '{self.old_name}')")
        self._apply_properties(self.old_name, self.old_body_color_hex, self.old_header_color_hex, self.old_columns_data)

