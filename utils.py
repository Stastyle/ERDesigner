# utils.py
# This file contains utility functions used across the ERD design tool.

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPixmap, QPainter, QColor, QIcon
from PyQt6.QtCore import Qt

# Import current_theme_settings from constants.py or pass it as an argument
# For simplicity here, we'll assume it's accessible if this were part of a larger structure.
# However, for modularity, it's better to pass theme settings or access them via a shared config object.
# For now, let's define a placeholder here or import directly if constants.py is created first.
# Assuming constants.py will define a dictionary named `current_theme_settings`
try:
    from constants import current_theme_settings 
except ImportError:
    # Fallback if constants.py is not yet available or for standalone use of this util
    current_theme_settings = {"text_color": QColor(Qt.GlobalColor.black)}


def get_standard_icon(standard_pixmap, fallback_text=""):
    """
    Tries to get a standard Qt icon. 
    If not available, creates a fallback text-based icon.
    """
    icon = QApplication.style().standardIcon(standard_pixmap)
    if icon.isNull() and fallback_text: 
        pm = QPixmap(24,24) 
        pm.fill(Qt.GlobalColor.transparent) 
        painter = QPainter(pm)
        # Use text_color from the theme settings
        painter.setPen(QColor(current_theme_settings.get("text_color", QColor(Qt.GlobalColor.black)))) 
        painter.drawText(pm.rect(), Qt.AlignmentFlag.AlignCenter, fallback_text)
        painter.end() 
        return QIcon(pm) 
    return icon

def snap_to_grid(value, grid_size):
    """Snaps a value to the nearest grid line."""
    if grid_size == 0: return value # Avoid division by zero
    return round(value / grid_size) * grid_size

def get_contrasting_text_color(bg_color):
    """Returns black or white based on the background color's luminance."""
    if not isinstance(bg_color, QColor) or not bg_color.isValid():
        return QColor(current_theme_settings.get("text_color", QColor(Qt.GlobalColor.black))) 
    
    # Calculate luminance (standard formula: Y = 0.2126 R + 0.7152 G + 0.0722 B)
    # Simpler formula often used: (0.299*R + 0.587*G + 0.114*B)
    luminance = (0.299 * bg_color.redF() + 0.587 * bg_color.greenF() + 0.114 * bg_color.blueF())
    # Using redF(), greenF(), blueF() returns values between 0.0 and 1.0

    if luminance > 0.5:
        return QColor(Qt.GlobalColor.black)
    else:
        return QColor(Qt.GlobalColor.white)

