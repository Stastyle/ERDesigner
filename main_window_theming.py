# main_window_theming.py
# Manages theme settings and application styling.

from PyQt6.QtGui import QColor, QBrush, QPixmap, QPainter, QPen, QIcon
from PyQt6.QtCore import Qt, QPointF
import constants

def update_theme_settings_util(window):
    """Updates window.current_theme_settings based on current_theme and user defaults."""
    if window.current_theme == "dark":
        window.current_theme_settings.update(constants.dark_theme_colors)
    else: # Default to light theme
        window.current_theme_settings.update(constants.light_theme_colors)

    # Override with user-defined default colors if they exist
    if window.user_default_table_body_color:
        window.current_theme_settings["default_table_body_color"] = window.user_default_table_body_color
    if window.user_default_table_header_color:
        window.current_theme_settings["default_table_header_color"] = window.user_default_table_header_color
    
    constants.current_theme_settings.clear()
    constants.current_theme_settings.update(window.current_theme_settings)


def set_theme_util(window, theme_name, force_update_tables=False):
    """Sets the application theme and updates UI elements accordingly."""
    window.current_theme = theme_name
    update_theme_settings_util(window) 
    apply_styles_util(window) 

    if hasattr(window, 'mainFloatingButton') and window.mainFloatingButton:
        # Ensure iconSize is valid before trying to get width
        icon_size = window.mainFloatingButton.iconSize()
        icon_render_size = icon_size.width() if icon_size.isValid() and icon_size.width() > 0 else 24 # Default if invalid

        pm = QPixmap(icon_render_size, icon_render_size)
        pm.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pm)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        text_color = QColor(window.current_theme_settings.get("text_color", QColor(Qt.GlobalColor.black)))
        pen_width_for_icon = 2.5 
        pen = QPen(text_color, pen_width_for_icon) 
        painter.setPen(pen)
        
        margin = int(icon_render_size * 0.25)
        center_x = float(icon_render_size) / 2.0
        center_y = float(icon_render_size) / 2.0
        
        painter.drawLine(QPointF(margin, center_y), QPointF(icon_render_size - margin, center_y))
        painter.drawLine(QPointF(center_x, margin), QPointF(center_x, icon_render_size - margin))
        painter.end()
        window.mainFloatingButton.setIcon(QIcon(pm))


    for table_data in window.tables_data.values():
        update_body_color = False
        update_header_color = False

        if force_update_tables:
            update_body_color = True
            update_header_color = True
        else:
            previous_theme_default_body = constants.dark_theme_colors["default_table_body_color"] if theme_name == "light" else constants.light_theme_colors["default_table_body_color"]
            previous_theme_default_header = constants.dark_theme_colors["default_table_header_color"] if theme_name == "light" else constants.light_theme_colors["default_table_header_color"]

            if window.user_default_table_body_color: 
                 if table_data.body_color == previous_theme_default_body : 
                     update_body_color = True
            elif table_data.body_color == previous_theme_default_body: 
                 update_body_color = True

            if window.user_default_table_header_color:
                if table_data.header_color == previous_theme_default_header:
                    update_header_color = True
            elif table_data.header_color == previous_theme_default_header:
                 update_header_color = True
        
        if update_body_color:
            table_data.body_color = QColor(window.current_theme_settings["default_table_body_color"])
        if update_header_color:
            table_data.header_color = QColor(window.current_theme_settings["default_table_header_color"])
        
        if table_data.graphic_item and (update_body_color or update_header_color):
            table_data.graphic_item.update() 

    if window.scene:
        window.scene.grid_pen.setColor(QColor(window.current_theme_settings.get("grid_color")))
        window.scene.setBackgroundBrush(QBrush(window.current_theme_settings['view_bg']))
        window.scene.update() 

    for rel_data in window.relationships_data:
        if rel_data.graphic_item:
            rel_data.graphic_item.setPen(QPen(window.current_theme_settings.get("relationship_line_color"), 1.8))
            rel_data.graphic_item.update_tooltip_and_paint() 

    if hasattr(window, 'diagram_explorer_tree') and window.diagram_explorer_tree:
        window.diagram_explorer_tree.setStyleSheet(f"""
            QTreeWidget {{
                background-color: {window.current_theme_settings['window_bg'].name()};
                color: {window.current_theme_settings['text_color'].name()};
                border: 1px solid {window.current_theme_settings['toolbar_border'].name()};
            }}
            QTreeWidget::item:hover {{
                background-color: {window.current_theme_settings['button_hover_bg'].name()};
            }}
            QTreeWidget::item:selected {{
                background-color: {window.current_theme_settings['button_checked_bg'].name()};
                color: {window.current_theme_settings['button_checked_text_color'].name()};
            }}
            QHeaderView::section {{ 
                background-color: {window.current_theme_settings['toolbar_bg'].name()};
                color: {window.current_theme_settings['text_color'].name()};
                padding: 4px;
                border: 1px solid {window.current_theme_settings['toolbar_border'].name()};
            }}
        """)
    if hasattr(window, 'diagram_explorer_dock') and window.diagram_explorer_dock:
         window.diagram_explorer_dock.setStyleSheet(f"""
            QDockWidget {{
                background-color: {window.current_theme_settings['toolbar_bg'].name()};
                color: {window.current_theme_settings['text_color'].name()};
            }}
            QDockWidget::title {{ 
                text-align: left; 
                background: {window.current_theme_settings['toolbar_bg'].name()};
                padding: 5px;
                padding-left: 8px; 
                color: {window.current_theme_settings['text_color'].name()};
                border-bottom: 1px solid {window.current_theme_settings['toolbar_border'].name()};
            }}
        """)

    window.save_app_settings() 
    if hasattr(window, '_update_floating_button_position'): 
        window._update_floating_button_position()


