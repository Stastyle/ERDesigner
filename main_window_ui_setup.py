# main_window_ui_setup.py
# Handles creation of UI elements like menus, diagram explorer, and floating button.

from PyQt6.QtWidgets import (
    QApplication, QDockWidget, QTreeWidget, QPushButton, QMenu, QStyle,
    QHeaderView 
)
from PyQt6.QtCore import Qt, QSize, QPoint, QPointF
from PyQt6.QtGui import QAction, QIcon, QKeySequence, QPixmap, QPainter, QPen, QColor, QActionGroup

from utils import get_standard_icon 
import constants 

def create_menus(window):
    """Creates the main menubar and its menus."""
    menubar = window.menuBar()

    # File Menu
    fileMenu = menubar.addMenu("&File")
    actionNew = QAction(get_standard_icon(QApplication.style().StandardPixmap.SP_FileIcon, "New"), "&New Diagram", window)
    actionNew.setShortcut(QKeySequence.StandardKey.New)
    actionNew.triggered.connect(window.new_diagram)
    fileMenu.addAction(actionNew)

    actionSave = QAction(get_standard_icon(QApplication.style().StandardPixmap.SP_DialogSaveButton, "Save"), "&Save", window)
    actionSave.setShortcut(QKeySequence.StandardKey.Save)
    actionSave.triggered.connect(window.save_file)
    fileMenu.addAction(actionSave)

    actionSaveAs = QAction(get_standard_icon(QApplication.style().StandardPixmap.SP_DriveHDIcon, "Save As"), "Save &As...", window)
    actionSaveAs.setShortcut(QKeySequence.StandardKey.SaveAs)
    actionSaveAs.triggered.connect(window.save_file_as)
    fileMenu.addAction(actionSaveAs)

    actionImportCSV = QAction(get_standard_icon(QApplication.style().StandardPixmap.SP_ArrowDown, "Import"), "&Import CSV", window)
    actionImportCSV.setShortcut(QKeySequence.StandardKey.Open) 
    actionImportCSV.triggered.connect(window.handle_import_csv_button)
    fileMenu.addAction(actionImportCSV)

    fileMenu.addSeparator()
    actionExit = QAction(get_standard_icon(QApplication.style().StandardPixmap.SP_DialogCloseButton, "Exit"), "E&xit", window)
    actionExit.triggered.connect(window.close)
    fileMenu.addAction(actionExit)

    # Edit Menu
    editMenu = menubar.addMenu("&Edit")
    window.undo_action = window.undo_stack.createUndoAction(window, "&Undo")
    window.undo_action.setIcon(get_standard_icon(QApplication.style().StandardPixmap.SP_ArrowLeft, "Undo"))
    window.undo_action.setShortcut(QKeySequence.StandardKey.Undo)
    editMenu.addAction(window.undo_action)

    window.redo_action = window.undo_stack.createRedoAction(window, "&Redo")
    window.redo_action.setIcon(get_standard_icon(QApplication.style().StandardPixmap.SP_ArrowRight, "Redo"))
    window.redo_action.setShortcut(QKeySequence.StandardKey.Redo)
    editMenu.addAction(window.redo_action)

    editMenu.addSeparator()
    window.delete_action = QAction(get_standard_icon(QApplication.style().StandardPixmap.SP_TrashIcon, "Delete"), "&Delete", window)
    window.delete_action.setShortcut(QKeySequence.StandardKey.Delete)
    window.delete_action.triggered.connect(window.delete_selected_items)
    editMenu.addAction(window.delete_action)
    
    editMenu.addSeparator()
    window.actionAddTable = QAction(get_standard_icon(QApplication.style().StandardPixmap.SP_FileDialogNewFolder, "Add Tbl"), "Add &Table", window)
    window.actionAddTable.triggered.connect(lambda: window.handle_add_table_button()) 
    editMenu.addAction(window.actionAddTable)

    window.actionDrawRelationship = QAction(get_standard_icon(QApplication.style().StandardPixmap.SP_ArrowForward, "Link"), "&Draw Relationship", window)
    window.actionDrawRelationship.setCheckable(True)
    window.actionDrawRelationship.triggered.connect(window.toggle_relationship_mode_action) 
    editMenu.addAction(window.actionDrawRelationship)

    # View Menu
    viewMenu = menubar.addMenu("&View")
    window.toggleExplorerAction = QAction("Toggle Diagram Explorer", window, checkable=True)
    window.toggleExplorerAction.triggered.connect(window.toggle_diagram_explorer)
    viewMenu.addAction(window.toggleExplorerAction)
    
    viewMenu.addSeparator()
    themeMenu = viewMenu.addMenu("&Theme")
    window.lightThemeAction = QAction("Light", window, checkable=True)
    window.lightThemeAction.setChecked(window.current_theme == "light")
    window.lightThemeAction.triggered.connect(lambda: window.set_theme("light"))
    themeMenu.addAction(window.lightThemeAction)

    window.darkThemeAction = QAction("Dark", window, checkable=True)
    window.darkThemeAction.setChecked(window.current_theme == "dark")
    window.darkThemeAction.triggered.connect(lambda: window.set_theme("dark"))
    themeMenu.addAction(window.darkThemeAction)

    theme_action_group = QActionGroup(window)
    theme_action_group.addAction(window.lightThemeAction)
    theme_action_group.addAction(window.darkThemeAction)
    theme_action_group.setExclusive(True)

    # Settings Menu
    settingsMenu = menubar.addMenu("&Settings")
    actionDefaultColors = QAction("Default Table Colors...", window)
    actionDefaultColors.triggered.connect(window.open_default_colors_dialog)
    settingsMenu.addAction(actionDefaultColors)

    actionCanvasSettings = QAction("Canvas Settings...", window)
    actionCanvasSettings.triggered.connect(window.open_canvas_settings_dialog)
    settingsMenu.addAction(actionCanvasSettings)
    
    actionDataTypeSettings = QAction("Column Data Types...", window)
    actionDataTypeSettings.triggered.connect(window.open_datatype_settings_dialog)
    settingsMenu.addAction(actionDataTypeSettings)


