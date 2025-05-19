# gui_items.py
# Version: 20250518.0602
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


ANCHOR_POINT_HANDLE_SIZE = 8
ANCHOR_POINT_HIT_AREA_PADDING = 7
INITIAL_BEND_OFFSET = GRID_SIZE * 1
LINE_CLICK_PERPENDICULAR_TOLERANCE = 5

CENTRAL_V_SEGMENT_HANDLE_SIZE = 8
CENTRAL_V_SEGMENT_HANDLE_COLOR = QColor(0, 100, 255, 180)


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

    def get_attachment_point(self, other_table_graphic: QGraphicsItem | None, from_column_name: str | None = None, to_column_name: str | None = None) -> QPointF:
        my_rect = self.sceneBoundingRect()
        my_y_in_scene = my_rect.center().y()

        col_name_to_use = from_column_name if from_column_name else to_column_name

        if col_name_to_use:
            idx = self.table_data.get_column_index(col_name_to_use)
            if idx != -1:
                col_y_in_item = self.header_height + self.padding / 2 + (idx * self.column_row_height) + (self.column_row_height / 2)
                my_y_in_scene = self.scenePos().y() + col_y_in_item
            else:
                my_y_in_scene = self.scenePos().y() + self.height / 2
        else:
            my_y_in_scene = self.scenePos().y() + self.height / 2

        exit_right = True
        if other_table_graphic:
            if other_table_graphic.sceneBoundingRect().center().x() < self.sceneBoundingRect().center().x():
                exit_right = False

        if exit_right:
            return QPointF(my_rect.right(), my_y_in_scene)
        else:
            return QPointF(my_rect.left(), my_y_in_scene)

    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange and self.scene():
            new_pos = QPointF(snap_to_grid(value.x(), GRID_SIZE), snap_to_grid(value.y(), GRID_SIZE))
            if new_pos != self.pos():
                self.table_data.x = new_pos.x()
                self.table_data.y = new_pos.y()
                if hasattr(self.scene(), 'handle_table_movement_for_groups'):
                    self.scene().handle_table_movement_for_groups(self, final_check=False)
                return new_pos
            return self.pos()

        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            if hasattr(self.scene(), 'update_relationships_for_table'):
                 self.scene().update_relationships_for_table(self.table_data.name)
            if hasattr(self.scene(), 'handle_table_movement_for_groups'):
                self.scene().handle_table_movement_for_groups(self, final_check=True)

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
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)

        self.start_attachment_point = QPointF()
        self.end_attachment_point = QPointF()

        self.anchor_pair_handles = []
        self.central_v_segment_handle = None

        self.dragging_anchor_pair_index = -1
        self.dragging_central_v_segment = False
        self._drag_start_pos_item = QPointF()
        self.original_dragged_anchor_pair_positions = []
        self.original_central_v_segment_x = 0.0

        self.update_tooltip_and_paint()

    def update_tooltip_and_paint(self):
        self.setToolTip(f"{self.relationship_data.table1_name}.{self.relationship_data.fk_column_name} ({self.relationship_data.relationship_type}) {self.relationship_data.table2_name}.{self.relationship_data.pk_column_name}")
        line_color = QColor(current_theme_settings.get("relationship_line_color", QColor(70, 70, 110)))
        current_pen = self.pen()
        current_pen.setColor(line_color)
        self.setPen(current_pen)
        self.update()

    def set_attachment_points(self, start_point: QPointF, end_point: QPointF):
        self.prepareGeometryChange()
        self.start_attachment_point = start_point
        self.end_attachment_point = end_point
        self._build_path()
        self._update_all_handles_visibility()

    def _build_path(self):
        path = QPainterPath()
        s_point = self.start_attachment_point
        e_point = self.end_attachment_point
        anchors = self.relationship_data.anchor_points

        if s_point.isNull() or e_point.isNull():
            self.setPath(path)
            return

        path.moveTo(s_point)
        current_path_point = s_point

        if not anchors:
            intermediate_x = getattr(self.relationship_data, 'central_vertical_segment_x', None)
            if intermediate_x is None:
                min_h_seg = MIN_HORIZONTAL_SEGMENT
                s_dir = 1 if e_point.x() > s_point.x() else -1
                if s_point.x() == e_point.x(): s_dir = 1

                intermediate_x1 = s_point.x() + s_dir * min_h_seg

                e_dir = 1 if s_point.x() > e_point.x() else -1
                if s_point.x() == e_point.x(): e_dir = -s_dir

                intermediate_x2 = e_point.x() + e_dir * min_h_seg

                if (s_dir == 1 and intermediate_x1 > intermediate_x2) or \
                   (s_dir == -1 and intermediate_x1 < intermediate_x2) or \
                   (s_point.x() == e_point.x()):
                     intermediate_x = (s_point.x() + e_point.x()) / 2.0
                     if s_point.x() == e_point.x():
                         intermediate_x = s_point.x() + min_h_seg / 2.0 * s_dir
                else:
                     intermediate_x = (intermediate_x1 + intermediate_x2) / 2.0

            path.lineTo(QPointF(intermediate_x, s_point.y()))
            path.lineTo(QPointF(intermediate_x, e_point.y()))
            path.lineTo(e_point)
        else:
            idx = 0
            while idx < len(anchors):
                p1_anchor = anchors[idx]
                p2_anchor = anchors[idx+1]

                path.lineTo(QPointF(p1_anchor.x(), current_path_point.y()))
                path.lineTo(p1_anchor)
                path.lineTo(p2_anchor)

                current_path_point = p2_anchor
                idx += 2

            if current_path_point.y() != e_point.y():
                 path.lineTo(QPointF(current_path_point.x(), e_point.y()))
            path.lineTo(e_point)

        self.setPath(path)


    def _update_all_handles_visibility(self):
        self._update_anchor_pair_handles_visibility()
        self._update_central_v_segment_handle_visibility()

    def _update_anchor_pair_handles_visibility(self):
        for handle in self.anchor_pair_handles:
            if handle.scene(): self.scene().removeItem(handle)
        self.anchor_pair_handles.clear()

        if self.isSelected() and self.relationship_data.anchor_points:
            i = 0
            while i + 1 < len(self.relationship_data.anchor_points):
                p1_scene = self.relationship_data.anchor_points[i]
                p2_scene = self.relationship_data.anchor_points[i+1]

                mid_point_scene = QPointF((p1_scene.x() + p2_scene.x()) / 2, (p1_scene.y() + p2_scene.y()) / 2)

                handle = QGraphicsEllipseItem(
                    self.mapFromScene(mid_point_scene).x() - ANCHOR_POINT_HANDLE_SIZE / 2,
                    self.mapFromScene(mid_point_scene).y() - ANCHOR_POINT_HANDLE_SIZE / 2,
                    ANCHOR_POINT_HANDLE_SIZE, ANCHOR_POINT_HANDLE_SIZE, self
                )
                handle.setBrush(QColor(current_theme_settings.get("button_checked_bg", QColor(0,123,255))))
                handle.setPen(QPen(QColor(current_theme_settings.get("button_checked_border", QColor(0,86,179))), 1))
                handle.setZValue(self.zValue() + 1)
                handle.setToolTip(f"Drag to move Bend Segment {i//2 + 1}. Double-click line to add new bend.")
                handle.setData(0, i)
                handle.setAcceptHoverEvents(True)
                self.anchor_pair_handles.append(handle)
                i += 2
        self.update()

    def _update_central_v_segment_handle_visibility(self):
        if self.central_v_segment_handle and self.central_v_segment_handle.scene():
            self.scene().removeItem(self.central_v_segment_handle)
            self.central_v_segment_handle = None

        if self.isSelected() and not self.relationship_data.anchor_points and \
           not self.start_attachment_point.isNull() and not self.end_attachment_point.isNull():

            s_point = self.start_attachment_point
            e_point = self.end_attachment_point

            intermediate_x = getattr(self.relationship_data, 'central_vertical_segment_x', None)
            if intermediate_x is None:
                min_h_seg = MIN_HORIZONTAL_SEGMENT
                s_dir = 1 if e_point.x() > s_point.x() else -1
                if s_point.x() == e_point.x(): s_dir = 1
                intermediate_x1 = s_point.x() + s_dir * min_h_seg
                e_dir = 1 if s_point.x() > e_point.x() else -1
                if s_point.x() == e_point.x(): e_dir = -s_dir
                intermediate_x2 = e_point.x() + e_dir * min_h_seg
                if (s_dir == 1 and intermediate_x1 > intermediate_x2) or \
                   (s_dir == -1 and intermediate_x1 < intermediate_x2) or \
                   (s_point.x() == e_point.x()):
                     intermediate_x = (s_point.x() + e_point.x()) / 2.0
                     if s_point.x() == e_point.x(): intermediate_x = s_point.x() + min_h_seg / 2.0 * s_dir
                else: intermediate_x = (intermediate_x1 + intermediate_x2) / 2.0

            handle_x_scene = intermediate_x
            handle_y_scene = (s_point.y() + e_point.y()) / 2.0

            handle_pos_item = self.mapFromScene(QPointF(handle_x_scene, handle_y_scene))

            self.central_v_segment_handle = QGraphicsEllipseItem(
                handle_pos_item.x() - CENTRAL_V_SEGMENT_HANDLE_SIZE / 2,
                handle_pos_item.y() - CENTRAL_V_SEGMENT_HANDLE_SIZE / 2,
                CENTRAL_V_SEGMENT_HANDLE_SIZE, CENTRAL_V_SEGMENT_HANDLE_SIZE, self
            )
            self.central_v_segment_handle.setBrush(CENTRAL_V_SEGMENT_HANDLE_COLOR)
            self.central_v_segment_handle.setPen(QPen(CENTRAL_V_SEGMENT_HANDLE_COLOR.darker(120), 1))
            self.central_v_segment_handle.setZValue(self.zValue() + 2)
            self.central_v_segment_handle.setToolTip("Drag to move vertical segment. Double-click line to add bends.")
            self.central_v_segment_handle.setAcceptHoverEvents(True)
        self.update()


    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            self._update_all_handles_visibility()
        return super().itemChange(change, value)

    def boundingRect(self) -> QRectF:
        path_rect = self.path().boundingRect()
        if not path_rect.isValid():
            return QRectF()
        margin = CARDINALITY_OFFSET + CARDINALITY_TEXT_MARGIN + \
                 max(ANCHOR_POINT_HANDLE_SIZE, CENTRAL_V_SEGMENT_HANDLE_SIZE) + \
                 ANCHOR_POINT_HIT_AREA_PADDING
        return path_rect.adjusted(-margin, -margin, margin, margin)

    def shape(self) -> QPainterPath:
        path_stroker = QPainterPathStroker()
        path_stroker.setWidth(self.pen().widthF() + ANCHOR_POINT_HIT_AREA_PADDING * 2.5)

        current_path = self.path()
        if current_path.isEmpty():
            return QPainterPath()

        main_shape = path_stroker.createStroke(current_path)

        if self.isSelected():
            for handle_item in self.anchor_pair_handles:
                handle_rect_in_parent = handle_item.mapRectToParent(handle_item.boundingRect())
                hit_rect = handle_rect_in_parent.adjusted(-ANCHOR_POINT_HIT_AREA_PADDING, -ANCHOR_POINT_HIT_AREA_PADDING,
                                                          ANCHOR_POINT_HIT_AREA_PADDING, ANCHOR_POINT_HIT_AREA_PADDING)
                main_shape.addEllipse(hit_rect)

            if self.central_v_segment_handle:
                handle_rect_in_parent = self.central_v_segment_handle.mapRectToParent(self.central_v_segment_handle.boundingRect())
                hit_rect = handle_rect_in_parent.adjusted(-ANCHOR_POINT_HIT_AREA_PADDING, -ANCHOR_POINT_HIT_AREA_PADDING,
                                                          ANCHOR_POINT_HIT_AREA_PADDING, ANCHOR_POINT_HIT_AREA_PADDING)
                main_shape.addEllipse(hit_rect)
        return main_shape

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget=None):
        super().paint(painter, option, widget)

        if not self.start_attachment_point.isNull() and \
           not self.end_attachment_point.isNull() and \
           self.path().elementCount() > 0:

            all_points_scene = [self.start_attachment_point] + self.relationship_data.anchor_points + [self.end_attachment_point]

            if len(all_points_scene) < 2: return

            rel_type = self.relationship_data.relationship_type
            card1_symbol, card2_symbol = "?", "?"
            parts = rel_type.split(':')
            if len(parts) == 2:
                card1_symbol = parts[0].strip().upper()
                card2_symbol = parts[1].strip().upper()

            painter.setPen(QColor(current_theme_settings.get("cardinality_text_color", QColor(Qt.GlobalColor.black))))
            font = painter.font()
            font.setBold(True)
            font.setPointSize(8)
            painter.setFont(font)
            font_metrics = QFontMetrics(font)

            first_seg_p1_scene = all_points_scene[0]
            first_seg_p2_scene = all_points_scene[1]

            first_seg_p1_item = self.mapFromScene(first_seg_p1_scene)

            text_rect1 = font_metrics.boundingRect(card1_symbol)
            dx1 = first_seg_p2_scene.x() - first_seg_p1_scene.x()
            dy1 = first_seg_p2_scene.y() - first_seg_p1_scene.y()

            text_pos1 = QPointF(first_seg_p1_item)

            if abs(dx1) > abs(dy1):
                text_pos1.setY(text_pos1.y() - text_rect1.height() * 0.7)
                if dx1 > 0: text_pos1.setX(text_pos1.x() + CARDINALITY_TEXT_MARGIN)
                else: text_pos1.setX(text_pos1.x() - CARDINALITY_TEXT_MARGIN - text_rect1.width())
            else:
                text_pos1.setX(text_pos1.x() - text_rect1.width() - CARDINALITY_TEXT_MARGIN)
                if dy1 > 0: text_pos1.setY(text_pos1.y() + CARDINALITY_TEXT_MARGIN + text_rect1.height()/2)
                else: text_pos1.setY(text_pos1.y() - CARDINALITY_TEXT_MARGIN - text_rect1.height()/2)
            painter.drawText(text_pos1, card1_symbol)

            last_seg_p1_scene = all_points_scene[-2]
            last_seg_p2_scene = all_points_scene[-1]

            last_seg_p2_item = self.mapFromScene(last_seg_p2_scene)

            text_rect2 = font_metrics.boundingRect(card2_symbol)
            dx2 = last_seg_p2_scene.x() - last_seg_p1_scene.x()
            dy2 = last_seg_p2_scene.y() - last_seg_p1_scene.y()

            text_pos2 = QPointF(last_seg_p2_item)

            if abs(dx2) > abs(dy2):
                text_pos2.setY(text_pos2.y() - text_rect2.height() * 0.7)
                if dx2 < 0: text_pos2.setX(text_pos2.x() + CARDINALITY_TEXT_MARGIN)
                else: text_pos2.setX(text_pos2.x() - CARDINALITY_TEXT_MARGIN - text_rect2.width())
            else:
                text_pos2.setX(text_pos2.x() - text_rect2.width() - CARDINALITY_TEXT_MARGIN)
                if dy2 < 0: text_pos2.setY(text_pos2.y() + CARDINALITY_TEXT_MARGIN + text_rect2.height()/2)
                else: text_pos2.setY(text_pos2.y() - CARDINALITY_TEXT_MARGIN)
            painter.drawText(text_pos2, card2_symbol)


    def get_anchor_pair_handle_at(self, pos_item: QPointF) -> int:
        for handle_item in self.anchor_pair_handles:
            handle_rect_in_parent = handle_item.mapRectToParent(handle_item.boundingRect())
            hit_rect = handle_rect_in_parent.adjusted(
                -ANCHOR_POINT_HIT_AREA_PADDING, -ANCHOR_POINT_HIT_AREA_PADDING,
                ANCHOR_POINT_HIT_AREA_PADDING, ANCHOR_POINT_HIT_AREA_PADDING
            )
            if hit_rect.contains(pos_item):
                return handle_item.data(0)
        return -1

    def get_central_v_segment_handle_rect_item_coords(self) -> QRectF | None:
        if self.central_v_segment_handle:
            return self.central_v_segment_handle.mapRectToParent(self.central_v_segment_handle.boundingRect())
        return None

    def _get_path_segments_from_definition(self, s_point: QPointF, e_point: QPointF, anchors: list[QPointF]) -> list[tuple[QPointF, QPointF]]:
        segments = []
        if s_point.isNull() or e_point.isNull(): return segments

        current_pos_scene = s_point

        if not anchors:
            intermediate_x = getattr(self.relationship_data, 'central_vertical_segment_x', None)
            if intermediate_x is None:
                min_h_seg = MIN_HORIZONTAL_SEGMENT
                s_dir = 1 if e_point.x() > s_point.x() else -1
                if s_point.x() == e_point.x(): s_dir = 1
                intermediate_x1 = s_point.x() + s_dir * min_h_seg
                e_dir = 1 if s_point.x() > e_point.x() else -1
                if s_point.x() == e_point.x(): e_dir = -s_dir
                intermediate_x2 = e_point.x() + e_dir * min_h_seg
                if (s_dir == 1 and intermediate_x1 > intermediate_x2) or \
                   (s_dir == -1 and intermediate_x1 < intermediate_x2) or \
                   (s_point.x() == e_point.x()):
                     intermediate_x = (s_point.x() + e_point.x()) / 2.0
                     if s_point.x() == e_point.x(): intermediate_x = s_point.x() + min_h_seg / 2.0 * s_dir
                else: intermediate_x = (intermediate_x1 + intermediate_x2) / 2.0

            p_h1_end_scene = QPointF(intermediate_x, s_point.y())
            p_v_end_scene = QPointF(intermediate_x, e_point.y())
            if s_point != p_h1_end_scene: segments.append((s_point, p_h1_end_scene))
            if p_h1_end_scene != p_v_end_scene: segments.append((p_h1_end_scene, p_v_end_scene))
            if p_v_end_scene != e_point: segments.append((p_v_end_scene, e_point))
        else:
            current_path_point_scene = s_point
            idx = 0
            while idx < len(anchors):
                p1_anchor_scene = anchors[idx]
                p2_anchor_scene = anchors[idx+1]

                corner1_scene = QPointF(p1_anchor_scene.x(), current_path_point_scene.y())
                if current_path_point_scene != corner1_scene: segments.append((current_path_point_scene, corner1_scene))

                if corner1_scene != p1_anchor_scene: segments.append((corner1_scene, p1_anchor_scene))

                if p1_anchor_scene != p2_anchor_scene: segments.append((p1_anchor_scene, p2_anchor_scene))

                current_path_point_scene = p2_anchor_scene
                idx += 2

            if current_path_point_scene.y() != e_point.y():
                 vertical_align_point_scene = QPointF(current_path_point_scene.x(), e_point.y())
                 segments.append((current_path_point_scene, vertical_align_point_scene))
                 current_path_point_scene = vertical_align_point_scene

            if current_path_point_scene.x() != e_point.x():
                 segments.append((current_path_point_scene, e_point))

        return segments


    def find_segment_for_new_bend(self, click_pos_item: QPointF) -> tuple[int, int, bool]:
        click_pos_scene = self.mapToScene(click_pos_item)

        reconstructed_drawn_segments_scene = self._get_path_segments_from_definition(
            self.start_attachment_point, self.end_attachment_point, self.relationship_data.anchor_points
        )

        if not reconstructed_drawn_segments_scene:
            return -1, -1, False

        closest_hit_drawn_segment_idx = -1
        min_dist_to_segment_line = float('inf')
        is_hit_segment_horizontal_orientation = False

        perp_tolerance = LINE_CLICK_PERPENDICULAR_TOLERANCE
        long_tolerance = ANCHOR_POINT_HIT_AREA_PADDING

        for i, (p1_s, p2_s) in enumerate(reconstructed_drawn_segments_scene):
            if (p1_s == p2_s): continue

            dist_to_line_projection = float('inf')
            is_current_drawn_segment_horizontal = abs(p1_s.y() - p2_s.y()) < 1e-3
            is_current_drawn_segment_vertical = abs(p1_s.x() - p2_s.x()) < 1e-3

            click_is_on_segment_projection_range = False

            if is_current_drawn_segment_horizontal:
                min_x = min(p1_s.x(), p2_s.x()); max_x = max(p1_s.x(), p2_s.x())
                if (min_x - long_tolerance <= click_pos_scene.x() <= max_x + long_tolerance):
                    dist_to_line_projection = abs(click_pos_scene.y() - p1_s.y())
                    if dist_to_line_projection < perp_tolerance:
                        click_is_on_segment_projection_range = True
            elif is_current_drawn_segment_vertical:
                min_y = min(p1_s.y(), p2_s.y()); max_y = max(p1_s.y(), p2_s.y())
                if (min_y - long_tolerance <= click_pos_scene.y() <= max_y + long_tolerance):
                    dist_to_line_projection = abs(click_pos_scene.x() - p1_s.x())
                    if dist_to_line_projection < perp_tolerance:
                        click_is_on_segment_projection_range = True
            else:
                continue

            if click_is_on_segment_projection_range:
                if dist_to_line_projection < min_dist_to_segment_line:
                    min_dist_to_segment_line = dist_to_line_projection
                    closest_hit_drawn_segment_idx = i
                    is_hit_segment_horizontal_orientation = is_current_drawn_segment_horizontal

        if closest_hit_drawn_segment_idx != -1:
            all_points_scene = [self.start_attachment_point] + self.relationship_data.anchor_points + [self.end_attachment_point]

            current_drawn_segment_counter = 0
            for logical_segment_start_idx in range(len(all_points_scene) - 1):
                p1_logical_scene = all_points_scene[logical_segment_start_idx]
                p2_logical_scene = all_points_scene[logical_segment_start_idx+1]

                num_drawn_segments_for_this_logical_segment = 0
                is_existing_anchor_bend = False
                if p1_logical_scene in self.relationship_data.anchor_points and \
                   p2_logical_scene in self.relationship_data.anchor_points:
                    try:
                        idx_p1 = self.relationship_data.anchor_points.index(p1_logical_scene)
                        if idx_p1 % 2 == 0 and idx_p1 + 1 < len(self.relationship_data.anchor_points) and \
                           self.relationship_data.anchor_points[idx_p1+1] == p2_logical_scene:
                            is_existing_anchor_bend = True
                    except ValueError: pass

                if is_existing_anchor_bend:
                    num_drawn_segments_for_this_logical_segment = 1
                else:
                    num_drawn_segments_for_this_logical_segment = 0
                    if abs(p1_logical_scene.x() - p2_logical_scene.x()) > 1e-3 : num_drawn_segments_for_this_logical_segment +=1
                    if abs(p1_logical_scene.y() - p2_logical_scene.y()) > 1e-3 : num_drawn_segments_for_this_logical_segment +=1
                    if num_drawn_segments_for_this_logical_segment == 0 and p1_logical_scene != p2_logical_scene:
                        num_drawn_segments_for_this_logical_segment = 1


                if closest_hit_drawn_segment_idx >= current_drawn_segment_counter and \
                   closest_hit_drawn_segment_idx < current_drawn_segment_counter + num_drawn_segments_for_this_logical_segment:

                    cmd_insert_idx = 0
                    if not self.relationship_data.anchor_points: # No anchors yet, new bend is first
                        cmd_insert_idx = 0
                    else:
                        # Determine insertion index based on which logical segment was hit
                        # This logic needs to be robust.
                        # If the hit segment is defined by (start_point, anchors[0]), insert at 0.
                        # If by (anchors[i], anchors[i+1]) where i is even (B_k to A_{k+1}), insert at i+2.
                        # If by (anchors[len-1], end_point), insert at len(anchors).

                        # Simplified: find which anchor pair we are "before" or "after"
                        # This is complex because a logical segment can be made of 1 or 2 drawn segments.
                        # For now, using a placeholder. This is a known area for improvement.
                        # The `insert_at_anchor_index_for_command` is the index in the `anchor_points` list.
                        # It should be an even number.
                        point_after_clicked_segment_start = reconstructed_drawn_segments_scene[closest_hit_drawn_segment_idx][0]
                        
                        temp_idx = 0
                        found = False
                        if point_after_clicked_segment_start == self.start_attachment_point:
                            cmd_insert_idx = 0
                            found = True
                        else:
                            for anchor_idx in range(0, len(self.relationship_data.anchor_points), 2):
                                # If click is on segment leading to A_k (anchors[anchor_idx])
                                # or on segment A_k to B_k (anchors[anchor_idx] to anchors[anchor_idx+1])
                                # then new bend should be inserted *before* A_k
                                if point_after_clicked_segment_start == self.relationship_data.anchor_points[anchor_idx]:
                                     cmd_insert_idx = anchor_idx
                                     found = True
                                     break
                                # If click is on segment leading to B_k (anchors[anchor_idx+1])
                                if anchor_idx + 1 < len(self.relationship_data.anchor_points):
                                    if point_after_clicked_segment_start == self.relationship_data.anchor_points[anchor_idx+1]:
                                        cmd_insert_idx = anchor_idx + 2 # Insert after this pair
                                        found = True
                                        break
                        if not found: # Clicked segment leading to end_point
                            cmd_insert_idx = len(self.relationship_data.anchor_points)


                    return logical_segment_start_idx, cmd_insert_idx, is_hit_segment_horizontal_orientation

                current_drawn_segment_counter += num_drawn_segments_for_this_logical_segment
            return -1,-1, False # Should not be reached if logic is correct
        return -1, -1, False


    def _add_orthogonal_bend(self, segment_start_idx_in_all_points: int, insert_at_anchor_index_for_command: int, p_click_item: QPointF, clicked_segment_is_horizontal: bool):
        from commands import AddOrthogonalBendCommand
        main_window = self.scene().main_window if self.scene() else None
        if not main_window: return

        p_click_scene = self.mapToScene(p_click_item)

        if not (0 <= insert_at_anchor_index_for_command <= len(self.relationship_data.anchor_points) and insert_at_anchor_index_for_command % 2 == 0):
            # print(f"Error: Invalid insert_at_anchor_index_for_command: {insert_at_anchor_index_for_command}. Must be even and within bounds.")
            # Attempt to recover or default
            if insert_at_anchor_index_for_command < 0: insert_at_anchor_index_for_command = 0
            elif insert_at_anchor_index_for_command > len(self.relationship_data.anchor_points): insert_at_anchor_index_for_command = len(self.relationship_data.anchor_points)
            if insert_at_anchor_index_for_command % 2 != 0: # If odd, make it previous even (or 0)
                insert_at_anchor_index_for_command = max(0, insert_at_anchor_index_for_command -1)


        cx_snap_scene = snap_to_grid(p_click_scene.x(), GRID_SIZE)
        cy_snap_scene = snap_to_grid(p_click_scene.y(), GRID_SIZE)

        new_anchor_A_scene = QPointF()
        new_anchor_B_scene = QPointF()

        if clicked_segment_is_horizontal:
            new_anchor_A_scene.setX(cx_snap_scene)
            new_anchor_A_scene.setY(cy_snap_scene)

            new_anchor_B_scene.setX(snap_to_grid(new_anchor_A_scene.x() + INITIAL_BEND_OFFSET, GRID_SIZE))
            new_anchor_B_scene.setY(cy_snap_scene)

            if new_anchor_B_scene.x() == new_anchor_A_scene.x():
                new_anchor_B_scene.setX(new_anchor_A_scene.x() + GRID_SIZE)
        else:
            new_anchor_A_scene.setX(cx_snap_scene)
            new_anchor_A_scene.setY(cy_snap_scene)

            new_anchor_B_scene.setX(cx_snap_scene)
            new_anchor_B_scene.setY(snap_to_grid(new_anchor_A_scene.y() + INITIAL_BEND_OFFSET, GRID_SIZE))

            if new_anchor_B_scene.y() == new_anchor_A_scene.y():
                new_anchor_B_scene.setY(new_anchor_A_scene.y() + GRID_SIZE)

        command = AddOrthogonalBendCommand(main_window, self.relationship_data,
                                           insert_at_anchor_index_for_command,
                                           new_anchor_A_scene, new_anchor_B_scene)
        main_window.undo_stack.push(command)

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton and self.isSelected():
            if not self.relationship_data.anchor_points and self.central_v_segment_handle:
                handle_rect_item = self.get_central_v_segment_handle_rect_item_coords()
                if handle_rect_item and \
                   handle_rect_item.adjusted(-ANCHOR_POINT_HIT_AREA_PADDING, -ANCHOR_POINT_HIT_AREA_PADDING,
                                             ANCHOR_POINT_HIT_AREA_PADDING, ANCHOR_POINT_HIT_AREA_PADDING).contains(event.pos()):
                    self.dragging_central_v_segment = True
                    self._drag_start_pos_item = event.pos()
                    self.original_central_v_segment_x = getattr(self.relationship_data, 'central_vertical_segment_x',
                                                               (self.start_attachment_point.x() + self.end_attachment_point.x()) / 2.0)
                    event.accept(); return

            clicked_anchor_pair_start_idx = self.get_anchor_pair_handle_at(event.pos())
            if clicked_anchor_pair_start_idx != -1:
                self.dragging_anchor_pair_index = clicked_anchor_pair_start_idx
                self.original_dragged_anchor_pair_positions = [
                    QPointF(self.relationship_data.anchor_points[self.dragging_anchor_pair_index]),
                    QPointF(self.relationship_data.anchor_points[self.dragging_anchor_pair_index + 1])
                ]
                self._drag_start_pos_item = event.pos()
                event.accept(); return

        self.dragging_anchor_pair_index = -1
        self.dragging_central_v_segment = False
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent):
        if self.dragging_central_v_segment and self.isSelected():
            delta_x_item = event.pos().x() - self._drag_start_pos_item.x()
            new_central_x_scene = snap_to_grid(self.original_central_v_segment_x + delta_x_item, GRID_SIZE)

            if getattr(self.relationship_data, 'central_vertical_segment_x', None) != new_central_x_scene:
                self.relationship_data.central_vertical_segment_x = new_central_x_scene
                self.prepareGeometryChange()
                self._build_path()
                self._update_all_handles_visibility()
                self.update()
            event.accept(); return

        elif self.dragging_anchor_pair_index != -1 and self.isSelected():
            if not (0 <= self.dragging_anchor_pair_index < len(self.relationship_data.anchor_points) - 1):
                self.dragging_anchor_pair_index = -1; super().mouseMoveEvent(event); return

            original_A_scene = self.original_dragged_anchor_pair_positions[0]
            original_B_scene = self.original_dragged_anchor_pair_positions[1]

            is_bend_segment_horizontal = abs(original_A_scene.y() - original_B_scene.y()) < 1e-3
            is_bend_segment_vertical = abs(original_A_scene.x() - original_B_scene.x()) < 1e-3

            delta_item = event.pos() - self._drag_start_pos_item

            new_A_scene = QPointF(original_A_scene)
            new_B_scene = QPointF(original_B_scene)

            if is_bend_segment_horizontal:
                new_y_scene = snap_to_grid(original_A_scene.y() + delta_item.y(), GRID_SIZE)
                new_A_scene.setY(new_y_scene)
                new_B_scene.setY(new_y_scene)
            elif is_bend_segment_vertical:
                new_x_scene = snap_to_grid(original_A_scene.x() + delta_item.x(), GRID_SIZE)
                new_A_scene.setX(new_x_scene)
                new_B_scene.setX(new_x_scene)
            else:
                super().mouseMoveEvent(event); return

            self.relationship_data.anchor_points[self.dragging_anchor_pair_index] = new_A_scene
            self.relationship_data.anchor_points[self.dragging_anchor_pair_index + 1] = new_B_scene

            self.prepareGeometryChange()
            self._build_path()
            self._update_all_handles_visibility()
            self.update()
            event.accept(); return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent):
        if self.dragging_central_v_segment and self.isSelected():
            from commands import MoveCentralVerticalSegmentCommand
            main_window = self.scene().main_window if self.scene() else None
            if not main_window:
                self.dragging_central_v_segment = False; super().mouseReleaseEvent(event); return

            new_x_scene = self.relationship_data.central_vertical_segment_x
            if self.original_central_v_segment_x != new_x_scene:
                command = MoveCentralVerticalSegmentCommand(main_window, self.relationship_data,
                                                            self.original_central_v_segment_x, new_x_scene)
                main_window.undo_stack.push(command)

            self.dragging_central_v_segment = False
            event.accept(); return

        elif self.dragging_anchor_pair_index != -1 and self.isSelected():
            from commands import MoveOrthogonalBendCommand
            main_window = self.scene().main_window if self.scene() else None
            if not main_window:
                self.dragging_anchor_pair_index = -1; super().mouseReleaseEvent(event); return

            old_A_scene = self.original_dragged_anchor_pair_positions[0]
            old_B_scene = self.original_dragged_anchor_pair_positions[1]
            new_A_scene = QPointF(self.relationship_data.anchor_points[self.dragging_anchor_pair_index])
            new_B_scene = QPointF(self.relationship_data.anchor_points[self.dragging_anchor_pair_index + 1])

            if old_A_scene != new_A_scene or old_B_scene != new_B_scene:
                command = MoveOrthogonalBendCommand(main_window, self.relationship_data,
                                                    self.dragging_anchor_pair_index,
                                                    old_A_scene, old_B_scene, new_A_scene, new_B_scene)
                main_window.undo_stack.push(command)

            self.dragging_anchor_pair_index = -1
            self.original_dragged_anchor_pair_positions = []
            event.accept(); return

        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QGraphicsSceneMouseEvent):
        if not self.isSelected() or event.button() != Qt.MouseButton.LeftButton:
            if self.shape().contains(event.pos()):
                event.accept()
            else:
                super().mouseDoubleClickEvent(event)
            return

        clicked_anchor_handle_idx = self.get_anchor_pair_handle_at(event.pos())
        if clicked_anchor_handle_idx != -1:
            event.accept(); return

        if not self.relationship_data.anchor_points and self.central_v_segment_handle:
            central_handle_rect_item = self.get_central_v_segment_handle_rect_item_coords()
            if central_handle_rect_item and \
               central_handle_rect_item.adjusted(-ANCHOR_POINT_HIT_AREA_PADDING, -ANCHOR_POINT_HIT_AREA_PADDING,
                                                 ANCHOR_POINT_HIT_AREA_PADDING, ANCHOR_POINT_HIT_AREA_PADDING).contains(event.pos()):
                event.accept(); return

        if self.shape().contains(event.pos()):
            logical_seg_start_idx, insert_idx_for_cmd, is_hit_segment_h = self.find_segment_for_new_bend(event.pos())

            if logical_seg_start_idx != -1 and insert_idx_for_cmd != -1:
                self._add_orthogonal_bend(logical_seg_start_idx, insert_idx_for_cmd, event.pos(), is_hit_segment_h)
                event.accept(); return

        event.accept()

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

        actions_added = False
        if self.isSelected():
            clicked_anchor_pair_start_idx = self.get_anchor_pair_handle_at(event.pos())
            if clicked_anchor_pair_start_idx != -1:
                delete_bend_action = QAction(f"Delete Bend {clicked_anchor_pair_start_idx//2 + 1}", menu)
                delete_bend_action.triggered.connect(
                    lambda checked=False, idx=clicked_anchor_pair_start_idx: self.delete_orthogonal_bend(idx)
                )
                menu.addAction(delete_bend_action)
                actions_added = True
            else:
                add_bend_action = QAction("Add Orthogonal Bend", menu)
                logical_seg_idx, cmd_insert_idx, is_hit_h = self.find_segment_for_new_bend(event.pos())
                if logical_seg_idx != -1 and cmd_insert_idx != -1:
                    add_bend_action.triggered.connect(
                        lambda checked=False, s_idx=logical_seg_idx, i_idx=cmd_insert_idx, c_pos=event.pos(), h_orient=is_hit_h: \
                        self._add_orthogonal_bend(s_idx, i_idx, c_pos, h_orient)
                    )
                    menu.addAction(add_bend_action)
                    actions_added = True

        edit_props_action = QAction("Edit Relationship Properties...", menu)
        edit_props_action.triggered.connect(
            lambda: main_win.edit_relationship_properties(self.relationship_data) if main_win else None
        )
        menu.addAction(edit_props_action)
        actions_added = True

        if actions_added:
            menu.exec(event.screenPos())
        event.accept()

    def delete_orthogonal_bend(self, pair_start_index_in_anchors: int):
        from commands import DeleteOrthogonalBendCommand
        main_window = self.scene().main_window if self.scene() else None
        if not main_window: return

        if 0 <= pair_start_index_in_anchors < len(self.relationship_data.anchor_points) - 1:
            deleted_A_scene = QPointF(self.relationship_data.anchor_points[pair_start_index_in_anchors])
            deleted_B_scene = QPointF(self.relationship_data.anchor_points[pair_start_index_in_anchors + 1])

            command = DeleteOrthogonalBendCommand(main_window, self.relationship_data,
                                                  pair_start_index_in_anchors,
                                                  deleted_A_scene, deleted_B_scene)
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
        self._initial_table_positions_on_move = {}


    def get_resize_handle_rects(self) -> dict[Qt.Edge, QRectF]:
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

        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange and self.scene():
            pass # Visual move handled by Qt, command created on ItemPositionHasChanged

        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged and main_window:
            from commands import MoveGroupCommand
            current_pos_snapped = QPointF(snap_to_grid(self.pos().x(), GRID_SIZE),
                                          snap_to_grid(self.pos().y(), GRID_SIZE))

            if current_pos_snapped != self.pos():
                self.setPos(current_pos_snapped)

            if self._move_start_pos_group.isNull() or current_pos_snapped == self._move_start_pos_group:
                self._move_start_pos_group = QPointF()
                self._initial_table_positions_on_move.clear()
            else:
                tables_to_move_details = []
                # Use the stored initial positions, not current ones which might have already moved with group
                for table_name, old_table_scene_pos in self._initial_table_positions_on_move.items():
                    tables_to_move_details.append({"name": table_name, "old_pos": old_table_scene_pos})
                
                command = MoveGroupCommand(main_window, self.group_data,
                                           self._move_start_pos_group, current_pos_snapped,
                                           tables_to_move_details)
                main_window.undo_stack.push(command)
                
                self._move_start_pos_group = QPointF()
                self._initial_table_positions_on_move.clear()

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
                # Store current (snapped) SCENE position as the start of a potential move
                self._move_start_pos_group = QPointF(snap_to_grid(self.scenePos().x(), GRID_SIZE),
                                                     snap_to_grid(self.scenePos().y(), GRID_SIZE))
                self._initial_table_positions_on_move.clear()
                if main_window and hasattr(main_window, 'tables_data'):
                    for table_name_in_group in list(self.group_data.table_names): # Iterate over a copy
                        table_data = main_window.tables_data.get(table_name_in_group)
                        if table_data and table_data.graphic_item:
                            # Store the SCENE position of the table
                            self._initial_table_positions_on_move[table_name_in_group] = QPointF(table_data.graphic_item.scenePos())
        
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
            self._move_start_pos_group = QPointF()
            self._initial_table_positions_on_move.clear()

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
        table_scene_rect = table_item.sceneBoundingRect()
        group_scene_rect = self.sceneBoundingRect()
        return group_scene_rect.contains(table_scene_rect.center())

    def get_contained_tables(self) -> list[TableGraphicItem]:
        contained = []
        if not self.scene():
            return contained

        group_scene_rect = self.sceneBoundingRect()
        for item in self.scene().items(group_scene_rect, Qt.ItemSelectionMode.IntersectsItemBoundingRect):
            if isinstance(item, TableGraphicItem) and item is not self:
                if group_scene_rect.contains(item.sceneBoundingRect().center()):
                    contained.append(item)
        return contained
