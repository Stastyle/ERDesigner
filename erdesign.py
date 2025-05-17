import sys
import csv
import math 
import os # For filename in window title
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QGraphicsView, QGraphicsScene,
    QGraphicsRectItem, QGraphicsTextItem, QGraphicsLineItem, QGraphicsPathItem,
    QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QDialog, QFormLayout,
    QLineEdit, QCheckBox, QComboBox, QMessageBox, QFileDialog,
    QGraphicsItem, QDialogButtonBox, QLabel, QScrollArea, QToolBar, QSizePolicy,
    QGraphicsSceneHoverEvent, QGraphicsSceneMouseEvent, QColorDialog
)
from PyQt6.QtCore import Qt, QPointF, QLineF, QRectF, QSize
from PyQt6.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont, QPainterPath, 
    QFontMetrics, QIcon, QAction, QPixmap, QTransform, QPainterPathStroker,
    QActionGroup 
)

# --- Constants ---
DEFAULT_TABLE_WIDTH = 200 
TABLE_HEADER_HEIGHT = 30
COLUMN_HEIGHT = 22 
PADDING = 10
GRID_SIZE = 20 
RELATIONSHIP_HANDLE_SIZE = 8 
MIN_HORIZONTAL_SEGMENT = GRID_SIZE * 1.5 
CSV_TABLE_DEF_MARKER = "TABLE_DEFINITION" 
CSV_COLUMN_DEF_MARKER = "COLUMN_DEFINITION" 
CSV_TABLE_POSITION_MARKER = "TABLE_POSITION" 
CSV_RELATIONSHIP_DEF_MARKER = "RELATIONSHIP_DEF" 
CARDINALITY_OFFSET = 10 
CARDINALITY_TEXT_MARGIN = 25 
TABLE_RESIZE_HANDLE_WIDTH = 10
MIN_TABLE_WIDTH = 120

# Default Theme Colors - These are base values, will be updated by theme selection
current_theme_settings = {
    "window_bg": QColor("#e8e8e8"), "view_bg": QColor("#f0f0f0"), "view_border": QColor("#cccccc"),
    "toolbar_bg": QColor("#dde0e5"), "toolbar_border": QColor("#c0c0c0"),
    "button_bg": QColor("#f0f2f5"), "button_border": QColor("#b0b5bf"),
    "button_hover_bg": QColor("#e0e5eb"), "button_pressed_bg": QColor("#c8cce0"),
    "button_checked_bg": QColor("#b8c0e0"), "button_checked_border": QColor("#8090a0"),
    "text_color": QColor(Qt.GlobalColor.black), "dialog_text_color": QColor(Qt.GlobalColor.black),
    "default_table_body_color": QColor(235, 235, 250), 
    "default_table_header_color": QColor(200, 200, 230),
}

light_theme = {
    "window_bg": QColor("#e8e8e8"), "view_bg": QColor("#f8f9fa"), "view_border": QColor("#ced4da"),
    "toolbar_bg": QColor("#e9ecef"), "toolbar_border": QColor("#ced4da"),
    "button_bg": QColor("#f8f9fa"), "button_border": QColor("#adb5bd"),
    "button_hover_bg": QColor("#e9ecef"), "button_pressed_bg": QColor("#dee2e6"),
    "button_checked_bg": QColor("#cfe2ff"), "button_checked_border": QColor("#9ec5fe"),
    "text_color": QColor(Qt.GlobalColor.black), "dialog_text_color": QColor(Qt.GlobalColor.black),
    "default_table_body_color": QColor(235, 235, 250), 
    "default_table_header_color": QColor(200, 200, 230),
}

dark_theme = {
    "window_bg": QColor("#2b2b2b"), "view_bg": QColor("#3c3c3c"), "view_border": QColor("#555555"),
    "toolbar_bg": QColor("#333333"), "toolbar_border": QColor("#505050"),
    "button_bg": QColor("#4f4f4f"), "button_border": QColor("#666666"),
    "button_hover_bg": QColor("#5a5a5a"), "button_pressed_bg": QColor("#646464"),
    "button_checked_bg": QColor("#4a5a7f"), "button_checked_border": QColor("#6c7ca0"),
    "text_color": QColor(Qt.GlobalColor.white), "dialog_text_color": QColor(Qt.GlobalColor.white),
    "default_table_body_color": QColor(60, 63, 65), 
    "default_table_header_color": QColor(83, 83, 83),
}


# --- Helper function to get standard icons ---
def get_standard_icon(standard_pixmap, fallback_text=""):
    icon = QApplication.style().standardIcon(standard_pixmap)
    if icon.isNull() and fallback_text: 
        pm = QPixmap(24,24) 
        pm.fill(Qt.GlobalColor.transparent) 
        painter = QPainter(pm)
        painter.setPen(current_theme_settings["text_color"]) 
        painter.drawText(pm.rect(), Qt.AlignmentFlag.AlignCenter, fallback_text)
        painter.end() 
        return QIcon(pm) 
    return icon

def snap_to_grid(value, grid_size):
    return round(value / grid_size) * grid_size

# --- Data Models ---
class Column:
    def __init__(self, name, data_type="TEXT", is_pk=False, is_fk=False, references_table=None, references_column=None, fk_relationship_type="N:1"):
        self.name = name
        self.data_type = data_type
        self.is_pk = is_pk
        self.is_fk = is_fk
        self.references_table = references_table 
        self.references_column = references_column 
        self.fk_relationship_type = fk_relationship_type


    def get_display_name(self):
        pk_str = "[PK] " if self.is_pk else ""
        fk_str = f"[FK] " if self.is_fk else ""
        return f"{pk_str}{fk_str}{self.name}"

    def __str__(self): 
        pk_str = "[PK] " if self.is_pk else ""
        fk_ref_str = ""
        if self.is_fk:
            if self.references_table and self.references_column:
                fk_ref_str = f"[FK ({self.fk_relationship_type}) -> {self.references_table}.{self.references_column}] "
            else:
                fk_ref_str = "[FK (incomplete)] " 
        return f"{pk_str}{fk_ref_str}{self.name}: {self.data_type}"

class Table:
    def __init__(self, name, x=50, y=50, width=DEFAULT_TABLE_WIDTH, 
                 body_color_hex=None, header_color_hex=None): 
        self.name = name
        self.columns = []
        self.x = snap_to_grid(x, GRID_SIZE)
        self.y = snap_to_grid(y, GRID_SIZE)
        self.width = snap_to_grid(width, GRID_SIZE) 
        self.graphic_item = None 
        self.body_color = QColor(body_color_hex) if body_color_hex else QColor(current_theme_settings["default_table_body_color"])
        self.header_color = QColor(header_color_hex) if header_color_hex else QColor(current_theme_settings["default_table_header_color"])


    def add_column(self, column):
        self.columns.append(column)

    def get_pk_column_names(self):
        return [col.name for col in self.columns if col.is_pk]
    
    def get_column_by_name(self, name):
        for col in self.columns:
            if col.name == name:
                return col
        return None
    
    def get_column_index(self, column_name):
        for i, col in enumerate(self.columns):
            if col.name == column_name:
                return i
        return -1

    def __str__(self):
        return self.name

class Relationship:
    def __init__(self, table1_name, table2_name, fk_column_name=None, pk_column_name=None, relationship_type="N:1"): 
        self.table1_name = table1_name # Table containing the FK
        self.table2_name = table2_name # Table containing the PK
        self.fk_column_name = fk_column_name 
        self.pk_column_name = pk_column_name 
        self.relationship_type = relationship_type 
        self.graphic_item = None 
        self.manual_bend_offset_x = None 

# --- Relationship Properties Dialog ---
class RelationshipDialog(QDialog):
    def __init__(self, relationship_data, parent_window_ref, parent=None): 
        super().__init__(parent)
        self.relationship_data = relationship_data
        self.main_window_ref = parent_window_ref
        self.setWindowTitle("Relationship Properties")
        self.setStyleSheet(f"QDialog {{ background-color: {current_theme_settings['window_bg'].name()}; }} QLabel, QComboBox {{ color: {current_theme_settings['dialog_text_color'].name()}; }}")


        layout = QFormLayout(self)

        self.from_label = QLabel(f"From (FK Side): {relationship_data.table1_name}.{relationship_data.fk_column_name}")
        self.to_label = QLabel(f"To (PK Side): {relationship_data.table2_name}.{relationship_data.pk_column_name}")
        
        self.type_combo = QComboBox()
        self.type_combo.addItems(["N:1", "1:1"]) 
        self.type_combo.setCurrentText(relationship_data.relationship_type or "N:1")

        layout.addRow(self.from_label)
        layout.addRow(self.to_label)
        layout.addRow("Relationship Type (FK table to PK table):", self.type_combo)

        self.buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttonBox.accepted.connect(self.accept_changes)
        self.buttonBox.rejected.connect(self.reject)
        layout.addWidget(self.buttonBox)

    def accept_changes(self):
        new_type = self.type_combo.currentText()
        self.relationship_data.relationship_type = new_type
        
        if self.main_window_ref and hasattr(self.main_window_ref, 'tables_data'):
            fk_table_obj = self.main_window_ref.tables_data.get(self.relationship_data.table1_name)
            if fk_table_obj:
                fk_col_obj = fk_table_obj.get_column_by_name(self.relationship_data.fk_column_name)
                if fk_col_obj:
                    fk_col_obj.fk_relationship_type = new_type 
                    if fk_table_obj.graphic_item: fk_table_obj.graphic_item.update()


        if self.relationship_data.graphic_item and hasattr(self.relationship_data.graphic_item, 'update_tooltip_and_paint'):
            self.relationship_data.graphic_item.update_tooltip_and_paint()
        self.accept()


