# commands.py
# This file will contain QUndoCommand subclasses for implementing undo/redo functionality.

from PyQt6.QtGui import QUndoCommand, QColor
from PyQt6.QtCore import QPointF, QRectF
from data_models import Table, Column, Relationship, GroupData
from gui_items import TableGraphicItem, OrthogonalRelationshipPathItem, GroupGraphicItem
import copy
import constants # Import constants for GRID_SIZE

class AddTableCommand(QUndoCommand):
    def __init__(self, main_window, table_data, description="Add Table"):
        super().__init__(description)
        self.main_window = main_window
        self.table_data_copy = copy.deepcopy(table_data) # table_data.group_name is already set if provided
        self.table_name = table_data.name
        self.table_graphic_item_instance = table_data.graphic_item if table_data.graphic_item else None

    def redo(self):
        # print(f"Redo: Adding table '{self.table_name}'")
        self.main_window.tables_data[self.table_name] = self.table_data_copy

        if not self.table_data_copy.graphic_item or not self.table_data_copy.graphic_item.scene():
            if self.table_graphic_item_instance and not self.table_graphic_item_instance.scene():
                self.main_window.scene.addItem(self.table_graphic_item_instance)
                self.table_data_copy.graphic_item = self.table_graphic_item_instance
            else:
                self.table_graphic_item_instance = TableGraphicItem(self.table_data_copy)
                self.main_window.scene.addItem(self.table_graphic_item_instance)
                self.table_data_copy.graphic_item = self.table_graphic_item_instance
        
        if self.table_data_copy.graphic_item:
            self.table_data_copy.graphic_item.setPos(self.table_data_copy.x, self.table_data_copy.y)
            self.table_data_copy.graphic_item.update()

        if self.table_data_copy.group_name:
            group_obj = self.main_window.groups_data.get(self.table_data_copy.group_name)
            if group_obj:
                group_obj.add_table(self.table_name)

        self.main_window.update_all_relationships_graphics()
        self.main_window.update_window_title()
        self.main_window.populate_diagram_explorer()


    def undo(self):
        original_group_name_for_undo = self.table_data_copy.group_name
        if original_group_name_for_undo:
            group_obj = self.main_window.groups_data.get(original_group_name_for_undo)
            if group_obj:
                group_obj.remove_table(self.table_name)

        if self.table_name in self.main_window.tables_data:
            if not self.table_graphic_item_instance and self.main_window.tables_data[self.table_name].graphic_item:
                self.table_graphic_item_instance = self.main_window.tables_data[self.table_name].graphic_item

            table_to_remove_data = self.main_window.tables_data.pop(self.table_name)

            if self.table_graphic_item_instance and self.table_graphic_item_instance.scene():
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

            if rel_data_copy.table2_name == self.table_name: # This table was the PK side
                other_table_obj = self.main_window.tables_data.get(rel_data_copy.table1_name) # This is the FK side
                if other_table_obj:
                    fk_col = other_table_obj.get_column_by_name(rel_data_copy.fk_column_name)
                    if fk_col and fk_col.is_fk and fk_col.references_table == self.table_name:
                        is_still_fk_by_other_rel = any(
                            r.table1_name == other_table_obj.name and r.fk_column_name == fk_col.name
                            for r in self.main_window.relationships_data # Check remaining relationships
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
            if self.table_graphic_item_instance and self.table_graphic_item_instance.scene():
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
                if not self.table_graphic_item_instance.scene():
                    self.main_window.scene.addItem(self.table_graphic_item_instance)
                self.table_graphic_item_instance.setPos(self.table_data_copy.x, self.table_data_copy.y)
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
                    if old_pk_name != new_pk_name_check : is_renamed_and_still_pk = True

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
                        self.main_window.create_relationship(
                            self.table_data_object, target_table_obj,
                            col.name, col.references_column, col.fk_relationship_type,
                            initial_anchor_points=[],
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
        self.main_window.populate_diagram_explorer()
        return True


    def redo(self):
        self._apply_properties(self.new_name, self.new_body_color_hex, self.new_header_color_hex, self.new_columns_data, self.new_group_name)

    def undo(self):
        self._apply_properties(self.old_name, self.old_body_color_hex, self.old_header_color_hex, self.old_columns_data, self.old_group_name)


class AddOrthogonalBendCommand(QUndoCommand):
    def __init__(self, main_window, relationship_data_ref, insert_at_index, bend_point_A, bend_point_B, description="Add Orthogonal Bend"):
        super().__init__(description)
        self.main_window = main_window
        self.relationship_data_ref = relationship_data_ref
        self.insert_at_index = insert_at_index
        self.bend_point_A = QPointF(bend_point_A)
        self.bend_point_B = QPointF(bend_point_B)

    def redo(self):
        if 0 <= self.insert_at_index <= len(self.relationship_data_ref.anchor_points):
            self.relationship_data_ref.anchor_points.insert(self.insert_at_index, self.bend_point_A)
            self.relationship_data_ref.anchor_points.insert(self.insert_at_index + 1, self.bend_point_B)

        if self.relationship_data_ref.graphic_item:
            self.relationship_data_ref.graphic_item.prepareGeometryChange()
            self.relationship_data_ref.graphic_item._build_path()
            self.relationship_data_ref.graphic_item._update_anchor_pair_handles_visibility()
            self.relationship_data_ref.graphic_item.update()
        self.main_window.update_window_title()
        self.main_window.populate_diagram_explorer()

    def undo(self):
        if 0 <= self.insert_at_index < len(self.relationship_data_ref.anchor_points) -1 and \
           self.relationship_data_ref.anchor_points[self.insert_at_index] == self.bend_point_A and \
           self.relationship_data_ref.anchor_points[self.insert_at_index + 1] == self.bend_point_B:

            del self.relationship_data_ref.anchor_points[self.insert_at_index + 1]
            del self.relationship_data_ref.anchor_points[self.insert_at_index]

        if self.relationship_data_ref.graphic_item:
            self.relationship_data_ref.graphic_item.prepareGeometryChange()
            self.relationship_data_ref.graphic_item._build_path()
            self.relationship_data_ref.graphic_item._update_anchor_pair_handles_visibility()
            self.relationship_data_ref.graphic_item.update()
        self.main_window.update_window_title()
        self.main_window.populate_diagram_explorer()

class MoveOrthogonalBendCommand(QUndoCommand):
    def __init__(self, main_window, relationship_data_ref, bend_pair_start_index, old_pos_A, old_pos_B, new_pos_A, new_pos_B, description="Move Orthogonal Bend"):
        super().__init__(description)
        self.main_window = main_window
        self.relationship_data_ref = relationship_data_ref
        self.bend_pair_start_index = bend_pair_start_index
        self.old_pos_A = QPointF(old_pos_A)
        self.old_pos_B = QPointF(old_pos_B)
        self.new_pos_A = QPointF(new_pos_A)
        self.new_pos_B = QPointF(new_pos_B)

    def _apply_positions(self, pos_A, pos_B):
        if 0 <= self.bend_pair_start_index < len(self.relationship_data_ref.anchor_points) -1:
            self.relationship_data_ref.anchor_points[self.bend_pair_start_index] = QPointF(pos_A)
            self.relationship_data_ref.anchor_points[self.bend_pair_start_index + 1] = QPointF(pos_B)
            if self.relationship_data_ref.graphic_item:
                self.relationship_data_ref.graphic_item.prepareGeometryChange()
                self.relationship_data_ref.graphic_item._build_path()
                self.relationship_data_ref.graphic_item._update_anchor_pair_handles_visibility()
                self.relationship_data_ref.graphic_item.update()
            self.main_window.update_window_title()
            self.main_window.populate_diagram_explorer()

    def redo(self):
        self._apply_positions(self.new_pos_A, self.new_pos_B)

    def undo(self):
        self._apply_positions(self.old_pos_A, self.old_pos_B)

class DeleteOrthogonalBendCommand(QUndoCommand):
    def __init__(self, main_window, relationship_data_ref, bend_pair_start_index, deleted_pos_A, deleted_pos_B, description="Delete Orthogonal Bend"):
        super().__init__(description)
        self.main_window = main_window
        self.relationship_data_ref = relationship_data_ref
        self.bend_pair_start_index = bend_pair_start_index
        self.deleted_pos_A = QPointF(deleted_pos_A)
        self.deleted_pos_B = QPointF(deleted_pos_B)

    def redo(self):
        if 0 <= self.bend_pair_start_index < len(self.relationship_data_ref.anchor_points) -1:
            if self.relationship_data_ref.anchor_points[self.bend_pair_start_index] == self.deleted_pos_A and \
               self.relationship_data_ref.anchor_points[self.bend_pair_start_index+1] == self.deleted_pos_B:

                del self.relationship_data_ref.anchor_points[self.bend_pair_start_index + 1]
                del self.relationship_data_ref.anchor_points[self.bend_pair_start_index]

                if self.relationship_data_ref.graphic_item:
                    self.relationship_data_ref.graphic_item.prepareGeometryChange()
                    self.relationship_data_ref.graphic_item._build_path()
                    self.relationship_data_ref.graphic_item._update_anchor_pair_handles_visibility()
                    self.relationship_data_ref.graphic_item.update()
                self.main_window.update_window_title()
                self.main_window.populate_diagram_explorer()

    def undo(self):
        if 0 <= self.bend_pair_start_index <= len(self.relationship_data_ref.anchor_points):
            self.relationship_data_ref.anchor_points.insert(self.bend_pair_start_index, self.deleted_pos_A)
            self.relationship_data_ref.anchor_points.insert(self.bend_pair_start_index + 1, self.deleted_pos_B)

            if self.relationship_data_ref.graphic_item:
                self.relationship_data_ref.graphic_item.prepareGeometryChange()
                self.relationship_data_ref.graphic_item._build_path()
                self.relationship_data_ref.graphic_item._update_anchor_pair_handles_visibility()
                self.relationship_data_ref.graphic_item.update()
            self.main_window.update_window_title()
            self.main_window.populate_diagram_explorer()

class MoveCentralVerticalSegmentCommand(QUndoCommand):
    def __init__(self, main_window, relationship_data_ref, old_x_pos, new_x_pos, description="Move Central Vertical Segment"):
        super().__init__(description)
        self.main_window = main_window
        self.relationship_data_ref = relationship_data_ref
        self.old_x_pos = old_x_pos
        self.new_x_pos = new_x_pos

    def _apply_position(self, x_pos_to_apply):
        self.relationship_data_ref.central_vertical_segment_x = x_pos_to_apply

        if self.relationship_data_ref.graphic_item:
            self.relationship_data_ref.graphic_item.prepareGeometryChange()
            self.relationship_data_ref.graphic_item._build_path()
            self.relationship_data_ref.graphic_item._update_all_handles_visibility()
            self.relationship_data_ref.graphic_item.update()

        self.main_window.update_window_title()
        self.main_window.populate_diagram_explorer()

    def redo(self):
        self._apply_position(self.new_x_pos)

    def undo(self):
        self._apply_position(self.old_x_pos)


class AddGroupCommand(QUndoCommand):
    def __init__(self, main_window, group_data: GroupData, description="Add Group"):
        super().__init__(description)
        self.main_window = main_window
        self.group_data_copy = copy.deepcopy(group_data)
        self.group_name = group_data.name
        self.group_graphic_item_instance = group_data.graphic_item if group_data.graphic_item else None

    def redo(self):
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
        if self.group_name in self.main_window.groups_data:
            if not self.group_graphic_item_instance and self.main_window.groups_data[self.group_name].graphic_item:
                self.group_graphic_item_instance = self.main_window.groups_data[self.group_name].graphic_item

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

        self.contained_tables_details = []
        self.deleted_relationships_details = []
        self.affected_fk_cols_states_outside_group = []

        for table_name_in_group in group_data_to_delete.table_names:
            table_data = self.main_window.tables_data.get(table_name_in_group)
            if table_data:
                self.contained_tables_details.append({
                    "data_copy": copy.deepcopy(table_data),
                    "graphic_item": table_data.graphic_item,
                    "original_group": table_data.group_name
                })
                for rel in list(self.main_window.relationships_data):
                    if rel.table1_name == table_name_in_group or rel.table2_name == table_name_in_group:
                        if not any(d["data_copy"].table1_name == rel.table1_name and
                                   d["data_copy"].fk_column_name == rel.fk_column_name and
                                   d["data_copy"].table2_name == rel.table2_name and
                                   d["data_copy"].pk_column_name == rel.pk_column_name
                                   for d in self.deleted_relationships_details):
                            self.deleted_relationships_details.append({
                                "data_copy": copy.deepcopy(rel),
                                "graphic_item": rel.graphic_item
                            })
        
        for rel_detail in self.deleted_relationships_details:
            rel_data_copy = rel_detail["data_copy"]
            if not any(t_detail["data_copy"].name == rel_data_copy.table1_name for t_detail in self.contained_tables_details):
                fk_table_obj = self.main_window.tables_data.get(rel_data_copy.table1_name)
                if fk_table_obj:
                    fk_col_obj = fk_table_obj.get_column_by_name(rel_data_copy.fk_column_name)
                    if fk_col_obj and fk_col_obj.is_fk and fk_col_obj.references_table == rel_data_copy.table2_name:
                         self.affected_fk_cols_states_outside_group.append({
                            "table_name": fk_table_obj.name, "column_name": fk_col_obj.name,
                            "is_fk": True, "references_table": rel_data_copy.table2_name,
                            "references_column": rel_data_copy.pk_column_name,
                            "fk_relationship_type": fk_col_obj.fk_relationship_type
                        })


    def redo(self):
        for rel_detail in self.deleted_relationships_details:
            rel_data_copy = rel_detail["data_copy"]
            rel_graphic_instance = rel_detail["graphic_item"]
            if rel_graphic_instance and rel_graphic_instance.scene():
                self.main_window.scene.removeItem(rel_graphic_instance)
            live_rel = next((r for r in self.main_window.relationships_data if
                             r.table1_name == rel_data_copy.table1_name and r.fk_column_name == rel_data_copy.fk_column_name and
                             r.table2_name == rel_data_copy.table2_name and r.pk_column_name == rel_data_copy.pk_column_name), None)
            if live_rel:
                self.main_window.relationships_data.remove(live_rel)
            
            if not any(t_detail["data_copy"].name == rel_data_copy.table1_name for t_detail in self.contained_tables_details):
                fk_table_obj = self.main_window.tables_data.get(rel_data_copy.table1_name)
                if fk_table_obj:
                    fk_col = fk_table_obj.get_column_by_name(rel_data_copy.fk_column_name)
                    if fk_col and fk_col.is_fk and fk_col.references_table == rel_data_copy.table2_name:
                        is_still_fk = any(r.table1_name == fk_table_obj.name and r.fk_column_name == fk_col.name for r in self.main_window.relationships_data)
                        if not is_still_fk:
                            fk_col.is_fk = False; fk_col.references_table = None; fk_col.references_column = None
                        if fk_table_obj.graphic_item: fk_table_obj.graphic_item.update()

        for table_detail in self.contained_tables_details:
            table_copy = table_detail["data_copy"]
            table_graphic_instance = table_detail["graphic_item"]
            if table_graphic_instance and table_graphic_instance.scene():
                self.main_window.scene.removeItem(table_graphic_instance)
            if table_copy.name in self.main_window.tables_data:
                del self.main_window.tables_data[table_copy.name]
        
        if self.group_graphic_item_instance and self.group_graphic_item_instance.scene():
            self.main_window.scene.removeItem(self.group_graphic_item_instance)
        if self.group_name in self.main_window.groups_data:
            del self.main_window.groups_data[self.group_name]

        self.main_window.update_window_title()
        self.main_window.populate_diagram_explorer()
        self.main_window.scene.update()

    def undo(self):
        if self.group_name not in self.main_window.groups_data:
            self.main_window.groups_data[self.group_name] = self.group_data_copy
            if self.group_graphic_item_instance:
                self.group_data_copy.graphic_item = self.group_graphic_item_instance
                if not self.group_graphic_item_instance.scene():
                    self.main_window.scene.addItem(self.group_graphic_item_instance)
                self.group_graphic_item_instance.setPos(self.group_data_copy.x, self.group_data_copy.y)
                self.group_graphic_item_instance.setRect(0,0, self.group_data_copy.width, self.group_data_copy.height)
                self.group_graphic_item_instance.update()
        
        for table_detail in self.contained_tables_details:
            table_copy = table_detail["data_copy"]
            table_graphic_instance = table_detail["graphic_item"]
            if table_copy.name not in self.main_window.tables_data:
                self.main_window.tables_data[table_copy.name] = table_copy
                table_copy.group_name = self.group_name
                if table_graphic_instance:
                    table_copy.graphic_item = table_graphic_instance
                    if not table_graphic_instance.scene():
                        self.main_window.scene.addItem(table_graphic_instance)
                    table_graphic_instance.setPos(table_copy.x, table_copy.y)
                    table_graphic_instance.update()
        
        for fk_state in self.affected_fk_cols_states_outside_group:
            other_table_obj = self.main_window.tables_data.get(fk_state["table_name"])
            if other_table_obj:
                fk_col_obj = other_table_obj.get_column_by_name(fk_state["column_name"])
                if fk_col_obj:
                    fk_col_obj.is_fk = fk_state["is_fk"]
                    fk_col_obj.references_table = fk_state["references_table"]
                    fk_col_obj.references_column = fk_state["references_column"]
                    fk_col_obj.fk_relationship_type = fk_state["fk_relationship_type"]
                    if other_table_obj.graphic_item: other_table_obj.graphic_item.update()

        for rel_detail in self.deleted_relationships_details:
            rel_data_copy = rel_detail["data_copy"]
            rel_graphic_instance = rel_detail["graphic_item"]
            is_dup = any(r.table1_name == rel_data_copy.table1_name and r.fk_column_name == rel_data_copy.fk_column_name and \
                         r.table2_name == rel_data_copy.table2_name and r.pk_column_name == rel_data_copy.pk_column_name \
                         for r in self.main_window.relationships_data)
            if not is_dup:
                self.main_window.relationships_data.append(rel_data_copy)
            if rel_graphic_instance:
                rel_data_copy.graphic_item = rel_graphic_instance
                if not rel_graphic_instance.scene():
                    self.main_window.scene.addItem(rel_graphic_instance)
        
        self.main_window.update_all_relationships_graphics()
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

        self.old_table_group_associations = {}

    def _apply_geometry_and_update_tables(self, x, y, width, height, is_redo: bool):
        if is_redo and not self.old_table_group_associations:
            for table_name, table_data_iter in self.main_window.tables_data.items():
                self.old_table_group_associations[table_name] = table_data_iter.group_name
        
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

            table_center_scene = table_data.graphic_item.sceneBoundingRect().center()
            is_visually_in_this_group_now = current_group_rect_scene.contains(table_center_scene)
            
            original_group_for_this_table = self.old_table_group_associations.get(table_name)
            current_actual_group_of_table = table_data.group_name

            if is_visually_in_this_group_now:
                if current_actual_group_of_table != group_name_being_applied:
                    if current_actual_group_of_table and current_actual_group_of_table in self.main_window.groups_data:
                        self.main_window.groups_data[current_actual_group_of_table].remove_table(table_name)
                    
                    self.group_data_ref.add_table(table_name)
                    table_data.group_name = group_name_being_applied
            else:
                if current_actual_group_of_table == group_name_being_applied:
                    self.group_data_ref.remove_table(table_name)
                    if not is_redo:
                        table_data.group_name = original_group_for_this_table
                        if original_group_for_this_table and original_group_for_this_table in self.main_window.groups_data:
                            self.main_window.groups_data[original_group_for_this_table].add_table(table_name)
                    else:
                        table_data.group_name = None

        self.main_window.update_window_title()
        self.main_window.populate_diagram_explorer()

    def redo(self):
        self._apply_geometry_and_update_tables(self.new_x, self.new_y, self.new_width, self.new_height, is_redo=True)

    def undo(self):
        self._apply_geometry_and_update_tables(self.old_x, self.old_y, self.old_width, self.old_height, is_redo=False)


class MoveGroupCommand(QUndoCommand):
    def __init__(self, main_window, group_data_ref: GroupData, old_pos: QPointF, new_pos: QPointF,
                 initial_tables_positions: list[dict], description="Move Group"):
        super().__init__(description)
        self.main_window = main_window
        self.group_data_ref = group_data_ref
        self.old_group_pos = QPointF(old_pos)
        self.new_group_pos = QPointF(new_pos)
        
        self.delta = self.new_group_pos - self.old_group_pos

        # initial_tables_positions is expected to be a list of dicts:
        # [{"name": "TableName1", "old_pos": QPointF(x1, y1)}, ...]
        self.tables_original_details = copy.deepcopy(initial_tables_positions)
        
        # print(f"MoveGroupCommand: Init. Group: {self.group_data_ref.name}, OldPos: {self.old_group_pos}, NewPos: {self.new_group_pos}, Delta: {self.delta}")
        # print(f"  Initial table positions captured: {self.tables_original_details}")


    def _apply_positions(self, target_group_pos: QPointF, move_delta: QPointF, is_redo_phase: bool):
        # print(f"MoveGroupCommand._apply_positions: Group '{self.group_data_ref.name}' to {target_group_pos}, Delta: {move_delta}, is_redo: {is_redo_phase}")
        
        # Move the group itself
        self.group_data_ref.x = target_group_pos.x()
        self.group_data_ref.y = target_group_pos.y()
        if self.group_data_ref.graphic_item:
            self.group_data_ref.graphic_item.setPos(target_group_pos)
            # print(f"  Group '{self.group_data_ref.name}' graphic_item moved to {self.group_data_ref.graphic_item.pos()}")


        # Move associated tables
        if not self.tables_original_details:
            print(f"  Warning: No table details to move for group '{self.group_data_ref.name}'.")

        for table_detail in self.tables_original_details:
            table_name = table_detail["name"]
            original_table_pos = table_detail["old_pos"] # This is QPointF

            table_data = self.main_window.tables_data.get(table_name)
            if table_data and table_data.graphic_item:
                # print(f"  Processing table '{table_name}' from group. Original pos: {original_table_pos}")
                target_table_pos_calculated = QPointF()
                if is_redo_phase: # Moving to new position
                    target_table_pos_calculated = original_table_pos + move_delta
                    # print(f"    Redo: Table '{table_name}' new calculated pos: {target_table_pos_calculated} (orig: {original_table_pos} + delta: {move_delta})")
                else: # Undoing, move back to original table pos
                    target_table_pos_calculated = original_table_pos
                    # print(f"    Undo: Table '{table_name}' new calculated pos (reverting): {target_table_pos_calculated}")
                
                snapped_table_x = self.main_window.scene.snap_to_grid(target_table_pos_calculated.x(), constants.GRID_SIZE)
                snapped_table_y = self.main_window.scene.snap_to_grid(target_table_pos_calculated.y(), constants.GRID_SIZE)
                final_table_pos = QPointF(snapped_table_x, snapped_table_y)

                table_data.x = final_table_pos.x()
                table_data.y = final_table_pos.y()
                table_data.graphic_item.setPos(final_table_pos)
                # print(f"    Table '{table_name}' data/graphic_item moved to {final_table_pos}")
            # else:
                # print(f"  Warning: Table '{table_name}' or its graphic_item not found for moving with group.")
        
        self.main_window.update_all_relationships_graphics()
        self.main_window.update_window_title()
        self.main_window.populate_diagram_explorer()

    def redo(self):
        # print(f"Redo MoveGroupCommand: Group '{self.group_data_ref.name}' to {self.new_group_pos}")
        self._apply_positions(self.new_group_pos, self.delta, is_redo_phase=True)

    def undo(self):
        # print(f"Undo MoveGroupCommand: Group '{self.group_data_ref.name}' back to {self.old_group_pos}")
        self._apply_positions(self.old_group_pos, self.delta, is_redo_phase=False) # Delta is used to revert tables if redo was applied


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

    def _associate_table_with_group(self, table_name: str, group_name_to_set: str | None, group_name_to_remove_from: str | None):
        table_data = self.main_window.tables_data.get(table_name)
        if not table_data:
            return

        if group_name_to_remove_from:
            old_group_obj = self.main_window.groups_data.get(group_name_to_remove_from)
            if old_group_obj:
                old_group_obj.remove_table(table_name)
        
        table_data.group_name = group_name_to_set
        if group_name_to_set:
            new_group_obj = self.main_window.groups_data.get(group_name_to_set)
            if new_group_obj:
                new_group_obj.add_table(table_name)
        
        self.main_window.populate_diagram_explorer()
        self.main_window.update_window_title()


    def redo(self):
        self._associate_table_with_group(self.table_name, self.new_group_name, self.old_group_name)

    def undo(self):
        self._associate_table_with_group(self.table_name, self.old_group_name, self.new_group_name)


class CreateRelationshipCommand(QUndoCommand):
    def __init__(self, main_window, fk_table_data, pk_table_data, fk_col_name, pk_col_name, rel_type, initial_anchor_points=None, description="Create Relationship"):
        super().__init__(description)
        self.main_window = main_window
        self.fk_table_name = fk_table_data.name
        self.pk_table_name = pk_table_data.name
        self.fk_col_name = fk_col_name
        self.pk_col_name = pk_col_name
        self.rel_type = rel_type
        self.initial_anchor_points = [QPointF(p) for p in initial_anchor_points] if initial_anchor_points else []

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
            self.rel_type, self.initial_anchor_points, from_undo_redo=True
        )
        if created_rel:
            self.created_relationship_data_copy = copy.deepcopy(created_rel)

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
