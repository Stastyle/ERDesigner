# constants.py
# This file contains global constants used throughout the ERD design tool application.

from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt 

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
# These are dictionaries that will be populated by the main window based on theme choice
light_theme_colors = {
    "window_bg": QColor("#e8e8e8"), "view_bg": QColor("#f8f9fa"), "view_border": QColor("#ced4da"),
    "toolbar_bg": QColor("#e9ecef"), "toolbar_border": QColor("#ced4da"),
    "button_bg": QColor("#f8f9fa"), "button_border": QColor("#adb5bd"),
    "button_hover_bg": QColor("#e9ecef"), "button_pressed_bg": QColor("#dee2e6"),
    "button_checked_bg": QColor("#cfe2ff"), "button_checked_border": QColor("#9ec5fe"),
    "text_color": QColor(Qt.GlobalColor.black), "dialog_text_color": QColor(Qt.GlobalColor.black),
    "default_table_body_color": QColor(235, 235, 250), 
    "default_table_header_color": QColor(200, 200, 230),
    "grid_color": QColor(200, 200, 200, 60),
    "relationship_line_color": QColor(70, 70, 110),
    "cardinality_text_color": QColor(30,30,30),
}

dark_theme_colors = {
    "window_bg": QColor("#2b2b2b"), "view_bg": QColor("#3c3c3c"), "view_border": QColor("#555555"),
    "toolbar_bg": QColor("#333333"), "toolbar_border": QColor("#505050"),
    "button_bg": QColor("#4f4f4f"), "button_border": QColor("#666666"),
    "button_hover_bg": QColor("#5a5a5a"), "button_pressed_bg": QColor("#646464"),
    "button_checked_bg": QColor("#4a5a7f"), "button_checked_border": QColor("#6c7ca0"),
    "text_color": QColor(Qt.GlobalColor.white), "dialog_text_color": QColor(Qt.GlobalColor.white),
    "default_table_body_color": QColor(60, 63, 65), 
    "default_table_header_color": QColor(83, 83, 83),
    "grid_color": QColor(100, 100, 100, 60),
    "relationship_line_color": QColor(180, 180, 220),
    "cardinality_text_color": QColor(220,220,220),
}

# current_theme_settings will be a copy of one of the above,
# potentially overridden by user defaults for table colors.
# It will be managed in the main_window.py
# Initialize with light theme as a default AFTER light_theme_colors is defined.
current_theme_settings = light_theme_colors.copy() # Corrected variable name
