# utils.py
# This file contains utility functions used across the ERD design tool.

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPixmap, QPainter, QColor, QIcon
from PyQt6.QtCore import Qt

# Import current_theme_settings from constants.py
from constants import current_theme_settings 


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
        painter.setPen(QColor(current_theme_settings.get("text_color", QColor(Qt.GlobalColor.black)))) 
        painter.drawText(pm.rect(), Qt.AlignmentFlag.AlignCenter, fallback_text)
        painter.end() 
        return QIcon(pm) 
    return icon

def snap_to_grid(value, grid_size):
    """Snaps a value to the nearest grid line."""
    if grid_size == 0: return value 
    return round(value / grid_size) * grid_size

def get_contrasting_text_color(bg_color):
    """Returns black or white based on the background color's luminance."""
    if not isinstance(bg_color, QColor) or not bg_color.isValid():
        return QColor(current_theme_settings.get("text_color", QColor(Qt.GlobalColor.black))) 
    
    luminance = (0.299 * bg_color.redF() + 0.587 * bg_color.greenF() + 0.114 * bg_color.blueF())

    if luminance > 0.5:
        return QColor(Qt.GlobalColor.black)
    else:
        return QColor(Qt.GlobalColor.white)

