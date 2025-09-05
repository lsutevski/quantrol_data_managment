from abc import ABC, abstractmethod
import pyqtgraph as pg
from PyQt6 import QtCore, QtWidgets, QtGui
from PyQt6.QtCore import pyqtSignal as Signal, pyqtSlot as Slot, QSize
from PyQt6.QtWidgets import QTreeWidget, QTabWidget, QStyle
import numpy as np
import sys
import cmasher as cmr
from functools import partial

from pyqtgraph.dockarea import DockArea, Dock
from plots import plot_library

import math

class ContextMenu(QtWidgets.QMenu):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.build_analysis_menu()

    def build_analysis_menu(self):
        # --- Markers ---
        m_markers = self.addMenu("Markers")
        self.act_marker_mode = m_markers.addAction("Marker mode")
        self.act_marker_mode.setCheckable(True)
        self.act_export_marker = m_markers.addAction("Export marker")

        # --- Transformations ---
        m_trans = self.addMenu("Transformations")
        self.act_fft = m_trans.addAction("FFT")
        self.act_logx = m_trans.addAction("LogX")
        self.act_logy = m_trans.addAction("LogY")

        m_deriv = m_trans.addMenu("Derivatives")
        self.act_first = m_deriv.addAction("First")
        self.act_second = m_deriv.addAction("Second")
        self.act_third = m_deriv.addAction("Third")

        # --- Marginals (checkable) ---
        m_marg = self.addMenu("Marginals")
        self.act_marg_x = m_marg.addAction("X")
        self.act_marg_x.setCheckable(True)
        self.act_marg_y = m_marg.addAction("Y")
        self.act_marg_y.setCheckable(True)

        # --- Legends (checkable) ---
        m_legends = self.addMenu("Legends")
        self.act_legend = m_legends.addAction("Show Legend")
        self.act_legend.setCheckable(True)

        # Dummy handlers
        def on_triggered(label: str, checked: bool = False):
            print(f"Triggered: {label} (checked={checked})")

        for a, label in [
            (self.act_marker_mode, "Markers > Marker mode"),
            (self.act_export_marker, "Markers > Export marker"),
            (self.act_fft, "Transformations > FFT"),
            (self.act_logx, "Transformations > LogX"),
            (self.act_logy, "Transformations > LogY"),
            (self.act_first, "Transformations > Derivatives > First"),
            (self.act_second, "Transformations > Derivatives > Second"),
            (self.act_third, "Transformations > Derivatives > Third"),
        ]:
            a.triggered.connect(partial(on_triggered, label))

        self.act_marg_x.toggled.connect(partial(on_triggered, "Marginals > X"))
        self.act_marg_y.toggled.connect(partial(on_triggered, "Marginals > Y"))


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

class CustomViewBox(pg.ViewBox):
    """Custom menu by overriding raiseContextMenu (pyqtgraph calls this)."""

    def __init__(self, widget, *args, **kwargs):
        kwargs.setdefault("enableMenu", True)  # IMPORTANT: must be True
        super().__init__(*args, **kwargs)
        # sc = self.scene()
        # vs = sc.views()
        # parent = vs[0]  # the GraphicsView (QWidget)

        self.menu = ContextMenu(widget)

    def raiseContextMenu(self, ev):
        pos = ev.screenPos().toPoint() if hasattr(ev, "screenPos") else QtGui.QCursor.pos()
        self.menu.popup(pos)
        ev.accept()  # suppress the native menu

class Markers:
    def __init__(self, plot_item):
        self.plot_item = plot_item
        self.item = pg.ScatterPlotItem(size=9, 
                                       brush='y', 
                                       pen=pg.mkPen('k', width=1))
        self.plot_item.addItem(self.item)
        self.item.setZValue(1000)
        self.markers = []
    
    def _refresh_markers(self):
        self.item.setData(x=[m[0] for m in self.markers], 
                          y=[m[1] for m in self.markers])
        
    def add(self, pos):
        self.markers.append(pos)
        self._refresh_markers()

    def clear_markers(self):
        self.markers.clear()
        self._refresh_markers()

    def get_markers(self):
        return self.markers
    
    def remove_near(self, x: float, y: float, tol_data: float) -> bool:
        best_i, best_d = None, float("inf")
        for i, p in enumerate(self.markers):
            d = math.hypot(p[0] - x, p[1] - y)
            if d < best_d: 
                best_d, best_i = d, i
        if best_i is not None and best_d <= tol_data:
            self.markers.pop(best_i) 
            self._refresh_markers()
            return True
        return False

    def show(self):
        self.item.setVisible(True)
    
    def hide(self):
        self.item.setVisible(False)

    def export_csv(self, path: str):
        import csv
        with open(path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["x","y"])
            for p in self.markers: 
                w.writerow([p[0], p[1]])


