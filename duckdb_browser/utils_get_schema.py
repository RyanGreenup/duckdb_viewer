import duckdb
import json

def get_duckdb_schema(table_name, con: duckdb.DuckDBPyConnection):
    schema = con.execute(f"DESCRIBE {table_name}").fetchdf()
    return schema[["column_name", "column_type"]].to_dict()

def get_complete_schema(con: duckdb.DuckDBPyConnection):
    all_tables = con.execute("SHOW TABLES").fetchdf()
    schema = dict()
    for table in all_tables['name']:
        schema[table] = get_duckdb_schema(table, con)
    return schema
