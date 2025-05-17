# utils.py
# Contains utility functions for the ERD design tool.

from PyQt6.QtWidgets import QApplication, QStyle
from PyQt6.QtGui import QPainter, QPixmap, QColor, QIcon, QFontMetrics, QImage # Ensure QIcon is imported
from PyQt6.QtCore import Qt, QSize, QRectF

from constants import GRID_SIZE # Assuming constants.py is in the same directory or accessible

def snap_to_grid(value, grid_size=GRID_SIZE):
    """Snaps a value to the nearest grid line."""
    return round(value / grid_size) * grid_size

def get_contrasting_text_color(bg_color):
    """
    Calculates whether black or white text provides better contrast against a given background color.
    """
    if not isinstance(bg_color, QColor):
        bg_color = QColor(bg_color) # Ensure it's a QColor object

    # Calculate luminance (standard formula)
    # Using YIQ formula: Y = 0.299*R + 0.587*G + 0.114*B
    # Or simpler: (R + G + B) / 3
    # Qt's QColor.lightnessF() returns lightness (0.0 to 1.0)
    luminance = bg_color.lightnessF()

    # Threshold can be adjusted, 0.5 is a common midpoint
    if luminance > 0.55: # Experiment with this threshold
        return QColor(Qt.GlobalColor.black)
    else:
        return QColor(Qt.GlobalColor.white)

def get_standard_icon(standard_pixmap_enum, fallback_text=None, color=None):
    """
    Retrieves a standard Qt icon, or a fallback text icon if not available.
    If color is provided, it tries to colorize the icon (basic attempt).

    Args:
        standard_pixmap_enum: QStyle.StandardPixmap enum value (e.g., QStyle.StandardPixmap.SP_FileIcon).
        fallback_text (str, optional): Text to use for a fallback icon if the standard one isn't found.
        color (QColor, optional): Color to try and tint the icon with.

    Returns:
        QIcon: The requested icon, a fallback, or an empty QIcon if all fails.
    """
    style = QApplication.style()
    if not style: # Should not happen in a running QApplication
        return QIcon()

    # Get the icon candidate from the style
    icon_candidate = style.standardIcon(standard_pixmap_enum)

    # Defensive check: Ensure icon_candidate is QIcon
    # This is the main fix for the reported TypeError
    if isinstance(icon_candidate, QPixmap):
        # If standardIcon unexpectedly returned a QPixmap, wrap it in QIcon
        processed_icon = QIcon(icon_candidate)
        # Log this unexpected behavior if possible, or print a warning
        print(f"Warning: standardIcon() returned QPixmap for {standard_pixmap_enum}. Wrapped in QIcon.")
    elif not isinstance(icon_candidate, QIcon):
        # If it's neither QIcon nor QPixmap, but something else (highly unlikely for standardIcon)
        # or if it failed and returned None (though standardIcon usually returns a null QIcon)
        processed_icon = QIcon() # Default to an empty icon
        print(f"Warning: standardIcon() for {standard_pixmap_enum} did not return a QIcon or QPixmap. Using empty QIcon.")
    else:
        # It's already a QIcon (possibly null)
        processed_icon = icon_candidate


    # Handle colorization if a valid icon exists and color is specified
    if not processed_icon.isNull() and color and isinstance(color, QColor) and color.isValid():
        try:
            # Attempt to create a colorized version
            original_pixmap = processed_icon.pixmap(QSize(16, 16)) # Get a QPixmap
            if not original_pixmap.isNull():
                tinted_pixmap = QPixmap(original_pixmap.size())
                tinted_pixmap.fill(Qt.GlobalColor.transparent) # Start transparent

                painter = QPainter(tinted_pixmap)
                painter.drawPixmap(0, 0, original_pixmap) # Draw original icon
                # Use CompositionMode_SourceIn to apply color tint
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
                painter.fillRect(tinted_pixmap.rect(), color)
                painter.end()
                return QIcon(tinted_pixmap) # Return new QIcon from tinted pixmap
        except Exception as e:
            print(f"Error colorizing icon: {e}")
            # Fall through to return the processed_icon without colorization if error occurs

    # Handle fallback if icon is null and fallback text is provided
    if processed_icon.isNull() and fallback_text:
        try:
            pixmap = QPixmap(16, 16)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)

            # Determine text color: use provided 'color' if valid, else default
            text_color_to_use = QColor(Qt.GlobalColor.black) # Default
            if color and isinstance(color, QColor) and color.isValid():
                # If a general 'color' was passed for tinting, it might not be ideal for text.
                # Consider if a separate text_color parameter is needed for fallbacks,
                # or use a contrasting color based on a hypothetical background.
                # For now, just use the provided color if it's there.
                text_color_to_use = color
            
            painter.setPen(text_color_to_use)
            font = painter.font()
            font.setPointSize(max(6, 12 - len(fallback_text))) # Basic dynamic font sizing
            painter.setFont(font)
            painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, fallback_text)
            painter.end()
            return QIcon(pixmap) # Return QIcon from generated pixmap
        except Exception as e:
            print(f"Error creating fallback text icon: {e}")
            return QIcon() # Return empty icon on error

    return processed_icon # Return the processed (and possibly null) icon
