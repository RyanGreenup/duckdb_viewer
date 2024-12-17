from PySide6.QtWidgets import (
    QTableView,
    QVBoxLayout,
    QWidget,
    QLineEdit,
    QHeaderView,
)
from PySide6.QtCore import (
    Qt,
    QSize,
    QAbstractItemModel,
    Signal,
)
from PySide6.QtCore import Qt as QtCore
from typing import List, Optional

class CustomHeaderWidget(QWidget):
    filterChanged = Signal(int, str)

    def __init__(self, column: int, column_name: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.column = column
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText(f"Filter {column_name}")
        self.filter_input.textChanged.connect(self.on_filter_changed)
        
        layout.addWidget(self.filter_input)

    def get_filter_input(self) -> QLineEdit:
        return self.filter_input

    def on_filter_changed(self, text: str) -> None:
        self.filterChanged.emit(self.column, text)

class TableWidget(QWidget):
    filterChanged = Signal(int, str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._main_layout = QVBoxLayout(self)
        self.table_view = QTableView(self)
        self.table_view.setHorizontalScrollMode(QTableView.ScrollPerPixel)
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self._main_layout.addWidget(self.table_view)
        self.header_widgets: List[CustomHeaderWidget] = []

    def set_model(self, model: QAbstractItemModel) -> None:
        self.table_view.setModel(model)
        self.setup_header_widgets(model)
        self.adjust_columns()

    def setup_header_widgets(self, model: QAbstractItemModel) -> None:
        header = self.table_view.horizontalHeader()
        self.header_widgets = []
        for col in range(model.columnCount()):
            column_name = model.headerData(col, Qt.Orientation.Horizontal)
            widget = CustomHeaderWidget(col, column_name)
            widget.filterChanged.connect(self.on_filter_changed)
            self.header_widgets.append(widget)
            self.table_view.setIndexWidget(model.index(0, col), widget)

    def on_filter_changed(self, column: int, text: str) -> None:
        self.filterChanged.emit(column, text)

    def adjust_columns(self) -> None:
        header = self.table_view.horizontalHeader()
        for col in range(self.table_view.model().columnCount()):
            header.resizeSection(col, self.calculate_column_width(col))
        self.table_view.setColumnHidden(0, False)  # Ensure the first column is visible

    def calculate_column_width(self, column: int) -> int:
        model = self.table_view.model()
        margin = 10  # Pixels
        max_width = 300  # Maximum column width
        width = max(
            self.table_view.fontMetrics().horizontalAdvance(
                model.headerData(column, Qt.Orientation.Horizontal)
            ),
            *[
                self.table_view.fontMetrics().horizontalAdvance(
                    str(model.index(row, column).data())
                )
                for row in range(min(10, model.rowCount()))
            ]
        )
        return min(width + margin, max_width)

    def clear_filters(self) -> None:
        for widget in self.header_widgets:
            widget.get_filter_input().clear()

    def add_filter_input(self, column: int, placeholder: str) -> Optional[QLineEdit]:
        if 0 <= column < len(self.header_widgets):
            filter_input = self.header_widgets[column].get_filter_input()
            filter_input.setPlaceholderText(placeholder)
            return filter_input
        return None

    def get_main_layout(self) -> QVBoxLayout:
        return self._main_layout

    def display_error(self, error_message: str) -> None:
        from PySide6.QtGui import QStandardItemModel

        error_model = QStandardItemModel(1, 1)
        error_model.setData(
            error_model.index(0, 0), error_message, QtCore.ItemDataRole.DisplayRole
        )
        self.table_view.setModel(error_model)
        self.setup_header_widgets(error_model)
