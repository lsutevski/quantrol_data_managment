![image](logo.png)
# Live Plotting Demo

This repository contains a real-time plotting application using PyQtGraph and JupyterLab. The application visualizes live data streams and includes customizable graph layouts.

## Features

- Real-time plotting using PyQtGraph.
- Modular and extensible plotting framework.
- JupyterLab support for interactive use.
- Pre-defined graph types: Line plots, scatter plots, heatmaps, and more.

## Requirements

The project uses `conda` for environment management. All required dependencies are listed in the `environment.yml` file.

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/live-plotting-demo.git
cd live-plotting-demo
```

### 2. Set Up the Environment
```bash
conda env create -f environment.yml
conda activate live_plot_env
```

### 3. Testing the functionality
First, you need to start the live_plot_widget.py by:
```bash
python live_plot_widget.py
```
Then, start the JupyterLab by:
```bash
jupyter lab
```
, open the LivePlottingDEMO.ipynb notebook and enjoy.

### Remark
This is a work in progress, let me know what you think.
