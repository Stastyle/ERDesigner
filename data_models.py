# data_models.py
# Contains data model classes: Column, Table, Relationship.

from PyQt6.QtGui import QColor
from constants import DEFAULT_TABLE_WIDTH, GRID_SIZE, current_theme_settings # Import necessary constants
from utils import snap_to_grid # Import utility
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
        # Columns are relatively simple, default deepcopy might be okay,
        # but explicit is safer if they ever hold complex objects.
        # For now, let's assume direct attribute copying is fine.
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
        self.graphic_item = None # This should not be deepcopied directly
        
        # Initialize colors based on current theme's defaults, then override if specific hex is given
        self.body_color = QColor(current_theme_settings["default_table_body_color"])
        if body_color_hex and QColor.isValidColor(body_color_hex):
            self.body_color = QColor(body_color_hex)
            
        self.header_color = QColor(current_theme_settings["default_table_header_color"])
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
        result = cls.__new__(cls) # Create new instance without calling __init__
        memo[id(self)] = result

        # Copy attributes, skipping graphic_item
        for k, v in self.__dict__.items():
            if k == 'graphic_item':
                setattr(result, k, None) # Explicitly set graphic_item to None in the copy
            elif k == 'body_color' or k == 'header_color': # QColor objects
                setattr(result, k, QColor(v)) # Create a new QColor instance
            elif k == 'columns':
                setattr(result, k, [copy.deepcopy(col, memo) for col in v]) # Deepcopy columns
            else:
                setattr(result, k, copy.deepcopy(v, memo)) # Deepcopy other attributes
        return result


class Relationship:
    def __init__(self, table1_name, table2_name, fk_column_name=None, pk_column_name=None, relationship_type="N:1"): 
        self.table1_name = table1_name # Table containing the FK
        self.table2_name = table2_name # Table containing the PK
        self.fk_column_name = fk_column_name 
        self.pk_column_name = pk_column_name 
        self.relationship_type = relationship_type 
        self.graphic_item = None # This should not be deepcopied directly
        self.manual_bend_offset_x = None

    def __deepcopy__(self, memo):
        cls = self.__class__
        result = cls.__new__(cls) # Create new instance
        memo[id(self)] = result

        for k, v in self.__dict__.items():
            if k == 'graphic_item':
                setattr(result, k, None) # Explicitly set graphic_item to None in the copy
            else:
                setattr(result, k, copy.deepcopy(v, memo)) # Deepcopy other attributes
        return result