# --- Orthogonal Relationship Line Graphic Item ---
class OrthogonalRelationshipLine(QGraphicsPathItem):
    def __init__(self, relationship_data, parent=None):
        super().__init__(parent)
        self.relationship_data = relationship_data
        self.relationship_data.graphic_item = self 
        self.setPen(QPen(QColor(70, 70, 110), 1.8)) 
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
        margin = CARDINALITY_OFFSET + CARDINALITY_TEXT_MARGIN 
        expanded_rect = path_rect.adjusted(-margin, -margin, margin, margin)
        if not self._handle_rect.isNull():
            expanded_rect = expanded_rect.united(self._handle_rect) 
        return expanded_rect


    def shape(self): 
        path_stroker = QPainterPathStroker() 
        path_stroker.setWidth(10) 
        shape_path = self.path()
        if shape_path.isEmpty(): 
            return QPainterPath()
            
        shape = path_stroker.createStroke(shape_path)
        if not self._handle_rect.isNull(): 
            shape.addRect(self._handle_rect)
        return shape

    def paint(self, painter, option, widget=None):
        super().paint(painter, option, widget) 
        
        if self.isSelected() and not self._handle_rect.isNull():
            painter.setBrush(QColor(100, 100, 255, 150))
            painter.setPen(QPen(QColor(50, 50, 150), 1))
            painter.drawRect(self._handle_rect)
        
        if len(self._path_points) == 4 and all(self._path_points): 
            p1 = self._path_points[0] 
            p2 = self._path_points[-1] 
            bend1_path = self._path_points[1] 
            bend2_path = self._path_points[2] 
            
            rel_type = self.relationship_data.relationship_type
            card1_symbol, card2_symbol = "?", "?" 

            if rel_type == "1:1": card1_symbol, card2_symbol = "1", "1"
            elif rel_type == "N:1": card1_symbol, card2_symbol = "N", "1" 
            elif rel_type == "1:N": card1_symbol, card2_symbol = "1", "N" 
            elif rel_type == "M:N": card1_symbol, card2_symbol = "M", "N" 

            painter.setPen(current_theme_settings["text_color"]) 
            font = QFont("Arial", 8, QFont.Weight.Bold)
            painter.setFont(font)
            font_metrics = QFontMetrics(font)

            # --- Draw card1 (at p1, FK side) ---
            text_rect1 = font_metrics.boundingRect(card1_symbol)
            is_p1_exit_horizontal = abs(p1.y() - bend1_path.y()) < 0.1 
            
            if is_p1_exit_horizontal: 
                y_offset1 = -text_rect1.height() / 2
                # If p1.x > bend1_path.x, line goes left from p1 (p1 is on the right of bend1), so text is to the left of p1
                # If p1.x < bend1_path.x, line goes right from p1 (p1 is on the left of bend1), so text is to the right of p1
                x_offset1 = -CARDINALITY_OFFSET - text_rect1.width() if p1.x() > bend1_path.x() else CARDINALITY_OFFSET
            else: # First segment is vertical
                x_offset1 = -text_rect1.width() / 2
                y_offset1 = -CARDINALITY_OFFSET - text_rect1.height() if p1.y() > bend1_path.y() else CARDINALITY_OFFSET + text_rect1.height()
            painter.drawText(p1 + QPointF(x_offset1, y_offset1), card1_symbol)

            # --- Draw card2 (at p2, PK side) ---
            text_rect2 = font_metrics.boundingRect(card2_symbol)
            is_p2_entry_horizontal = abs(p2.y() - bend2_path.y()) < 0.1

            if is_p2_entry_horizontal: 
                y_offset2 = -text_rect2.height() / 2
                # If p2.x < bend2_path.x, line comes from right to p2 (p2 is on the left of bend2), so text is to the right of p2
                # If p2.x > bend2_path.x, line comes from left to p2 (p2 is on the right of bend2), so text is to the left of p2
                x_offset2 = -CARDINALITY_OFFSET - text_rect2.width() if p2.x() < bend2_path.x() else CARDINALITY_OFFSET
            else: # Last segment is vertical
                x_offset2 = -text_rect2.width() / 2
                y_offset2 = -CARDINALITY_OFFSET - text_rect2.height() if p2.y() > bend2_path.y() else CARDINALITY_OFFSET + text_rect2.height()
            painter.drawText(p2 + QPointF(x_offset2, y_offset2), card2_symbol)


    def hoverMoveEvent(self, event: QGraphicsSceneHoverEvent): 
        if not self._handle_rect.isNull() and self._handle_rect.contains(event.pos()):
            if len(self._path_points) == 4:
                bend1 = self._path_points[1]
                bend2 = self._path_points[2]
                if abs(bend1.x() - bend2.x()) < 0.1: 
                    self.setCursor(Qt.CursorShape.SizeHorCursor)
                elif abs(bend1.y() - bend2.y()) < 0.1: 
                    self.setCursor(Qt.CursorShape.ArrowCursor) 
                else:
                    self.setCursor(Qt.CursorShape.ArrowCursor)
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        super().hoverMoveEvent(event)

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent): 
        if not self._handle_rect.isNull() and self._handle_rect.contains(event.pos()) and event.button() == Qt.MouseButton.LeftButton:
            self._dragging_handle = True
            self._drag_start_offset = self._handle_rect.center() - event.pos() 
            if len(self._path_points) == 4: 
                bend1 = self._path_points[1]
                bend2 = self._path_points[2]
                if abs(bend1.x() - bend2.x()) < 0.1: self.setCursor(Qt.CursorShape.SizeHorCursor)
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
            self.setCursor(Qt.CursorShape.ArrowCursor)
            if self.scene() and hasattr(self.scene().main_window, 'update_orthogonal_path'):
                 self.scene().main_window.update_orthogonal_path(self.relationship_data)
            event.accept()
            return
        super().mouseReleaseEvent(event)
    
    def mouseDoubleClickEvent(self, event: QGraphicsSceneMouseEvent): 
        if self.scene() and hasattr(self.scene().main_window, 'edit_relationship_properties'):
            self.scene().main_window.edit_relationship_properties(self.relationship_data)
            event.accept()
        else:
            super().mouseDoubleClickEvent(event)


