import duckdb
from typing import List

def get_complete_schema(con: duckdb.DuckDBPyConnection) -> str:
    """
    Returns the complete schema of a DuckDB database as a string.

    Args:
        con (duckdb.DuckDBPyConnection): An active DuckDB connection.

    Returns:
        str: A string representation of the complete database schema.
    """
    schema_str = "Database Schema:\n\n"

    # Get all tables
    tables = con.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'").fetchall()

    for table in tables:
        table_name = table[0]
        schema_str += f"Table: {table_name}\n"

        # Get column information for each table
        columns = con.execute(f"PRAGMA table_info('{table_name}')").fetchall()

        for column in columns:
            col_name = column[1]
            col_type = column[2]
            is_nullable = "NULL" if column[3] == 0 else "NOT NULL"
            default_value = f"DEFAULT {column[4]}" if column[4] is not None else ""
            is_primary_key = "PRIMARY KEY" if column[5] == 1 else ""

            schema_str += f"  - {col_name} {col_type} {is_nullable} {default_value} {is_primary_key}\n"

        schema_str += "\n"

    # Get all views
    views = con.execute("SELECT table_name FROM information_schema.views WHERE table_schema = 'main'").fetchall()

    for view in views:
        view_name = view[0]
        schema_str += f"View: {view_name}\n"

        # Get the view definition
        view_def = con.execute(f"SELECT sql FROM sqlite_master WHERE type='view' AND name='{view_name}'").fetchone()[0]
        schema_str += f"  Definition: {view_def}\n\n"

    return schema_str.strip()
