check:
    ruff format duckdb_browser/*.py
    ruff check duckdb_browser --fix
    pyright duckdb_browser
    ruff format duckdb_browser/*.py
    mypy --strict duckdb_browser
    # vulture duckdb_browser/*.py

