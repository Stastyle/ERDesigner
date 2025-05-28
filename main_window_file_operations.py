# main_window_file_operations.py
# Handles file operations like import/export CSV.

import csv
import os
import sys
import math # Added for math.ceil
from PyQt6.QtWidgets import QFileDialog, QMessageBox
from PyQt6.QtCore import QPointF, QRectF, Qt
import constants
from data_models import Column
from commands import AddTableCommand
from sql_parser import parse_sql_schema # Added for SQL import

def handle_import_erd_button_impl(window):
    """Handles importing ERD data from an ERD file (CSV formatted)."""
    path, _ = QFileDialog.getOpenFileName(window, "Import ERD File", "", "ERD Files (*.erd);;All Files (*)")
    if not path:
        return

    if not window.prompt_to_save_if_dirty():
        return # User cancelled or save failed

    window.new_diagram() 

    parsed_tables_from_csv = {} 
    parsed_relationships_from_csv = [] 
    imported_canvas_width, imported_canvas_height = None, None
    imported_notes = ""

    try:
        with open(path, 'r', newline='', encoding='utf-8-sig') as csvfile: 
            reader = csv.reader(csvfile)
            current_section = None 
            
            header_columns_expected = ["table name", "column name"] 
            header_table_pos_expected = "table name" 
            header_rels_expected = "from table (fk source)" 
            header_canvas_expected = "width" 
            header_notes_expected = "notes_content_follows" # Simple marker for notes
            

            for row_num, row in enumerate(reader):
                if not row or not row[0].strip(): 
                    continue
                
                first_cell_stripped = row[0].strip()

                if first_cell_stripped == constants.CSV_TABLE_POSITION_MARKER:
                    current_section = "TABLE_DEFINITIONS"
                    if len(row) > 1 and row[1].strip().lower() == header_table_pos_expected: continue
                elif first_cell_stripped == constants.CSV_RELATIONSHIP_DEF_MARKER:
                    current_section = "RELATIONSHIPS"
                    # Check for new header with VerticalSegmentX
                    if len(row) > 1 and row[1].strip().lower() == header_rels_expected: continue
                elif first_cell_stripped == constants.CSV_CANVAS_SIZE_MARKER:
                    current_section = "CANVAS_SIZE"
                    if len(row) > 1 and row[1].strip().lower() == header_canvas_expected: continue
                elif first_cell_stripped == constants.CSV_NOTES_MARKER:
                    current_section = "NOTES"
                    # Notes content will be on subsequent lines, no specific header row for content itself
                    if len(row) > 1 and row[1].strip().lower() == header_notes_expected: continue
                elif current_section is None and len(row) > 1 and \
                     row[0].strip().lower() == header_columns_expected[0] and \
                     row[1].strip().lower() == header_columns_expected[1]:
                    current_section = "COLUMNS" 
                    continue 
                elif current_section is None: 
                    current_section = "COLUMNS"


                if current_section == "COLUMNS": 
                    if len(row) < 2 : continue 
                    table_name_csv, col_name_csv = row[0].strip(), row[1].strip()
                    if not table_name_csv : continue 

                    if table_name_csv not in parsed_tables_from_csv:
                        parsed_tables_from_csv[table_name_csv] = {"columns": [], "pos": None, "width": constants.DEFAULT_TABLE_WIDTH, "body_color": None, "header_color": None}
                    
                    if col_name_csv == "N/A (No Columns)" or not col_name_csv: 
                        continue

                    data_type = row[2].strip() if len(row) > 2 else "TEXT"
                    is_pk = row[3].strip().lower() == "yes" if len(row) > 3 else False
                    is_fk_val = row[4].strip().lower() == "yes" if len(row) > 4 else False
                    ref_table = row[5].strip() if is_fk_val and len(row) > 5 and row[5].strip() else None
                    ref_col = row[6].strip() if is_fk_val and len(row) > 6 and row[6].strip() else None
                    fk_rel_type = row[7].strip() if is_fk_val and len(row) > 7 and row[7].strip() else "N:1"

                    column = Column(name=col_name_csv, data_type=data_type, is_pk=is_pk, is_fk=is_fk_val,
                                    references_table=ref_table, references_column=ref_col, fk_relationship_type=fk_rel_type)
                    parsed_tables_from_csv[table_name_csv]["columns"].append(column)

                elif current_section == "TABLE_DEFINITIONS": 
                    if len(row) < 5: continue
                    table_name_def = row[1].strip()
                    try:
                        pos_x, pos_y = float(row[2].strip()), float(row[3].strip())
                        width_val = float(row[4].strip()) if row[4].strip() else constants.DEFAULT_TABLE_WIDTH
                        body_hex = (row[5].strip() or None) if len(row) > 5 else None
                        header_hex = (row[6].strip() or None) if len(row) > 6 else None

                        if table_name_def not in parsed_tables_from_csv: 
                            parsed_tables_from_csv[table_name_def] = {"columns": [], "width": constants.DEFAULT_TABLE_WIDTH} 
                        
                        parsed_tables_from_csv[table_name_def].update({
                            "pos": QPointF(pos_x, pos_y),
                            "width": width_val,
                            "body_color": body_hex,
                            "header_color": header_hex
                        })
                    except ValueError as ve:
                        print(f"Warning: Could not parse number in table definition for '{table_name_def}': {row} - {ve}")
                

                elif current_section == "RELATIONSHIPS": 
                    # Marker, FromTable, FKCol, ToTable, PKCol, RelType, VerticalSegmentX (optional)
                    if len(row) < 6: continue 
                    rel_from_table, rel_from_col = row[1].strip(), row[2].strip()
                    rel_to_table, rel_to_col = row[3].strip(), row[4].strip()
                    rel_type = row[5].strip() if len(row) > 5 and row[5].strip() else "N:1"
                    
                    vertical_segment_x_override = None
                    if len(row) > 6 and row[6].strip():
                        try:
                            vertical_segment_x_override = float(row[6].strip())
                        except ValueError:
                            # print(f"Warning: Could not parse VerticalSegmentX for relationship {rel_from_table}.{rel_from_col}: '{row[6]}'")
                            pass # Keep as None if parsing fails

                    if all([rel_from_table, rel_from_col, rel_to_table, rel_to_col]):
                        parsed_relationships_from_csv.append({
                            "from_table": rel_from_table, "from_col": rel_from_col,
                            "to_table": rel_to_table, "to_col": rel_to_col,
                            "type": rel_type, 
                            "vertical_segment_x_override": vertical_segment_x_override 
                        })
                
                elif current_section == "CANVAS_SIZE": 
                    data_offset = 1 
                    if len(row) >= data_offset + 2: 
                        try:
                            imported_canvas_width = int(row[data_offset].strip())
                            imported_canvas_height = int(row[data_offset+1].strip())
                        except ValueError:
                            print(f"Warning: Could not parse canvas size from CSV row: {row}")
                
                elif current_section == "NOTES":
                    # The first row after the marker is considered the notes content
                    # For multi-line notes, we'd need a more complex parsing or an end marker.
                    imported_notes = row[0] # Assuming notes are in the first cell of the row after marker
                    current_section = None # Stop processing notes after one line for simplicity
            
            if imported_canvas_width and imported_canvas_height:
                constants.current_canvas_dimensions["width"] = imported_canvas_width
                constants.current_canvas_dimensions["height"] = imported_canvas_height
                if window.scene: 
                    window.scene.setSceneRect(0,0, imported_canvas_width, imported_canvas_height)

            window.diagram_notes = imported_notes
            if hasattr(window, 'notes_text_edit') and window.notes_text_edit:
                window.notes_text_edit.setPlainText(window.diagram_notes)

            window.undo_stack.beginMacro("Import CSV")
            
            all_imported_table_graphics = [] 
            for table_name_to_import, t_data in parsed_tables_from_csv.items():
                table_obj_data = window.handle_add_table_button( 
                    table_name_prop=table_name_to_import,
                    columns_prop=t_data["columns"], 
                    pos=t_data.get("pos"), 
                    width_prop=t_data.get("width"),
                    body_color_hex=t_data.get("body_color"),
                    header_color_hex=t_data.get("header_color")
                )
                if table_obj_data and table_obj_data.graphic_item:
                    all_imported_table_graphics.append(table_obj_data.graphic_item)
            
            for rel_info in parsed_relationships_from_csv:
                fk_table_obj = window.tables_data.get(rel_info["from_table"])
                pk_table_obj = window.tables_data.get(rel_info["to_table"])
                if fk_table_obj and pk_table_obj:
                    fk_col_obj = fk_table_obj.get_column_by_name(rel_info["from_col"])
                    pk_col_obj = pk_table_obj.get_column_by_name(rel_info["to_col"])
                    if fk_col_obj and pk_col_obj: 
                        if not pk_col_obj.is_pk: 
                            continue
                        # Pass vertical_segment_x_override to create_relationship
                        window.create_relationship(
                            fk_table_obj, pk_table_obj,
                            fk_col_obj.name, pk_col_obj.name,
                            rel_info["type"], 
                            vertical_segment_x_override=rel_info["vertical_segment_x_override"]
                        )
            
            window.undo_stack.endMacro()

            window.update_all_relationships_graphics() 
            window.populate_diagram_explorer()
            window.update_sql_preview_pane() # Update SQL preview after import
            window.current_file_path = path 
            window.update_window_title()

            if all_imported_table_graphics:
                overall_rect = QRectF()
                if all_imported_table_graphics[0].sceneBoundingRect().isValid(): 
                    overall_rect = all_imported_table_graphics[0].sceneBoundingRect()
                
                for item_graphic in all_imported_table_graphics[1:]:
                    item_rect = item_graphic.sceneBoundingRect()
                    if item_rect.isValid(): 
                        overall_rect = overall_rect.united(item_rect)
                
                if overall_rect.isValid() and not overall_rect.isEmpty():
                    padding = 50 
                    overall_rect.adjust(-padding, -padding, padding, padding)
                    window.view.fitInView(overall_rect, Qt.AspectRatioMode.KeepAspectRatio)

            QMessageBox.information(window, "Import Successful",
                                    f"{len(parsed_tables_from_csv)} tables, "
                                    f"and {len(window.relationships_data)} relationships processed from {os.path.basename(path)}. "
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


def export_to_erd_impl(window, file_path_to_save=None):
    """Exports the current ERD data to an ERD file (CSV formatted)."""
    if not window.tables_data and not window.relationships_data: 
        QMessageBox.information(window, "Export ERD File", "No data to export.")
        return
    
    if not file_path_to_save: 
        print("Error: No file path provided for export.")
        return

    try:
        with open(file_path_to_save, 'w', newline='', encoding='utf-8-sig') as csvfile: 
            writer = csv.writer(csvfile)

            writer.writerow(["Table Name", "Column Name", "Data Type", "Is Primary Key", "Is Foreign Key", 
                             "References Table", "References Column", "FK Relationship Type"])
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

            writer.writerow([constants.CSV_TABLE_POSITION_MARKER, "Table Name", "X", "Y", "Width", 
                             "Body Color HEX", "Header Color HEX"])
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
            

            writer.writerow([constants.CSV_CANVAS_SIZE_MARKER, "Width", "Height"]) 
            writer.writerow([constants.CSV_CANVAS_SIZE_MARKER, constants.current_canvas_dimensions["width"], constants.current_canvas_dimensions["height"]])
            
            if window.relationships_data:
                writer.writerow([]) 
                # Updated header for relationships to include VerticalSegmentX
                writer.writerow([constants.CSV_RELATIONSHIP_DEF_MARKER, 
                                 "From Table (FK Source)", "FK Column", 
                                 "To Table (PK Source)", "PK Column", 
                                 "Relationship Type", "VerticalSegmentX"])
                sorted_rels = sorted(window.relationships_data, key=lambda r: (r.table1_name, r.fk_column_name, r.table2_name, r.pk_column_name))
                for rel in sorted_rels:
                    # Ensure all fields are present, even if empty, for consistent row length
                    rel_type_str = rel.relationship_type if rel.relationship_type else "N:1"
                    fk_col_str = rel.fk_column_name if rel.fk_column_name else ""
                    pk_col_str = rel.pk_column_name if rel.pk_column_name else ""

                    # Write vertical_segment_x_override, or empty string if None
                    vertical_x_str = str(rel.vertical_segment_x_override) if rel.vertical_segment_x_override is not None else ""
                    writer.writerow([
                        constants.CSV_RELATIONSHIP_DEF_MARKER, 
                        rel.table1_name,
                        rel.fk_column_name,
                        rel.table2_name,
                        pk_col_str,
                        rel_type_str,
                        vertical_x_str 
                    ])

            # Save Notes
            writer.writerow([])
            writer.writerow([constants.CSV_NOTES_MARKER, "notes_content_follows"])
            # For simplicity, save notes as a single line. For multi-line, would need to handle newlines.
            writer.writerow([window.diagram_notes if window.diagram_notes else ""])

            QMessageBox.information(window, "File Saved", f"Data saved successfully to: {file_path_to_save}")
    except Exception as e:
        QMessageBox.critical(window, "Save Error", f"Could not save file: {e}")
        print(f"Error exporting to ERD file: {e}")


def handle_import_sql_button_impl(window):
    """Handles importing ERD data from an SQL file."""
    path, _ = QFileDialog.getOpenFileName(window, "Import SQL File", "", "SQL Files (*.sql);;All Files (*)")
    if not path:
        return

    if not window.prompt_to_save_if_dirty():
        return # User cancelled or save failed

    try:
        with open(path, 'r', encoding='utf-8') as f:
            sql_content = f.read()
    except Exception as e:
        QMessageBox.critical(window, "Import Error", f"Could not read SQL file: {e}")
        return

    if not sql_content.strip():
        QMessageBox.information(window, "Import SQL", "SQL file is empty.")
        return

    window.new_diagram() # Clear current diagram

    try:
        parsed_tables_from_sql, parsed_relationships_from_sql = parse_sql_schema(sql_content)
    except Exception as e:
        QMessageBox.critical(window, "SQL Parse Error", f"Could not parse SQL schema: {e}\nCheck console for details.")
        print(f"SQL Parse Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return

    window.undo_stack.beginMacro("Import SQL")

    all_imported_table_graphics = []
    target_positions = []

    if parsed_tables_from_sql:
        num_tables = len(parsed_tables_from_sql)
        avg_table_width = constants.DEFAULT_TABLE_WIDTH
        # Estimate average table height (header + 5 columns + padding)
        avg_table_height_estimate = constants.TABLE_HEADER_HEIGHT + (5 * constants.COLUMN_HEIGHT) + constants.PADDING
        
        inter_table_spacing_x = 50
        inter_table_spacing_y = 50 # Spacing between rows of tables

        view_width_for_calc = window.view.width() if window.view and window.view.width() > 200 else 1200
        
        tables_per_row = max(1, int((view_width_for_calc - inter_table_spacing_x) / (avg_table_width + inter_table_spacing_x)))
        num_rows = math.ceil(num_tables / tables_per_row)

        block_content_width = tables_per_row * avg_table_width + max(0, tables_per_row - 1) * inter_table_spacing_x
        block_content_height = num_rows * avg_table_height_estimate + max(0, num_rows - 1) * inter_table_spacing_y

        view_center_scene = QPointF(view_width_for_calc / 2, (window.view.height() if window.view else 800) / 2)
        if window.view:
            view_center_scene = window.view.mapToScene(window.view.viewport().rect().center())

        start_x_for_block = view_center_scene.x() - block_content_width / 2
        start_y_for_block = view_center_scene.y() - block_content_height / 2

        current_row_idx = 0
        current_col_idx = 0
        for i in range(num_tables):
            px = start_x_for_block + current_col_idx * (avg_table_width + inter_table_spacing_x)
            py = start_y_for_block + current_row_idx * (avg_table_height_estimate + inter_table_spacing_y)
            target_positions.append(QPointF(px, py))
            current_col_idx += 1
            if current_col_idx >= tables_per_row:
                current_col_idx = 0
                current_row_idx += 1

    # Add tables at calculated positions
    table_names_ordered = list(parsed_tables_from_sql.keys()) # Keep an order
    for i, table_name_to_import in enumerate(table_names_ordered):
        t_data = parsed_tables_from_sql[table_name_to_import]
        pos_for_table = target_positions[i] if i < len(target_positions) else QPointF(50 + (i % 5) * 250, 50 + (i // 5) * 200) # Fallback

        table_obj_data = window.handle_add_table_button(
            table_name_prop=table_name_to_import,
            columns_prop=t_data["columns"], # These are already Column objects from parser
            pos=pos_for_table
        )
        if table_obj_data and table_obj_data.graphic_item:
            all_imported_table_graphics.append(table_obj_data.graphic_item)

    # Add relationships
    for rel_info in parsed_relationships_from_sql:
        fk_table_obj = window.tables_data.get(rel_info["from_table"])
        pk_table_obj = window.tables_data.get(rel_info["to_table"])
        if fk_table_obj and pk_table_obj:
            # The parser should have already marked fk_col_obj.is_fk = True
            window.create_relationship(
                fk_table_obj, pk_table_obj,
                rel_info["from_col"], rel_info["to_col"],
                rel_info["type"]
            )

    window.undo_stack.endMacro()
    window.update_all_relationships_graphics()
    window.populate_diagram_explorer()
    window.update_sql_preview_pane()
    window.current_file_path = None # Imported SQL is not a "saved" ERD file
    window.copied_table_data = None # Clear copy buffer on new/import
    window.update_window_title()

    # Focus on imported content
    if all_imported_table_graphics:
        overall_rect = QRectF()
        if all_imported_table_graphics[0].sceneBoundingRect().isValid():
            overall_rect = all_imported_table_graphics[0].sceneBoundingRect()
        
        for item_graphic in all_imported_table_graphics[1:]:
            item_rect = item_graphic.sceneBoundingRect()
            if item_rect.isValid():
                overall_rect = overall_rect.united(item_rect)
        
        if overall_rect.isValid() and not overall_rect.isEmpty():
            padding = 75 # Increased padding for better view
            overall_rect.adjust(-padding, -padding, padding, padding)
            window.view.fitInView(overall_rect, Qt.AspectRatioMode.KeepAspectRatio)

    QMessageBox.information(window, "Import Successful",
                            f"{len(parsed_tables_from_sql)} tables and "
                            f"{len(parsed_relationships_from_sql)} potential relationships processed from SQL.\n"
                            "Tables have been centered on the canvas.")
