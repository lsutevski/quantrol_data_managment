from abc import ABC, abstractmethod
import pyqtgraph as pg
from PyQt6 import QtCore, QtWidgets, QtGui
from PyQt6.QtCore import pyqtSignal as Signal, pyqtSlot as Slot
from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, QGridLayout, QProgressBar, QDockWidget, QFormLayout, QLabel, QLineEdit
import numpy as np
import sys
import cmasher as cmr
from functools import partial

MAP_LAYER = -100
LINE_LAYER = -50
SCATTER_LAYER = -20

WIDTH = 3
NCOLORS = 7

colors = []
cmap_map = pg.colormap.get('CET-D2')

mpl_cmap = cmr.guppy
rgba = mpl_cmap(np.linspace(0, 1, NCOLORS, endpoint=False))
rgb8 = (rgba[:, :3] * 255).astype(np.uint8)

penRotation = [pg.mkPen(color = tuple(col), width = WIDTH) for col in rgb8]

pg.setConfigOption('background', "#d6d6d6")   # plot background
pg.setConfigOption('foreground', "#020202")         # axes, labels, text

class AbstractPlot(ABC):
    @abstractmethod
    def updateData(self, data):
        pass

    @abstractmethod
    def updateLayout(self, plot_item, key, value):
        pass

    def fft(self):
        pass


class LinePlot(AbstractPlot):
    def __init__(self):
        super().__init__()
        self.plotItem : pg.PlotItem = None

        self.x_values = None
        self.y_values = None

        self._visible = True

    def updateLayout(self, plot_item, key, value, **kwargs):
        # Use the specified pen in the configuration
        pen = kwargs.get("pen", pg.mkPen("black"))  # Default to black if no pen
        self.plotItem = plot_item.plot(pen=pen)
        self.plotItem.setZValue(LINE_LAYER)
        # plot_item.setTitle(value.get("title", key))

    def updateData(self, data):
        self.x_values = data.get("x", [])
        self.y_values = data.get("y", [])
        self.plotItem.setData(self.x_values, self.y_values)

    def setVisible(self, visible: bool):
        if self.plotItem and self._visible != visible:
            self.plotItem.setVisible(visible)
            self._visible = visible



class ScatterPlot(AbstractPlot):
    def __init__(self):
        super().__init__()
        self.plotItem = None

        self.x_values = None
        self.y_values = None

        self._visible = True

    def updateLayout(self, plot_item, key, value, **kwargs):
        # Use the specified pen in the configuration
        pen = kwargs.get("pen", pg.mkPen("black"))  # Default to black if no pen
        brush = pg.mkBrush(pen.color())  # Use pen color for the scatter brush
        self.plotItem = pg.ScatterPlotItem(symbol="o", size=8, brush=brush)
        self.plotItem.setZValue(SCATTER_LAYER)
        plot_item.addItem(self.plotItem)
        plot_item.setTitle(value.get("title", key))

    def updateData(self, data):
        self.x_values = data.get("x", None)
        self.y_values = data.get("y", None)
        self.plotItem.setData(self.x_values, self.y_values)

    def setVisible(self, visible: bool):
        if self.plotItem and self._visible != visible:
            self.plotItem.setVisible(visible)
            self._visible = visible

class Counts(AbstractPlot):
    def __init__(self):
        super().__init__()
        self.lines = []
        self._visible = True

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

    def setVisible(self, visible: bool):
        if self.plot_item and self._visible != visible:
            for line in self.lines:
                line.setVisible(visible)
            self._visible = visible


