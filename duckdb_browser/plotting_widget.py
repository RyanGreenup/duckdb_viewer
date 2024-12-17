from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QComboBox,
    QLabel,
    QSizePolicy,
)
from PySide6.QtCore import Qt
from PySide6.QtCharts import QChart, QChartView, QLineSeries, QScatterSeries, QBarSeries, QBarSet
from PySide6.QtGui import QPainter
import pandas as pd
from typing import Optional, List

class PlottingWidget(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._layout = QVBoxLayout(self)

        # Create combo boxes
        self.x_combo = QComboBox()
        self.y_combo = QComboBox()
        self.plot_type_combo = QComboBox()
        self.plot_type_combo.addItems(["Scatter", "Line", "Bar"])

        # Set minimum width for combo boxes
        min_width = 150
        self.x_combo.setMinimumWidth(min_width)
        self.y_combo.setMinimumWidth(min_width)
        self.plot_type_combo.setMinimumWidth(min_width)

        # Apply stylesheet for a more professional look
        style = """
        QComboBox {
            border: 1px solid #ccc;
            border-radius: 3px;
            padding: 5px;
            min-height: 25px;
        }
        QComboBox::drop-down {
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 25px;
            border-left: 1px solid #ccc;
        }
        QComboBox::down-arrow {
            image: url(down_arrow.png);
        }
        """
        self.x_combo.setStyleSheet(style)
        self.y_combo.setStyleSheet(style)
        self.plot_type_combo.setStyleSheet(style)

        # Set size policy to expand horizontally
        self.x_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.y_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.plot_type_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        combo_layout = QHBoxLayout()
        combo_layout.addWidget(QLabel("Plot Type:"))
        combo_layout.addWidget(self.plot_type_combo)
        combo_layout.addWidget(QLabel("X-axis:"))
        combo_layout.addWidget(self.x_combo)
        combo_layout.addWidget(QLabel("Y-axis:"))
        combo_layout.addWidget(self.y_combo)
        combo_layout.setAlignment(Qt.AlignTop)
        combo_layout.setSpacing(10)
        self._layout.addLayout(combo_layout)

        # Create QChart and QChartView
        self.chart = QChart()
        self.chart_view = QChartView(self.chart)
        self.chart_view.setRenderHint(QPainter.Antialiasing)
        self._layout.addWidget(self.chart_view)

        # Connect combo boxes to update_plot method
        self.x_combo.currentIndexChanged.connect(self.update_plot)
        self.y_combo.currentIndexChanged.connect(self.update_plot)
        self.plot_type_combo.currentIndexChanged.connect(self.update_plot)

        self.data: Optional[pd.DataFrame] = None

    def set_columns(self, columns: List[str]) -> None:
        self.x_combo.clear()
        self.y_combo.clear()
        self.x_combo.addItems(columns)
        self.y_combo.addItems(columns)
        if len(columns) > 1:
            self.y_combo.setCurrentIndex(1)

    def set_data(self, data: pd.DataFrame) -> None:
        self.data = data
        self.set_columns(data.columns.tolist())
        self.update_plot()

    def update_plot(self) -> None:
        if self.data is not None:
            x_col = self.x_combo.currentText()
            y_col = self.y_combo.currentText()
            self.plot_data(x_col, y_col)

    def plot_data(self, x_col: str, y_col: str) -> None:
        if self.data is None:
            return

        self.chart.removeAllSeries()
        self.chart.createDefaultAxes()

        plot_type = self.plot_type_combo.currentText()

        if plot_type == "Scatter":
            series = QScatterSeries()
            for x, y in zip(self.data[x_col], self.data[y_col]):
                series.append(float(x), float(y))
            self.chart.addSeries(series)
        elif plot_type == "Line":
            series = QLineSeries()
            for x, y in zip(self.data[x_col], self.data[y_col]):
                series.append(float(x), float(y))
            self.chart.addSeries(series)
        elif plot_type == "Bar":
            series = QBarSeries()
            bar_set = QBarSet(y_col)
            for y in self.data[y_col]:
                bar_set.append(float(y))
            series.append(bar_set)
            self.chart.addSeries(series)

        self.chart.setTitle(f"{plot_type} Plot: {x_col} vs {y_col}")
        self.chart.createDefaultAxes()
        x_axis = self.chart.axes(Qt.Horizontal)[0]
        x_axis.setTitleText(x_col)
        y_axis = self.chart.axes(Qt.Vertical)[0]
        y_axis.setTitleText(y_col)

        if plot_type == "Bar":
            categories = [str(x) for x in self.data[x_col]]
            x_axis.setCategories(categories)

        self.chart_view.update()
