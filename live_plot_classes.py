from abc import ABC, abstractmethod, ABCMeta
import pyqtgraph as pg
from PyQt6 import QtCore, QtWidgets, QtGui
from PyQt6.QtCore import QObject, QThread, pyqtSignal as Signal, pyqtSlot as Slot, QTimer
from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QStyle, QGridLayout, QProgressBar, QDockWidget, QFormLayout, QLabel, QLineEdit
from time import sleep
from threading import Thread
import numpy as np
from cmap import Colormap
import sys

WIDTH = 3
NCOLORS = 5

colors = []
cmap = pg.colormap.get('CET-D1A')
for i in range(NCOLORS):
    color = cmap.map(i/NCOLORS, 'qcolor')
    colors.append(color)

penRotation = [pg.mkPen(color = c, width = WIDTH) for c in colors]


class AbstractPlot(ABC):
    @abstractmethod
    def updateData(self, data):
        pass

    @abstractmethod
    def updateLayout(self, plot_item, key, value):
        pass

class LinePlot(AbstractPlot):
    def __init__(self):
        self.plotItem = None

    def updateLayout(self, plot_item, key, value, **kwargs):
        # Use the specified pen in the configuration
        pen = kwargs.get("pen", pg.mkPen("black"))  # Default to black if no pen
        self.plotItem = plot_item.plot(pen=pen)
        plot_item.setTitle(value.get("title", key))

    def updateData(self, data):
        self.plotItem.setData(data.get("x", []), data.get("y", []))




class ScatterPlot(AbstractPlot):
    def __init__(self):
        self.plotItem = None

    def updateLayout(self, plot_item, key, value, **kwargs):
        # Use the specified pen in the configuration
        pen = kwargs.get("pen", pg.mkPen("black"))  # Default to black if no pen
        brush = pg.mkBrush(pen.color())  # Use pen color for the scatter brush
        self.plotItem = pg.ScatterPlotItem(symbol="o", size=8, brush=brush)
        plot_item.addItem(self.plotItem)
        plot_item.setTitle(value.get("title", key))

    def updateData(self, data):
        self.plotItem.setData(data.get("x", []), data.get("y", []))




class Counts(AbstractPlot):
    def __init__(self):
        self.lines = []

    def updateLayout(self, plot_item, key, value, **kwargs):
        self.plot_item = plot_item
        # Save the pen for later use in drawing lines
        self.pen = kwargs.get("pen", pg.mkPen("black"))  # Default to black if no pen
        self.plot_item.setLimits(yMin=0, yMax=1, minYRange=1)
        self.plot_item.setTitle(value.get("title", key))

    def updateData(self, data):
        # Clear previous lines
        for line in self.lines:
            line.hide()

        # Draw new lines using the specified pen
        self.lines = [
            self.plot_item.addLine(x=t, pen=self.pen) for t in data.get("x", [])
        ]


class Map(AbstractPlot):
    def __init__(self):
        self.plotItem = None

    def updateLayout(self, plot_item, key, value, **kwargs):
        # Add the heatmap (ImageItem) to the provided PlotItem
        self.plotItem = pg.ImageItem()
        plot_item.addItem(self.plotItem)
        plot_item.setTitle(value.get("title", key))

    def updateData(self, data):
        self.plotItem.setImage(data.get("z", np.zeros((1, 1))).transpose(), autoLevels=False)

        x_values = data.get("x", None)
        y_values = data.get("y", None)
        z_values = data.get("z", None)

        if x_values is not None:
            scale_x = (x_values[-1] - x_values[0]) / z_values.shape[1]
            translate_x = x_values[0]
        else:
            scale_x = 1
            translate_x = 0

        if y_values is not None:
            scale_y = (y_values[-1] - y_values[0]) / z_values.shape[0]
            translate_y = y_values[0]
        else:
            scale_y = 1
            translate_y = 0

        transform = QtGui.QTransform()
        transform.translate(translate_x, translate_y)
        transform.scale(scale_x, scale_y)
        self.plotItem.setTransform(transform)
       
plot_library = {
    "LinePlot": LinePlot,
    "ScatterPlot": ScatterPlot,
    "Counts": Counts,
    "HeatMap": Map,
}

class GraphManager:
    def __init__(self, main_window, data_pack):
        self.main_window = main_window
        self.data_pack = data_pack
        self.graphs = {}

    def create_graphs(self):
        # Iterate over "layout" to create GraphCreator instances
        layout = self.data_pack.get("layout", {})
        for graph_name, graph_config in layout.items():
            graph = GraphCreator(self.main_window, graph_name, graph_config)
            self.graphs[graph_name] = graph


    def update_data(self):
        # Parse the "data" part of the data_pack
        data = self.data_pack.get("data", {})
        for graph_name, graph_data in data.items():
            graph = self.graphs.get(graph_name)
            if not graph:
                continue  # Skip if the graph doesn't exist

            # Update the graph with new data
            graph.updateData(graph_data)


    def apply_layout(self):
        # Add graphs to the main window based on their configurations
        for graph_name, graph in self.graphs.items():
            loc = graph.config.get("loc", (0, 0, 1, 1))
            self.main_window.addDockWidget(
                QtCore.Qt.DockWidgetArea.LeftDockWidgetArea, graph
            )



