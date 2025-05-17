# main_window.py
# Contains the ERDCanvasWindow class, the main application window.

import sys
import csv
import math 
import os

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QGraphicsView, QMessageBox, QFileDialog, 
    QToolBar, QWidget, QHBoxLayout
)
from PyQt6.QtCore import Qt, QPointF, QSize
from PyQt6.QtGui import QColor, QBrush, QAction, QIcon, QKeySequence, QPixmap, QPainter

# Import from other modules
import constants 
from utils import get_standard_icon, snap_to_grid, get_contrasting_text_color
from data_models import Table, Column, Relationship
from gui_items import TableGraphicItem, OrthogonalRelationshipLine
from dialogs import TableDialog, RelationshipDialog, DefaultColorsDialog
from canvas_scene import ERDGraphicsScene


class ERDCanvasWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_file_path = None
        self.current_theme = "light" # Default theme
        self.user_default_table_body_color = None
        self.user_default_table_header_color = None
        
        self.current_theme_settings = {} 
        self.update_theme_settings() 
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

        self.create_toolbar_and_menus() 
        main_layout.addWidget(self.toolbar) 

        main_layout.addWidget(self.view, 1) 
        self.setCentralWidget(main_widget)

        print("Main window created.")
        self.apply_styles() 

    def update_theme_settings(self):
        """Updates the instance's current_theme_settings and the global one in constants."""
        if self.current_theme == "dark":
            self.current_theme_settings = constants.dark_theme.copy()
        else: # Default to light theme
            self.current_theme_settings = constants.light_theme.copy()
        
        if self.user_default_table_body_color:
            self.current_theme_settings["default_table_body_color"] = self.user_default_table_body_color
        if self.user_default_table_header_color:
            self.current_theme_settings["default_table_header_color"] = self.user_default_table_header_color
        
        constants.current_theme_settings.clear()
        constants.current_theme_settings.update(self.current_theme_settings)


    def set_theme(self, theme_name):
        previous_theme_body_default = QColor(self.current_theme_settings["default_table_body_color"])
        previous_theme_header_default = QColor(self.current_theme_settings["default_table_header_color"])

        self.current_theme = theme_name
        self.update_theme_settings() 
        self.apply_styles() 
        
        for table_data in self.tables_data.values():
            update_body = False
            update_header = False

            if self.user_default_table_body_color: 
                if table_data.body_color == previous_theme_body_default or \
                   table_data.body_color == (constants.dark_theme["default_table_body_color"] if theme_name == "light" else constants.light_theme["default_table_body_color"]): 
                    update_body = True
            elif table_data.body_color == previous_theme_body_default: 
                 update_body = True
            
            if self.user_default_table_header_color:
                if table_data.header_color == previous_theme_header_default or \
                   table_data.header_color == (constants.dark_theme["default_table_header_color"] if theme_name == "light" else constants.light_theme["default_table_header_color"]):
                    update_header = True
            elif table_data.header_color == previous_theme_header_default:
                 update_header = True

            if update_body:
                 table_data.body_color = QColor(self.current_theme_settings["default_table_body_color"])
            if update_header:
                 table_data.header_color = QColor(self.current_theme_settings["default_table_header_color"])


            if table_data.graphic_item:
                table_data.graphic_item.update()
        
        if self.scene: 
            self.scene.grid_pen.setColor(QColor(self.current_theme_settings.get("grid_color", QColor(200, 200, 200, 60))))
            self.scene.setBackgroundBrush(QBrush(self.current_theme_settings['view_bg']))
            self.scene.update() 

        for rel_data in self.relationships_data:
            if rel_data.graphic_item:
                rel_data.graphic_item.setPen(QPen(self.current_theme_settings.get("relationship_line_color", QColor(70,70,110)), 1.8))
                rel_data.graphic_item.update_tooltip_and_paint()

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
        # Use colors from self.current_theme_settings
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {self.current_theme_settings['window_bg'].name()};
            }}
            QToolBar {{
                background-color: {self.current_theme_settings['toolbar_bg'].name()};
                border: 1px solid {self.current_theme_settings['toolbar_border'].name()};
                padding: 5px; spacing: 8px; min-width: 180px; 
            }}
            QToolBar QToolButton {{ 
                background-color: {self.current_theme_settings['button_bg'].name()};
                border: 1px solid {self.current_theme_settings['button_border'].name()};
                border-radius: 4px; padding: 8px 5px; margin: 2px;
                min-width: 150px; text-align: left; 
                color: {self.current_theme_settings['text_color'].name()};
            }}
            QToolBar QToolButton:hover {{ background-color: {self.current_theme_settings['button_hover_bg'].name()}; }}
            QToolBar QToolButton:pressed {{ background-color: {self.current_theme_settings['button_pressed_bg'].name()}; }}
            QToolBar QToolButton:checked {{ 
                background-color: {self.current_theme_settings['button_checked_bg'].name()}; 
                border: 1px solid {self.current_theme_settings['button_checked_border'].name()};
            }}
            QPushButton {{ 
                background-color: {self.current_theme_settings['button_bg'].name()};
                border: 1px solid {self.current_theme_settings['button_border'].name()};
                border-radius: 4px; padding: 5px 10px; min-width: 80px;
                color: {self.current_theme_settings['text_color'].name()};
            }}
            QPushButton:hover {{ background-color: {self.current_theme_settings['button_hover_bg'].name()}; }}
            QPushButton:pressed {{ background-color: {self.current_theme_settings['button_pressed_bg'].name()}; }}
            QComboBox, QLineEdit {{
                border: 1px solid {self.current_theme_settings['button_border'].name()}; 
                border-radius: 3px; padding: 3px; min-height: 20px; 
                background-color: {self.current_theme_settings['view_bg'].name()}; 
                color: {self.current_theme_settings['text_color'].name()};
            }}
            QComboBox QAbstractItemView {{ 
                background-color: {self.current_theme_settings['view_bg'].name()};
                color: {self.current_theme_settings['text_color'].name()};
                selection-background-color: {self.current_theme_settings['button_checked_bg'].name()};
            }}
            QScrollArea {{ border: 1px solid {self.current_theme_settings['toolbar_border'].name()}; }}
            QLabel {{ padding: 2px; color: {self.current_theme_settings['dialog_text_color'].name()}; }}
            QDialog {{ background-color: {self.current_theme_settings['window_bg'].name()}; }}
            QMenuBar {{ background-color: {self.current_theme_settings['toolbar_bg'].name()}; color: {self.current_theme_settings['text_color'].name()};}}
            QMenuBar::item:selected {{ background-color: {self.current_theme_settings['button_hover_bg'].name()}; }}
            QMenu {{ background-color: {self.current_theme_settings['toolbar_bg'].name()}; color: {self.current_theme_settings['text_color'].name()}; }}
            QMenu::item:selected {{ background-color: {self.current_theme_settings['button_hover_bg'].name()}; }}

        """)
        self.view.setStyleSheet(f"background-color: {self.current_theme_settings['view_bg'].name()}; border: 1px solid {self.current_theme_settings['view_border'].name()};")
        if self.scene: 
            self.scene.setBackgroundBrush(QBrush(self.current_theme_settings['view_bg']))


    def create_toolbar_and_menus(self): 
        # --- Toolbar ---
        self.toolbar = QToolBar("Main Toolbar")
        self.toolbar.setMovable(False) 
        self.toolbar.setOrientation(Qt.Orientation.Vertical) 
        self.toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon) 
        self.toolbar.setIconSize(QSize(24,24)) 
        self.addToolBar(Qt.ToolBarArea.LeftToolBarArea, self.toolbar)

        actionNew = QAction(get_standard_icon(QApplication.style().StandardPixmap.SP_FileIcon, "New"), "&New Diagram", self)
        actionNew.setShortcut(QKeySequence.StandardKey.New)
        actionNew.triggered.connect(self.new_diagram)
        self.toolbar.addAction(actionNew)

        self.toolbar.addSeparator()

        actionSave = QAction(get_standard_icon(QApplication.style().StandardPixmap.SP_DialogSaveButton, "Save"), "&Save", self)
        actionSave.setShortcut(QKeySequence.StandardKey.Save)
        actionSave.triggered.connect(self.save_file)
        self.toolbar.addAction(actionSave)
        
        actionSaveAs = QAction(get_standard_icon(QApplication.style().StandardPixmap.SP_DriveHDIcon, "Save As"), "Save &As...", self) 
        actionSaveAs.setShortcut(QKeySequence.StandardKey.SaveAs)
        actionSaveAs.triggered.connect(self.save_file_as)
        self.toolbar.addAction(actionSaveAs)

        actionImportCSV = QAction(get_standard_icon(QApplication.style().StandardPixmap.SP_ArrowDown, "Import"), "&Import CSV", self)
        actionImportCSV.setShortcut(QKeySequence.StandardKey.Open)
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
        
        self.lightThemeAction = QAction("Light", self, checkable=True)
        self.lightThemeAction.setChecked(self.current_theme == "light")
        self.lightThemeAction.triggered.connect(lambda: self.set_theme("light"))
        themeMenu.addAction(self.lightThemeAction)

        self.darkThemeAction = QAction("Dark", self, checkable=True)
        self.darkThemeAction.setChecked(self.current_theme == "dark")
        self.darkThemeAction.triggered.connect(lambda: self.set_theme("dark"))
        themeMenu.addAction(self.darkThemeAction)
        
        from PyQt6.QtGui import QActionGroup # Moved import here to ensure it's available
        theme_action_group = QActionGroup(self)
        theme_action_group.addAction(self.lightThemeAction)
        theme_action_group.addAction(self.darkThemeAction)
        theme_action_group.setExclusive(True)


        settingsMenu = menubar.addMenu("&Settings")
        actionDefaultColors = QAction("Default Table Colors...", self)
        actionDefaultColors.triggered.connect(self.open_default_colors_dialog)
        settingsMenu.addAction(actionDefaultColors)


    def open_default_colors_dialog(self):
        dialog = DefaultColorsDialog(self, self) 
        if dialog.exec():
            pass


    def new_diagram(self):
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
        path, _ = QFileDialog.getSaveFileName(self, "Save ERD File", self.current_file_path or "", "CSV Files (*.csv);;All Files (*)") 
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


    def handle_add_table_button(self, table_name_prop=None, columns_prop=None, pos=None, width_prop=None, body_color_hex=None, header_color_hex=None): 
        if table_name_prop: 
            table_name = table_name_prop
            columns = columns_prop
            if not table_name: return None 
            if table_name in self.tables_data: 
                print(f"Import/Add: Table '{table_name}' already exists. Skipping.")
                return None 
        else: 
            initial_body_color = self.user_default_table_body_color or QColor(self.current_theme_settings["default_table_body_color"])
            initial_header_color = self.user_default_table_header_color or QColor(self.current_theme_settings["default_table_header_color"])
            
            dialog = TableDialog(self, table_name_prop if table_name_prop else "", 
                                 columns_prop, initial_body_color, initial_header_color) 
            if not dialog.exec(): return None 
            table_name, columns, body_color_hex, header_color_hex = dialog.get_table_data() 
            if not table_name:
                QMessageBox.warning(self, "Warning", "Table name cannot be empty.")
                return None
            if table_name in self.tables_data and not table_name_prop : 
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
        path, _ = QFileDialog.getOpenFileName(self, "Import ERD File", "", "CSV Files (*.csv);;All Files (*)") 
        if not path: return

        self.new_diagram() 

        parsed_tables = {} 
        parsed_relationships_from_csv = [] 

        try:
            with open(path, 'r', newline='', encoding='utf-8-sig') as csvfile: 
                reader = csv.reader(csvfile)
                
                current_section = "COLUMNS" 

                for row_num, row in enumerate(reader):
                    if not row: continue 
                    
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
                        if len(row) < 7: continue 
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
                    
                    elif current_section == "RELATIONSHIPS": 
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
                    body_color_hex=body_color_h, 
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

    def finalize_relationship_drawing(self, source_table_data, source_column_data, dest_table_data, dest_column_data):
        """Handles the logic after the user has clicked the source and destination columns for a new relationship."""
        fk_table, fk_col, pk_table, pk_col_obj = None, None, None, None

        if source_column_data.is_pk and not dest_column_data.is_pk: 
            fk_table, fk_col = dest_table_data, dest_column_data
            pk_table, pk_col_obj = source_table_data, source_column_data
        elif not source_column_data.is_pk and dest_column_data.is_pk: 
            fk_table, fk_col = source_table_data, source_column_data
            pk_table, pk_col_obj = dest_table_data, dest_column_data
        elif source_column_data.is_pk and dest_column_data.is_pk:
             QMessageBox.warning(self, "Invalid Connection", "Cannot directly connect two Primary Keys. One column must be a Foreign Key.")
             return
        else: 
            QMessageBox.warning(self, "Invalid Connection", 
                                f"Target column '{dest_column_data.name}' in '{dest_table_data.name}' must be a Primary Key, or source column '{source_column_data.name}' in '{source_table_data.name}' must be a Primary Key.")
            return

        if fk_col.is_fk and \
           (fk_col.references_table != pk_table.name or \
            fk_col.references_column != pk_col_obj.name):
            reply = QMessageBox.question(self, "Confirm FK Change",
                                         f"Column '{fk_col.name}' in '{fk_table.name}' is already an FK. Change it to reference '{pk_table.name}.{pk_col_obj.name}'?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.No:
                return
        
        fk_col.is_fk = True
        fk_col.references_table = pk_table.name
        fk_col.references_column = pk_col_obj.name
        fk_col.fk_relationship_type = "N:1" # Default when drawing
        
        if fk_table.graphic_item: fk_table.graphic_item.update()
        
        self.create_relationship(fk_table, pk_table, fk_col.name, pk_col_obj.name, fk_col.fk_relationship_type)


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
    if not isinstance(bg_color, QColor) or not bg_color.isValid():
        return QColor(current_theme_settings.get("text_color", QColor(Qt.GlobalColor.black))) 
    
    luminance = (0.299 * bg_color.redF() + 0.587 * bg_color.greenF() + 0.114 * bg_color.blueF())

    if luminance > 0.5:
        return QColor(Qt.GlobalColor.black)
    else:
        return QColor(Qt.GlobalColor.white)