class LegendTabs(QTabWidget):
    def __init__(self, tabs_spec, func, parent=None, closable=True, tab_name = "Legend"):
        super().__init__(parent)
        self._trees = {}
        self.setWindowTitle(tab_name)
        self.func = func
        for tab_name, nodes in tabs_spec.items():
            tree = QtWidgets.QTreeWidget()
            tree.itemChanged.connect(self.func)
            tree.setHeaderHidden(True)
            tree.setUniformRowHeights(True)
            tree.setAnimated(True)
            tree.setIndentation(18)
            # tree.itemChanged.connect(self._on_item_changed)
            self._build_tree(tree, None, nodes)
            self.addTab(self._wrap_with_toolbar(tree), tab_name)
            self._trees[tab_name] = tree

        self.setWindowFlags(QtCore.Qt.WindowType.Window | 
                            QtCore.Qt.WindowType.CustomizeWindowHint | 
                            QtCore.Qt.WindowType.WindowTitleHint)

    def _wrap_with_toolbar(self, tree):
        w = QtWidgets.QWidget()
        lay = QtWidgets.QVBoxLayout(w)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(6)
        row = QtWidgets.QHBoxLayout()
        btnShow = QtWidgets.QPushButton("Show all")
        btnHide = QtWidgets.QPushButton("Hide all")
        row.addWidget(btnShow); row.addWidget(btnHide); row.addStretch(1)
        lay.addLayout(row)
        lay.addWidget(tree, 1)
        # btnShow.clicked.connect(lambda: self._set_all_in_tree(tree, QtCore.Qt.CheckState.Checked))
        # btnHide.clicked.connect(lambda: self._set_all_in_tree(tree, QtCore.Qt.CheckState.Unchecked))
        return w
    
    # ---- tree build helpers
    def _build_tree(self, tree, parent_item, nodes):
        for entry in nodes.items():
            label, payload = entry
            if isinstance(payload, dict):  # group
                item = QtWidgets.QTreeWidgetItem([label])
                item.setFlags(item.flags() | QtCore.Qt.ItemFlag.ItemIsUserCheckable | QtCore.Qt.ItemFlag.ItemIsAutoTristate)
                item.setCheckState(0, QtCore.Qt.CheckState.Checked)
                if parent_item is None:
                    tree.addTopLevelItem(item)
                else:
                    parent_item.addChild(item)
                self._build_tree(tree, item, payload)
            else:  # leaf with a target object
                target = payload
                item = QtWidgets.QTreeWidgetItem([label])
                item.setFlags(item.flags() | QtCore.Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(0, QtCore.Qt.CheckState.Checked)
                # store target on the item
                item.setData(0, QtCore.Qt.ItemDataRole.UserRole, target)
                # color swatch icon (if the item has a pen color)
                icon = self._make_color_icon(getattr(getattr(target, "opts", {}), "get", lambda *_: None)("pen"))
                if icon is not None:
                    item.setIcon(0, icon)
                if parent_item is None:
                    tree.addTopLevelItem(item)
                else:
                    parent_item.addChild(item)
    
    def _make_color_icon(self, pen):
        try:
            if pen is None:
                return None
            qpen = pen if isinstance(pen, QtGui.QPen) else pg.mkPen(pen)
            col = qpen.color()
            pm = QtGui.QPixmap(12, 12)
            pm.fill(col)
            painter = QtGui.QPainter(pm)
            painter.setPen(QtGui.QColor(100,100,100))
            painter.drawRect(0, 0, 11, 11)
            painter.end()
            return QtGui.QIcon(pm)
        except Exception:
            return None
        

class ToggleLegendButton(QtWidgets.QToolButton):
    def __init__(self, widget : QtWidgets.QWidget, *args, **kwargs):
        super().__init__(*args, 
                         **kwargs)
        self.widget = widget
        self.collapsed = True
        self.set_icon()
        self.setAutoRaise(True)
    

        self.clicked.connect(self._toggle)

    def _toggle(self):
        self.collapsed = not self.collapsed
        self.widget.setVisible(not self.collapsed)
        self.set_icon()
       
    def set_icon(self):
        # we control the RIGHT (or BOTTOM) pane
        sp = QStyle.StandardPixmap.SP_ArrowRight if self.collapsed else QStyle.StandardPixmap.SP_ArrowLeft
        icon = self.style().standardIcon(sp)
        self.setIcon(icon)
        self.setIconSize(QSize(14, 14))

    