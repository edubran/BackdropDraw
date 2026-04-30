"""
Backdrop Draw for Nuke
======================
Press the shortcut key to activate, draw a rubber-band area with the mouse,
then choose a label and color to create a backdrop node.

Author : Eduardo Brandao — eduardo@bosonpost.com.br
Version: 3.1

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
1. Press the shortcut key (default: v) inside the Node Graph.
2. Click and drag to draw the backdrop area.
3. Release the mouse — the dialog appears near your cursor.
4. Click a preset button OR type a custom label.
5. Pick a color swatch, use Random, or open the custom picker.
6. Adjust font size and text alignment if needed.
7. Press Enter or click OK to create. Escape cancels.

SETTINGS
--------
Open Nuke menu > Custom > Backdrop Draw Settings.
Settings are saved per-user in ~/.nuke/backdrop_draw_settings.json
"""

import os
import json
import random
import nuke
from PySide2 import QtWidgets, QtCore, QtGui
from PySide2.QtCore import Qt


# ─────────────────────────────────────────────────────────────────────────────
#  DEFAULT SETTINGS
# ─────────────────────────────────────────────────────────────────────────────
_DEFAULTS = {
    "shortcut"       : "v",
    "font_size"      : 42,
    "padding"        : 40,
    "preset_columns" : 3,
    "text_alignment" : "center",
    "presets"        : [
        "Additive_Key", "Bloom", "Camera_Projection", "Camera_Setup",
        "CG", "CG:Ambient", "CG:Diffuse", "CG:Reflection", "CG:Refraction",
        "CG:Shadow", "CG:Specular", "Cleanup", "Controllers",
        "Color_Correction", "Despill", "Edge_Fixes", "Elements", "FX",
        "Key", "Matte", "Lens_Flare", "Light_Setup", "Light_Wrap", "Output",
        "Previous_Versions", "References", "Relight", "Resources",
        "Rig_Removal", "Roto", "Set_Extension", "Stereo_Fixes", "Temp",
        "Test", "Transformations",
    ],
    "colors": [
        {"name": "Dark Gray", "hex": "#2a2a2a"},
        {"name": "Blue",      "hex": "#1a3a5c"},
        {"name": "Green",     "hex": "#1a4a2a"},
        {"name": "Red",       "hex": "#4a1a1a"},
        {"name": "Purple",    "hex": "#3a1a4a"},
        {"name": "Orange",    "hex": "#4a3010"},
        {"name": "Yellow",    "hex": "#4a4a10"},
        {"name": "Cyan",      "hex": "#104a4a"},
    ],
}

_SETTINGS_PATH = os.path.join(
    os.path.expanduser("~"), ".nuke", "backdrop_draw_settings.json"
)

def _load_settings():
    s = dict(_DEFAULTS)
    if os.path.isfile(_SETTINGS_PATH):
        try:
            with open(_SETTINGS_PATH, "r") as f:
                user = json.load(f)
            s.update(user)
        except Exception as e:
            print("[Backdrop Draw] Could not load settings: %s" % e)
    return s

def _save_settings(s):
    try:
        with open(_SETTINGS_PATH, "w") as f:
            json.dump(s, f, indent=2)
    except Exception as e:
        print("[Backdrop Draw] Could not save settings: %s" % e)

CFG = _load_settings()


# ─────────────────────────────────────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _hex_to_nuke_color(hex_color):
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return int("%02x%02x%02xff" % (r, g, b), 16)

def _random_dark_color():
    r = random.randint(15, 75)
    g = random.randint(15, 75)
    b = random.randint(15, 75)
    return "#%02x%02x%02x" % (r, g, b)

def _next_z_order():
    existing = [
        n["z_order"].value()
        for n in nuke.allNodes("BackdropNode")
        if not n["z_order"].isAnimated()
    ]
    return int(min(existing) - 1) if existing else -1

def _alignment_prefix(alignment):
    return {"left": "<left>", "center": "<center>", "right": "<right>"}.get(alignment, "<center>")


# ─────────────────────────────────────────────────────────────────────────────
#  NODE GRAPH HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _get_node_graph_widget():
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

