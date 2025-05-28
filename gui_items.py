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

import constants # Import the constants module
from constants import (
    TABLE_HEADER_HEIGHT, COLUMN_HEIGHT, PADDING, GRID_SIZE, show_cardinality_text_globally, show_cardinality_symbols_globally,
    RELATIONSHIP_HANDLE_SIZE, MIN_HORIZONTAL_SEGMENT, SYMBOL_OFFSET_FROM_TABLE_EDGE, 
    CROWS_FOOT_LINE_LENGTH, CROWS_FOOT_ANGLE_DEG, SYMBOL_STROKE_WIDTH, CARDINALITY_OFFSET,
    CARDINALITY_TEXT_MARGIN, TABLE_RESIZE_HANDLE_WIDTH, MIN_TABLE_WIDTH, current_theme_settings
)
from utils import snap_to_grid, get_contrasting_text_color
from data_models import Table 


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
            "columns": copy.deepcopy(self.table_data.columns)
        }

        dialog = TableDialog(main_window, self.table_data.name,
                             copy.deepcopy(self.table_data.columns), 
                             self.table_data.body_color, self.table_data.header_color)

        if dialog.exec():
            # קבלת כל הנתונים מהדיאלוג, כולל צבעים מותאמים אישית חדשים
            new_name_str, new_columns_data_list, new_body_color_hex_str, new_header_color_hex_str, newly_picked_custom_colors_set = dialog.get_table_data()

            # טיפול בצבעים מותאמים אישית חדשים שנבחרו
            if newly_picked_custom_colors_set:
                made_changes_to_global_custom_list = False
                current_saved_hex = {c.name() for c in constants.user_saved_custom_colors}
                basic_hex = {QColor(bc).name() for bc in constants.BASIC_COLORS_HEX}
                for color_hex in newly_picked_custom_colors_set:
                    if color_hex not in current_saved_hex and color_hex not in basic_hex:
                        constants.user_saved_custom_colors.append(QColor(color_hex))
                        made_changes_to_global_custom_list = True
                if made_changes_to_global_custom_list:
                    constants.user_saved_custom_colors = constants.user_saved_custom_colors[-constants.MAX_SAVED_CUSTOM_COLORS:]
                    main_window.save_app_settings()

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
                "columns": new_columns_data_list
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

    def contextMenuEvent(self, event: QGraphicsSceneMouseEvent):
        main_window = self.scene().main_window if self.scene() else None
        if not main_window:
            super().contextMenuEvent(event)
            return

        menu = QMenu()
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {main_window.current_theme_settings['toolbar_bg'].name()};
                color: {main_window.current_theme_settings['text_color'].name()};
                border: 1px solid {main_window.current_theme_settings['toolbar_border'].name()};
            }}
            QMenu::item:selected {{
                background-color: {main_window.current_theme_settings['button_hover_bg'].name()};
            }}
        """)

        edit_action = QAction("Edit Table...", menu)
        edit_action.triggered.connect(lambda: self.mouseDoubleClickEvent(event)) # Reuse double-click logic
        menu.addAction(edit_action)

        copy_action = QAction("Copy Table", menu)
        copy_action.triggered.connect(self.request_copy_table)
        menu.addAction(copy_action)

        delete_action = QAction("Delete Table", menu)
        delete_action.triggered.connect(self.request_delete_table)
        menu.addAction(delete_action)

        menu.exec(event.screenPos())
        event.accept()

    def request_delete_table(self):
        main_window = self.scene().main_window if self.scene() else None
        if not main_window: return

        from commands import DeleteTableCommand # Local import
        reply = QMessageBox.question(main_window, "Confirm Deletion",
                                     f"Are you sure you want to delete table '{self.table_data.name}' and all its relationships?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            command = DeleteTableCommand(main_window, self.table_data)
            main_window.undo_stack.push(command)

    def request_copy_table(self):
        main_window = self.scene().main_window if self.scene() else None
        if main_window:
            main_window.copy_selected_table(self.table_data)

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

            # Get current display preferences
            should_show_text = show_cardinality_text_globally
            should_show_symbols = show_cardinality_symbols_globally
            if self.scene() and hasattr(self.scene(), 'main_window') and self.scene().main_window:
                should_show_text = self.scene().main_window.show_cardinality_text
                should_show_symbols = self.scene().main_window.show_cardinality_symbols

            s_point_item = self.mapFromScene(s_point_scene)
            e_point_item = self.mapFromScene(e_point_scene)
            if should_show_text:
                painter.setPen(QColor(current_theme_settings.get("cardinality_text_color", QColor(Qt.GlobalColor.black))))
                font = painter.font(); font.setBold(True); font.setPointSize(8)
                painter.setFont(font)
                font_metrics = QFontMetrics(font)

                # --- Cardinality at start_attachment_point (FK side) ---
                text_rect1 = font_metrics.boundingRect(card1_symbol)
                text_pos1 = QPointF(s_point_item) 
                text_pos1.setY(s_point_item.y() - text_rect1.height() * 0.7) 
                
                s_point_on_left_edge = False
                if self.scene() and self.scene().main_window:
                    table1_data = self.scene().main_window.tables_data.get(self.relationship_data.table1_name)
                    if table1_data and table1_data.graphic_item:
                        table1_rect_scene = table1_data.graphic_item.sceneBoundingRect()
                        if abs(s_point_scene.x() - table1_rect_scene.left()) < 1.0:
                            s_point_on_left_edge = True
                
                if s_point_on_left_edge: 
                    text_pos1.setX(s_point_item.x() - CARDINALITY_TEXT_MARGIN - text_rect1.width())
                else: 
                    text_pos1.setX(s_point_item.x() + CARDINALITY_TEXT_MARGIN)
                painter.drawText(text_pos1, card1_symbol)

                # --- Cardinality at end_attachment_point (PK side) ---
                text_rect2 = font_metrics.boundingRect(card2_symbol)
                text_pos2 = QPointF(e_point_item)
                text_pos2.setY(e_point_item.y() - text_rect2.height() * 0.7) 
                
                e_point_on_left_edge = False
                if self.scene() and self.scene().main_window:
                    table2_data = self.scene().main_window.tables_data.get(self.relationship_data.table2_name)
                    if table2_data and table2_data.graphic_item:
                        table2_rect_scene = table2_data.graphic_item.sceneBoundingRect()
                        if abs(e_point_scene.x() - table2_rect_scene.left()) < 1.0:
                            e_point_on_left_edge = True
                
                if e_point_on_left_edge: 
                    text_pos2.setX(e_point_item.x() - CARDINALITY_TEXT_MARGIN - text_rect2.width())
                else: 
                    text_pos2.setX(e_point_item.x() + CARDINALITY_TEXT_MARGIN)
                painter.drawText(text_pos2, card2_symbol)

            if should_show_symbols:
                symbol_pen = QPen(painter.pen().color(), SYMBOL_STROKE_WIDTH) 
                symbol_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                painter.setPen(symbol_pen)
                
                path_elements = [self.path().elementAt(i) for i in range(self.path().elementCount())]
                
                prev_s_point = self.mapFromScene(QPointF(intermediate_x_scene, s_point_scene.y())) 
                if self.path().elementCount() >= 2 and path_elements[1].type == QPainterPath.ElementType.LineToElement:
                     prev_s_point = QPointF(path_elements[1].x, path_elements[1].y)
                elif self.path().elementCount() == 2: 
                     prev_s_point = e_point_item

                angle_s_rad = math.atan2(s_point_item.y() - prev_s_point.y(), s_point_item.x() - prev_s_point.x())
                symbol_vertex_s_x = s_point_item.x() + SYMBOL_OFFSET_FROM_TABLE_EDGE * math.cos(angle_s_rad)
                symbol_vertex_s_y = s_point_item.y() + SYMBOL_OFFSET_FROM_TABLE_EDGE * math.sin(angle_s_rad)
                symbol_vertex_s = QPointF(symbol_vertex_s_x, symbol_vertex_s_y)

                if card1_symbol in ["N", "M"]: 
                    self._draw_many_symbol(painter, symbol_vertex_s, angle_s_rad)

                prev_e_point = self.mapFromScene(QPointF(intermediate_x_scene, e_point_scene.y())) 
                if self.path().elementCount() >= 3 and path_elements[-2].type == QPainterPath.ElementType.LineToElement:
                     prev_e_point = QPointF(path_elements[-2].x, path_elements[-2].y)
                elif self.path().elementCount() == 2: 
                     prev_e_point = s_point_item
                     
                angle_e_rad = math.atan2(e_point_item.y() - prev_e_point.y(), e_point_item.x() - prev_e_point.x())
                symbol_vertex_e_x = e_point_item.x() + SYMBOL_OFFSET_FROM_TABLE_EDGE * math.cos(angle_e_rad)
                symbol_vertex_e_y = e_point_item.y() + SYMBOL_OFFSET_FROM_TABLE_EDGE * math.sin(angle_e_rad)
                symbol_vertex_e = QPointF(symbol_vertex_e_x, symbol_vertex_e_y)

                if card2_symbol in ["N", "M"]: 
                    self._draw_many_symbol(painter, symbol_vertex_e, angle_e_rad)

    def _draw_one_symbol(self, painter: QPainter, connection_point: QPointF, line_angle_rad: float):
        """Draws 'one' symbol. Currently, no symbol is drawn for '1'."""
        # This method can be left empty or removed if no symbol is desired for "1".
        pass

    def _draw_many_symbol(self, painter: QPainter, connection_point: QPointF, line_angle_rad: float):
        """Draws 'many' symbol (crow's foot) at connection_point."""
        painter.save()
        painter.translate(connection_point)
        painter.rotate(math.degrees(line_angle_rad)) # Rotate to align with the line

        # Crow's foot lines extend "behind" the connection_point along the rotated x-axis
        angle1_rad = math.radians(CROWS_FOOT_ANGLE_DEG)
        angle2_rad = -math.radians(CROWS_FOOT_ANGLE_DEG)

        # Central line (optional, some notations don't have it if other lines are present)
        # painter.drawLine(QPointF(0, 0), QPointF(-CROWS_FOOT_LINE_LENGTH, 0)) 

        # Outer lines
        end_x1 = -CROWS_FOOT_LINE_LENGTH * math.cos(angle1_rad)
        end_y1 = -CROWS_FOOT_LINE_LENGTH * math.sin(angle1_rad)
        painter.drawLine(QPointF(0, 0), QPointF(end_x1, end_y1))

        end_x2 = -CROWS_FOOT_LINE_LENGTH * math.cos(angle2_rad)
        end_y2 = -CROWS_FOOT_LINE_LENGTH * math.sin(angle2_rad)
        painter.drawLine(QPointF(0, 0), QPointF(end_x2, end_y2))
        
        # Third line for many (often straight back if not using the optional central line above)
        painter.drawLine(QPointF(0,0), QPointF(-CROWS_FOOT_LINE_LENGTH, 0))

        painter.restore()

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
            # Calculate the new proposed X in scene coordinates
            new_vertical_x_scene_candidate = self.original_vertical_segment_x_scene + delta_x_item

            # Update the data model directly for live feedback
            self.relationship_data.vertical_segment_x_override = new_vertical_x_scene_candidate

            # --- MODIFIED LIVE UPDATE of attachment points and path ---
            main_win = self.scene().main_window if self.scene() and hasattr(self.scene(), 'main_window') else None
            
            if main_win:
                table1_obj = main_win.tables_data.get(self.relationship_data.table1_name)
                table2_obj = main_win.tables_data.get(self.relationship_data.table2_name)

                if table1_obj and table1_obj.graphic_item and table2_obj and table2_obj.graphic_item:
                    t1_graphic = table1_obj.graphic_item
                    t2_graphic = table2_obj.graphic_item
                    
                    old_p1 = self.start_attachment_point
                    old_p2 = self.end_attachment_point

                    p1_new = t1_graphic.get_attachment_point(
                        t2_graphic,
                        from_column_name=self.relationship_data.fk_column_name,
                        hint_intermediate_x=self.relationship_data.vertical_segment_x_override
                    )
                    p2_new = t2_graphic.get_attachment_point(
                        t1_graphic,
                        to_column_name=self.relationship_data.pk_column_name,
                        hint_intermediate_x=self.relationship_data.vertical_segment_x_override
                    )

                    # set_attachment_points will update stored points and call _build_path if they changed.
                    self.set_attachment_points(p1_new, p2_new)

                    # If attachment points (sides) did not change, set_attachment_points
                    # would not have called _build_path. But the override did change, so we must.
                    if old_p1 == p1_new and old_p2 == p2_new:
                        self.prepareGeometryChange() # Path will change due to override
                        self._build_path()           # Rebuild with new override
                else:
                    # Fallback if tables not found (should not happen in normal operation)
                    self.prepareGeometryChange()
                    self._build_path() 
            else:
                # Fallback if main_window not found
                self.prepareGeometryChange()
                self._build_path()
            # --- END MODIFIED LIVE UPDATE ---
            
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent):
        if self.dragging_vertical_segment and self.isSelected():
            from commands import SetRelationshipVerticalSegmentXCommand # Keep local import
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
