import sys
import zmq
from IPython.display import display
from matplotlib import pyplot as plt
from random import randrange
from threading import Thread
import time
from tqdm.notebook import tqdm

import pyqtgraph as pg
#from ..global_variables import START_EVENT, STOP_EVENT

from random import randint
import sys
#%gui qt6
import pyqtgraph as pg
from PyQt6 import QtCore, QtWidgets, QtGui
from PyQt6.QtCore import Qt, QObject, QThread, pyqtSignal as Signal, pyqtSlot as Slot, QTimer
from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QStyle, QGridLayout, QProgressBar, QDockWidget, QFormLayout, QLabel, QLineEdit, QStatusBar, QToolBar
from PyQt6.QtGui import QIcon, QAction
from time import sleep
from threading import Thread
import numpy as np
from cmap import Colormap

from live_plot_classes import *

DATA_PORT = 5555
CONTROL_PORT = 5556

pg.setConfigOption('background', 0.9)
pg.setConfigOption('foreground', 'k')

left  = 0.125  # the left side of the subplots of the figure
right = 0.9    # the right side of the subplots of the figure
bottom = 0.1   # the bottom of the subplots of the figure
top = 0.9      # the top of the subplots of the figure
wspace = 0.2   # the amount of width reserved for blank space between subplots
hspace = 0.2   # the amount of height reserved for white space between subplots