def _capture_dag_state(ng):
    try:
        zoom   = nuke.zoom()
        cx, cy = nuke.center()
    except Exception:
        zoom   = 1.0
        cx, cy = 0.0, 0.0
    tl = ng.mapToGlobal(ng.rect().topLeft())
    return {
        "zoom": zoom, "center_x": cx, "center_y": cy,
        "widget_w": ng.width(), "widget_h": ng.height(),
        "global_x": tl.x(), "global_y": tl.y(),
    }

def _global_rect_to_canvas(ds, rect):
    tl_lx = rect.left()   - ds["global_x"]
    tl_ly = rect.top()    - ds["global_y"]
    br_lx = rect.right()  - ds["global_x"]
    br_ly = rect.bottom() - ds["global_y"]
    zoom  = ds["zoom"]
    cx, cy = ds["center_x"], ds["center_y"]
    hw, hh = ds["widget_w"] / 2.0, ds["widget_h"] / 2.0
    return (
        cx + (tl_lx - hw) / zoom, cy + (tl_ly - hh) / zoom,
        cx + (br_lx - hw) / zoom, cy + (br_ly - hh) / zoom,
    )


# ─────────────────────────────────────────────────────────────────────────────
#  SETTINGS DIALOG
# ─────────────────────────────────────────────────────────────────────────────