# --- Dialog for Adding/Editing Table ---
class TableDialog(QDialog): 
    def __init__(self, parent_window, table_name="", columns_data=None): 
        super().__init__(parent_window)
        self.main_window_ref = parent_window 
        self.setWindowTitle("Table Details")
        self.setStyleSheet(f"QDialog {{ background-color: {current_theme_settings['window_bg'].name()}; }} "
                           f"QLabel, QCheckBox, QLineEdit, QComboBox {{ color: {current_theme_settings['dialog_text_color'].name()}; }}")

        
        self.layout = QVBoxLayout(self)

        # Table Name and Color Pickers
        top_form_layout = QFormLayout()
        self.tableNameInput = QLineEdit(table_name)
        top_form_layout.addRow("Table Name:", self.tableNameInput)

        self.bodyColorButton = QPushButton("Body Color")
        self.bodyColorButton.clicked.connect(self.choose_body_color)
        table_obj = parent_window.tables_data.get(table_name) if table_name else None
        self.currentBodyColor = table_obj.body_color if table_obj else QColor(current_theme_settings["default_table_body_color"])
        self.bodyColorButton.setStyleSheet(f"background-color: {self.currentBodyColor.name()}; color: {get_contrasting_text_color(self.currentBodyColor).name()}; padding: 5px;")
        
        self.headerColorButton = QPushButton("Header Color")
        self.headerColorButton.clicked.connect(self.choose_header_color)
        self.currentHeaderColor = table_obj.header_color if table_obj else QColor(current_theme_settings["default_table_header_color"])
        self.headerColorButton.setStyleSheet(f"background-color: {self.currentHeaderColor.name()}; color: {get_contrasting_text_color(self.currentHeaderColor).name()}; padding: 5px;")

        color_button_layout = QHBoxLayout()
        color_button_layout.addWidget(self.bodyColorButton)
        color_button_layout.addWidget(self.headerColorButton)
        top_form_layout.addRow(color_button_layout)
        
        self.layout.addLayout(top_form_layout)


        self.columnsLabel = QLabel("Columns:")
        self.layout.addWidget(self.columnsLabel)

        self.scrollWidget = QWidget() 
        self.columnsLayout = QVBoxLayout(self.scrollWidget) 
        self.column_widgets = [] 

        if columns_data:
            for col_data in columns_data:
                self.add_column_input_row(col_data.name, col_data.data_type, col_data.is_pk, col_data.is_fk, 
                                          col_data.references_table, col_data.references_column, col_data.fk_relationship_type, add_to_layout=True) 
        else:
            self.add_column_input_row(add_to_layout=True) 
        
        self.columnsLayout.addStretch(1) 

        self.scrollArea = QScrollArea()
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setWidget(self.scrollWidget) 
        self.layout.addWidget(self.scrollArea)
        
        self.btnAddColumn = QPushButton("Add Column")
        self.btnAddColumn.setIcon(get_standard_icon(QApplication.style().StandardPixmap.SP_FileDialogNewFolder, "+"))
        self.btnAddColumn.clicked.connect(self.on_add_column_button_clicked)
        self.layout.addWidget(self.btnAddColumn)

        self.buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setText("OK")
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancel")
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.layout.addWidget(self.buttonBox)
        
        self.setMinimumSize(750, 450) 
        # self.update_move_button_states() # Removed

    def choose_body_color(self):
        color = QColorDialog.getColor(self.currentBodyColor, self, "Choose Table Body Color")
        if color.isValid():
            self.currentBodyColor = color
            self.bodyColorButton.setStyleSheet(f"background-color: {self.currentBodyColor.name()}; color: {get_contrasting_text_color(self.currentBodyColor).name()}; padding: 5px;")

    def choose_header_color(self):
        color = QColorDialog.getColor(self.currentHeaderColor, self, "Choose Table Header Color")
        if color.isValid():
            self.currentHeaderColor = color
            self.headerColorButton.setStyleSheet(f"background-color: {self.currentHeaderColor.name()}; color: {get_contrasting_text_color(self.currentHeaderColor).name()}; padding: 5px;")


    def on_add_column_button_clicked(self):
        # Remove the stretch item before adding a new row
        stretch_item = self.columnsLayout.takeAt(self.columnsLayout.count() - 1)
        
        self.add_column_input_row(add_to_layout=True) 
        
        # Re-add the stretch item at the very end
        if stretch_item: # Check if stretch_item is not None (it might be if layout was empty)
            # If it was a layout (QVBoxLayout containing a stretch), add it back
            if isinstance(stretch_item.layout(), QVBoxLayout): 
                 self.columnsLayout.addLayout(stretch_item.layout())
            elif stretch_item.spacerItem(): # If it was just a spacer item
                 self.columnsLayout.addStretch(1)
            # else: # Fallback if it was something else, just add a new stretch
            #    self.columnsLayout.addStretch(1)
        else: # If no stretch item was found (e.g., layout was empty before adding first real item)
            self.columnsLayout.addStretch(1)

        # self.update_move_button_states() # Removed


    def add_column_input_row(self, name="", data_type="TEXT", is_pk=False, is_fk=False, 
                             ref_table_name="", ref_col_name="", fk_rel_type="N:1", add_to_layout=True): 
        
        row_container_widget = QWidget()
        main_row_v_layout = QVBoxLayout(row_container_widget)
        main_row_v_layout.setContentsMargins(0,0,0,0)
        main_row_v_layout.setSpacing(2) 

        top_row_widget = QWidget()
        top_row_h_layout = QHBoxLayout(top_row_widget)
        top_row_h_layout.setContentsMargins(0,0,0,0)

        font_metrics = QFontMetrics(self.font()) 
        button_height = font_metrics.height() + 4 
        button_width_char = font_metrics.horizontalAdvance("X") + 10 

        name_edit = QLineEdit(name)
        name_edit.setPlaceholderText("Column Name")
        type_combo = QComboBox()
        type_combo.addItems(["TEXT", "INTEGER", "REAL", "BLOB", "VARCHAR(255)", "BOOLEAN", "DATE", "DATETIME", "SERIAL", "UUID", "NUMERIC", "TIMESTAMP"])
        type_combo.setCurrentText(data_type)
        
        pk_checkbox = QCheckBox("PK")
        pk_checkbox.setChecked(is_pk)
        
        fk_checkbox = QCheckBox("FK") 
        fk_checkbox.setChecked(is_fk)

        btn_remove_col = QPushButton("X")
        btn_remove_col.setFixedSize(button_width_char, button_height) 
        
        # Removed move buttons
        # btn_move_up = QPushButton("↑")
        # btn_move_up.setFixedSize(button_width_char, button_height)
        # btn_move_down = QPushButton("↓")
        # btn_move_down.setFixedSize(button_width_char, button_height)

        # top_row_h_layout.addWidget(btn_move_up) # Removed
        # top_row_h_layout.addWidget(btn_move_down) # Removed
        top_row_h_layout.addWidget(name_edit, 2) 
        top_row_h_layout.addWidget(type_combo, 1)
        top_row_h_layout.addWidget(pk_checkbox)
        top_row_h_layout.addWidget(fk_checkbox)
        top_row_h_layout.addStretch(1) # Add stretch to push remove button to the right
        top_row_h_layout.addWidget(btn_remove_col)
        main_row_v_layout.addWidget(top_row_widget)

        fk_details_widget = QWidget()
        fk_details_layout = QHBoxLayout(fk_details_widget) 
        fk_details_layout.setContentsMargins(20, 2, 5, 2) # Indent FK details, keep left margin
        fk_details_layout.setSpacing(5)

        ref_table_combo = QComboBox()
        ref_table_combo.setPlaceholderText("Referenced Table")
        # ref_table_combo.addItem("") # No empty item if a table must be selected
        current_table_name_being_edited = self.tableNameInput.text()
        for t_name in self.main_window_ref.tables_data.keys():
            if t_name != current_table_name_being_edited:
                 ref_table_combo.addItem(t_name)
        if ref_table_name:
            ref_table_combo.setCurrentText(ref_table_name)
        elif ref_table_combo.count() > 0 : # Auto-select first if list is not empty
             ref_table_combo.setCurrentIndex(0)

        
        ref_col_combo = QComboBox()
        ref_col_combo.setPlaceholderText("Referenced PK Column")

        fk_rel_type_label = QLabel("Rel. Type:") 
        fk_rel_type_combo = QComboBox()
        fk_rel_type_combo.addItems(["N:1", "1:1"]) 
        fk_rel_type_combo.setCurrentText(fk_rel_type)

        fk_details_layout.addWidget(QLabel("-> Refers to:"),0, Qt.AlignmentFlag.AlignLeft)
        fk_details_layout.addWidget(ref_table_combo,1)
        fk_details_layout.addWidget(QLabel("."),0, Qt.AlignmentFlag.AlignCenter)
        fk_details_layout.addWidget(ref_col_combo,1)
        fk_details_layout.addWidget(fk_rel_type_label,0, Qt.AlignmentFlag.AlignRight) 
        fk_details_layout.addWidget(fk_rel_type_combo,1)
        # fk_details_layout.addStretch(1) # No stretch here, let it be compact
        
        fk_details_widget.setVisible(is_fk) 
        main_row_v_layout.addWidget(fk_details_widget)
        
        ref_table_combo.currentTextChanged.connect(
            lambda new_table_text, rcc=ref_col_combo, rtc=ref_table_combo: self.update_ref_col_combo(new_table_text, rcc, rtc)
        )
        
        # Initial population based on ref_table_name (if provided)
        self.update_ref_col_combo(ref_table_combo.currentText(), ref_col_combo, ref_table_combo)
        if ref_col_name: 
            ref_col_combo.setCurrentText(ref_col_name)
        
        fk_checkbox.toggled.connect(fk_details_widget.setVisible)

        row_widgets_dict = { 
            "container_widget": row_container_widget, 
            "name": name_edit, "type": type_combo, 
            "pk": pk_checkbox, "fk": fk_checkbox,
            "ref_table_combo": ref_table_combo, "ref_col_combo": ref_col_combo,
            "fk_rel_type_combo": fk_rel_type_combo, 
            "remove_button": btn_remove_col,
            # "up_button": btn_move_up, "down_button": btn_move_down, # Removed
            "fk_details_widget": fk_details_widget 
        }
        
        btn_remove_col.clicked.connect(lambda checked=False, rw=row_widgets_dict: self.remove_column_input_row(rw))
        # btn_move_up.clicked.connect(lambda checked=False, rw=row_widgets_dict: self.move_column_row(rw, -1)) # Removed
        # btn_move_down.clicked.connect(lambda checked=False, rw=row_widgets_dict: self.move_column_row(rw, 1)) # Removed
        
        if add_to_layout: 
            self.columnsLayout.insertWidget(self.columnsLayout.count() -1, row_container_widget)
        
        if not any(cw["container_widget"] == row_container_widget for cw in self.column_widgets): 
            self.column_widgets.append(row_widgets_dict)
        
        # self.update_move_button_states() # Removed


    # def move_column_row(self, row_widgets_dict, direction): # Removed
    #     pass

    # def update_move_button_states(self): # Removed
    #     pass


    def update_ref_col_combo(self, table_name, col_combo_to_update, table_combo_source):
        current_ref_col = col_combo_to_update.currentText() 
        col_combo_to_update.clear()
        
        if table_name and table_name in self.main_window_ref.tables_data:
            target_table_obj = self.main_window_ref.tables_data[table_name]
            pk_columns = target_table_obj.get_pk_column_names()
            if pk_columns:
                col_combo_to_update.addItems(pk_columns)
                if current_ref_col in pk_columns:
                    col_combo_to_update.setCurrentText(current_ref_col)
                elif pk_columns: 
                    col_combo_to_update.setCurrentIndex(0) 
                col_combo_to_update.setEnabled(True)
            else:
                col_combo_to_update.setEnabled(False) 
        else: 
            col_combo_to_update.setEnabled(False)


    def remove_column_input_row(self, row_widgets_to_remove):
        if row_widgets_to_remove in self.column_widgets:
            container = row_widgets_to_remove["container_widget"]
            layout = container.layout()
            if layout:
                while layout.count():
                    item = layout.takeAt(0)
                    widget = item.widget()
                    if widget:
                        widget.deleteLater()
            container.deleteLater() 
            self.column_widgets.remove(row_widgets_to_remove)
            self.scrollWidget.adjustSize() 
            # self.update_move_button_states() # Removed


    def get_table_data(self):
        table_name = self.tableNameInput.text().strip()
        columns = []
        # Iterate based on the visual order in columnsLayout
        ordered_columns_data = []
        for i in range(self.columnsLayout.count() -1): 
            item_widget = self.columnsLayout.itemAt(i).widget()
            for cw_dict in self.column_widgets:
                if cw_dict["container_widget"] == item_widget:
                    ordered_columns_data.append(cw_dict)
                    break
        
        for col_row_widgets in ordered_columns_data: 
            name = col_row_widgets["name"].text().strip()
            data_type = col_row_widgets["type"].currentText()
            is_pk = col_row_widgets["pk"].isChecked()
            is_fk = col_row_widgets["fk"].isChecked() 
            ref_table = col_row_widgets["ref_table_combo"].currentText() if is_fk else None
            ref_col = col_row_widgets["ref_col_combo"].currentText() if is_fk and ref_table and col_row_widgets["ref_col_combo"].count() > 0 and col_row_widgets["ref_col_combo"].currentText() != "No PK defined" else None
            fk_rel_type = col_row_widgets["fk_rel_type_combo"].currentText() if is_fk else "N:1" 

            if is_fk and (not ref_table or not ref_col): 
                is_fk = False 
                ref_table = None 
                ref_col = None 
                fk_rel_type = "N:1" 
            if name: 
                columns.append(Column(name, data_type, is_pk, is_fk, ref_table, ref_col, fk_rel_type))
        
        # Get table colors
        body_color = self.currentBodyColor.name()
        header_color = self.currentHeaderColor.name()
        return table_name, columns, body_color, header_color


