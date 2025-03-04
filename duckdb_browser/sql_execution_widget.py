from typing import Optional, List
from PySide6.QtWidgets import (
    QWidget,
    QSplitter,
    QVBoxLayout,
    QTextEdit,
    QPushButton,
    QCompleter,
)
from PySide6.QtCore import Qt
from utils_get_schema import get_complete_schema
from PySide6.QtGui import QKeySequence, QShortcut, QTextDocument
from PySide6.QtCore import QStringListModel
from PySide6.QtCore import QAbstractItemModel
from plotting_widget import PlottingWidget
import pandas as pd
from PySide6.QtGui import (
    QKeyEvent,
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
        block_start = self.currentBlock().position()
        current_position = 0
        for token, value in lex(text, self.lexer):
            token_str = str(token)
            style_key = token_str.split(".")[-1]
            if style_key in self.styles:
                start = block_start + current_position
                length = len(value)
                self.setFormat(start, length, self.styles[style_key])
            current_position += len(value)


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

    def setDocument(self, document: QTextDocument) -> None:
        super().setDocument(document)
        self.highlighter.setDocument(document)

    def set_background_color(self, color: QColor) -> None:
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Base, color)
        self.setPalette(palette)

    def keyPressEvent(self, e: QKeyEvent) -> None:
        if self.completer.popup().isVisible():
            if e.key() in (Qt.Key.Key_Enter, Qt.Key.Key_Return, Qt.Key.Key_Tab):
                e.ignore()
                return
            elif (
                e.key() == Qt.Key.Key_N
                and e.modifiers() & Qt.KeyboardModifier.ControlModifier
            ):
                self.completer.setCurrentRow(self.completer.currentRow() + 1)
                self.completer.popup().setCurrentIndex(self.completer.currentIndex())
                e.accept()
                return
            elif (
                e.key() == Qt.Key.Key_P
                and e.modifiers() & Qt.KeyboardModifier.ControlModifier
            ):
                self.completer.setCurrentRow(self.completer.currentRow() - 1)
                self.completer.popup().setCurrentIndex(self.completer.currentIndex())
                e.accept()
                return

        super().keyPressEvent(e)

        ctrl_or_shift = e.modifiers() & (
            Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier
        )
        if ctrl_or_shift and e.text() == "":
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

    def text_under_cursor(self) -> str:
        tc = self.textCursor()
        tc.select(QTextCursor.SelectionType.WordUnderCursor)
        return tc.selectedText()

    def insert_completion(self, completion: str) -> None:
        tc = self.textCursor()
        extra = len(completion) - len(self.completer.completionPrefix())
        tc.movePosition(QTextCursor.MoveOperation.Left)
        tc.movePosition(QTextCursor.MoveOperation.EndOfWord)
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
        self.plotting_widget: PlottingWidget
        self.create_content()
        self.update_completions()
        self.setup_shortcuts()

    def create_content(self) -> None:
        # Create main horizontal splitter
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_splitter.setHandleWidth(20)
        self.main_layout.addWidget(main_splitter)

        # Create left widget for SQL input, execute button, and table view
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        # Create and set up the SQLTextEdit
        self.text_edit = SQLTextEdit()
        left_layout.addWidget(self.text_edit)

        # Create execute button
        self.execute_button = QPushButton("Execute Query")
        self.execute_button.clicked.connect(self.on_execute_clicked)
        left_layout.addWidget(self.execute_button)

        # Create and set up the table widget
        self.table_widget = TableWidget()
        self.table_widget.table_view.setSortingEnabled(True)
        self.table_widget.filterChanged.connect(self.on_filter_changed)
        left_layout.addWidget(self.table_widget)

        # Add left widget to main splitter
        main_splitter.addWidget(left_widget)

        # Create plotting widget and add it to main splitter
        self.plotting_widget = PlottingWidget()
        main_splitter.addWidget(self.plotting_widget)

        # Set initial sizes for the main splitter
        main_splitter.setSizes([int(self.width() * 0.6), int(self.width() * 0.4)])

    def on_filter_changed(self, column: int, filter_text: str) -> None:
        model = self.table_widget.table_view.model()
        if isinstance(model, DuckDBTableModel):
            model.set_filter(column, filter_text)
            self.table_widget.adjust_columns()

    def setup_shortcuts(self) -> None:
        shortcut = QShortcut(QKeySequence("Ctrl+Return"), self)
        shortcut.activated.connect(self.on_execute_clicked)

    def on_execute_clicked(self) -> None:
        query = self.text_edit.toPlainText()
        self.execute_sql(query)

    def update_completions(self) -> None:
        schema = get_complete_schema(self.connection)
        table_names = list(schema.keys())
        column_names = [
            col["name"] for table in schema.values() for col in table["columns"]
        ]
        keywords = [
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
            "LIMIT",
            "RIGHT JOIN",
        ]
        completions = keywords + table_names + column_names
        self.text_edit.completer.update_completions(completions)

    def execute_sql(self, query: str) -> None:
        try:
            result = self.connection.execute(query)
            model = DuckDBTableModel(self.connection, "", result=result)
            self.table_widget.set_model(model)
            self.highlight_sql(success=True)
            self.update_completions()

            # Update plot with new data
            if model.rowCount() > 0 and model.columnCount() >= 2:
                data = {
                    model.headerData(col, Qt.Orientation.Horizontal): [
                        model.data(model.index(row, col))
                        for row in range(model.rowCount())
                    ]
                    for col in range(model.columnCount())
                }
                df = pd.DataFrame(data)
                self.plotting_widget.set_data(df)

        except Exception as e:
            error_message = f"Error executing SQL: {str(e)}"
            self.table_widget.display_error(error_message)
            self.highlight_sql(success=False)

    def highlight_sql(self, success: bool) -> None:
        color = QColor(200, 255, 200) if success else QColor(255, 200, 200)
        self.text_edit.set_background_color(color)
