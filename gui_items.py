# gui_items.py
# Contains QGraphicsItem subclasses for representing tables and relationships.

import math
from PyQt6.QtWidgets import (
    QGraphicsItem, QGraphicsPathItem, QApplication, QStyle,
    QGraphicsSceneHoverEvent, QGraphicsSceneMouseEvent, QMessageBox
)
from PyQt6.QtCore import Qt, QPointF, QRectF, QSizeF
from PyQt6.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont, QPainterPath,
    QFontMetrics, QPainterPathStroker
)

from constants import (
    TABLE_HEADER_HEIGHT, COLUMN_HEIGHT, PADDING, GRID_SIZE,
    RELATIONSHIP_HANDLE_SIZE, MIN_HORIZONTAL_SEGMENT, CARDINALITY_OFFSET,
    CARDINALITY_TEXT_MARGIN, TABLE_RESIZE_HANDLE_WIDTH, MIN_TABLE_WIDTH,
    current_theme_settings
)
from utils import snap_to_grid, get_contrasting_text_color
# from commands import EditTableCommand # REMOVE THIS TOP-LEVEL IMPORT


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

    def _calculate_height(self):
        num_columns = len(self.table_data.columns)
        self.height = self.header_height + (num_columns * self.column_row_height) + self.padding
        if num_columns == 0:
             self.height = self.header_height + self.padding * 1.5

    def boundingRect(self):
        return QRectF(-TABLE_RESIZE_HANDLE_WIDTH / 2, 0, self.width + TABLE_RESIZE_HANDLE_WIDTH, self.height)


    def paint(self, painter, option, widget=None):
        self.prepareGeometryChange() 
        self._calculate_height()

        body_rect = QRectF(0, 0, self.width, self.height)
        path = QPainterPath()
        path.addRoundedRect(body_rect, self.border_radius, self.border_radius)

        body_color = self.table_data.body_color if self.table_data.body_color.isValid() else QColor(current_theme_settings["default_table_body_color"])
        header_color = self.table_data.header_color if self.table_data.header_color.isValid() else QColor(current_theme_settings["default_table_header_color"])

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
        font = QFont("Arial", 10, QFont.Weight.Bold)
        painter.setFont(font)
        text_rect_header = QRectF(0, 0, self.width, self.header_height).adjusted(self.padding / 2, 0, -self.padding / 2, 0)
        painter.drawText(text_rect_header, Qt.AlignmentFlag.AlignCenter, self.table_data.name)

        column_text_color = get_contrasting_text_color(body_color)
        painter.setPen(column_text_color)
        col_font = QFont("Arial", 9)
        painter.setFont(col_font)

        current_y = self.header_height + self.padding / 2
        line_color = QColor(current_theme_settings.get("view_border", QColor(220, 220, 220)))

        for column_idx, column in enumerate(self.table_data.columns):
            col_name_text = column.get_display_name()
            col_type_text = column.data_type

            if column_idx > 0:
                painter.setPen(QPen(line_color, 0.8))
                painter.drawLine(QPointF(self.padding / 2, current_y - self.padding / 4),
                                 QPointF(self.width - self.padding / 2, current_y - self.padding / 4))
                painter.setPen(column_text_color)

            name_rect = QRectF(self.padding, current_y,
                               self.width * 0.6 - self.padding * 1.5, self.column_row_height)
            painter.drawText(name_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, col_name_text)

            type_rect = QRectF(self.width * 0.6 - self.padding / 2, current_y,
                               self.width * 0.4 - self.padding / 2, self.column_row_height)
            painter.drawText(type_rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, col_type_text)

            current_y += self.column_row_height

        if self.isSelected():
            handle_width = TABLE_RESIZE_HANDLE_WIDTH
            handle_rect = QRectF(self.width - handle_width / 2, self.height / 2 - handle_width, handle_width, handle_width * 2)
            painter.setBrush(border_color_selected.lighter(120))
            painter.setPen(QPen(border_color_selected.darker(120), 1))
            painter.drawRoundedRect(handle_rect, 3, 3)


    def get_resize_handle_rect(self):
        return QRectF(self.width - TABLE_RESIZE_HANDLE_WIDTH, 0, TABLE_RESIZE_HANDLE_WIDTH * 2, self.height)


    def get_column_rect(self, column_index):
        if 0 <= column_index < len(self.table_data.columns):
            y_pos = self.header_height + self.padding / 2 + (column_index * self.column_row_height)
            return QRectF(0, y_pos, self.width, self.column_row_height)
        return QRectF()


    def get_attachment_point(self, other_table_graphic, from_column_name=None, to_column_name=None):
        my_rect = self.sceneBoundingRect()
        my_y = my_rect.center().y()

        if from_column_name:
            idx = self.table_data.get_column_index(from_column_name)
            if idx != -1:
                col_y_in_item = self.header_height + self.padding / 2 + (idx * self.column_row_height) + (self.column_row_height / 2)
                my_y = self.scenePos().y() + col_y_in_item

        exit_right = True
        if other_table_graphic:
            if other_table_graphic.sceneBoundingRect().center().x() < self.sceneBoundingRect().center().x():
                exit_right = False

        if self.scene() and self.scene().main_window:
            rel = None
            for r_data in self.scene().main_window.relationships_data:
                is_table1 = r_data.table1_name == self.table_data.name and r_data.fk_column_name == from_column_name
                is_table2 = r_data.table2_name == self.table_data.name and r_data.pk_column_name == from_column_name

                if is_table1 or is_table2:
                    rel = r_data
                    break

            if rel and rel.manual_bend_offset_x is not None:
                if exit_right and rel.manual_bend_offset_x < self.sceneBoundingRect().center().x():
                    exit_right = False
                elif not exit_right and rel.manual_bend_offset_x > self.sceneBoundingRect().center().x():
                    exit_right = True

        if exit_right:
            return QPointF(my_rect.right(), my_y)
        else:
            return QPointF(my_rect.left(), my_y)


    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange and self.scene():
            new_pos = QPointF(snap_to_grid(value.x(), GRID_SIZE), snap_to_grid(value.y(), GRID_SIZE))
            if new_pos != self.pos():
                self.table_data.x = new_pos.x()
                self.table_data.y = new_pos.y()
                if hasattr(self.scene(), 'update_relationships_for_table'):
                    self.scene().update_relationships_for_table(self.table_data.name)
                return new_pos
            return self.pos()

        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
             if hasattr(self.scene(), 'update_relationships_for_table'):
                 self.scene().update_relationships_for_table(self.table_data.name)

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
                     # self.scene().main_window.undo_stack.setClean(False) # Commented out
                     self.scene().main_window.update_window_title() 


            self.setCursor(Qt.CursorShape.ArrowCursor)
            if self.scene() and hasattr(self.scene(), 'update_relationships_for_table'):
                self.scene().update_relationships_for_table(self.table_data.name)
            event.accept()
            return
        super().mouseReleaseEvent(event)


    def mouseDoubleClickEvent(self, event):
        main_window = self.scene().main_window
        if not main_window: return super().mouseDoubleClickEvent(event)

        from dialogs import TableDialog 
        from data_models import Column 
        import copy 
        from commands import EditTableCommand 

        old_properties = {
            "name": self.table_data.name,
            "body_color_hex": self.table_data.body_color.name(),
            "header_color_hex": self.table_data.header_color.name(),
            "columns": copy.deepcopy(self.table_data.columns) # Deep copy for accurate comparison
        }

        dialog = TableDialog(main_window, self.table_data.name,
                             copy.deepcopy(self.table_data.columns), # Pass a deep copy to the dialog
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
                "columns": new_columns_data_list # This list is already of Column objects from dialog
            }

            name_changed = old_properties["name"] != new_properties["name"]
            body_color_changed = old_properties["body_color_hex"] != new_properties["body_color_hex"]
            header_color_changed = old_properties["header_color_hex"] != new_properties["header_color_hex"]
            
            columns_changed = False
            if len(old_properties["columns"]) != len(new_properties["columns"]):
                columns_changed = True
            else:
                # Check for content changes or order changes
                old_cols_tuples = [(c.name, c.data_type, c.is_pk, c.is_fk, c.references_table, c.references_column, c.fk_relationship_type) for c in old_properties["columns"]]
                new_cols_tuples = [(c.name, c.data_type, c.is_pk, c.is_fk, c.references_table, c.references_column, c.fk_relationship_type) for c in new_properties["columns"]]
                if old_cols_tuples != new_cols_tuples:
                    columns_changed = True
            
            if name_changed or body_color_changed or header_color_changed or columns_changed:
                command = EditTableCommand(main_window, self.table_data, old_properties, new_properties)
                main_window.undo_stack.push(command)
                # The command's redo will now handle applying all changes, including column order and content.
            else:
                print("No changes detected in table properties.")

        super().mouseDoubleClickEvent(event)

