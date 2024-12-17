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
from typing import List, Optional, Union, cast, overload
from PySide6.QtCore import (
    QPersistentModelIndex,
    Qt,
    QAbstractTableModel,
    QModelIndex,
    QAbstractItemModel,
    QObject,
)
from typing import Any, Tuple
import duckdb
from duckdb import DuckDBPyConnection
import typer
import pandas as pd

# Custom type for our data
DataType = List[List[Any]]


class DatabaseItem:
    def __init__(
        self, name: str, item_type: str, parent: Optional["DatabaseItem"] = None
    ):
        self.name = name
        self.type = item_type
        self.parent = parent
        self.children: List["DatabaseItem"] = []

    def add_child(self, child: "DatabaseItem") -> None:
        self.children.append(child)

    def child_count(self) -> int:
        return len(self.children)

    def row(self) -> int:
        if self.parent:
            return self.parent.children.index(self)
        return 0


class TableListModel(QAbstractItemModel):
    def __init__(self, connection: DuckDBPyConnection):
        super().__init__()
        self.connection = connection
        self.root = DatabaseItem("Database", "root")
        self.tables_item = DatabaseItem("Tables", "category", self.root)
        self.views_item = DatabaseItem("Views", "category", self.root)
        self.root.add_child(self.tables_item)
        self.root.add_child(self.views_item)
        self._fetch_structure()

    def _fetch_structure(self) -> None:
        # Fetch tables and views
        query = """
        SELECT type, name
        FROM sqlite_master
        WHERE type IN ('table', 'view')
        ORDER BY type, name
        """
        for item_type, name in self.connection.execute(query).fetchall():
            parent_item = self.tables_item if item_type == "table" else self.views_item
            item = DatabaseItem(name, item_type, parent_item)
            parent_item.add_child(item)

            # Fetch columns for each table/view
            columns_query = f"PRAGMA table_info('{name}')"
            for column_info in self.connection.execute(columns_query).fetchall():
                column_name = column_info[1]
                column_type = column_info[2]
                column_item = DatabaseItem(
                    f"{column_name} ({column_type})", "column", item
                )
                item.add_child(column_item)

    def rowCount(
        self, parent: Union[QModelIndex, QPersistentModelIndex] = QModelIndex()
    ) -> int:
        if parent.isValid():
            item: DatabaseItem = parent.internalPointer()
            return item.child_count()
        return self.root.child_count()

    def columnCount(
        self, parent: Union[QModelIndex, QPersistentModelIndex] = QModelIndex()
    ) -> int:
        return 1

    def data(
        self,
        index: Union[QModelIndex, QPersistentModelIndex],
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if not index.isValid():
            return None

        item = index.internalPointer()

        if role == Qt.ItemDataRole.DisplayRole:
            return item.name
        elif role == Qt.ItemDataRole.UserRole:
            return item.type

        return None

    def index(
        self,
        row: int,
        column: int,
        parent: Union[QModelIndex, QPersistentModelIndex] = QModelIndex(),
    ) -> QModelIndex:
        if not self.hasIndex(row, column, parent):
            return QModelIndex()

        if not parent.isValid():
            parent_item = self.root
        else:
            parent_item = cast(DatabaseItem, parent.internalPointer())

        child_item = parent_item.children[row]
        if child_item:
            return self.createIndex(row, column, child_item)
        return QModelIndex()

    @overload
    def parent(self) -> QObject: ...

    @overload
    def parent(
        self, child: Union[QModelIndex, QPersistentModelIndex]
    ) -> QModelIndex: ...

    def parent(
        self, child: Union[QModelIndex, QPersistentModelIndex, None] = None
    ) -> Union[QObject, QModelIndex]:
        if child is None:
            return super().parent()

        if not child.isValid():
            return QModelIndex()

        child_item: DatabaseItem = child.internalPointer()
        parent_item = child_item.parent

        if parent_item == self.root:
            return QModelIndex()

        return self.createIndex(parent_item.row(), 0, parent_item)

    def get_item_info(
        self, index: Union[QModelIndex, QPersistentModelIndex]
    ) -> Tuple[str, str, Optional[str]]:
        item = index.internalPointer()
        if item.type == "column":
            table_name = item.parent.name
            column_name = item.name.split()[0]  # Remove the type information
            return item.type, table_name, column_name
        return item.type, item.name, None


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
        self._main_layout = QVBoxLayout(self)
        self.filter_widget = QWidget(self)
        self.filter_layout = QHBoxLayout(self.filter_widget)
        self.filter_layout.setContentsMargins(0, 0, 0, 0)
        self.table_view = QTableView(self)
        self._main_layout.addWidget(self.filter_widget)
        self._main_layout.addWidget(self.table_view)

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

    def get_main_layout(self) -> QVBoxLayout:
        return self._main_layout


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
        self.sidebar.expanded.connect(self.adjust_column_width)

        # Expand the "Tables" and "Views" items by default
        self.sidebar.expand(self.sidebar_model.index(0, 0, QModelIndex()))
        self.sidebar.expand(self.sidebar_model.index(1, 0, QModelIndex()))

        # Create and set up the table widget
        self.table_widget = TableWidget()
        self.table_widget.table_view.setSortingEnabled(True)

        # Add views to splitter
        splitter.addWidget(self.sidebar)
        splitter.addWidget(self.table_widget)

        # Set splitter sizes
        splitter.setSizes([200, 600])  # Adjust these values as needed
        splitter.setHandleWidth(20)

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
        for category_row in range(self.sidebar_model.rowCount()):
            category_index = self.sidebar_model.index(category_row, 0)
            for row in range(self.sidebar_model.rowCount(category_index)):
                index = self.sidebar_model.index(row, 0, category_index)
                if (
                    self.sidebar_model.data(index, Qt.ItemDataRole.DisplayRole)
                    == table_name
                ):
                    return index
        return QModelIndex()

    def load_first_table(self) -> None:
        tables_index = self.sidebar_model.index(0, 0, QModelIndex())
        if self.sidebar_model.rowCount(tables_index) > 0:
            first_table_index = self.sidebar_model.index(0, 0, tables_index)
            self.on_sidebar_clicked(first_table_index)

    def on_sidebar_clicked(self, index: QModelIndex) -> None:
        item_type, item_name, column_name = self.sidebar_model.get_item_info(index)

        if item_type in ("table", "view"):
            self.load_table_or_view(item_name)
        elif item_type == "column":
            self.load_table_or_view(item_name, focus_column=column_name)
        # Ignore clicks on category items ("Tables" and "Views")

    def load_table_or_view(self, name: str, focus_column: Optional[str] = None) -> None:
        self.table_model = DuckDBTableModel(self.con, name)
        self.table_widget.table_view.setModel(self.table_model)

        # Clear existing filter inputs
        self.table_widget.clear_filters()
        self.filter_inputs.clear()

        # Create new filter inputs
        for col in range(self.table_model.columnCount()):
            column_name = self.table_model.headerData(col, Qt.Orientation.Horizontal)
            placeholder = f"Filter {column_name}"
            line_edit = self.table_widget.add_filter(placeholder)
            line_edit.textChanged.connect(
                lambda text, column=col: self.apply_filter(text, column)
            )
            self.filter_inputs.append(line_edit)

            if focus_column and column_name == focus_column:
                line_edit.setFocus()

        # Adjust column widths
        header = self.table_widget.table_view.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        # Update the main layout
        self.table_widget.get_main_layout().update()

    def adjust_column_width(self, index: QModelIndex) -> None:
        self.sidebar.resizeColumnToContents(0)

    def apply_filter(self, text: str, column: int) -> None:
        self.table_model.set_filter(column, text)


def main(db_path: str = "duckdb_browser.db", table_name: Optional[str] = None) -> None:
    app = QApplication(sys.argv)
    window = MainWindow(db_path=db_path, initial_table=table_name)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    typer.run(main)


# Footnotes
# [fn_QModelIndex.parent]
# This matches the documentation
# An issue with pyright probably
# https://doc.qt.io/qtforpython-6/PySide6/QtCore/QAbstractItemModel.html#PySide6.QtCore.QAbstractItemModel.parent