def apply_styles_util(window):
    """Applies the general stylesheet to the main window and its components."""
    # Define the style for the floating action button specifically
    # Button size is 44px, so radius is 22px for a circle.
    fab_style = """
        QPushButton#mainFloatingButton {{
            border-radius: 22px; /* Half of the button's width/height (44px / 2) */
            background-color: {button_bg};
            color: {text_color}; 
            border: 1px solid {button_border};
            padding: 0px; 
        }}
        QPushButton#mainFloatingButton:hover {{
            background-color: {button_hover_bg};
        }}
    """.format(
        button_bg=window.current_theme_settings['button_bg'].name(),
        text_color=window.current_theme_settings['text_color'].name(), 
        button_border=window.current_theme_settings['button_border'].name(),
        button_hover_bg=window.current_theme_settings['button_hover_bg'].name()
    )

    super_stylesheet = f"""
        QMainWindow {{
            background-color: {window.current_theme_settings['window_bg'].name()};
        }}
        QPushButton {{
            background-color: {window.current_theme_settings['button_bg'].name()};
            border: 1px solid {window.current_theme_settings['button_border'].name()};
            border-radius: 4px;
            padding: 5px 10px;
            min-width: 80px;
            color: {window.current_theme_settings['text_color'].name()};
        }}
        QPushButton:hover {{
            background-color: {window.current_theme_settings['button_hover_bg'].name()};
        }}
        QPushButton:pressed {{
            background-color: {window.current_theme_settings['button_pressed_bg'].name()};
        }}
        QComboBox, QLineEdit {{
            border: 1px solid {window.current_theme_settings['button_border'].name()};
            border-radius: 3px;
            padding: 3px;
            min-height: 20px; 
            background-color: {window.current_theme_settings['view_bg'].name()}; 
            color: {window.current_theme_settings['text_color'].name()};
        }}
        QComboBox QAbstractItemView {{ 
            background-color: {window.current_theme_settings['view_bg'].name()};
            color: {window.current_theme_settings['text_color'].name()};
            selection-background-color: {window.current_theme_settings['button_checked_bg'].name()};
        }}
        QScrollArea {{
             border: 1px solid {window.current_theme_settings['toolbar_border'].name()};
        }}
        QLabel {{
            padding: 2px;
            color: {window.current_theme_settings['dialog_text_color'].name()}; 
        }}
        QDialog {{
            background-color: {window.current_theme_settings['window_bg'].name()};
        }}
        QMenuBar {{
            background-color: {window.current_theme_settings['toolbar_bg'].name()};
            color: {window.current_theme_settings['text_color'].name()};
        }}
        QMenuBar::item:selected {{ 
            background-color: {window.current_theme_settings['button_hover_bg'].name()};
        }}
        QMenu {{
            background-color: {window.current_theme_settings['toolbar_bg'].name()};
            color: {window.current_theme_settings['text_color'].name()};
            border: 1px solid {window.current_theme_settings['toolbar_border'].name()};
        }}
        QMenu::item:selected {{
            background-color: {window.current_theme_settings['button_hover_bg'].name()};
        }}
        {fab_style}
    """
    window.setStyleSheet(super_stylesheet)

    if window.view:
        window.view.setStyleSheet(f"background-color: {window.current_theme_settings['view_bg'].name()}; border: 1px solid {window.current_theme_settings['view_border'].name()};")
    if window.scene:
        window.scene.setBackgroundBrush(QBrush(window.current_theme_settings['view_bg']))