class OrthogonalRelationshipLine(QGraphicsPathItem):
    def __init__(self, relationship_data, parent=None):
        super().__init__(parent)
        self.relationship_data = relationship_data
        self.relationship_data.graphic_item = self
        self.setPen(QPen(current_theme_settings.get("relationship_line_color", QColor(70, 70, 110)), 1.8))
        self.setZValue(-1)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setAcceptHoverEvents(True)

        self._path_points = []
        self._handle_rect = QRectF()
        self._dragging_handle = False
        self._drag_start_offset = QPointF()
        self.update_tooltip_and_paint()


    def update_tooltip_and_paint(self):
        self.setToolTip(f"{self.relationship_data.table1_name}.{self.relationship_data.fk_column_name} "
                        f"({self.relationship_data.relationship_type}) "
                        f"{self.relationship_data.table2_name}.{self.relationship_data.pk_column_name}")
        self.setPen(QPen(current_theme_settings.get("relationship_line_color", QColor(70, 70, 110)), 1.8))
        self.update()


    def set_path_points(self, p1, bend1, bend2, p2):
        self.prepareGeometryChange()
        self._path_points = [p1, bend1, bend2, p2]
        path = QPainterPath()
        if not self._path_points or not all(isinstance(pt, QPointF) for pt in self._path_points) or \
           any(math.isnan(pt.x()) or math.isnan(pt.y()) for pt in self._path_points):
            self.setPath(path)
            self._handle_rect = QRectF()
            return

        path.moveTo(p1)
        path.lineTo(bend1)
        path.lineTo(bend2)
        path.lineTo(p2)
        self.setPath(path)
        self.update_handle_rect()

    def update_handle_rect(self):
        old_handle_rect = self._handle_rect
        if len(self._path_points) == 4:
            p1, bend1, bend2, p2_unused = self._path_points

            middle_segment_is_vertical = abs(bend1.x() - bend2.x()) < 0.1
            middle_segment_is_horizontal = abs(bend1.y() - bend2.y()) < 0.1

            if middle_segment_is_vertical:
                if isinstance(bend1, QPointF) and isinstance(bend2, QPointF):
                    mid_y = (bend1.y() + bend2.y()) / 2
                    self._handle_rect = QRectF(bend1.x() - RELATIONSHIP_HANDLE_SIZE / 2,
                                            mid_y - RELATIONSHIP_HANDLE_SIZE / 2,
                                            RELATIONSHIP_HANDLE_SIZE, RELATIONSHIP_HANDLE_SIZE)
                else: self._handle_rect = QRectF()
            elif middle_segment_is_horizontal:
                if isinstance(bend1, QPointF) and isinstance(bend2, QPointF):
                    mid_x = (bend1.x() + bend2.x()) / 2
                    self._handle_rect = QRectF(mid_x - RELATIONSHIP_HANDLE_SIZE / 2,
                                            bend1.y() - RELATIONSHIP_HANDLE_SIZE / 2,
                                            RELATIONSHIP_HANDLE_SIZE, RELATIONSHIP_HANDLE_SIZE)
                else: self._handle_rect = QRectF()
            else:
                 self._handle_rect = QRectF()
        else:
            self._handle_rect = QRectF()

        if old_handle_rect != self._handle_rect:
            self.prepareGeometryChange()


    def boundingRect(self):
        path_rect = self.path().boundingRect()
        margin = CARDINALITY_OFFSET + CARDINALITY_TEXT_MARGIN + 5
        expanded_rect = path_rect.adjusted(-margin, -margin, margin, margin)
        if not self._handle_rect.isNull():
            expanded_rect = expanded_rect.united(self._handle_rect)
        return expanded_rect


    def shape(self):
        path_stroker = QPainterPathStroker()
        path_stroker.setWidth(10 + CARDINALITY_TEXT_MARGIN)
        shape_path = self.path()
        if shape_path.isEmpty():
            return QPainterPath()

        shape = path_stroker.createStroke(shape_path)
        if not self._handle_rect.isNull():
            shape.addRect(self._handle_rect)

        if len(self._path_points) == 4 and all(self._path_points):
            p1 = self._path_points[0]
            p2 = self._path_points[-1]
            bend1_path = self._path_points[1]
            bend2_path = self._path_points[2]
            font = QFont("Arial", 8, QFont.Weight.Bold)
            font_metrics = QFontMetrics(font)

            rel_type = self.relationship_data.relationship_type
            card1_symbol, card2_symbol = "?", "?"

            parts = rel_type.split(':')
            if len(parts) == 2:
                card1_symbol = parts[0].strip().upper()
                card2_symbol = parts[1].strip().upper() 
            elif rel_type == "1" or rel_type == "1:1":
                card1_symbol, card2_symbol = "1", "1"
            elif rel_type == "N":
                card1_symbol, card2_symbol = "N", "1" 
            elif rel_type == "M":
                card1_symbol, card2_symbol = "M", "N" 


            text_rect1_bounds = font_metrics.boundingRect(card1_symbol)
            is_p1_exit_horizontal = abs(p1.y() - bend1_path.y()) < 0.1
            x_offset1, y_offset1 = 0, 0
            if is_p1_exit_horizontal:
                y_offset1 = -text_rect1_bounds.height() / 2
                if p1.x() < bend1_path.x():
                    x_offset1 = CARDINALITY_OFFSET
                else:
                    x_offset1 = -CARDINALITY_OFFSET - text_rect1_bounds.width()
            else:
                x_offset1 = -text_rect1_bounds.width() / 2
                if p1.y() < bend1_path.y():
                    y_offset1 = CARDINALITY_OFFSET + text_rect1_bounds.height()
                else:
                    y_offset1 = -CARDINALITY_OFFSET - text_rect1_bounds.height()

            top_left_p1 = p1 + QPointF(x_offset1, y_offset1 - text_rect1_bounds.height() / 1.5)
            size_p1 = QSizeF(text_rect1_bounds.width() * 1.5, text_rect1_bounds.height() * 1.5)
            actual_text_rect1 = QRectF(top_left_p1, size_p1)
            shape.addRect(actual_text_rect1)

            text_rect2_bounds = font_metrics.boundingRect(card2_symbol)
            is_p2_entry_horizontal = abs(p2.y() - bend2_path.y()) < 0.1 
            x_offset2, y_offset2 = 0, 0
            if is_p2_entry_horizontal:
                y_offset2 = -text_rect2_bounds.height() / 2
                if p2.x() < bend2_path.x(): 
                    x_offset2 = CARDINALITY_OFFSET
                else: 
                    x_offset2 = -CARDINALITY_OFFSET - text_rect2_bounds.width()
            else: 
                x_offset2 = -text_rect2_bounds.width() / 2
                if p2.y() < bend2_path.y(): 
                    y_offset2 = CARDINALITY_OFFSET + text_rect2_bounds.height()
                else: 
                    y_offset2 = -CARDINALITY_OFFSET - text_rect2_bounds.height()


            top_left_p2 = p2 + QPointF(x_offset2, y_offset2 - text_rect2_bounds.height() / 1.5)
            size_p2 = QSizeF(text_rect2_bounds.width() * 1.5, text_rect2_bounds.height() * 1.5)
            actual_text_rect2 = QRectF(top_left_p2, size_p2)
            shape.addRect(actual_text_rect2)

        return shape

    def paint(self, painter, option, widget=None):
        super().paint(painter, option, widget)

        if self.isSelected() and not self._handle_rect.isNull():
            painter.setBrush(QColor(current_theme_settings.get("button_checked_bg", QColor(0,123,255)).lighter(130)))
            painter.setPen(QPen(QColor(current_theme_settings.get("button_checked_border", QColor(0,86,179))), 1))
            painter.drawRect(self._handle_rect)

        if len(self._path_points) == 4 and all(isinstance(p, QPointF) and not (math.isnan(p.x()) or math.isnan(p.y())) for p in self._path_points):
            p1 = self._path_points[0]
            p2 = self._path_points[-1]
            bend1_path = self._path_points[1]
            bend2_path = self._path_points[2]

            rel_type = self.relationship_data.relationship_type
            card1_symbol, card2_symbol = "?", "?"

            parts = rel_type.split(':')
            if len(parts) == 2:
                card1_symbol = parts[0].strip().upper()
                card2_symbol = parts[1].strip().upper() 
            elif rel_type == "1" or rel_type == "1:1":
                card1_symbol, card2_symbol = "1", "1"
            elif rel_type == "N":
                card1_symbol, card2_symbol = "N", "1" 
            elif rel_type == "M":
                card1_symbol, card2_symbol = "M", "N" 


            painter.setPen(QColor(current_theme_settings["cardinality_text_color"]))
            font = QFont("Arial", 8, QFont.Weight.Bold)
            painter.setFont(font)
            font_metrics = QFontMetrics(font)

            text_rect1 = font_metrics.boundingRect(card1_symbol)
            is_p1_exit_horizontal = abs(p1.y() - bend1_path.y()) < 0.1
            x_offset1, y_offset1 = 0,0
            if is_p1_exit_horizontal:
                y_offset1 = -text_rect1.height() / 2
                if p1.x() < bend1_path.x():
                    x_offset1 = CARDINALITY_OFFSET
                else:
                    x_offset1 = -CARDINALITY_OFFSET - text_rect1.width()
            else:
                x_offset1 = -text_rect1.width() / 2
                if p1.y() < bend1_path.y():
                    y_offset1 = CARDINALITY_OFFSET + text_rect1.height()
                else:
                    y_offset1 = -CARDINALITY_OFFSET - text_rect1.height()
            painter.drawText(p1 + QPointF(x_offset1, y_offset1), card1_symbol)

            text_rect2 = font_metrics.boundingRect(card2_symbol)
            is_p2_entry_horizontal = abs(p2.y() - bend2_path.y()) < 0.1
            x_offset2, y_offset2 = 0,0
            if is_p2_entry_horizontal:
                y_offset2 = -text_rect2.height() / 2
                if p2.x() < bend2_path.x(): 
                    x_offset2 = CARDINALITY_OFFSET 
                else: 
                    x_offset2 = -CARDINALITY_OFFSET - text_rect2.width() 
            else: 
                x_offset2 = -text_rect2.width() / 2
                if p2.y() < bend2_path.y(): 
                    y_offset2 = CARDINALITY_OFFSET + text_rect2.height() 
                else: 
                    y_offset2 = -CARDINALITY_OFFSET - text_rect2.height() 
            painter.drawText(p2 + QPointF(x_offset2, y_offset2), card2_symbol)


    def hoverMoveEvent(self, event: QGraphicsSceneHoverEvent):
        if self.isSelected() and not self._handle_rect.isNull() and self._handle_rect.contains(event.pos()):
            if len(self._path_points) == 4:
                bend1 = self._path_points[1]
                bend2 = self._path_points[2]
                if abs(bend1.x() - bend2.x()) < 0.1:
                    self.setCursor(Qt.CursorShape.SizeHorCursor)
                elif abs(bend1.y() - bend2.y()) < 0.1:
                    self.setCursor(Qt.CursorShape.SizeVerCursor)
                else:
                    self.setCursor(Qt.CursorShape.ArrowCursor)
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        super().hoverMoveEvent(event)

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent):
        if self.isSelected() and not self._handle_rect.isNull() and self._handle_rect.contains(event.pos()) and event.button() == Qt.MouseButton.LeftButton:
            self._dragging_handle = True
            self._drag_start_offset = self._handle_rect.center() - event.pos()
            if len(self._path_points) == 4:
                bend1 = self._path_points[1]; bend2 = self._path_points[2]
                if abs(bend1.x() - bend2.x()) < 0.1: self.setCursor(Qt.CursorShape.SizeHorCursor)
                elif abs(bend1.y() - bend2.y()) < 0.1: self.setCursor(Qt.CursorShape.SizeVerCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent):
        if self._dragging_handle and len(self._path_points) == 4:
            new_handle_center = event.pos() + self._drag_start_offset

            bend1 = self._path_points[1]
            bend2 = self._path_points[2]

            if abs(bend1.x() - bend2.x()) < 0.1: 
                new_x = snap_to_grid(new_handle_center.x(), GRID_SIZE / 2)
                self.relationship_data.manual_bend_offset_x = new_x
                if self.scene() and hasattr(self.scene().main_window, 'update_orthogonal_path'):
                    self.scene().main_window.update_orthogonal_path(self.relationship_data)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent):
        if self._dragging_handle:
            self._dragging_handle = False
            if self.scene() and hasattr(self.scene().main_window, 'update_orthogonal_path'):
                 self.scene().main_window.update_orthogonal_path(self.relationship_data)

            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QGraphicsSceneMouseEvent):
        if self.scene() and hasattr(self.scene().main_window, 'edit_relationship_properties'):
            self.scene().main_window.edit_relationship_properties(self.relationship_data)
            event.accept()
        else:
            super().mouseDoubleClickEvent(event)
