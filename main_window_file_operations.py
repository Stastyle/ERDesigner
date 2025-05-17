# main_window_file_operations.py
# Handles file operations like import/export CSV.

import csv
import os
import sys
from PyQt6.QtWidgets import QFileDialog, QMessageBox
from PyQt6.QtCore import QPointF, QRectF, Qt # Added QRectF and Qt
import constants 
from data_models import Column 

def handle_import_csv_button_impl(window):
    """Handles importing ERD data from a CSV file."""
    path, _ = QFileDialog.getOpenFileName(window, "Import ERD File", "", "CSV Files (*.csv);;All Files (*)")
    if not path:
        return

    window.new_diagram() 

    parsed_tables = {}  
    parsed_relationships_from_csv = [] 
    imported_canvas_width, imported_canvas_height = None, None

    try:
        with open(path, 'r', newline='', encoding='utf-8-sig') as csvfile: 
            reader = csv.reader(csvfile)
            current_section = None 
            
            for row_num, row in enumerate(reader):
                if not row or not row[0].strip(): 
                    continue
                
                first_cell_stripped = row[0].strip()

                if first_cell_stripped == constants.CSV_TABLE_POSITION_MARKER:
                    current_section = "TABLE_DEFINITIONS"
                    if len(row) > 1 and row[1].strip().lower() == "table name": continue
                elif first_cell_stripped == constants.CSV_RELATIONSHIP_DEF_MARKER:
                    current_section = "RELATIONSHIPS"
                    if len(row) > 1 and row[1].strip().lower() == "from table (fk source)": continue
                elif first_cell_stripped == constants.CSV_CANVAS_SIZE_MARKER:
                    current_section = "CANVAS_SIZE"
                    if len(row) > 1 and row[1].strip().lower() == "width": continue
                elif current_section is None and len(row) > 1 and row[0].strip().lower() == "table name" and row[1].strip().lower() == "column name":
                    current_section = "COLUMNS"
                    continue 
                elif current_section is None: 
                    current_section = "COLUMNS"

                if current_section == "COLUMNS":
                    if len(row) < 7: 
                        print(f"Skipping malformed column row (too few cells): {row}")
                        continue
                    table_name_csv, col_name_csv = row[0].strip(), row[1].strip()
                    if not table_name_csv : continue 

                    if table_name_csv not in parsed_tables:
                        parsed_tables[table_name_csv] = {"columns": [], "pos": None, "width": constants.DEFAULT_TABLE_WIDTH, "body_color": None, "header_color": None}
                    
                    if col_name_csv == "N/A (No Columns)" or not col_name_csv: 
                        continue

                    data_type = row[2].strip()
                    is_pk = row[3].strip().lower() == "yes"
                    is_fk_val = row[4].strip().lower() == "yes"
                    ref_table = row[5].strip() if is_fk_val and len(row) > 5 and row[5].strip() else None
                    ref_col = row[6].strip() if is_fk_val and len(row) > 6 and row[6].strip() else None
                    fk_rel_type = row[7].strip() if is_fk_val and len(row) > 7 and row[7].strip() else "N:1" 

                    column = Column(name=col_name_csv, data_type=data_type, is_pk=is_pk, is_fk=is_fk_val,
                                    references_table=ref_table, references_column=ref_col, fk_relationship_type=fk_rel_type)
                    parsed_tables[table_name_csv]["columns"].append(column)

                elif current_section == "TABLE_DEFINITIONS":
                    if len(row) < 5: 
                        print(f"Skipping malformed table definition row: {row}")
                        continue
                    table_name_def = row[1].strip()
                    try:
                        pos_x, pos_y = float(row[2].strip()), float(row[3].strip())
                        width_val = float(row[4].strip()) if row[4].strip() else constants.DEFAULT_TABLE_WIDTH
                        body_hex = (row[5].strip() or None) if len(row) > 5 else None
                        header_hex = (row[6].strip() or None) if len(row) > 6 else None

                        if table_name_def not in parsed_tables: 
                            parsed_tables[table_name_def] = {"columns": [], "width": constants.DEFAULT_TABLE_WIDTH} 
                        
                        parsed_tables[table_name_def].update({
                            "pos": QPointF(pos_x, pos_y), 
                            "width": width_val,
                            "body_color": body_hex,
                            "header_color": header_hex
                        })
                    except ValueError as ve:
                        print(f"Warning: Could not parse number in table definition for '{table_name_def}': {row} - {ve}")
                
                elif current_section == "RELATIONSHIPS":
                    if len(row) < 6: continue
                    rel_from_table, rel_from_col = row[1].strip(), row[2].strip()
                    rel_to_table, rel_to_col = row[3].strip(), row[4].strip()
                    rel_type = row[5].strip() if len(row) > 5 and row[5].strip() else "N:1" 
                    manual_bend_x_str = row[6].strip() if len(row) > 6 and row[6].strip() else None
                    manual_bend_x = float(manual_bend_x_str) if manual_bend_x_str is not None else None

                    if all([rel_from_table, rel_from_col, rel_to_table, rel_to_col]):
                        parsed_relationships_from_csv.append({
                            "from_table": rel_from_table, "from_col": rel_from_col,
                            "to_table": rel_to_table, "to_col": rel_to_col,
                            "type": rel_type, "bend_x": manual_bend_x
                        })
                
                elif current_section == "CANVAS_SIZE":
                    data_offset = 1 
                    if len(row) >= data_offset + 2: 
                        try:
                            imported_canvas_width = int(row[data_offset].strip())
                            imported_canvas_height = int(row[data_offset+1].strip())
                        except ValueError:
                            print(f"Warning: Could not parse canvas size from CSV row: {row}")
            
            if imported_canvas_width and imported_canvas_height:
                constants.current_canvas_dimensions["width"] = imported_canvas_width
                constants.current_canvas_dimensions["height"] = imported_canvas_height
                if window.scene: 
                    window.scene.setSceneRect(0,0, imported_canvas_width, imported_canvas_height)
                print(f"Applied canvas size from CSV: {imported_canvas_width}x{imported_canvas_height}")

            window.undo_stack.beginMacro("Import CSV")
            imported_tables_count = 0
            
            all_imported_table_graphics = [] # List to store graphic items of imported tables

            for table_name_to_import, data in parsed_tables.items():
                table_obj = window.handle_add_table_button(
                    table_name_prop=table_name_to_import,
                    columns_prop=data["columns"], 
                    pos=data.get("pos"), 
                    width_prop=data.get("width"),
                    body_color_hex=data.get("body_color"),
                    header_color_hex=data.get("header_color")
                )
                if table_obj: 
                    imported_tables_count +=1
                    if table_obj.graphic_item: # Store the graphic item
                        all_imported_table_graphics.append(table_obj.graphic_item)
            
            for table_name, fk_table_obj in window.tables_data.items(): 
                for fk_col_obj in fk_table_obj.columns:
                    if fk_col_obj.is_fk and fk_col_obj.references_table and fk_col_obj.references_column:
                        pk_table_name = fk_col_obj.references_table
                        pk_col_name = fk_col_obj.references_column
                        pk_table_obj = window.tables_data.get(pk_table_name)
                        
                        if pk_table_obj:
                            pk_col_obj = pk_table_obj.get_column_by_name(pk_col_name)
                            if pk_col_obj and pk_col_obj.is_pk:
                                is_explicitly_defined = any(
                                    rel_def["from_table"] == fk_table_obj.name and
                                    rel_def["from_col"] == fk_col_obj.name and
                                    rel_def["to_table"] == pk_table_obj.name and
                                    rel_def["to_col"] == pk_col_obj.name
                                    for rel_def in parsed_relationships_from_csv
                                )
                                if not is_explicitly_defined:
                                    window.create_relationship(fk_table_obj, pk_table_obj, fk_col_obj.name, pk_col_obj.name, fk_col_obj.fk_relationship_type)
                            else:
                                print(f"Warning: Referenced PK column '{pk_col_name}' not found or not PK in table '{pk_table_name}' for FK '{fk_table_obj.name}.{fk_col_obj.name}'.")
                        else:
                             print(f"Warning: Referenced PK table '{pk_table_name}' not found for FK '{fk_table_obj.name}.{fk_col_obj.name}'.")

            for rel_info in parsed_relationships_from_csv:
                fk_table_obj = window.tables_data.get(rel_info["from_table"])
                pk_table_obj = window.tables_data.get(rel_info["to_table"])
                if fk_table_obj and pk_table_obj:
                    fk_col_obj = fk_table_obj.get_column_by_name(rel_info["from_col"])
                    pk_col_obj = pk_table_obj.get_column_by_name(rel_info["to_col"])
                    if fk_col_obj and pk_col_obj: 
                        if not pk_col_obj.is_pk:
                            print(f"Warning: Explicit relationship references non-PK column: {rel_info['to_table']}.{rel_info['to_col']}. Skipping.")
                            continue
                        window.create_relationship(
                            fk_table_obj, pk_table_obj, 
                            fk_col_obj.name, pk_col_obj.name, 
                            rel_info["type"], rel_info["bend_x"]
                        )
                    else:
                        print(f"Warning: Columns for explicit relationship not found: {rel_info}. Skipping.")
                else:
                    print(f"Warning: Tables for explicit relationship not found: {rel_info}. Skipping.")
            
            final_rels_count = len(window.relationships_data)
            window.undo_stack.endMacro()

            window.update_all_relationships_graphics() 
            window.populate_diagram_explorer()
            window.current_file_path = path 
            window.update_window_title()

            # --- Zoom to fit all imported tables ---
            if all_imported_table_graphics:
                overall_rect = QRectF()
                # Initialize with the bounding rect of the first item
                if all_imported_table_graphics[0].sceneBoundingRect().isValid():
                    overall_rect = all_imported_table_graphics[0].sceneBoundingRect()
                
                for item_graphic in all_imported_table_graphics[1:]:
                    item_rect = item_graphic.sceneBoundingRect()
                    if item_rect.isValid(): # Ensure the rect is valid before uniting
                        overall_rect = overall_rect.united(item_rect)
                
                if overall_rect.isValid() and not overall_rect.isEmpty():
                    # Add some padding to the rectangle
                    padding = 50 
                    overall_rect.adjust(-padding, -padding, padding, padding)
                    window.view.fitInView(overall_rect, Qt.AspectRatioMode.KeepAspectRatio)
            # --- End of Zoom logic ---

            QMessageBox.information(window, "Import Successful",
                                    f"{imported_tables_count} tables and {final_rels_count} relationships processed from {os.path.basename(path)}. "
                                    f"Check console for details.")

    except FileNotFoundError:
        QMessageBox.critical(window, "Import Error", f"File not found: {path}")
        if window.undo_stack.isActive(): window.undo_stack.endMacro() 
    except Exception as e:
        QMessageBox.critical(window, "Import Error", f"Could not import from CSV: {e}\nCheck console for details.")
        print(f"CSV Import Error: {e}", file=sys.stderr) 
        import traceback
        traceback.print_exc(file=sys.stderr)
        if window.undo_stack.isActive(): window.undo_stack.endMacro()


