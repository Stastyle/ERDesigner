# canvas_scene.py
# Version: 20250518.0403
# Contains the ERDGraphicsScene class for managing scene interactions.

from PyQt6.QtWidgets import (
    QGraphicsScene, QGraphicsPathItem, QMessageBox, QApplication, QGraphicsView,
    QGraphicsSceneMouseEvent, QMenu
)
from PyQt6.QtCore import Qt, QPointF, QRectF, QSizeF
from PyQt6.QtGui import QPen, QColor, QPainterPath, QTransform, QAction

from constants import GRID_SIZE, DEFAULT_TABLE_WIDTH, TABLE_HEADER_HEIGHT, current_theme_settings, MIN_GROUP_WIDTH, MIN_GROUP_HEIGHT
from utils import snap_to_grid
from gui_items import TableGraphicItem, OrthogonalRelationshipPathItem, GroupGraphicItem
from data_models import Table, GroupData # Table is used for type hinting
from commands import SetTableGroupCommand

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

        if item_at_pos is None: # Double-click on empty space
            scene_pos = event.scenePos()
            snapped_x = snap_to_grid(scene_pos.x() - DEFAULT_TABLE_WIDTH / 2, GRID_SIZE)
            snapped_y = snap_to_grid(scene_pos.y() - TABLE_HEADER_HEIGHT / 2, GRID_SIZE)
            if self.main_window and hasattr(self.main_window, 'handle_add_table_button'):
                self.main_window.handle_add_table_button(pos=QPointF(snapped_x, snapped_y))
            event.accept()

    def cancel_active_drawing_modes(self) -> bool:
        action_cancelled = False
        if self.main_window and self.main_window.drawing_relationship_mode:
            self.main_window.reset_drawing_mode() # This will also update button state and cursor
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
            if QApplication.overrideCursor() is not None:
                QApplication.restoreOverrideCursor()
            if self.main_window and self.main_window.view:
                 self.main_window.view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            action_cancelled = True

        return action_cancelled

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent):
        # Group drawing mode (Left Click)
        if self.drawing_group_mode and event.button() == Qt.MouseButton.LeftButton:
            self.new_group_start_pos = event.scenePos()
            self.new_group_rect_item = QGraphicsPathItem()
            path = QPainterPath()
            path.addRect(QRectF(self.new_group_start_pos, self.new_group_start_pos))
            self.new_group_rect_item.setPath(path)
            pen = QPen(QColor(current_theme_settings.get("group_border_color", QColor(100,100,255))), 1.5, Qt.PenStyle.DashLine)
            self.new_group_rect_item.setPen(pen)
            self.new_group_rect_item.setZValue(0.5) # Ensure it's above grid but below other items
            self.addItem(self.new_group_rect_item)
            event.accept()
            return

        # General relationship drawing mode (Button activated)
        if self.main_window and self.main_window.drawing_relationship_mode:
            target_table_item, target_column_obj = self.get_item_and_column_at(event.scenePos())
            if event.button() == Qt.MouseButton.LeftButton:
                if not self.start_item_for_line: # First click to select start column
                    if target_table_item and target_column_obj:
                        self.start_item_for_line = target_table_item
                        self.start_column_for_line = target_column_obj
                        self.line_in_progress = QGraphicsPathItem()
                        self.line_in_progress.setPen(QPen(QColor(255,0,0,150), 2, Qt.PenStyle.DashLine))
                        self.line_in_progress.setZValue(10) # Ensure line is on top
                        self.addItem(self.line_in_progress)
                        start_pos = self.start_item_for_line.get_attachment_point(None, from_column_name=self.start_column_for_line.name)
                        path = QPainterPath(start_pos)
                        path.lineTo(event.scenePos())
                        self.line_in_progress.setPath(path)
                    else: # Clicked on empty space, cancel mode
                        self.main_window.reset_drawing_mode()
                else: # Second click to select end column or cancel
                    if target_table_item and target_column_obj and target_table_item != self.start_item_for_line:
                        self.main_window.finalize_relationship_drawing(
                            self.start_item_for_line.table_data, self.start_column_for_line,
                            target_table_item.table_data, target_column_obj
                        )
                    # Always reset mode after second click (whether successful or on empty space)
                    self.main_window.reset_drawing_mode()
                event.accept(); return
            elif event.button() == Qt.MouseButton.RightButton: # Cancel drawing relationship with right click
                self.main_window.reset_drawing_mode()
                event.accept(); return

        # Right-click specific logic
        if event.button() == Qt.MouseButton.RightButton:
            item_at_pos = self.itemAt(event.scenePos(), self.views()[0].transform() if self.views() else QTransform())
            if item_at_pos:
                # Let the item handle its own context menu first
                super().mousePressEvent(event) # This allows the item's contextMenuEvent to be called
                if event.isAccepted():
                    return # Item handled it

            # If no item handled it, or if it's an empty space click, proceed with scene/shortcut logic
            if self.drawing_relationship_shortcut_active: # Cancel active shortcut drawing
                self.cancel_active_drawing_modes()
                event.accept(); return
            else:
                target_table_item, target_column_obj = self.get_item_and_column_at(event.scenePos())
                if target_table_item and target_column_obj and not target_column_obj.is_fk: # MODIFIED: Check if not already FK
                    # Start relationship drawing shortcut only if column is not already an FK
                    if self.main_window and self.main_window.drawing_relationship_mode: self.main_window.reset_drawing_mode() # Cancel general mode if active

                    self.drawing_relationship_shortcut_active = True
                    self.shortcut_start_table_item = target_table_item
                    self.shortcut_start_column_obj = target_column_obj
                    self.line_in_progress = QGraphicsPathItem()
                    self.line_in_progress.setPen(QPen(QColor(0,0,255,150), 2, Qt.PenStyle.DashDotLine))
                    self.line_in_progress.setZValue(10)
                    self.addItem(self.line_in_progress)
                    start_pos = self.shortcut_start_table_item.get_attachment_point(None, from_column_name=self.shortcut_start_column_obj.name)
                    path = QPainterPath(start_pos)
                    path.lineTo(event.scenePos())
                    self.line_in_progress.setPath(path)
                    if self.main_window:
                        QApplication.setOverrideCursor(Qt.CursorShape.CrossCursor)
                        if self.main_window.view: self.main_window.view.setDragMode(QGraphicsView.DragMode.NoDrag)
                    event.accept(); return
                # If on an FK column or empty space, the scene's contextMenuEvent will be triggered later
                # Do not call super().mousePressEvent(event) here if we intend to show a scene context menu,
                # as that might be consumed by the view. contextMenuEvent is the right place.
                # If an item was under cursor but didn't accept the event, it will fall through to contextMenuEvent.

        # Left-click to finalize relationship from shortcut
        if event.button() == Qt.MouseButton.LeftButton and self.drawing_relationship_shortcut_active:
            target_table_item, target_column_obj = self.get_item_and_column_at(event.scenePos())
            if target_table_item and target_column_obj and self.shortcut_start_table_item and target_table_item != self.shortcut_start_table_item:
                if self.main_window:
                    self.main_window.finalize_relationship_drawing(
                        self.shortcut_start_table_item.table_data, self.shortcut_start_column_obj,
                        target_table_item.table_data, target_column_obj
                    )
            self.cancel_active_drawing_modes() # Cancel shortcut mode regardless of success
            event.accept(); return

        if not event.isAccepted():
            super().mousePressEvent(event)


    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent):
        if self.drawing_group_mode and self.new_group_rect_item:
            rect = QRectF(self.new_group_start_pos, event.scenePos()).normalized()
            path = QPainterPath()
            path.addRect(rect)
            self.new_group_rect_item.setPath(path)
            event.accept()
            return

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
            self.removeItem(self.new_group_rect_item)
            self.new_group_rect_item = None

            if final_rect.width() < MIN_GROUP_WIDTH or final_rect.height() < MIN_GROUP_HEIGHT:
                QMessageBox.information(self.main_window, "Group Too Small",
                                        f"Minimum group size is {MIN_GROUP_WIDTH}x{MIN_GROUP_HEIGHT} pixels.")
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

            if not (final_rect.width() < MIN_GROUP_WIDTH or final_rect.height() < MIN_GROUP_HEIGHT):
                 pass
            else: # Group creation aborted due to size, or dialog was cancelled by handle_add_group_button
                self.cancel_active_drawing_modes() # Ensure mode is reset

            event.accept()
            return

        super().mouseReleaseEvent(event)


    def update_relationships_for_table(self, table_name_moved: str):
        if self.main_window and hasattr(self.main_window, 'update_all_relationships_graphics'):
            self.main_window.update_all_relationships_graphics()

    def handle_table_movement_for_groups(self, table_item: TableGraphicItem, final_check=False):
        if not self.main_window or not hasattr(self.main_window, 'groups_data'):
            return

        table_data = table_item.table_data
        old_group_name = table_data.group_name
        determined_new_group_name = None

        for group_data_obj in self.main_window.groups_data.values():
            if group_data_obj.graphic_item and group_data_obj.graphic_item.contains_table(table_item):
                determined_new_group_name = group_data_obj.name
                break

        if old_group_name != determined_new_group_name:
            if final_check:
                command = SetTableGroupCommand(self.main_window, table_data, old_group_name, determined_new_group_name)
                self.main_window.undo_stack.push(command)

    def handle_group_movement(self, group_item: GroupGraphicItem, delta: QPointF):
        pass # Actual movement logic is in MoveGroupCommand

    def handle_group_resize_visual_feedback(self, group_item: GroupGraphicItem):
        pass # Actual resize logic is in ResizeGroupCommand

    def snap_to_grid(self, value, grid_size):
        if grid_size == 0: return value
        return round(value / grid_size) * grid_size

    def contextMenuEvent(self, event: QGraphicsSceneMouseEvent):
        """Handles context menu requests on the scene itself."""
        item_at_pos = self.itemAt(event.scenePos(), self.views()[0].transform() if self.views() else QTransform())

        # If an item is under the cursor and has its own context menu, it should have handled it in mousePressEvent.
        # This scene context menu is primarily for empty space.
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

            add_group_action = QAction("Add Group", menu)
            add_group_action.triggered.connect(lambda: self.main_window.handle_add_group_button(pos=event.scenePos())) # Will use default size
            menu.addAction(add_group_action)

            add_relationship_action = QAction("Add Relationship", menu) # Changed to English
            # This action will toggle the relationship drawing mode on the main window
            add_relationship_action.triggered.connect(lambda: self.main_window.toggle_relationship_mode_action(True))
            menu.addAction(add_relationship_action)


            menu.exec(event.screenPos())
            event.accept()
        else:
            # If there's an item, but it didn't handle the context menu via mousePressEvent,
            # we can call the superclass method to allow Qt's default item context menu handling (if any).
            super().contextMenuEvent(event)
