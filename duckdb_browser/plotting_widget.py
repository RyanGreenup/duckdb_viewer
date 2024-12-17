from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QPushButton
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import seaborn as sns
import pandas as pd
from typing import Optional, List
from matplotlib.axes import Axes


class PlottingWidget(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._layout = QVBoxLayout(self)
        
        # Create combo boxes and update button
        self.x_combo = QComboBox()
        self.y_combo = QComboBox()
        self.update_button = QPushButton("Update Plot")
        
        combo_layout = QHBoxLayout()
        combo_layout.addWidget(self.x_combo)
        combo_layout.addWidget(self.y_combo)
        combo_layout.addWidget(self.update_button)
        self._layout.addLayout(combo_layout)
        
        self.figure: Figure = Figure(figsize=(5, 4), dpi=100)
        self.canvas: FigureCanvas = FigureCanvas(self.figure)  # type: ignore [no-untyped-call]
        self._layout.addWidget(self.canvas)

        # Set Seaborn style
        sns.set_theme(style="whitegrid")
        
        # Connect update button to plot_data method
        self.update_button.clicked.connect(self.update_plot)
        
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

        # Use Seaborn to create a scatter plot
        sns.scatterplot(data=self.data, x=x_col, y=y_col, ax=ax)

        ax.set_title(f"{x_col} vs {y_col}")
        self.figure.tight_layout()
        self.canvas.draw_idle()  # type: ignore [no-untyped-call]
