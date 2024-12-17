from PySide6.QtWidgets import QWidget, QSplitter, QVBoxLayout, QPlainTextEdit
from PySide6.QtCore import Qt
from view_table import TableWidget
from duckdb import DuckDBPyConnection
from model_table import DuckDBTableModel

class SQLExecutionWidget(QWidget):
    def __init__(self, connection: DuckDBPyConnection, parent: QWidget = None):
        super().__init__(parent)
        self.connection = connection
        self.layout = QVBoxLayout(self)
        self.create_content()

    def create_content(self) -> None:
        # Create splitter
        splitter = QSplitter(Qt.Orientation.Vertical)

        # Create and set up the table widget
        self.table_widget = TableWidget()
        self.table_widget.table_view.setSortingEnabled(True)

        # Create and set up the QPlainTextEdit
        self.text_edit = QPlainTextEdit()
        self.text_edit.setPlaceholderText("Enter your SQL query here...")

        # Add widgets to splitter
        splitter.addWidget(self.text_edit)
        splitter.addWidget(self.table_widget)

        # Set splitter sizes
        splitter.setSizes([200, 400])  # Adjust these values as needed
        splitter.setHandleWidth(20)

        # Add splitter to layout
        self.layout.addWidget(splitter)

    def execute_sql(self, query: str) -> None:
        try:
            result = self.connection.execute(query)
            model = DuckDBTableModel(self.connection, "", result)
            self.table_widget.set_model(model)
        except Exception as e:
            # Handle the error (e.g., show it in the table view or in a message box)
            print(f"Error executing SQL: {e}")
