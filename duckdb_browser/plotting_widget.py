from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QComboBox,
    QLabel,
    QSizePolicy,
)
from PySide6.QtCore import Qt
from PySide6.QtCharts import QChart, QChartView, QLineSeries, QScatterSeries, QBarSeries, QBarSet, QValueAxis, QBoxPlotSeries, QBoxSet
from PySide6.QtGui import QPainter
import pandas as pd
import numpy as np
from typing import Optional, List

class PlottingWidget(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._layout = QVBoxLayout(self)

        # Create combo boxes
        self.x_combo = QComboBox()
        self.y_combo = QComboBox()
        self.plot_type_combo = QComboBox()
        self.plot_type_combo.addItems(["Scatter", "Line", "Bar", "Histogram", "Box Plot"])

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
        if self.data is None or x_col == '' or y_col == '':
            return

        self.chart.removeAllSeries()
        self.chart.createDefaultAxes()

        plot_type = self.plot_type_combo.currentText()

        # Convert data to numeric, replacing non-numeric values with NaN
        x_data = pd.to_numeric(self.data[x_col], errors='coerce')
        y_data = pd.to_numeric(self.data[y_col], errors='coerce')

        # Remove NaN values
        valid_data = pd.DataFrame({'x': x_data, 'y': y_data}).dropna()

        if plot_type == "Scatter":
            series = QScatterSeries()
            for x, y in zip(valid_data['x'], valid_data['y']):
                series.append(float(x), float(y))
            self.chart.addSeries(series)
        elif plot_type == "Line":
            series = QLineSeries()
            for x, y in zip(valid_data['x'], valid_data['y']):
                series.append(float(x), float(y))
            self.chart.addSeries(series)
        elif plot_type == "Bar":
            series = QBarSeries()
            bar_set = QBarSet(str(y_col))
            for y in valid_data['y']:
                bar_set.append(float(y))
            series.append(bar_set)
            self.chart.addSeries(series)
        elif plot_type == "Histogram":
            series = QBarSeries()
            bar_set = QBarSet("Frequency")
            
            # Calculate histogram data
            hist, bin_edges = np.histogram(valid_data['x'], bins='auto')
            
            for count in hist:
                bar_set.append(float(count))
            series.append(bar_set)
            self.chart.addSeries(series)
        elif plot_type == "Box Plot":
            series = QBoxPlotSeries()
            series.setName(str(y_col))

            # Calculate box plot statistics
            q1 = np.percentile(valid_data['y'], 25)
            median = np.median(valid_data['y'])
            q3 = np.percentile(valid_data['y'], 75)
            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr

            # Create a QBoxSet for the entire dataset
            box_set = QBoxSet(lower_bound, q1, median, q3, upper_bound)
            series.append(box_set)

            self.chart.addSeries(series)

        self.chart.setTitle(f"{plot_type}: {y_col}")
        self.chart.createDefaultAxes()
        x_axis = self.chart.axes(Qt.Horizontal)[0]
        y_axis = self.chart.axes(Qt.Vertical)[0]

        if plot_type == "Histogram":
            x_axis.setTitleText("Bins")
            y_axis.setTitleText("Frequency")
            categories = [f"{bin_edges[i]:.2f}-{bin_edges[i+1]:.2f}" for i in range(len(bin_edges)-1)]
            x_axis.setCategories(categories)
        elif plot_type == "Box Plot":
            x_axis.setTitleText(str(y_col))
            y_axis.setTitleText("Value")
            x_axis.setLabelsVisible(False)
        else:
            x_axis.setTitleText(str(x_col))
            y_axis.setTitleText(str(y_col))
            if plot_type == "Bar":
                categories = [str(x) for x in valid_data['x']]
                x_axis.setCategories(categories)

        self.chart_view.update()
