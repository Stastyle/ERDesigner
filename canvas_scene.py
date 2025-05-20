# canvas_scene.py
# Version: 20250519.05 (Fixed AttributeError)
# Contains the ERDGraphicsScene class for managing scene interactions.

from PyQt6.QtWidgets import (
    QGraphicsScene, QGraphicsPathItem, QMessageBox, QApplication, QGraphicsView,
    QGraphicsSceneMouseEvent, QMenu, QInputDialog
)
from PyQt6.QtCore import Qt, QPointF, QRectF, QSizeF
from PyQt6.QtGui import QPen, QColor, QPainterPath, QTransform, QAction

from constants import GRID_SIZE, DEFAULT_TABLE_WIDTH, TABLE_HEADER_HEIGHT, current_theme_settings, MIN_GROUP_WIDTH, MIN_GROUP_HEIGHT
from utils import snap_to_grid
from gui_items import TableGraphicItem, OrthogonalRelationshipPathItem, GroupGraphicItem # Assuming TableGraphicItem is imported
from data_models import Table, GroupData


class ERDGraphicsScene(QGraphicsScene):
    def __init__(self, parent_window=None):
        super().__init__(parent_window)
        self.line_in_progress = None
        self.start_item_for_line = None
        self.start_column_for_line = None
        self.main_window = parent_window
        self.grid_pen = QPen(QColor(current_theme_settings.get("grid_color", QColor(200, 200, 200, 60))),
                             0.5, Qt.PenStyle.SolidLine)
        self.drawing_relationship_shortcut_active = False
        self.shortcut_start_table_item = None
        self.shortcut_start_column_obj = None

        self.drawing_group_mode = False 
        self.new_group_rect_item = None 
        self.new_group_start_pos = QPointF()

        self.right_click_drawing_group_mode = False
        self.right_click_group_rect_item = None
        self.right_click_group_start_pos = QPointF()


    def drawBackground(self, painter, rect):
        super().drawBackground(painter, rect)
        self.grid_pen.setColor(QColor(current_theme_settings.get("grid_color", QColor(200, 200, 200, 60))))
        left = int(rect.left()) - (int(rect.left()) % GRID_SIZE)
        top = int(rect.top()) - (int(rect.top()) % GRID_SIZE)
        points = []
        for x in range(left, int(rect.right()), GRID_SIZE):
            for y in range(top, int(rect.bottom()), GRID_SIZE):
                points.append(QPointF(x, y))
        if points:
            painter.setPen(self.grid_pen)
            for p in points: painter.drawPoint(p)

    def get_item_and_column_at(self, scene_pos: QPointF):
        view = self.views()[0] if self.views() else None
        if not view:
            return None, None

        items_at_pos = self.items(scene_pos, Qt.ItemSelectionMode.IntersectsItemShape, Qt.SortOrder.DescendingOrder, view.transform())
        table_item_found = None
        column_obj_found = None

        for item in items_at_pos:
            if isinstance(item, TableGraphicItem):
                table_item_found = item
                item_local_pos = table_item_found.mapFromScene(scene_pos)
                current_y_check = table_item_found.header_height + table_item_found.padding / 2
                for idx, col_data in enumerate(table_item_found.table_data.columns):
                    col_rect = QRectF(0, current_y_check, table_item_found.width, table_item_found.column_row_height)
                    if col_rect.contains(item_local_pos):
                        column_obj_found = col_data
                        break
                    current_y_check += table_item_found.column_row_height
                if column_obj_found:
                    break
        return table_item_found, column_obj_found

    def mouseDoubleClickEvent(self, event: QGraphicsSceneMouseEvent):
        super().mouseDoubleClickEvent(event)
        if event.isAccepted():
            return

        item_at_pos = self.itemAt(event.scenePos(), self.views()[0].transform() if self.views() else QTransform())

        if item_at_pos is None: 
            scene_pos = event.scenePos()
            snapped_x = snap_to_grid(scene_pos.x() - DEFAULT_TABLE_WIDTH / 2, GRID_SIZE)
            snapped_y = snap_to_grid(scene_pos.y() - TABLE_HEADER_HEIGHT / 2, GRID_SIZE)
            if self.main_window and hasattr(self.main_window, 'handle_add_table_button'):
                self.main_window.handle_add_table_button(pos=QPointF(snapped_x, snapped_y))
            event.accept()

    def cancel_active_drawing_modes(self) -> bool:
        action_cancelled = False
        if self.main_window and self.main_window.drawing_relationship_mode:
            self.main_window.reset_drawing_mode() 
            action_cancelled = True
        if self.drawing_relationship_shortcut_active:
            self.drawing_relationship_shortcut_active = False
            self.shortcut_start_table_item = None
            self.shortcut_start_column_obj = None
            if self.line_in_progress:
                self.removeItem(self.line_in_progress); self.line_in_progress = None
            if self.main_window:
                QApplication.restoreOverrideCursor()
                if self.main_window.view: self.main_window.view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            action_cancelled = True

        if self.drawing_group_mode: 
            self.drawing_group_mode = False
            if self.new_group_rect_item:
                self.removeItem(self.new_group_rect_item)
                self.new_group_rect_item = None
            if self.main_window and hasattr(self.main_window, 'actionAddGroup'):
                if self.main_window.actionAddGroup.isCheckable():
                    self.main_window.actionAddGroup.setChecked(False) 
            if not self.right_click_drawing_group_mode and QApplication.overrideCursor() is not None:
                QApplication.restoreOverrideCursor()
            if not self.right_click_drawing_group_mode and self.main_window and self.main_window.view:
                 self.main_window.view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            action_cancelled = True
        
        if self.right_click_drawing_group_mode: 
            self.right_click_drawing_group_mode = False
            if self.right_click_group_rect_item:
                self.removeItem(self.right_click_group_rect_item)
                self.right_click_group_rect_item = None
            if not self.drawing_group_mode and QApplication.overrideCursor() is not None:
                 QApplication.restoreOverrideCursor()
            if not self.drawing_group_mode and self.main_window and self.main_window.view:
                 self.main_window.view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            action_cancelled = True
        return action_cancelled

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent):
        if self.main_window and self.main_window.drawing_relationship_mode:
            target_table_item, target_column_obj = self.get_item_and_column_at(event.scenePos())
            if event.button() == Qt.MouseButton.LeftButton:
                if not self.start_item_for_line: 
                    if target_table_item and target_column_obj:
                        self.start_item_for_line = target_table_item
                        self.start_column_for_line = target_column_obj
                        self.line_in_progress = QGraphicsPathItem()
                        self.line_in_progress.setPen(QPen(QColor(255,0,0,150), 2, Qt.PenStyle.DashLine))
                        self.line_in_progress.setZValue(10)
                        self.addItem(self.line_in_progress)
                        start_pos = self.start_item_for_line.get_attachment_point(None, from_column_name=self.start_column_for_line.name)
                        path = QPainterPath(start_pos)
                        path.lineTo(event.scenePos())
                        self.line_in_progress.setPath(path)
                    else: 
                        self.main_window.reset_drawing_mode()
                else: 
                    if target_table_item and target_column_obj and target_table_item != self.start_item_for_line:
                        self.main_window.finalize_relationship_drawing(
                            self.start_item_for_line.table_data, self.start_column_for_line,
                            target_table_item.table_data, target_column_obj
                        )
                    self.main_window.reset_drawing_mode()
                event.accept(); return
            elif event.button() == Qt.MouseButton.RightButton: 
                self.main_window.reset_drawing_mode() 
                event.accept(); return 

        if self.drawing_group_mode and event.button() == Qt.MouseButton.LeftButton:
            self.new_group_start_pos = event.scenePos()
            self.new_group_rect_item = QGraphicsPathItem() 
            path = QPainterPath()
            path.addRect(QRectF(self.new_group_start_pos, self.new_group_start_pos))
            self.new_group_rect_item.setPath(path)
            pen = QPen(QColor(current_theme_settings.get("group_border_color", QColor(100,100,255))), 1.5, Qt.PenStyle.DashLine)
            self.new_group_rect_item.setPen(pen)
            self.new_group_rect_item.setZValue(0.5) 
            self.addItem(self.new_group_rect_item)
            event.accept()
            return
        elif self.drawing_group_mode and event.button() == Qt.MouseButton.RightButton: 
            self.cancel_active_drawing_modes()
            event.accept()
            return

        if event.button() == Qt.MouseButton.RightButton:
            item_at_pos = self.itemAt(event.scenePos(), self.views()[0].transform() if self.views() else QTransform())
            if item_at_pos:
                super().mousePressEvent(event) 
                if event.isAccepted():
                    return 
            
            if self.drawing_relationship_shortcut_active: 
                self.cancel_active_drawing_modes()
                event.accept(); return
            
            target_table_item, target_column_obj = self.get_item_and_column_at(event.scenePos())
            if target_table_item and target_column_obj:
                if not target_column_obj.is_fk: 
                    if self.main_window and self.main_window.drawing_relationship_mode: self.main_window.reset_drawing_mode() 
                    if self.drawing_group_mode: self.cancel_active_drawing_modes() 

                    self.drawing_relationship_shortcut_active = True
                    self.shortcut_start_table_item = target_table_item
                    self.shortcut_start_column_obj = target_column_obj
                    self.line_in_progress = QGraphicsPathItem()
                    self.line_in_progress.setPen(QPen(QColor(0,0,255,150), 2, Qt.PenStyle.DashDotLine))
                    self.line_in_progress.setZValue(10)
                    self.addItem(self.line_in_progress)
                    start_pos = self.shortcut_start_table_item.get_attachment_point(None, from_column_name=self.shortcut_start_column_obj.name)
                    path = QPainterPath(start_pos); path.lineTo(event.scenePos()); self.line_in_progress.setPath(path)
                    if self.main_window:
                        QApplication.setOverrideCursor(Qt.CursorShape.CrossCursor)
                        if self.main_window.view: self.main_window.view.setDragMode(QGraphicsView.DragMode.NoDrag)
                    event.accept(); return
            
            if self.main_window and self.main_window.drawing_relationship_mode: self.main_window.reset_drawing_mode() 
            if self.drawing_group_mode: self.cancel_active_drawing_modes() 

            self.right_click_drawing_group_mode = True
            self.right_click_group_start_pos = event.scenePos()
            self.right_click_group_rect_item = QGraphicsPathItem()
            path = QPainterPath(); path.addRect(QRectF(self.right_click_group_start_pos, self.right_click_group_start_pos))
            self.right_click_group_rect_item.setPath(path)
            pen = QPen(QColor(current_theme_settings.get("group_border_color", QColor(0, 150, 0))), 1.5, Qt.PenStyle.DashLine) 
            self.right_click_group_rect_item.setPen(pen)
            self.right_click_group_rect_item.setZValue(0.5)
            self.addItem(self.right_click_group_rect_item)
            if self.main_window: 
                 QApplication.setOverrideCursor(Qt.CursorShape.CrossCursor)
                 if self.main_window.view: self.main_window.view.setDragMode(QGraphicsView.DragMode.NoDrag)
            event.accept(); return

        if event.button() == Qt.MouseButton.LeftButton and self.drawing_relationship_shortcut_active:
            target_table_item, target_column_obj = self.get_item_and_column_at(event.scenePos())
            if target_table_item and target_column_obj and self.shortcut_start_table_item and target_table_item != self.shortcut_start_table_item:
                if self.main_window:
                    self.main_window.finalize_relationship_drawing(
                        self.shortcut_start_table_item.table_data, self.shortcut_start_column_obj,
                        target_table_item.table_data, target_column_obj
                    )
            self.cancel_active_drawing_modes() 
            event.accept(); return

        if not event.isAccepted():
            super().mousePressEvent(event)


    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent):
        if self.drawing_group_mode and self.new_group_rect_item:
            rect = QRectF(self.new_group_start_pos, event.scenePos()).normalized()
            path = QPainterPath(); path.addRect(rect); self.new_group_rect_item.setPath(path)
            event.accept(); return
        
        if self.right_click_drawing_group_mode and self.right_click_group_rect_item:
            rect = QRectF(self.right_click_group_start_pos, event.scenePos()).normalized()
            path = QPainterPath(); path.addRect(rect); self.right_click_group_rect_item.setPath(path)
            event.accept(); return

        active_start_item = None; active_start_column = None
        if self.main_window and self.main_window.drawing_relationship_mode and self.start_item_for_line:
            active_start_item = self.start_item_for_line; active_start_column = self.start_column_for_line
        elif self.drawing_relationship_shortcut_active and self.shortcut_start_table_item:
            active_start_item = self.shortcut_start_table_item; active_start_column = self.shortcut_start_column_obj

        if self.line_in_progress and active_start_item and active_start_column:
            start_pos = active_start_item.get_attachment_point(None, from_column_name=active_start_column.name)
            path = QPainterPath(start_pos); path.lineTo(event.scenePos()); self.line_in_progress.setPath(path)
            event.accept(); return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent):
        if self.drawing_group_mode and self.new_group_rect_item and event.button() == Qt.MouseButton.LeftButton:
            final_rect = QRectF(self.new_group_start_pos, event.scenePos()).normalized()
            self.removeItem(self.new_group_rect_item); self.new_group_rect_item = None 

            if final_rect.width() < MIN_GROUP_WIDTH or final_rect.height() < MIN_GROUP_HEIGHT:
                QMessageBox.information(self.main_window, "קבוצה קטנה מדי",
                                        f"גודל קבוצה מינימלי הוא {MIN_GROUP_WIDTH}x{MIN_GROUP_HEIGHT} פיקסלים.")
            else:
                if self.main_window and hasattr(self.main_window, 'handle_add_group_button'):
                    snapped_x = snap_to_grid(final_rect.x(), GRID_SIZE)
                    snapped_y = snap_to_grid(final_rect.y(), GRID_SIZE)
                    snapped_width = snap_to_grid(final_rect.width(), GRID_SIZE)
                    snapped_height = snap_to_grid(final_rect.height(), GRID_SIZE)
                    self.main_window.handle_add_group_button(
                        pos=QPointF(snapped_x, snapped_y),
                        size=QSizeF(snapped_width, snapped_height),
                        from_drawing_mode=True 
                    )
            if final_rect.width() < MIN_GROUP_WIDTH or final_rect.height() < MIN_GROUP_HEIGHT:
                self.cancel_active_drawing_modes() 
            event.accept(); return

        if self.right_click_drawing_group_mode and self.right_click_group_rect_item and event.button() == Qt.MouseButton.RightButton:
            final_rect = QRectF(self.right_click_group_start_pos, event.scenePos()).normalized()
            self.removeItem(self.right_click_group_rect_item); self.right_click_group_rect_item = None

            if final_rect.width() < MIN_GROUP_WIDTH or final_rect.height() < MIN_GROUP_HEIGHT:
                QMessageBox.information(self.main_window, "קבוצה קטנה מדי",
                                        f"גודל קבוצה מינימלי הוא {MIN_GROUP_WIDTH}x{MIN_GROUP_HEIGHT} פיקסלים.")
            else:
                if self.main_window and hasattr(self.main_window, 'handle_add_group_button'):
                    group_name, ok = QInputDialog.getText(self.main_window, "שם קבוצה חדשה", "הכנס שם לקבוצה:")
                    if ok and group_name.strip():
                        snapped_x = snap_to_grid(final_rect.x(), GRID_SIZE)
                        snapped_y = snap_to_grid(final_rect.y(), GRID_SIZE)
                        snapped_width = snap_to_grid(final_rect.width(), GRID_SIZE)
                        snapped_height = snap_to_grid(final_rect.height(), GRID_SIZE)
                        
                        self.main_window.handle_add_group_button(
                            group_name_prop=group_name.strip(),
                            pos=QPointF(snapped_x, snapped_y),
                            size=QSizeF(snapped_width, snapped_height)
                        )
            
            self.cancel_active_drawing_modes() 
            event.accept(); return

        super().mouseReleaseEvent(event)


    def update_relationships_for_table(self, table_name_moved: str):
        if self.main_window and hasattr(self.main_window, 'update_all_relationships_graphics'):
            self.main_window.update_all_relationships_graphics()

    def handle_table_movement_for_groups(self, table_item: TableGraphicItem, final_check=False, scene_pos_override: QPointF | None = None):
        from commands import SetTableGroupCommand 
        if not self.main_window or not hasattr(self.main_window, 'groups_data'):
            return

        table_data = table_item.table_data
        old_group_name = table_data.group_name
        determined_new_group_name = None
        
        for group_data_obj in self.main_window.groups_data.values():
            if group_data_obj.graphic_item:
                group_scene_rect = group_data_obj.graphic_item.sceneBoundingRect()
                
                point_to_test: QPointF
                if scene_pos_override is not None:
                    # If an override position is given (e.g., mouse cursor during drag over a group),
                    # test this specific point for containment.
                    point_to_test = scene_pos_override
                else:
                    # If no override, the table_item is at its current position.
                    # Test the center of the table_item for containment.
                    if table_item: # table_item is the TableGraphicItem
                        point_to_test = table_item.sceneBoundingRect().center() # Corrected: No .graphic_item here
                    else:
                        # This case should ideally not be reached if table_item is always valid.
                        continue 
                
                if group_scene_rect.contains(point_to_test):
                    determined_new_group_name = group_data_obj.name
                    break
        
        if old_group_name != determined_new_group_name:
            if final_check: 
                command = SetTableGroupCommand(self.main_window, table_data, old_group_name, determined_new_group_name)
                self.main_window.undo_stack.push(command)

    def handle_group_movement(self, group_item: GroupGraphicItem, delta: QPointF):
        pass 

    def handle_group_resize_visual_feedback(self, group_item: GroupGraphicItem):
        pass 

    def snap_to_grid(self, value, grid_size): 
        if grid_size == 0: return value
        return round(value / grid_size) * grid_size

    def contextMenuEvent(self, event: QGraphicsSceneMouseEvent):
        if self.drawing_group_mode or self.right_click_drawing_group_mode or \
           (self.main_window and self.main_window.drawing_relationship_mode) or \
           self.drawing_relationship_shortcut_active:
            event.accept()
            return

        item_at_pos = self.itemAt(event.scenePos(), self.views()[0].transform() if self.views() else QTransform())

        if not item_at_pos and self.main_window: 
            menu = QMenu()
            if hasattr(self.main_window, 'current_theme_settings'):
                 menu.setStyleSheet(f"""
                    QMenu {{
                        background-color: {self.main_window.current_theme_settings.get('toolbar_bg', QColor(240,240,240)).name()};
                        color: {self.main_window.current_theme_settings.get('text_color', QColor(0,0,0)).name()};
                        border: 1px solid {self.main_window.current_theme_settings.get('toolbar_border', QColor(200,200,200)).name()};
                    }}
                    QMenu::item:selected {{
                        background-color: {self.main_window.current_theme_settings.get('button_hover_bg', QColor(220,220,220)).name()};
                    }}
                """)

            add_table_action = QAction("הוסף טבלה", menu) 
            add_table_action.triggered.connect(lambda: self.main_window.handle_add_table_button(pos=event.scenePos()))
            menu.addAction(add_table_action)

            add_group_action = QAction("הוסף קבוצה (מכפתור)", menu) 
            add_group_action.triggered.connect(lambda: self.main_window.handle_add_group_button(pos=event.scenePos())) 
            menu.addAction(add_group_action)
            
            start_draw_group_rmb_action = QAction("התחל ציור קבוצה (לחצן ימני)", menu) 
            start_draw_group_rmb_action.setToolTip("לחץ לחיצה ימנית וגרור על מנת לצייר קבוצה") 
            start_draw_group_rmb_action.setEnabled(False) 
            menu.addAction(start_draw_group_rmb_action)


            add_relationship_action = QAction("הוסף קשר (מכפתור)", menu) 
            add_relationship_action.triggered.connect(lambda: self.main_window.toggle_relationship_mode_action(True))
            menu.addAction(add_relationship_action)


            menu.exec(event.screenPos())
            event.accept()
        else:
            super().contextMenuEvent(event) 

