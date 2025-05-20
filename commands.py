# commands.py
# This file will contain QUndoCommand subclasses for implementing undo/redo functionality.

from PyQt6.QtGui import QUndoCommand, QColor
from PyQt6.QtCore import QPointF, QRectF
from data_models import Table, Column, Relationship, GroupData
# from gui_items import TableGraphicItem, OrthogonalRelationshipPathItem, GroupGraphicItem # Keep as local imports
import copy
import constants # Import constants for GRID_SIZE

# print("commands.py loaded") # DEBUG

class AddTableCommand(QUndoCommand):
    def __init__(self, main_window, table_data, description="Add Table"):
        super().__init__(description)
        self.main_window = main_window
        self.table_data_copy = copy.deepcopy(table_data)
        self.table_name = table_data.name
        self.table_graphic_item_instance = table_data.graphic_item if table_data.graphic_item else None
        self.initial_parent_item_name = None 

    def redo(self):
        from gui_items import TableGraphicItem 
        self.main_window.tables_data[self.table_name] = self.table_data_copy

        parent_graphic = None
        if self.table_data_copy.group_name:
            group_data = self.main_window.groups_data.get(self.table_data_copy.group_name)
            if group_data and group_data.graphic_item:
                parent_graphic = group_data.graphic_item

        if not self.table_data_copy.graphic_item or not self.table_data_copy.graphic_item.scene():
            if self.table_graphic_item_instance and not self.table_graphic_item_instance.scene():
                self.table_data_copy.graphic_item = self.table_graphic_item_instance
            else:
                self.table_graphic_item_instance = TableGraphicItem(self.table_data_copy) 
                self.table_data_copy.graphic_item = self.table_graphic_item_instance

        if parent_graphic:
            if self.table_data_copy.graphic_item.parentItem() != parent_graphic:
                self.table_data_copy.graphic_item.setParentItem(parent_graphic)
            relative_pos = parent_graphic.mapFromScene(QPointF(self.table_data_copy.x, self.table_data_copy.y))
            self.table_data_copy.graphic_item.setPos(relative_pos)
        else:
            if self.table_data_copy.graphic_item.parentItem() is not None:
                self.table_data_copy.graphic_item.setParentItem(None) 
            self.table_data_copy.graphic_item.setPos(self.table_data_copy.x, self.table_data_copy.y)
            if not self.table_data_copy.graphic_item.scene(): 
                 self.main_window.scene.addItem(self.table_data_copy.graphic_item)


        if self.table_data_copy.graphic_item:
            self.table_data_copy.graphic_item.update()

        if self.table_data_copy.group_name:
            group_obj = self.main_window.groups_data.get(self.table_data_copy.group_name)
            if group_obj:
                group_obj.add_table(self.table_name)

        self.main_window.update_all_relationships_graphics()
        self.main_window.update_window_title()
        self.main_window.populate_diagram_explorer()


    def undo(self):
        if not self.table_graphic_item_instance and self.table_name in self.main_window.tables_data:
            live_table_data = self.main_window.tables_data[self.table_name]
            if live_table_data.graphic_item:
                self.table_graphic_item_instance = live_table_data.graphic_item
        
        original_group_name_for_undo = self.table_data_copy.group_name
        if original_group_name_for_undo:
            group_obj = self.main_window.groups_data.get(original_group_name_for_undo)
            if group_obj:
                group_obj.remove_table(self.table_name)

        if self.table_name in self.main_window.tables_data:
            table_to_remove_data = self.main_window.tables_data.pop(self.table_name)
            
            if self.table_graphic_item_instance:
                if self.table_graphic_item_instance.parentItem(): 
                    self.table_graphic_item_instance.setParentItem(None)
                if self.table_graphic_item_instance.scene():
                    self.main_window.scene.removeItem(self.table_graphic_item_instance)
            
            if table_to_remove_data:
                 table_to_remove_data.graphic_item = None
            if self.table_data_copy is not table_to_remove_data:
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
        self.affected_fk_columns_original_states = []
        self.original_group_name = table_data_to_delete.group_name
        self.original_parent_item_name = None 
        if self.table_graphic_item_instance and self.table_graphic_item_instance.parentItem():
            parent_group_graphic = self.table_graphic_item_instance.parentItem()
            if hasattr(parent_group_graphic, 'group_data'):
                self.original_parent_item_name = parent_group_graphic.group_data.name


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

        if self.original_group_name and self.original_group_name in self.main_window.groups_data:
            group_obj = self.main_window.groups_data[self.original_group_name]
            group_obj.remove_table(self.table_name)

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
            parent_graphic_for_undo = None
            if self.original_parent_item_name: 
                parent_group_data = self.main_window.groups_data.get(self.original_parent_item_name)
                if parent_group_data and parent_group_data.graphic_item:
                    parent_graphic_for_undo = parent_group_data.graphic_item

            if self.table_graphic_item_instance: 
                self.table_data_copy.graphic_item = self.table_graphic_item_instance
                if parent_graphic_for_undo:
                    if self.table_graphic_item_instance.parentItem() != parent_graphic_for_undo:
                        self.table_graphic_item_instance.setParentItem(parent_graphic_for_undo)
                    relative_pos = parent_graphic_for_undo.mapFromScene(QPointF(self.table_data_copy.x, self.table_data_copy.y))
                    self.table_graphic_item_instance.setPos(relative_pos)
                else: 
                    if self.table_graphic_item_instance.parentItem() is not None:
                        self.table_graphic_item_instance.setParentItem(None)
                    self.table_graphic_item_instance.setPos(self.table_data_copy.x, self.table_data_copy.y)
                    if not self.table_graphic_item_instance.scene():
                         self.main_window.scene.addItem(self.table_graphic_item_instance)
                self.table_graphic_item_instance.update()

        self.table_data_copy.group_name = self.original_group_name
        if self.original_group_name and self.original_group_name in self.main_window.groups_data:
            group_obj = self.main_window.groups_data[self.original_group_name]
            group_obj.add_table(self.table_name)

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
        
        self.old_group_name = old_properties.get("group_name") 
        self.new_group_name = new_properties.get("group_name") 


    def _apply_properties(self, name_to_apply, body_color_hex_to_apply, header_color_hex_to_apply, columns_to_apply_list, group_name_to_apply):
        original_name_of_live_object = self.table_data_object.name 
        name_changed = original_name_of_live_object != name_to_apply

        if name_changed:
            if name_to_apply in self.main_window.tables_data and self.main_window.tables_data[name_to_apply] is not self.table_data_object:
                return False 
            
            if original_name_of_live_object in self.main_window.tables_data:
                del self.main_window.tables_data[original_name_of_live_object]
            self.main_window.tables_data[name_to_apply] = self.table_data_object
            
            self.table_data_object.name = name_to_apply 
            
            self.main_window.update_relationship_table_names(original_name_of_live_object, name_to_apply)
            self.main_window.update_fk_references_to_table(original_name_of_live_object, name_to_apply)

        self.table_data_object.body_color = QColor(body_color_hex_to_apply)
        self.table_data_object.header_color = QColor(header_color_hex_to_apply)

        columns_state_before_this_apply = self.old_columns_data if name_to_apply == self.new_name else self.new_columns_data

        old_pk_map = {col.name: col for col in columns_state_before_this_apply if col.is_pk}
        new_pk_map = {col.name: col for col in columns_to_apply_list if col.is_pk}

        for old_pk_name, old_pk_col_obj in old_pk_map.items():
            if old_pk_name not in new_pk_map or not new_pk_map[old_pk_name].is_pk : 
                is_renamed_and_still_pk = False
                if len(old_pk_map) == 1 and len(new_pk_map) == 1: 
                    new_pk_name_check = list(new_pk_map.keys())[0]
                    if old_pk_name != new_pk_name_check : 
                        is_renamed_and_still_pk = True
                
                if not is_renamed_and_still_pk: 
                     self.main_window.update_fk_references_to_pk(name_to_apply, old_pk_name, None) 

        for new_pk_name, new_pk_col_obj in new_pk_map.items():
            original_old_pk_name_for_this_new_pk = None
            if new_pk_name not in old_pk_map: 
                if len(old_pk_map) == 1 and len(new_pk_map) == 1:
                     original_old_pk_name_for_this_new_pk = list(old_pk_map.keys())[0]
            
            if original_old_pk_name_for_this_new_pk and original_old_pk_name_for_this_new_pk != new_pk_name:
                self.main_window.update_fk_references_to_pk(name_to_apply, original_old_pk_name_for_this_new_pk, new_pk_name)
        
        self.table_data_object.columns = copy.deepcopy(columns_to_apply_list) 

        self.main_window.remove_relationships_for_table(name_to_apply, columns_state_before_this_apply)

        for col in self.table_data_object.columns:
            if col.is_fk and col.references_table and col.references_column:
                target_table_obj = self.main_window.tables_data.get(col.references_table)
                if target_table_obj:
                    target_pk_col_obj = target_table_obj.get_column_by_name(col.references_column)
                    if target_pk_col_obj and target_pk_col_obj.is_pk: 
                        # Pass the vertical_segment_x_override from the existing relationship if it's being updated,
                        # or None if it's a brand new one.
                        # This requires finding the existing relationship data if any.
                        existing_rel_data = next((r for r in self.main_window.relationships_data if
                                                  r.table1_name == self.table_data_object.name and r.fk_column_name == col.name and
                                                  r.table2_name == target_table_obj.name and r.pk_column_name == col.references_column), None)
                        
                        override_x = existing_rel_data.vertical_segment_x_override if existing_rel_data else None

                        self.main_window.create_relationship(
                            self.table_data_object, target_table_obj, 
                            col.name, col.references_column,           
                            col.fk_relationship_type,                  
                            vertical_segment_x_override=override_x, # Pass existing or None
                            from_undo_redo=True                        
                        )
                    else: 
                        col.is_fk = False; col.references_table = None; col.references_column = None
                else: 
                    col.is_fk = False; col.references_table = None; col.references_column = None
        
        if self.table_data_object.group_name != group_name_to_apply:
            if self.table_data_object.group_name and self.table_data_object.group_name in self.main_window.groups_data:
                self.main_window.groups_data[self.table_data_object.group_name].remove_table(self.table_data_object.name)
            
            self.table_data_object.group_name = group_name_to_apply
            
            if group_name_to_apply and group_name_to_apply in self.main_window.groups_data:
                self.main_window.groups_data[group_name_to_apply].add_table(self.table_data_object.name)


        if self.table_data_object.graphic_item:
            self.table_data_object.graphic_item.prepareGeometryChange()
            self.table_data_object.graphic_item._calculate_height() 
            self.table_data_object.graphic_item.update() 

        self.main_window.update_all_relationships_graphics() 
        self.main_window.update_window_title()
        self.main_window.populate_diagram_explorer()
        return True


    def redo(self):
        self._apply_properties(self.new_name, self.new_body_color_hex, self.new_header_color_hex, self.new_columns_data, self.new_group_name)

    def undo(self):
        self._apply_properties(self.old_name, self.old_body_color_hex, self.old_header_color_hex, self.old_columns_data, self.old_group_name)


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
            self.relationship_data_ref.graphic_item.prepareGeometryChange()
            self.relationship_data_ref.graphic_item._build_path() # Rebuild based on new override
            # No separate handle update needed here as _build_path calls it if necessary
            self.relationship_data_ref.graphic_item.update()
        self.main_window.update_window_title()
        # self.main_window.populate_diagram_explorer() # Not strictly needed for this change

    def redo(self):
        self._apply_override(self.new_x_override)

    def undo(self):
        self._apply_override(self.old_x_override)


