from PySide6.QtWidgets import (
    QTableView,
    QVBoxLayout,
    QWidget,
    QLineEdit,
    QHeaderView,
)
from PySide6.QtCore import (
    Qt,
)



class FilterHeader(QHeaderView):
    def __init__(self, parent=None):
        super().__init__(Qt.Orientation.Horizontal, parent)
        self.setSectionsClickable(True)
        self.setSortIndicatorShown(True)
        self.filter_widgets = []  # Initialize filter_widgets here

    def setFilterWidgets(self, count):
        self.filter_widgets = [QLineEdit(self) for _ in range(count)]
        for widget in self.filter_widgets:
            widget.setParent(self)
        self.adjustPositions()

    def filterWidget(self, index):
        if 0 <= index < len(self.filter_widgets):
            return self.filter_widgets[index]
        return None

    def sizeHint(self):
        size = super().sizeHint()
        if self.filter_widgets:
            size.setHeight(size.height() + self.filter_widgets[0].sizeHint().height())
        return size

    def updateGeometries(self):
        super().updateGeometries()
        self.adjustPositions()

    def adjustPositions(self):
        if hasattr(self, 'filter_widgets') and self.filter_widgets:
            for index, widget in enumerate(self.filter_widgets):
                widget.setGeometry(
                    self.sectionPosition(index),
                    self.height() - widget.height(),
                    self.sectionSize(index),
                    widget.height()
                )

    def filterText(self, index):
        if 0 <= index < len(self.filter_widgets):
            return self.filter_widgets[index].text()
        return ""

    def clearFilters(self):
        for widget in self.filter_widgets:
            widget.clear()

class TableHeader(QHeaderView):
    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        self.setSectionsClickable(True)
        self.setSortIndicatorShown(True)

    def sizeHint(self):
        size = super().sizeHint()
        if self.orientation() == Qt.Orientation.Horizontal:
            size.setHeight(size.height() * 2)  # Double the height for two lines
        return size

class CombinedHeaderWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.table_header = TableHeader(Qt.Orientation.Horizontal)
        self.filter_header = FilterHeader()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.table_header)
        layout.addWidget(self.filter_header)

    def setModel(self, model):
        self.table_header.setModel(model)
        self.filter_header.setModel(model)
        self.filter_header.setFilterWidgets(model.columnCount())

    def setFilterWidgets(self, count):
        self.filter_header.setFilterWidgets(count)

    def filterWidget(self, index):
        return self.filter_header.filterWidget(index)

    def clearFilters(self):
        self.filter_header.clearFilters()

class TableWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._main_layout = QVBoxLayout(self)
        self.table_view = QTableView(self)
        self.combined_header = CombinedHeaderWidget(self.table_view)
        self.table_view.setHorizontalHeader(self.combined_header.table_header)
        self.table_view.setVerticalHeader(TableHeader(Qt.Orientation.Vertical, self.table_view))
        self._main_layout.addWidget(self.table_view)

    def set_model(self, model):
        self.table_view.setModel(model)
        self.combined_header.setModel(model)

    def clear_filters(self):
        self.combined_header.clearFilters()

    def add_filter_input(self, column, placeholder):
        filter_widget = self.combined_header.filterWidget(column)
        if filter_widget:
            filter_widget.setPlaceholderText(placeholder)
        return filter_widget

    def get_main_layout(self):
        return self._main_layout

from typing import Optional, List
from PySide6.QtWidgets import QWidget, QVBoxLayout, QTableView, QLineEdit
from PySide6.QtCore import Qt
from models.table import DuckDBTableModel

class TableWidget(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._main_layout = QVBoxLayout(self)
        self.table_view = QTableView(self)
        self._main_layout.addWidget(self.table_view)
        self.filter_inputs: List[QLineEdit] = []

    def set_model(self, model: DuckDBTableModel) -> None:
        self.table_view.setModel(model)

    def get_model(self) -> Optional[DuckDBTableModel]:
        model = self.table_view.model()
        return model if isinstance(model, DuckDBTableModel) else None

    def clear_filters(self) -> None:
        for filter_input in self.filter_inputs:
            filter_input.deleteLater()
        self.filter_inputs.clear()

    def add_filter_input(self, column: int, placeholder: str) -> QLineEdit:
        filter_input = QLineEdit(self)
        filter_input.setPlaceholderText(placeholder)
        self._main_layout.insertWidget(column, filter_input)
        self.filter_inputs.append(filter_input)
        return filter_input

    def get_main_layout(self) -> QVBoxLayout:
        return self._main_layout
