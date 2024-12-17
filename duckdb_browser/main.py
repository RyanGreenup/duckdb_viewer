#!/usr/bin/env python
import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QTableView
from PySide6.QtGui import QStandardItemModel, QStandardItem
import duckdb
from duckdb import DuckDBPyConnection
from typing import Optional
import typer


def create_connection(db_path: str = ":memory:") -> DuckDBPyConnection:
    # Connect to DuckDB database or create if it doesn't exist
    con = duckdb.connect(database=db_path, read_only=False)

    # Create a table and insert some data if the table does not exist
    try:
        con.execute("SELECT * FROM test")
    except duckdb.CatalogException:
        con.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
        con.execute("INSERT INTO test VALUES (1, 'John')")
        con.execute("INSERT INTO test VALUES (2, 'Jane')")

    return con


class MainWindow(QMainWindow):
    def __init__(
        self, db_path: str = ":memory:", parent: Optional[QMainWindow] = None
    ) -> None:
        super().__init__(parent)

        # Connect to DuckDB
        self.con = create_connection(db_path=db_path)

        # Fetch data from DuckDB
        query = duckdb.sql("SELECT * FROM test", connection=self.con)
        results = query.fetchall()

        # Create a QStandardItemModel and populate it with the fetched data
        self.model = QStandardItemModel()
        self.model.setColumnCount(2)  # ID and Name columns
        self.model.setHorizontalHeaderLabels(["ID", "Name"])

        for row in results:
            id_item = QStandardItem(str(row[0]))
            name_item = QStandardItem(row[1])
            self.model.appendRow([id_item, name_item])

        # Create a QTableView and set the model
        self.view = QTableView(self)
        self.view.setModel(self.model)
        self.setCentralWidget(self.view)


def main(db_path: str = ":memory:") -> None:
    app = QApplication(sys.argv)
    window = MainWindow(db_path=db_path)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    typer.run(main)
