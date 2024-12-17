import json
from PySide6.QtWidgets import (
    QMainWindow,
    QTreeView,
    QSplitter,
    QVBoxLayout,
    QWidget,
    QLineEdit,
    QAbstractItemView,
    QTabWidget,
    QMenuBar,
    QStatusBar,
    QMenu,
    QMessageBox,
    QFileDialog,
    QTextEdit,
    QDialog,
    QPushButton,
)
from typing import List, Optional, Callable
from PySide6.QtCore import Qt, QModelIndex, Signal
import duckdb
from duckdb import DuckDBPyConnection
from view_table import TableWidget
from model_table import DuckDBTableModel
from model_sidebar_list import TableListModel
from sql_execution_widget import SQLExecutionWidget
from utils_get_schema import get_complete_schema, generate_create_table_statements


class MainWindow(QMainWindow):
    database_changed = Signal(str)

    con: DuckDBPyConnection
    tab_widget: QTabWidget
    tab1: QWidget
    tab1_layout: QVBoxLayout
    tab2: SQLExecutionWidget
    sidebar: QTreeView
    sidebar_model: TableListModel
    table_widget: TableWidget
    filter_inputs: List[QLineEdit]
    table_model: DuckDBTableModel
    status_bar: QStatusBar
    schema_dialog: Optional['SchemaDialog']

    def __init__(
        self,
        db_path: str = ":memory:",
        initial_table: Optional[str] = None,
        parent: Optional[QMainWindow] = None,
        on_database_changed: Optional[Callable[[str], None]] = None,
    ) -> None:
        super().__init__(parent)

        self.db_path = db_path
        if on_database_changed:
            self.database_changed.connect(on_database_changed)

        # Create menu bar
        self.create_menu_bar()

        # Create status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # Connect to DuckDB
        self.con = create_connection(db_path=self.db_path)

        # Create main widget and layout
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)

        # Create tab widget
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        # Create and add the first tab (current layout)
        self.tab1 = QWidget()
        self.tab1_layout = QVBoxLayout(self.tab1)
        self.create_tab1_content()
        self.tab_widget.addTab(self.tab1, "Table View")

        # Create and add the second tab (SQL execution)
        self.tab2 = SQLExecutionWidget(self.con)
        self.tab_widget.addTab(self.tab2, "Execute SQL")

        # Set central widget
        self.setCentralWidget(main_widget)

        # Initialize filter inputs list
        self.filter_inputs = []

        # Load the specified table or the first table if it exists
        self.load_initial_table(initial_table)

    def create_tab1_content(self) -> None:
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

        # Add splitter to tab1 layout
        self.tab1_layout.addWidget(splitter)

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

        # Create new filter inputs for the table widget
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
                if line_edit:
                    line_edit.setFocus()

        # Adjust column widths
        self.table_widget.table_view.resizeColumnsToContents()

        # Enable horizontal scrolling
        self.table_widget.table_view.setHorizontalScrollMode(
            QAbstractItemView.ScrollMode.ScrollPerPixel
        )

        # Update the main layout
        self.table_widget.get_main_layout().update()

        self.status_bar.showMessage(
            f"Loaded {name} with {self.table_model.rowCount()} rows"
        )

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
        filtered_row_count = self.table_model.rowCount()
        total_row_count = self.table_model.get_total_row_count()
        self.status_bar.showMessage(
            f"Showing {filtered_row_count} of {total_row_count} rows"
        )

    def create_menu_bar(self) -> None:
        menu_bar = QMenuBar(self)
        self.setMenuBar(menu_bar)

        # File menu
        file_menu = QMenu("&File", self)
        menu_bar.addMenu(file_menu)

        # Add actions to File menu
        open_db_action = file_menu.addAction("&Open Database")
        open_db_action.triggered.connect(self.open_database)

        show_schema_action = file_menu.addAction("Show &Schema")
        show_schema_action.triggered.connect(self.show_schema_dialog)

        show_sql_schema_action = file_menu.addAction("Show &SQL Schema")
        show_sql_schema_action.triggered.connect(self.show_sql_schema_dialog)

        exit_action = file_menu.addAction("E&xit")
        exit_action.triggered.connect(self.close)

        # Edit menu
        edit_menu = QMenu("&Edit", self)
        menu_bar.addMenu(edit_menu)

        # Add actions to Edit menu
        clear_filters_action = edit_menu.addAction("&Clear Filters")
        clear_filters_action.triggered.connect(self.clear_all_filters)

        # Help menu
        help_menu = QMenu("&Help", self)
        menu_bar.addMenu(help_menu)

        # Add actions to Help menu
        about_action = help_menu.addAction("&About")
        about_action.triggered.connect(self.show_about_dialog)

    def open_database(self) -> None:
        file_dialog = QFileDialog(self)
        file_dialog.setNameFilter("DuckDB files (*.db);;All files (*)")
        if file_dialog.exec():
            selected_files = file_dialog.selectedFiles()
            if selected_files:
                new_db_path = selected_files[0]
                self.db_path = new_db_path
                self.con.close()
                self.con = create_connection(db_path=self.db_path)
                self.sidebar_model = TableListModel(self.con)
                self.sidebar.setModel(self.sidebar_model)
                self.load_first_table()
                self.status_bar.showMessage(f"Opened database: {self.db_path}")
                self.database_changed.emit(self.db_path)

    def clear_all_filters(self) -> None:
        self.table_widget.clear_filters()
        for filter_input in self.filter_inputs:
            filter_input.clear()
        if hasattr(self.table_model, "clear_all_filters"):
            self.table_model.clear_all_filters()
        else:
            # Fallback if clear_all_filters is not implemented
            for column in range(self.table_model.columnCount()):
                self.table_model.set_filter(column, "")

    def show_about_dialog(self) -> None:
        QMessageBox.about(
            self,
            "About DuckDB Browser",
            "DuckDB Browser is a simple GUI for browsing DuckDB databases.",
        )

    def show_schema_dialog(self) -> None:
        if not hasattr(self, 'schema_dialog') or self.schema_dialog is None:
            self.schema_dialog = SchemaDialog(self, self.con)
        self.schema_dialog.show_schema()

    def show_sql_schema_dialog(self) -> None:
        if not hasattr(self, 'schema_dialog') or self.schema_dialog is None:
            self.schema_dialog = SchemaDialog(self, self.con)
        self.schema_dialog.show_sql_schema()