class Map(AbstractPlot):
    def __init__(self):
        super().__init__()
        self.plotItem = None

        self.x_values = None
        self.y_values = None
        self.z_values = None

        self._visible = True

    def updateLayout(self, plot_item, key, value, **kwargs):
        # Add the heatmap (ImageItem) to the provided PlotItem
        self.plotItem = pg.ImageItem()
        self.plotItem.setZValue(MAP_LAYER + kwargs.get("z_value", 0))
        # self.plotItem.setColorMap(cmap_map)
        plot_item.addItem(self.plotItem)
        plot_item.setTitle(value.get("title", key))

        # # Set the colormap for the heatmap
        # self.plotItem.setLookupTable(pg.colormap.get('CET-D1A').getLookupTable())

    def updateData(self, data):
        self.plotItem.setImage(data.get("z", np.zeros((1, 1))).transpose(), autoLevels=False)

        self.x_values = data.get("x", None)
        self.y_values = data.get("y", None)
        self.z_values = data.get("z", None)

        if self.x_values is not None:
            scale_x = (self.x_values[-1] - self.x_values[0]) / self.z_values.shape[1]
            translate_x = self.x_values[0]
        else:
            scale_x = 1
            translate_x = 0

        if self.y_values is not None:
            scale_y = (self.y_values[-1] - self.y_values[0]) / self.z_values.shape[0]
            translate_y = self.y_values[0]
        else:
            scale_y = 1
            translate_y = 0

        transform = QtGui.QTransform()
        transform.translate(translate_x, translate_y)
        transform.scale(scale_x, scale_y)
        self.plotItem.setTransform(transform)

    def setVisible(self, visible: bool):
        if self.plotItem and self._visible != visible:
            self.plotItem.setVisible(visible)
            self._visible = visible


class MultiHistogramLUTItem(pg.HistogramLUTItem):
    def __init__(self,
                 images : list[pg.ImageItem] = None,
                 **kwargs):
        super().__init__(**kwargs)

        self.images : list[pg.ImageItem] = []

        self.hist_data : np.ndarray = None
        self.hist_centers : np.ndarray = None

        self.gradient.loadPreset('viridis')

        self.sigLevelsChanged.connect(self.updateHistogram)
        self.gradient.sigGradientChanged.connect(self.updateHistogram)

        if images:
            self.addImages(*images)

        self._visibleImages = []

    def addImages(self, *ims):
        """Call this whenever you want to overlay one or more new ImageItems."""
        for im in ims:
            self.images.append(im)
        self.updateHistogram()
        self._pending_region_change = True

    def updateHistogram(self):
        arrays = []
        for im in self.images:
            data = getattr(im, 'image', None)
            if data is not None:
                arrays.append(data.ravel())
        if not arrays:
            return
        
        all_data = np.hstack(arrays)

        counts, edges = np.histogram(all_data, bins='scott') #256)

        centers = (edges[:-1] + edges[1:]) * 0.5

        self.plot.setData(centers, counts)

        self.updateLUT()

    def updateLUT(self):
        for im in self.images:
            im.setLevels(self.getLevels())
            im.setLookupTable(self.gradient.getLookupTable(nPts=256, alpha=True))

    def updateLUTRegion(self):
        try:
            self.updateHistogram()
            self.region.setRegion(self.plot.getData()[0][[0, -1]])
            self._pending_region_change = False
        except IndexError as e:
            pass
        



class ContextMenu(QtWidgets.QMenu):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.build_analysis_menu()

    def build_analysis_menu(self):
        # --- Markers ---
        m_markers = self.addMenu("Markers")
        act_marker_mode = m_markers.addAction("Marker mode")
        act_export_marker = m_markers.addAction("Export marker")

        # --- Transformations ---
        m_trans = self.addMenu("Transformations")
        act_fft = m_trans.addAction("FFT")
        act_logx = m_trans.addAction("LogX")
        act_logy = m_trans.addAction("LogY")

        m_deriv = m_trans.addMenu("Derivatives")
        act_first = m_deriv.addAction("First")
        act_second = m_deriv.addAction("Second")
        act_third = m_deriv.addAction("Third")

        # --- Marginals (checkable) ---
        m_marg = self.addMenu("Marginals")
        act_marg_x = m_marg.addAction("X")
        act_marg_x.setCheckable(True)
        act_marg_y = m_marg.addAction("Y")
        act_marg_y.setCheckable(True)

        # Dummy handlers
        def on_triggered(label: str, checked: bool = False):
            print(f"Triggered: {label} (checked={checked})")

        for a, label in [
            (act_marker_mode, "Markers > Marker mode"),
            (act_export_marker, "Markers > Export marker"),
            (act_fft, "Transformations > FFT"),
            (act_logx, "Transformations > LogX"),
            (act_logy, "Transformations > LogY"),
            (act_first, "Transformations > Derivatives > First"),
            (act_second, "Transformations > Derivatives > Second"),
            (act_third, "Transformations > Derivatives > Third"),
        ]:
            a.triggered.connect(partial(on_triggered, label))

        act_marg_x.toggled.connect(partial(on_triggered, "Marginals > X"))
        act_marg_y.toggled.connect(partial(on_triggered, "Marginals > Y"))