class GraphCreator(QDockWidget):
    def __init__(self, main_window, name, config):
        super().__init__()
        self.main_window = main_window
        self.name = name
        self.config = config  # Full configuration for this plot
        self.layout_widget = pg.GraphicsLayoutWidget()  # Base layout
        self.plots = {}
        self.lut_item = None

        # Pen index for cycling through penRotation
        self.penIndex = 0

        # Set up the dock widget properties
        self.setFloating(True)
        self.setAllowedAreas(QtCore.Qt.DockWidgetArea.AllDockWidgetAreas)

        # Parse and apply the configuration
        self.parse_config()

        # Set the GraphicsLayoutWidget as the dock's widget
        self.setWidget(self.layout_widget)

    def parse_config(self):
        # Parse labels
        x_label = self.config.get("x_label", "X-Axis")
        y_label = self.config.get("y_label", "Y-Axis")

        # Create a single PlotItem for overlays
        self.main_plot_item = self.layout_widget.addPlot(row=0, col=0)
        self.main_plot_item.setLabel(axis="left", text=y_label)
        self.main_plot_item.setLabel(axis="bottom", text=x_label)
        self.main_plot_item.showGrid(x=True, y=True)

        # Check if there's a heatmap and add LUT if necessary
        if any(part["type"] == "HeatMap" for part in self.config["content"].values()):
            self.lut_item = pg.HistogramLUTItem()
            self.layout_widget.addItem(self.lut_item, row=0, col=1)

        # Create parts (e.g., part1, part2) and add them to the plot
        for part_name, part_config in self.config["content"].items():
            # Handle pen configuration
            pen = self.get_pen(part_config)

            # Get the plot type
            plot_type = part_config["type"]
            if plot_type not in plot_library:
                raise ValueError(f"Unknown plot type: {plot_type}")

            # Instantiate the plot
            plot_instance = plot_library[plot_type]()
            plot_instance.updateLayout(self.main_plot_item, part_name, part_config, pen = pen)

            # Link the LUT to the heatmap
            if plot_type == "HeatMap" and self.lut_item:
                self.lut_item.setImageItem(plot_instance.plotItem)

            self.plots[part_name] = plot_instance

    def get_pen(self, part_config):
        """
        Generate a pen based on the part configuration.
        """
        # If "pen" is explicitly specified, use it
        if "pen" in part_config:
            return part_config["pen"]

        # If "color" is specified, create a pen from the color
        if "color" in part_config:
            width = part_config.get("width", WIDTH)
            return pg.mkPen(color=part_config["color"], width=width)

        # If only "width" is specified, take a pen from penRotation and adjust the width
        if "width" in part_config:
            width = part_config["width"]
            pen = penRotation[self.penIndex % len(penRotation)]
            self.penIndex += 1
            return pg.mkPen(color=pen.color(), width=width)

        # Default case: Use a pen from penRotation
        pen = penRotation[self.penIndex % len(penRotation)]
        self.penIndex += 1
        return pen

    def updateData(self, data):
        # Update each plot with its specific data
        for part_name, plot in self.plots.items():
            if part_name in data:
                plot.updateData(data[part_name])



if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication, QMainWindow

    app = QApplication(sys.argv)
    main_window = QMainWindow()
    main_window.setWindowTitle("Graph Manager Test with Custom Pens")
    main_window.resize(1200, 800)

    # Example data_pack
    data_pack = {
        "layout": {
            "Plot1": {
                "content": {
                    "part1": {"type": "ScatterPlot"},
                    "part2": {"type": "LinePlot"},
                },
                "y_label": "Measurement",
                "x_label": "Time",
                "loc": (0, 0, 1, 1),
            },
            "Plot2": {
                "content": {
                    "part1": {"type": "Counts", "pen": pg.mkPen("blue", width=2)},
                },
                "y_label": "Counts",
                "x_label": "Categories",
                "loc": (1, 0, 1, 1),
            },
            "Plot3": {
                "content": {
                    "part1": {"type": "Counts"},
                    "part2": {"type": "HeatMap"},
                },
                "y_label": "Intensity",
                "x_label": "X-Axis",
                "loc": (2, 0, 1, 1),
            },
        },
        "data": {
            "Plot1": {
                "part1": {
                    "x": np.linspace(0, 10, 100),
                    "y": np.sin(np.linspace(0, 10, 100)) + 0.2 * np.random.randn(100),
                },
                "part2": {
                    "x": np.linspace(0, 10, 100),
                    "y": np.sin(np.linspace(0, 10, 100)),
                },
            },
            "Plot2": {
                "part1": {
                    "x": np.arange(0, 10, 1),
                },
            },
            "Plot3": {
                "part1": {"x":[5]},
                "part2": {
                    "x": np.linspace(0, 10, 100),
                    "y": np.linspace(0, 10, 100),
                    "z": np.random.random((100, 100)),
                },
            },
        },
    }

    # Create and apply GraphManager
    manager = GraphManager(main_window, data_pack)
    manager.create_graphs()
    manager.update_data()
    manager.apply_layout()

    main_window.show()
    sys.exit(app.exec())
