from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QComboBox,
    QLabel,
    QSizePolicy,
)
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QPainter
from PySide6.QtCharts import (
    QChart,
    QChartView,
    QLineSeries,
    QScatterSeries,
    QBarSeries,
    QBarSet,
    QValueAxis,
    QBoxPlotSeries,
    QBoxSet,
    QBarCategoryAxis,
)
from PySide6.QtGui import QColor
import pandas as pd
import numpy as np
from typing import Optional, List, Tuple, Dict, Union
from numpy.typing import NDArray
from enum import Enum, auto
from pandas import Series

# Custom type for the return value of _convert_to_numeric_or_categorical
NumericOrCategoricalResult = Tuple[Series, Optional[List[str]]]


class CustomToolTip(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.ToolTip)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(10, 10, 10, 10)
        self.label = QLabel(self)
        self.label.setStyleSheet("""
            QLabel {
                background-color: rgba(25, 25, 25, 230);
                color: white;
                border-radius: 5px;
                padding: 10px;
                font-size: 12px;
            }
        """)
        self._layout.addWidget(self.label)

    def show_tooltip(self, text: str, pos: QPointF) -> None:
        self.label.setText(text)
        self.adjustSize()
        super().show()
        self.move(pos.toPoint())


class PlotType(Enum):
    SCATTER = auto()
    LINE = auto()
    BAR = auto()
    HISTOGRAM = auto()
    BOX_PLOT = auto()


