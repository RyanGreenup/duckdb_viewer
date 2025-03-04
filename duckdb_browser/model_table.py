from typing import List, Union, Optional, Any, Tuple
from PySide6.QtCore import (
    QPersistentModelIndex,
    Qt,
    QAbstractTableModel,
    QModelIndex,
)
from duckdb import DuckDBPyConnection
import pandas as pd

# Custom type for our data
DataType = List[List[Any]]


class DuckDBTableModel(QAbstractTableModel):
    connection: DuckDBPyConnection
    table_name: str
    _data: DataType
    headers: List[Tuple[str, str]]
    _sort_column: int
    _sort_order: Qt.SortOrder
    _filters: List[str]
    _filtered_data: DataType

    def __init__(
        self,
        connection: DuckDBPyConnection,
        table_name: str,
        result: Optional[Any] = None,
    ):
        super().__init__()
        self.connection = connection
        self.table_name = table_name
        self._data = []
        self.headers = []  # (column_name, column_type)
        self._sort_column = 0
        self._sort_order = Qt.SortOrder.AscendingOrder
        self._filters = []
        self._filtered_data = []

        if result is not None:
            self._fetch_data_from_result(result)
        elif table_name:
            self._fetch_data()

    def _fetch_data(self) -> None:
        # Fetch column information
        columns_query = f"PRAGMA table_info('{self.table_name}')"
        columns_info = self.connection.execute(columns_query).fetchall()
        self.headers = [(col[1], col[2]) for col in columns_info]  # (name, type)

        # Fetch data
        query = f"SELECT * FROM {self.table_name}"
        df: pd.DataFrame = self.connection.execute(query).df()
        self._data = df.values.tolist()  # type: ignore
        self._data = [list(row) for row in self._data]  # Ensure each row is a list
        self._filtered_data = [row.copy() for row in self._data]  # Deep copy of _data
        self._filters = [""] * len(self.headers)

    def _fetch_data_from_result(self, result: Any) -> None:
        # Fetch column names and types
        self.headers = [(col[0], str(col[1])) for col in result.description]

        # Fetch data
        fetched_data = result.fetchall()
        self._data = [list(row) for row in fetched_data]  # Convert tuples to lists
        self._filtered_data = self._data

        # Initialize filters
        self._filters = [""] * len(self.headers)

    def set_filter(self, column: int, filter_text: str) -> None:
        self.layoutAboutToBeChanged.emit()
        self._filters[column] = filter_text.lower()
        self._apply_filters()
        self.layoutChanged.emit()

    def clear_all_filters(self) -> None:
        self.layoutAboutToBeChanged.emit()
        self._filters = [""] * len(self.headers)
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
        return len(self._filtered_data) + 1  # +1 for the header row

    def columnCount(
        self, parent: Union[QModelIndex, QPersistentModelIndex] = QModelIndex()
    ) -> int:
        return len(self.headers)

    def data(
        self,
        index: Union[QModelIndex, QPersistentModelIndex],
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if not index.isValid() or index.row() == 0:  # Header row
            return None
        if role == Qt.ItemDataRole.DisplayRole:
            return str(self._filtered_data[index.row() - 1][index.column()])
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
            return f"{self.headers[section][0]}\n({self.headers[section][1]})"
        return None

    def setData(
        self,
        index: Union[QModelIndex, QPersistentModelIndex],
        value: Any,
        role: int = Qt.ItemDataRole.EditRole,
    ) -> bool:
        if role == Qt.ItemDataRole.EditRole and index.row() > 0:
            row = index.row() - 1
            col = index.column()
            column_name = self.headers[col][0]
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
        if index.row() == 0:  # Header row
            return Qt.ItemFlag.ItemIsEnabled
        return (
            Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsSelectable
            | Qt.ItemFlag.ItemIsEditable
        )

    def get_total_row_count(self) -> int:
        return len(self._data)
