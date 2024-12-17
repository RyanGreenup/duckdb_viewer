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
)
from typing import List, Optional


class FilterHeader(QHeaderView):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(Qt.Orientation.Horizontal, parent)
        self.setSectionsClickable(True)
        self.setSortIndicatorShown(True)
        self.filter_widgets: List[QLineEdit] = []  # Initialize the filter_widgets list
        self.setStretchLastSection(True)

    def setFilterWidgets(self, count: int) -> None:
        self.filter_widgets = [QLineEdit(self) for _ in range(count)]
        for widget in self.filter_widgets:
            widget.setParent(self)
        self.adjustPositions()

    def sizeHint(self) -> QSize:
        size = super().sizeHint()
        if self.filter_widgets:
            size.setHeight(size.height() * 2)  # Double the height for header and filter
        return size

    def updateGeometries(self) -> None:
        super().updateGeometries()
        self.adjustPositions()

    def adjustPositions(self) -> None:
        if self.filter_widgets:
            header_height = super().sizeHint().height()
            for index, widget in enumerate(self.filter_widgets):
                widget.setGeometry(
                    self.sectionPosition(index),
                    header_height,
                    self.sectionSize(index),
                    header_height,
                )

    def filterWidget(self, index: int) -> Optional[QLineEdit]:
        if 0 <= index < len(self.filter_widgets):
            return self.filter_widgets[index]
        return None

    def filterText(self, index: int) -> str:
        if 0 <= index < len(self.filter_widgets):
            return self.filter_widgets[index].text()
        return ""

    def clearFilters(self) -> None:
        for widget in self.filter_widgets:
            widget.clear()



class CombinedHeaderWidget(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.filter_header = FilterHeader(self)
        self.filter_header.setFilterWidgets(0)  # Initialize with 0 columns, update later when model is set
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.filter_header)

    def setModel(self, model: QAbstractItemModel) -> None:
        self.filter_header.setModel(model)
        self.filter_header.setFilterWidgets(model.columnCount())

    def setFilterWidgets(self, count: int) -> None:
        self.filter_header.setFilterWidgets(count)

    def filterWidget(self, index: int) -> Optional[QLineEdit]:
        return self.filter_header.filterWidget(index)

    def clearFilters(self) -> None:
        self.filter_header.clearFilters()


class TableWidget(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._main_layout = QVBoxLayout(self)
        self.table_view = QTableView(self)
        self.combined_header = CombinedHeaderWidget(self.table_view)
        self.table_view.setHorizontalHeader(self.combined_header.filter_header)
        self._main_layout.addWidget(self.table_view)

    def set_model(self, model: QAbstractItemModel) -> None:
        self.table_view.setModel(model)
        self.combined_header.setModel(model)

    def clear_filters(self) -> None:
        self.combined_header.clearFilters()

    def add_filter_input(self, column: int, placeholder: str) -> Optional[QLineEdit]:
        filter_widget = self.combined_header.filterWidget(column)
        if filter_widget:
            filter_widget.setPlaceholderText(placeholder)
        return filter_widget

    def get_main_layout(self) -> QVBoxLayout:
        return self._main_layout
