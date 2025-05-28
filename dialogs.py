# dialogs.py
# This file contains QDialog subclasses for user interactions.

from PyQt6.QtWidgets import ( QMenu,
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QLabel, QScrollArea, QWidget, QGridLayout, QTabWidget,
    QPushButton, QDialogButtonBox, QCheckBox, QComboBox, QHBoxLayout, QColorDialog,
    QApplication, QSizePolicy, QListWidget, QListWidgetItem, QAbstractItemView,
    QSpinBox, QInputDialog, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtGui import QFontMetrics, QColor, QIcon, QPixmap, QPainter, QAction

import constants # Import the constants module
from utils import get_standard_icon, get_contrasting_text_color
from data_models import Column

class ColorSwatchButton(QPushButton):
    """A QPushButton that displays a color and handles context menu for deletion."""
    delete_requested = pyqtSignal(QColor)

    def __init__(self, color_obj, main_window_ref, parent=None): # Added main_window_ref
        super().__init__(parent)
        self.color_data = color_obj
        self.main_window_ref = main_window_ref # Store main window reference
        self.setFixedSize(20, 20)
        self.setStyleSheet(f"background-color: {self.color_data.name()}; border: 1px solid gray;")
        self.setToolTip(self.color_data.name())

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        if self.main_window_ref and hasattr(self.main_window_ref, 'current_theme_settings'):
            menu.setStyleSheet(f"""
                QMenu {{
                    background-color: {self.main_window_ref.current_theme_settings.get('toolbar_bg', QColor(240,240,240)).name()};
                    color: {self.main_window_ref.current_theme_settings.get('text_color', QColor(0,0,0)).name()};
                    border: 1px solid {self.main_window_ref.current_theme_settings.get('toolbar_border', QColor(200,200,200)).name()};
                }}
                QMenu::item:selected {{
                    background-color: {self.main_window_ref.current_theme_settings.get('button_hover_bg', QColor(220,220,220)).name()};
                }}
            """)

        delete_action = QAction("Delete Custom Color", self)
        delete_action.triggered.connect(self.request_delete)
        menu.addAction(delete_action)
        menu.exec(event.globalPos())

    def request_delete(self):
        self.delete_requested.emit(self.color_data)


class AdvancedColorPickerDialog(QDialog):
    def __init__(self, initial_color, main_window_ref, parent=None): # Added main_window_ref
        super().__init__(parent)
        self.setWindowTitle("Select Color")
        self.setMinimumWidth(240) # Adjusted for a more compact layout
        self.selected_color = QColor(initial_color) # Start with the initial color
        self.is_new_custom_pick = False # Flag to indicate if a new color was picked from QColorDialog

        main_layout = QVBoxLayout(self)
        self.main_window_ref = main_window_ref # Store main window reference
        self.tab_widget = QTabWidget()

        # Basic Colors Tab
        basic_colors_widget = QWidget()
        basic_layout = QGridLayout(basic_colors_widget)
        basic_layout.setSpacing(5)
        basic_colors_per_row = 4 # Aim for a 4x3 grid for 12 basic colors
        row, col = 0, 0
        for i, hex_color in enumerate(constants.BASIC_COLORS_HEX):
            color = QColor(hex_color)
            btn = QPushButton()
            btn.setFixedSize(20, 20) # Smaller color swatch buttons
            btn.setStyleSheet(f"background-color: {color.name()}; border: 1px solid gray;")
            btn.setToolTip(color.name())
            btn.clicked.connect(lambda chk, c=color: self.set_selected_color(c, is_new_custom=False))
            basic_layout.addWidget(btn, row, col)
            col += 1
            if col >= basic_colors_per_row:
                col = 0
                row += 1
        self.tab_widget.addTab(basic_colors_widget, "Basic Colors")

        # Custom Colors Tab
        custom_colors_widget = QWidget()
        custom_layout = QVBoxLayout(custom_colors_widget)
        
        self.custom_colors_grid_widget = QWidget() # For the grid of saved custom colors
        self.custom_colors_grid_layout = QGridLayout(self.custom_colors_grid_widget)
        self.custom_colors_grid_layout.setSpacing(5)
        self.populate_custom_colors_grid()
        custom_layout.addWidget(self.custom_colors_grid_widget)

        btn_choose_from_palette = QPushButton("Choose from Palette...")
        btn_choose_from_palette.clicked.connect(self.pick_from_palette)
        custom_layout.addWidget(btn_choose_from_palette)
        custom_layout.addStretch()
        self.tab_widget.addTab(custom_colors_widget, "Custom Colors")

        main_layout.addWidget(self.tab_widget)

        # OK and Cancel buttons
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        main_layout.addWidget(self.buttonBox)

    def populate_custom_colors_grid(self):
        # Clear existing buttons
        for i in reversed(range(self.custom_colors_grid_layout.count())): 
            widget_to_remove = self.custom_colors_grid_layout.itemAt(i).widget()
            if widget_to_remove:
                widget_to_remove.setParent(None)
                widget_to_remove.deleteLater()

        row, col = 0, 0
        custom_colors_per_row = 6 # Aim for a 6xN grid for custom colors
        for color in constants.user_saved_custom_colors:
            # Always use ColorSwatchButton for the custom colors grid
            btn = ColorSwatchButton(color, self.main_window_ref, self) # Pass main_window_ref
            btn.clicked.connect(lambda chk, c=color: self.set_selected_color(c, is_new_custom=False))
            btn.delete_requested.connect(self.handle_delete_custom_color)

            self.custom_colors_grid_layout.addWidget(btn, row, col)
            col += 1
            if col >= custom_colors_per_row:
                col = 0
                row += 1
    def pick_from_palette(self):
        color = QColorDialog.getColor(self.selected_color, self, "Choose Custom Color")
        if color.isValid():
            # Check if this color is already basic or saved custom
            is_basic = any(QColor(bc_hex).name() == color.name() for bc_hex in constants.BASIC_COLORS_HEX)
            is_existing_custom = any(saved_c.name() == color.name() for saved_c in constants.user_saved_custom_colors)
            
            self.set_selected_color(color, is_new_custom=not (is_basic or is_existing_custom))
            self.accept() # Accept immediately after picking from palette

    def set_selected_color(self, color, is_new_custom):
        self.selected_color = color
        self.is_new_custom_pick = is_new_custom
        if not is_new_custom: # If picked from basic or existing custom, accept dialog
            self.accept()

    def get_result(self):
        return self.selected_color, self.is_new_custom_pick

    def handle_delete_custom_color(self, color_to_delete):
        if color_to_delete in constants.user_saved_custom_colors:
            constants.user_saved_custom_colors.remove(color_to_delete)
            self.populate_custom_colors_grid() # Refresh the grid
            if self.main_window_ref and hasattr(self.main_window_ref, 'save_app_settings'):
                self.main_window_ref.save_app_settings() # Save changes to config



class DefaultColorsDialog(QDialog):
    def __init__(self, parent_window_ref, parent=None):
        super().__init__(parent)
        self.main_window_ref = parent_window_ref
        self.setWindowTitle("Set Default Table Colors")
        self.setMinimumWidth(400)
        # Use constants.current_theme_settings which is updated by main_window
        self.newly_picked_custom_colors = set() # To store hex strings of new custom colors
        self.setStyleSheet(f"QDialog {{ background-color: {constants.current_theme_settings.get('window_bg', QColor('#F0F0F0')).name()}; }} "
                           f"QLabel, QPushButton {{ color: {constants.current_theme_settings.get('dialog_text_color', QColor('#000000')).name()}; }}")

        layout = QFormLayout(self)

        self.current_body_color = self.main_window_ref.user_default_table_body_color or \
                                  QColor(constants.current_theme_settings.get('default_table_body_color', QColor(Qt.GlobalColor.white)))
        self.current_header_color = self.main_window_ref.user_default_table_header_color or \
                                    QColor(constants.current_theme_settings.get('default_table_header_color', QColor(Qt.GlobalColor.lightGray)))

        self.body_color_button = QPushButton(f"Body: {self.current_body_color.name()}")
        self.body_color_button.setStyleSheet(
            f"background-color: {self.current_body_color.name()}; "
            f"color: {get_contrasting_text_color(self.current_body_color).name()}; padding: 5px;"
        )
        self.body_color_button.clicked.connect(self.pick_body_color)

        self.header_color_button = QPushButton(f"Header: {self.current_header_color.name()}")
        self.header_color_button.setStyleSheet(
            f"background-color: {self.current_header_color.name()}; "
            f"color: {get_contrasting_text_color(self.current_header_color).name()}; padding: 5px;"
        )
        self.header_color_button.clicked.connect(self.pick_header_color)

        layout.addRow("Default Table Body Color:", self.body_color_button)
        layout.addRow("Default Table Header Color:", self.header_color_button)

        self.buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel) # Defined self.buttonBox
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setText("OK")
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancel")
        self.buttonBox.accepted.connect(self.accept_changes)
        self.buttonBox.rejected.connect(self.reject)
        layout.addWidget(self.buttonBox)

    def pick_body_color(self):
        picker_dialog = AdvancedColorPickerDialog(self.current_body_color, self.main_window_ref, self)
        if picker_dialog.exec():
            chosen_color, was_new_custom = picker_dialog.get_result()
            if chosen_color.isValid():
                self.current_body_color = chosen_color
                self.body_color_button.setText(f"Body: {chosen_color.name()}")
                self.body_color_button.setStyleSheet(
                    f"background-color: {chosen_color.name()}; color: {get_contrasting_text_color(chosen_color).name()}; padding: 5px;"
                )
                if was_new_custom:
                    self.newly_picked_custom_colors.add(chosen_color.name())

    def pick_header_color(self):
        picker_dialog = AdvancedColorPickerDialog(self.current_header_color, self.main_window_ref, self)
        if picker_dialog.exec():
            chosen_color, was_new_custom = picker_dialog.get_result()
            if chosen_color.isValid():
                self.current_header_color = chosen_color
                self.header_color_button.setText(f"Header: {chosen_color.name()}")
                self.header_color_button.setStyleSheet(
                    f"background-color: {chosen_color.name()}; color: {get_contrasting_text_color(chosen_color).name()}; padding: 5px;"
                )
                if was_new_custom:
                    self.newly_picked_custom_colors.add(chosen_color.name())

    def accept_changes(self):
        old_body_color = self.main_window_ref.user_default_table_body_color
        old_header_color = self.main_window_ref.user_default_table_header_color
        
        new_body_color = self.current_body_color
        new_header_color = self.current_header_color

        # Handle newly picked custom colors and save if list changed
        custom_color_list_changed = False
        if self.newly_picked_custom_colors:
            current_saved_hex = {c.name() for c in constants.user_saved_custom_colors}
            basic_hex = {QColor(bc_hex).name() for bc_hex in constants.BASIC_COLORS_HEX}
            
            for color_hex in self.newly_picked_custom_colors:
                if color_hex not in current_saved_hex and color_hex not in basic_hex:
                    constants.user_saved_custom_colors.append(QColor(color_hex))
                    made_changes_to_custom_list = True
            
            if made_changes_to_custom_list:
                constants.user_saved_custom_colors = constants.user_saved_custom_colors[-constants.MAX_SAVED_CUSTOM_COLORS:]
                custom_color_list_changed = True # Ensure this flag is accurate

        if custom_color_list_changed:
             self.main_window_ref.save_app_settings() # Save custom color list changes

        # Check if default colors actually changed
        default_colors_changed = False
        if (old_body_color.name() if old_body_color else None) != (new_body_color.name() if new_body_color else None) or \
           (old_header_color.name() if old_header_color else None) != (new_header_color.name() if new_header_color else None):
            from commands import EditDefaultColorsCommand # Local import
            command = EditDefaultColorsCommand(self.main_window_ref,
                                               old_body_color, old_header_color,
                                               new_body_color, new_header_color)
            self.main_window_ref.undo_stack.push(command)
        self.accept()

    def get_colors(self):
        return self.current_body_color, self.current_header_color


