# gui_items.py
# Version: 20250521.0020 (Corrected Cardinality Placement Logic)
# Contains QGraphicsItem subclasses for representing tables, relationships, and groups.

import math
from PyQt6.QtWidgets import (
    QGraphicsItem, QGraphicsPathItem, QApplication, QStyle,
    QGraphicsSceneHoverEvent, QGraphicsSceneMouseEvent, QMessageBox,
    QGraphicsEllipseItem, QMenu, QInputDialog, QGraphicsRectItem,
    QStyleOptionGraphicsItem
)
from PyQt6.QtCore import Qt, QPointF, QRectF, QSizeF, QLineF
from PyQt6.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont, QPainterPath,
    QFontMetrics, QPainterPathStroker, QAction, QFontDatabase
)

from constants import (
    TABLE_HEADER_HEIGHT, COLUMN_HEIGHT, PADDING, GRID_SIZE,
    RELATIONSHIP_HANDLE_SIZE, MIN_HORIZONTAL_SEGMENT, CARDINALITY_OFFSET,
    CARDINALITY_TEXT_MARGIN, TABLE_RESIZE_HANDLE_WIDTH, MIN_TABLE_WIDTH,
    current_theme_settings,
    GROUP_TITLE_AREA_HEIGHT,
    GROUP_RESIZE_HANDLE_SIZE,
    MIN_GROUP_WIDTH,
    MIN_GROUP_HEIGHT,
    GROUP_BORDER_RADIUS
)
from utils import snap_to_grid, get_contrasting_text_color
from data_models import GroupData, Table 


LINE_CLICK_PERPENDICULAR_TOLERANCE = 5 
VERTICAL_SEGMENT_HANDLE_SIZE = 8 
VERTICAL_SEGMENT_HANDLE_COLOR = QColor(0, 100, 255, 180) 
VERTICAL_SEGMENT_HIT_AREA_PADDING = 5 