class SchemaDialog(QDialog):
    con: DuckDBPyConnection
    def __init__(
        self, parent: Optional[QWidget] = None, con: DuckDBPyConnection = None
    ):
        super().__init__(parent)
        self.con = con
        self.setMinimumSize(600, 400)

        layout = QVBoxLayout(self)

        self.text_edit = QTextEdit(self)
        self.text_edit.setReadOnly(True)
        layout.addWidget(self.text_edit)

        ok_button = QPushButton("OK", self)
        ok_button.clicked.connect(self.accept)
        layout.addWidget(ok_button)

    def show_schema(self) -> None:
        if not self.con:
            QMessageBox.warning(
                self,
                "No Database Open",
                "Please open a database before viewing the schema.",
            )
            return

        schema = get_complete_schema(self.con)
        schema_str = json.dumps(schema, indent=2)

        self.setWindowTitle("Database Schema")
        self.text_edit.setPlainText(f"Here's the complete schema of the database:\n\n{schema_str}")
        self.exec()

    def show_sql_schema(self) -> None:
        if not self.con:
            QMessageBox.warning(
                self,
                "No Database Open",
                "Please open a database before viewing the schema.",
            )
            return

        schema = get_complete_schema(self.con)
        create_statements = generate_create_table_statements(schema)

        self.setWindowTitle("SQL Schema")
        self.text_edit.setPlainText(f"Here are the CREATE TABLE statements for the database:\n\n{'\n\n'.join(create_statements)}")
        self.exec()


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