class RelationshipDialog(QDialog):
    def __init__(self, relationship_data, parent_window_ref, parent=None):
        super().__init__(parent)
        self.relationship_data = relationship_data
        self.main_window_ref = parent_window_ref
        self.setWindowTitle("Relationship Properties")
        self.setStyleSheet(f"QDialog {{ background-color: {constants.current_theme_settings.get('window_bg', QColor('#F0F0F0')).name()}; }} "
                           f"QLabel, QComboBox {{ color: {constants.current_theme_settings.get('dialog_text_color', QColor('#000000')).name()}; }}")

        layout = QFormLayout(self)

        self.from_label = QLabel(f"From (FK Side): {relationship_data.table1_name}.{relationship_data.fk_column_name}")
        self.to_label = QLabel(f"To (PK Side): {relationship_data.table2_name}.{relationship_data.pk_column_name}")

        self.type_combo = QComboBox()
        self.type_combo.addItems(["N:1", "1:1", "1:N", "M:N"])
        self.type_combo.setCurrentText(relationship_data.relationship_type or "N:1")

        layout.addRow(self.from_label)
        layout.addRow(self.to_label)
        layout.addRow("Relationship Type (FK table to PK table):", self.type_combo)

        self.buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel) # Defined self.buttonBox
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setText("OK")
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancel")
        self.buttonBox.accepted.connect(self.accept_changes)
        self.buttonBox.rejected.connect(self.reject)
        layout.addWidget(self.buttonBox)

    def accept_changes(self):
        new_type = self.type_combo.currentText()
        if self.relationship_data.relationship_type != new_type:
            self.relationship_data.relationship_type = new_type
            if self.main_window_ref and hasattr(self.main_window_ref, 'tables_data'):
                fk_table_obj = self.main_window_ref.tables_data.get(self.relationship_data.table1_name)
                if fk_table_obj:
                    fk_col_obj = fk_table_obj.get_column_by_name(self.relationship_data.fk_column_name)
                    if fk_col_obj:
                        fk_col_obj.fk_relationship_type = new_type
                        if fk_table_obj.graphic_item: fk_table_obj.graphic_item.update()

            if self.relationship_data.graphic_item and hasattr(self.relationship_data.graphic_item, 'update_tooltip_and_paint'):
                self.relationship_data.graphic_item.update_tooltip_and_paint()
            
            if self.main_window_ref and hasattr(self.main_window_ref, 'undo_stack'):
                 self.main_window_ref.update_window_title() 
        self.accept()

