# constants.py
# This file contains global constants used throughout the ERD design tool application.

from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt

# --- Existing Constants ---
DEFAULT_TABLE_WIDTH = 200
TABLE_HEADER_HEIGHT = 30
COLUMN_HEIGHT = 22
PADDING = 10
GRID_SIZE = 20
RELATIONSHIP_HANDLE_SIZE = 8
MIN_HORIZONTAL_SEGMENT = GRID_SIZE * 1.5
CSV_TABLE_DEF_MARKER = "TABLE_DEFINITION" # May not be used if all table info is under TABLE_POSITION
CSV_COLUMN_DEF_MARKER = "COLUMN_DEFINITION" # Used if columns are listed separately
CSV_TABLE_POSITION_MARKER = "TABLE_POSITION" # Used for table x,y,width,colors
CSV_RELATIONSHIP_DEF_MARKER = "RELATIONSHIP_DEF"
CARDINALITY_OFFSET = 10
CARDINALITY_TEXT_MARGIN = 25
TABLE_RESIZE_HANDLE_WIDTH = 10
MIN_TABLE_WIDTH = 120

# --- New Constants for Canvas Size ---
DEFAULT_CANVAS_WIDTH = 4000
DEFAULT_CANVAS_HEIGHT = 3000
CSV_CANVAS_SIZE_MARKER = "CANVAS_SIZE_DEFINITION" # Marker for CSV

# --- New Constants for Editable Data Types ---
# This is the master list of data types the application knows about by default.
# The user-editable list will be loaded from config or initialized from this.
DEFAULT_COLUMN_DATA_TYPES = [
    "TEXT", "INTEGER", "REAL", "BLOB", "VARCHAR(255)", "BOOLEAN",
    "DATE", "DATETIME", "NUMERIC", "TIMESTAMP", "SERIAL", "UUID",
    "CHAR", "VARCHAR", "INT", "SMALLINT", "BIGINT", "DECIMAL",
    "FLOAT", "DOUBLE PRECISION", "TIME", "JSON"
]


# --- Globally Accessible Current Settings (to be updated from config/UI) ---
# These will be dictionaries or simple types updated by main_window.py
current_theme_settings = {} # This is populated by main_window.py

# Holds the current canvas dimensions, loaded from config or defaults.
current_canvas_dimensions = {
    "width": DEFAULT_CANVAS_WIDTH,
    "height": DEFAULT_CANVAS_HEIGHT
}

# Holds the current list of user-editable column data types.
# Loaded from config, or defaults to DEFAULT_COLUMN_DATA_TYPES.
editable_column_data_types = DEFAULT_COLUMN_DATA_TYPES[:] # Start with a copy


# --- Theme Colors (unchanged from previous versions) ---
light_theme_colors = {
    "window_bg": QColor("#F8F9FA"),
    "view_bg": QColor("#FFFFFF"),
    "view_border": QColor("#DEE2E6"),
    "toolbar_bg": QColor("#E9ECEF"),
    "toolbar_border": QColor("#CED4DA"),
    "button_bg": QColor("#FFFFFF"),
    "button_border": QColor("#CED4DA"),
    "button_hover_bg": QColor("#E9ECEF"),
    "button_pressed_bg": QColor("#DEE2E6"),
    "button_checked_bg": QColor("#007BFF"),
    "button_checked_text_color": QColor(Qt.GlobalColor.white),
    "button_checked_border": QColor("#0056B3"),
    "text_color": QColor("#212529"),
    "dialog_text_color": QColor("#212529"),
    "default_table_body_color": QColor("#FFFFFF"),
    "default_table_header_color": QColor("#6C757D"),
    "default_table_header_text_color": QColor(Qt.GlobalColor.white),
    "default_table_body_text_color": QColor("#495057"),
    "grid_color": QColor(233, 236, 239, 100),
    "relationship_line_color": QColor(108, 117, 125),
    "cardinality_text_color": QColor(73, 80, 87),
    "dialog_input_bg": QColor("#FFFFFF"),
    "dialog_input_border": QColor("#CED4DA"),
}

dark_theme_colors = {
    "window_bg": QColor("#212529"),
    "view_bg": QColor("#2B3035"),
    "view_border": QColor("#495057"),
    "toolbar_bg": QColor("#343A40"),
    "toolbar_border": QColor("#495057"),
    "button_bg": QColor("#495057"),
    "button_border": QColor("#6C757D"),
    "button_hover_bg": QColor("#5A6268"),
    "button_pressed_bg": QColor("#6C757D"),
    "button_checked_bg": QColor("#007BFF"),
    "button_checked_text_color": QColor(Qt.GlobalColor.white),
    "button_checked_border": QColor("#0056B3"),
    "text_color": QColor("#F8F9FA"),
    "dialog_text_color": QColor("#F8F9FA"),
    "default_table_body_color": QColor("#343A40"),
    "default_table_header_color": QColor("#495057"),
    "default_table_header_text_color": QColor(Qt.GlobalColor.white),
    "default_table_body_text_color": QColor("#E9ECEF"),
    "grid_color": QColor(73, 80, 87, 100),
    "relationship_line_color": QColor(173, 181, 189),
    "cardinality_text_color": QColor(206, 212, 218),
    "dialog_input_bg": QColor("#343A40"),
    "dialog_input_border": QColor("#6C757D"),
}

# Note: current_theme_settings is initialized as an empty dict here.
# main_window.py is responsible for populating it based on the loaded theme
# and user default colors during its __init__ and update_theme_settings methods.
