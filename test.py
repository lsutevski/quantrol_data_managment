from PyQt6 import QtWidgets, QtCore, QtGui
import pyqtgraph as pg
import numpy as np

# ---------------- Legend with tabs + hierarchical groups ----------------
class LegendTabs(QtWidgets.QTabWidget):
    """Tabbed legend. Each tab hosts a tri-state QTreeWidget of groups/items."""
    def __init__(self, tabs_spec, parent=None):
        """
        tabs_spec: dict[str, list[group_or_item]]
          group_or_item can be:
            - ("Label", pyqtgraph_object)  -> leaf
            - ("Group Label", [ ... children ... ]) -> group
        """
        super().__init__(parent)
        self._trees = {}
        for tab_name, nodes in tabs_spec.items():
            tree = QtWidgets.QTreeWidget()
            tree.setHeaderHidden(True)
            tree.setUniformRowHeights(True)
            tree.setAnimated(True)
            tree.setIndentation(18)
            tree.itemChanged.connect(self._on_item_changed)
            self._build_tree(tree, None, nodes)
            self.addTab(self._wrap_with_toolbar(tree), tab_name)
            self._trees[tab_name] = tree

    # toolbar with Show/Hide all for the current tab
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
        btnShow.clicked.connect(lambda: self._set_all_in_tree(tree, QtCore.Qt.CheckState.Checked))
        btnHide.clicked.connect(lambda: self._set_all_in_tree(tree, QtCore.Qt.CheckState.Unchecked))
        return w

    # ---- tree build helpers
    def _build_tree(self, tree, parent_item, nodes):
        for entry in nodes:
            label, payload = entry
            if isinstance(payload, list):  # group
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

    # ---- interactions
    def _on_item_changed(self, item, column):
        if column != 0:
            return
        # Block recursion while we update children/targets
        tree = item.treeWidget()
        if tree is None:
            return
        tree.blockSignals(True)
        try:
            state = item.checkState(0)
            target = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
            if target is not None:
                # leaf -> toggle the pyqtgraph object
                visible = (state == QtCore.Qt.CheckState.Checked)
                try:
                    target.setVisible(visible)
                except Exception:
                    pass
            else:
                # group -> cascade to children
                for i in range(item.childCount()):
                    child = item.child(i)
                    child.setCheckState(0, state)
        finally:
            tree.blockSignals(False)

    def _set_all_in_tree(self, tree, state):
        tree.blockSignals(True)
        try:
            for i in range(tree.topLevelItemCount()):
                it = tree.topLevelItem(i)
                it.setCheckState(0, state)
        finally:
            tree.blockSignals(False)
        # Manually trigger visibility sync for leaves
        self._sync_visibility(tree)

    def _sync_visibility(self, tree):
        def walk(item):
            target = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
            if target is not None:
                try:
                    target.setVisible(item.checkState(0) == QtCore.Qt.CheckState.Checked)
                except Exception:
                    pass
            for i in range(item.childCount()):
                walk(item.child(i))
        for i in range(tree.topLevelItemCount()):
            walk(tree.topLevelItem(i))

# ---------------- Splitter with handle button to tuck legend ----------------
class ToggleHandle(QtWidgets.QSplitterHandle):
    def __init__(self, orientation, parent):
        super().__init__(orientation, parent)
        self._saved_width = 220
        self._legend_index = 1  # right pane
        self.btn = QtWidgets.QToolButton(self)
        self.btn.setAutoRaise(True)
        self.btn.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.btn.setFixedSize(18, 18)
        self.btn.clicked.connect(self.toggleLegend)
        parent.splitterMoved.connect(self._updateArrow)
        self._updateArrow()

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        self.btn.move((self.width()-self.btn.width())//2, (self.height()-self.btn.height())//2)

    def legendVisible(self):
        sizes = self.splitter().sizes()
        return len(sizes) > self._legend_index and sizes[self._legend_index] > 5

    def _updateArrow(self, *args):
        vis = self.legendVisible()
        self.btn.setArrowType(QtCore.Qt.ArrowType.RightArrow if vis else QtCore.Qt.ArrowType.LeftArrow)
        self.btn.setToolTip("Hide legend" if vis else "Show legend")

    def toggleLegend(self):
        s = self.splitter()
        sizes = s.sizes()
        if self.legendVisible():
            self._saved_width = max(160, sizes[self._legend_index])
            sizes[self._legend_index] = 0
            sizes[1 - self._legend_index] = max(1, sum(sizes) - 0)
        else:
            sizes[self._legend_index] = self._saved_width
            sizes[1 - self._legend_index] = max(1, sum(sizes) - self._saved_width)
        s.setSizes(sizes)
        self._updateArrow()

class TuckableSplitter(QtWidgets.QSplitter):
    def createHandle(self):
        return ToggleHandle(self.orientation(), self)

# ---------------- Demo window ----------------
class Main(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Tabbed hierarchical legend + handle toggle")

        glw = pg.GraphicsLayoutWidget()
        p = glw.addPlot(row=0, col=0, title="Demo Plot"); p.showGrid(x=True, y=True)
        x = np.linspace(0, 10, 1000)

        # Items
        sine   = p.plot(x, np.sin(x),       pen=pg.mkPen('#d62728', width=2), name='Sine')
        cosine = p.plot(x, np.cos(x),       pen=pg.mkPen('#2ca02c', width=2), name='Cosine')
        harm3  = p.plot(x, 0.3*np.sin(3*x), pen=pg.mkPen('#1f77b4', width=2), name='3×Sine')
        scat   = pg.ScatterPlotItem(x[::40], np.sin(x[::40]), pen=None, brush=(100,100,255,180), size=7)
        p.addItem(scat)

        # ----- Define tabbed hierarchy
        legend_spec = {
            "Signals": [
                ("Sinusoids", [
                    ("Sine", sine),
                    ("Cosine", cosine),
                ]),
                ("Harmonics", [
                    ("3×Sine", harm3),
                ]),
            ],
            "Points / ROIs": [
                ("Scatter", scat),
                # You can add groups here, e.g. ("User ROIs", [("ROI 1", roi1), ("ROI 2", roi2)])
            ],
        }

        legend = LegendTabs(legend_spec)

        splitter = TuckableSplitter(QtCore.Qt.Orientation.Horizontal)
        splitter.setHandleWidth(28)
        splitter.addWidget(glw)
        splitter.addWidget(legend)
        splitter.setChildrenCollapsible(True)
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, True)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)
        splitter.setSizes([900, 260])

        cw = QtWidgets.QWidget()
        lay = QtWidgets.QHBoxLayout(cw)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(splitter)
        self.setCentralWidget(cw)
        self.resize(1150, 640)

def main():
    app = QtWidgets.QApplication([])
    win = Main(); win.show()
    app.exec()

if __name__ == "__main__":
    main()
