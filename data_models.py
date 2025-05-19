# data_models.py
# Contains data model classes: Column, Table, Relationship, GroupData.

from PyQt6.QtGui import QColor
from PyQt6.QtCore import QPointF, Qt # Ensure QPointF and Qt are imported
from constants import DEFAULT_TABLE_WIDTH, GRID_SIZE, current_theme_settings
from utils import snap_to_grid
import copy

class Column:
    def __init__(self, name, data_type="TEXT", is_pk=False, is_fk=False,
                 references_table=None, references_column=None, fk_relationship_type="N:1"):
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

    def __deepcopy__(self, memo):
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result
        for k, v in self.__dict__.items():
            setattr(result, k, copy.deepcopy(v, memo))
        return result

class Table:
    def __init__(self, name, x=50, y=50, width=DEFAULT_TABLE_WIDTH,
                 body_color_hex=None, header_color_hex=None):
        self.name = name
        self.columns = []
        self.x = snap_to_grid(x, GRID_SIZE)
        self.y = snap_to_grid(y, GRID_SIZE)
        self.width = snap_to_grid(width, GRID_SIZE)
        self.graphic_item = None
        self.group_name = None # NEW: Name of the group this table belongs to

        default_body_qcolor = QColor(current_theme_settings.get("default_table_body_color", QColor(Qt.GlobalColor.white)))
        self.body_color = default_body_qcolor
        if body_color_hex and QColor.isValidColor(body_color_hex):
            self.body_color = QColor(body_color_hex)

        default_header_qcolor = QColor(current_theme_settings.get("default_table_header_color", QColor(Qt.GlobalColor.lightGray)))
        self.header_color = default_header_qcolor
        if header_color_hex and QColor.isValidColor(header_color_hex):
            self.header_color = QColor(header_color_hex)


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

    def __deepcopy__(self, memo):
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result

        for k, v in self.__dict__.items():
            if k == 'graphic_item':
                setattr(result, k, None)
            elif k == 'body_color' or k == 'header_color':
                setattr(result, k, QColor(v))
            elif k == 'columns':
                setattr(result, k, [copy.deepcopy(col, memo) for col in v])
            else:
                setattr(result, k, copy.deepcopy(v, memo))
        return result


class Relationship:
    def __init__(self, table1_name, table2_name, fk_column_name=None, pk_column_name=None, relationship_type="N:1"):
        self.table1_name = table1_name # FK side table
        self.table2_name = table2_name # PK side table
        self.fk_column_name = fk_column_name # FK column name in table1
        self.pk_column_name = pk_column_name # PK column name in table2
        self.relationship_type = relationship_type # e.g., "N:1", "1:1"
        self.graphic_item = None # Reference to the QGraphicsItem
        self.anchor_points = [] # List of QPointF for orthogonal bends, e.g. [A1, A2, B1, B2, ...]

    def __deepcopy__(self, memo):
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result

        for k, v in self.__dict__.items():
            if k == 'graphic_item':
                setattr(result, k, None)
            elif k == 'anchor_points': # Ensure deepcopy of QPointF list
                setattr(result, k, [QPointF(p) for p in v])
            else:
                setattr(result, k, copy.deepcopy(v, memo))
        return result

class GroupData:
    """
    Represents a group of tables in the ERD.
    """
    def __init__(self, name, x=0, y=0, width=400, height=300,
                 border_color_hex=None, title_bg_color_hex=None, title_text_color_hex=None):
        self.name = name
        self.x = snap_to_grid(x, GRID_SIZE)
        self.y = snap_to_grid(y, GRID_SIZE)
        self.width = snap_to_grid(width, GRID_SIZE)
        self.height = snap_to_grid(height, GRID_SIZE)
        self.table_names = []  # List of names of tables belonging to this group
        self.graphic_item = None  # Reference to its GroupGraphicItem

        # Default colors can be themed or user-defined later
        self.border_color = QColor(border_color_hex) if border_color_hex and QColor.isValidColor(border_color_hex) else QColor(current_theme_settings.get("group_border_color", QColor(150, 150, 150)))
        self.title_bg_color = QColor(title_bg_color_hex) if title_bg_color_hex and QColor.isValidColor(title_bg_color_hex) else QColor(current_theme_settings.get("group_title_bg_color", QColor(200, 200, 200)))
        self.title_text_color = QColor(title_text_color_hex) if title_text_color_hex and QColor.isValidColor(title_text_color_hex) else QColor(current_theme_settings.get("group_title_text_color", QColor(0,0,0)))


    def add_table(self, table_name: str):
        if table_name not in self.table_names:
            self.table_names.append(table_name)

    def remove_table(self, table_name: str):
        if table_name in self.table_names:
            self.table_names.remove(table_name)

    def __str__(self):
        return f"Group: {self.name} (Tables: {len(self.table_names)})"

    def __deepcopy__(self, memo):
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result

        for k, v in self.__dict__.items():
            if k == 'graphic_item':
                setattr(result, k, None) # Don't deepcopy the graphic item reference
            elif k in ['border_color', 'title_bg_color', 'title_text_color']:
                setattr(result, k, QColor(v)) # Deepcopy QColor objects
            elif k == 'table_names':
                setattr(result, k, copy.deepcopy(v, memo)) # Deepcopy list of strings
            else:
                setattr(result, k, copy.deepcopy(v, memo))
        return result