class TableGraphicItem(QGraphicsItem):
    def __init__(self, table_data_object, parent=None): 
        super().__init__(parent) 
        self.table_data = table_data_object
        self.table_data.graphic_item = self
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsScenePositionChanges) 
        self.setAcceptHoverEvents(True)
        self.width = self.table_data.width
        self.header_height = TABLE_HEADER_HEIGHT
        self.column_row_height = COLUMN_HEIGHT
        self.padding = PADDING
        self.border_radius = 8
        self._calculate_height()
        
        if parent:
            relative_pos = parent.mapFromScene(QPointF(self.table_data.x, self.table_data.y))
            self.setPos(relative_pos)
        else:
            self.setPos(self.table_data.x, self.table_data.y) 

        self._resizing_width = False
        self._resize_start_x = 0
        self._initial_width_on_resize = 0
        self._old_width_for_command = 0
        self.setZValue(1) 

    def _calculate_height(self):
        num_columns = len(self.table_data.columns)
        self.height = self.header_height + (num_columns * self.column_row_height) + self.padding
        if num_columns == 0:
             self.height = self.header_height + self.padding * 1.5

    def boundingRect(self):
        return QRectF(-TABLE_RESIZE_HANDLE_WIDTH / 2, 0, self.width + TABLE_RESIZE_HANDLE_WIDTH, self.height)


    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget=None):
        self.prepareGeometryChange()
        self._calculate_height()

        body_rect = QRectF(0, 0, self.width, self.height)
        path = QPainterPath()
        path.addRoundedRect(body_rect, self.border_radius, self.border_radius)

        body_color = self.table_data.body_color if self.table_data.body_color.isValid() else QColor(current_theme_settings.get("default_table_body_color", QColor(Qt.GlobalColor.white)))
        header_color = self.table_data.header_color if self.table_data.header_color.isValid() else QColor(current_theme_settings.get("default_table_header_color", QColor(Qt.GlobalColor.lightGray)))

        painter.setBrush(QBrush(body_color))

        border_color_selected = QColor(current_theme_settings.get("button_checked_bg", QColor(0, 123, 255)))
        border_color_default = QColor(current_theme_settings.get("view_border", QColor(200,200,200)))
        border_color = border_color_selected if self.isSelected() else border_color_default
        border_width = 2.0 if self.isSelected() else 1.0
        painter.setPen(QPen(border_color, border_width))
        painter.drawPath(path)

        header_path = QPainterPath()
        header_path.addRoundedRect(QRectF(0, 0, self.width, self.header_height), self.border_radius, self.border_radius)
        rect_to_subtract = QRectF(0, self.header_height - self.border_radius, self.width, self.border_radius)
        subtraction_path = QPainterPath()
        subtraction_path.addRect(rect_to_subtract)
        header_path = header_path.subtracted(subtraction_path)

        painter.setBrush(QBrush(header_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPath(header_path)

        header_text_color = get_contrasting_text_color(header_color)
        painter.setPen(header_text_color)
        font = painter.font()
        font.setBold(True)
        font.setPointSize(10)
        painter.setFont(font)
        text_rect_header = QRectF(0, 0, self.width, self.header_height).adjusted(self.padding / 2, 0, -self.padding / 2, 0)
        painter.drawText(text_rect_header, Qt.AlignmentFlag.AlignCenter, self.table_data.name)

        column_text_color = get_contrasting_text_color(body_color)
        painter.setPen(column_text_color)
        col_font = painter.font()
        col_font.setBold(False)
        col_font.setPointSize(9)
        painter.setFont(col_font)

        current_y = self.header_height + self.padding / 2
        line_color = QColor(current_theme_settings.get("view_border", QColor(220,220,220))).lighter(110)

        for column_idx, column in enumerate(self.table_data.columns):
            col_name_text = column.get_display_name()
            col_type_text = column.data_type

            if column_idx > 0:
                painter.setPen(QPen(line_color, 0.8))
                painter.drawLine(QPointF(self.padding / 2, current_y - self.padding / 4),
                                 QPointF(self.width - self.padding / 2, current_y - self.padding / 4))
                painter.setPen(column_text_color)

            name_rect = QRectF(self.padding, current_y, self.width * 0.6 - self.padding * 1.5, self.column_row_height)
            painter.drawText(name_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, col_name_text)

            type_rect = QRectF(self.width * 0.6 - self.padding / 2, current_y, self.width * 0.4 - self.padding / 2, self.column_row_height)
            painter.drawText(type_rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, col_type_text)

            current_y += self.column_row_height

        if self.isSelected():
            handle_width = TABLE_RESIZE_HANDLE_WIDTH
            handle_rect = QRectF(self.width - handle_width / 2, self.height / 2 - handle_width, handle_width, handle_width * 2)
            painter.setBrush(border_color_selected.lighter(120))
            painter.setPen(QPen(border_color_selected.darker(120), 1))
            painter.drawRoundedRect(handle_rect, 3, 3)

    def get_resize_handle_rect(self):
        handle_width = TABLE_RESIZE_HANDLE_WIDTH
        return QRectF(self.width - handle_width, 0, handle_width * 2 , self.height)


    def get_column_rect(self, column_index: int) -> QRectF:
        if 0 <= column_index < len(self.table_data.columns):
            y_pos = self.header_height + self.padding / 2 + (column_index * self.column_row_height)
            return QRectF(0, y_pos, self.width, self.column_row_height)
        return QRectF()

    def get_attachment_point(self, other_table_graphic: QGraphicsItem | None, 
                             from_column_name: str | None = None, 
                             to_column_name: str | None = None,
                             hint_intermediate_x: float | None = None) -> QPointF: # Added hint
        my_rect_scene = self.sceneBoundingRect() 
        my_y_in_scene = my_rect_scene.center().y()

        col_name_to_use = from_column_name if from_column_name else to_column_name

        if col_name_to_use:
            idx = self.table_data.get_column_index(col_name_to_use)
            if idx != -1:
                col_y_in_item_coords = self.header_height + self.padding / 2 + (idx * self.column_row_height) + (self.column_row_height / 2)
                point_in_item = QPointF(0, col_y_in_item_coords)
                point_in_scene = self.mapToScene(point_in_item)
                my_y_in_scene = point_in_scene.y()
        
        exit_right = True 
        if hint_intermediate_x is not None:
            # If the vertical segment is to the left of my center, I should attach on my left.
            if hint_intermediate_x < my_rect_scene.center().x():
                exit_right = False
            else: # Vertical segment is to the right (or at center), attach on my right.
                exit_right = True
        elif other_table_graphic: 
            if other_table_graphic.sceneBoundingRect().center().x() < my_rect_scene.center().x():
                exit_right = False 
        
        if exit_right:
            return QPointF(my_rect_scene.right(), my_y_in_scene)
        else:
            return QPointF(my_rect_scene.left(), my_y_in_scene)

    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange and self.scene():
            new_pos_in_parent = QPointF(snap_to_grid(value.x(), GRID_SIZE), snap_to_grid(value.y(), GRID_SIZE))

            if new_pos_in_parent != self.pos():
                if not self.parentItem() and hasattr(self.scene(), 'handle_table_movement_for_groups'):
                    self.scene().handle_table_movement_for_groups(self, scene_pos_override=new_pos_in_parent, final_check=False)

                if hasattr(self.scene(), 'update_relationships_for_table'):
                    self.scene().update_relationships_for_table(self.table_data.name)
                return new_pos_in_parent 
            return self.pos() 

        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            new_scene_pos = self.scenePos() 
            snapped_new_scene_pos_x = snap_to_grid(new_scene_pos.x(), GRID_SIZE)
            snapped_new_scene_pos_y = snap_to_grid(new_scene_pos.y(), GRID_SIZE)
            
            final_snapped_scene_pos = QPointF(snapped_new_scene_pos_x, snapped_new_scene_pos_y)

            if final_snapped_scene_pos != new_scene_pos: 
                if self.parentItem():
                    self.setPos(self.parentItem().mapFromScene(final_snapped_scene_pos))
                else:
                    self.setPos(final_snapped_scene_pos)
                self.table_data.x = final_snapped_scene_pos.x()
                self.table_data.y = final_snapped_scene_pos.y()
            else: 
                self.table_data.x = new_scene_pos.x()
                self.table_data.y = new_scene_pos.y()


            if hasattr(self.scene(), 'update_relationships_for_table'):
                 self.scene().update_relationships_for_table(self.table_data.name)
            
            is_part_of_active_group_drag = False
            mouse_grabber = self.scene().mouseGrabberItem() if self.scene() else None
            if isinstance(mouse_grabber, GroupGraphicItem) and self.parentItem() == mouse_grabber:
                is_part_of_active_group_drag = True
            
            if not is_part_of_active_group_drag and hasattr(self.scene(), 'handle_table_movement_for_groups'):
                self.scene().handle_table_movement_for_groups(self, final_check=True)


        if change == QGraphicsItem.GraphicsItemChange.ItemParentHasChanged:
            if self.scene() and hasattr(self.scene(), 'update_relationships_for_table'):
                self.scene().update_relationships_for_table(self.table_data.name)
            if self.table_data: 
                current_scene_pos = self.scenePos()
                self.table_data.x = current_scene_pos.x()
                self.table_data.y = current_scene_pos.y()


        return super().itemChange(change, value)

    def hoverMoveEvent(self, event: QGraphicsSceneHoverEvent):
        if self.isSelected() and self.get_resize_handle_rect().contains(event.pos()):
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        super().hoverMoveEvent(event)

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent):
        if self.isSelected() and self.get_resize_handle_rect().contains(event.pos()) and event.button() == Qt.MouseButton.LeftButton:
            self._resizing_width = True
            self._resize_start_x = event.scenePos().x()
            self._initial_width_on_resize = self.width
            self._old_width_for_command = self.table_data.width 
            self.setCursor(Qt.CursorShape.SizeHorCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent):
        if self._resizing_width:
            delta_x = event.scenePos().x() - self._resize_start_x
            new_width = self._initial_width_on_resize + delta_x
            new_width = max(MIN_TABLE_WIDTH, snap_to_grid(new_width, GRID_SIZE))

            if self.width != new_width:
                self.prepareGeometryChange()
                self.width = new_width
                self._calculate_height()
                self.update()
                if self.scene() and hasattr(self.scene(), 'update_relationships_for_table'):
                    self.scene().update_relationships_for_table(self.table_data.name)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent):
        if self._resizing_width:
            self._resizing_width = False
            if self.table_data.width != self.width: 
                 self.table_data.width = self.width 
                 if self.scene() and self.scene().main_window:
                     self.scene().main_window.undo_stack.setClean(False) 
                     self.scene().main_window.update_window_title()


            self.setCursor(Qt.CursorShape.ArrowCursor)
            if self.scene() and hasattr(self.scene(), 'update_relationships_for_table'):
                self.scene().update_relationships_for_table(self.table_data.name)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QGraphicsSceneMouseEvent):
        main_window = self.scene().main_window if self.scene() else None
        if not main_window:
            return super().mouseDoubleClickEvent(event)

        from dialogs import TableDialog
        from data_models import Column 
        import copy
        from commands import EditTableCommand

        old_properties = {
            "name": self.table_data.name,
            "body_color_hex": self.table_data.body_color.name(),
            "header_color_hex": self.table_data.header_color.name(),
            "columns": copy.deepcopy(self.table_data.columns), 
            "group_name": self.table_data.group_name 
        }

        dialog = TableDialog(main_window, self.table_data.name,
                             copy.deepcopy(self.table_data.columns), 
                             self.table_data.body_color, self.table_data.header_color)

        if dialog.exec():
            new_name_str, new_columns_data_list, new_body_color_hex_str, new_header_color_hex_str = dialog.get_table_data()

            if not new_name_str:
                QMessageBox.warning(main_window, "Warning", "Table name cannot be empty.") 
                return

            if new_name_str != old_properties["name"] and new_name_str in main_window.tables_data:
                QMessageBox.warning(main_window, "Warning", f"Table with name '{new_name_str}' already exists.") 
                return

            new_properties = {
                "name": new_name_str,
                "body_color_hex": new_body_color_hex_str,
                "header_color_hex": new_header_color_hex_str,
                "columns": new_columns_data_list, 
                "group_name": self.table_data.group_name 
            }

            name_changed = old_properties["name"] != new_properties["name"]
            body_color_changed = old_properties["body_color_hex"] != new_properties["body_color_hex"]
            header_color_changed = old_properties["header_color_hex"] != new_properties["header_color_hex"]

            columns_changed = False
            if len(old_properties["columns"]) != len(new_properties["columns"]):
                columns_changed = True
            else:
                old_cols_tuples = sorted([(c.name, c.data_type, c.is_pk, c.is_fk, c.references_table, c.references_column, c.fk_relationship_type) for c in old_properties["columns"]])
                new_cols_tuples = sorted([(c.name, c.data_type, c.is_pk, c.is_fk, c.references_table, c.references_column, c.fk_relationship_type) for c in new_properties["columns"]])
                if old_cols_tuples != new_cols_tuples:
                    columns_changed = True
            
            if name_changed or body_color_changed or header_color_changed or columns_changed:
                command = EditTableCommand(main_window, self.table_data, old_properties, new_properties)
                main_window.undo_stack.push(command)

        event.accept()