class ColumnEntryWidget(QWidget):
    delete_requested = pyqtSignal(QListWidgetItem)
    def __init__(self, main_window_ref, table_name_input_ref, list_item_ref, parent_dialog,
                 name="", data_type="TEXT", is_pk=False, is_fk=False,
                 ref_table_name="", ref_col_name="", fk_rel_type="N:1"):
        super().__init__()
        self.main_window_ref = main_window_ref
        self.table_name_input_ref = table_name_input_ref
        self.list_item_ref = list_item_ref
        self.parent_dialog = parent_dialog
        self.init_ui(name, data_type, is_pk, is_fk, ref_table_name, ref_col_name, fk_rel_type)

    def init_ui(self, name, data_type, is_pk, is_fk, ref_table_name, ref_col_name, fk_rel_type):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(2, 2, 2, 2); main_layout.setSpacing(3)
        top_row_h_layout = QHBoxLayout()
        self.name_edit = QLineEdit(name); self.name_edit.setPlaceholderText("Column Name")
        self.type_combo = QComboBox()
        
        self.type_combo.addItems(constants.editable_column_data_types)
        if data_type in constants.editable_column_data_types:
            self.type_combo.setCurrentText(data_type)
        elif constants.editable_column_data_types: 
            self.type_combo.setCurrentIndex(0) 

        self.pk_checkbox = QCheckBox("PK"); self.pk_checkbox.setChecked(is_pk)
        self.fk_checkbox = QCheckBox("FK"); self.fk_checkbox.setChecked(is_fk)
        self.fk_checkbox.toggled.connect(self.toggle_fk_details)
        self.btn_remove_col = QPushButton("X")
        font_metrics = QFontMetrics(self.font())
        button_height = font_metrics.height() + 6
        button_width_char = font_metrics.horizontalAdvance("X") + 10
        self.btn_remove_col.setFixedSize(button_width_char, button_height)
        self.btn_remove_col.clicked.connect(self.request_delete)
        top_row_h_layout.addWidget(self.name_edit, 3); top_row_h_layout.addWidget(self.type_combo, 2)
        top_row_h_layout.addWidget(self.pk_checkbox); top_row_h_layout.addWidget(self.fk_checkbox)
        top_row_h_layout.addStretch(1); top_row_h_layout.addWidget(self.btn_remove_col)
        main_layout.addLayout(top_row_h_layout)
        self.fk_details_widget = QWidget()
        fk_details_layout = QHBoxLayout(self.fk_details_widget)
        fk_details_layout.setContentsMargins(20, 0, 0, 0)
        self.ref_table_combo = QComboBox(); self.ref_table_combo.setPlaceholderText("Referenced Table")
        self.ref_col_combo = QComboBox(); self.ref_col_combo.setPlaceholderText("Referenced PK Column")
        self.fk_rel_type_combo = QComboBox(); self.fk_rel_type_combo.addItems(["N:1", "1:1", "1:N", "M:N"])
        self.fk_rel_type_combo.setCurrentText(fk_rel_type)
        fk_details_layout.addWidget(QLabel("-> Refers to:")); fk_details_layout.addWidget(self.ref_table_combo, 2)
        fk_details_layout.addWidget(QLabel(".")); fk_details_layout.addWidget(self.ref_col_combo, 2)
        fk_details_layout.addWidget(QLabel("Rel.Type:")); fk_details_layout.addWidget(self.fk_rel_type_combo, 1)
        fk_details_layout.addStretch()
        main_layout.addWidget(self.fk_details_widget)
        self.fk_details_widget.setVisible(is_fk)
        self.ref_table_combo.currentTextChanged.connect(self.update_ref_col_combo_internal)
        self.populate_ref_table_combo(ref_table_name)
        self.update_ref_col_combo_internal(self.ref_table_combo.currentText(), ref_col_name)

    def toggle_fk_details(self, checked):
        self.fk_details_widget.setVisible(checked)
        if checked:
            self.populate_ref_table_combo(self.ref_table_combo.currentText() or None)
            self.update_ref_col_combo_internal(self.ref_table_combo.currentText(), self.ref_col_combo.currentText() or None)

    def populate_ref_table_combo(self, current_ref_table_name=None):
        self.ref_table_combo.blockSignals(True); self.ref_table_combo.clear()
        current_table_being_edited = self.table_name_input_ref.text().strip()
        added_items = []
        if self.main_window_ref and hasattr(self.main_window_ref, 'tables_data'):
            for t_name in self.main_window_ref.tables_data.keys():
                if t_name != current_table_being_edited:
                    self.ref_table_combo.addItem(t_name); added_items.append(t_name)
        if current_ref_table_name and current_ref_table_name in added_items:
            self.ref_table_combo.setCurrentText(current_ref_table_name)
        elif added_items: self.ref_table_combo.setCurrentIndex(0)
        self.ref_table_combo.blockSignals(False)
        self.update_ref_col_combo_internal(self.ref_table_combo.currentText(), self.ref_col_combo.currentText())

    def update_ref_col_combo_internal(self, table_name, current_ref_col_name=None):
        self.ref_col_combo.blockSignals(True); self.ref_col_combo.clear(); self.ref_col_combo.setEnabled(False)
        added_pk_cols = []
        if table_name and self.main_window_ref and hasattr(self.main_window_ref, 'tables_data'):
            target_table_obj = self.main_window_ref.tables_data.get(table_name)
            if target_table_obj:
                pk_columns = target_table_obj.get_pk_column_names()
                if pk_columns:
                    self.ref_col_combo.addItems(pk_columns); added_pk_cols.extend(pk_columns)
                    self.ref_col_combo.setEnabled(True)
        if current_ref_col_name and current_ref_col_name in added_pk_cols:
            self.ref_col_combo.setCurrentText(current_ref_col_name)
        elif added_pk_cols: self.ref_col_combo.setCurrentIndex(0)
        self.ref_col_combo.blockSignals(False)

    def get_data(self):
        name = self.name_edit.text().strip()
        data_type = self.type_combo.currentText()
        is_pk = self.pk_checkbox.isChecked()
        is_fk = self.fk_checkbox.isChecked()
        ref_table = self.ref_table_combo.currentText() if is_fk else None
        ref_col = self.ref_col_combo.currentText() if is_fk and ref_table and self.ref_col_combo.count() > 0 else None
        fk_rel_type = self.fk_rel_type_combo.currentText() if is_fk else "N:1"
        if is_fk and (not ref_table or not ref_col):
            is_fk = False; ref_table = None; ref_col = None; fk_rel_type = "N:1"
        if not name: return None
        return Column(name, data_type, is_pk, is_fk, ref_table, ref_col, fk_rel_type)

    def request_delete(self): self.delete_requested.emit(self.list_item_ref)

