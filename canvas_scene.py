# canvas_scene.py
# Contains the ERDGraphicsScene class for managing scene interactions.

from PyQt6.QtWidgets import QGraphicsScene, QGraphicsPathItem, QMessageBox
from PyQt6.QtCore import Qt, QPointF, QRectF 
from PyQt6.QtGui import QPen, QColor, QPainterPath, QTransform 

from constants import GRID_SIZE, DEFAULT_TABLE_WIDTH, TABLE_HEADER_HEIGHT, current_theme_settings
from utils import snap_to_grid
from gui_items import TableGraphicItem, OrthogonalRelationshipLine


class ERDGraphicsScene(QGraphicsScene):
    def __init__(self, parent_window=None): 
        super().__init__(parent_window) 
        self.line_in_progress = None
        self.start_item_for_line = None
        self.start_column_for_line = None 
        self.main_window = parent_window # Reference to ERDCanvasWindow
        self.grid_pen = QPen(QColor(current_theme_settings.get("grid_color", QColor(200, 200, 200, 60))), 
                             0.5, Qt.PenStyle.SolidLine) 

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
            for p in points:
                painter.drawPoint(p) 

    def get_item_and_column_at(self, scene_pos):
        view = self.views()[0] if self.views() else None
        if not view: return None, None

        items = self.items(scene_pos, Qt.ItemSelectionMode.IntersectsItemShape, 
                           Qt.SortOrder.DescendingOrder, view.transform())
        table_item = None
        column_obj = None

        for item in items:
            if isinstance(item, TableGraphicItem):
                table_item = item
                item_local_pos = table_item.mapFromScene(scene_pos)
                current_y_check = table_item.header_height + table_item.padding / 2
                for idx, col_data in enumerate(table_item.table_data.columns):
                    col_rect = QRectF(0, current_y_check, table_item.width, table_item.column_row_height)
                    if col_rect.contains(item_local_pos):
                        column_obj = col_data
                        break
                    current_y_check += table_item.column_row_height
                break 
        return table_item, column_obj


    def mouseDoubleClickEvent(self, event):
        # Handle double-click on relationship lines first
        for item in self.items(event.scenePos()):
            if isinstance(item, OrthogonalRelationshipLine):
                if hasattr(self.main_window, 'edit_relationship_properties'):
                    self.main_window.edit_relationship_properties(item.relationship_data)
                    event.accept()
                    return # Event handled

        table_item_at_click, _ = self.get_item_and_column_at(event.scenePos()) 
        if table_item_at_click is None: 
            # Double-click on an empty area - restore adding table
            scene_pos = event.scenePos()
            # Calculate position for the new table, snapped to grid
            snapped_x = snap_to_grid(scene_pos.x() - DEFAULT_TABLE_WIDTH / 2, GRID_SIZE) 
            snapped_y = snap_to_grid(scene_pos.y() - TABLE_HEADER_HEIGHT / 2, GRID_SIZE) 
            if self.main_window and hasattr(self.main_window, 'handle_add_table_button'):
                self.main_window.handle_add_table_button(pos=QPointF(snapped_x, snapped_y))
            event.accept() # Event handled by adding a table
        else: 
            # Double-click was on an item (e.g., a table that's not a relationship line).
            # Let the item handle it or propagate to QGraphicsScene default.
            super().mouseDoubleClickEvent(event)


    def mousePressEvent(self, event):
        if self.main_window and self.main_window.drawing_relationship_mode: 
            target_table_item, target_column_obj = self.get_item_and_column_at(event.scenePos())
            
            if not self.start_item_for_line: # First click (Source Column)
                if target_table_item and target_column_obj:
                    self.start_item_for_line = target_table_item
                    self.start_column_for_line = target_column_obj 

                    self.line_in_progress = QGraphicsPathItem() 
                    self.line_in_progress.setPen(QPen(QColor(255,0,0,150), 2, Qt.PenStyle.DashLine))
                    self.line_in_progress.setZValue(10) 
                    self.addItem(self.line_in_progress)
                    
                    start_col_idx = self.start_item_for_line.table_data.get_column_index(self.start_column_for_line.name)
                    start_pos = QPointF() 
                    if start_col_idx != -1:
                        start_y_in_item = self.start_item_for_line.header_height + self.start_item_for_line.padding / 2 + \
                                          (start_col_idx * self.start_item_for_line.column_row_height) + \
                                          (self.start_item_for_line.column_row_height / 2)
                        start_y_scene = self.start_item_for_line.scenePos().y() + start_y_in_item
                        
                        start_x_scene = self.start_item_for_line.sceneBoundingRect().left() \
                            if event.scenePos().x() < self.start_item_for_line.sceneBoundingRect().center().x() \
                            else self.start_item_for_line.sceneBoundingRect().right()
                        start_pos = QPointF(start_x_scene, start_y_scene)
                    else: 
                        start_pos = self.start_item_for_line.get_attachment_point(None, from_column_name=self.start_column_for_line.name)


                    path = QPainterPath(start_pos)
                    path.lineTo(event.scenePos())
                    self.line_in_progress.setPath(path)
                    print(f"Relationship drawing: Started from table '{self.start_item_for_line.table_data.name}', column '{self.start_column_for_line.name}'")
                else:
                    print("Relationship drawing: First click was not on a table column.")
            else: # Second click (Target Column)
                if target_table_item and target_column_obj and target_table_item != self.start_item_for_line:
                    source_table_data = self.start_item_for_line.table_data
                    source_column_data = self.start_column_for_line
                    dest_table_data = target_table_item.table_data
                    dest_column_data = target_column_obj

                    self.main_window.finalize_relationship_drawing(source_table_data, source_column_data, dest_table_data, dest_column_data)
                else:
                    print(f"Relationship drawing: Second click target was not a valid column on a different table.")
                
                if self.main_window:
                    self.main_window.reset_drawing_mode()

        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.line_in_progress and self.start_item_for_line and self.start_column_for_line:
            start_col_idx = self.start_item_for_line.table_data.get_column_index(self.start_column_for_line.name)
            start_pos = QPointF() 
            if start_col_idx != -1:
                start_y_in_item = self.start_item_for_line.header_height + self.start_item_for_line.padding / 2 + \
                                  (start_col_idx * self.start_item_for_line.column_row_height) + \
                                  (self.start_item_for_line.column_row_height / 2)
                start_y_scene = self.start_item_for_line.scenePos().y() + start_y_in_item
                
                start_x_scene = self.start_item_for_line.sceneBoundingRect().left() \
                    if event.scenePos().x() < self.start_item_for_line.sceneBoundingRect().center().x() \
                    else self.start_item_for_line.sceneBoundingRect().right()
                start_pos = QPointF(start_x_scene, start_y_scene)
            else: 
                 start_pos = self.start_item_for_line.get_attachment_point(None, from_column_name=self.start_column_for_line.name)


            path = QPainterPath(start_pos)
            path.lineTo(event.scenePos()) 
            self.line_in_progress.setPath(path)
        else:
            super().mouseMoveEvent(event)

    def update_relationships_for_table(self, table_name_moved):
        if self.main_window and hasattr(self.main_window, 'update_all_relationships_graphics'):
            self.main_window.update_all_relationships_graphics()