class MainWindow(QMainWindow):

    colors = []
    cmap = pg.colormap.get('CET-D1A')
    #colormap = pg.colormap.get('viridis', source='matplotlib')  # Use any colormap you like
    for i in range(4):
        color = cmap.map(i/4, 'qcolor')
        colors.append(color)

    penRotation = [pg.mkPen(color = c, width = 3) for c in colors]

    currentPens = {}

    cmap = pg.colormap.get('CET-L12')

    def __init__(self, zmq_socket):
        super().__init__()

        self.thread = QThread()

        self.timer = QTimer()
        self.timer.timeout.connect(self.updatePlots)

        self.layout = None

        self.zmq_socket = zmq_socket

        self.poller = zmq.Poller()
        self.poller.register(self.zmq_socket, zmq.POLLIN)
        #self._createLayout(self.layout)

    def _createLayout(self, data_pack):
        self.setWindowTitle("Measurement Live Plot")
        self.resize(1400, 1200)

        self.layout = data_pack['layout']
        plotLayout = QGridLayout()
        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        self.plotWidgets = {}

        verticalLayout = QVBoxLayout()
        horizontalLayout = QHBoxLayout()


        self.toolbar = QToolBar("Main Toolbar")
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.toolbar)

        self.start_action = QAction(self.style().standardIcon(
                                        self.style().StandardPixmap.SP_MediaPlay),
                                    "Start", self)
        self.start_action.triggered.connect(self._start)
        self.toolbar.addAction(self.start_action)

        self.stop_action = QAction(self.style().standardIcon(
                                        self.style().StandardPixmap.SP_MediaStop),
                                    "Stop", self)
        self.stop_action.triggered.connect(self._stop)
        self.toolbar.addAction(self.stop_action)

        self.save_action = QAction(self.style().standardIcon(
                                        self.style().StandardPixmap.SP_DialogSaveButton),
                                    "Save", self)
        self.save_action.triggered.connect(self._save)
        self.toolbar.addAction(self.save_action)

        self.load_action = QAction(self.style().standardIcon(
                                        self.style().StandardPixmap.SP_DialogOpenButton),
                                    "Load", self)
        self.toolbar.addAction(self.load_action)
        self.load_action.triggered.connect(self._load)

        self.redock_action = QAction(self.style().standardIcon(
                                        self.style().StandardPixmap.SP_BrowserReload),
                                    "Redock", self)
        self.redock_action.triggered.connect(self._redockAll)
        self.toolbar.addAction(self.redock_action)






        #self._stopData()



        # horizontalLayout.addWidget(self.startButton)
        # horizontalLayout.addWidget(self.stopButton)
        # horizontalLayout.addWidget(self.saveButton)
        # horizontalLayout.addWidget(self.redockButton)
        # horizontalLayout.addWidget(self.stopDataButton)


        self.plotItems = {}

        self.lineEdits = {}
        metaData = data_pack.get('metadata', None)

        if metaData is not None:
            metadataWidget = QWidget()
            metadataLayout = QFormLayout()

            for attribute, value in metaData.items():
                line_edit = QLineEdit(value)
                metadataLayout.addRow(QLabel(attribute), line_edit)
                self.lineEdits[attribute] = line_edit

            metadataWidget.setLayout(metadataLayout)

            #horizontalLayout.addWidget(metadataWidget)

        horizontalWidget = QWidget()
        horizontalWidget.setLayout(horizontalLayout)

        for key, value in self.layout.items():
            self.plotWidgets[key] = GraphCreator(self, key, value)

            plotLayout.addWidget(self.plotWidgets[key],#dockWidget,
                                 self.layout[key]['loc'][0],
                                 self.layout[key]['loc'][1],
                                 self.layout[key]['loc'][2],
                                 self.layout[key]['loc'][3])


        plotWidget = QWidget()
        plotWidget.setLayout(plotLayout)


        ### Set the progress bar
        self.progressBar = QProgressBar(self)
        self.progressBar.setValue(0)

        self.progressBar.setMaximum(data_pack.get("n_iterations", 1_000_000))
        self.progressBar.setFormat("{}/{}".format(0,data_pack.get("n_iterations", 1_000_000)))

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.addPermanentWidget(self.progressBar, stretch=1)

        #verticalLayout.addWidget(self.progressBar)
        verticalLayout.addWidget(horizontalWidget)
        verticalLayout.addWidget(plotWidget)


        self.main_widget.setLayout(verticalLayout)

        try:
            self._stop()
        except:
            pass

        try:
            self._start()
        except:
            pass

    def _redockAll(self):
        self.main_widget.setParent(None)
        self._createLayout(self.data)
        self._start()

    def updateProgress(self, v):
        self.progressBar.setValue(v)

    def _start(self):
        self.timer.start(400)
        self.startButton.setEnabled(False)
        self.stopButton.setEnabled(True)

    def _stop(self):
        self.timer.stop()
        self.startButton.setEnabled(True)
        self.stopButton.setEnabled(False)

    def _stopData(self):
        self.startButton.setEnabled(False)
        self.stopButton.setEnabled(False)
        self.stopDataButton.setEnabled(False)

    def _save(self):
        # Start a new thread for the save operation
        save_thread = Thread(target=self.send_save_command)
        save_thread.start()

    def _load(self):
        pass

    def send_save_command(self):
        # Create a new context and socket for this thread
        thread_context = zmq.Context()
        thread_socket = thread_context.socket(zmq.REQ)
        thread_socket.connect(f"tcp://localhost:{CONTROL_PORT}")

        # Send save command to the measurement without waiting for a response
        thread_socket.send_string("SAVE")
        try:
            thread_socket.recv_string(flags=zmq.NOBLOCK)
        except zmq.Again:
            pass
        finally:
            thread_socket.close()
            thread_context.term()




    def updatePlots(self):
        events = dict(self.poller.poll(100))  # Poll sockets with a 100-ms timeout
        if self.zmq_socket in events:
            try:
                data = self.zmq_socket.recv_pyobj(flags=zmq.NOBLOCK)
                self.data = data
            except zmq.Again as e:
                return None  # No data received

        else:
            return None

        if self.layout == None:
            try:
                self.layout = data["layout"]
            except:
                return None

            self._createLayout(data)

        elif self.layout != data["layout"]:
            self.main_widget.setParent(None)
            self.layout = data["layout"]
            self._createLayout(data)



        self.progressBar.setValue(data.get("iter", 0)+1)
        self.progressBar.setFormat("{}/{}".format(data.get("iter", 0),
                                                  data.get("n_iterations", 1_000_000)))

        metaData = data.get('metadata', None)

        if metaData is not None:
            for attribute, value in metaData.items():
                self.lineEdits[attribute].setText(value)

        for key, value in self.layout.items():
            self.plotWidgets[key].updateData(data["data"].get(key,{}))


def main():
    zmq_context = zmq.Context()
    zmq_socket = zmq_context.socket(zmq.SUB)
    zmq_socket.setsockopt(zmq.RCVHWM, 1)  # Set high-water mark to 1

    zmq_socket.connect(f"tcp://localhost:{DATA_PORT}")
    zmq_socket.setsockopt_string(zmq.SUBSCRIBE, '')  # Subscribe to all topics


    app = QApplication(sys.argv)

    main_window = MainWindow(zmq_socket)
    main_window.show()
    main_window.timer.start(400)

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
