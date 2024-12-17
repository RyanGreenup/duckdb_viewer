from PySide6.QtWidgets import QWidget, QVBoxLayout
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import seaborn as sns
import pandas as pd


class PlottingWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.figure = Figure(figsize=(5, 4), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        self.layout.addWidget(self.canvas)

        # Set Seaborn style
        sns.set_theme(style="whitegrid")

    def plot_data(self, data: pd.DataFrame):
        self.figure.clear()
        ax = self.figure.add_subplot(111)

        # Use Seaborn to create a scatter plot
        sns.scatterplot(data=data, x=data.columns[0], y=data.columns[1], ax=ax)

        ax.set_title(f"{data.columns[0]} vs {data.columns[1]}")
        self.figure.tight_layout()
        self.canvas.draw()