class AddGroupCommand(QUndoCommand):
    def __init__(self, main_window, group_data: GroupData, description="Add Group"):
        super().__init__(description)
        self.main_window = main_window
        self.group_data_copy = copy.deepcopy(group_data) 
        self.group_name = group_data.name
        self.group_graphic_item_instance = group_data.graphic_item 

    def redo(self):
        from gui_items import GroupGraphicItem 
        self.main_window.groups_data[self.group_name] = self.group_data_copy

        if not self.group_data_copy.graphic_item or not self.group_data_copy.graphic_item.scene():
            if self.group_graphic_item_instance and not self.group_graphic_item_instance.scene():
                self.main_window.scene.addItem(self.group_graphic_item_instance)
                self.group_data_copy.graphic_item = self.group_graphic_item_instance
            else:
                self.group_graphic_item_instance = GroupGraphicItem(self.group_data_copy)
                self.main_window.scene.addItem(self.group_graphic_item_instance)
                self.group_data_copy.graphic_item = self.group_graphic_item_instance
        
        if self.group_data_copy.graphic_item:
            self.group_data_copy.graphic_item.setPos(self.group_data_copy.x, self.group_data_copy.y)
            self.group_data_copy.graphic_item.setRect(0, 0, self.group_data_copy.width, self.group_data_copy.height)
            self.group_data_copy.graphic_item.update()
        
        self.main_window.update_window_title()
        self.main_window.populate_diagram_explorer()

    def undo(self):
        if not self.group_graphic_item_instance and self.group_name in self.main_window.groups_data:
            live_group_data = self.main_window.groups_data[self.group_name]
            if live_group_data.graphic_item:
                self.group_graphic_item_instance = live_group_data.graphic_item

        if self.group_name in self.main_window.groups_data:
            group_to_remove_data = self.main_window.groups_data.pop(self.group_name)
            
            if self.group_graphic_item_instance and self.group_graphic_item_instance.scene():
                self.main_window.scene.removeItem(self.group_graphic_item_instance)

            if group_to_remove_data:
                 group_to_remove_data.graphic_item = None
            if self.group_data_copy is not group_to_remove_data:
                 self.group_data_copy.graphic_item = None
            
            for table_data in self.main_window.tables_data.values():
                if table_data.group_name == self.group_name:
                    table_data.group_name = None 

        self.main_window.update_window_title()
        self.main_window.populate_diagram_explorer()


