# sql_parser.py
# Contains basic logic to parse SQL CREATE TABLE and ALTER TABLE statements.

import re
from data_models import Column

def map_sql_type_to_app_type(sql_type_str):
    """Maps common SQL types back to application-specific data types."""
    if not sql_type_str:
        return "TEXT"
    sql_type_upper = sql_type_str.upper()

    # Handle types with lengths like VARCHAR(255), CHAR(N)
    # This will keep them as is, assuming the app's type list might contain them.
    if "VARCHAR" in sql_type_upper and "(" in sql_type_upper and ")" in sql_type_upper:
        return sql_type_upper
    if "CHAR" in sql_type_upper and "(" in sql_type_upper and ")" in sql_type_upper:
        return sql_type_upper
    if "NUMERIC" in sql_type_upper and "(" in sql_type_upper and ")" in sql_type_upper:
        return sql_type_upper
    if "DECIMAL" in sql_type_upper and "(" in sql_type_upper and ")" in sql_type_upper:
        return sql_type_upper

    # Reverse mapping (simplified)
    # This should ideally align with the app's DEFAULT_COLUMN_DATA_TYPES
    mapping = {
        "TEXT": "TEXT",
        "INTEGER": "INTEGER",
        "INT": "INTEGER",
        "BIGINT": "BIGINT",
        "SMALLINT": "SMALLINT",
        "REAL": "REAL",
        "FLOAT": "FLOAT",
        "DOUBLE": "DOUBLE PRECISION", # Common alias
        "DOUBLE PRECISION": "DOUBLE PRECISION",
        "NUMERIC": "NUMERIC", # Base type
        "DECIMAL": "DECIMAL", # Base type
        "BOOLEAN": "BOOLEAN",
        "DATE": "DATE",
        "DATETIME": "DATETIME",
        "TIMESTAMP": "TIMESTAMP",
        "TIME": "TIME",
        "BLOB": "BLOB",
        "VARCHAR": "VARCHAR", # Base type
        "CHAR": "CHAR"        # Base type
        # Add more mappings as needed
    }
    # Attempt to find a direct match or a match for the base type (e.g., "INTEGER" for "INTEGER PRIMARY KEY")
    for key in mapping:
        if key in sql_type_upper:
            return mapping[key]
    
    return sql_type_upper # Return original if no simple mapping found

def _extract_identifier(match_obj, group_idx_quoted, group_idx_unquoted):
    """Helper to get an identifier from regex match groups (quoted or unquoted)."""
    quoted_val = match_obj.group(group_idx_quoted)
    if quoted_val is not None:
        return quoted_val
    return match_obj.group(group_idx_unquoted)

