#!/usr/bin/env python
import sys
from PySide6.QtWidgets import (
    QApplication,
)
from typing import Optional
import typer
import signal
from main_window import MainWindow

app = typer.Typer(pretty_exceptions_enable=False)

@app.command()
def main(db_path: str = "duckdb_browser.db", table_name: Optional[str] = None) -> None:
    app = QApplication(sys.argv)
    window = MainWindow(db_path=db_path, initial_table=table_name)
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    app()


# Footnotes
# [fn_QModelIndex.parent]
# This matches the documentation
# An issue with pyright probably
# https://doc.qt.io/qtforpython-6/PySide6/QtCore/QAbstractItemModel.html#PySide6.QtCore.QAbstractItemModel.parent