class OrthogonalRelationshipPathItem(QGraphicsPathItem):
    def __init__(self, relationship_data, parent=None):
        super().__init__(parent)
        self.relationship_data = relationship_data
        self.relationship_data.graphic_item = self
        self.setPen(QPen(current_theme_settings.get("relationship_line_color", QColor(70, 70, 110)), 1.8))
        self.setZValue(-1) 
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setAcceptHoverEvents(True) 

        self.start_attachment_point = QPointF() 
        self.end_attachment_point = QPointF()   
        
        self.vertical_segment_handle = None 
        self.dragging_vertical_segment = False
        self._drag_start_pos_item = QPointF() 
        self.original_vertical_segment_x_scene = 0.0 

        self.update_tooltip_and_paint()

    def update_tooltip_and_paint(self):
        self.setToolTip(f"From: {self.relationship_data.table1_name}.{self.relationship_data.fk_column_name}\n"
                        f"To: {self.relationship_data.table2_name}.{self.relationship_data.pk_column_name}\n"
                        f"Type: {self.relationship_data.relationship_type}")
        line_color = QColor(current_theme_settings.get("relationship_line_color", QColor(70, 70, 110)))
        current_pen = self.pen()
        current_pen.setColor(line_color)
        self.setPen(current_pen)
        self.update() 

    def set_attachment_points(self, start_point: QPointF, end_point: QPointF):
        if self.start_attachment_point != start_point or self.end_attachment_point != end_point:
            self.prepareGeometryChange() 
            self.start_attachment_point = start_point
            self.end_attachment_point = end_point
            self._build_path()
            self._update_vertical_segment_handle_visibility() 

    def _calculate_intermediate_x_scene(self, s_point_scene: QPointF, e_point_scene: QPointF) -> float:
        if self.relationship_data.vertical_segment_x_override is not None:
            return self.relationship_data.vertical_segment_x_override

        min_h_seg = MIN_HORIZONTAL_SEGMENT
        s_exits_right_default = s_point_scene.x() < e_point_scene.x()
        
        if self.scene() and self.scene().main_window:
            table1_obj = self.scene().main_window.tables_data.get(self.relationship_data.table1_name)
            table2_obj = self.scene().main_window.tables_data.get(self.relationship_data.table2_name)
            if table1_obj and table1_obj.graphic_item and table2_obj and table2_obj.graphic_item:
                if table1_obj.graphic_item.sceneBoundingRect().center().x() > table2_obj.graphic_item.sceneBoundingRect().center().x():
                    s_exits_right_default = False
                else:
                    s_exits_right_default = True
        
        intermediate_x = 0.0
        if abs(s_point_scene.x() - e_point_scene.x()) < min_h_seg * 1.5: 
            intermediate_x = s_point_scene.x() + (min_h_seg if s_exits_right_default else -min_h_seg)
        else: 
            intermediate_x = (s_point_scene.x() + e_point_scene.x()) / 2.0
        
        return snap_to_grid(intermediate_x, GRID_SIZE / 2) 


    def _build_path(self):
        path = QPainterPath()
        s_point_scene = self.start_attachment_point
        e_point_scene = self.end_attachment_point

        if s_point_scene.isNull() or e_point_scene.isNull():
            self.setPath(path) 
            return

        s_point_item = self.mapFromScene(s_point_scene)
        e_point_item = self.mapFromScene(e_point_scene)
        path.moveTo(s_point_item)

        intermediate_x_scene = self._calculate_intermediate_x_scene(s_point_scene, e_point_scene)
        
        bend1_scene = QPointF(intermediate_x_scene, s_point_scene.y())
        bend2_scene = QPointF(intermediate_x_scene, e_point_scene.y())

        bend1_item = self.mapFromScene(bend1_scene)
        bend2_item = self.mapFromScene(bend2_scene)

        path.lineTo(bend1_item) 
        path.lineTo(bend2_item) 
        path.lineTo(e_point_item) 

        self.setPath(path)
        self._update_vertical_segment_handle_visibility() 

    def _update_vertical_segment_handle_visibility(self):
        if self.vertical_segment_handle and self.vertical_segment_handle.scene():
            self.scene().removeItem(self.vertical_segment_handle)
            self.vertical_segment_handle = None

        if self.isSelected() and not self.start_attachment_point.isNull() and not self.end_attachment_point.isNull():
            s_point_scene = self.start_attachment_point
            e_point_scene = self.end_attachment_point
            
            intermediate_x_scene = self._calculate_intermediate_x_scene(s_point_scene, e_point_scene)
            
            handle_x_scene = intermediate_x_scene
            handle_y_scene = (s_point_scene.y() + e_point_scene.y()) / 2.0 

            handle_pos_item = self.mapFromScene(QPointF(handle_x_scene, handle_y_scene))

            self.vertical_segment_handle = QGraphicsEllipseItem(
                handle_pos_item.x() - VERTICAL_SEGMENT_HANDLE_SIZE / 2,
                handle_pos_item.y() - VERTICAL_SEGMENT_HANDLE_SIZE / 2,
                VERTICAL_SEGMENT_HANDLE_SIZE, VERTICAL_SEGMENT_HANDLE_SIZE, self
            )
            self.vertical_segment_handle.setBrush(VERTICAL_SEGMENT_HANDLE_COLOR)
            self.vertical_segment_handle.setPen(QPen(VERTICAL_SEGMENT_HANDLE_COLOR.darker(120), 1))
            self.vertical_segment_handle.setZValue(self.zValue() + 1) 
            self.vertical_segment_handle.setToolTip("Drag to move the vertical segment") 
            self.vertical_segment_handle.setAcceptHoverEvents(True) 
        self.update()


    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            self._update_vertical_segment_handle_visibility()
        return super().itemChange(change, value)

    def boundingRect(self) -> QRectF:
        path_rect = self.path().boundingRect()
        if not path_rect.isValid(): 
            return QRectF()
        margin = CARDINALITY_OFFSET + CARDINALITY_TEXT_MARGIN + LINE_CLICK_PERPENDICULAR_TOLERANCE + VERTICAL_SEGMENT_HANDLE_SIZE
        return path_rect.adjusted(-margin, -margin, margin, margin)

    def shape(self) -> QPainterPath: 
        path_stroker = QPainterPathStroker()
        path_stroker.setWidth(self.pen().widthF() + LINE_CLICK_PERPENDICULAR_TOLERANCE * 2) 
        current_path = self.path()
        if current_path.isEmpty(): 
            return QPainterPath()
        
        main_shape = path_stroker.createStroke(current_path)
        if self.isSelected() and self.vertical_segment_handle:
            handle_rect_in_parent = self.vertical_segment_handle.mapRectToParent(self.vertical_segment_handle.boundingRect())
            hit_rect = handle_rect_in_parent.adjusted(-VERTICAL_SEGMENT_HIT_AREA_PADDING, -VERTICAL_SEGMENT_HIT_AREA_PADDING,
                                                      VERTICAL_SEGMENT_HIT_AREA_PADDING, VERTICAL_SEGMENT_HIT_AREA_PADDING)
            main_shape.addEllipse(hit_rect)
        return main_shape

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget=None):
        super().paint(painter, option, widget) 

        if not self.start_attachment_point.isNull() and \
           not self.end_attachment_point.isNull() and \
           self.path().elementCount() > 0: 

            s_point_scene = self.start_attachment_point
            e_point_scene = self.end_attachment_point
            
            intermediate_x_scene = self._calculate_intermediate_x_scene(s_point_scene, e_point_scene)
            
            rel_type = self.relationship_data.relationship_type
            card1_symbol, card2_symbol = "?", "?" 
            parts = rel_type.split(':')
            if len(parts) == 2:
                card1_symbol = parts[0].strip().upper()
                card2_symbol = parts[1].strip().upper()

            painter.setPen(QColor(current_theme_settings.get("cardinality_text_color", QColor(Qt.GlobalColor.black))))
            font = painter.font(); font.setBold(True); font.setPointSize(8)
            painter.setFont(font)
            font_metrics = QFontMetrics(font)

            # --- Cardinality at start_attachment_point (FK side) ---
            text_rect1 = font_metrics.boundingRect(card1_symbol)
            s_point_item = self.mapFromScene(s_point_scene) 
            text_pos1 = QPointF(s_point_item) 
            text_pos1.setY(s_point_item.y() - text_rect1.height() * 0.7) 
            
            # Determine if s_point_scene is on the left or right edge of its table
            s_point_on_left_edge = False
            if self.scene() and self.scene().main_window:
                table1_data = self.scene().main_window.tables_data.get(self.relationship_data.table1_name)
                if table1_data and table1_data.graphic_item:
                    table1_rect_scene = table1_data.graphic_item.sceneBoundingRect()
                    if abs(s_point_scene.x() - table1_rect_scene.left()) < 1.0:
                        s_point_on_left_edge = True
            
            if s_point_on_left_edge: # Attached to left edge of source table
                text_pos1.setX(s_point_item.x() - CARDINALITY_TEXT_MARGIN - text_rect1.width())
            else: # Attached to right edge of source table
                text_pos1.setX(s_point_item.x() + CARDINALITY_TEXT_MARGIN)
            painter.drawText(text_pos1, card1_symbol)

            # --- Cardinality at end_attachment_point (PK side) ---
            text_rect2 = font_metrics.boundingRect(card2_symbol)
            e_point_item = self.mapFromScene(e_point_scene) 
            text_pos2 = QPointF(e_point_item)
            text_pos2.setY(e_point_item.y() - text_rect2.height() * 0.7) 
            
            e_point_on_left_edge = False
            if self.scene() and self.scene().main_window:
                table2_data = self.scene().main_window.tables_data.get(self.relationship_data.table2_name)
                if table2_data and table2_data.graphic_item:
                    table2_rect_scene = table2_data.graphic_item.sceneBoundingRect()
                    if abs(e_point_scene.x() - table2_rect_scene.left()) < 1.0:
                        e_point_on_left_edge = True
            
            if e_point_on_left_edge: # Attached to left edge of target table
                text_pos2.setX(e_point_item.x() - CARDINALITY_TEXT_MARGIN - text_rect2.width())
            else: # Attached to right edge of target table
                text_pos2.setX(e_point_item.x() + CARDINALITY_TEXT_MARGIN)
            painter.drawText(text_pos2, card2_symbol)


    def get_vertical_segment_handle_rect_item_coords(self) -> QRectF | None:
        if self.vertical_segment_handle:
            return self.vertical_segment_handle.mapRectToParent(self.vertical_segment_handle.boundingRect())
        return None

    def hoverMoveEvent(self, event: QGraphicsSceneHoverEvent):
        if self.isSelected() and self.vertical_segment_handle:
            handle_rect_item = self.get_vertical_segment_handle_rect_item_coords()
            if handle_rect_item and handle_rect_item.adjusted(
                -VERTICAL_SEGMENT_HIT_AREA_PADDING, -VERTICAL_SEGMENT_HIT_AREA_PADDING,
                VERTICAL_SEGMENT_HIT_AREA_PADDING, VERTICAL_SEGMENT_HIT_AREA_PADDING).contains(event.pos()):
                self.setCursor(Qt.CursorShape.SizeHorCursor)
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        super().hoverMoveEvent(event)


    def mousePressEvent(self, event: QGraphicsSceneMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton and self.isSelected() and self.vertical_segment_handle:
            handle_rect_item = self.get_vertical_segment_handle_rect_item_coords()
            if handle_rect_item and handle_rect_item.adjusted(
                -VERTICAL_SEGMENT_HIT_AREA_PADDING, -VERTICAL_SEGMENT_HIT_AREA_PADDING,
                VERTICAL_SEGMENT_HIT_AREA_PADDING, VERTICAL_SEGMENT_HIT_AREA_PADDING).contains(event.pos()):
                
                self.dragging_vertical_segment = True
                self._drag_start_pos_item = event.pos() 
                self.original_vertical_segment_x_scene = self._calculate_intermediate_x_scene(
                    self.start_attachment_point, self.end_attachment_point
                )
                self.setCursor(Qt.CursorShape.SizeHorCursor)
                event.accept()
                return
        
        self.dragging_vertical_segment = False
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent):
        if self.dragging_vertical_segment and self.isSelected():
            delta_x_item = event.pos().x() - self._drag_start_pos_item.x()
            new_vertical_x_scene = self.original_vertical_segment_x_scene + delta_x_item 

            if self.relationship_data.vertical_segment_x_override != new_vertical_x_scene:
                self.relationship_data.vertical_segment_x_override = new_vertical_x_scene
                self.prepareGeometryChange()
                self._build_path() 
                self.update() 
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent):
        if self.dragging_vertical_segment and self.isSelected():
            from commands import SetRelationshipVerticalSegmentXCommand 
            main_window = self.scene().main_window if self.scene() else None
            if not main_window: 
                self.dragging_vertical_segment = False; super().mouseReleaseEvent(event); return

            current_override_x = self.relationship_data.vertical_segment_x_override
            final_snapped_x_scene = snap_to_grid(current_override_x, GRID_SIZE / 2) if current_override_x is not None else None
            self.relationship_data.vertical_segment_x_override = final_snapped_x_scene
            
            self.prepareGeometryChange()
            self._build_path()
            self.update()

            if final_snapped_x_scene != self.original_vertical_segment_x_scene: 
                command = SetRelationshipVerticalSegmentXCommand(main_window, self.relationship_data,
                                                                 self.original_vertical_segment_x_scene, 
                                                                 final_snapped_x_scene) 
                main_window.undo_stack.push(command)
            
            self.dragging_vertical_segment = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
            return
        super().mouseReleaseEvent(event)


    def mouseDoubleClickEvent(self, event: QGraphicsSceneMouseEvent):
        if self.shape().contains(event.pos()): 
            if self.scene() and hasattr(self.scene().main_window, 'edit_relationship_properties'):
                self.scene().main_window.edit_relationship_properties(self.relationship_data)
                event.accept()
                return
        super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event: QGraphicsSceneMouseEvent): 
        if not self.shape().contains(event.pos()):
            super().contextMenuEvent(event) 
            return

        menu = QMenu()
        main_win = self.scene().main_window if self.scene() else None
        if main_win: 
            menu.setStyleSheet(f"""
                QMenu {{
                    background-color: {main_win.current_theme_settings['toolbar_bg'].name()};
                    color: {main_win.current_theme_settings['text_color'].name()};
                    border: 1px solid {main_win.current_theme_settings['toolbar_border'].name()};
                }}
                QMenu::item:selected {{
                    background-color: {main_win.current_theme_settings['button_hover_bg'].name()};
                }}
            """)
        
        edit_props_action = QAction("Edit Relationship Properties...", menu) 
        edit_props_action.triggered.connect(
            lambda: main_win.edit_relationship_properties(self.relationship_data) if main_win else None
        )
        menu.addAction(edit_props_action)
        
        if self.relationship_data.vertical_segment_x_override is not None:
            reset_bend_action = QAction("Reset Vertical Line Position", menu) 
            reset_bend_action.triggered.connect(self.reset_vertical_segment_override)
            menu.addAction(reset_bend_action)

        menu.exec(event.screenPos())
        event.accept()

    def reset_vertical_segment_override(self):
        from commands import SetRelationshipVerticalSegmentXCommand 
        main_window = self.scene().main_window if self.scene() else None
        if not main_window: return

        if self.relationship_data.vertical_segment_x_override is not None:
            old_x_override = self.relationship_data.vertical_segment_x_override
            command = SetRelationshipVerticalSegmentXCommand(main_window, self.relationship_data,
                                                             old_x_override, 
                                                             None)          
            main_window.undo_stack.push(command)