class PlottingWidget(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._layout = QVBoxLayout(self)

        # Create combo boxes
        self.x_combo = QComboBox()
        self.y_combo = QComboBox()
        self.color_combo = QComboBox()
        self.plot_type_combo = QComboBox()
        self.plot_type_combo.addItems(
            [plot_type.name.capitalize().replace("_", " ") for plot_type in PlotType]
        )

        # Create custom tooltip
        self.tooltip = CustomToolTip(self)

        # Set minimum width for combo boxes
        min_width = 150
        self.x_combo.setMinimumWidth(min_width)
        self.y_combo.setMinimumWidth(min_width)
        self.color_combo.setMinimumWidth(min_width)
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
        self.color_combo.setStyleSheet(style)
        self.plot_type_combo.setStyleSheet(style)

        # Set size policy to expand horizontally
        self.x_combo.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.y_combo.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.color_combo.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.plot_type_combo.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )

        combo_layout = QHBoxLayout()
        combo_layout.addWidget(QLabel("Plot Type:"))
        combo_layout.addWidget(self.plot_type_combo)
        combo_layout.addWidget(QLabel("X-axis:"))
        combo_layout.addWidget(self.x_combo)
        combo_layout.addWidget(QLabel("Y-axis:"))
        combo_layout.addWidget(self.y_combo)
        combo_layout.addWidget(QLabel("Color:"))
        combo_layout.addWidget(self.color_combo)
        combo_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        combo_layout.setSpacing(10)
        self._layout.addLayout(combo_layout)

        # Create QChart and QChartView
        self.chart = QChart()
        self.chart_view = QChartView(self.chart)
        self.chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.chart_view.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self._layout.addWidget(self.chart_view)

        # Connect combo boxes to update_plot method
        self.x_combo.currentIndexChanged.connect(self.update_plot)
        self.y_combo.currentIndexChanged.connect(self.update_plot)
        self.color_combo.currentIndexChanged.connect(self.update_plot)
        self.plot_type_combo.currentIndexChanged.connect(self.update_plot)

        self.data: Optional[pd.DataFrame] = None

    def set_columns(self, columns: List[str]) -> None:
        self.x_combo.clear()
        self.y_combo.clear()
        self.color_combo.clear()
        self.x_combo.addItems(columns)
        self.y_combo.addItems(columns)
        self.color_combo.addItems(["None"] + columns)
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
        if self.data is None or x_col == "" or y_col == "":
            return

        self.chart.removeAllSeries()
        self.chart.createDefaultAxes()

        plot_type = PlotType[
            self.plot_type_combo.currentText().upper().replace(" ", "_")
        ]
        color_col = self.color_combo.currentText()

        # Convert data to numeric or categorical for plotting
        x_data, x_categories = self._convert_to_numeric_or_categorical(self.data[x_col])
        y_data, y_categories = self._convert_to_numeric_or_categorical(self.data[y_col])

        # Create valid_data DataFrame with original data
        valid_data = pd.DataFrame(
            {
                "x": self.data[x_col],
                "y": self.data[y_col],
                "x_plot": x_data,
                "y_plot": y_data,
            }
        )
        if color_col != "None":
            valid_data["color"] = self.data[color_col]
        valid_data = valid_data.dropna()

        # Handle empty color column
        if color_col == "None":
            color_col = None
        elif color_col not in valid_data.columns:
            color_col = None
        elif valid_data["color"].empty:
            color_col = None

        match plot_type:
            case PlotType.SCATTER:
                self._plot_scatter(valid_data, color_col)
            case PlotType.LINE:
                self._plot_line(valid_data, color_col)
            case PlotType.BAR:
                self._plot_bar(valid_data, color_col, x_col)
            case PlotType.HISTOGRAM:
                self._plot_histogram(valid_data, color_col)
            case PlotType.BOX_PLOT:
                self._plot_box(valid_data, color_col, x_col)

        self.chart.setTitle(f"{plot_type.name.capitalize().replace('_', ' ')}: {y_col}")
        self.chart.createDefaultAxes()
        x_axis = self.chart.axes(Qt.Orientation.Horizontal)[0]
        y_axis = self.chart.axes(Qt.Orientation.Vertical)[0]

        self._set_axis_labels(
            x_axis,
            y_axis,
            plot_type,
            x_col,
            y_col,
            valid_data,
            color_col,
            x_categories,
            y_categories,
        )

        if color_col:
            self.chart.legend().show()
        else:
            self.chart.legend().hide()

        self.chart_view.update()

    def _convert_to_numeric_or_categorical(
        self, data: pd.Series
    ) -> NumericOrCategoricalResult:
        if data.dtype == "object":
            categories = data.unique().tolist()
            return pd.Series(pd.Categorical(data).codes), categories
        else:
            return pd.to_numeric(data, errors="coerce"), None

    def _plot_scatter(self, valid_data: pd.DataFrame, color_col: Optional[str]) -> None:
        if color_col:
            unique_colors = valid_data["color"].unique()
            color_map = self._get_color_map(unique_colors)
            for color in unique_colors:
                series = QScatterSeries()
                series.setName(f"{color_col}: {color}")
                series.setColor(color_map[color])
                color_data = valid_data[valid_data["color"] == color]
                for y, x, y_plot, x_plot in zip(
                    color_data["y"],
                    color_data["x"],
                    color_data["y_plot"],
                    color_data["x_plot"],
                ):
                    series.append(float(x_plot), float(y_plot))
                series.hovered.connect(self._show_tooltip)
                self.chart.addSeries(series)
        else:
            series = QScatterSeries()
            series.setName("Data")
            for y, x, y_plot, x_plot in zip(
                valid_data["y"],
                valid_data["x"],
                valid_data["y_plot"],
                valid_data["x_plot"],
            ):
                series.append(float(x_plot), float(y_plot))
            series.hovered.connect(self._show_tooltip)
            self.chart.addSeries(series)

    def _plot_line(self, valid_data: pd.DataFrame, color_col: Optional[str]) -> None:
        if color_col:
            unique_colors = valid_data["color"].unique()
            color_map = self._get_color_map(unique_colors)
            for color in unique_colors:
                series = QLineSeries()
                series.setName(f"{color_col}: {color}")
                series.setColor(color_map[color])
                color_data = valid_data[valid_data["color"] == color]
                for y_plot, x_plot in zip(color_data["y_plot"], color_data["x_plot"]):
                    series.append(float(x_plot), float(y_plot))
                series.hovered.connect(self._show_tooltip)
                self.chart.addSeries(series)
        else:
            series = QLineSeries()
            series.setName("Data")
            for y_plot, x_plot in zip(valid_data["y_plot"], valid_data["x_plot"]):
                series.append(float(x_plot), float(y_plot))
            series.hovered.connect(self._show_tooltip)
            self.chart.addSeries(series)

    def _plot_bar(
        self, valid_data: pd.DataFrame, color_col: Optional[str], x_col: str
    ) -> None:
        series = QBarSeries()
        if color_col != "None":
            unique_colors = valid_data["color"].unique()
            color_map = self._get_color_map(unique_colors)
            for color in unique_colors:
                bar_set = QBarSet(str(color))
                bar_set.setColor(color_map[color])
                color_data = valid_data[valid_data["color"] == color]
                for x, x_plot in zip(color_data["x"], color_data["x_plot"]):
                    bar_set.append(float(x_plot))
                    bar_set.setLabel(str(x))
                series.append(bar_set)
        else:
            bar_set = QBarSet(str(x_col))
            for x, x_plot in zip(valid_data["x"], valid_data["x_plot"]):
                bar_set.append(float(x_plot))
                bar_set.setLabel(str(x))
            series.append(bar_set)
        self.chart.addSeries(series)

    def _plot_histogram(
        self, valid_data: pd.DataFrame, color_col: Optional[str]
    ) -> None:
        series = QBarSeries()
        if color_col != "None":
            unique_colors = valid_data["color"].unique()
            color_map = self._get_color_map(unique_colors)
            for color in unique_colors:
                bar_set = QBarSet(str(color))
                bar_set.setColor(color_map[color])
                color_data = valid_data[valid_data["color"] == color]
                hist, bin_edges = np.histogram(color_data["y_plot"], bins="auto")
                for count, bin_start, bin_end in zip(
                    hist, bin_edges[:-1], bin_edges[1:]
                ):
                    bar_set.append(float(count))
                    bar_set.setLabel(f"{bin_start:.2f}-{bin_end:.2f}")
                series.append(bar_set)
        else:
            bar_set = QBarSet("Frequency")
            hist, bin_edges = np.histogram(valid_data["y_plot"], bins="auto")
            for count, bin_start, bin_end in zip(hist, bin_edges[:-1], bin_edges[1:]):
                bar_set.append(float(count))
                bar_set.setLabel(f"{bin_start:.2f}-{bin_end:.2f}")
            series.append(bar_set)
        self.chart.addSeries(series)

    def _plot_box(
        self, valid_data: pd.DataFrame, color_col: Optional[str], x_col: str
    ) -> None:
        if color_col != "None":
            unique_colors = valid_data["color"].unique()
            color_map = self._get_color_map(unique_colors)
            series = QBoxPlotSeries()
            for color in unique_colors:
                color_data = valid_data[valid_data["color"] == color]["x_plot"]
                box_set = self._create_box_set(color_data)
                box_set.setLabel(str(color))
                box_set.setBrush(color_map[color])
                series.append(box_set)
            self.chart.addSeries(series)
        else:
            series = QBoxPlotSeries()
            box_set = self._create_box_set(valid_data["x_plot"])
            series.append(box_set)
            self.chart.addSeries(series)

    def _create_box_set(self, data: pd.Series) -> QBoxSet:
        q1 = float(np.percentile(data, 25))
        median = float(np.median(data))
        q3 = float(np.percentile(data, 75))
        iqr = q3 - q1
        lower_bound = float(q1 - 1.5 * iqr)
        upper_bound = float(q3 + 1.5 * iqr)
        return QBoxSet(lower_bound, q1, median, q3, upper_bound)

    ColorMap = Dict[Union[str, float], QColor]

    def _get_color_map(
        self, unique_colors: Union[NDArray, List[Union[str, float]]]
    ) -> ColorMap:
        return {
            str(color): QColor(
                hash(str(color)) % 256,
                hash(str(color) * 2) % 256,
                hash(str(color) * 3) % 256,
            )
            for color in unique_colors
        }

    def _set_axis_labels(
        self,
        x_axis,
        y_axis,
        plot_type,
        x_col,
        y_col,
        valid_data,
        color_col,
        x_categories,
        y_categories,
    ):
        if x_axis is None or y_axis is None:
            return

        x_axis.setTitleText(str(x_col))
        y_axis.setTitleText(str(y_col))

        if plot_type == PlotType.HISTOGRAM:
            x_axis.setTitleText("Bins")
            y_axis.setTitleText("Frequency")
            _, bin_edges = np.histogram(valid_data["x"], bins="auto")
            categories = [
                f"{bin_edges[i]:.2f}-{bin_edges[i+1]:.2f}"
                for i in range(len(bin_edges) - 1)
            ]
            self._set_categories(x_axis, categories)
        elif plot_type == PlotType.BOX_PLOT:
            x_axis.setTitleText(str(y_col))
            y_axis.setTitleText("Value")
            if color_col:
                self._set_categories(x_axis, valid_data["color"].unique())
            else:
                x_axis.setLabelsVisible(False)
        elif plot_type == PlotType.BAR:
            categories = [str(x) for x in valid_data["x"]]
            self._set_categories(x_axis, categories)
        else:
            if x_categories:
                self._set_categories(x_axis, x_categories)
            if y_categories:
                self._set_categories(y_axis, y_categories)

        # Rotate x-axis labels by 45 degrees
        if isinstance(x_axis, QBarCategoryAxis):
            x_axis.setLabelsAngle(-45)

        # Add gap at the bottom for x-axis labels
        self.chart.layout().setContentsMargins(0, 0, 0, 40)

    def _set_categories(self, axis, categories):
        if isinstance(axis, QValueAxis):
            new_axis = QBarCategoryAxis()
            new_axis.append(categories)
            self.chart.setAxisX(new_axis, self.chart.series()[0])
        else:
            axis.setCategories(categories)

    def _show_tooltip(self, point: QPointF, state: bool):
        if state:
            x = self.chart.mapToValue(point).x()
            y = self.chart.mapToValue(point).y()
            tooltip_text = f"X: {x:.2f}<br>Y: {y:.2f}"
            global_pos = self.chart_view.mapToGlobal(
                self.chart.mapToPosition(point).toPoint()
            )
            self.tooltip.show_tooltip(tooltip_text, QPointF(global_pos))
        else:
            self.tooltip.hide()