def create_diagram_explorer_widget(window):
    """Creates the diagram explorer dock widget and tree."""
    window.diagram_explorer_dock = QDockWidget("Diagram Explorer", window)
    window.diagram_explorer_dock.setObjectName("DiagramExplorerDock")
    window.diagram_explorer_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)

    window.diagram_explorer_tree = QTreeWidget()
    window.diagram_explorer_tree.setHeaderLabels(["Item Name", "Type"]) 
    window.diagram_explorer_tree.setAlternatingRowColors(True)
    window.diagram_explorer_tree.itemDoubleClicked.connect(window.on_explorer_item_double_clicked)

    window.diagram_explorer_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
    window.diagram_explorer_tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents) 

    window.diagram_explorer_dock.setWidget(window.diagram_explorer_tree)
    window.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, window.diagram_explorer_dock)
    window.diagram_explorer_dock.visibilityChanged.connect(lambda visible: update_floating_button_position_widget(window))


def create_main_floating_action_button_widget(window):
    """Creates the main floating action button."""
    button_size = 44  
    icon_render_size = 24 

    window.mainFloatingButton = QPushButton(window) 
    window.mainFloatingButton.setObjectName("mainFloatingButton")
    window.mainFloatingButton.setFixedSize(button_size, button_size)
    
    pm = QPixmap(icon_render_size, icon_render_size)
    pm.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    
    text_color = QColor(window.current_theme_settings.get("text_color", QColor(Qt.GlobalColor.black)))
    pen_width = 2.5 
    pen = QPen(text_color, pen_width) 
    painter.setPen(pen)
    
    margin = int(icon_render_size * 0.25) 
    center_x = float(icon_render_size) / 2.0
    center_y = float(icon_render_size) / 2.0
    
    painter.drawLine(QPointF(margin, center_y), QPointF(icon_render_size - margin, center_y))
    painter.drawLine(QPointF(center_x, margin), QPointF(center_x, icon_render_size - margin))

    painter.end()
    plus_icon = QIcon(pm)

    window.mainFloatingButton.setIcon(plus_icon)
    window.mainFloatingButton.setIconSize(QSize(icon_render_size, icon_render_size))
    window.mainFloatingButton.setToolTip("Add Item") 
    window.mainFloatingButton.clicked.connect(window.show_floating_button_menu)
    
    window.mainFloatingButton.raise_() 
    window.mainFloatingButton.show()


def update_floating_button_position_widget(window):
    """Updates the position of the floating action button relative to the main window's central widget area."""
    button_size = window.mainFloatingButton.width() if hasattr(window, 'mainFloatingButton') and window.mainFloatingButton else 44
    margin = 25 

    if hasattr(window, 'mainFloatingButton') and window.mainFloatingButton and window.isVisible():
        try:
            central_widget = window.centralWidget()
            if not central_widget:
                return

            central_widget_geom = central_widget.geometry()
            
            btn_x_raw = float(central_widget_geom.right() - button_size - margin)
            btn_y_raw = float(central_widget_geom.bottom() - button_size - margin)
            
            btn_x_int = int(btn_x_raw)
            btn_y_int = int(btn_y_raw)
            
            window.mainFloatingButton.move(btn_x_int, btn_y_int)
            window.mainFloatingButton.raise_()

        except RuntimeError as e:
            # print(f"Error in update_floating_button_position_widget: {e}")
            pass


def show_floating_button_menu_widget(window):
    """Shows the context menu for the floating action button."""
    menu = QMenu(window)
    menu.setStyleSheet(f"""
        QMenu {{
            background-color: {window.current_theme_settings['toolbar_bg'].name()};
            color: {window.current_theme_settings['text_color'].name()};
            border: 1px solid {window.current_theme_settings['toolbar_border'].name()};
        }}
        QMenu::item:selected {{
            background-color: {window.current_theme_settings['button_hover_bg'].name()};
        }}
    """)
    
    add_table_action = QAction("Add Table", window) 
    add_table_action.triggered.connect(lambda: window.handle_add_table_button())
    menu.addAction(add_table_action)

    add_relationship_action = QAction("Add Relationship", window) 
    add_relationship_action.setCheckable(True)
    add_relationship_action.setChecked(window.drawing_relationship_mode)
    add_relationship_action.triggered.connect(window.toggle_relationship_mode_action)
    menu.addAction(add_relationship_action)
    
    button_pos_global = window.mainFloatingButton.mapToGlobal(QPoint(0, 0))
    menu_height_hint = menu.sizeHint().height()
    
    menu_x = button_pos_global.x()
    menu_y = button_pos_global.y() - menu_height_hint
    
    if menu_y < 0 : 
        menu_y = button_pos_global.y() + window.mainFloatingButton.height()

    menu.exec(QPoint(menu_x, menu_y))
