# sql_generator.py
# Contains logic to generate SQL statements from diagram data.

def map_data_type_to_sql(app_type_str):
    """Maps application-specific data types to common SQL types."""
    if not app_type_str:
        return "TEXT" # Default if type is empty
    app_type_upper = app_type_str.upper()

    # Handle types with lengths like VARCHAR(255), CHAR(N)
    if "VARCHAR" in app_type_upper and "(" in app_type_upper and ")" in app_type_upper:
        return app_type_upper
    if "CHAR" in app_type_upper and "(" in app_type_upper and ")" in app_type_upper:
        return app_type_upper
    
    # Mapping for common types
    mapping = {
        "TEXT": "TEXT",
        "INTEGER": "INTEGER",
        "INT": "INTEGER",
        "SERIAL": "INTEGER", # Simplified; consider dialect for AUTOINCREMENT/SERIAL
        "BIGINT": "BIGINT",
        "SMALLINT": "SMALLINT",
        "REAL": "REAL",
        "FLOAT": "FLOAT",
        "DOUBLE PRECISION": "DOUBLE PRECISION",
        "NUMERIC": "NUMERIC",
        "DECIMAL": "DECIMAL",
        "BOOLEAN": "BOOLEAN", # Standard SQL; some DBs use INTEGER
        "DATE": "DATE",
        "DATETIME": "DATETIME",
        "TIMESTAMP": "TIMESTAMP",
        "TIME": "TIME",
        "BLOB": "BLOB",
        "UUID": "VARCHAR(36)", # Common representation for UUID
        "JSON": "TEXT",        # Or JSON type if DB supports it
        "CHAR": "CHAR"         # Default for CHAR if no length, or CHAR(1)
    }
    return mapping.get(app_type_upper, app_type_upper) # Return original if not in map (e.g. VARCHAR) or default

def generate_sql_for_diagram(tables_data, relationships_data):
    """
    Generates SQL CREATE TABLE and ALTER TABLE statements for the diagram.
    tables_data: dict of {name: Table_object}
    relationships_data: list of Relationship_object
    """
    sql_statements = []
    
    sorted_table_names = sorted(tables_data.keys())

    for table_name in sorted_table_names:
        table = tables_data[table_name]
        if not table.columns:
            sql_statements.append(f"-- Table \"{table.name}\" has no columns and will not be created.\n")
            continue

        cols_sql = []
        pk_cols = []
        for col in table.columns:
            col_sql_part = f"    \"{col.name}\" {map_data_type_to_sql(col.data_type)}"
            if col.is_pk:
                pk_cols.append(f"\"{col.name}\"")
            cols_sql.append(col_sql_part)
        
        create_table_sql = f"CREATE TABLE \"{table.name}\" (\n"
        create_table_sql += ",\n".join(cols_sql)
        
        if pk_cols:
            create_table_sql += f",\n    PRIMARY KEY ({', '.join(pk_cols)})"
        
        create_table_sql += "\n);"
        sql_statements.append(create_table_sql)
        sql_statements.append("\n")

    if relationships_data:
        sql_statements.append("-- Foreign Key Constraints\n")
        sorted_relationships = sorted(relationships_data, key=lambda r: (r.table1_name, r.fk_column_name))
        for rel in sorted_relationships:
            constraint_name = f"fk_{rel.table1_name}_{rel.fk_column_name}"
            alter_sql = (
                f"ALTER TABLE \"{rel.table1_name}\"\n"
                f"ADD CONSTRAINT \"{constraint_name}\" FOREIGN KEY (\"{rel.fk_column_name}\")\n"
                f"REFERENCES \"{rel.table2_name}\" (\"{rel.pk_column_name}\");"
            )
            sql_statements.append(alter_sql)
            sql_statements.append("\n")
            
    return "".join(sql_statements)