# --- Graphical Representation of a Table ---
class TableGraphicItem(QGraphicsItem):
    def __init__(self, table_data_object, parent=None):
        super().__init__(parent)
        self.table_data = table_data_object 
        self.table_data.graphic_item = self 
        
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges) 
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsScenePositionChanges)
        self.setAcceptHoverEvents(True) # For resize cursor

        self.width = self.table_data.width # Use width from data model
        self.header_height = TABLE_HEADER_HEIGHT
        self.column_row_height = COLUMN_HEIGHT
        self.padding = PADDING
        
        self._calculate_height()
        self.setPos(self.table_data.x, self.table_data.y) 
        
        self._resizing_width = False
        self._resize_start_x = 0
        self._initial_width_on_resize = 0


    def _calculate_height(self):
        num_columns = len(self.table_data.columns)
        self.height = self.header_height + (num_columns * self.column_row_height) + self.padding * (1 if num_columns > 0 else 2) 
        if num_columns == 0: 
             self.height = self.header_height + self.padding 

    def boundingRect(self):
        # Add a small margin for the resize handle area to be included in repaint
        return QRectF(-TABLE_RESIZE_HANDLE_WIDTH / 2, 0, self.width + TABLE_RESIZE_HANDLE_WIDTH, self.height)


    def paint(self, painter, option, widget=None):
        self._calculate_height() 
        
        # Main table body
        body_rect = QRectF(0, 0, self.width, self.height)
        path = QPainterPath()
        path.addRoundedRect(body_rect, 7, 7) 
        painter.setBrush(QBrush(self.table_data.body_color)) # Use custom body color
        if self.isSelected():
            painter.setPen(QPen(QColor(100, 100, 200), 2.5)) 
        else:
            painter.setPen(QPen(QColor(60,60,70), 1.5)) 
        painter.drawPath(path)

        header_rect = QRectF(0, 0, self.width, self.header_height)
        painter.setBrush(QBrush(self.table_data.header_color)) # Use custom header color
        painter.drawRect(header_rect) 
        
        # Determine text color based on header background for contrast
        header_text_color = get_contrasting_text_color(self.table_data.header_color)
        painter.setPen(header_text_color)
        font = QFont("Arial", 10, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(header_rect.adjusted(self.padding, 0, -self.padding, 0), 
                         Qt.AlignmentFlag.AlignCenter, self.table_data.name)

        # Determine text color for columns based on body background
        column_text_color = get_contrasting_text_color(self.table_data.body_color)
        painter.setPen(column_text_color)
        col_font = QFont("Arial", 9) 
        painter.setFont(col_font)
        
        current_y = self.header_height + self.padding / 2
        for column_idx, column in enumerate(self.table_data.columns):
            col_name_text = column.get_display_name()
            col_type_text = column.data_type

            name_rect = QRectF(self.padding / 2, current_y, 
                               self.width * 0.6 - self.padding, self.column_row_height) 
            painter.drawText(name_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, col_name_text)

            type_rect = QRectF(self.width * 0.6, current_y,
                               self.width * 0.4 - self.padding / 2, self.column_row_height) 
            painter.drawText(type_rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, col_type_text)
            
            current_y += self.column_row_height
            if column_idx < len(self.table_data.columns) - 1: 
                 painter.setPen(QPen(QColor(210,210,220), 0.8)) 
                 painter.drawLine(QPointF(self.padding / 2, current_y), QPointF(self.width - self.padding/2, current_y))
                 painter.setPen(column_text_color) # Reset pen to column text color
        
        # Draw resize handle if selected
        if self.isSelected():
            handle_x = self.width - TABLE_RESIZE_HANDLE_WIDTH / 2
            handle_y = self.height / 2 - TABLE_RESIZE_HANDLE_WIDTH /2
            painter.setBrush(QColor(150,150,200, 180))
            painter.setPen(QPen(QColor(80,80,120), 1))
            painter.drawRect(QRectF(handle_x, handle_y, TABLE_RESIZE_HANDLE_WIDTH, TABLE_RESIZE_HANDLE_WIDTH))


    def get_resize_handle_rect(self):
        """Returns the QRectF for the resize handle in item coordinates."""
        return QRectF(self.width - TABLE_RESIZE_HANDLE_WIDTH, 0, TABLE_RESIZE_HANDLE_WIDTH, self.height)


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
        
        # Determine exit side based on other table's position OR manual bend offset
        exit_right = True # Default exit side
        if other_table_graphic: # If we have a target table
            if other_table_graphic.sceneBoundingRect().center().x() < self.sceneBoundingRect().center().x():
                exit_right = False # Other table is to the left
        
        # If a manual bend offset is defined and it's on the "opposite" side of the default exit, flip the exit
        if self.scene() and self.scene().main_window: # Check if scene and main_window exist
            # Find the specific relationship this attachment point belongs to
            rel = None
            for r_data in self.scene().main_window.relationships_data:
                if (r_data.table1_name == self.table_data.name and r_data.fk_column_name == from_column_name) or \
                   (r_data.table2_name == self.table_data.name and r_data.pk_column_name == from_column_name): # from_column_name could be a PK if this is table2
                    rel = r_data
                    break
            
            if rel and rel.manual_bend_offset_x is not None:
                # If default exit is right, but manual bend is to the left of my center, exit left
                if exit_right and rel.manual_bend_offset_x < self.sceneBoundingRect().center().x():
                    exit_right = False
                # If default exit is left, but manual bend is to the right of my center, exit right
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
            self.setCursor(Qt.CursorShape.SizeHorCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent):
        if self._resizing_width:
            delta_x = event.scenePos().x() - self._resize_start_x
            new_width = self._initial_width_on_resize + delta_x
            new_width = max(MIN_TABLE_WIDTH, snap_to_grid(new_width, GRID_SIZE)) # Snap to grid and enforce min width

            if self.width != new_width:
                self.prepareGeometryChange() # Notify system that geometry is about to change
                self.width = new_width
                self.table_data.width = new_width # Update data model
                self._calculate_height() # Height might change if width affects column wrapping (not implemented, but good practice)
                self.update() # Request a repaint
                if self.scene() and hasattr(self.scene(), 'update_relationships_for_table'):
                    self.scene().update_relationships_for_table(self.table_data.name)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent):
        if self._resizing_width:
            self._resizing_width = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            # Final update of relationships if needed, though it should happen during move
            if self.scene() and hasattr(self.scene(), 'update_relationships_for_table'):
                self.scene().update_relationships_for_table(self.table_data.name)
            event.accept()
            return
        super().mouseReleaseEvent(event)


    def mouseDoubleClickEvent(self, event):
        main_window = self.scene().main_window 
        if not main_window: return super().mouseDoubleClickEvent(event)

        # Store old column definitions for comparison, especially PKs and FKs
        old_columns_copy = [Column(c.name, c.data_type, c.is_pk, c.is_fk, c.references_table, c.references_column, c.fk_relationship_type) for c in self.table_data.columns]
        old_table_name = self.table_data.name

        dialog = TableDialog(main_window, self.table_data.name, old_columns_copy) # Pass copy
        if dialog.exec():
            new_name, new_columns_data, body_color_hex, header_color_hex = dialog.get_table_data() # Get colors
            if not new_name:
                QMessageBox.warning(main_window, "Warning", "Table name cannot be empty.")
                return

            # Update table colors
            self.table_data.body_color = QColor(body_color_hex)
            self.table_data.header_color = QColor(header_color_hex)


            # --- Handle Table Rename ---
            if new_name != old_table_name:
                if new_name in main_window.tables_data:
                    QMessageBox.warning(main_window, "Warning", f"Table with name '{new_name}' already exists.")
                    return 
                main_window.tables_data.pop(old_table_name)
                self.table_data.name = new_name
                main_window.tables_data[new_name] = self.table_data
                main_window.update_relationship_table_names(old_table_name, new_name)
                main_window.update_fk_references_to_table(old_table_name, new_name) 

            # --- Handle Column Changes (PKs, FKs, Names) ---
            # 1. Update PK name changes in referencing FKs
            for old_col_idx, old_col in enumerate(old_columns_copy):
                new_col_at_old_idx = new_columns_data[old_col_idx] if old_col_idx < len(new_columns_data) else None
                
                if old_col.is_pk:
                    if new_col_at_old_idx and old_col.name != new_col_at_old_idx.name and new_col_at_old_idx.is_pk : 
                        main_window.update_fk_references_to_pk(
                            self.table_data.name, 
                            old_col.name, 
                            new_col_at_old_idx.name
                        )
                    elif not new_col_at_old_idx or not new_col_at_old_idx.is_pk: 
                         main_window.update_fk_references_to_pk(
                            self.table_data.name, 
                            old_col.name, 
                            None 
                        )


            self.table_data.columns = new_columns_data 
            
            # 2. Re-evaluate and update relationships based on new FK definitions
            main_window.remove_relationships_for_table(self.table_data.name, old_columns_copy) # Pass old columns to identify specific FKs to remove
            for col in self.table_data.columns: 
                if col.is_fk and col.references_table and col.references_column:
                    target_table_obj = main_window.tables_data.get(col.references_table)
                    if target_table_obj:
                        target_pk_col_obj = target_table_obj.get_column_by_name(col.references_column)
                        if target_pk_col_obj and target_pk_col_obj.is_pk:
                            main_window.create_relationship(self.table_data, target_table_obj, col.name, col.references_column, col.fk_relationship_type)
                        else: 
                            col.is_fk = False; col.references_table = None; col.references_column = None 
            
            main_window.update_all_relationships_graphics() 
            self.prepareGeometryChange() 
            self._calculate_height() 
            self.update() 
        super().mouseDoubleClickEvent(event)