def parse_sql_schema(sql_content):
    """
    Parses SQL content to extract table definitions and relationships.
    Returns a tuple: (tables_dict, relationships_list)
    tables_dict: {table_name: {"columns": [Column_objects], "pks": [pk_col_names]}}
    relationships_list: [{"from_table": str, "from_col": str, "to_table": str, "to_col": str, "type": "N:1"}]
    """
    tables = {}
    relationships = []

    # Remove comments (simple /* ... */ and -- ...)
    sql_content = re.sub(r"/\*.*?\*/", "", sql_content, flags=re.DOTALL)
    sql_content = re.sub(r"--.*?\n", "", sql_content)
    
    # Split statements by semicolon, handling potential semicolons within strings later if needed
    statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]

    for stmt in statements:
        stmt_upper = stmt.upper()

        # Parse CREATE TABLE
        if stmt_upper.startswith("CREATE TABLE"):
            # Regex to capture table name and column definitions
            # Handles quoted (e.g., "My Table") and unquoted (e.g., My_Table) names.
            create_table_match = re.search(
                r"CREATE TABLE\s+(?:IF NOT EXISTS\s+)?(?:\"([^\"]+)\"|([a-zA-Z0-9_]+))\s*\((.+)\)",
                stmt, re.IGNORECASE | re.DOTALL
            )
            if create_table_match:
                # group(1) is for quoted table name, group(2) for unquoted
                table_name_quoted = create_table_match.group(1)
                table_name_unquoted = create_table_match.group(2)
                table_name = table_name_quoted if table_name_quoted is not None else table_name_unquoted
                if not table_name: continue # Should not happen if regex matches
                columns_str = create_table_match.group(3)
                
                current_columns = []
                primary_keys = []

                # Split column definitions by comma, careful about commas in type definitions like NUMERIC(10,2)
                # This simple split might fail for complex column defs or table constraints defined inline.
                col_defs = re.split(r',(?![^\(]*\))', columns_str) # Split by comma not inside parentheses

                for col_def_full in col_defs:
                    col_def = col_def_full.strip()
                    if not col_def: continue

                    if col_def.upper().startswith("PRIMARY KEY"):
                        pk_match = re.search(r"PRIMARY KEY\s*\((.+)\)", col_def, re.IGNORECASE)
                        if pk_match:
                            pks = [pk.strip().strip('"') for pk in pk_match.group(1).split(',')]
                            primary_keys.extend(pks)
                        continue
                    
                    # Regex for column name (quoted or unquoted) and type
                    col_match = re.match(
                        r"(?:\"([^\"]+)\"|([a-zA-Z0-9_]+))\s+([\w\s\(\),]+?)(?:\s+PRIMARY KEY|\s+NOT NULL|\s+NULL|\s+UNIQUE|\s+DEFAULT.*|$)",
                        col_def, re.IGNORECASE
                    )
                    if col_match:
                        col_name_quoted = col_match.group(1)
                        col_name_unquoted = col_match.group(2)
                        col_name = col_name_quoted if col_name_quoted is not None else col_name_unquoted
                        col_type_sql = col_match.group(3).strip()
                        col_type_app = map_sql_type_to_app_type(col_type_sql)
                        
                        is_pk = "PRIMARY KEY" in col_def.upper() or col_name in primary_keys
                        if is_pk and col_name not in primary_keys: # Add if defined inline
                            primary_keys.append(col_name)

                        current_columns.append(Column(name=col_name, data_type=col_type_app, is_pk=is_pk))
                
                tables[table_name] = {"columns": current_columns, "pks": list(set(primary_keys))} # Ensure unique PKs
                # Update is_pk for columns based on collected primary_keys
                for col_obj in tables[table_name]["columns"]:
                    if col_obj.name in tables[table_name]["pks"]:
                        col_obj.is_pk = True

        # Parse ALTER TABLE for FOREIGN KEY constraints
        elif stmt_upper.startswith("ALTER TABLE"):
            fk_match = re.search(
                r"ALTER TABLE\s+(?:\"([^\"]+)\"|([a-zA-Z0-9_]+))\s+"  # From Table
                r"ADD\s+(?:CONSTRAINT\s+(?:\"([^\"]+)\"|([a-zA-Z0-9_]+))\s+)?FOREIGN KEY\s*\((?:\"([^\"]+)\"|([a-zA-Z0-9_]+))\)\s+"  # Opt. Constraint, From Column
                r"REFERENCES\s+(?:\"([^\"]+)\"|([a-zA-Z0-9_]+))\s*\((?:\"([^\"]+)\"|([a-zA-Z0-9_]+))\)",  # To Table, To Column
                stmt, re.IGNORECASE
            )
            if fk_match:
                from_table = _extract_identifier(fk_match, 1, 2)
                # Constraint name is group 3 (quoted) or 4 (unquoted), optional. We don't use it here.
                from_col = _extract_identifier(fk_match, 5, 6)
                to_table = _extract_identifier(fk_match, 7, 8)
                to_col = _extract_identifier(fk_match, 9, 10)
                
                relationships.append({
                    "from_table": from_table, "from_col": from_col,
                    "to_table": to_table, "to_col": to_col,
                    "type": "N:1" # Default type, can be refined later
                })
                # Mark the column as FK in the table structure
                if from_table in tables and tables[from_table]["columns"]:
                    for col_obj in tables[from_table]["columns"]:
                        if col_obj.name == from_col:
                            col_obj.is_fk = True
                            col_obj.references_table = to_table
                            col_obj.references_column = to_col
                            # col_obj.fk_relationship_type could be set here if parsed
    return tables, relationships