class DeleteGroupCommand(QUndoCommand):
    def __init__(self, main_window, group_data_to_delete: GroupData, description="Delete Group"):
        super().__init__(description)
        self.main_window = main_window
        self.group_data_copy = copy.deepcopy(group_data_to_delete)
        self.group_name = group_data_to_delete.name
        self.group_graphic_item_instance = group_data_to_delete.graphic_item
        self.contained_tables_original_group_info = {} 

        for table_name_in_group in list(self.group_data_copy.table_names): 
            table_data = self.main_window.tables_data.get(table_name_in_group)
            if table_data:
                self.contained_tables_original_group_info[table_name_in_group] = self.group_name


    def redo(self):
        for table_name in list(self.group_data_copy.table_names): 
            table_data = self.main_window.tables_data.get(table_name)
            if table_data and table_data.group_name == self.group_name:
                table_data.group_name = None 
                if table_data.graphic_item and table_data.graphic_item.parentItem() == self.group_graphic_item_instance:
                    scene_pos = self.group_graphic_item_instance.mapToScene(table_data.graphic_item.pos())
                    table_data.graphic_item.setParentItem(None) 
                    table_data.graphic_item.setPos(scene_pos) 
                    table_data.x = scene_pos.x() 
                    table_data.y = scene_pos.y()


        if self.group_graphic_item_instance and self.group_graphic_item_instance.scene():
            self.main_window.scene.removeItem(self.group_graphic_item_instance)
        if self.group_name in self.main_window.groups_data:
            del self.main_window.groups_data[self.group_name]

        self.main_window.update_window_title()
        self.main_window.populate_diagram_explorer()
        self.main_window.scene.update()

    def undo(self):
        from gui_items import GroupGraphicItem 
        if self.group_name not in self.main_window.groups_data:
            self.main_window.groups_data[self.group_name] = self.group_data_copy
            if self.group_graphic_item_instance:
                self.group_data_copy.graphic_item = self.group_graphic_item_instance
                if not self.group_graphic_item_instance.scene():
                    self.main_window.scene.addItem(self.group_graphic_item_instance)
                self.group_graphic_item_instance.setPos(self.group_data_copy.x, self.group_data_copy.y)
                self.group_graphic_item_instance.setRect(0,0, self.group_data_copy.width, self.group_data_copy.height)
                self.group_graphic_item_instance.update()


        self.group_data_copy.table_names.clear() 
        for table_name, original_group in self.contained_tables_original_group_info.items():
            table_data = self.main_window.tables_data.get(table_name)
            if table_data:
                table_data.group_name = self.group_name 
                self.group_data_copy.add_table(table_data.name) 
                if table_data.graphic_item and self.group_graphic_item_instance:
                    if table_data.graphic_item.parentItem() != self.group_graphic_item_instance:
                        relative_pos = self.group_graphic_item_instance.mapFromScene(QPointF(table_data.x, table_data.y))
                        table_data.graphic_item.setParentItem(self.group_graphic_item_instance)
                        table_data.graphic_item.setPos(relative_pos)


        self.main_window.update_window_title()
        self.main_window.populate_diagram_explorer()
        self.main_window.scene.update()


