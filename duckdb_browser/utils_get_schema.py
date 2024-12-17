import duckdb
from typing import Dict, Any, List

def get_duckdb_schema(table_name: str, con: duckdb.DuckDBPyConnection) -> List[Dict[str, Any]]:
    schema = con.execute(f"DESCRIBE {table_name}").fetchdf()
    columns = []
    for _, row in schema.iterrows():
        column = {
            "name": row["column_name"],
            "type": row["column_type"],
            "null": "NULL" if row["null"] == "YES" else "NOT NULL",
            "default": row["default"],
        }
        columns.append(column)
    return columns

def get_complete_schema(con: duckdb.DuckDBPyConnection) -> Dict[str, Any]:
    all_tables = con.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'").fetchdf()
    schema = {}
    for table in all_tables['table_name']:
        schema[table] = {
            "columns": get_duckdb_schema(table, con),
            "primary_keys": [],
            "foreign_keys": []
        }
        
        # Get primary keys
        primary_keys = con.execute(f"""
            SELECT column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            WHERE tc.constraint_type = 'PRIMARY KEY'
                AND tc.table_name = '{table}'
                AND tc.table_schema = 'main'
        """).fetchdf()
        
        if not primary_keys.empty:
            schema[table]["primary_keys"] = primary_keys['column_name'].tolist()
        
        # Note: DuckDB doesn't support retrieving foreign key information through SQL queries
        # If you need foreign key information, you'll have to implement a custom solution
        # or maintain this information separately
    
    return schema
