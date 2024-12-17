import duckdb
from typing import Dict, Any

def get_duckdb_schema(table_name: str, con: duckdb.DuckDBPyConnection) -> Dict[str, Any]:
    schema = con.execute(f"DESCRIBE {table_name}").fetchdf()
    columns = []
    for _, row in schema.iterrows():
        column = {
            "name": row["column_name"],
            "type": row["column_type"],
            "null": "NOT NULL" if row["null"] == "NO" else "NULL",
            "default": row["default"],
        }
        columns.append(column)
    return columns

def get_complete_schema(con: duckdb.DuckDBPyConnection) -> Dict[str, Any]:
    all_tables = con.execute("SHOW TABLES").fetchdf()
    schema = {}
    for table in all_tables['name']:
        table_info = con.execute(f"PRAGMA table_info('{table}')").fetchdf()
        primary_keys = table_info[table_info['pk'] > 0]['name'].tolist()
        
        schema[table] = {
            "columns": get_duckdb_schema(table, con),
            "primary_keys": primary_keys,
        }
        
        # Get foreign keys
        foreign_keys = con.execute(f"PRAGMA foreign_key_list('{table}')").fetchdf()
        if not foreign_keys.empty:
            schema[table]["foreign_keys"] = []
            for _, fk in foreign_keys.iterrows():
                schema[table]["foreign_keys"].append({
                    "column": fk['from'],
                    "references": {
                        "table": fk['table'],
                        "column": fk['to']
                    }
                })
    
    return schema
