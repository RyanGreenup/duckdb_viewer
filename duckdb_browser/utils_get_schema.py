import duckdb
from typing import Dict, Any, List


def get_complete_schema(con: duckdb.DuckDBPyConnection) -> Dict[str, Any]:
    try:
        schema: Dict[str, Dict[str, Any]] = {}

        # Get all tables with their columns and primary key information
        tables_info = con.execute("""
            SELECT 
                t.table_name,
                c.column_name,
                c.data_type,
                c.is_nullable,
                CASE WHEN pk.column_name IS NOT NULL THEN true ELSE false END AS is_primary_key
            FROM 
                information_schema.tables t
            JOIN 
                information_schema.columns c ON t.table_name = c.table_name
            LEFT JOIN (
                SELECT tc.table_name, kcu.column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu 
                    ON tc.constraint_name = kcu.constraint_name
                WHERE tc.constraint_type = 'PRIMARY KEY'
            ) pk ON t.table_name = pk.table_name AND c.column_name = pk.column_name
            WHERE 
                t.table_schema = 'main'
            ORDER BY 
                t.table_name, c.ordinal_position
        """).fetchall()

        for row in tables_info:
            table_name, column_name, data_type, is_nullable, is_primary_key = row

            if table_name not in schema:
                schema[table_name] = {
                    "columns": [],
                    "primary_keys": [],
                    "foreign_keys": [],  # Still empty, as DuckDB doesn't provide easy access to this info
                }

            schema[table_name]["columns"].append(
                {"name": column_name, "type": data_type, "notnull": is_nullable == "NO"}
            )

            if is_primary_key:
                schema[table_name]["primary_keys"].append(column_name)

        return schema

    except Exception as e:
        print(f"Error retrieving schema: {str(e)}")
        return {}


def generate_create_table_statements(schema: Dict[str, Any]) -> List[str]:
    create_statements = []

    for table_name, table_info in schema.items():
        columns = []
        for column in table_info["columns"]:
            column_def = f"{column['name']} {column['type']}"
            if column["notnull"]:
                column_def += " NOT NULL"
            columns.append(column_def)

        primary_key = ""
        if table_info["primary_keys"]:
            primary_key = f", PRIMARY KEY ({', '.join(table_info['primary_keys'])})"

        create_statement = f"CREATE TABLE {table_name} (\n    {',\n    '.join(columns)}{primary_key}\n);"
        create_statements.append(create_statement)

    return create_statements
