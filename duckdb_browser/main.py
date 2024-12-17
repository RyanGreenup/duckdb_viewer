#!/usr/bin/env python
import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QTableView
from PySide6.QtCore import QPersistentModelIndex, Qt, QAbstractTableModel, QModelIndex
import duckdb
from duckdb import DuckDBPyConnection
from typing import Optional, Any, List, Union
import typer
import pandas as pd

# Custom type for our data
DataType = List[List[Any]]


class DuckDBTableModel(QAbstractTableModel):
    def __init__(self, connection: DuckDBPyConnection, table_name: str):
        super().__init__()
        self.connection = connection
        self.table_name = table_name
        self._data: DataType = []
        self.headers: List[str] = []
        self._fetch_data()

    def _fetch_data(self) -> None:
        query = f"SELECT * FROM {self.table_name}"
        df: pd.DataFrame = self.connection.execute(query).df()
        self._data = df.values.tolist()
        self.headers = df.columns.tolist()

    def rowCount(
        self, parent: Union[QModelIndex, QPersistentModelIndex] = QModelIndex()
    ) -> int:
        return len(self._data)

    def columnCount(
        self, parent: Union[QModelIndex, QPersistentModelIndex] = QModelIndex()
    ) -> int:
        return len(self.headers)

    def data(
        self,
        index: Union[QModelIndex, QPersistentModelIndex],
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if role == Qt.ItemDataRole.DisplayRole:
            return str(self._data[index.row()][index.column()])
        return None

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if (
            orientation == Qt.Orientation.Horizontal
            and role == Qt.ItemDataRole.DisplayRole
        ):
            return self.headers[section]
        return None

    def setData(
        self, index: QModelIndex, value: Any, role: int = Qt.ItemDataRole.EditRole
    ) -> bool:
        if role == Qt.ItemDataRole.EditRole:
            row = index.row()
            col = index.column()
            column_name = self.headers[col]
            self._data[row][col] = value

            # Update the database
            update_query = f"""
            UPDATE {self.table_name}
            SET {column_name} = ?
            WHERE id = ?
            """
            self.connection.execute(update_query, [value, self._data[row][0]])

            self.dataChanged.emit(index, index, [role])
            return True
        return False

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        return (
            Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsSelectable
            | Qt.ItemFlag.ItemIsEditable
        )


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

        # Create and set the model
        self.model = DuckDBTableModel(self.con, "test")

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
