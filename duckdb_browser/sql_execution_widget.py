from typing import Optional
from PySide6.QtWidgets import (
    QWidget,
    QSplitter,
    QVBoxLayout,
    QTextEdit,
    QPushButton,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QSyntaxHighlighter, QTextCharFormat, QPalette, QFont
from view_table import TableWidget
from duckdb import DuckDBPyConnection
from model_table import DuckDBTableModel
from pygments import lex
from pygments.lexers import SqlLexer
from pygments.token import Token


class SQLSyntaxHighlighter(QSyntaxHighlighter):
    def __init__(self, parent):
        super().__init__(parent)
        self.lexer = SqlLexer()
        self.styles = self.generate_styles()

    def generate_styles(self):
        styles = {}
        styles[Token.Keyword] = self.format_for_token(Token.Keyword, '#007020', 'bold')
        styles[Token.String] = self.format_for_token(Token.String, '#4070a0')
        styles[Token.Number] = self.format_for_token(Token.Number, '#40a070')
        styles[Token.Operator] = self.format_for_token(Token.Operator, '#666666')
        styles[Token.Punctuation] = self.format_for_token(Token.Punctuation, '#666666')
        styles[Token.Comment] = self.format_for_token(Token.Comment, '#60a0b0', 'italic')
        return styles

    def format_for_token(self, token, color, font_style=None):
        text_format = QTextCharFormat()
        text_format.setForeground(QColor(color))
        if font_style == 'bold':
            text_format.setFontWeight(QFont.Bold)
        elif font_style == 'italic':
            text_format.setFontItalic(True)
        return text_format

    def highlightBlock(self, text):
        for token, value in lex(text, self.lexer):
            if token in self.styles:
                self.setFormat(
                    self.currentBlock().position(),
                    len(value),
                    self.styles[token]
                )


class SQLTextEdit(QTextEdit):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.highlighter = SQLSyntaxHighlighter(self.document())
        self.setPlaceholderText("Enter your SQL query here...")

    def set_background_color(self, color: QColor) -> None:
        palette = self.palette()
        palette.setColor(QPalette.Base, color)
        self.setPalette(palette)


class SQLExecutionWidget(QWidget):
    def __init__(
        self, connection: DuckDBPyConnection, parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.connection: DuckDBPyConnection = connection
        self.main_layout: QVBoxLayout = QVBoxLayout(self)
        self.table_widget: TableWidget
        self.text_edit: SQLTextEdit
        self.execute_button: QPushButton
        self.create_content()

    def create_content(self) -> None:
        # Create splitter
        splitter = QSplitter(Qt.Orientation.Vertical)

        # Create and set up the table widget
        self.table_widget = TableWidget()
        self.table_widget.table_view.setSortingEnabled(True)

        # Create and set up the SQLTextEdit
        self.text_edit = SQLTextEdit()

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
        self.text_edit.set_background_color(color)