class RenameGroupCommand(QUndoCommand):
    def __init__(self, main_window, group_data_ref: GroupData, old_name: str, new_name: str, description="Rename Group"):
        super().__init__(description)
        self.main_window = main_window
        self.group_data_ref = group_data_ref 
        self.old_name = old_name
        self.new_name = new_name

    def _apply_name(self, name_to_set: str, name_to_remove_from_dict: str):
        self.group_data_ref.name = name_to_set
        
        if name_to_remove_from_dict in self.main_window.groups_data:
            if self.main_window.groups_data[name_to_remove_from_dict] is self.group_data_ref:
                 del self.main_window.groups_data[name_to_remove_from_dict]
        self.main_window.groups_data[name_to_set] = self.group_data_ref 

        for table_data in self.main_window.tables_data.values():
            if table_data.group_name == name_to_remove_from_dict:
                table_data.group_name = name_to_set
        
        if self.group_data_ref.graphic_item:
            self.group_data_ref.graphic_item.update() 

        self.main_window.update_window_title()
        self.main_window.populate_diagram_explorer() 

    def redo(self):
        self._apply_name(self.new_name, self.old_name)

    def undo(self):
        self._apply_name(self.old_name, self.new_name)


class ResizeGroupCommand(QUndoCommand):
    def __init__(self, main_window, group_data_ref: GroupData, old_rect: QRectF, new_rect: QRectF, description="Resize Group"):
        super().__init__(description)
        self.main_window = main_window
        self.group_data_ref = group_data_ref 
        self.old_x = old_rect.x()
        self.old_y = old_rect.y()
        self.old_width = old_rect.width()
        self.old_height = old_rect.height()
        self.new_x = new_rect.x()
        self.new_y = new_rect.y()
        self.new_width = new_rect.width()
        self.new_height = new_rect.height()
        self.table_association_changes = [] 


    def _apply_geometry_and_update_tables(self, x, y, width, height, is_redo: bool):
        if is_redo:
            self.table_association_changes.clear() 

        self.group_data_ref.x = x
        self.group_data_ref.y = y
        self.group_data_ref.width = width
        self.group_data_ref.height = height

        if self.group_data_ref.graphic_item:
            self.group_data_ref.graphic_item.prepareGeometryChange()
            self.group_data_ref.graphic_item.setPos(x, y)
            self.group_data_ref.graphic_item.setRect(0, 0, width, height) 
            self.group_data_ref.graphic_item.update()

        current_group_rect_scene = QRectF(x, y, width, height) 
        group_name_being_applied = self.group_data_ref.name

        for table_name, table_data in self.main_window.tables_data.items():
            if not table_data.graphic_item: 
                continue

            table_center_scene = table_data.graphic_item.mapToScene(table_data.graphic_item.boundingRect().center())
            is_visually_in_this_group_now = current_group_rect_scene.contains(table_center_scene)
            
            original_group_of_table = table_data.group_name 

            if is_visually_in_this_group_now:
                if original_group_of_table != group_name_being_applied:
                    if is_redo: 
                        self.table_association_changes.append((table_name, original_group_of_table, group_name_being_applied))
                    
                    if original_group_of_table and original_group_of_table in self.main_window.groups_data:
                        self.main_window.groups_data[original_group_of_table].remove_table(table_name)
                    
                    self.group_data_ref.add_table(table_name)
                    table_data.group_name = group_name_being_applied
                    if table_data.graphic_item.parentItem() != self.group_data_ref.graphic_item:
                        scene_pos = table_data.graphic_item.scenePos() 
                        table_data.graphic_item.setParentItem(self.group_data_ref.graphic_item)
                        table_data.graphic_item.setPos(self.group_data_ref.graphic_item.mapFromScene(scene_pos))
            else: 
                if original_group_of_table == group_name_being_applied: 
                    if is_redo: 
                        self.table_association_changes.append((table_name, group_name_being_applied, None))

                    self.group_data_ref.remove_table(table_name)
                    table_data.group_name = None
                    if table_data.graphic_item.parentItem() == self.group_data_ref.graphic_item:
                        scene_pos = table_data.graphic_item.mapToScene(table_data.graphic_item.pos())
                        table_data.graphic_item.setParentItem(None)
                        table_data.graphic_item.setPos(scene_pos)
        
        self.main_window.update_window_title()
        self.main_window.populate_diagram_explorer()

    def redo(self):
        self._apply_geometry_and_update_tables(self.new_x, self.new_y, self.new_width, self.new_height, is_redo=True)

    def undo(self):
        self.group_data_ref.x = self.old_x
        self.group_data_ref.y = self.old_y
        self.group_data_ref.width = self.old_width
        self.group_data_ref.height = self.old_height
        if self.group_data_ref.graphic_item:
            self.group_data_ref.graphic_item.prepareGeometryChange()
            self.group_data_ref.graphic_item.setPos(self.old_x, self.old_y)
            self.group_data_ref.graphic_item.setRect(0, 0, self.old_width, self.old_height)
            self.group_data_ref.graphic_item.update()

        for table_name, original_group, new_group_during_redo in reversed(self.table_association_changes):
            table_data = self.main_window.tables_data.get(table_name)
            if not table_data: continue

            if new_group_during_redo and new_group_during_redo in self.main_window.groups_data:
                self.main_window.groups_data[new_group_during_redo].remove_table(table_name)
            
            table_data.group_name = original_group
            if original_group and original_group in self.main_window.groups_data:
                self.main_window.groups_data[original_group].add_table(table_name)
            
            new_parent_graphic = None
            if original_group and original_group in self.main_window.groups_data:
                new_parent_graphic = self.main_window.groups_data[original_group].graphic_item
            
            if table_data.graphic_item:
                current_parent = table_data.graphic_item.parentItem()
                if current_parent != new_parent_graphic:
                    scene_pos = table_data.graphic_item.mapToScene(QPointF(0,0)) if current_parent else table_data.graphic_item.scenePos()
                    table_data.graphic_item.setParentItem(new_parent_graphic)
                    if new_parent_graphic:
                        table_data.graphic_item.setPos(new_parent_graphic.mapFromScene(scene_pos))
                    else:
                        table_data.graphic_item.setPos(scene_pos)


        self.main_window.update_window_title()
        self.main_window.populate_diagram_explorer()