# --- Custom Graphics Scene ---
class ERDGraphicsScene(QGraphicsScene):
    def __init__(self, parent_window=None): 
        super().__init__(parent_window) 
        self.line_in_progress = None
        self.start_item_for_line = None
        self.start_column_for_line = None 
        self.main_window = parent_window 
        self.grid_pen = QPen(QColor(200, 200, 200, 60), 0.5, Qt.PenStyle.SolidLine) 

    def drawBackground(self, painter, rect):
        super().drawBackground(painter, rect)
        
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

        items = self.items(scene_pos, Qt.ItemSelectionMode.IntersectsItemShape, Qt.SortOrder.DescendingOrder, view.transform())
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
        items_at_click = self.items(event.scenePos())
        for item in items_at_click:
            if isinstance(item, OrthogonalRelationshipLine):
                if hasattr(self.main_window, 'edit_relationship_properties'):
                    self.main_window.edit_relationship_properties(item.relationship_data)
                    event.accept()
                    return
        
        table_item_at_click, _ = self.get_item_and_column_at(event.scenePos()) 
        if table_item_at_click is None: 
            scene_pos = event.scenePos()
            snapped_x = snap_to_grid(scene_pos.x() - DEFAULT_TABLE_WIDTH / 2, GRID_SIZE) 
            snapped_y = snap_to_grid(scene_pos.y() - TABLE_HEADER_HEIGHT / 2, GRID_SIZE)
            self.main_window.handle_add_table_button(pos=QPointF(snapped_x, snapped_y))
        else: 
            super().mouseDoubleClickEvent(event) 


    def mousePressEvent(self, event):
        if self.main_window and self.main_window.drawing_relationship_mode: 
            target_table_item, target_column_obj = self.get_item_and_column_at(event.scenePos())
            
            if not self.start_item_for_line: 
                if target_table_item and target_column_obj:
                    self.start_item_for_line = target_table_item
                    self.start_column_for_line = target_column_obj 

                    self.line_in_progress = QGraphicsPathItem() 
                    self.line_in_progress.setPen(QPen(QColor(255,0,0,150), 2, Qt.PenStyle.DashLine))
                    self.line_in_progress.setZValue(10) 
                    self.addItem(self.line_in_progress)
                    
                    start_col_idx = self.start_item_for_line.table_data.get_column_index(self.start_column_for_line.name)
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
            else: 
                if target_table_item and target_column_obj and target_table_item != self.start_item_for_line:
                    source_table = self.start_item_for_line.table_data
                    source_column = self.start_column_for_line
                    dest_table = target_table_item.table_data
                    dest_column = target_column_obj

                    fk_table, fk_col, pk_table, pk_col_obj = None, None, None, None

                    if source_column.is_pk and not dest_column.is_pk: 
                        fk_table, fk_col = dest_table, dest_column
                        pk_table, pk_col_obj = source_table, source_column
                    elif not source_column.is_pk and dest_column.is_pk: 
                        fk_table, fk_col = source_table, source_column
                        pk_table, pk_col_obj = dest_table, dest_column
                    elif source_column.is_pk and dest_column.is_pk:
                         QMessageBox.warning(self.main_window, "Invalid Connection", "Cannot directly connect two Primary Keys. One column must be a Foreign Key.")
                         self.main_window.reset_drawing_mode(); return
                    else: 
                        QMessageBox.warning(self.main_window, "Invalid Connection", 
                                            f"Target column '{dest_column.name}' in '{dest_table.name}' must be a Primary Key, or source column '{source_column.name}' in '{source_table.name}' must be a Primary Key.")
                        self.main_window.reset_drawing_mode(); return


                    if fk_col.is_fk and \
                       (fk_col.references_table != pk_table.name or \
                        fk_col.references_column != pk_col_obj.name):
                        reply = QMessageBox.question(self.main_window, "Confirm FK Change",
                                                     f"Column '{fk_col.name}' in '{fk_table.name}' is already an FK. Change it to reference '{pk_table.name}.{pk_col_obj.name}'?",
                                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                        if reply == QMessageBox.StandardButton.No:
                            self.main_window.reset_drawing_mode(); return
                    
                    fk_col.is_fk = True
                    fk_col.references_table = pk_table.name
                    fk_col.references_column = pk_col_obj.name
                    fk_col.fk_relationship_type = "N:1" # Default when drawing, can be changed in dialog
                    
                    if fk_table.graphic_item: fk_table.graphic_item.update()
                    
                    self.main_window.create_relationship(fk_table, pk_table, fk_col.name, pk_col_obj.name, fk_col.fk_relationship_type)
                
                else:
                    print(f"Relationship drawing: Second click target was not a valid column on a different table.")
                
                self.main_window.reset_drawing_mode()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.line_in_progress and self.start_item_for_line and self.start_column_for_line:
            start_col_idx = self.start_item_for_line.table_data.get_column_index(self.start_column_for_line.name)
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
                 start_pos = self.start_item_for_line.get_attachment_point_to_pos(event.scenePos())


            path = QPainterPath(start_pos)
            path.lineTo(event.scenePos()) 
            self.line_in_progress.setPath(path)
        else:
            super().mouseMoveEvent(event)

    def update_relationships_for_table(self, table_name_moved):
        if not self.main_window: return
        self.main_window.update_all_relationships_graphics()

# --- Main Application Window ---
class ERDCanvasWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_file_path = None
        self.current_theme = "light" # Default theme
        self.user_default_table_body_color = None
        self.user_default_table_header_color = None
        self.update_theme_settings() # Apply initial theme defaults
        self.update_window_title() 

        self.setGeometry(100, 100, 1300, 850) 

        self.tables_data = {} 
        self.relationships_data = [] 
        self.drawing_relationship_mode = False 

        self.scene = ERDGraphicsScene(self) 
        self.scene.setSceneRect(0, 0, 4000, 3000) 

        self.view = QGraphicsView(self.scene, self)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing) 
        self.view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag) 
        self.view.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse) 
        self.view.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter) 
        self.view.setInteractive(True) 
        self.view.wheelEvent = self.view_wheel_event


        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget) 

        self.create_toolbar_and_menus() # Renamed for clarity
        main_layout.addWidget(self.toolbar) 

        main_layout.addWidget(self.view, 1) 
        self.setCentralWidget(main_widget)

        print("Main window created.")
        self.apply_styles() # Apply initial styles based on theme

    def update_theme_settings(self):
        """Updates the global current_theme_settings based on self.current_theme"""
        global current_theme_settings # Allow modification of the global dict
        if self.current_theme == "dark":
            current_theme_settings = dark_theme.copy() # Use a copy to avoid modifying the original
        else: # Default to light theme (includes "system" for now)
            current_theme_settings = light_theme.copy()
        
        # Apply user-defined defaults if they exist
        if self.user_default_table_body_color:
            current_theme_settings["default_table_body_color"] = self.user_default_table_body_color
        if self.user_default_table_header_color:
            current_theme_settings["default_table_header_color"] = self.user_default_table_header_color


    def set_theme(self, theme_name):
        self.current_theme = theme_name
        self.update_theme_settings()
        self.apply_styles() # Re-apply stylesheet
        # Update existing tables to new theme defaults if they were using old defaults
        for table_data in self.tables_data.values():
            # If table color is one of the old defaults, update to new default
            # This logic is a bit simplistic and assumes user hasn't picked a color identical to an old default
            if theme_name == "dark":
                if table_data.body_color == light_theme["default_table_body_color"]:
                    table_data.body_color = QColor(current_theme_settings["default_table_body_color"])
                if table_data.header_color == light_theme["default_table_header_color"]:
                    table_data.header_color = QColor(current_theme_settings["default_table_header_color"])
            else: # Switching to light
                if table_data.body_color == dark_theme["default_table_body_color"]:
                    table_data.body_color = QColor(current_theme_settings["default_table_body_color"])
                if table_data.header_color == dark_theme["default_table_header_color"]:
                    table_data.header_color = QColor(current_theme_settings["default_table_header_color"])

            if table_data.graphic_item:
                table_data.graphic_item.update()
        self.scene.update() # Redraw scene background if needed
        print(f"Theme set to: {theme_name}")


    def update_window_title(self):
        title = "ERD Design Tool"
        if self.current_file_path:
            title += f" - {os.path.basename(self.current_file_path)}"
        else:
            title += " - Untitled"
        self.setWindowTitle(title)


    def view_wheel_event(self, event):
        factor = 1.15 
        if event.angleDelta().y() > 0: 
            self.view.scale(factor, factor)
        else: 
            self.view.scale(1.0 / factor, 1.0 / factor)
        event.accept()


    def apply_styles(self):
        # Use colors from current_theme_settings
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {current_theme_settings['window_bg'].name()};
            }}
            QToolBar {{
                background-color: {current_theme_settings['toolbar_bg'].name()};
                border: 1px solid {current_theme_settings['toolbar_border'].name()};
                padding: 5px; spacing: 8px; min-width: 180px; 
            }}
            QToolBar QToolButton {{ 
                background-color: {current_theme_settings['button_bg'].name()};
                border: 1px solid {current_theme_settings['button_border'].name()};
                border-radius: 4px; padding: 8px 5px; margin: 2px;
                min-width: 150px; text-align: left; 
                color: {current_theme_settings['text_color'].name()};
            }}
            QToolBar QToolButton:hover {{ background-color: {current_theme_settings['button_hover_bg'].name()}; }}
            QToolBar QToolButton:pressed {{ background-color: {current_theme_settings['button_pressed_bg'].name()}; }}
            QToolBar QToolButton:checked {{ 
                background-color: {current_theme_settings['button_checked_bg'].name()}; 
                border: 1px solid {current_theme_settings['button_checked_border'].name()};
            }}
            QPushButton {{ 
                background-color: {current_theme_settings['button_bg'].name()};
                border: 1px solid {current_theme_settings['button_border'].name()};
                border-radius: 4px; padding: 5px 10px; min-width: 80px;
                color: {current_theme_settings['text_color'].name()};
            }}
            QPushButton:hover {{ background-color: {current_theme_settings['button_hover_bg'].name()}; }}
            QPushButton:pressed {{ background-color: {current_theme_settings['button_pressed_bg'].name()}; }}
            QComboBox, QLineEdit {{
                border: 1px solid {current_theme_settings['button_border'].name()}; 
                border-radius: 3px; padding: 3px; min-height: 20px; 
                background-color: {current_theme_settings['view_bg'].name()}; /* Match view for input fields */
                color: {current_theme_settings['text_color'].name()};
            }}
            QComboBox QAbstractItemView {{ /* Dropdown list part of ComboBox */
                background-color: {current_theme_settings['view_bg'].name()};
                color: {current_theme_settings['text_color'].name()};
                selection-background-color: {current_theme_settings['button_checked_bg'].name()};
            }}
            QScrollArea {{ border: 1px solid {current_theme_settings['toolbar_border'].name()}; }}
            QLabel {{ padding: 2px; color: {current_theme_settings['dialog_text_color'].name()}; }}
            QDialog {{ background-color: {current_theme_settings['window_bg'].name()}; }}
        """)
        self.view.setStyleSheet(f"background-color: {current_theme_settings['view_bg'].name()}; border: 1px solid {current_theme_settings['view_border'].name()};")
        self.scene.setBackgroundBrush(QBrush(current_theme_settings['view_bg']))


    def create_toolbar_and_menus(self): # Renamed
        # --- Toolbar ---
        self.toolbar = QToolBar("Main Toolbar")
        self.toolbar.setMovable(False) 
        self.toolbar.setOrientation(Qt.Orientation.Vertical) 
        self.toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon) 
        self.toolbar.setIconSize(QSize(24,24)) 
        self.addToolBar(Qt.ToolBarArea.LeftToolBarArea, self.toolbar)

        actionNew = QAction(get_standard_icon(QApplication.style().StandardPixmap.SP_FileIcon, "New"), "&New Diagram", self)
        actionNew.triggered.connect(self.new_diagram)
        self.toolbar.addAction(actionNew)

        self.toolbar.addSeparator()

        actionSave = QAction(get_standard_icon(QApplication.style().StandardPixmap.SP_DialogSaveButton, "Save"), "&Save", self)
        actionSave.setShortcut("Ctrl+S")
        actionSave.triggered.connect(self.save_file)
        self.toolbar.addAction(actionSave)
        
        actionSaveAs = QAction(get_standard_icon(QApplication.style().StandardPixmap.SP_DriveHDIcon, "Save As"), "Save &As...", self) 
        actionSaveAs.triggered.connect(self.save_file_as)
        self.toolbar.addAction(actionSaveAs)

        actionImportCSV = QAction(get_standard_icon(QApplication.style().StandardPixmap.SP_ArrowDown, "Import"), "&Import CSV", self)
        actionImportCSV.setShortcut("Ctrl+O")
        actionImportCSV.triggered.connect(self.handle_import_csv_button)
        self.toolbar.addAction(actionImportCSV)
        
        self.toolbar.addSeparator()

        self.actionAddTable = QAction(get_standard_icon(QApplication.style().StandardPixmap.SP_FileDialogNewFolder, "Add Tbl"), "Add &Table", self)
        self.actionAddTable.triggered.connect(lambda: self.handle_add_table_button()) 
        self.toolbar.addAction(self.actionAddTable)
        
        self.actionDrawRelationship = QAction(get_standard_icon(QApplication.style().StandardPixmap.SP_ArrowForward, "Link"), "&Draw Relationship", self)
        self.actionDrawRelationship.setCheckable(True)
        self.actionDrawRelationship.triggered.connect(self.toggle_relationship_mode_action)
        self.toolbar.addAction(self.actionDrawRelationship)

        # --- Menus ---
        menubar = self.menuBar()
        fileMenu = menubar.addMenu("&File")
        fileMenu.addAction(actionNew)
        fileMenu.addAction(actionSave)
        fileMenu.addAction(actionSaveAs)
        fileMenu.addAction(actionImportCSV)
        fileMenu.addSeparator()
        actionExit = QAction(get_standard_icon(QApplication.style().StandardPixmap.SP_DialogCloseButton, "Exit"), "E&xit", self)
        actionExit.triggered.connect(self.close)
        fileMenu.addAction(actionExit)

        viewMenu = menubar.addMenu("&View")
        themeMenu = viewMenu.addMenu("&Theme")
        
        lightThemeAction = QAction("Light", self, checkable=True)
        lightThemeAction.setChecked(self.current_theme == "light")
        lightThemeAction.triggered.connect(lambda: self.set_theme("light"))
        themeMenu.addAction(lightThemeAction)

        darkThemeAction = QAction("Dark", self, checkable=True)
        darkThemeAction.setChecked(self.current_theme == "dark")
        darkThemeAction.triggered.connect(lambda: self.set_theme("dark"))
        themeMenu.addAction(darkThemeAction)
        
        # Action Group for themes
        theme_action_group = QActionGroup(self)
        theme_action_group.addAction(lightThemeAction)
        theme_action_group.addAction(darkThemeAction)
        theme_action_group.setExclusive(True)


        settingsMenu = menubar.addMenu("&Settings")
        actionDefaultColors = QAction("Default Table Colors...", self)
        actionDefaultColors.triggered.connect(self.open_default_colors_dialog)
        settingsMenu.addAction(actionDefaultColors)


    def open_default_colors_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Set Default Table Colors")
        dialog.setStyleSheet(f"QDialog {{ background-color: {current_theme_settings['window_bg'].name()}; }} QLabel, QPushButton {{ color: {current_theme_settings['dialog_text_color'].name()}; }}")

        layout = QFormLayout(dialog)

        body_button = QPushButton(f"Body: {self.user_default_table_body_color.name() if self.user_default_table_body_color else current_theme_settings['default_table_body_color'].name()}")
        body_button.setStyleSheet(f"background-color: {(self.user_default_table_body_color or current_theme_settings['default_table_body_color']).name()}; color: {get_contrasting_text_color(self.user_default_table_body_color or current_theme_settings['default_table_body_color']).name()}; padding: 5px;")
        
        header_button = QPushButton(f"Header: {self.user_default_table_header_color.name() if self.user_default_table_header_color else current_theme_settings['default_table_header_color'].name()}")
        header_button.setStyleSheet(f"background-color: {(self.user_default_table_header_color or current_theme_settings['default_table_header_color']).name()}; color: {get_contrasting_text_color(self.user_default_table_header_color or current_theme_settings['default_table_header_color']).name()}; padding: 5px;")

        def pick_body():
            color = QColorDialog.getColor(self.user_default_table_body_color or current_theme_settings['default_table_body_color'], self)
            if color.isValid():
                self.user_default_table_body_color = color
                body_button.setText(f"Body: {color.name()}")
                body_button.setStyleSheet(f"background-color: {color.name()}; color: {get_contrasting_text_color(color).name()}; padding: 5px;")
                self.update_theme_settings() 
                self.set_theme(self.current_theme) 

        def pick_header():
            color = QColorDialog.getColor(self.user_default_table_header_color or current_theme_settings['default_table_header_color'], self)
            if color.isValid():
                self.user_default_table_header_color = color
                header_button.setText(f"Header: {color.name()}")
                header_button.setStyleSheet(f"background-color: {color.name()}; color: {get_contrasting_text_color(color).name()}; padding: 5px;")
                self.update_theme_settings()
                self.set_theme(self.current_theme)


        body_button.clicked.connect(pick_body)
        header_button.clicked.connect(pick_header)

        layout.addRow("Default Table Body Color:", body_button)
        layout.addRow("Default Table Header Color:", header_button)
        
        buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttonBox.accepted.connect(dialog.accept)
        layout.addWidget(buttonBox)
        dialog.exec()


    def new_diagram(self):
        # Optional: Add a confirmation dialog if there are unsaved changes
        self.scene.clear() 
        self.tables_data.clear()
        self.relationships_data.clear()
        self.current_file_path = None
        self.update_window_title()
        print("New diagram created.")

    def save_file(self):
        if self.current_file_path:
            self.export_to_csv(self.current_file_path) 
        else:
            self.save_file_as()

    def save_file_as(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save ERD File", self.current_file_path or "", "CSV Files (*.csv);;All Files (*)") # Changed filter
        if path:
            self.export_to_csv(path) 
            self.current_file_path = path
            self.update_window_title()


    def reset_drawing_mode(self):
        """Helper to reset relationship drawing state."""
        if self.scene.line_in_progress:
            self.scene.removeItem(self.scene.line_in_progress)
            self.scene.line_in_progress = None
        self.scene.start_item_for_line = None
        self.scene.start_column_for_line = None
        if self.actionDrawRelationship: 
            self.actionDrawRelationship.setChecked(False)
        self.toggle_relationship_mode_action(False)


    def toggle_relationship_mode_action(self, checked):
        self.drawing_relationship_mode = checked 
        if checked:
            self.view.setDragMode(QGraphicsView.DragMode.NoDrag) 
            print("Relationship drawing mode: Active. Click on the source column (FK or PK).")
        else:
            self.view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            if self.scene.line_in_progress:
                self.scene.removeItem(self.scene.line_in_progress)
                self.scene.line_in_progress = None
            self.scene.start_item_for_line = None 
            self.scene.start_column_for_line = None
            print("Relationship drawing mode: Off.")


    def handle_add_table_button(self, table_name_prop=None, columns_prop=None, pos=None, width_prop=None, body_color_hex=None, header_color_hex=None): # Added color_props
        if table_name_prop: 
            table_name = table_name_prop
            columns = columns_prop
            if not table_name: return None 
            if table_name in self.tables_data: 
                print(f"Import/Add: Table '{table_name}' already exists. Skipping.")
                return None 
        else: 
            dialog = TableDialog(self, table_name_prop if table_name_prop else "") 
            if not dialog.exec(): return None 
            table_name, columns, body_color_hex, header_color_hex = dialog.get_table_data() # Get colors
            if not table_name:
                QMessageBox.warning(self, "Warning", "Table name cannot be empty.")
                return None
            if table_name in self.tables_data: 
                QMessageBox.warning(self, "Warning", f"Table with name '{table_name}' already exists.")
                return None
        
        if pos:
            default_x = snap_to_grid(pos.x(), GRID_SIZE)
            default_y = snap_to_grid(pos.y(), GRID_SIZE)
        else: 
            visible_rect = self.view.mapToScene(self.view.viewport().geometry()).boundingRect()
            default_x = snap_to_grid(visible_rect.center().x() - (width_prop or DEFAULT_TABLE_WIDTH) / 2, GRID_SIZE)
            default_y = snap_to_grid(visible_rect.center().y() - TABLE_HEADER_HEIGHT / 2, GRID_SIZE)

        table_width = width_prop if width_prop is not None else DEFAULT_TABLE_WIDTH
        new_table_data = Table(table_name, x=default_x, y=default_y, width=table_width, 
                               body_color_hex=body_color_hex, header_color_hex=header_color_hex)
        
        for col in columns: new_table_data.add_column(col)
        
        self.tables_data[table_name] = new_table_data
        table_item = TableGraphicItem(new_table_data) 
        self.scene.addItem(table_item)
        print(f"Table '{table_name}' added at snapped position ({default_x},{default_y}) with width {table_width}.")
        return new_table_data 

    def handle_import_csv_button(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import ERD File", "", "CSV Files (*.csv);;All Files (*)") # Changed filter name
        if not path: return

        self.new_diagram() 

        parsed_tables = {} 
        parsed_relationships_from_csv = [] 

        try:
            with open(path, 'r', newline='', encoding='utf-8-sig') as csvfile: 
                reader = csv.reader(csvfile)
                
                current_section = "COLUMNS" # Start by expecting column definitions

                for row_num, row in enumerate(reader):
                    if not row: continue 
                    
                    # Section detection
                    if row[0] == CSV_TABLE_POSITION_MARKER: 
                        current_section = "TABLE_DEFINITIONS" 
                        if len(row) > 1 and row[1].lower() == "table name": continue 
                    elif row[0] == CSV_RELATIONSHIP_DEF_MARKER:
                        current_section = "RELATIONSHIPS"
                        if len(row) > 1 and row[1].lower() == "from table (fk source)": continue 
                    elif row_num == 0 and row[0].lower() == "table name": 
                        current_section = "COLUMNS" 
                        continue 
                    
                    if current_section == "COLUMNS":
                        if len(row) < 7: continue 
                        table_name_csv = row[0].strip()
                        col_name_csv = row[1].strip()
                        
                        if table_name_csv == "": continue
                        if table_name_csv not in parsed_tables:
                            # Initialize with default width and colors, will be overridden by TABLE_DEFINITIONS if present
                            parsed_tables[table_name_csv] = {"columns": [], "pos": None, "width": DEFAULT_TABLE_WIDTH, "body_color": None, "header_color": None}
                        
                        if col_name_csv == "N/A (No Columns)" or col_name_csv == "":
                            continue 

                        data_type_csv = row[2].strip()
                        is_pk_csv = row[3].lower() == "yes"
                        is_fk_csv = row[4].lower() == "yes"
                        ref_table_csv = row[5].strip() if is_fk_csv else None
                        ref_col_csv = row[6].strip() if is_fk_csv else None
                        fk_rel_type_csv = row[7].strip() if is_fk_csv and len(row) > 7 else "N:1"
                        column = Column(col_name_csv, data_type_csv, is_pk_csv, is_fk_csv, ref_table_csv, ref_col_csv, fk_rel_type_csv)
                        parsed_tables[table_name_csv]["columns"].append(column)

                    elif current_section == "TABLE_DEFINITIONS": 
                        if len(row) < 7: continue # Marker, Name, X, Y, Width, BodyColor, HeaderColor
                        table_name_def = row[1].strip()
                        try:
                            x_pos = float(row[2].strip())
                            y_pos = float(row[3].strip())
                            width_val = float(row[4].strip()) if len(row) > 4 and row[4].strip() else DEFAULT_TABLE_WIDTH
                            body_color_hex = row[5].strip() if len(row) > 5 and row[5].strip() else None
                            header_color_hex = row[6].strip() if len(row) > 6 and row[6].strip() else None

                            if table_name_def in parsed_tables:
                                parsed_tables[table_name_def]["pos"] = QPointF(x_pos, y_pos)
                                parsed_tables[table_name_def]["width"] = width_val
                                parsed_tables[table_name_def]["body_color"] = body_color_hex
                                parsed_tables[table_name_def]["header_color"] = header_color_hex
                            else: 
                                parsed_tables[table_name_def] = {"columns": [], "pos": QPointF(x_pos, y_pos), "width": width_val, "body_color": body_color_hex, "header_color": header_color_hex}
                        except ValueError:
                            print(f"Warning: Could not parse definition for table '{table_name_def}'")
                    
                    elif current_section == "RELATIONSHIPS": # For explicit relationship properties like type and bend
                        if len(row) < 6: continue
                        rel_from_table = row[1].strip()
                        rel_from_col = row[2].strip()
                        rel_to_table = row[3].strip()
                        rel_to_col = row[4].strip()
                        rel_type = row[5].strip() if len(row) > 5 else "N:1"
                        manual_bend_x = None
                        if len(row) > 6 and row[6].strip():
                            try: manual_bend_x = float(row[6].strip())
                            except ValueError: pass

                        if rel_from_table and rel_from_col and rel_to_table and rel_to_col:
                            parsed_relationships_from_csv.append({
                                "from_table": rel_from_table, "from_col": rel_from_col,
                                "to_table": rel_to_table, "to_col": rel_to_col,
                                "type": rel_type, "bend_x": manual_bend_x
                            })

            imported_tables_count = 0
            for table_name_to_import, data in parsed_tables.items():
                cols_to_import = data["columns"]
                table_pos = data.get("pos") 
                table_width = data.get("width", DEFAULT_TABLE_WIDTH)
                body_color_h = data.get("body_color")
                header_color_h = data.get("header_color")


                created_table_data = self.handle_add_table_button(
                    table_name_prop=table_name_to_import, 
                    columns_prop=cols_to_import, 
                    pos=table_pos,
                    width_prop=table_width,
                    body_color_hex=body_color_h, # Pass colors
                    header_color_hex=header_color_h
                )
                if created_table_data:
                    imported_tables_count += 1
            
            imported_rels_count = 0
            # Create relationships AFTER all tables and their columns (including FK flags) are processed
            for table_name, table_obj in self.tables_data.items():
                for col in table_obj.columns:
                    if col.is_fk and col.references_table and col.references_column:
                        target_table_obj = self.tables_data.get(col.references_table)
                        if target_table_obj:
                            target_pk_col = target_table_obj.get_column_by_name(col.references_column)
                            if target_pk_col and target_pk_col.is_pk:
                                # Check if this relationship was also in parsed_relationships_from_csv to get its specific type/bend
                                rel_props = next((r for r in parsed_relationships_from_csv 
                                                  if r["from_table"] == table_name and r["from_col"] == col.name and
                                                     r["to_table"] == col.references_table and r["to_col"] == col.references_column), None)
                                
                                rel_type_to_create = col.fk_relationship_type # Default from column
                                bend_x_to_create = None
                                if rel_props:
                                    rel_type_to_create = rel_props["type"]
                                    bend_x_to_create = rel_props["bend_x"]
                                    # Update column's FK type if explicitly defined in relationship section
                                    if col.fk_relationship_type != rel_type_to_create:
                                        col.fk_relationship_type = rel_type_to_create
                                        if table_obj.graphic_item: table_obj.graphic_item.update()


                                self.create_relationship(table_obj, target_table_obj, col.name, col.references_column, rel_type_to_create, bend_x_to_create)
                                imported_rels_count +=1
                            else:
                                print(f"Import Warning: FK '{table_name}.{col.name}' references non-PK column '{col.references_table}.{col.references_column}'. Relationship not created.")
                        else:
                                print(f"Import Warning: FK '{table_name}.{col.name}' references non-existent table '{col.references_table}'. Relationship not created.")


            self.update_all_relationships_graphics() 
            self.current_file_path = path
            self.update_window_title()

            msg_parts = []
            if imported_tables_count > 0: msg_parts.append(f"{imported_tables_count} tables") 
            if imported_rels_count > 0: msg_parts.append(f"{imported_rels_count} relationships") 

            if msg_parts:
                QMessageBox.information(self, "Import Successful", f"{' and '.join(msg_parts)} imported.") 
            else:
                QMessageBox.information(self, "Import Info", "No new data was imported. Check CSV format or if data already exists.") 

        except FileNotFoundError: QMessageBox.critical(self, "Import Error", f"File not found: {path}") 
        except Exception as e: QMessageBox.critical(self, "Import Error", f"Could not import from CSV: {e}\nCheck console for details."); print(f"CSV Import Error: {e}", file=sys.stderr) 


    def export_to_csv(self, file_path_to_save=None): 
        if not self.tables_data : 
            QMessageBox.information(self, "Export CSV", "No data to export."); return 
        
        if not file_path_to_save:
            print("Error: No file path provided for export_to_csv.")
            return

        try:
            with open(file_path_to_save, 'w', newline='', encoding='utf-8-sig') as csvfile: 
                writer = csv.writer(csvfile)
                # Section 1: Table Column Definitions
                writer.writerow(["Table Name", "Column Name", "Data Type", "Is Primary Key", "Is Foreign Key", "References Table", "References Column", "FK Relationship Type"])
                for _, table_obj in self.tables_data.items():
                    if not table_obj.columns: 
                        writer.writerow([table_obj.name, "N/A (No Columns)", "", "", "", "", "", ""])
                    else:
                        for col in table_obj.columns:
                            writer.writerow([table_obj.name, col.name, col.data_type, 
                                             "Yes" if col.is_pk else "No", 
                                             "Yes" if col.is_fk else "No",
                                             col.references_table if col.is_fk else "", 
                                             col.references_column if col.is_fk else "",
                                             col.fk_relationship_type if col.is_fk else ""]) 
                
                # Section 2: Table Definitions (Name, X, Y, Width, BodyColor, HeaderColor)
                writer.writerow([]) 
                writer.writerow([CSV_TABLE_POSITION_MARKER, "Table Name", "X", "Y", "Width", "Body Color HEX", "Header Color HEX"])
                for table_name, table_obj in self.tables_data.items():
                    writer.writerow([CSV_TABLE_POSITION_MARKER, table_name, table_obj.x, table_obj.y, table_obj.width,
                                     table_obj.body_color.name(), table_obj.header_color.name()])

                # Section 3: Explicit Relationship Definitions (for types, manual bends etc.)
                if self.relationships_data:
                    writer.writerow([]) 
                    writer.writerow([CSV_RELATIONSHIP_DEF_MARKER, "From Table (FK Source)", "FK Column", "To Table (PK Source)", "PK Column", "Relationship Type", "Manual Bend X Offset"])
                    for rel in self.relationships_data:
                        writer.writerow([CSV_RELATIONSHIP_DEF_MARKER, rel.table1_name, rel.fk_column_name, rel.table2_name, rel.pk_column_name, rel.relationship_type, rel.manual_bend_offset_x if rel.manual_bend_offset_x is not None else ""])
                        
                QMessageBox.information(self, "File Saved", f"Data saved successfully to: {file_path_to_save}") 
        except Exception as e: QMessageBox.critical(self, "Save Error", f"Could not save file: {e}") 

    def edit_relationship_properties(self, relationship_data):
        dialog = RelationshipDialog(relationship_data, self) 
        if dialog.exec():
            print(f"Relationship properties updated for {relationship_data.table1_name} -> {relationship_data.table2_name}. New type: {relationship_data.relationship_type}")
            self.update_orthogonal_path(relationship_data) 

    def create_relationship(self, table1_data, table2_data, fk_col_name=None, pk_col_name=None, relationship_type_from_fk="N:1", manual_bend_x=None):
        if not (fk_col_name and pk_col_name):
            print("Error: FK and PK column names must be provided to create a relationship.")
            return

        # table1_data is FK holder, table2_data is PK holder
        for rel in self.relationships_data:
            if (rel.table1_name == table1_data.name and rel.fk_column_name == fk_col_name and \
                rel.table2_name == table2_data.name and rel.pk_column_name == pk_col_name):
                print(f"Relationship {table1_data.name}.{fk_col_name} -> {table2_data.name}.{pk_col_name} already exists.")
                # Update its type and bend if different (e.g. during import)
                changed = False
                if rel.relationship_type != relationship_type_from_fk:
                    rel.relationship_type = relationship_type_from_fk
                    changed = True
                if manual_bend_x is not None and rel.manual_bend_offset_x != manual_bend_x:
                    rel.manual_bend_offset_x = manual_bend_x
                    changed = True
                if changed and rel.graphic_item: 
                    rel.graphic_item.update_tooltip_and_paint()
                    self.update_orthogonal_path(rel) # Redraw if properties changed
                return

        relationship = Relationship(table1_data.name, table2_data.name, fk_col_name, pk_col_name, relationship_type_from_fk)
        if manual_bend_x is not None:
            relationship.manual_bend_offset_x = manual_bend_x

        line_item = OrthogonalRelationshipLine(relationship) 
        self.relationships_data.append(relationship)
        self.scene.addItem(line_item) 
        self.update_orthogonal_path(relationship) 
        print(f"Relationship created: {table1_data.name}.{fk_col_name} ({relationship_type_from_fk}) -> {table2_data.name}.{pk_col_name}")


    def update_orthogonal_path(self, relationship_data):
        if not relationship_data.graphic_item: return
        
        table1_obj = self.tables_data.get(relationship_data.table1_name) 
        table2_obj = self.tables_data.get(relationship_data.table2_name) 

        if not (table1_obj and table1_obj.graphic_item and table2_obj and table2_obj.graphic_item):
            if isinstance(relationship_data.graphic_item, OrthogonalRelationshipLine):
                relationship_data.graphic_item.set_path_points(QPointF(), QPointF(), QPointF(), QPointF()) 
            return

        t1_graphic = table1_obj.graphic_item
        t2_graphic = table2_obj.graphic_item

        p1 = t1_graphic.get_attachment_point(t2_graphic, relationship_data.fk_column_name) 
        p2 = t2_graphic.get_attachment_point(t1_graphic, relationship_data.pk_column_name) 
        
        bend1, bend2 = QPointF(), QPointF()
        
        vertical_segment_x = relationship_data.manual_bend_offset_x
        if vertical_segment_x is None:
            t1_rect = t1_graphic.sceneBoundingRect()
            t2_rect = t2_graphic.sceneBoundingRect()
            
            horizontal_center_diff = abs(t1_rect.center().x() - t2_rect.center().x())
            
            # If tables are significantly overlapping horizontally or very close
            if horizontal_center_diff < (t1_graphic.width / 2 + t2_graphic.width / 2 - GRID_SIZE * 0.5): # Use dynamic width
                # Determine if one is mostly above the other
                is_t1_above_t2 = t1_rect.bottom() < t2_rect.top() + GRID_SIZE
                is_t2_above_t1 = t2_rect.bottom() < t1_rect.top() + GRID_SIZE

                if is_t1_above_t2 or is_t2_above_t1: # One is clearly above the other
                     # Exit horizontally, then vertical segment to the side
                    if p1.x() < t1_rect.center().x(): # p1 exits left from t1
                        vertical_segment_x = min(t1_rect.left(), t2_rect.left()) - MIN_HORIZONTAL_SEGMENT
                    else: # p1 exits right from t1
                        vertical_segment_x = max(t1_rect.right(), t2_rect.right()) + MIN_HORIZONTAL_SEGMENT
                else: # Significant horizontal overlap but not one above other (e.g. side by side but close)
                    vertical_segment_x = (p1.x() + p2.x()) / 2
            else: # Default for tables more horizontally separated
                vertical_segment_x = (p1.x() + p2.x()) / 2
            
            vertical_segment_x = snap_to_grid(vertical_segment_x, GRID_SIZE)

        bend1 = QPointF(vertical_segment_x, p1.y())
        bend2 = QPointF(vertical_segment_x, p2.y())
        
        # Ensure first and last horizontal segments have a minimum length
        # This makes sure the line "exits" the table horizontally before turning.
        if p1.x() != bend1.x(): 
            if abs(p1.x() - bend1.x()) < MIN_HORIZONTAL_SEGMENT:
                bend1.setX(p1.x() + math.copysign(MIN_HORIZONTAL_SEGMENT , bend1.x() - p1.x()))
                bend2.setX(bend1.x()) # Keep vertical segment aligned if bend1.x changed
        
        if p2.x() != bend2.x(): 
             if abs(p2.x() - bend2.x()) < MIN_HORIZONTAL_SEGMENT:
                # If bend2.x (which is vertical_segment_x) needs to move to satisfy p2's min length,
                # it means the vertical segment itself needs to shift.
                # This logic can get complex if vertical_segment_x was manually set.
                # For now, prioritize the manual_bend_offset_x if set.
                if relationship_data.manual_bend_offset_x is None:
                    new_bend2_x = p2.x() + math.copysign(MIN_HORIZONTAL_SEGMENT, bend2.x() - p2.x())
                    bend1.setX(new_bend2_x) # Shift the whole vertical segment
                    bend2.setX(new_bend2_x)


        if isinstance(relationship_data.graphic_item, OrthogonalRelationshipLine):
            relationship_data.graphic_item.set_path_points(p1, bend1, bend2, p2)
        

    def update_all_relationships_graphics(self):
        for rel_data in self.relationships_data:
            self.update_orthogonal_path(rel_data)

    def update_relationship_table_names(self, old_table_name, new_table_name):
        for rel in self.relationships_data:
            if rel.table1_name == old_table_name: rel.table1_name = new_table_name
            if rel.table2_name == old_table_name: rel.table2_name = new_table_name
        for table in self.tables_data.values():
            for column in table.columns:
                if column.is_fk and column.references_table == old_table_name:
                    column.references_table = new_table_name
                    if table.graphic_item: table.graphic_item.update()
        self.update_all_relationships_graphics()

    def update_fk_references_to_table(self, old_table_name, new_table_name):
        """Called when a table is renamed, to update FKs in OTHER tables."""
        for table_data in self.tables_data.values():
            if table_data.name == new_table_name: continue 
            for column in table_data.columns:
                if column.is_fk and column.references_table == old_table_name:
                    column.references_table = new_table_name
                    if table_data.graphic_item: table_data.graphic_item.update()
        self.update_all_relationships_graphics() 

    def update_fk_references_to_pk(self, pk_table_name, old_pk_col_name, new_pk_col_name):
        """Called when a PK column in pk_table_name is renamed or removed."""
        for table_data in self.tables_data.values(): # Iterate through all tables
            for column in table_data.columns:
                if column.is_fk and \
                   column.references_table == pk_table_name and \
                   column.references_column == old_pk_col_name:
                    if new_pk_col_name: # PK was renamed
                        column.references_column = new_pk_col_name
                    else: # PK was removed, so invalidate this FK
                        column.is_fk = False
                        column.references_table = None
                        column.references_column = None
                        # Also remove the corresponding Relationship object and its graphic
                        rel_to_remove = next((r for r in self.relationships_data if 
                                              r.table1_name == table_data.name and 
                                              r.fk_column_name == column.name and
                                              r.table2_name == pk_table_name and
                                              r.pk_column_name == old_pk_col_name), None)
                        if rel_to_remove:
                            if rel_to_remove.graphic_item: self.scene.removeItem(rel_to_remove.graphic_item)
                            if rel_to_remove in self.relationships_data: self.relationships_data.remove(rel_to_remove)
                    
                    if table_data.graphic_item: table_data.graphic_item.update()
        self.update_all_relationships_graphics()

    def remove_relationships_for_table(self, table_name, old_columns_of_table=None):
        """Removes all relationship data and graphics connected to a table,
           or specific FKs if old_columns_of_table is provided."""
        rels_to_remove = []
        if old_columns_of_table: # Removing specific FKs that were changed/removed
            for old_col in old_columns_of_table:
                if old_col.is_fk and old_col.references_table and old_col.references_column:
                    # Find if this specific FK still exists with the same target in the current table_data
                    current_table_obj = self.tables_data.get(table_name)
                    if current_table_obj:
                        current_col_obj = current_table_obj.get_column_by_name(old_col.name)
                        if not current_col_obj or \
                           not current_col_obj.is_fk or \
                           current_col_obj.references_table != old_col.references_table or \
                           current_col_obj.references_column != old_col.references_column:
                            # This FK was removed or its target changed
                            for rel in self.relationships_data:
                                if rel.table1_name == table_name and rel.fk_column_name == old_col.name and \
                                   rel.table2_name == old_col.references_table and rel.pk_column_name == old_col.references_column:
                                    if rel not in rels_to_remove: rels_to_remove.append(rel)
                                    break 
        else: # Removing all relationships for a table (e.g., table deleted)
            rels_to_remove = [
                rel for rel in self.relationships_data 
                if rel.table1_name == table_name or rel.table2_name == table_name
            ]

        for rel in rels_to_remove:
            if rel.graphic_item:
                self.scene.removeItem(rel.graphic_item)
            if rel in self.relationships_data:
                self.relationships_data.remove(rel)
            print(f"Relationship involving '{rel.table1_name}.{rel.fk_column_name}' to '{rel.table2_name}.{rel.pk_column_name}' removed.")


    def delete_selected_items(self):
        selected_graphics = self.scene.selectedItems()
        if not selected_graphics: return

        tables_to_delete_graphics = [item for item in selected_graphics if isinstance(item, TableGraphicItem)]
        lines_to_delete_graphics = [item for item in selected_graphics if isinstance(item, OrthogonalRelationshipLine)] 
        
        delete_message_parts = []
        if tables_to_delete_graphics: delete_message_parts.append(f"{len(tables_to_delete_graphics)} tables and their relationships") 
        
        standalone_lines = []
        if lines_to_delete_graphics:
            for line_graphic in lines_to_delete_graphics:
                is_standalone = True
                if hasattr(line_graphic, 'relationship_data'):
                    rel_data_of_line = line_graphic.relationship_data
                    table1_selected = any(tg.table_data.name == rel_data_of_line.table1_name for tg in tables_to_delete_graphics)
                    table2_selected = any(tg.table_data.name == rel_data_of_line.table2_name for tg in tables_to_delete_graphics)
                    if table1_selected or table2_selected: is_standalone = False
                if is_standalone: standalone_lines.append(line_graphic)
            if standalone_lines: delete_message_parts.append(f"{len(standalone_lines)} relationships") 
        
        if not delete_message_parts: return

        reply = QMessageBox.question(self, "Confirm Delete", f"Delete {', '.join(delete_message_parts)}?", 
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.No: return

        for line_graphic in standalone_lines: 
            if hasattr(line_graphic, 'relationship_data'):
                rel_to_remove = line_graphic.relationship_data
                from_table = self.tables_data.get(rel_to_remove.table1_name)
                if from_table:
                    fk_col = from_table.get_column_by_name(rel_to_remove.fk_column_name)
                    if fk_col and fk_col.references_table == rel_to_remove.table2_name and fk_col.references_column == rel_to_remove.pk_column_name:
                        is_part_of_other_rel = any(
                            r != rel_to_remove and r.table1_name == from_table.name and r.fk_column_name == fk_col.name
                            for r in self.relationships_data
                        )
                        if not is_part_of_other_rel:
                            fk_col.is_fk = False
                            fk_col.references_table = None
                            fk_col.references_column = None
                            if from_table.graphic_item: from_table.graphic_item.update()

                self.scene.removeItem(line_graphic) 
                if rel_to_remove in self.relationships_data: self.relationships_data.remove(rel_to_remove)
                print(f"Relationship deleted: {rel_to_remove.table1_name} to {rel_to_remove.table2_name}")

        for table_graphic in tables_to_delete_graphics:
            table_name_to_delete = table_graphic.table_data.name
            # Remove relationships associated with the table being deleted
            self.remove_relationships_for_table(table_name_to_delete)

            self.scene.removeItem(table_graphic)
            if table_name_to_delete in self.tables_data: del self.tables_data[table_name_to_delete]
            print(f"Table '{table_name_to_delete}' deleted.")
        self.scene.update()

# --- Helper function for contrasting text color ---
def get_contrasting_text_color(bg_color):
    """Returns black or white based on the background color's luminance."""
    if not isinstance(bg_color, QColor):
        return QColor(Qt.GlobalColor.black) # Default if color is invalid
    # Calculate luminance (standard formula)
    luminance = (0.299 * bg_color.red() + 0.587 * bg_color.green() + 0.114 * bg_color.blue()) / 255
    return QColor(Qt.GlobalColor.black) if luminance > 0.5 else QColor(Qt.GlobalColor.white)


# --- Running the Application ---
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = ERDCanvasWindow()
    window.show()
    sys.exit(app.exec())
