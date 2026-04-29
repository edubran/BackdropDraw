"""
Backdrop Draw for Nuke
============================
Press the shortcut key to activate, draw a rubber-band area with the mouse,
then type a label and pick a color to create a backdrop node.

Author : Eduardo Brandao — eduardo@bosonpost.com.br
Version: 2.0

INSTALLATION
------------
1. Copy this file to your .nuke directory
   (~/.nuke/ on Linux/Mac  or  %USERPROFILE%\\.nuke\\ on Windows)

2. In your menu.py add:
       import backdrop_draw
       backdrop_draw.register()

3. Restart Nuke.

USAGE
-----
1. Press the shortcut key (default v) — cursor becomes a crosshair.
2. Click and drag to draw the area.
3. Release the mouse — the label/color dialog appears near your cursor.
4. Type a custom name OR select a preset from the dropdown.
5. Choose a color, click OK.
6. Press Escape to cancel at any time.

SETTINGS
--------
Edit the SETTINGS dict below to customise behaviour.
"""

import nuke
from PySide2 import QtWidgets, QtCore, QtGui
from PySide2.QtCore import Qt


# ─────────────────────────────────────────────────────────────────────────────
#  SETTINGS
# ─────────────────────────────────────────────────────────────────────────────
SETTINGS = {
    "shortcut"      : "v",
    "default_label" : "",
    "font_size"     : 42,
    "padding"       : 40,
    "presets"       : [
        "Additive_Key", "Bloom", "Camera_Projection", "Camera_Setup",
        "CG", "CG:Ambient", "CG:Diffuse", "CG:Reflection", "CG:Refraction",
        "CG:Shadow", "CG:Specular", "Cleanup", "Controllers",
        "Color_Correction", "Despill", "Edge_Fixes", "Elements", "FX",
        "Key", "Matte", "Lens_Flare", "Light_Setup", "Light_Wrap", "Output",
        "Previous_Versions", "References", "Relight", "Resources",
        "Rig_Removal", "Roto", "Set_Extension", "Stereo_Fixes", "Temp",
        "Test", "Transformations",
    ],
    "preset_colors" : [
        ("Dark Gray", "#2a2a2a"),
        ("Blue",      "#1a3a5c"),
        ("Green",     "#1a4a2a"),
        ("Red",       "#4a1a1a"),
        ("Purple",    "#3a1a4a"),
        ("Orange",    "#4a3010"),
        ("Yellow",    "#4a4a10"),
        ("Cyan",      "#104a4a"),
    ],
}
# ─────────────────────────────────────────────────────────────────────────────


def _hex_to_nuke_color(hex_color):
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return int("%02x%02x%02xff" % (r, g, b), 16)


def _next_z_order():
    existing = [
        n["z_order"].value()
        for n in nuke.allNodes("BackdropNode")
        if not n["z_order"].isAnimated()
    ]
    return int(min(existing) - 1) if existing else -1


def _get_node_graph_widget():
    """Finds the DAG widget by its objectName prefix 'DAG.'"""
    for top in QtWidgets.QApplication.topLevelWidgets():
        for child in top.findChildren(QtWidgets.QWidget):
            if type(child).__name__ != "QGLWidget":
                continue
            parent = child.parent()
            if parent is None or type(parent).__name__ != "QWidget":
                continue
            if parent.objectName().startswith("DAG."):
                return child
    return None


def _capture_dag_state(ng_widget):
    """Captures DAG position, zoom and center before the overlay opens."""
    try:
        zoom   = nuke.zoom()
        cx, cy = nuke.center()
    except Exception:
        zoom   = 1.0
        cx, cy = 0.0, 0.0

    global_tl = ng_widget.mapToGlobal(ng_widget.rect().topLeft())
    return {
        "zoom"     : zoom,
        "center_x" : cx,
        "center_y" : cy,
        "widget_w" : ng_widget.width(),
        "widget_h" : ng_widget.height(),
        "global_x" : global_tl.x(),
        "global_y" : global_tl.y(),
    }


def _global_rect_to_canvas(dag_state, global_rect):
    """Converts a screen-space QRect to Nuke canvas coordinates."""
    tl_lx = global_rect.left()   - dag_state["global_x"]
    tl_ly = global_rect.top()    - dag_state["global_y"]
    br_lx = global_rect.right()  - dag_state["global_x"]
    br_ly = global_rect.bottom() - dag_state["global_y"]

    zoom = dag_state["zoom"]
    cx   = dag_state["center_x"]
    cy   = dag_state["center_y"]
    hw   = dag_state["widget_w"] / 2.0
    hh   = dag_state["widget_h"] / 2.0

    return (
        cx + (tl_lx - hw) / zoom,
        cy + (tl_ly - hh) / zoom,
        cx + (br_lx - hw) / zoom,
        cy + (br_ly - hh) / zoom,
    )


# ── Label / Color dialog ──────────────────────────────────────────────────────

