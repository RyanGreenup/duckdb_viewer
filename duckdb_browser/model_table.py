from typing import List, Union
from PySide6.QtCore import (
    QPersistentModelIndex,
    Qt,
    QAbstractTableModel,
    QModelIndex,
)
from typing import Any, Tuple
from duckdb import DuckDBPyConnection
import pandas as pd

# Custom type for our data
DataType = List[List[Any]]


class DuckDBTableModel(QAbstractTableModel):
    def __init__(self, connection: DuckDBPyConnection, table_name: str):
        super().__init__()
        self.connection = connection
        self.table_name = table_name
        self._data: DataType = []
        self.headers: List[Tuple[str, str]] = []  # (column_name, column_type)
        self._sort_column = 0
        self._sort_order = Qt.SortOrder.AscendingOrder
        self._filters: List[str] = []
        self._filtered_data: DataType = []
        
        if table_name:
            self._fetch_data()

    def _fetch_data(self) -> None:
        # Fetch column information
        columns_query = f"PRAGMA table_info('{self.table_name}')"
        columns_info = self.connection.execute(columns_query).fetchall()
        self.headers = [(col[1], col[2]) for col in columns_info]  # (name, type)

        # Fetch data
        query = f"SELECT * FROM {self.table_name}"
        df: pd.DataFrame = self.connection.execute(query).df()
        self._data = df.values.tolist()
        self._filtered_data = self._data
        self._filters = [""] * len(self.headers)

    def set_data_from_result(self, result) -> None:
        self.layoutAboutToBeChanged.emit()
        # Fetch column names and types
        self.headers = [(col[0], str(col[1])) for col in result.description]
        
        # Fetch data
        self._data = result.fetchall()
        self._filtered_data = self._data
        
        # Initialize filters
        self._filters = [""] * len(self.headers)
        self.layoutChanged.emit()

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
            return f"{self.headers[section][0]}\n({self.headers[section][1]})"
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
