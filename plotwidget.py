from abc import ABC, abstractmethod
import pyqtgraph as pg
from PyQt6.QtWidgets import QTabWidget, QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, QProgressBar, QFormLayout, QLabel, QLineEdit, QDialog
import numpy as np
import sys
import cmasher as cmr

from pyqtgraph.dockarea import DockArea, Dock
from graph import Graph

MAP_LAYER = -3
LINE_LAYER = -2
SCATTER_LAYER = -1

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

    def _buildWidget(self, layout: dict, metadata: dict = None):
        self.graphs = {}
        vertical_layout = QVBoxLayout(self)

        self.progressBar = QProgressBar(self)
        self.progressBar.setValue(0)
        self.progressBar.setMaximum(layout.get("n_iterations", 1_000_000))
        self.progressBar.setFormat("{}/{}".format(0, layout.get("n_iterations", 1_000_000)))
        vertical_layout.addWidget(self.progressBar)

        

        # ---- DockArea with per-plot Docks ----
        self.area = DockArea()
        vertical_layout.addWidget(self.area, 1)  # stretch
        # (Optional) metadata panel
        if metadata:
            self.lineEdits = {}
            metadataWidget = QWidget()
            metadataLayout = QFormLayout(metadataWidget)
            for attribute, value in metadata.items():
                le = QLineEdit(value)
                metadataLayout.addRow(QLabel(attribute), le)
                self.lineEdits[attribute] = le
            vertical_layout.addWidget(metadataWidget)

        docks = {}
        # Create all Graphs and wrap each one in a Dock
        for key, cfg in layout.items():
            g = Graph(key, cfg)
            self.graphs[key] = g
            d = Dock(key, size=(400, 300))
            d.addWidget(g)
            docks[key] = d

        # --- Place docks in a GRID using your 'loc': (row, col, row_span, col_span) ---
        # Simple strategy: left-to-right within a row, rows stacked top-to-bottom.
        # Spans are ignored here, but can be added if you use them.
        # Build row -> [(col, name), ...]
        rowmap = {}
        for name, cfg in layout.items():
            r, c, rs, cs = cfg['loc']
            rowmap.setdefault(r, []).append((c, name))

        sorted_rows = sorted(rowmap.keys())
        prev_row_first = None
        for r in sorted_rows:
            row_elems = sorted(rowmap[r], key=lambda t: t[0])
            for i, (_, name) in enumerate(row_elems):
                if r == sorted_rows[0] and i == 0:
                    self.area.addDock(docks[name], position='left')
                elif i > 0:
                    left_name = row_elems[i-1][1]
                    self.area.addDock(docks[name], position='right', relativeTo=docks[left_name])
                else:
                    # first in a new row → put it below the first dock of the previous row
                    self.area.addDock(docks[name], position='bottom', relativeTo=docks[prev_row_first])
            prev_row_first = row_elems[0][1]

        # EXAMPLE: make initial tab-stacks (optional)
        # if you want Plot3 tabbed with Plot1 right away:
        # self.area.addDock(docks['Plot3'], position='above', relativeTo=docks['Plot1'])

        # Save/restore helpers (optional)
        self._initial_state = self.area.saveState()

    def save_layout_state(self):
        return self.area.saveState()

    def restore_layout_state(self, state):
        self.area.restoreState(state)




    # def _buildWidget(self,
    #                  layout: dict,
    #                  metadata: dict = None):

    #     vertical_layout = QVBoxLayout()
    #     plot_layout = QGridLayout()
    #     graph_widget = QWidget()
    #     graph_widget.setLayout(plot_layout)

    #     for key, value in layout.items():
    #         self.graphs[key] = Graph(key, value)

    #         plot_layout.addWidget(
    #             self.graphs[key],
    #             layout[key]['loc'][0],
    #             layout[key]['loc'][1],
    #             layout[key]['loc'][2],
    #         

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
        "metadata": {
            "experiment": "Test Experiment",
            "date": "2023-10-01",
            "author": "John Doe"
        },
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
                "loc": (0, 1, 1, 1),
            },
            "Plot3": {
                "content": {
                    "part1": {"type": "LinePlot", "pen": pg.mkPen("black", width=5)},
                    "part2": {"type": "HeatMap"},
                    "part3": {"type": "HeatMap"}
                },
                "y_label": "Intensity",
                "x_label": "X-Axis",
                "loc": (1, 0, 1, 1),
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
                    "y": np.linspace(5, 20, 100),
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