class GroupGraphicItem(QGraphicsRectItem):
    def __init__(self, group_data: GroupData, parent: QGraphicsItem | None = None):
        super().__init__(parent) 
        self.group_data = group_data
        self.group_data.graphic_item = self

        self.setRect(0, 0, self.group_data.width, self.group_data.height) 
        self.setPos(self.group_data.x, self.group_data.y) 

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsScenePositionChanges, True) 
        self.setAcceptHoverEvents(True)
        self.setZValue(0) 

        self._resizing_edge = None 
        self._resize_start_mouse_pos = QPointF() 
        self._initial_rect_on_resize = QRectF()  

        self._move_start_pos_group = QPointF() 
        self.child_tables_start_scene_positions = {} 


    def get_resize_handle_rects(self) -> dict[Qt.Edge | Qt.Corner, QRectF]: 
        rect = self.rect() 
        s = GROUP_RESIZE_HANDLE_SIZE
        s_half = s / 2.0

        handles = {
            Qt.Edge.TopEdge: QRectF(rect.left() + s, rect.top() - s_half, rect.width() - 2*s, s),
            Qt.Edge.BottomEdge: QRectF(rect.left() + s, rect.bottom() - s_half, rect.width() - 2*s, s),
            Qt.Edge.LeftEdge: QRectF(rect.left() - s_half, rect.top() + s, s, rect.height() - 2*s),
            Qt.Edge.RightEdge: QRectF(rect.right() - s_half, rect.top() + s, s, rect.height() - 2*s),
            Qt.Corner.TopLeftCorner: QRectF(rect.left() - s_half, rect.top() - s_half, s, s),
            Qt.Corner.TopRightCorner: QRectF(rect.right() - s_half, rect.top() - s_half, s, s),
            Qt.Corner.BottomLeftCorner: QRectF(rect.left() - s_half, rect.bottom() - s_half, s, s),
            Qt.Corner.BottomRightCorner: QRectF(rect.right() - s_half, rect.bottom() - s_half, s, s),
        }
        return handles

    @property
    def title_area_height(self) -> float:
        return GROUP_TITLE_AREA_HEIGHT


    def get_title_rect(self) -> QRectF: 
        return QRectF(0, 0, self.rect().width(), self.title_area_height)

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget=None):
        border_color = self.group_data.border_color
        title_bg_color = self.group_data.title_bg_color
        title_text_color = self.group_data.title_text_color

        if self.isSelected():
            border_color = QColor(current_theme_settings.get("group_selected_border_color", QColor(0, 123, 255)))

        pen = QPen(border_color, 1.5, Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush) 
        main_rect_path = QPainterPath()
        main_rect_path.addRoundedRect(self.rect(), GROUP_BORDER_RADIUS, GROUP_BORDER_RADIUS)
        painter.drawPath(main_rect_path)

        title_rect = self.get_title_rect()
        title_path = QPainterPath()
        title_path.addRoundedRect(title_rect, GROUP_BORDER_RADIUS, GROUP_BORDER_RADIUS)
        rect_to_subtract = QRectF(0, title_rect.bottom() - GROUP_BORDER_RADIUS, title_rect.width(), GROUP_BORDER_RADIUS)
        subtraction_path = QPainterPath()
        subtraction_path.addRect(rect_to_subtract)
        title_path = title_path.subtracted(subtraction_path)

        painter.setBrush(QBrush(title_bg_color))
        painter.setPen(Qt.PenStyle.NoPen) 
        painter.drawPath(title_path)

        painter.setPen(title_text_color)
        font = painter.font()
        font.setBold(True)
        if "Arial" not in QFontDatabase.families():
            font.setFamily(QFontDatabase.systemFont(QFontDatabase.SystemFont.GeneralFont).family())
        else:
            font.setFamily("Arial")
        painter.setFont(font)
        text_padding = 5 
        title_text_rect = title_rect.adjusted(text_padding, text_padding / 2, -text_padding, -text_padding / 2)
        painter.drawText(title_text_rect, Qt.AlignmentFlag.AlignCenter, self.group_data.name)

        if self.isSelected():
            painter.setBrush(border_color.lighter(120)) 
            painter.setPen(QPen(border_color.darker(120), 1)) 
            for edge, handle_rect in self.get_resize_handle_rects().items():
                painter.drawRoundedRect(handle_rect, 2, 2) 


    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value):
        main_window = self.scene().main_window if self.scene() else None

        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange and self.scene() and main_window:
            for child_item in self.childItems(): 
                if isinstance(child_item, TableGraphicItem):
                    if hasattr(self.scene(), 'update_relationships_for_table'):
                        self.scene().update_relationships_for_table(child_item.table_data.name)
            return value 

        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged and main_window:
            from commands import MoveGroupCommand 

            final_snapped_group_pos = QPointF(snap_to_grid(self.pos().x(), GRID_SIZE),
                                              snap_to_grid(self.pos().y(), GRID_SIZE))
            
            if final_snapped_group_pos != self.pos(): 
                self.setPos(final_snapped_group_pos) 
            
            if not self._move_start_pos_group.isNull() and final_snapped_group_pos != self._move_start_pos_group:
                tables_original_scene_pos_details = []
                for table_name, start_scene_pos in self.child_tables_start_scene_positions.items():
                    tables_original_scene_pos_details.append({"name": table_name, "old_pos": start_scene_pos})

                command = MoveGroupCommand(main_window, self.group_data,
                                           self._move_start_pos_group, 
                                           final_snapped_group_pos,    
                                           tables_original_scene_pos_details) 
                main_window.undo_stack.push(command)
            
            self._move_start_pos_group = QPointF() 
            self.child_tables_start_scene_positions.clear()


        if change == QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            self.update() 

        return super().itemChange(change, value)

    def hoverMoveEvent(self, event: QGraphicsSceneHoverEvent):
        if not self.isSelected():
            self.setCursor(Qt.CursorShape.ArrowCursor)
            super().hoverMoveEvent(event)
            return

        self._resizing_edge = None 
        cursor_set = False
        for edge, handle_rect in self.get_resize_handle_rects().items():
            if handle_rect.contains(event.pos()): 
                self._resizing_edge = edge
                if edge == Qt.Edge.TopEdge or edge == Qt.Edge.BottomEdge:
                    self.setCursor(Qt.CursorShape.SizeVerCursor)
                elif edge == Qt.Edge.LeftEdge or edge == Qt.Edge.RightEdge:
                    self.setCursor(Qt.CursorShape.SizeHorCursor)
                elif edge == Qt.Corner.TopLeftCorner or edge == Qt.Corner.BottomRightCorner:
                    self.setCursor(Qt.CursorShape.SizeFDiagCursor)
                elif edge == Qt.Corner.TopRightCorner or edge == Qt.Corner.BottomLeftCorner:
                    self.setCursor(Qt.CursorShape.SizeBDiagCursor)
                cursor_set = True
                break
        
        if not cursor_set: 
            self.setCursor(Qt.CursorShape.ArrowCursor) 
        super().hoverMoveEvent(event)

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent):
        main_window = self.scene().main_window if self.scene() else None
        if event.button() == Qt.MouseButton.LeftButton:
            if self.isSelected() and self._resizing_edge is not None: 
                self._resize_start_mouse_pos = event.scenePos() 
                self._initial_rect_on_resize = self.sceneBoundingRect() 
                event.accept()
                return
            else: 
                self._move_start_pos_group = QPointF(snap_to_grid(self.scenePos().x(), GRID_SIZE),
                                                     snap_to_grid(self.scenePos().y(), GRID_SIZE))
                self.child_tables_start_scene_positions.clear()
                if main_window:
                    for child_item in self.childItems(): 
                        if isinstance(child_item, TableGraphicItem):
                            self.child_tables_start_scene_positions[child_item.table_data.name] = child_item.scenePos()
        
        self._resizing_edge = None 
        super().mousePressEvent(event)


    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent):
        if self._resizing_edge is not None and self.isSelected():
            current_mouse_pos_scene = event.scenePos()
            delta = current_mouse_pos_scene - self._resize_start_mouse_pos 

            new_rect_scene = QRectF(self._initial_rect_on_resize) 
            if self._resizing_edge == Qt.Edge.TopEdge or self._resizing_edge == Qt.Corner.TopLeftCorner or self._resizing_edge == Qt.Corner.TopRightCorner:
                new_rect_scene.setTop(self._initial_rect_on_resize.top() + delta.y())
            if self._resizing_edge == Qt.Edge.BottomEdge or self._resizing_edge == Qt.Corner.BottomLeftCorner or self._resizing_edge == Qt.Corner.BottomRightCorner:
                new_rect_scene.setBottom(self._initial_rect_on_resize.bottom() + delta.y())
            if self._resizing_edge == Qt.Edge.LeftEdge or self._resizing_edge == Qt.Corner.TopLeftCorner or self._resizing_edge == Qt.Corner.BottomLeftCorner:
                new_rect_scene.setLeft(self._initial_rect_on_resize.left() + delta.x())
            if self._resizing_edge == Qt.Edge.RightEdge or self._resizing_edge == Qt.Corner.TopRightCorner or self._resizing_edge == Qt.Corner.BottomRightCorner:
                new_rect_scene.setRight(self._initial_rect_on_resize.right() + delta.x())

            if new_rect_scene.width() < MIN_GROUP_WIDTH:
                if self._resizing_edge == Qt.Edge.LeftEdge or self._resizing_edge == Qt.Corner.TopLeftCorner or self._resizing_edge == Qt.Corner.BottomLeftCorner:
                    new_rect_scene.setLeft(new_rect_scene.right() - MIN_GROUP_WIDTH)
                else: 
                    new_rect_scene.setRight(new_rect_scene.left() + MIN_GROUP_WIDTH)
            
            if new_rect_scene.height() < MIN_GROUP_HEIGHT:
                if self._resizing_edge == Qt.Edge.TopEdge or self._resizing_edge == Qt.Corner.TopLeftCorner or self._resizing_edge == Qt.Corner.TopRightCorner:
                    new_rect_scene.setTop(new_rect_scene.bottom() - MIN_GROUP_HEIGHT)
                else: 
                    new_rect_scene.setBottom(new_rect_scene.top() + MIN_GROUP_HEIGHT)

            snapped_top_left_x = snap_to_grid(new_rect_scene.left(), GRID_SIZE)
            snapped_top_left_y = snap_to_grid(new_rect_scene.top(), GRID_SIZE)
            snapped_width = snap_to_grid(new_rect_scene.width(), GRID_SIZE)
            snapped_height = snap_to_grid(new_rect_scene.height(), GRID_SIZE)
            final_width = max(MIN_GROUP_WIDTH, snapped_width)
            final_height = max(MIN_GROUP_HEIGHT, snapped_height)
            
            self.prepareGeometryChange()
            self.setPos(snapped_top_left_x, snapped_top_left_y)
            self.setRect(0, 0, final_width, final_height) 

            if hasattr(self.scene(), 'handle_group_resize_visual_feedback'):
                 self.scene().handle_group_resize_visual_feedback(self) 
            self.update() 
            event.accept()
            return
        
        super().mouseMoveEvent(event) 


    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent):
        if self._resizing_edge is not None and self.isSelected(): 
            main_window = self.scene().main_window if self.scene() else None
            if main_window:
                from commands import ResizeGroupCommand 
                new_rect_scene = self.sceneBoundingRect() 
                old_rect_scene = self._initial_rect_on_resize 

                if old_rect_scene != new_rect_scene : 
                    command = ResizeGroupCommand(main_window, self.group_data, old_rect_scene, new_rect_scene)
                    main_window.undo_stack.push(command)
            
            self._resizing_edge = None
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
            return

        if self._resizing_edge is None and not self._move_start_pos_group.isNull(): 
            self.child_tables_start_scene_positions.clear() 

        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QGraphicsSceneMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton and self.get_title_rect().contains(event.pos()): 
            main_window = self.scene().main_window if self.scene() else None
            if main_window:
                from commands import RenameGroupCommand 
                current_name = self.group_data.name
                text, ok = QInputDialog.getText(main_window, "Edit Group Name", "Group Name:", 
                                                text=current_name)
                if ok and text and text.strip() != current_name:
                    new_name = text.strip()
                    if hasattr(main_window, 'groups_data') and new_name in main_window.groups_data and main_window.groups_data[new_name] is not self.group_data:
                        QMessageBox.warning(main_window, "Name Conflict", f"A group with the name '{new_name}' already exists.") 
                    else:
                        command = RenameGroupCommand(main_window, self.group_data, current_name, new_name)
                        main_window.undo_stack.push(command)
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def contains_table(self, table_item: TableGraphicItem) -> bool:
        return table_item.parentItem() == self

    def get_contained_tables(self) -> list[TableGraphicItem]: 
        contained = []
        for item in self.childItems(): 
            if isinstance(item, TableGraphicItem):
                contained.append(item)
        return contained

