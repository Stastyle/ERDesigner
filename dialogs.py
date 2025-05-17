# dialogs.py
# This file contains QDialog subclasses for user interactions.

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QLabel, QScrollArea, QWidget,
    QPushButton, QDialogButtonBox, QCheckBox, QComboBox, QHBoxLayout, QColorDialog
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFontMetrics, QColor, QIcon, QPixmap, QPainter

# Assuming constants.py and utils.py are in the same directory or accessible via PYTHONPATH
from constants import current_theme_settings # For default colors and text color
from utils import get_standard_icon, get_contrasting_text_color


class DefaultColorsDialog(QDialog):
    def __init__(self, parent_window_ref, parent=None):
        super().__init__(parent)
        self.main_window_ref = parent_window_ref
        self.setWindowTitle("Set Default Table Colors")
        self.setMinimumWidth(400)
        self.setStyleSheet(f"QDialog {{ background-color: {current_theme_settings['window_bg'].name()}; }} "
                           f"QLabel, QPushButton {{ color: {current_theme_settings['dialog_text_color'].name()}; }}")


        layout = QFormLayout(self)

        # Initialize with current user defaults or theme defaults if user defaults are not set
        self.current_body_color = self.main_window_ref.user_default_table_body_color or \
                                  QColor(current_theme_settings['default_table_body_color'])
        self.current_header_color = self.main_window_ref.user_default_table_header_color or \
                                    QColor(current_theme_settings['default_table_header_color'])

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
        
        buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttonBox.button(QDialogButtonBox.StandardButton.Ok).setText("OK")
        buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancel")
        buttonBox.accepted.connect(self.accept_changes)
        buttonBox.rejected.connect(self.reject)
        layout.addWidget(buttonBox)

    def pick_body_color(self):
        color = QColorDialog.getColor(self.current_body_color, self, "Choose Default Body Color")
        if color.isValid():
            self.current_body_color = color
            self.body_color_button.setText(f"Body: {color.name()}")
            self.body_color_button.setStyleSheet(
                f"background-color: {color.name()}; color: {get_contrasting_text_color(color).name()}; padding: 5px;"
            )

    def pick_header_color(self):
        color = QColorDialog.getColor(self.current_header_color, self, "Choose Default Header Color")
        if color.isValid():
            self.current_header_color = color
            self.header_color_button.setText(f"Header: {color.name()}")
            self.header_color_button.setStyleSheet(
                f"background-color: {color.name()}; color: {get_contrasting_text_color(color).name()}; padding: 5px;"
            )
    
    def accept_changes(self):
        self.main_window_ref.user_default_table_body_color = self.current_body_color
        self.main_window_ref.user_default_table_header_color = self.current_header_color
        self.main_window_ref.update_theme_settings() 
        self.main_window_ref.set_theme(self.main_window_ref.current_theme) 
        self.accept()

    def get_colors(self): # This method might not be strictly needed if changes are applied directly
        return self.current_body_color, self.current_header_color


class RelationshipDialog(QDialog):
    def __init__(self, relationship_data, parent_window_ref, parent=None): 
        super().__init__(parent)
        self.relationship_data = relationship_data
        self.main_window_ref = parent_window_ref
        self.setWindowTitle("Relationship Properties")
        self.setStyleSheet(f"QDialog {{ background-color: {current_theme_settings['window_bg'].name()}; }} QLabel, QComboBox {{ color: {current_theme_settings['dialog_text_color'].name()}; }}")


        layout = QFormLayout(self)

        self.from_label = QLabel(f"From (FK Side): {relationship_data.table1_name}.{relationship_data.fk_column_name}")
        self.to_label = QLabel(f"To (PK Side): {relationship_data.table2_name}.{relationship_data.pk_column_name}")
        
        self.type_combo = QComboBox()
        self.type_combo.addItems(["N:1", "1:1"]) 
        self.type_combo.setCurrentText(relationship_data.relationship_type or "N:1")

        layout.addRow(self.from_label)
        layout.addRow(self.to_label)
        layout.addRow("Relationship Type (FK table to PK table):", self.type_combo)

        self.buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setText("OK")
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancel")
        self.buttonBox.accepted.connect(self.accept_changes)
        self.buttonBox.rejected.connect(self.reject)
        layout.addWidget(self.buttonBox)

    def accept_changes(self):
        new_type = self.type_combo.currentText()
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
        self.accept()


