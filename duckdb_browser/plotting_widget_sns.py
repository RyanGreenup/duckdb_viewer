from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QComboBox,
    QPushButton,
    QLabel,
    QSizePolicy,
)
from PySide6.QtCore import Qt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import seaborn as sns
import pandas as pd
from typing import Optional, List, Literal, cast
from matplotlib.axes import Axes

PlotType = Literal["Scatter", "Line", "Bar"]


class PlottingWidget(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._layout = QVBoxLayout(self)

        # Create combo boxes and update button
        self.x_combo = QComboBox()
        self.y_combo = QComboBox()
        self.plot_type_combo = QComboBox()
        self.plot_type_combo.addItems(["Scatter", "Line", "Bar"])
        self.update_button = QPushButton("Update Plot")

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
        size_policy = QSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.x_combo.setSizePolicy(size_policy)
        self.y_combo.setSizePolicy(size_policy)
        self.plot_type_combo.setSizePolicy(size_policy)

        combo_layout = QHBoxLayout()
        combo_layout.addWidget(QLabel("Plot Type:"))
        combo_layout.addWidget(self.plot_type_combo)
        combo_layout.addWidget(QLabel("X-axis:"))
        combo_layout.addWidget(self.x_combo)
        combo_layout.addWidget(QLabel("Y-axis:"))
        combo_layout.addWidget(self.y_combo)
        combo_layout.addWidget(self.update_button)
        self.update_button.hide()  # Hide the update button as it's no longer needed
        combo_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        combo_layout.setSpacing(10)
        self._layout.addLayout(combo_layout)

        self.figure: Figure = Figure(figsize=(5, 4), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        self._layout.addWidget(self.canvas)

        # Set Seaborn style
        sns.set_theme(style="whitegrid")

        # Connect update button and combo boxes to update_plot method
        self.update_button.clicked.connect(self.update_plot)
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

    def update_plot(self) -> None:
        if self.data is not None:
            x_col = self.x_combo.currentText()
            y_col = self.y_combo.currentText()
            self.plot_data(x_col, y_col)

    def plot_data(self, x_col: str, y_col: str) -> None:
        if self.data is None:
            return

        self.figure.clear()
        ax: Axes = self.figure.add_subplot(111)

        plot_type: PlotType = cast(PlotType, self.plot_type_combo.currentText())

        if plot_type == "Scatter":
            sns.scatterplot(data=self.data, x=x_col, y=y_col, ax=ax)
        elif plot_type == "Line":
            sns.lineplot(data=self.data, x=x_col, y=y_col, ax=ax)
        elif plot_type == "Bar":
            sns.barplot(data=self.data, x=x_col, y=y_col, ax=ax)

        ax.set_title(f"{plot_type} Plot: {x_col} vs {y_col}")
        ax.tick_params(axis="x", rotation=45)
        self.figure.tight_layout()
        self.canvas.draw_idle()
