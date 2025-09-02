from abc import ABC, abstractmethod
import pyqtgraph as pg
from PyQt6 import QtCore, QtWidgets, QtGui
from PyQt6.QtCore import pyqtSignal as Signal, pyqtSlot as Slot, Qt, QPointF
from PyQt6.QtWidgets import QTabWidget, QDialog, QFileDialog, QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, QGridLayout, QProgressBar, QDockWidget, QFormLayout, QLabel, QLineEdit
import numpy as np
import sys
import cmasher as cmr
from functools import partial
from plots import plot_library, MultiHistogramLUTItem, Map
from plot_utils import ContextMenu, CustomViewBox, Markers, LegendTabs
from typing import Optional

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
pg.setConfigOption('foreground', "#020202")         # axes, labels, text\


right_marginal_slot = dict(
    row=1, col=1, rowspan=1, colspan=1
)
bottom_marginal_slot = dict(
    row=2, col=0, rowspan=1, colspan=1
)

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

        self.viewBox = CustomViewBox(widget=self.layout_widget)
        self.viewBox.menu.act_marker_mode.triggered.connect(self.set_marker_mode)
        self.viewBox.menu.act_fft.triggered.connect(self._on_fft)
        self.viewBox.menu.act_legend.triggered.connect(self._on_legend)

        self.penIndex = 0

        self._show_marginals = False
        self._x_marginal = False
        self._y_marginal = False
        self._marker_mode = False

        # Set up the dock widget properties
        self.setFloating(True)
        self.setAllowedAreas(QtCore.Qt.DockWidgetArea.AllDockWidgetAreas)

        self.parse_config()

        self.setWidget(self.layout_widget)

        

    def parse_config(self):
        image_counter = 0
        self.images = []

        x_label = self.config.get("x_label", "X-Axis")
        y_label = self.config.get("y_label", "Y-Axis")

        self.main_plot_item = self.layout_widget.addPlot(1, 0, 1, 1, viewBox = self.viewBox) #row=0, col=0, row_span=2, col_span=2)
        self.main_plot_item.setLabel(axis="left", text=y_label)
        self.main_plot_item.setLabel(axis="bottom", text=x_label)
        self.main_plot_item.showGrid(x=True, y=True)

        self.markers = Markers(self.main_plot_item)

        if any(part["type"] == "HeatMap" for part in self.config["content"].values()):
            self.lut_item = MultiHistogramLUTItem(orientation="horizontal")
            self.layout_widget.addItem(self.lut_item, 0, 0, 1, 1)

        for part_name, part_config in self.config["content"].items():
            pen = self.get_pen(part_config)

            plot_type = part_config["type"]
            
            if plot_type not in plot_library:
                raise ValueError(f"Unknown plot type: {plot_type}")

            plot_instance = plot_library[plot_type]()
            plot_instance.updateLayout(self.main_plot_item, part_name, part_config, pen=pen, z_value = image_counter)

            if isinstance(plot_instance, Map) and self.lut_item:
                self.lut_item.addImages(plot_instance.plotItem)
                self.images.append(plot_instance)
                image_counter += 1

                print(plot_instance.plotItem.zValue())


            self.plots[part_name] = plot_instance

        if any(part["type"] == "HeatMap" for part in self.config["content"].values()):
            self.bottom_marginal, self.bottom_marginal_plots, self.right_marginal, self.right_marginal_plots = self.addMarginals()
            self.bottom_marginal.setDefaultPadding(0.0)
            self.bottom_marginal.setXLink(self.main_plot_item)
            self.right_marginal.setDefaultPadding(0.0)
            self.right_marginal.setYLink(self.main_plot_item)


            
            self._hideMarginalPlots(marginal="horizontal")
            self._hideMarginalPlots(marginal="vertical")

            self.horizontal_crosshair = self.addCrosshair(angle=0)
            self.horizontal_crosshair.hide()
            self.vertical_crosshair = self.addCrosshair(angle=90)
            self.vertical_crosshair.hide()

            self.horizontal_crosshair.sigPositionChanged.connect(self.updateMarginals)
            self.vertical_crosshair.sigPositionChanged.connect(self.updateMarginals)

            self.marginals = True

            self.viewBox.menu.act_marg_x.toggled.connect(self.showMarginals)
            self.viewBox.menu.act_marg_y.toggled.connect(self.showMarginals)



        self.layout_widget.scene().sigMouseClicked.connect(self._on_mouse_click)

        

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

        bottom_marginal_plots = []
        right_marginal_plots = []
        for image in self.lut_item.images:
            bottom_marginal_plots.append(bottom_marginal.plot(pen=pg.mkPen(color='black', width=2)))
            right_marginal_plots.append(right_marginal.plot(pen=pg.mkPen(color='black', width=2)))

        return bottom_marginal, \
               bottom_marginal_plots, \
               right_marginal, \
               right_marginal_plots

    def showMarginals(self, *args):
        x = self.viewBox.menu.act_marg_x.isChecked()
        y = self.viewBox.menu.act_marg_y.isChecked()

        if x and not self._x_marginal:
            self.horizontal_crosshair.show()
            self.layout_widget.addItem(self.bottom_marginal, **bottom_marginal_slot)
            self._x_marginal = True
        elif not x and self._x_marginal:
            self.horizontal_crosshair.hide()
            self._hideMarginalPlots("horizontal")
            self._x_marginal = False

        if y and not self._y_marginal:
            self.vertical_crosshair.show()
            self.layout_widget.addItem(self.right_marginal, **right_marginal_slot)
            self._y_marginal = True
        elif not y and self._y_marginal:
            self.vertical_crosshair.hide()
            self._hideMarginalPlots("vertical")
            self._y_marginal = False

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
        if self.marginals:
            self.update_marginal_data("horizontal")
            self.update_marginal_data("vertical")

    def update_marginal_data(self, position):
        x_data = []
        y_data = []

        for i, image in enumerate(self.images):
            if position == "horizontal":
                if (self.horizontal_crosshair.value() >= image.y_values[0] and 
                    self.horizontal_crosshair.value() <= image.y_values[-1]):
                    self.bottom_marginal_plots[i].setData(
                        np.array(image.x_values),
                        np.array(image.z_values[:, np.argmin(np.abs(image.y_values - self.horizontal_crosshair.value()))]))
                else:
                    self.bottom_marginal_plots[i].setData([], [])
            elif position == "vertical":
                if self.vertical_crosshair.value() >= image.x_values[0] and self.vertical_crosshair.value() <= image.x_values[-1]:
                    self.right_marginal_plots[i].setData(
                        np.array(image.z_values[np.argmin(np.abs(image.x_values - self.vertical_crosshair.value())), :]),
                        np.array(image.y_values)
                    )
                else:
                    self.right_marginal_plots[i].setData([], [])

        return np.array(x_data), np.array(y_data)

    def _hideMarginalPlots(self, marginal: str):
        if marginal == "horizontal":
            self.layout_widget.removeItem(self.bottom_marginal)
        elif marginal == "vertical":
            self.layout_widget.removeItem(self.right_marginal)
    def _showMarginalPlots(self, marginal: str):
        if marginal == "horizontal":
            self.layout_widget.addItem(self.bottom_marginal, **bottom_marginal_slot)
        elif marginal == "vertical":
            self.layout_widget.addItem(self.right_marginal, **right_marginal_slot)

    def set_marker_mode(self, enabled: bool):
        self._marker_mode = enabled
        self.layout_widget.setCursor(Qt.CursorShape.CrossCursor if enabled else Qt.CursorShape.ArrowCursor)


    def _on_mouse_click(self, ev):
        if not self._marker_mode or ev.button() != Qt.MouseButton.LeftButton: return

        pos_scene = ev.scenePos() 
        pos_view: QPointF = self.viewBox.mapSceneToView(pos_scene) 
        x, y = pos_view.x(), pos_view.y()

        p0 = pos_scene
        p1 = QPointF(p0.x()+6, p0.y())
        d0 = self.viewBox.mapSceneToView(p0) 
        d1 = self.viewBox.mapSceneToView(p1)
        tol = abs(d1.x() - d0.x())
        if not self.markers.remove_near(x, y, tol_data=tol): 
            self.markers.add((x, y))

    def export_markers_csv(self, path: Optional[str] = None):
        if not self.markers: return
        if path is None:
            path, _ = QFileDialog.getSaveFileName(self, "Export markers CSV", "markers.csv", "CSV Files (*.csv)")
            if not path: return
        self.markers.export_csv(path)

    def _get_image_value(self, pos):
        im = None
        for image in self.lut_item.images:
            if (pos[0] > image.x_values[0] and
                pos[0] < image.x_values[-1] and
                pos[1] > image.y_values[0] and
                pos[1] < image.y_values[-1]):
                if im is None:
                    im = image
                elif im.getZValue() < image.getZValue():
                    im = image
        if im is None:
            return None
        else:
            return im.z_values[np.argmin(np.abs(im.y_values - pos[1])), np.argmin(np.abs(im.x_values - pos[0]))]

    def _on_fft(self):
        data = np.random.normal(size=1024)
        dialog = TransformPopup(data)
        dialog.exec()

    def _on_legend(self):
        legend = LegendTabs({
            'plots': {
                'single plot': self.plots
            }
        })
        legend.exec()

class TransformPopup(QDialog):
    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Data Transformations")
        self.resize(600, 400)

        layout = QVBoxLayout(self)

        tabs = QTabWidget()
        layout.addWidget(tabs)

        tab2D = Graph("2D data", cfg)
        
        # --- Tab 1: Original data ---
        tab1 = pg.PlotWidget()
        tab1.plot(data, pen='c')
        tabs.addTab(tab1, "Original")

        # --- Tab 2: FFT ---
        tab2 = pg.PlotWidget()
        fft_data = np.abs(np.fft.fft(data))
        tab2.plot(fft_data, pen='y')
        tabs.addTab(tab2, "FFT")

        # --- Tab 3: Log transform ---
        tab3 = pg.PlotWidget()
        log_data = np.log1p(np.abs(data))   # log(1+x) to avoid negatives
        tab3.plot(log_data, pen='m')
        tabs.addTab(tab3, "Log")