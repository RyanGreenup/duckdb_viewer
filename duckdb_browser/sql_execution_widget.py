from PySide6.QtWidgets import (
    QWidget,
    QSplitter,
    QVBoxLayout,
    QPlainTextEdit,
    QPushButton,
)
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

        # Create execute button
        self.execute_button = QPushButton("Execute Query")
        self.execute_button.clicked.connect(self.on_execute_clicked)

        # Create a widget to hold the text edit and button
        input_widget = QWidget()
        input_layout = QVBoxLayout(input_widget)
        input_layout.addWidget(self.text_edit)
        input_layout.addWidget(self.execute_button)

        # Add widgets to splitter
        splitter.addWidget(input_widget)
        splitter.addWidget(self.table_widget)

        # Set splitter sizes
        splitter.setSizes([200, 400])  # Adjust these values as needed
        splitter.setHandleWidth(20)

        # Add splitter to layout
        self.layout.addWidget(splitter)

    def on_execute_clicked(self) -> None:
        query = self.text_edit.toPlainText()
        self.execute_sql(query)

    def execute_sql(self, query: str) -> None:
        try:
            result = self.connection.execute(query)
            model = DuckDBTableModel(self.connection, "", result=result)
            self.table_widget.set_model(model)
        except Exception as e:
            # Handle the error (e.g., show it in the table view or in a message box)
            print(f"Error executing SQL: {e}")