class TableDialog(QDialog):
    def __init__(self, parent_window, table_name="", columns_data=None, table_body_color=None, table_header_color=None):
        super().__init__(parent_window)
        self.main_window_ref = parent_window
        self.setWindowTitle("Table Details")
        self.newly_picked_custom_colors_for_table = set() # לאיסוף צבעים חדשים שנבחרו עבור טבלה זו
        self.setMinimumSize(750, 500)
        self.setStyleSheet(f"""
            QDialog {{ background-color: {constants.current_theme_settings.get('window_bg', QColor('#F0F0F0')).name()}; }}
            QLabel, QCheckBox, QLineEdit, QComboBox, QPushButton {{ color: {constants.current_theme_settings.get('dialog_text_color', QColor('#000000')).name()}; }}
            QLineEdit, QComboBox {{ background-color: {constants.current_theme_settings.get('dialog_input_bg', QColor(Qt.GlobalColor.white)).name()}; border: 1px solid {constants.current_theme_settings.get('button_border', QColor(Qt.GlobalColor.gray)).name()}; padding: 3px; }}
            QListWidget {{ background-color: {constants.current_theme_settings.get('view_bg', QColor(Qt.GlobalColor.white)).name()}; border: 1px solid {constants.current_theme_settings.get('toolbar_border', QColor(Qt.GlobalColor.lightGray)).name()}; }}
            QPushButton {{ background-color: {constants.current_theme_settings.get('button_bg', QColor(Qt.GlobalColor.white)).name()}; border: 1px solid {constants.current_theme_settings.get('button_border', QColor(Qt.GlobalColor.gray)).name()}; padding: 5px; }}
            QPushButton:hover {{ background-color: {constants.current_theme_settings.get('button_hover_bg', QColor(Qt.GlobalColor.lightGray)).name()}; }}
            QPushButton:pressed {{ background-color: {constants.current_theme_settings.get('button_pressed_bg', QColor(Qt.GlobalColor.darkGray)).name()}; }}
        """)
        self.layout = QVBoxLayout(self)
        top_form_layout = QFormLayout()
        self.tableNameInput = QLineEdit(table_name)
        top_form_layout.addRow("Table Name:", self.tableNameInput)
        self.bodyColorButton = QPushButton("Body Color")
        self.bodyColorButton.clicked.connect(self.choose_body_color)
        self.currentBodyColor = table_body_color or QColor(constants.current_theme_settings.get("default_table_body_color", QColor(Qt.GlobalColor.white)))
        self.bodyColorButton.setStyleSheet(f"background-color: {self.currentBodyColor.name()}; color: {get_contrasting_text_color(self.currentBodyColor).name()}; padding: 5px;")
        self.headerColorButton = QPushButton("Header Color")
        self.headerColorButton.clicked.connect(self.choose_header_color)
        self.currentHeaderColor = table_header_color or QColor(constants.current_theme_settings.get("default_table_header_color", QColor(Qt.GlobalColor.lightGray)))
        self.headerColorButton.setStyleSheet(f"background-color: {self.currentHeaderColor.name()}; color: {get_contrasting_text_color(self.currentHeaderColor).name()}; padding: 5px;")
        color_button_layout = QHBoxLayout(); color_button_layout.addWidget(self.bodyColorButton); color_button_layout.addWidget(self.headerColorButton)
        top_form_layout.addRow(color_button_layout); self.layout.addLayout(top_form_layout)
        self.columnsLabel = QLabel("Columns (Drag to reorder):"); self.layout.addWidget(self.columnsLabel)
        self.columnsListWidget = QListWidget()
        self.columnsListWidget.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.columnsListWidget.setStyleSheet(f"QListWidget::item {{ border-bottom: 1px solid {constants.current_theme_settings.get('toolbar_border', QColor(Qt.GlobalColor.lightGray)).name()}; }}")
        self.layout.addWidget(self.columnsListWidget)
        if columns_data:
            for col_data in columns_data: self.add_column_entry(col_data)
        else: self.add_column_entry()
        self.btnAddColumn = QPushButton("Add Column")
        self.btnAddColumn.setIcon(get_standard_icon(QApplication.style().StandardPixmap.SP_FileDialogNewFolder, "+"))
        self.btnAddColumn.clicked.connect(lambda: self.add_column_entry())
        self.layout.addWidget(self.btnAddColumn)
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel) # Defined self.buttonBox
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setText("OK")
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancel")
        self.buttonBox.accepted.connect(self.validate_and_accept); self.buttonBox.rejected.connect(self.reject)
        self.layout.addWidget(self.buttonBox)

    def choose_body_color(self):
        picker_dialog = AdvancedColorPickerDialog(self.currentBodyColor, self.main_window_ref, self)
        if picker_dialog.exec():
            chosen_color, was_new_custom = picker_dialog.get_result()
            if chosen_color.isValid():
                self.currentBodyColor = chosen_color
                self.bodyColorButton.setStyleSheet(f"background-color: {self.currentBodyColor.name()}; color: {get_contrasting_text_color(self.currentBodyColor).name()}; padding: 5px;")
                if was_new_custom:
                    self.newly_picked_custom_colors_for_table.add(chosen_color.name())

    def choose_header_color(self):
        picker_dialog = AdvancedColorPickerDialog(self.currentHeaderColor, self.main_window_ref, self)
        if picker_dialog.exec():
            chosen_color, was_new_custom = picker_dialog.get_result()
            if chosen_color.isValid():
                self.currentHeaderColor = chosen_color
                self.headerColorButton.setStyleSheet(f"background-color: {self.currentHeaderColor.name()}; color: {get_contrasting_text_color(self.currentHeaderColor).name()}; padding: 5px;")
                if was_new_custom:
                    self.newly_picked_custom_colors_for_table.add(chosen_color.name())

    def add_column_entry(self, column_data=None):
        list_item = QListWidgetItem(self.columnsListWidget)
        entry_widget_args = {"main_window_ref": self.main_window_ref, "table_name_input_ref": self.tableNameInput, "list_item_ref": list_item, "parent_dialog": self}
        if column_data:
            entry_widget_args.update({"name": column_data.name, "data_type": column_data.data_type, "is_pk": column_data.is_pk, "is_fk": column_data.is_fk, "ref_table_name": column_data.references_table, "ref_col_name": column_data.references_column, "fk_rel_type": column_data.fk_relationship_type})
        entry_widget = ColumnEntryWidget(**entry_widget_args)
        entry_widget.delete_requested.connect(self.remove_column_entry)
        list_item.setSizeHint(entry_widget.sizeHint()); self.columnsListWidget.addItem(list_item); self.columnsListWidget.setItemWidget(list_item, entry_widget)

    def remove_column_entry(self, list_item_to_remove):
        row = self.columnsListWidget.row(list_item_to_remove)
        if row != -1: self.columnsListWidget.takeItem(row)

    def validate_and_accept(self):
        """Validates table data before accepting the dialog."""
        column_names = []
        for i in range(self.columnsListWidget.count()):
            list_item = self.columnsListWidget.item(i)
            entry_widget = self.columnsListWidget.itemWidget(list_item)
            if entry_widget:
                # Directly access the name_edit widget's text for validation
                col_name = entry_widget.name_edit.text().strip()
                if col_name: # Only consider non-empty names for duplication check
                    column_names.append(col_name)

        duplicate_names = {name for name in column_names if column_names.count(name) > 1}

        if duplicate_names:
            QMessageBox.warning(self, "Duplicate Column Names",
                                f"The following column names are duplicated: {', '.join(duplicate_names)}.\nPlease ensure all column names are unique.")
            return # Do not accept the dialog

        self.accept() # Proceed with accepting the dialog

    def get_table_data(self):
        table_name = self.tableNameInput.text().strip()
        columns = []
        for i in range(self.columnsListWidget.count()):
            list_item = self.columnsListWidget.item(i)
            entry_widget = self.columnsListWidget.itemWidget(list_item)
            if entry_widget:
                col_data = entry_widget.get_data()
                if col_data: columns.append(col_data)
        body_color = self.currentBodyColor.name(); header_color = self.currentHeaderColor.name()
        return table_name, columns, body_color, header_color, self.newly_picked_custom_colors_for_table