class TableDialog(QDialog): 
    def __init__(self, parent_window, table_name="", columns_data=None, table_body_color=None, table_header_color=None): 
        super().__init__(parent_window)
        self.main_window_ref = parent_window 
        self.setWindowTitle("Table Details")
        self.setStyleSheet(f"QDialog {{ background-color: {current_theme_settings['window_bg'].name()}; }} "
                           f"QLabel, QCheckBox, QLineEdit, QComboBox, QPushButton {{ color: {current_theme_settings['dialog_text_color'].name()}; }}")

        
        self.layout = QVBoxLayout(self)

        # Table Name and Color Pickers
        top_form_layout = QFormLayout()
        self.tableNameInput = QLineEdit(table_name)
        top_form_layout.addRow("Table Name:", self.tableNameInput)

        self.bodyColorButton = QPushButton("Body Color")
        self.bodyColorButton.clicked.connect(self.choose_body_color)
        self.currentBodyColor = table_body_color or QColor(current_theme_settings["default_table_body_color"])
        self.bodyColorButton.setStyleSheet(f"background-color: {self.currentBodyColor.name()}; color: {get_contrasting_text_color(self.currentBodyColor).name()}; padding: 5px;")
        
        self.headerColorButton = QPushButton("Header Color")
        self.headerColorButton.clicked.connect(self.choose_header_color)
        self.currentHeaderColor = table_header_color or QColor(current_theme_settings["default_table_header_color"])
        self.headerColorButton.setStyleSheet(f"background-color: {self.currentHeaderColor.name()}; color: {get_contrasting_text_color(self.currentHeaderColor).name()}; padding: 5px;")

        color_button_layout = QHBoxLayout()
        color_button_layout.addWidget(self.bodyColorButton)
        color_button_layout.addWidget(self.headerColorButton)
        top_form_layout.addRow(color_button_layout)
        
        self.layout.addLayout(top_form_layout)


        self.columnsLabel = QLabel("Columns:")
        self.layout.addWidget(self.columnsLabel)

        self.scrollWidget = QWidget() 
        self.columnsLayout = QVBoxLayout(self.scrollWidget) 
        self.column_widgets = [] 

        if columns_data:
            for col_data in columns_data:
                self.add_column_input_row(col_data.name, col_data.data_type, col_data.is_pk, col_data.is_fk, 
                                          col_data.references_table, col_data.references_column, col_data.fk_relationship_type, add_to_layout=True) 
        else:
            self.add_column_input_row(add_to_layout=True) 
        
        self.columnsLayout.addStretch(1) 

        self.scrollArea = QScrollArea()
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setWidget(self.scrollWidget) 
        self.layout.addWidget(self.scrollArea)
        
        self.btnAddColumn = QPushButton("Add Column")
        self.btnAddColumn.setIcon(get_standard_icon(QApplication.style().StandardPixmap.SP_FileDialogNewFolder, "+"))
        self.btnAddColumn.clicked.connect(self.on_add_column_button_clicked)
        self.layout.addWidget(self.btnAddColumn)

        self.buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setText("OK")
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancel")
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.layout.addWidget(self.buttonBox)
        
        self.setMinimumSize(750, 450) 

    def choose_body_color(self):
        color = QColorDialog.getColor(self.currentBodyColor, self, "Choose Table Body Color")
        if color.isValid():
            self.currentBodyColor = color
            self.bodyColorButton.setStyleSheet(f"background-color: {self.currentBodyColor.name()}; color: {get_contrasting_text_color(self.currentBodyColor).name()}; padding: 5px;")

    def choose_header_color(self):
        color = QColorDialog.getColor(self.currentHeaderColor, self, "Choose Table Header Color")
        if color.isValid():
            self.currentHeaderColor = color
            self.headerColorButton.setStyleSheet(f"background-color: {self.currentHeaderColor.name()}; color: {get_contrasting_text_color(self.currentHeaderColor).name()}; padding: 5px;")


    def on_add_column_button_clicked(self):
        # Remove the stretch item before adding a new row
        stretch_item = self.columnsLayout.takeAt(self.columnsLayout.count() - 1)
        
        self.add_column_input_row(add_to_layout=True) 
        
        # Re-add the stretch item at the very end
        if stretch_item: 
            self.columnsLayout.addStretch(1) 
            if stretch_item.layout() is None and stretch_item.widget() is None and stretch_item.spacerItem(): 
                 pass 
            elif stretch_item.layout() is not None: 
                 stretch_item.layout().deleteLater() 
            elif stretch_item.widget() is not None: 
                 stretch_item.widget().deleteLater() 
        else: 
            self.columnsLayout.addStretch(1)


    def add_column_input_row(self, name="", data_type="TEXT", is_pk=False, is_fk=False, 
                             ref_table_name="", ref_col_name="", fk_rel_type="N:1", add_to_layout=True): 
        
        row_container_widget = QWidget()
        main_row_v_layout = QVBoxLayout(row_container_widget)
        main_row_v_layout.setContentsMargins(0,0,0,0)
        main_row_v_layout.setSpacing(2) 

        top_row_widget = QWidget()
        top_row_h_layout = QHBoxLayout(top_row_widget)
        top_row_h_layout.setContentsMargins(0,0,0,0)

        font_metrics = QFontMetrics(self.font()) 
        button_height = font_metrics.height() + 4 
        button_width_char = font_metrics.horizontalAdvance("X") + 10 

        name_edit = QLineEdit(name)
        name_edit.setPlaceholderText("Column Name")
        type_combo = QComboBox()
        type_combo.addItems(["TEXT", "INTEGER", "REAL", "BLOB", "VARCHAR(255)", "BOOLEAN", "DATE", "DATETIME", "SERIAL", "UUID", "NUMERIC", "TIMESTAMP"])
        type_combo.setCurrentText(data_type)
        
        pk_checkbox = QCheckBox("PK")
        pk_checkbox.setChecked(is_pk)
        
        fk_checkbox = QCheckBox("FK") 
        fk_checkbox.setChecked(is_fk)

        btn_remove_col = QPushButton("X")
        btn_remove_col.setFixedSize(button_width_char, button_height) 
        
        top_row_h_layout.addWidget(name_edit, 2) 
        top_row_h_layout.addWidget(type_combo, 1)
        top_row_h_layout.addWidget(pk_checkbox)
        top_row_h_layout.addWidget(fk_checkbox)
        top_row_h_layout.addStretch(1) 
        top_row_h_layout.addWidget(btn_remove_col)
        main_row_v_layout.addWidget(top_row_widget)

        fk_details_widget = QWidget()
        fk_details_layout = QHBoxLayout(fk_details_widget) 
        fk_details_layout.setContentsMargins(20, 2, 5, 2) 
        fk_details_layout.setSpacing(5)

        ref_table_combo = QComboBox()
        ref_table_combo.setPlaceholderText("Referenced Table")
        current_table_name_being_edited = self.tableNameInput.text()
        for t_name in self.main_window_ref.tables_data.keys():
            if t_name != current_table_name_being_edited:
                 ref_table_combo.addItem(t_name)
        if ref_table_name:
            ref_table_combo.setCurrentText(ref_table_name)
        elif ref_table_combo.count() > 0 : 
             ref_table_combo.setCurrentIndex(0)

        
        ref_col_combo = QComboBox()
        ref_col_combo.setPlaceholderText("Referenced PK Column")

        fk_rel_type_label = QLabel("Rel. Type:") 
        fk_rel_type_combo = QComboBox()
        fk_rel_type_combo.addItems(["N:1", "1:1"]) 
        fk_rel_type_combo.setCurrentText(fk_rel_type)

        fk_details_layout.addWidget(QLabel("-> Refers to:"),0, Qt.AlignmentFlag.AlignLeft)
        fk_details_layout.addWidget(ref_table_combo,1)
        fk_details_layout.addWidget(QLabel("."),0, Qt.AlignmentFlag.AlignCenter)
        fk_details_layout.addWidget(ref_col_combo,1)
        fk_details_layout.addWidget(fk_rel_type_label,0, Qt.AlignmentFlag.AlignRight) 
        fk_details_layout.addWidget(fk_rel_type_combo,1)
        
        fk_details_widget.setVisible(is_fk) 
        main_row_v_layout.addWidget(fk_details_widget)
        
        ref_table_combo.currentTextChanged.connect(
            lambda new_table_text, rcc=ref_col_combo, rtc=ref_table_combo: self.update_ref_col_combo(new_table_text, rcc, rtc)
        )
        
        self.update_ref_col_combo(ref_table_combo.currentText(), ref_col_combo, ref_table_combo)
        if ref_col_name: 
            ref_col_combo.setCurrentText(ref_col_name)
        
        fk_checkbox.toggled.connect(fk_details_widget.setVisible)

        row_widgets_dict = { 
            "container_widget": row_container_widget, 
            "name": name_edit, "type": type_combo, 
            "pk": pk_checkbox, "fk": fk_checkbox,
            "ref_table_combo": ref_table_combo, "ref_col_combo": ref_col_combo,
            "fk_rel_type_combo": fk_rel_type_combo, 
            "remove_button": btn_remove_col,
            "fk_details_widget": fk_details_widget 
        }
        
        btn_remove_col.clicked.connect(lambda checked=False, rw=row_widgets_dict: self.remove_column_input_row(rw))
        
        if add_to_layout: 
            self.columnsLayout.insertWidget(self.columnsLayout.count() -1, row_container_widget)
        
        if not any(cw["container_widget"] == row_container_widget for cw in self.column_widgets): 
            self.column_widgets.append(row_widgets_dict)


    def update_ref_col_combo(self, table_name, col_combo_to_update, table_combo_source):
        current_ref_col = col_combo_to_update.currentText() 
        col_combo_to_update.clear()
        
        if table_name and table_name in self.main_window_ref.tables_data:
            target_table_obj = self.main_window_ref.tables_data[table_name]
            pk_columns = target_table_obj.get_pk_column_names()
            if pk_columns:
                col_combo_to_update.addItems(pk_columns)
                if current_ref_col in pk_columns:
                    col_combo_to_update.setCurrentText(current_ref_col)
                elif pk_columns: 
                    col_combo_to_update.setCurrentIndex(0) 
                col_combo_to_update.setEnabled(True)
            else:
                col_combo_to_update.setEnabled(False) 
        else: 
            col_combo_to_update.setEnabled(False)


    def remove_column_input_row(self, row_widgets_to_remove):
        if row_widgets_to_remove in self.column_widgets:
            container = row_widgets_to_remove["container_widget"]
            layout = container.layout()
            if layout:
                while layout.count():
                    item = layout.takeAt(0)
                    widget = item.widget()
                    if widget:
                        widget.deleteLater()
            container.deleteLater() 
            self.column_widgets.remove(row_widgets_to_remove)
            self.scrollWidget.adjustSize() 


    def get_table_data(self):
        table_name = self.tableNameInput.text().strip()
        columns = []
        ordered_columns_data = []
        for i in range(self.columnsLayout.count() -1): 
            item_widget = self.columnsLayout.itemAt(i).widget()
            for cw_dict in self.column_widgets:
                if cw_dict["container_widget"] == item_widget:
                    ordered_columns_data.append(cw_dict)
                    break
        
        for col_row_widgets in ordered_columns_data: 
            name = col_row_widgets["name"].text().strip()
            data_type = col_row_widgets["type"].currentText()
            is_pk = col_row_widgets["pk"].isChecked()
            is_fk = col_row_widgets["fk"].isChecked() 
            ref_table = col_row_widgets["ref_table_combo"].currentText() if is_fk else None
            ref_col = col_row_widgets["ref_col_combo"].currentText() if is_fk and ref_table and col_row_widgets["ref_col_combo"].count() > 0 and col_row_widgets["ref_col_combo"].currentText() != "No PK defined" else None
            fk_rel_type = col_row_widgets["fk_rel_type_combo"].currentText() if is_fk else "N:1" 

            if is_fk and (not ref_table or not ref_col): 
                is_fk = False 
                ref_table = None 
                ref_col = None 
                fk_rel_type = "N:1" 
            if name: 
                columns.append(Column(name, data_type, is_pk, is_fk, ref_table, ref_col, fk_rel_type))
        
        body_color = self.currentBodyColor.name()
        header_color = self.currentHeaderColor.name()
        return table_name, columns, body_color, header_color
