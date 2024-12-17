from PySide6.QtWidgets import (
    QTableView,
    QVBoxLayout,
    QWidget,
    QLineEdit,
    QHeaderView,
    QLabel,
)
from PySide6.QtCore import (
    Qt,
    QSize,
    QAbstractItemModel,
)
from PySide6.QtCore import Qt as QtCore
from typing import List, Optional


class CustomHeaderWidget(QWidget):
    def __init__(self, column_name: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        
        self.label = QLabel(column_name)
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText(f"Filter {column_name}")
        
        layout.addWidget(self.label)
        layout.addWidget(self.filter_input)

    def get_filter_input(self) -> QLineEdit:
        return self.filter_input


class TableWidget(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._main_layout = QVBoxLayout(self)
        self.table_view = QTableView(self)
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._main_layout.addWidget(self.table_view)
        self.header_widgets: List[CustomHeaderWidget] = []

    def set_model(self, model: QAbstractItemModel) -> None:
        self.table_view.setModel(model)
        self.setup_header_widgets(model)

    def setup_header_widgets(self, model: QAbstractItemModel) -> None:
        header = self.table_view.horizontalHeader()
        self.header_widgets = []
        for col in range(model.columnCount()):
            column_name = model.headerData(col, Qt.Orientation.Horizontal)
            widget = CustomHeaderWidget(column_name)
            self.header_widgets.append(widget)
            header.setSectionResizeMode(col, QHeaderView.Stretch)
            self.table_view.setIndexWidget(model.index(0, col), widget)

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