# --- Canvas Settings Dialog ---
class CanvasSettingsDialog(QDialog):
    def __init__(self, current_width, current_height, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Canvas Settings")
        self.setMinimumWidth(300)
        self.setStyleSheet(f"QDialog {{ background-color: {constants.current_theme_settings.get('window_bg', QColor('#F0F0F0')).name()}; }} "
                           f"QLabel, QSpinBox, QPushButton {{ color: {constants.current_theme_settings.get('dialog_text_color', QColor('#000000')).name()}; }} "
                           f"QSpinBox {{ background-color: {constants.current_theme_settings.get('dialog_input_bg', QColor(Qt.GlobalColor.white)).name()}; border: 1px solid {constants.current_theme_settings.get('button_border', QColor(Qt.GlobalColor.gray)).name()}; }}")

        layout = QFormLayout(self)
        self.width_spinbox = QSpinBox()
        self.width_spinbox.setRange(500, 20000) 
        self.width_spinbox.setValue(current_width)
        self.width_spinbox.setSuffix(" px")

        self.height_spinbox = QSpinBox()
        self.height_spinbox.setRange(500, 20000) 
        self.height_spinbox.setValue(current_height)
        self.height_spinbox.setSuffix(" px")

        layout.addRow("Canvas Width:", self.width_spinbox)
        layout.addRow("Canvas Height:", self.height_spinbox)

        self.buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel) # Corrected variable name
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setText("OK")
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancel")
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        layout.addWidget(self.buttonBox) # Corrected variable name

    def get_dimensions(self):
        return self.width_spinbox.value(), self.height_spinbox.value()

