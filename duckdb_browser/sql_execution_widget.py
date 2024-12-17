from typing import Optional
from PySide6.QtWidgets import (
    QWidget,
    QSplitter,
    QVBoxLayout,
    QTextEdit,
    QPushButton,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtGui import QColor
from view_table import TableWidget
from duckdb import DuckDBPyConnection
from model_table import DuckDBTableModel


class SQLExecutionWidget(QWidget):
    def __init__(
        self, connection: DuckDBPyConnection, parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.connection: DuckDBPyConnection = connection
        self.main_layout: QVBoxLayout = QVBoxLayout(self)
        self.table_widget: TableWidget
        self.text_edit: QTextEdit
        self.execute_button: QPushButton
        self.create_content()

    def create_content(self) -> None:
        # Create splitter
        splitter = QSplitter(Qt.Orientation.Vertical)

        # Create and set up the table widget
        self.table_widget = TableWidget()
        self.table_widget.table_view.setSortingEnabled(True)

        # Create and set up the QTextEdit
        self.text_edit = QTextEdit()
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
        self.main_layout.addWidget(splitter)

    def on_execute_clicked(self) -> None:
        query = self.text_edit.toPlainText()
        self.execute_sql(query)

    def execute_sql(self, query: str) -> None:
        try:
            result = self.connection.execute(query)
            model = DuckDBTableModel(self.connection, "", result=result)
            self.table_widget.set_model(model)
            self.highlight_sql(success=True)
        except Exception as e:
            error_message = f"Error executing SQL: {str(e)}"
            self.table_widget.display_error(error_message)
            self.highlight_sql(success=False)

    def highlight_sql(self, success: bool) -> None:
        color = QColor(200, 255, 200) if success else QColor(255, 200, 200)
        self.text_edit.setStyleSheet(f"background-color: {color.name()};")
