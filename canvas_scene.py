# canvas_scene.py
# Version: 20250519.05 (Fixed AttributeError)
# Contains the ERDGraphicsScene class for managing scene interactions.

from PyQt6.QtWidgets import (
    QGraphicsScene, QGraphicsPathItem, QMessageBox, QApplication, QGraphicsView,
    QGraphicsSceneMouseEvent, QMenu, QInputDialog
)
from PyQt6.QtCore import Qt, QPointF, QRectF, QSizeF
from PyQt6.QtGui import QPen, QColor, QPainterPath, QTransform, QAction

from constants import GRID_SIZE, DEFAULT_TABLE_WIDTH, TABLE_HEADER_HEIGHT, current_theme_settings
from utils import snap_to_grid
from gui_items import TableGraphicItem, OrthogonalRelationshipPathItem # Assuming TableGraphicItem is imported
from data_models import Table


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

    def update_grid_pen_color(self): # Helper to update grid pen if theme changes
        self.shortcut_start_column_obj = None


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
            # print("Shortcut drawing mode cancelled.") # Debug
            action_cancelled = True

        return action_cancelled

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent):
        # 1. Handle main button-initiated drawing mode
        if self.main_window and self.main_window.drawing_relationship_mode: # This mode uses self.start_item_for_line
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

        # 2. Handle completion/cancellation of the new right-click shortcut mode
        if self.drawing_relationship_shortcut_active: # This mode uses self.shortcut_start_table_item
            if event.button() == Qt.MouseButton.LeftButton: # Finalize with Left Click
                target_table_item, target_column_obj = self.get_item_and_column_at(event.scenePos())
                if target_table_item and target_column_obj and \
                   self.shortcut_start_table_item and target_table_item != self.shortcut_start_table_item:
                    # Attempt to finalize
                    if self.main_window:
                        self.main_window.finalize_relationship_drawing(
                            self.shortcut_start_table_item.table_data, self.shortcut_start_column_obj,
                            target_table_item.table_data, target_column_obj
                        )
                # Always cancel the shortcut mode after a left-click attempt (finalize or not)
                self.cancel_active_drawing_modes()
                event.accept()
                return
            elif event.button() == Qt.MouseButton.RightButton: # Cancel with Right Click
                self.cancel_active_drawing_modes()
                event.accept()
                return
            # Other mouse buttons during shortcut mode could also cancel or be ignored.
            # For example, if user presses middle mouse button, it will fall through and likely do nothing or default scene behavior.

        # 3. Handle initiation of the new right-click shortcut mode
        #    (Only if not in button mode and shortcut not already active)
        if event.button() == Qt.MouseButton.RightButton and \
           not (self.main_window and self.main_window.drawing_relationship_mode) and \
           not self.drawing_relationship_shortcut_active:
            
            item_at_pos = self.itemAt(event.scenePos(), self.views()[0].transform() if self.views() else QTransform())
            # If right-click is on an existing item that handles its own context menu, let it.
            if item_at_pos and not isinstance(item_at_pos, TableGraphicItem): # e.g. Relationship item
                super().mousePressEvent(event)
                if event.isAccepted():
                    return

            target_table_item, target_column_obj = self.get_item_and_column_at(event.scenePos())
            if target_table_item and target_column_obj:
                # Eligible to START: Column is PK, OR (Column is not PK AND not FK)
                if target_column_obj.is_pk or \
                   (not target_column_obj.is_pk and not target_column_obj.is_fk):
                    
                    self.drawing_relationship_shortcut_active = True
                    self.shortcut_start_table_item = target_table_item
                    self.shortcut_start_column_obj = target_column_obj
                    
                    self.line_in_progress = QGraphicsPathItem()
                    self.line_in_progress.setPen(QPen(QColor(0, 0, 255, 180), 2, Qt.PenStyle.DashDotLine)) # Blue, dashed
                    self.line_in_progress.setZValue(10) 
                    self.addItem(self.line_in_progress)
                    
                    start_pos = self.shortcut_start_table_item.get_attachment_point(None, from_column_name=self.shortcut_start_column_obj.name)
                    path = QPainterPath(start_pos)
                    path.lineTo(event.scenePos()) 
                    self.line_in_progress.setPath(path)
                    
                    if self.main_window:
                        QApplication.setOverrideCursor(Qt.CursorShape.CrossCursor)
                        if self.main_window.view: self.main_window.view.setDragMode(QGraphicsView.DragMode.NoDrag)
                    # print(f"Shortcut drawing initiated from: {target_table_item.table_data.name}.{target_column_obj.name}") # Debug
                    event.accept()
                    return
                # else: # Clicked on an existing FK (but not PK) or other non-eligible column
                    # print(f"Right-click on non-eligible column for shortcut: {target_column_obj.name} (is_fk={target_column_obj.is_fk})") # Debug
                    # Let it fall through for potential context menu on the TableGraphicItem itself
                    pass 
            # If not initiated (e.g. click on canvas, or on table but not specific eligible column),
            # let event propagate for general scene context menu or TableGraphicItem's context menu.

        # 4. Fallback to default behavior if not handled by drawing modes or shortcut initiation
        if not event.isAccepted():
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent):
        active_start_item = None
        active_start_column = None

        if self.main_window and self.main_window.drawing_relationship_mode and self.start_item_for_line:
            active_start_item = self.start_item_for_line; active_start_column = self.start_column_for_line
        elif self.drawing_relationship_shortcut_active and self.shortcut_start_table_item:
            active_start_item = self.shortcut_start_table_item; active_start_column = self.shortcut_start_column_obj

        if self.line_in_progress and active_start_item and active_start_column:
            start_pos = active_start_item.get_attachment_point(None, from_column_name=active_start_column.name)
            path = QPainterPath(start_pos)
            path.lineTo(event.scenePos())
            self.line_in_progress.setPath(path)
            event.accept(); return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent):
        super().mouseReleaseEvent(event)


    def update_relationships_for_table(self, table_name_moved: str):
        if self.main_window and hasattr(self.main_window, 'update_all_relationships_graphics'):
            self.main_window.update_all_relationships_graphics()

    def snap_to_grid(self, value, grid_size): 
        if grid_size == 0: return value
        return round(value / grid_size) * grid_size

    def contextMenuEvent(self, event: QGraphicsSceneMouseEvent):
        if (self.main_window and self.main_window.drawing_relationship_mode) or self.drawing_relationship_shortcut_active:
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

            add_table_action = QAction("Add Table", menu)
            add_table_action.triggered.connect(lambda: self.main_window.handle_add_table_button(pos=event.scenePos()))
            menu.addAction(add_table_action)


            add_relationship_action = QAction("Add Relationship (from button)", menu)
            add_relationship_action.triggered.connect(lambda: self.main_window.toggle_relationship_mode_action(True))
            menu.addAction(add_relationship_action)

            if self.main_window and self.main_window.copied_table_data:
                paste_table_action = QAction("Paste Table Here", menu)
                paste_table_action.triggered.connect(lambda: self.main_window.paste_copied_table(pos=event.scenePos()))
                menu.addAction(paste_table_action)


            menu.exec(event.screenPos())
            event.accept()
        else:
            super().contextMenuEvent(event) 
