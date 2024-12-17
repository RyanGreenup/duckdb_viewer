from PySide6.QtWidgets import (
    QTableView,
    QVBoxLayout,
    QWidget,
    QLineEdit,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QStyleOptionFrame,
    QStyle,
    QCommonStyle,
)
from PySide6.QtCore import (
    Qt,
    QSize,
    QAbstractItemModel,
    Signal,
)
from PySide6.QtGui import QFont, QColor, QPalette, QPainter
from PySide6.QtCore import Qt as QtCore
from typing import List, Optional

class CustomHeaderWidget(QWidget):
    filterChanged = Signal(int, str)

    def __init__(self, column: int, column_name: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.column = column
        self.setAutoFillBackground(True)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)
        
        # Add column name label
        label = QLabel(column_name)
        label.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setBold(True)
        label.setFont(font)
        layout.addWidget(label)
        
        # Create a horizontal layout for the filter input and icon
        filter_layout = QHBoxLayout()
        filter_layout.setContentsMargins(0, 0, 0, 0)
        filter_layout.setSpacing(4)
        
        # Add filter icon (you can replace this with an actual icon)
        filter_icon = QLabel("🔍")
        filter_layout.addWidget(filter_icon)
        
        # Add filter input
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Filter")
        self.filter_input.textChanged.connect(self.on_filter_changed)
        self.style_filter_input()
        filter_layout.addWidget(self.filter_input)
        
        layout.addLayout(filter_layout)

    def style_filter_input(self):
        # Use QStyle to set the look of the QLineEdit
        option = QStyleOptionFrame()
        option.initFrom(self.filter_input)
        option.state |= QStyle.State_Sunken
        option.features = QStyleOptionFrame.None_
        option.lineWidth = 1
        option.midLineWidth = 0

        # Set the frame style
        self.filter_input.setFrame(True)
        self.filter_input.setStyle(QCommonStyle())
        self.filter_input.style().drawPrimitive(QStyle.PE_PanelLineEdit, option, QPainter(self.filter_input), self.filter_input)

        # Set colors
        palette = self.filter_input.palette()
        palette.setColor(QPalette.Base, QColor("#f8f8f8"))
        palette.setColor(QPalette.Text, QColor("#000000"))
        self.filter_input.setPalette(palette)

        # Set margins and padding
        self.filter_input.setTextMargins(4, 2, 4, 2)

    def get_filter_input(self) -> QLineEdit:
        return self.filter_input

    def on_filter_changed(self, text: str) -> None:
        self.filterChanged.emit(self.column, text)

class TableWidget(QWidget):
    filterChanged = Signal(int, str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.setSpacing(0)
        self.table_view = QTableView(self)
        self.table_view.setHorizontalScrollMode(QTableView.ScrollPerPixel)
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table_view.verticalHeader().setVisible(False)  # Hide vertical header
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
            header.setSectionResizeMode(col, QHeaderView.Fixed)
            header.setMinimumSectionSize(100)  # Set a minimum width for columns
            self.table_view.setIndexWidget(model.index(0, col), widget)
        
        # Adjust the height of the first row to accommodate the header widgets
        self.table_view.setRowHeight(0, 60)

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
