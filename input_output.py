import h5py
import numpy as np
import os

from pathlib import Path
from filelock import FileLock

DEFAULT_DIR = Path.home() / 'plot_data'

from zmq import (
    Context, Poller,
    SUB, PUB,
    RCVHWM, SNDHWM,
    SUBSCRIBE, POLLIN, NOBLOCK,
    Again,
    EADDRINUSE,
    ZMQError
)

import threading

def save_data_to_hdf5(file_path, data):
    """
    Save data to an HDF5 file in a recursive manner.

    Parameters:
        file_path (str): Path to the HDF5 file.
        data (dict): Data to save, where keys are dataset names and values are numpy arrays.
    """
    def _save_recursive(group, data):
        for key, value in data.items():
            if key == 'metadata':
                # Save metadata as attributes of the group
                for meta_key, meta_value in value.items():
                    group.attrs[meta_key] = meta_value

            elif isinstance(value, dict):
                subgroup = group.create_group(key)
                _save_recursive(subgroup, value)

            elif isinstance(value, str):
                group.create_dataset(key, data=np.string_(value))

            else:
                group.create_dataset(key, data=value)

    if not os.path.exists(os.path.dirname(file_path)):
        os.makedirs(os.path.dirname(file_path))
    with h5py.File(file_path, 'w') as f:
        _save_recursive(f, data)



def load_data_from_hdf5(file_path):
    """
    Load data from an HDF5 file in a recursive manner.

    Parameters:
        file_path (str): Path to the HDF5 file.

    Returns:
        dict: Loaded data, where keys are dataset names and values are numpy arrays.
    """
    def _load_recursive(group):
        data = {}
        for key in group.keys():
            item = group[key]
            if isinstance(item, h5py.Group):
                data[str(key)] = _load_recursive(item)

            elif isinstance(item[()], bytes):
                data[str(key)] = str(item[()].decode('utf-8'))

            else:
                data[str(key)] = item[()]
        if group.attrs:
            data['metadata'] = {}
            for attr in group.attrs:
                data['metadata'][attr] = group.attrs[attr]
        return data

    with h5py.File(file_path, 'r') as f:
        return _load_recursive(f)


class DataPacket:
    '''
    A class to handle data loading and saving operations.
    Supports only HDF5 format for now.
    '''

    def __init__(self, data = None, source = None):
        if source and not data:
            self.load_data(source)
            self.source = Path(source)
            self._lock = FileLock(self.source / ".lock")

        elif data:
            self.data = data
            self.source = source if source else Path(DEFAULT_DIR / str(id(self.data)))
            self._lock = FileLock(self.source / ".lock")

        else:
            self.data = data
            self.source = source

    def setData(self, data):
        self.data = data
        if self.source:
            self.save_data()
        else:
            self.source = Path(id(self.data))

    def update(self):
        if self.source:
            self.data = self._load_data_from_hdf5(self.source)

    def load_data(self, source, format = "hdf5"):
        if format == "hdf5":
            self.data = self._load_data_from_hdf5(source)
            self.source = source
        else:
            raise ValueError(f"Unsupported format: {format}")

    def save_data(self, format = "hdf5"):
        if format == "hdf5":
            self._save_data_to_hdf5(self.source, self.data)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def __getitem__(self, key):
        if not self.data:
            raise Warning("No data loaded")
        return self.data.get(key)
    
    @property
    def graphs(self):
        if not self.data:
            raise Warning("No data loaded")
        return tuple(self.data.keys())

    @classmethod
    def _load_data_from_hdf5(cls, file_path, _layer = 0, _name = None):
        """
        Load data from an HDF5 file in a recursive manner.

        Parameters:
            file_path (str): Path to the HDF5 file.

        Returns:
            dict: Loaded data, where keys are dataset names and values are numpy arrays.
        """
        if _layer == 0:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")
            with h5py.File(file_path, 'r') as f:
                _name = str(file_path)
                return cls._load_data_from_hdf5(f, _layer+1, _name = _name)

        else:
            group = file_path
            data = {}
            for key in group.keys():
                item = group[key]
                if isinstance(item, h5py.Group):
                    data[str(key)] = cls._load_data_from_hdf5(item, _layer+1, _name = _name)

                elif isinstance(item[()], bytes):
                    data[str(key)] = str(item[()].decode('utf-8'))
                else:
                    data[str(key)] = item[()]
            if group.attrs:
                data['metadata'] = {}
                for attr in group.attrs:
                    data['metadata'][attr] = group.attrs[attr]
            return data

    @classmethod
    def _save_data_to_hdf5(cls, file_path, data, _layer = 0):
        """
        Save data to an HDF5 file in a recursive manner.

        Parameters:
            file_path (str): Path to the HDF5 file.
            data (dict): Data to save, where keys are dataset names and values are numpy arrays.
        """
        if _layer == 0:
            if not os.path.exists(os.path.dirname(file_path)):
                os.makedirs(os.path.dirname(file_path))

            with h5py.File(file_path, 'w') as f:
                cls._save_data_to_hdf5(f, data)
            return

        for key, value in data.items():
            if key == 'metadata':
                # Save metadata as attributes of the group
                for meta_key, meta_value in value.items():
                    file_path.attrs[meta_key] = meta_value

            elif isinstance(value, dict):
                subgroup = file_path.create_group(key)
                cls._save_data_to_hdf5(subgroup, value)

            elif isinstance(value, str):
                file_path.create_dataset(key, data=np.bytes_(value, 'utf-8'))

            else:
                file_path.create_dataset(key, data=value)