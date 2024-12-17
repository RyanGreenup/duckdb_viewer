#!/usr/bin/env python
import sys
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QTableView,
    QTreeView,
    QSplitter,
    QVBoxLayout,
    QWidget,
    QHBoxLayout,
    QLineEdit,
    QHeaderView,
)
from typing import List, Optional
from PySide6.QtCore import (
    QPersistentModelIndex,
    Qt,
    QAbstractTableModel,
    QModelIndex,
    QAbstractItemModel,
)
import duckdb
from duckdb import DuckDBPyConnection
from typing import Optional, Any, List, Union
import typer
import pandas as pd

# Custom type for our data
DataType = List[List[Any]]


class TableListModel(QAbstractItemModel):
    def __init__(self, connection: DuckDBPyConnection):
        super().__init__()
        self.connection = connection
        self.tables = self._fetch_tables()

    def _fetch_tables(self) -> List[str]:
        query = "SELECT name FROM sqlite_master WHERE type='table'"
        return [row[0] for row in self.connection.execute(query).fetchall()]

    def rowCount(
        self, parent: Union[QModelIndex, QPersistentModelIndex] = QModelIndex()
    ) -> int:
        return len(self.tables) if not parent.isValid() else 0

    def columnCount(
        self, parent: Union[QModelIndex, QPersistentModelIndex] = QModelIndex()
    ) -> int:
        return 1

    def data(
        self,
        index: Union[QModelIndex, QPersistentModelIndex],
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if role == Qt.ItemDataRole.DisplayRole:
            return self.tables[index.row()]
        return None

    def index(
        self,
        row: int,
        column: int,
        parent: Union[QModelIndex, QPersistentModelIndex] = QModelIndex(),
    ) -> QModelIndex:
        if self.hasIndex(row, column, parent):
            return self.createIndex(row, column)
        return QModelIndex()

    def parent(self, child: QModelIndex) -> QModelIndex:  # type: ignore # Documentation confirms this is correct
        return QModelIndex()


class DuckDBTableModel(QAbstractTableModel):
    def __init__(self, connection: DuckDBPyConnection, table_name: str):
        super().__init__()
        self.connection = connection
        self.table_name = table_name
        self._data: DataType = []
        self.headers: List[str] = []
        self._fetch_data()
        self._sort_column = 0
        self._sort_order = Qt.SortOrder.AscendingOrder
        self._filters: List[str] = [""] * len(self.headers)
        self._filtered_data: DataType = self._data

    def _fetch_data(self) -> None:
        query = f"SELECT * FROM {self.table_name}"
        df: pd.DataFrame = self.connection.execute(query).df()
        self._data = df.values.tolist()
        self.headers = df.columns.tolist()
        self._filtered_data = self._data

    def set_filter(self, column: int, filter_text: str) -> None:
        self.layoutAboutToBeChanged.emit()
        self._filters[column] = filter_text.lower()
        self._apply_filters()
        self.layoutChanged.emit()

    def _apply_filters(self) -> None:
        self._filtered_data = [
            row
            for row in self._data
            if all(
                str(row[col]).lower().find(filter_text) != -1
                for col, filter_text in enumerate(self._filters)
                if filter_text
            )
        ]

    def sort(
        self, column: int, order: Qt.SortOrder = Qt.SortOrder.AscendingOrder
    ) -> None:
        self.layoutAboutToBeChanged.emit()
        self._sort_column = column
        self._sort_order = order
        self._filtered_data.sort(
            key=lambda x: x[column], reverse=(order == Qt.SortOrder.DescendingOrder)
        )
        self.layoutChanged.emit()

    def rowCount(
        self, parent: Union[QModelIndex, QPersistentModelIndex] = QModelIndex()
    ) -> int:
        return len(self._filtered_data)

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
            return str(self._filtered_data[index.row()][index.column()])
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
        self,
        index: Union[QModelIndex, QPersistentModelIndex],
        value: Any,
        role: int = Qt.ItemDataRole.EditRole,
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

    def flags(self, index: Union[QModelIndex, QPersistentModelIndex]) -> Qt.ItemFlag:
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
    result = con.execute("SELECT COUNT(*) FROM test").fetchone()
    if result is not None and result[0] == 0:
        con.execute("INSERT INTO test VALUES (1, 'John'), (2, 'Jane')")

    return con


class TableWidget(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.filter_widget = QWidget(self)
        self.filter_layout = QHBoxLayout(self.filter_widget)
        self.filter_layout.setContentsMargins(0, 0, 0, 0)
        self.table_view = QTableView(self)
        self.layout.addWidget(self.filter_widget)
        self.layout.addWidget(self.table_view)

    def clear_filters(self) -> None:
        while self.filter_layout.count():
            item = self.filter_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def add_filter(self, placeholder: str) -> QLineEdit:
        line_edit = QLineEdit(self.filter_widget)
        line_edit.setPlaceholderText(placeholder)
        self.filter_layout.addWidget(line_edit)
        return line_edit

class MainWindow(QMainWindow):
    def __init__(
        self,
        db_path: str = ":memory:",
        initial_table: Optional[str] = None,
        parent: Optional[QMainWindow] = None,
    ) -> None:
        super().__init__(parent)

        # Connect to DuckDB
        self.con = create_connection(db_path=db_path)

        # Create main widget and layout
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)

        # Create splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Create and set up the sidebar tree view
        self.sidebar = QTreeView()
        self.sidebar_model = TableListModel(self.con)
        self.sidebar.setModel(self.sidebar_model)
        self.sidebar.setHeaderHidden(True)
        self.sidebar.clicked.connect(self.on_sidebar_clicked)

        # Create and set up the table widget
        self.table_widget = TableWidget()
        self.table_widget.table_view.setSortingEnabled(True)

        # Add views to splitter
        splitter.addWidget(self.sidebar)
        splitter.addWidget(self.table_widget)

        # Set splitter sizes
        splitter.setSizes([200, 600])  # Adjust these values as needed

        # Add splitter to main layout
        main_layout.addWidget(splitter)

        # Set central widget
        self.setCentralWidget(main_widget)

        # Initialize filter inputs list
        self.filter_inputs: List[QLineEdit] = []

        # Load the specified table or the first table if it exists
        self.load_initial_table(initial_table)

    def load_initial_table(self, initial_table: Optional[str] = None) -> None:
        if initial_table:
            # Try to load the specified table
            index = self.find_table_index(initial_table)
            if index.isValid():
                self.on_sidebar_clicked(index)
            else:
                print(
                    f"Table '{initial_table}' not found. Loading first available table."
                )
                self.load_first_table()
        else:
            self.load_first_table()

    def find_table_index(self, table_name: str) -> QModelIndex:
        for row in range(self.sidebar_model.rowCount()):
            index = self.sidebar_model.index(row, 0)
            if (
                self.sidebar_model.data(index, Qt.ItemDataRole.DisplayRole)
                == table_name
            ):
                return index
        return QModelIndex()

    def load_first_table(self) -> None:
        if self.sidebar_model.rowCount() > 0:
            first_table_index = self.sidebar_model.index(0, 0)
            self.on_sidebar_clicked(first_table_index)

    def on_sidebar_clicked(self, index: QModelIndex) -> None:
        table_name = self.sidebar_model.data(index, Qt.ItemDataRole.DisplayRole)
        self.table_model = DuckDBTableModel(self.con, table_name)
        self.table_widget.table_view.setModel(self.table_model)
        self.sidebar.setCurrentIndex(index)

        # Clear existing filter inputs
        self.table_widget.clear_filters()
        self.filter_inputs.clear()

        # Create new filter inputs
        for col in range(self.table_model.columnCount()):
            placeholder = f"Filter {self.table_model.headerData(col, Qt.Orientation.Horizontal)}"
            line_edit = self.table_widget.add_filter(placeholder)
            line_edit.textChanged.connect(
                lambda text, column=col: self.apply_filter(text, column)
            )
            self.filter_inputs.append(line_edit)

        # Adjust column widths
        header = self.table_widget.table_view.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

    def apply_filter(self, text: str, column: int) -> None:
        self.table_model.set_filter(column, text)


def main(db_path: str = "duckdb_browser.db", table_name: Optional[str] = None) -> None:
    app = QApplication(sys.argv)
    window = MainWindow(db_path=db_path, initial_table=table_name)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    typer.run(main)
