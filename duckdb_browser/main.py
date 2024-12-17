#!/usr/bin/env python
import sys
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import QApplication, QMainWindow, QTableView
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex
import duckdb
from duckdb import DuckDBPyConnection
from typing import Optional
import typer


class DuckDBTableModel(QAbstractTableModel):
    def __init__(self, connection: DuckDBPyConnection, table_name: str):
        super().__init__()
        self.connection = connection
        self.table_name = table_name
        self.data = self._fetch_data()
        self.headers = self.data.columns.tolist()

    def _fetch_data(self):
        query = f"SELECT * FROM {self.table_name}"
        return self.connection.execute(query).df()

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self.data)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self.headers)

    def data(self, index: QModelIndex, role: Qt.ItemDataRole = Qt.DisplayRole) -> Optional[str]:
        if role == Qt.DisplayRole:
            return str(self.data.iloc[index.row(), index.column()])
        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role: Qt.ItemDataRole = Qt.DisplayRole) -> Optional[str]:
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.headers[section]
        return None

    def setData(self, index: QModelIndex, value: any, role: Qt.ItemDataRole = Qt.EditRole) -> bool:
        if role == Qt.EditRole:
            row = index.row()
            col = index.column()
            column_name = self.headers[col]
            # old_value = self.data.iloc[row, col]  # Removed unused variable
            self.data.iloc[row, col] = value

            # Update the database
            update_query = f"""
            UPDATE {self.table_name}
            SET {column_name} = ?
            WHERE id = ?
            """
            self.connection.execute(update_query, [value, self.data.iloc[row, 0]])

            self.dataChanged.emit(index, index, [role])
            return True
        return False

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable


def create_connection(db_path: str = ":memory:") -> DuckDBPyConnection:
    # Connect to DuckDB database or create if it doesn't exist
    con = duckdb.connect(database=db_path, read_only=False)

    # Create a table and insert some data if the table does not exist
    con.execute("""
        CREATE TABLE IF NOT EXISTS test (
            id INTEGER PRIMARY KEY,
            name TEXT
        )
    """)

    # Check if the table is empty and insert initial data if needed
    if con.execute("SELECT COUNT(*) FROM test").fetchone()[0] == 0:
        con.execute("INSERT INTO test VALUES (1, 'John'), (2, 'Jane')")

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


def main(db_path: str = "duckdb_browser.db") -> None:
    app = QApplication(sys.argv)
    window = MainWindow(db_path=db_path)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    typer.run(main)