class MoveGroupCommand(QUndoCommand):
    def __init__(self, main_window, group_data_ref: GroupData, old_pos: QPointF, new_pos: QPointF,
                 initial_tables_details: list[dict], description="Move Group"): 
        super().__init__(description)
        self.main_window = main_window
        self.group_data_ref = group_data_ref 
        self.old_group_scene_pos = QPointF(old_pos) 
        self.new_group_scene_pos = QPointF(new_pos) 
        
        self.delta = self.new_group_scene_pos - self.old_group_scene_pos
        self.tables_original_scene_positions = {} 
        for table_detail in initial_tables_details: 
            self.tables_original_scene_positions[table_detail["name"]] = table_detail["old_pos"]


    def _apply_group_and_children_positions(self, target_group_scene_pos: QPointF):
        self.group_data_ref.x = target_group_scene_pos.x()
        self.group_data_ref.y = target_group_scene_pos.y()
        if self.group_data_ref.graphic_item:
            self.group_data_ref.graphic_item.setPos(target_group_scene_pos) 

        current_group_graphic = self.group_data_ref.graphic_item
        if not current_group_graphic: return 

        for table_name_in_group in list(self.group_data_ref.table_names): 
            table_data = self.main_window.tables_data.get(table_name_in_group)
            if table_data and table_data.graphic_item and table_data.graphic_item.parentItem() == current_group_graphic:
                new_table_scene_pos = current_group_graphic.mapToScene(table_data.graphic_item.pos())
                
                snapped_new_table_scene_x = snap_to_grid(new_table_scene_pos.x(), constants.GRID_SIZE)
                snapped_new_table_scene_y = snap_to_grid(new_table_scene_pos.y(), constants.GRID_SIZE)
                
                table_data.x = snapped_new_table_scene_x
                table_data.y = snapped_new_table_scene_y
        
        self.main_window.update_all_relationships_graphics() 
        self.main_window.update_window_title()
        self.main_window.populate_diagram_explorer()

    def redo(self):
        self._apply_group_and_children_positions(self.new_group_scene_pos)

    def undo(self):
        self._apply_group_and_children_positions(self.old_group_scene_pos)
        for table_name, original_scene_pos in self.tables_original_scene_positions.items():
            table_data = self.main_window.tables_data.get(table_name)
            if table_data:
                table_data.x = original_scene_pos.x()
                table_data.y = original_scene_pos.y()
                # The visual position of child items is handled by Qt when parent's pos is set.
                # We only need to ensure data model's absolute coords are correct for relationships.