def export_to_csv_impl(window, file_path_to_save=None):
    """Exports the current ERD data to a CSV file."""
    if not window.tables_data and not window.relationships_data : 
        QMessageBox.information(window, "Export CSV", "No data to export.")
        return
    
    if not file_path_to_save: 
        print("Error: No file path provided for export.")
        return

    try:
        with open(file_path_to_save, 'w', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.writer(csvfile)

            writer.writerow(["Table Name", "Column Name", "Data Type", "Is Primary Key", "Is Foreign Key", "References Table", "References Column", "FK Relationship Type"])
            for _, table_obj in sorted(window.tables_data.items()): 
                if not table_obj.columns:
                    writer.writerow([table_obj.name, "N/A (No Columns)", "", "", "", "", "", ""])
                else:
                    for col in table_obj.columns:
                        writer.writerow([
                            table_obj.name,
                            col.name,
                            col.data_type,
                            "Yes" if col.is_pk else "No",
                            "Yes" if col.is_fk else "No",
                            col.references_table if col.is_fk else "",
                            col.references_column if col.is_fk else "",
                            col.fk_relationship_type if col.is_fk else ""
                        ])
            
            writer.writerow([]) 

            writer.writerow([constants.CSV_TABLE_POSITION_MARKER, "Table Name", "X", "Y", "Width", "Body Color HEX", "Header Color HEX"])
            for table_name, table_obj in sorted(window.tables_data.items()):
                writer.writerow([
                    constants.CSV_TABLE_POSITION_MARKER, 
                    table_name,
                    table_obj.x,
                    table_obj.y,
                    table_obj.width,
                    table_obj.body_color.name(), 
                    table_obj.header_color.name()
                ])
            
            writer.writerow([])

            writer.writerow([constants.CSV_CANVAS_SIZE_MARKER, "Width", "Height"]) 
            writer.writerow([constants.CSV_CANVAS_SIZE_MARKER, constants.current_canvas_dimensions["width"], constants.current_canvas_dimensions["height"]])
            
            if window.relationships_data:
                writer.writerow([])
                writer.writerow([constants.CSV_RELATIONSHIP_DEF_MARKER, "From Table (FK Source)", "FK Column", "To Table (PK Source)", "PK Column", "Relationship Type", "Manual Bend X Offset"])
                sorted_rels = sorted(window.relationships_data, key=lambda r: (r.table1_name, r.fk_column_name, r.table2_name, r.pk_column_name))
                for rel in sorted_rels:
                    writer.writerow([
                        constants.CSV_RELATIONSHIP_DEF_MARKER, 
                        rel.table1_name,
                        rel.fk_column_name,
                        rel.table2_name,
                        rel.pk_column_name,
                        rel.relationship_type,
                        rel.manual_bend_offset_x if rel.manual_bend_offset_x is not None else "" 
                    ])

            QMessageBox.information(window, "File Saved", f"Data saved successfully to: {file_path_to_save}")
    except Exception as e:
        QMessageBox.critical(window, "Save Error", f"Could not save file: {e}")
        print(f"Error exporting to CSV: {e}")