# --- Data Type Settings Dialog ---
class DataTypeSettingsDialog(QDialog):
    def __init__(self, current_types, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Manage Column Data Types")
        self.setMinimumSize(400, 300)
        self.setStyleSheet(f"QDialog {{ background-color: {constants.current_theme_settings.get('window_bg', QColor('#F0F0F0')).name()}; }} "
                           f"QLabel, QLineEdit, QListWidget, QPushButton {{ color: {constants.current_theme_settings.get('dialog_text_color', QColor('#000000')).name()}; }} "
                           f"QLineEdit, QListWidget {{ background-color: {constants.current_theme_settings.get('dialog_input_bg', QColor(Qt.GlobalColor.white)).name()}; border: 1px solid {constants.current_theme_settings.get('button_border', QColor(Qt.GlobalColor.gray)).name()}; }}")

        self.layout = QVBoxLayout(self)

        self.list_widget = QListWidget()
        self.list_widget.addItems(current_types)
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.layout.addWidget(self.list_widget)

        button_layout = QHBoxLayout()
        self.add_button = QPushButton("Add Type")
        self.add_button.clicked.connect(self.add_type)
        self.remove_button = QPushButton("Remove Selected")
        self.remove_button.clicked.connect(self.remove_type)

        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.remove_button)
        self.layout.addLayout(button_layout)

        self.buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel) # Corrected variable name
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setText("OK")
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancel")
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.layout.addWidget(self.buttonBox) # Corrected variable name

    def add_type(self):
        text, ok = QInputDialog.getText(self, "Add Data Type", "Enter new data type:")
        if ok and text.strip():
            new_type = text.strip().upper() 
            items = [self.list_widget.item(i).text() for i in range(self.list_widget.count())]
            if new_type not in items:
                self.list_widget.addItem(new_type)
            else:
                QMessageBox.warning(self, "Duplicate", f"Data type '{new_type}' already exists.")

    def remove_type(self):
        selected_items = self.list_widget.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "Remove", "Please select a data type to remove.")
            return
        for item in selected_items:
            self.list_widget.takeItem(self.list_widget.row(item))

    def get_data_types(self):
        types = []
        for i in range(self.list_widget.count()):
            types.append(self.list_widget.item(i).text())
        if not types: 
            QMessageBox.warning(self, "Data Types Empty", "Data types list cannot be empty. Restoring defaults (TEXT, INTEGER).")
            return ["TEXT", "INTEGER"] 
        return types
