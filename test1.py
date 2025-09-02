import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore

app = pg.mkQApp("Hover x,y,(z) demo")

# --- Window and plot ---
win = pg.GraphicsLayoutWidget()
plot = win.addPlot()
vb = plot.vb

# --- Dummy image (H x W) ---
H, W = 200, 300
img = (np.linspace(0, 1, W)[None, :] * np.linspace(0, 1, H)[:, None])
img += 0.1 * np.random.randn(H, W)   # add a bit of noise
img_item = pg.ImageItem(img)
plot.addItem(img_item)

# --- Dummy curve on top (shares the same ViewBox) ---
x = np.linspace(0, W-1, 500)
y = 50*np.sin(x/20) + H/2
plot.plot(x, y, pen=pg.mkPen(width=2))

# Show full image extents
plot.setRange(xRange=(0, W), yRange=(0, H))
plot.setLimits(xMin=-10, xMax=W+10, yMin=-10, yMax=H+10)

# --- Hover box (text with background) ---
hover = pg.TextItem("", anchor=(0, 1))  # bottom-left anchor
hover.setZValue(1_000)                  # stay on top
plot.addItem(hover)

def format_hover_html(x, y, z=None):
    text = f"x={x:.2f}, y={y:.2f}"
    if z is not None:
        if isinstance(z, tuple):
            text += ", z=(" + ", ".join(f"{v:.3g}" for v in z) + ")"
        else:
            text += f", z={z:.3g}"
    # Small HTML box; works nicely with TextItem.setHtml
    return (
        f"<span style='background-color: rgba(0,0,0,0.75);"
        f"color: #fff; padding: 2px 4px; border: 1px solid #ddd;"
        f"font-size: 11px;'>"
        f"{text}</span>"
    )

def sample_image_z(image_item: pg.ImageItem, view_pt):
    """Return pixel value at view coordinates if inside the image; else None."""
    arr = getattr(image_item, "image", None)
    if arr is None:
        return None
    # Map view (data) coords -> image-item local coords (pixel indices)
    item_pt = vb.mapFromViewToItem(image_item, view_pt)
    ix = int(np.floor(item_pt.x()))
    iy = int(np.floor(item_pt.y()))
    if arr.ndim == 2:
        if 0 <= iy < arr.shape[0] and 0 <= ix < arr.shape[1]:
            return float(arr[iy, ix])
    elif arr.ndim == 3:  # e.g. HxWxC
        if 0 <= iy < arr.shape[0] and 0 <= ix < arr.shape[1]:
            return tuple(float(v) for v in arr[iy, ix])
    return None

def on_mouse_moved(evt):
    pos = evt[0]  # SignalProxy packs args
    if not plot.sceneBoundingRect().contains(pos):
        hover.setVisible(False)
        return

    hover.setVisible(True)
    vpos = vb.mapSceneToView(pos)
    x, y = vpos.x(), vpos.y()
    z = sample_image_z(img_item, vpos)

    hover.setHtml(format_hover_html(x, y, z))

    # Place hover box near the cursor (a small offset)
    offset = QtCore.QPointF(10, -10)
    hover.setPos(vpos + offset)

# Throttle updates for performance
proxy = pg.SignalProxy(win.scene().sigMouseMoved, rateLimit=120, slot=on_mouse_moved)

win.show()
app.exec()
