from PyQt6.QtCore import (
    QObject,
    pyqtSignal,
    QTimer,
    QThread,
)
from input_output import DataPacket
from pathlib import Path
from input_output import save_data_to_hdf5, DEFAULT_DIR
import time
import os
from typing import Dict

class CoreBackend(QObject):
    layoutReady = pyqtSignal()
    dataReady = pyqtSignal()
    configChanged = pyqtSignal()

    def __init__(self):
        super().__init__()

        self.layout = set([])
        self.data_packets : Dict[str, DataPacket] = {}

        self._check_source_folder = True

        self.timer = QTimer()
        self.timer.timeout.connect(self.updateData)

        self._timeout = 1000  # Default timeout in milliseconds

        self._sourceFolder = DEFAULT_DIR

        self.add_from_source_folder()

    def _addSource(self, file):
        if file in self.data_packets:
            return
        data_packet = DataPacket(source=file)
        self.data_packets[str(file)] = data_packet

    def _removeSource(self, file):
        if file in self.data_packets:
            self.data_packets.pop(str(file))

    def _get_source_files(self, folder):
        return [Path(folder) / str(f) for f in os.listdir(folder) if f.endswith(".h5") or f.endswith(".hdf5")]

    def add_from_source_folder(self):
        folder_files = self._get_source_files(self.sourceFolder)
        for file in folder_files:
            self._addSource(file)

    def updateData(self):
        for packet in self.data_packets.values():
            packet.update()
        
        if self.check_source_folder:
            folder_files = self._get_source_files(DEFAULT_DIR)
            for file in folder_files:
                if file not in self.data_packets:
                    self._addSource(file)   

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

    def start(self):
        self.timer.start(self.updateData)

    @property
    def timeout(self):
        return self._timeout

    @timeout.setter
    def timeout(self, value):
        self._timeout = value
        self.configChanged.emit()

    @property
    def check_source_folder(self):
        return self._check_source_folder

    @check_source_folder.setter
    def check_source_folder(self, value):
        self._check_source_folder = value

        if self._check_source_folder:
            self.add_from_source_folder()

    @property
    def sourceFolder(self):
        return self._sourceFolder

    @sourceFolder.setter
    def sourceFolder(self, folder):
        self._sourceFolder = folder

    @property
    def config(self) -> Dict[str, tuple[str, type]]:
        return {
            "Refresh interval": ("timeout", int),
            "Check source folder": ("check_source_folder", bool),
            "Source folder": ("sourceFolder", str)
        }

    def set_config(self, values):
        conf = self.config
        for key, value in values.items():
            if key in conf:
                attr, attr_type = conf[key]
                setattr(self, attr, attr_type(value))