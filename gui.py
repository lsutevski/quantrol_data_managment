
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pyqtgraph as pg
from PyQt6 import QtCore
from PyQt6.QtCore import (
    Qt, QTimer
)
from PyQt6.QtWidgets import (
    QMainWindow,
    QVBoxLayout,
    QWidget,
    QHBoxLayout,
    QPushButton,
    QFrame,
    QFileDialog,
    QDialog,
    QLabel,
    QSpinBox,
    QDoubleSpinBox,
    QDialogButtonBox,
    QLineEdit,
    QFormLayout,
    QProgressBar,
    QGridLayout,
    QDockWidget,
)

from backend import CoreBackend
from plots import PlotWidget
from input_output import DataReceiver, DataFromFile

left  = 0.125  # the left side of the subplots of the figure
right = 0.9    # the right side of the subplots of the figure
bottom = 0.1   # the bottom of the subplots of the figure
top = 0.9      # the top of the subplots of the figure
wspace = 0.2   # the amount of width reserved for blank space between subplots
hspace = 0.2   # the amount of height reserved for white space between subplots

class MainWindow(QMainWindow):
    def __init__(self, backend: CoreBackend):
        super().__init__()


        self._createLayout()

        self.backend = backend

        self.plotWidget = None

        self.backend.layoutReady.connect(self.initPlotWidget)
        self.backend.dataReady.connect(self.updateData)


    def _createLayout(self):
        self.setWindowTitle("My Application")
        self.resize(800, 600)

        # — Top toolbar area —
        toolbar = QWidget()
        tlayout = QHBoxLayout()
        tlayout.setSpacing(5)
        tlayout.setContentsMargins(5, 5, 5, 5)

        self.start_btn = QPushButton("Start")
        self.start_btn.setEnabled(True)
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setEnabled(False)
        self.load_btn = QPushButton("Load")
        self.config_btn = QPushButton("Configure")
        self.reload_btn = QPushButton("Reload")

        for btn in (
            self.start_btn, self.stop_btn,
            self.load_btn, self.config_btn, self.reload_btn
        ):
            btn.setFixedHeight(24)
            tlayout.addWidget(btn)

        # Spacer to push LED to far right
        tlayout.addStretch()

        # LED indicator (red by default) on far right
        self.led = QFrame()
        self.led.setFixedSize(16, 16)
        self.led_off_style = """
            QFrame {
                background-color: #f0f0f0;
                border: 1px solid #ccc;
                border-radius: 4px;
            }
        """
        self.led_on_style = """
            QFrame {
                background-color: #4caf50;   /* green “on” */
                border: 1px solid #388e3c;
                border-radius: 4px;
            }
        """
        self.led.setStyleSheet(self.led_off_style)

        tlayout.addWidget(self.led)

        toolbar.setLayout(tlayout)
        toolbar.setFixedHeight(34)

        # — Main widget area —
        self.main_frame = QFrame()
        self.main_frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.main_frame.setStyleSheet(
            "QFrame { background-color: #f0f0f0; border: 1px solid #ccc; border-radius: 4px; }"
        )

        # — Assemble central widget —
        central = QWidget()
        vbox = QVBoxLayout()
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)
        vbox.addWidget(toolbar)
        vbox.addWidget(self.main_frame, 1)
        central.setLayout(vbox)
        self.setCentralWidget(central)

        self.main_layout = QVBoxLayout()
        self.main_frame.setLayout(self.main_layout)

        # — Connections —
        self.start_btn.clicked.connect(self.start)
        self.stop_btn.clicked.connect(self.stop)
        self.load_btn.clicked.connect(self.load_file)
        self.reload_btn.clicked.connect(lambda: print("Reloading…"))
        self.config_btn.clicked.connect(self.open_config)

    def load_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load file")

        if path:
            self.backend.setDataReceiver('file', path)

    def open_config(self):
        dlg = ConfigDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            port, rate = dlg.get_values()
            self.backend._setParams(port=port, rate=rate)
            self.backend.setDataReceiver('live')
            print(f"Configured port={port}, rate={rate}s")

    def start(self):
        if self.backend.dataReceiver is None:
            self.backend.setDataReceiver('live')
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

    def stop(self):
        if self.backend.dataReceiver is not None:
            self.backend.setDataReceiver(None)
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def initPlotWidget(self):
        try:
            self.clearPlotWidget()
        except AttributeError:
            pass

        if isinstance(self.backend.dataReceiver, DataReceiver):
            progress_bar = True
        else:
            progress_bar = False


        self.plotWidget = PlotWidget(self.backend.layout,
                                     metadata=self.backend.data.get('metadata', None),
                                     progress_bar=progress_bar)

        self.main_layout.addWidget(self.plotWidget)

    def clearPlotWidget(self):
        if self.plotWidget is not None:
            self.plotWidget.setParent(None)
            self.plotWidget = None

    def updateData(self):
        self.led.setStyleSheet(self.led_on_style)
        QTimer.singleShot(1000, lambda: self.led.setStyleSheet(self.led_off_style))
        if self.plotWidget is not None:
            self.plotWidget.updateData(self.backend.data.get('data', {}))

class ConfigDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configure")


        # Port input
        port_label = QLabel("Port:")
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(parent.backend.port)

        hl_port = QHBoxLayout()
        hl_port.addWidget(port_label)
        hl_port.addWidget(self.port_spin)
        hl_port.addStretch()

        # Refresh rate
        rate_label = QLabel("Refresh rate (s):")
        self.rate_spin = QDoubleSpinBox()
        self.rate_spin.setRange(100, 10_000)
        self.rate_spin.setSingleStep(10)
        self.rate_spin.setDecimals(0)
        self.rate_spin.setValue(parent.backend.rate)

        hl_rate = QHBoxLayout()
        hl_rate.addWidget(rate_label)
        hl_rate.addWidget(self.rate_spin)
        hl_rate.addStretch()

        # OK / Cancel
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        # Layout
        vbox = QVBoxLayout()
        vbox.setContentsMargins(10, 10, 10, 10)
        vbox.setSpacing(10)
        vbox.addLayout(hl_port)
        vbox.addLayout(hl_rate)
        vbox.addWidget(buttons)
        self.setLayout(vbox)
        self.setFixedSize(360, 140)

    def get_values(self):
        return self.port_spin.value(), self.rate_spin.value()