class BackdropDialog(QtWidgets.QDialog):

    # Margin to keep the dialog inside the screen
    _SCREEN_MARGIN = 16

    def __init__(self, cursor_pos, parent=None):
        super(BackdropDialog, self).__init__(parent)
        self.setWindowTitle("Create Backdrop")
        self.setMinimumWidth(380)
        self.setWindowFlags(Qt.Dialog | Qt.WindowStaysOnTopHint)
        self._color      = SETTINGS["preset_colors"][0][1]
        self._cursor_pos = cursor_pos
        self._build_ui()

    def _build_ui(self):
        root = QtWidgets.QVBoxLayout(self)
        root.setSpacing(10)
        root.setContentsMargins(14, 14, 14, 14)

        # ── Label field (focused on open) ─────────────────────────────────────
        root.addWidget(QtWidgets.QLabel("<b>Backdrop Label</b>"))
        self.name_edit = QtWidgets.QLineEdit(SETTINGS["default_label"])
        self.name_edit.setPlaceholderText("Type a custom name…")
        root.addWidget(self.name_edit)

        # ── Preset dropdown ───────────────────────────────────────────────────
        root.addWidget(QtWidgets.QLabel("<b>Presets</b>"))
        self.preset_combo = QtWidgets.QComboBox()
        self.preset_combo.addItem("— select preset —", userData=None)
        for p in SETTINGS["presets"]:
            self.preset_combo.addItem(p, userData=p)
        self.preset_combo.currentIndexChanged.connect(self._on_preset_changed)
        root.addWidget(self.preset_combo)

        # ── Color palette ─────────────────────────────────────────────────────
        root.addWidget(QtWidgets.QLabel("<b>Color</b>"))
        grid_widget = QtWidgets.QWidget()
        grid = QtWidgets.QGridLayout(grid_widget)
        grid.setSpacing(5)
        grid.setContentsMargins(0, 0, 0, 0)

        self._swatch_buttons = []
        COLS = 4
        for i, (name, hex_col) in enumerate(SETTINGS["preset_colors"]):
            btn = QtWidgets.QPushButton(name)
            btn.setFixedHeight(28)
            btn.setStyleSheet(self._swatch_style(hex_col, selected=False))
            btn.clicked.connect(self._make_preset_handler(hex_col))
            grid.addWidget(btn, i // COLS, i % COLS)
            self._swatch_buttons.append((btn, hex_col))
        root.addWidget(grid_widget)

        # ── Custom color ──────────────────────────────────────────────────────
        row = QtWidgets.QHBoxLayout()
        pick_btn = QtWidgets.QPushButton("Custom color...")
        pick_btn.clicked.connect(self._pick_custom)
        row.addWidget(pick_btn)
        self._preview = QtWidgets.QFrame()
        self._preview.setFixedSize(38, 26)
        self._preview.setFrameShape(QtWidgets.QFrame.StyledPanel)
        row.addWidget(self._preview)
        row.addStretch()
        root.addLayout(row)

        # ── OK / Cancel ───────────────────────────────────────────────────────
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        self._apply_color(self._color)

    # ── Preset dropdown handler ───────────────────────────────────────────────

    def _on_preset_changed(self, index):
        value = self.preset_combo.itemData(index)
        if value is not None:
            self.name_edit.setText(value)
            # Reset combo to placeholder so it can be reused
            # (keep text so user can still edit it)

    # ── Color helpers ─────────────────────────────────────────────────────────

    @staticmethod
    def _swatch_style(hex_col, selected):
        border = "2px solid white" if selected else "2px solid #555"
        return "background-color: {c}; border: {b}; border-radius: 3px; color: transparent;".format(
            c=hex_col, b=border
        )

    def _make_preset_handler(self, hex_col):
        def handler():
            self._apply_color(hex_col)
        return handler

    def _apply_color(self, hex_col):
        self._color = hex_col
        self._preview.setStyleSheet("background-color: %s;" % hex_col)
        for btn, col in self._swatch_buttons:
            btn.setStyleSheet(self._swatch_style(col, selected=(col == hex_col)))

    def _pick_custom(self):
        chosen = QtWidgets.QColorDialog.getColor(
            QtGui.QColor(self._color), self, "Choose Color",
            QtWidgets.QColorDialog.DontUseNativeDialog,
        )
        if chosen.isValid():
            for btn, col in self._swatch_buttons:
                btn.setStyleSheet(self._swatch_style(col, selected=False))
            self._apply_color(chosen.name())

    def get_values(self):
        return self.name_edit.text(), self._color

    # ── Position near cursor, stay inside screen ──────────────────────────────

    def showEvent(self, event):
        super(BackdropDialog, self).showEvent(event)
        self._position_near_cursor()
        # Auto-focus the label field so the user can type immediately
        self.name_edit.setFocus(Qt.OtherFocusReason)
        self.name_edit.selectAll()

    def _position_near_cursor(self):
        """Positions the dialog so its bottom-right corner is near the cursor."""
        screen = QtWidgets.QApplication.screenAt(self._cursor_pos)
        if screen is None:
            screen = QtWidgets.QApplication.primaryScreen()
        screen_rect = screen.availableGeometry()

        self.adjustSize()
        w = self.width()
        h = self.height()
        m = self._SCREEN_MARGIN

        # Bottom-right corner of dialog sits at cursor position
        x = self._cursor_pos.x() - w - 16
        y = self._cursor_pos.y() - h - 16

        # Clamp to screen bounds
        x = max(screen_rect.left() + m, min(x, screen_rect.right()  - w - m))
        y = max(screen_rect.top()  + m, min(y, screen_rect.bottom() - h - m))

        self.move(x, y)


# ── Floating rubber-band overlay ──────────────────────────────────────────────

class DrawOverlay(QtWidgets.QWidget):

    area_selected = QtCore.Signal(QtCore.QRect, QtCore.QPoint)  # rect + cursor pos
    cancelled     = QtCore.Signal()

    def __init__(self):
        super(DrawOverlay, self).__init__(
            None,
            Qt.Window
            | Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool,
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setAutoFillBackground(False)
        self.setMouseTracking(True)

        self._origin = None
        self._rubber = QtWidgets.QRubberBand(QtWidgets.QRubberBand.Rectangle, self)

        screen = QtWidgets.QApplication.primaryScreen().geometry()
        self.setGeometry(screen)

        self.show()
        self.raise_()
        self.activateWindow()
        self.setFocus(Qt.OtherFocusReason)
        self.grabMouse(Qt.CrossCursor)
        self.grabKeyboard()

    def paintEvent(self, _event):
        pass

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._origin = event.pos()
            self._rubber.setGeometry(QtCore.QRect(self._origin, QtCore.QSize()))
            self._rubber.show()

    def mouseMoveEvent(self, event):
        if self._origin is not None:
            self._rubber.setGeometry(
                QtCore.QRect(self._origin, event.pos()).normalized()
            )

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._origin is not None:
            local_rect  = QtCore.QRect(self._origin, event.pos()).normalized()
            global_tl   = self.mapToGlobal(local_rect.topLeft())
            global_br   = self.mapToGlobal(local_rect.bottomRight())
            global_rect = QtCore.QRect(global_tl, global_br)
            # Capture global cursor position for dialog placement
            cursor_pos  = self.mapToGlobal(event.pos())
            self._close_overlay()
            if local_rect.width() > 5 and local_rect.height() > 5:
                self.area_selected.emit(global_rect, cursor_pos)
            else:
                self.cancelled.emit()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self._close_overlay()
            self.cancelled.emit()

    def _close_overlay(self):
        self.releaseMouse()
        self.releaseKeyboard()
        self._rubber.hide()
        self.hide()
        self.close()


# ── Backdrop creation ─────────────────────────────────────────────────────────

def _make_backdrop(dag_state, global_rect, cursor_pos):
    dlg = BackdropDialog(cursor_pos, QtWidgets.QApplication.activeWindow())
    if dlg.exec_() != QtWidgets.QDialog.Accepted:
        return

    label, hex_color = dlg.get_values()
    tl_x, tl_y, br_x, br_y = _global_rect_to_canvas(dag_state, global_rect)

    pad     = SETTINGS["padding"]
    z_order = _next_z_order()

    bd = nuke.nodes.BackdropNode(
        xpos           = int(tl_x - pad),
        ypos           = int(tl_y - pad),
        bdwidth        = int((br_x - tl_x) + pad * 2),
        bdheight       = int((br_y - tl_y) + pad * 2),
        tile_color     = _hex_to_nuke_color(hex_color),
        note_font_size = SETTINGS["font_size"],
        z_order        = z_order,
        label          = label,
    )
    bd["z_order"].setValue(z_order)


# ── Entry point ───────────────────────────────────────────────────────────────

_overlay = None

def start_backdrop_draw():
    global _overlay
    if _overlay is not None:
        return

    ng = _get_node_graph_widget()
    if ng is None:
        nuke.message("Could not find the Node Graph (DAG) panel.\nMake sure the Node Graph is visible in your current layout.")
        return

    dag_state = _capture_dag_state(ng)
    overlay   = DrawOverlay()
    _overlay  = overlay

    def on_selected(rect, cursor_pos):
        global _overlay
        _overlay = None
        QtCore.QTimer.singleShot(50, lambda: _make_backdrop(dag_state, rect, cursor_pos))

    def on_cancelled():
        global _overlay
        _overlay = None

    overlay.area_selected.connect(on_selected)
    overlay.cancelled.connect(on_cancelled)


# ── Registration ──────────────────────────────────────────────────────────────

def register():
    sc = SETTINGS["shortcut"]
    #nuke.menu("Nuke").addCommand("Custom/Backdrop Draw", start_backdrop_draw, sc)
    nuke.menu("Nodes").addCommand("Custom/Backdrop Draw", start_backdrop_draw, sc)
    print("[Backdrop Draw] Registered — shortcut: %s" % sc)


if __name__ == "__main__":
    register()
