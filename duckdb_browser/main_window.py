from PySide6.QtWidgets import (
    QMainWindow,
    QTreeView,
    QSplitter,
    QVBoxLayout,
    QWidget,
    QLineEdit,
    QAbstractItemView,
)
from typing import List, Optional
from PySide6.QtCore import (
    Qt,
    QModelIndex,
)
import duckdb
from duckdb import DuckDBPyConnection
from views.table_view import TableWidget
from models.table import DuckDBTableModel
from models.sidebar_list import TableListModel


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
        self.table_widget.set_model(self.table_model)

        # Clear existing filter inputs
        self.table_widget.clear_filters()
        self.filter_inputs = []

        # Create new filter inputs
        for col in range(self.table_model.columnCount()):
            column_name, column_type = self.table_model.headers[col]
            placeholder = f"Filter {column_name}"
            line_edit = self.table_widget.add_filter_input(col, placeholder)
            if line_edit:
                line_edit.textChanged.connect(
                    lambda text, column=col: self.apply_filter(text, column)
                )
                self.filter_inputs.append(line_edit)

                if focus_column and column_name == focus_column:
                    line_edit.setFocus()

        # Adjust column widths
        self.table_widget.table_view.resizeColumnsToContents()

        # Enable horizontal scrolling
        self.table_widget.table_view.setHorizontalScrollMode(
            QAbstractItemView.ScrollMode.ScrollPerPixel
        )

        # Update the main layout
        self.table_widget.get_main_layout().update()

    def calculate_column_width(self, column: int) -> int:
        font_metrics = self.table_widget.table_view.fontMetrics()
        header_width = (
            font_metrics.horizontalAdvance(
                self.table_model.headerData(column, Qt.Orientation.Horizontal)
            )
            + 20
        )

        max_content_width = header_width
        for row in range(min(10, self.table_model.rowCount())):  # Check first 10 rows
            index = self.table_model.index(row, column)
            content_width = (
                font_metrics.horizontalAdvance(str(self.table_model.data(index))) + 20
            )
            max_content_width = max(max_content_width, content_width)

        return min(max_content_width, 300)  # Cap width at 300 pixels

    def adjust_column_width(self, index: QModelIndex) -> None:
        self.sidebar.resizeColumnToContents(0)

    def apply_filter(self, text: str, column: int) -> None:
        self.table_model.set_filter(column, text)


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