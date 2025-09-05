from PyQt6.QtCore import (
    QObject,
    pyqtSignal,
    QTimer,
    QThread,
)
from input_output import DataReceiver, DataFromFile, DataPacket
from pathlib import Path
from input_output import save_data_to_hdf5, DEFAULT_DIR
import time
import os
from typing import Dict

LIVE_MODE = 'live'
FILE_MODE = 'file'

# class CoreBackend(QObject):
#     layoutReady = pyqtSignal()
#     dataReady = pyqtSignal()

#     def __init__(self, savePath: Path = None, port = 5555, rate = 1000):
#         super().__init__()

#         self.mode = LIVE_MODE

#         self.layout = None
#         self.plotWidget = None

#         self.dataReceiver = None

#         self.timer = QTimer()
#         self.timer.timeout.connect(self.getData)

#         self.data = None

#         self.thread = QThread()

#         if savePath is None:
#             self.savePath = DEFAULT_DIR
#         else:
#             self.savePath = savePath

#         self.experimentName = None
#         self.timeStamp = None

#         self.port = port
#         self.rate = rate

#     def getData(self):
#         self.data = self.dataReceiver.check_data()
#         if self.data is not None:
#             layout = self.data.get('layout', {})
#             if layout is not None and self.compareLayout(layout):
#                 self.layout = layout
#                 self.layoutReady.emit()

#             self.dataReady.emit()
#             self._saveData()

#     def compareLayout(self, layout):
#         """
#         Compares the current layout with a new layout.
#         :param layout: The new layout to compare against the current one.
#         :return: True if the layouts are different, False otherwise.
#         """
#         if self.layout is None:
#             return True
#         return self.layout != layout

#     def setDataReceiver(self,
#                         mode,
#                         source = None):
#         """
#         Sets the data receiver for the backend.
#         :param dataReceiver: The class that handles data reception. Can be
#                              either DataReceiver or DataFromFile.
#         :param source: The source from which the data receiver will
#                        receive data. Either a port number for live data
#                        or a file path for file-based data.
#         """
#         if mode == LIVE_MODE:
#             self.mode = LIVE_MODE
#             if source is None:
#                 source = self.port
#             else:
#                 self._setParams(port=source)
#             self.dataReceiver = DataReceiver(source)
#             self.timer.start(self.rate)

#         elif mode == FILE_MODE:
#             self.timer.stop()
#             self.mode = FILE_MODE
#             self.dataReceiver = DataFromFile(source)
#             self.layout = None
#             self.getData()

#         elif mode is None:
#             self.timer.stop()
#             self.dataReceiver = None

#         else:
#             raise ValueError("Invalid mode. Use 'live' or 'file'.")

#         self.timeStamp = time.strftime("%d_%m_%Y_%H_%M_%S")


#     def _saveData(self, expeirmentName="UnknownExperiment"):
#         """
#         Saves the current data to a file.
#         """
#         path = self.savePath / f"{self.experimentName}" / f"{self.timeStamp}.hdf5"
#         save_data_to_hdf5(path, self.data)

#     def _setParams(self, port = None, rate = None):
#         """
#         Sets the parameters for the backend.
#         :param port: The port to use for the data receiver.
#         :param rate: The refresh rate for the data receiver.
#         """
#         if port is not None:
#             self.port = port
#         if rate is not None:
#             self.rate = rate

class CoreBackend(QObject):
    layoutReady = pyqtSignal()
    dataReady = pyqtSignal()

    def __init__(self):
        super().__init__()

        self.layout = set([])
        self.data_packets : Dict[str, DataPacket] = {}

        self._default_folder = True

        self.timer = QTimer()
        self.timer.timeout.connect(self.updateData)

        self.timeout = 1000  # Default timeout in milliseconds

    def grabData(self, *files):
        if self._default_folder:
            folder_files = [f for f in os.listdir(DEFAULT_DIR) if f.endswith(".h5") or f.endswith(".hdf5")]

            for file in folder_files:
                data_packet = DataPacket(source=file)
                self.data_packets[file] = data_packet

        for file in files:
            data_packet = DataPacket(source=file)
            self.data_packets[file] = data_packet

    def updateData(self):
        for packet in self.data_packets.values():
            packet.update()
        self.dataReady.emit()

    def extractLayout(self):
        '''
        Later on add some smart way to save layout and then based on that position the graphs.
        '''
        layout = set([])
        for packet in self.data_packets.keys():
            graphs = packet.data.get('graphs', [])
            layout.update(graphs)
        if self.layout != layout:
            self.layout = layout
            self.layoutReady.emit()

    def startDataAcquisition(self):
        self.timer.start(self.timeout)