plot_library = {
    "LinePlot": LinePlot,
    "ScatterPlot": ScatterPlot,
    "Counts": Counts,
    "HeatMap": Map,
}

class GraphManager:
    def __init__(self,
                 main_window,
                 data_pack):

        self.main_window = main_window
        self.data_pack = data_pack
        self.graphs = {}

    def create_graphs(self):
        '''
        Creates instances of Graph for each graph defined in the layout dict.
        '''
        layout = self.data_pack.get("layout", {})
        for graph_name, graph_config in layout.items():
            graph = Graph(graph_name, graph_config)
            self.graphs[graph_name] = graph


    def update_data(self):
        '''
        Updates the data in each graph.
        '''
        data = self.data_pack.get("data", {})
        for graph_name, graph_data in data.items():
            graph = self.graphs.get(graph_name)
            if not graph:
                continue
            graph.updateData(graph_data)


    def apply_layout(self):
        for graph_name, graph in self.graphs.items():
            self.main_window.addDockWidget(
                QtCore.Qt.DockWidgetArea.LeftDockWidgetArea, graph
            )

class CustomViewBox(pg.ViewBox):
    """Custom menu by overriding raiseContextMenu (pyqtgraph calls this)."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("enableMenu", True)  # IMPORTANT: must be True
        super().__init__(*args, **kwargs)
        self._menu: QtWidgets.QMenu | None = None

    def _menu_parent(self) -> QtWidgets.QWidget | None:
        sc = self.scene()
        if sc:
            vs = sc.views()
            if vs:
                return vs[0]  # the GraphicsView (QWidget)
        return None

    def _ensure_menu(self):
        parent = self._menu_parent()
        if self._menu is None or self._menu.parent() is not parent:
            self._menu = ContextMenu(parent)

    def raiseContextMenu(self, ev):
        # Called by pyqtgraph when right-click/context-menu happens in the ViewBox
        self._ensure_menu()
        pos = ev.screenPos().toPoint() if hasattr(ev, "screenPos") else QtGui.QCursor.pos()
        self._menu.popup(pos)
        ev.accept()  # suppress the native menu


class Graph(QDockWidget):
    def __init__(self,
                 name,
                 config):

        super().__init__()

        self.name = name
        self.config = config
        self.layout_widget = pg.GraphicsLayoutWidget()
        self.plots = {}
        self.lut_item = None

        self.viewBox = CustomViewBox()

        self.penIndex = 0

        # Set up the dock widget properties
        self.setFloating(True)
        self.setAllowedAreas(QtCore.Qt.DockWidgetArea.AllDockWidgetAreas)
        self.parse_config()

        self.setWidget(self.layout_widget)

        

    def parse_config(self):
        x_label = self.config.get("x_label", "X-Axis")
        y_label = self.config.get("y_label", "Y-Axis")

        self.main_plot_item = self.layout_widget.addPlot(1, 0, 1, 1, viewBox = self.viewBox) #row=0, col=0, row_span=2, col_span=2)
        self.main_plot_item.setLabel(axis="left", text=y_label)
        self.main_plot_item.setLabel(axis="bottom", text=x_label)
        self.main_plot_item.showGrid(x=True, y=True)


        if any(part["type"] == "HeatMap" for part in self.config["content"].values()):
            self.lut_item = MultiHistogramLUTItem(orientation="horizontal")  #pg.HistogramLUTItem()
            self.layout_widget.addItem(self.lut_item, 0, 0, 1, 1)#row=0, col=1, span = 2)

        for part_name, part_config in self.config["content"].items():
            pen = self.get_pen(part_config)

            plot_type = part_config["type"]
            
            if plot_type not in plot_library:
                raise ValueError(f"Unknown plot type: {plot_type}")

            plot_instance = plot_library[plot_type]()
            plot_instance.updateLayout(self.main_plot_item, part_name, part_config, pen=pen)

            # Link the LUT to the heatmap
            if plot_type == "HeatMap" and self.lut_item:
                # self.lut_item.setImageItem(plot_instance.plotItem)
                self.lut_item.addImages(plot_instance.plotItem)


            self.plots[part_name] = plot_instance

        if any(part["type"] == "HeatMap" for part in self.config["content"].values()):
            self.bottom_marginal, self.right_marginal = self.addMarginals()

            self.horizontal_crosshair = self.addCrosshair(angle=0)
            self.vertical_crosshair = self.addCrosshair(angle=90)

            self.horizontal_crosshair.sigPositionChanged.connect(self.updateMarginals)
            self.vertical_crosshair.sigPositionChanged.connect(self.updateMarginals)

        # self.checklist = CheckboxList(list(self.plots.keys()), self)
        # self.layout_widget.addItem(self.checklist, 0, 0, 1, 1)  # row=1, col=0, span=1, col_span=2


    def get_pen(self, part_config):
        if "pen" in part_config:
            return part_config["pen"]

        elif "color" in part_config:
            width = part_config.get("width", WIDTH)
            return pg.mkPen(color=part_config["color"], width=width)

        elif "width" in part_config:
            width = part_config["width"]
            pen = penRotation[self.penIndex % len(penRotation)]
            self.penIndex += 1
            return pg.mkPen(color=pen.color(), width=width)

        pen = penRotation[self.penIndex % len(penRotation)]
        self.penIndex += 1
        return pen

    def updateData(self, data):
        for part_name, plot in self.plots.items():
            if part_name in data:
                plot.updateData(data[part_name])

    def addMarginals(self):
        layout = self.layout_widget.ci.layout
        bottom_marginal = self.layout_widget.addPlot(2, 0, 1, 1)
        bottom_marginal.setLabel(axis="left", text="Bottom Marginal")
        layout.setRowStretchFactor(1, 2)
        right_marginal = self.layout_widget.addPlot(1, 1, 1, 1)
        right_marginal.setLabel(axis="bottom", text="Right Marginal")
        layout.setColumnStretchFactor(0, 2)

        return bottom_marginal.plot(pen=pg.mkPen(color='black', width=2)), right_marginal.plot(pen=pg.mkPen(color='black', width=2))

    def addCrosshair(self, angle, pos = 0):
        line = pg.InfiniteLine(angle=angle,
                               movable=True,
                               pen=pg.mkPen(color='r', width=2))
        line.setZValue(1000)
        line.setPos(pos)
        line.setBounds([-10, 100])

        self.main_plot_item.addItem(line)

        return line

    def updateMarginals(self):
        self.bottom_marginal.setData(*self.get_marginal_data("horizontal"))
        self.right_marginal.setData(*self.get_marginal_data("vertical"))

    def get_marginal_data(self, position):
        x_data = []
        y_data = []

        for plot in self.plots.values():
            if isinstance(plot, Map):
                if position == "horizontal":
                    if self.horizontal_crosshair.value() >= plot.y_values[0] and self.horizontal_crosshair.value() <= plot.y_values[-1]:
                        x_data.extend(plot.x_values)
                        y_data.extend(plot.z_values[:, np.argmin(np.abs(plot.y_values - self.horizontal_crosshair.value()))])
                    else:
                        x_data.extend([])
                        y_data.extend([])
                elif position == "vertical":
                    if self.vertical_crosshair.value() >= plot.x_values[0] and self.vertical_crosshair.value() <= plot.x_values[-1]:
                        y_data.extend(plot.y_values)
                        x_data.extend(plot.z_values[np.argmin(np.abs(plot.x_values - self.vertical_crosshair.value())), :])
                    else:
                        x_data.extend([])
                        y_data.extend([])

        return np.array(x_data), np.array(y_data)

class PlotWidget(QWidget):
    """
    Creates a widget representing plots.
    """

    def __init__(self,
                 layout: dict,
                 progress_bar: bool = False,
                 metadata: dict = None):

        super().__init__()
        self.graphs = {}
        self._buildWidget(layout, metadata)




    def _buildWidget(self,
                     layout: dict,
                     metadata: dict = None):

        vertical_layout = QVBoxLayout()
        plot_layout = QGridLayout()
        graph_widget = QWidget()
        graph_widget.setLayout(plot_layout)

        for key, value in layout.items():
            self.graphs[key] = Graph(key, value)

            plot_layout.addWidget(
                self.graphs[key],
                layout[key]['loc'][0],
                layout[key]['loc'][1],
                layout[key]['loc'][2],
                layout[key]['loc'][3]
            )

        self.progressBar = QProgressBar(self)
        self.progressBar.setValue(0)
        self.progressBar.setMaximum(layout.get("n_iterations", 1_000_000))
        self.progressBar.setFormat("{}/{}".format(0, layout.get("n_iterations", 1_000_000)))

        vertical_layout.addWidget(self.progressBar)
        vertical_layout.addWidget(graph_widget)



        if metadata:
            self.lineEdits = {}
            metadataWidget = QWidget()
            metadataLayout = QFormLayout()

            for attribute, value in metadata.items():
                line_edit = QLineEdit(value)
                metadataLayout.addRow(QLabel(attribute), line_edit)
                self.lineEdits[attribute] = line_edit

            metadataWidget.setLayout(metadataLayout)
            vertical_layout.addWidget(metadataWidget)


        self.setLayout(vertical_layout)

    def updateData(self, data_pack):
        for key, graph in self.graphs.items():
            graph.updateData(
                data_pack.get(key, {})
            )
        self.progressBar.setValue(data_pack.get("iter", 0))

        metaData = data_pack.get('metadata', None)

        if metaData is not None:
            for attribute, value in metaData.items():
                self.lineEdits[attribute].setText(value)
        # self.progressBar.setFormat("{}/{}".format(
        #     data_pack.get("iter", 0),
        #     data_pack.get("n_iterations", 1_000_000)
        # ))

if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication, QMainWindow

    app = QApplication(sys.argv)
    main_window = QMainWindow()
    main_window.setWindowTitle("Graph Manager Test with Custom Pens")
    main_window.resize(1200, 800)

    map_data = np.random.random((100, 100))
    map_data[0,0] = np.nan
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
                    "part1": {"type": "LinePlot", "pen": pg.mkPen("black", width=5)},
                    "part2": {"type": "HeatMap"},
                    "part3": {"type": "HeatMap"}
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
                "part1": {
                    "x": np.linspace(0, 10, 100),
                    "y": np.linspace(0, 10, 100),
                    'color' : 'black'
                },
                "part2": {
                    "x": np.linspace(0, 10, 100),
                    "y": np.linspace(0, 10, 100),
                    "z": np.random.random((100, 100)),
                },
                "part3": {
                    "x": np.linspace(5, 15, 100),
                    "y": np.linspace(10, 20, 100),
                    "z": np.random.random((100, 100))*2,
                },
            },
        },
    }

    # # Create and apply GraphManager
    # manager = GraphManager(main_window, data_pack)
    # manager.create_graphs()
    # manager.update_data()
    # manager.apply_layout()

    plot_widget = PlotWidget(
        layout=data_pack["layout"],
        metadata=data_pack.get("metadata", None),
        progress_bar=False
    )
    plot_widget.updateData(data_pack["data"])

    main_window.setCentralWidget(plot_widget)
    main_window.show()
    sys.exit(app.exec())
