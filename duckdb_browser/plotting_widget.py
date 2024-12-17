from PySide6.QtWidgets import QWidget, QVBoxLayout
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import seaborn as sns
import pandas as pd
from typing import Optional
from matplotlib.axes import Axes


class PlottingWidget(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._layout = QVBoxLayout(self)
        self.figure: Figure = Figure(figsize=(5, 4), dpi=100)
        self.canvas: FigureCanvas = FigureCanvas(self.figure)  # type: ignore [no-untyped-call]
        self._layout.addWidget(self.canvas)

        # Set Seaborn style
        sns.set_theme(style="whitegrid")

    def plot_data(self, data: pd.DataFrame) -> None:
        self.figure.clear()
        ax: Axes = self.figure.add_subplot(111)

        # Use Seaborn to create a scatter plot
        sns.scatterplot(data=data, x=data.columns[0], y=data.columns[1], ax=ax)

        ax.set_title(f"{data.columns[0]} vs {data.columns[1]}")
        self.figure.tight_layout()
        self.canvas.draw_idle()  # type: ignore [no-untyped-call]