class SetTableGroupCommand(QUndoCommand):
    def __init__(self, main_window, table_data_ref: Table,
                 old_group_name: str | None, new_group_name: str | None,
                 description="Set Table Group"):
        super().__init__(description)
        self.main_window = main_window
        self.table_data_ref = table_data_ref 
        self.table_name = table_data_ref.name
        self.old_group_name = old_group_name
        self.new_group_name = new_group_name
        
        self.table_original_scene_x = table_data_ref.x
        self.table_original_scene_y = table_data_ref.y


    def _associate_table_with_group(self, table_name: str, target_group_name: str | None, previous_group_name: str | None):
        table_data = self.main_window.tables_data.get(table_name)
        if not table_data or not table_data.graphic_item:
            return

        table_graphic = table_data.graphic_item
        # Get current absolute scene position BEFORE any parent change
        # If it's already parented, map its local (0,0) to scene. If not, scenePos() is absolute.
        current_scene_pos = table_graphic.mapToScene(QPointF(0,0)) if table_graphic.parentItem() else table_graphic.scenePos()


        if previous_group_name and previous_group_name != target_group_name:
            prev_group_data = self.main_window.groups_data.get(previous_group_name)
            if prev_group_data and prev_group_data.graphic_item:
                prev_group_data.remove_table(table_name)
                if table_graphic.parentItem() == prev_group_data.graphic_item:
                    table_graphic.setParentItem(None) 
                    table_graphic.setPos(current_scene_pos) # Restore absolute scene position

        table_data.group_name = target_group_name
        
        if target_group_name:
            new_group_data = self.main_window.groups_data.get(target_group_name)
            if new_group_data and new_group_data.graphic_item:
                new_group_data.add_table(table_name)
                if table_graphic.parentItem() != new_group_data.graphic_item:
                    relative_pos = new_group_data.graphic_item.mapFromScene(current_scene_pos)
                    table_graphic.setParentItem(new_group_data.graphic_item) 
                    table_graphic.setPos(relative_pos) 
        else: 
            if table_graphic.parentItem() is not None:
                table_graphic.setParentItem(None) 
                table_graphic.setPos(current_scene_pos) 

        final_scene_pos = table_graphic.scenePos() if table_graphic.parentItem() is None else table_graphic.mapToScene(QPointF(0,0))
        table_data.x = final_scene_pos.x()
        table_data.y = final_scene_pos.y()
        
        self.main_window.populate_diagram_explorer()
        self.main_window.update_window_title()
        self.main_window.update_all_relationships_graphics() 


    def redo(self):
        self._associate_table_with_group(self.table_name, self.new_group_name, self.old_group_name)

    def undo(self):
        self._associate_table_with_group(self.table_name, self.old_group_name, self.new_group_name)
        if self.old_group_name is None and self.table_data_ref.graphic_item:
            self.table_data_ref.x = self.table_original_scene_x
            self.table_data_ref.y = self.table_original_scene_y
            if self.table_data_ref.graphic_item.parentItem() is None: 
                 self.table_data_ref.graphic_item.setPos(self.table_original_scene_x, self.table_original_scene_y)


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

