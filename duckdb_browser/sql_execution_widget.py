from typing import Optional, List
from PySide6.QtWidgets import (
    QWidget,
    QSplitter,
    QVBoxLayout,
    QTextEdit,
    QPushButton,
    QCompleter,
)
from PySide6.QtCore import Qt, QStringListModel
from PySide6.QtCore import QAbstractItemModel
from PySide6.QtGui import QKeyEvent
from PySide6.QtGui import (
    QColor,
    QSyntaxHighlighter,
    QTextCharFormat,
    QPalette,
    QFont,
    QTextCursor,
)
from enum import Enum
from view_table import TableWidget
from duckdb import DuckDBPyConnection
from model_table import DuckDBTableModel
from pygments import lex
from pygments.lexers import SqlLexer


class FontStyle(Enum):
    NORMAL = 1
    BOLD = 2
    ITALIC = 3


class SQLSyntaxHighlighter(QSyntaxHighlighter):
    def __init__(self, parent: QTextEdit) -> None:
        super().__init__(parent)
        self.lexer = SqlLexer()
        self.styles: dict[str, QTextCharFormat] = self.generate_styles()

    def generate_styles(self) -> dict[str, QTextCharFormat]:
        styles: dict[str, QTextCharFormat] = {}
        styles["Keyword"] = self.format_for_token("#007020", FontStyle.BOLD)
        styles["String"] = self.format_for_token("#4070a0")
        styles["Number"] = self.format_for_token("#40a070")
        styles["Operator"] = self.format_for_token("#666666")
        styles["Punctuation"] = self.format_for_token("#666666")
        styles["Comment"] = self.format_for_token("#60a0b0", FontStyle.ITALIC)
        return styles

    def format_for_token(
        self, color: str, font_style: FontStyle = FontStyle.NORMAL
    ) -> QTextCharFormat:
        text_format = QTextCharFormat()
        text_format.setForeground(QColor(color))
        if font_style == FontStyle.BOLD:
            text_format.setFontWeight(QFont.Weight.Bold)
        elif font_style == FontStyle.ITALIC:
            text_format.setFontItalic(True)
        return text_format

    def highlightBlock(self, text: str) -> None:
        for token_type, value in lex(text, self.lexer):
            token_str = str(token_type)
            if token_str.split(".")[-1] in self.styles:
                self.setFormat(
                    self.currentBlock().position(),
                    len(value),
                    self.styles[token_str.split(".")[-1]],
                )


class SQLCompleter(QCompleter):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setModel(QStringListModel())
        self.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)

    def update_completions(self, table_names: List[str]) -> None:
        completions = [
            "SELECT",
            "FROM",
            "WHERE",
            "GROUP BY",
            "HAVING",
            "ORDER BY",
            "INSERT INTO",
            "UPDATE",
            "DELETE",
            "CREATE TABLE",
            "ALTER TABLE",
            "DROP TABLE",
            "JOIN",
            "INNER JOIN",
            "LEFT JOIN",
            "RIGHT JOIN",
        ] + table_names
        model = self.model()
        if isinstance(model, QStringListModel):
            model.setStringList(completions)
        else:
            new_model = QStringListModel(completions)
            self.setModel(new_model)

    def model(self) -> QAbstractItemModel:
        model = super().model()
        assert isinstance(model, QAbstractItemModel)
        return model


class SQLTextEdit(QTextEdit):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.highlighter = SQLSyntaxHighlighter(self)
        self.setPlaceholderText("Enter your SQL query here...")
        self.completer = SQLCompleter(self)
        self.completer.setWidget(self)
        self.completer.activated.connect(self.insert_completion)

    def set_background_color(self, color: QColor) -> None:
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Base, color)
        self.setPalette(palette)

    def keyPressEvent(self, e: QKeyEvent) -> None:
        if self.completer.popup().isVisible():
            if e.key() in (Qt.Key.Key_Enter, Qt.Key.Key_Return, Qt.Key.Key_Tab):
                e.ignore()
                return
            elif e.key() == Qt.Key.Key_N and e.modifiers() & Qt.KeyboardModifier.ControlModifier:
                self.completer.setCurrentRow(self.completer.currentRow() + 1)
                self.completer.popup().setCurrentIndex(self.completer.currentIndex())
                e.accept()
                return
            elif e.key() == Qt.Key.Key_P and e.modifiers() & Qt.KeyboardModifier.ControlModifier:
                self.completer.setCurrentRow(self.completer.currentRow() - 1)
                self.completer.popup().setCurrentIndex(self.completer.currentIndex())
                e.accept()
                return

        super().keyPressEvent(e)

        ctrl_or_shift = event.modifiers() & (Qt.ControlModifier | Qt.ShiftModifier)
        if ctrl_or_shift and event.text() == "":
            return

        completion_prefix = self.text_under_cursor()
        if completion_prefix != self.completer.completionPrefix():
            self.completer.setCompletionPrefix(completion_prefix)
            self.completer.popup().setCurrentIndex(
                self.completer.completionModel().index(0, 0)
            )

        cr = self.cursorRect()
        cr.setWidth(
            self.completer.popup().sizeHintForColumn(0)
            + self.completer.popup().verticalScrollBar().sizeHint().width()
        )
        self.completer.complete(cr)

    def text_under_cursor(self):
        tc = self.textCursor()
        tc.select(QTextCursor.WordUnderCursor)
        return tc.selectedText()

    def insert_completion(self, completion):
        tc = self.textCursor()
        extra = len(completion) - len(self.completer.completionPrefix())
        tc.movePosition(QTextCursor.Left)
        tc.movePosition(QTextCursor.EndOfWord)
        tc.insertText(completion[-extra:])
        self.setTextCursor(tc)


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
        self.update_completions()

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

    def update_completions(self):
        table_names = self.connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        table_names = [name[0] for name in table_names]
        self.text_edit.completer.update_completions(table_names)

    def execute_sql(self, query: str) -> None:
        try:
            result = self.connection.execute(query)
            model = DuckDBTableModel(self.connection, "", result=result)
            self.table_widget.set_model(model)
            self.highlight_sql(success=True)
            self.update_completions()  # Update completions after successful query execution
        except Exception as e:
            error_message = f"Error executing SQL: {str(e)}"
            self.table_widget.display_error(error_message)
            self.highlight_sql(success=False)

    def highlight_sql(self, success: bool) -> None:
        color = QColor(200, 255, 200) if success else QColor(255, 200, 200)
        self.text_edit.set_background_color(color)