class SettingsDialog(QtWidgets.QDialog):
    """
    Full settings panel.
    Preset editor: interactive list with Add / Rename / Remove / reorder buttons.
    Color editor: list with Add / Remove and inline hex editing.
    """

    def __init__(self, parent=None):
        super(SettingsDialog, self).__init__(parent)
        self.setWindowTitle("Backdrop Draw — Settings")
        self.setMinimumWidth(520)
        self.setMinimumHeight(620)
        self.setWindowFlags(Qt.Dialog | Qt.WindowStaysOnTopHint)
        self._build_ui()

    def _build_ui(self):
        root = QtWidgets.QVBoxLayout(self)
        root.setSpacing(10)
        root.setContentsMargins(14, 14, 14, 14)

        tabs = QtWidgets.QTabWidget()
        tabs.addTab(self._build_general_tab(), "General")
        tabs.addTab(self._build_presets_tab(),  "Preset Labels")
        tabs.addTab(self._build_colors_tab(),   "Colors")
        root.addWidget(tabs)

        note = QtWidgets.QLabel(
            "<i>Shortcut changes require a Nuke restart. All other changes apply immediately.</i>"
        )
        note.setWordWrap(True)
        root.addWidget(note)

        btns = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Save | QtWidgets.QDialogButtonBox.Cancel
        )
        btns.accepted.connect(self._save)
        btns.rejected.connect(self.reject)
        root.addWidget(btns)

    # ── General tab ───────────────────────────────────────────────────────────

    def _build_general_tab(self):
        w = QtWidgets.QWidget()
        form = QtWidgets.QFormLayout(w)
        form.setSpacing(10)
        form.setContentsMargins(10, 10, 10, 10)

        self.shortcut_edit = QtWidgets.QLineEdit(CFG.get("shortcut", "v"))
        form.addRow("Shortcut key:", self.shortcut_edit)

        self.font_spin = QtWidgets.QSpinBox()
        self.font_spin.setRange(10, 200)
        self.font_spin.setValue(CFG.get("font_size", 42))
        form.addRow("Default font size:", self.font_spin)

        self.padding_spin = QtWidgets.QSpinBox()
        self.padding_spin.setRange(0, 300)
        self.padding_spin.setValue(CFG.get("padding", 40))
        form.addRow("Padding (canvas units):", self.padding_spin)

        self.cols_spin = QtWidgets.QSpinBox()
        self.cols_spin.setRange(1, 6)
        self.cols_spin.setValue(CFG.get("preset_columns", 3))
        form.addRow("Preset button columns:", self.cols_spin)

        self.align_combo = QtWidgets.QComboBox()
        for lbl, val in [("Left", "left"), ("Center", "center"), ("Right", "right")]:
            self.align_combo.addItem(lbl, val)
        idx = self.align_combo.findData(CFG.get("text_alignment", "center"))
        if idx >= 0:
            self.align_combo.setCurrentIndex(idx)
        form.addRow("Default text alignment:", self.align_combo)

        return w

    # ── Presets tab ───────────────────────────────────────────────────────────

    def _build_presets_tab(self):
        w = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(w)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        layout.addWidget(QtWidgets.QLabel(
            "Add, rename, remove or reorder preset labels.\n"
            "Double-click a label to rename it inline."
        ))

        self.presets_list = QtWidgets.QListWidget()
        self.presets_list.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        self.presets_list.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        for p in CFG.get("presets", []):
            item = QtWidgets.QListWidgetItem(p)
            item.setFlags(item.flags() | Qt.ItemIsEditable)
            self.presets_list.addItem(item)
        layout.addWidget(self.presets_list)

        # Buttons row
        btn_row = QtWidgets.QHBoxLayout()

        add_btn = QtWidgets.QPushButton("＋ Add")
        add_btn.clicked.connect(self._preset_add)
        btn_row.addWidget(add_btn)

        rename_btn = QtWidgets.QPushButton("✏ Rename")
        rename_btn.clicked.connect(self._preset_rename)
        btn_row.addWidget(rename_btn)

        remove_btn = QtWidgets.QPushButton("✕ Remove")
        remove_btn.clicked.connect(self._preset_remove)
        btn_row.addWidget(remove_btn)

        btn_row.addStretch()

        up_btn = QtWidgets.QPushButton("▲")
        up_btn.setFixedWidth(32)
        up_btn.clicked.connect(self._preset_move_up)
        btn_row.addWidget(up_btn)

        down_btn = QtWidgets.QPushButton("▼")
        down_btn.setFixedWidth(32)
        down_btn.clicked.connect(self._preset_move_down)
        btn_row.addWidget(down_btn)

        layout.addLayout(btn_row)

        # New preset input
        input_row = QtWidgets.QHBoxLayout()
        self.new_preset_edit = QtWidgets.QLineEdit()
        self.new_preset_edit.setPlaceholderText("New preset name…")
        self.new_preset_edit.returnPressed.connect(self._preset_add)
        input_row.addWidget(self.new_preset_edit)
        layout.addLayout(input_row)

        return w

    def _preset_add(self):
        name = self.new_preset_edit.text().strip()
        if not name:
            return
        item = QtWidgets.QListWidgetItem(name)
        item.setFlags(item.flags() | Qt.ItemIsEditable)
        self.presets_list.addItem(item)
        self.new_preset_edit.clear()
        self.presets_list.scrollToBottom()

    def _preset_rename(self):
        item = self.presets_list.currentItem()
        if item:
            self.presets_list.editItem(item)

    def _preset_remove(self):
        row = self.presets_list.currentRow()
        if row >= 0:
            self.presets_list.takeItem(row)

    def _preset_move_up(self):
        row = self.presets_list.currentRow()
        if row > 0:
            item = self.presets_list.takeItem(row)
            self.presets_list.insertItem(row - 1, item)
            self.presets_list.setCurrentRow(row - 1)

    def _preset_move_down(self):
        row = self.presets_list.currentRow()
        if row < self.presets_list.count() - 1:
            item = self.presets_list.takeItem(row)
            self.presets_list.insertItem(row + 1, item)
            self.presets_list.setCurrentRow(row + 1)

    # ── Colors tab ────────────────────────────────────────────────────────────

    def _build_colors_tab(self):
        w = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(w)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        layout.addWidget(QtWidgets.QLabel(
            "Add or remove color swatches.\n"
            "Click the color square to change it. Click the name to rename."
        ))

        self.colors_table = QtWidgets.QTableWidget(0, 3)
        self.colors_table.setHorizontalHeaderLabels(["Color", "Name", "Hex"])
        self.colors_table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.Fixed)
        self.colors_table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        self.colors_table.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.Fixed)
        self.colors_table.setColumnWidth(0, 40)
        self.colors_table.setColumnWidth(2, 80)
        self.colors_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.colors_table.verticalHeader().setVisible(False)

        for c in CFG.get("colors", []):
            self._add_color_row(c["name"], c["hex"])

        layout.addWidget(self.colors_table)

        btn_row = QtWidgets.QHBoxLayout()
        add_btn = QtWidgets.QPushButton("＋ Add Color")
        add_btn.clicked.connect(self._color_add)
        btn_row.addWidget(add_btn)

        remove_btn = QtWidgets.QPushButton("✕ Remove")
        remove_btn.clicked.connect(self._color_remove)
        btn_row.addWidget(remove_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        return w

    def _add_color_row(self, name, hex_col):
        row = self.colors_table.rowCount()
        self.colors_table.insertRow(row)
        self.colors_table.setRowHeight(row, 30)

        # Color swatch button
        swatch = QtWidgets.QPushButton()
        swatch.setStyleSheet("background-color: %s; border: 1px solid #666; border-radius: 3px;" % hex_col)
        swatch.setProperty("hex_col", hex_col)
        swatch.clicked.connect(lambda _, r=row: self._pick_row_color(r))
        self.colors_table.setCellWidget(row, 0, swatch)

        # Name
        name_item = QtWidgets.QTableWidgetItem(name)
        self.colors_table.setItem(row, 1, name_item)

        # Hex
        hex_item = QtWidgets.QTableWidgetItem(hex_col)
        self.colors_table.setItem(row, 2, hex_item)

    def _pick_row_color(self, row):
        swatch = self.colors_table.cellWidget(row, 0)
        current = swatch.property("hex_col") or "#2a2a2a"
        chosen = QtWidgets.QColorDialog.getColor(
            QtGui.QColor(current), self, "Choose Color",
            QtWidgets.QColorDialog.DontUseNativeDialog,
        )
        if chosen.isValid():
            hex_col = chosen.name()
            swatch.setStyleSheet(
                "background-color: %s; border: 1px solid #666; border-radius: 3px;" % hex_col
            )
            swatch.setProperty("hex_col", hex_col)
            self.colors_table.item(row, 2).setText(hex_col)

    def _color_add(self):
        self._add_color_row("New Color", "#2a2a2a")

    def _color_remove(self):
        row = self.colors_table.currentRow()
        if row >= 0:
            self.colors_table.removeRow(row)

    # ── Save ──────────────────────────────────────────────────────────────────

    def _save(self):
        global CFG
        CFG["shortcut"]       = self.shortcut_edit.text().strip() or "v"
        CFG["font_size"]      = self.font_spin.value()
        CFG["padding"]        = self.padding_spin.value()
        CFG["preset_columns"] = self.cols_spin.value()
        CFG["text_alignment"] = self.align_combo.currentData()

        presets = []
        for i in range(self.presets_list.count()):
            t = self.presets_list.item(i).text().strip()
            if t:
                presets.append(t)
        CFG["presets"] = presets

        colors = []
        for row in range(self.colors_table.rowCount()):
            swatch  = self.colors_table.cellWidget(row, 0)
            name_it = self.colors_table.item(row, 1)
            if swatch and name_it:
                colors.append({
                    "name": name_it.text().strip(),
                    "hex":  swatch.property("hex_col") or "#2a2a2a",
                })
        CFG["colors"] = colors if colors else _DEFAULTS["colors"]

        _save_settings(CFG)
        self.accept()


def open_settings():
    dlg = SettingsDialog(QtWidgets.QApplication.activeWindow())
    dlg.exec_()


# ─────────────────────────────────────────────────────────────────────────────
#  BACKDROP CREATE DIALOG
# ─────────────────────────────────────────────────────────────────────────────

class BackdropDialog(QtWidgets.QDialog):

    _SCREEN_MARGIN = 16

    def __init__(self, cursor_pos, parent=None):
        super(BackdropDialog, self).__init__(parent)
        self.setWindowTitle("Backdrop Draw")
        self.setWindowFlags(Qt.Dialog | Qt.WindowStaysOnTopHint)
        self._cursor_pos = cursor_pos
        self._color      = _random_dark_color()   # random color by default
        self._font_size  = CFG.get("font_size", 42)
        self._alignment  = CFG.get("text_alignment", "center")
        self._bold       = True                   # bold label by default
        self._build_ui()

    def _build_ui(self):
        root = QtWidgets.QVBoxLayout(self)
        root.setSpacing(8)
        root.setContentsMargins(10, 10, 10, 10)

        # ── Label input ───────────────────────────────────────────────────────
        root.addWidget(QtWidgets.QLabel("<b>Label</b>"))
        self.name_edit = QtWidgets.QLineEdit()
        self.name_edit.setPlaceholderText("Type a name or click a preset below…")
        self.name_edit.setFixedHeight(28)
        self.name_edit.returnPressed.connect(self.accept)
        root.addWidget(self.name_edit)

        # ── Preset buttons grid ───────────────────────────────────────────────
        root.addWidget(QtWidgets.QLabel("<b>Presets</b>"))
        preset_widget = QtWidgets.QWidget()
        cols = CFG.get("preset_columns", 3)
        preset_layout = QtWidgets.QGridLayout(preset_widget)
        preset_layout.setSpacing(4)
        preset_layout.setContentsMargins(0, 0, 0, 0)

        presets = CFG.get("presets", [])
        for i, label in enumerate(presets):
            btn = QtWidgets.QPushButton(label)
            btn.setFixedHeight(28)
            btn.setStyleSheet(
                "QPushButton {"
                "  text-align: center;"
                "  padding: 2px 6px;"
                "  border-radius: 3px;"
                "  border: 1px solid #555;"
                "  background-color: #3a3a3a;"
                "}"
                "QPushButton:hover {"
                "  background-color: #4a6fa5;"
                "  border-color: #6a9fd8;"
                "  color: white;"
                "}"
                "QPushButton:pressed {"
                "  background-color: #2a5080;"
                "}"
            )
            btn.clicked.connect(self._make_label_handler(label))
            preset_layout.addWidget(btn, i // cols, i % cols)

        root.addWidget(preset_widget)

        # ── Color swatches ────────────────────────────────────────────────────
        root.addWidget(QtWidgets.QLabel("<b>Color</b>"))
        color_row = QtWidgets.QHBoxLayout()
        color_row.setSpacing(4)

        self._swatch_btns = []
        for c in CFG.get("colors", []):
            btn = QtWidgets.QPushButton()
            btn.setFixedSize(28, 28)
            btn.setToolTip(c["name"])
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(self._swatch_css(c["hex"], False))
            btn.clicked.connect(self._make_color_handler(c["hex"]))
            color_row.addWidget(btn)
            self._swatch_btns.append((btn, c["hex"]))

        color_row.addStretch()

        rand_btn = QtWidgets.QPushButton("🎲")
        rand_btn.setFixedSize(28, 28)
        rand_btn.setToolTip("Random color")
        rand_btn.setCursor(Qt.PointingHandCursor)
        rand_btn.clicked.connect(self._set_random_color)
        color_row.addWidget(rand_btn)

        custom_btn = QtWidgets.QPushButton("＋")
        custom_btn.setFixedSize(28, 28)
        custom_btn.setToolTip("Custom color…")
        custom_btn.setCursor(Qt.PointingHandCursor)
        custom_btn.clicked.connect(self._pick_custom_color)
        color_row.addWidget(custom_btn)

        self._color_preview = QtWidgets.QLabel()
        self._color_preview.setFixedSize(28, 28)
        color_row.addWidget(self._color_preview)

        root.addLayout(color_row)

        # ── Font size + Alignment ─────────────────────────────────────────────
        opts_row = QtWidgets.QHBoxLayout()
        opts_row.setSpacing(6)

        opts_row.addWidget(QtWidgets.QLabel("Size:"))
        self.font_spin = QtWidgets.QSpinBox()
        self.font_spin.setRange(10, 200)
        self.font_spin.setValue(self._font_size)
        self.font_spin.setFixedWidth(58)
        opts_row.addWidget(self.font_spin)

        opts_row.addSpacing(10)
        opts_row.addWidget(QtWidgets.QLabel("Align:"))

        self._align_btns = {}
        for symbol, val in [("◀", "left"), ("▬", "center"), ("▶", "right")]:
            btn = QtWidgets.QPushButton(symbol)
            btn.setCheckable(True)
            btn.setFixedSize(26, 26)
            btn.clicked.connect(self._make_align_handler(val))
            opts_row.addWidget(btn)
            self._align_btns[val] = btn

        self._align_btns[self._alignment].setChecked(True)

        opts_row.addSpacing(10)
        self.bold_check = QtWidgets.QCheckBox("Bold")
        self.bold_check.setChecked(self._bold)
        opts_row.addWidget(self.bold_check)

        opts_row.addStretch()
        root.addLayout(opts_row)

        # ── OK / Cancel ───────────────────────────────────────────────────────
        btns = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        root.addWidget(btns)

        self._apply_color(self._color)
        # No swatch is pre-selected since color is random

    # ── Handlers ──────────────────────────────────────────────────────────────

    def _make_label_handler(self, label):
        def h():
            self.name_edit.setText(label)
            self.name_edit.setFocus()
        return h

    def _make_color_handler(self, hex_col):
        def h():
            self._apply_color(hex_col)
        return h

    def _make_align_handler(self, val):
        def h():
            self._alignment = val
            for v, b in self._align_btns.items():
                b.setChecked(v == val)
        return h

    def _set_random_color(self):
        self._apply_color(_random_dark_color())
        for btn, _ in self._swatch_btns:
            btn.setStyleSheet(self._swatch_css(btn.toolTip(), False))

    def _pick_custom_color(self):
        chosen = QtWidgets.QColorDialog.getColor(
            QtGui.QColor(self._color), self, "Choose Color",
            QtWidgets.QColorDialog.DontUseNativeDialog,
        )
        if chosen.isValid():
            self._apply_color(chosen.name())
            for btn, _ in self._swatch_btns:
                btn.setStyleSheet(self._swatch_css("", False))

    # ── Color styling ─────────────────────────────────────────────────────────

    @staticmethod
    def _swatch_css(hex_col, selected):
        border = "3px solid white" if selected else "2px solid #555"
        bg = "background-color: %s; " % hex_col if hex_col.startswith("#") else ""
        return "%sborder: %s; border-radius: 4px;" % (bg, border)

    def _apply_color(self, hex_col):
        self._color = hex_col
        self._color_preview.setStyleSheet(
            "background-color: %s; border: 2px solid #888; border-radius: 4px;" % hex_col
        )
        for btn, col in self._swatch_btns:
            btn.setStyleSheet(
                "background-color: %s; border: %s; border-radius: 4px;" % (
                    col,
                    "3px solid white" if col == hex_col else "2px solid #555",
                )
            )

    # ── Return values ─────────────────────────────────────────────────────────

    def get_values(self):
        prefix = _alignment_prefix(self._alignment)
        label  = self.name_edit.text().strip()
        if self.bold_check.isChecked() and label:
            label = "<b>" + label + "</b>"
        if label:
            label = prefix + label
        return label, self._color, self.font_spin.value()

    # ── Position near cursor ──────────────────────────────────────────────────

    def showEvent(self, event):
        super(BackdropDialog, self).showEvent(event)
        self._position_near_cursor()
        self.name_edit.setFocus(Qt.OtherFocusReason)

    def _position_near_cursor(self):
        screen = QtWidgets.QApplication.screenAt(self._cursor_pos)
        if screen is None:
            screen = QtWidgets.QApplication.primaryScreen()
        sr = screen.availableGeometry()
        self.adjustSize()
        w, h, m = self.width(), self.height(), self._SCREEN_MARGIN
        x = self._cursor_pos.x() - w - 16
        y = self._cursor_pos.y() - h - 16
        x = max(sr.left() + m, min(x, sr.right()  - w - m))
        y = max(sr.top()  + m, min(y, sr.bottom() - h - m))
        self.move(x, y)


# ─────────────────────────────────────────────────────────────────────────────
#  RUBBER-BAND OVERLAY
# ─────────────────────────────────────────────────────────────────────────────

class DrawOverlay(QtWidgets.QWidget):

    area_selected = QtCore.Signal(QtCore.QRect, QtCore.QPoint)
    cancelled     = QtCore.Signal()

    def __init__(self):
        super(DrawOverlay, self).__init__(
            None,
            Qt.Window | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool,
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setAutoFillBackground(False)
        self.setMouseTracking(True)
        self._origin = None
        self._rubber = QtWidgets.QRubberBand(QtWidgets.QRubberBand.Rectangle, self)
        self.setGeometry(QtWidgets.QApplication.primaryScreen().geometry())
        self.show()
        self.raise_()
        self.activateWindow()
        self.setFocus(Qt.OtherFocusReason)
        self.grabMouse(Qt.CrossCursor)
        self.grabKeyboard()

    def paintEvent(self, _):
        pass

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._origin = e.pos()
            self._rubber.setGeometry(QtCore.QRect(self._origin, QtCore.QSize()))
            self._rubber.show()

    def mouseMoveEvent(self, e):
        if self._origin is not None:
            self._rubber.setGeometry(QtCore.QRect(self._origin, e.pos()).normalized())

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton and self._origin is not None:
            local  = QtCore.QRect(self._origin, e.pos()).normalized()
            g_tl   = self.mapToGlobal(local.topLeft())
            g_br   = self.mapToGlobal(local.bottomRight())
            g_rect = QtCore.QRect(g_tl, g_br)
            cur    = self.mapToGlobal(e.pos())
            self._close()
            if local.width() > 5 and local.height() > 5:
                self.area_selected.emit(g_rect, cur)
            else:
                self.cancelled.emit()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self._close()
            self.cancelled.emit()

    def _close(self):
        self.releaseMouse()
        self.releaseKeyboard()
        self._rubber.hide()
        self.hide()
        self.close()


# ─────────────────────────────────────────────────────────────────────────────
#  BACKDROP CREATION
# ─────────────────────────────────────────────────────────────────────────────

def _make_backdrop(dag_state, global_rect, cursor_pos):
    dlg = BackdropDialog(cursor_pos, QtWidgets.QApplication.activeWindow())
    if dlg.exec_() != QtWidgets.QDialog.Accepted:
        return

    label, hex_color, font_size = dlg.get_values()
    tl_x, tl_y, br_x, br_y = _global_rect_to_canvas(dag_state, global_rect)

    pad     = CFG.get("padding", 40)
    z_order = _next_z_order()

    bd = nuke.nodes.BackdropNode(
        xpos           = int(tl_x - pad),
        ypos           = int(tl_y - pad),
        bdwidth        = int((br_x - tl_x) + pad * 2),
        bdheight       = int((br_y - tl_y) + pad * 2),
        tile_color     = _hex_to_nuke_color(hex_color),
        note_font_size = font_size,
        z_order        = z_order,
        label          = label,
    )
    bd["z_order"].setValue(z_order)


# ─────────────────────────────────────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

_overlay = None

def start_backdrop_draw():
    global _overlay, CFG
    if _overlay is not None:
        return
    CFG = _load_settings()

    ng = _get_node_graph_widget()
    if ng is None:
        nuke.message(
            "Could not find the Node Graph (DAG) panel.\n"
            "Make sure the Node Graph is visible in your current layout."
        )
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


# ─────────────────────────────────────────────────────────────────────────────
#  REGISTRATION
# ─────────────────────────────────────────────────────────────────────────────

def register():
    sc = CFG.get("shortcut", "v")
    nuke.menu("Nuke").addCommand("Custom/Backdrop Draw",          start_backdrop_draw, sc)
    nuke.menu("Nodes").addCommand("Custom/Backdrop Draw",         start_backdrop_draw, sc)
    nuke.menu("Nuke").addCommand("Custom/Backdrop Draw Settings", open_settings)
    print("[Backdrop Draw] Registered — shortcut: %s" % sc)


if __name__ == "__main__":
    register()
