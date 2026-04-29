# Backdrop Draw for Nuke

A Nuke tool by **Eduardo Brandao** — [eduardo@bosonpost.com.br](mailto:eduardo@bosonpost.com.br)

Draw a rubber-band area directly in the Node Graph to create a labeled, colored BackdropNode — no need to select nodes first.

---

## Features

- **Draw to create** — press the shortcut, click and drag to define the area, done
- **Dialog near your cursor** — the label/color window appears right where your mouse is
- **Instant typing** — the label field is focused automatically on open
- **Preset labels** — dropdown with common comp department labels
- **Color palette** — 8 quick-pick colors + full custom color picker
- **Auto z-order** — each new backdrop is placed behind all existing ones automatically
- **Works in all layouts** — correctly identifies the Node Graph in Compositing, Scripting, and any custom layout

---

## Requirements

- Nuke 12 or later (tested on Nuke 13/14/15)
- PySide2 (bundled with Nuke)

---

## Installation

1. Copy `backdrop_draw.py` to your `.nuke` directory:
   - **Linux / Mac:** `~/.nuke/`
   - **Windows:** `%USERPROFILE%\.nuke\`

2. Open (or create) `menu.py` in the same `.nuke` folder and add:

```python
import backdrop_draw
backdrop_draw.register()
```

3. Restart Nuke.

On startup you should see in the Script Editor:
```
[Backdrop Draw] Registered — shortcut: v
```

---

## Usage

| Step | Action |
|------|--------|
| 1 | Press **`v`** inside the Node Graph — cursor becomes a crosshair |
| 2 | Click and drag to draw the backdrop area |
| 3 | Release the mouse — the dialog appears near your cursor |
| 4 | Type a custom label **or** pick one from the Presets dropdown |
| 5 | Choose a color from the palette or use the custom color picker |
| 6 | Click **OK** — the backdrop is created behind your nodes |

Press **Escape** at any time to cancel.

---

## Preset Labels

The following labels are available in the dropdown out of the box:

`Additive_Key` · `Bloom` · `Camera_Projection` · `Camera_Setup` · `CG` · `CG:Ambient` · `CG:Diffuse` · `CG:Reflection` · `CG:Refraction` · `CG:Shadow` · `CG:Specular` · `Cleanup` · `Controllers` · `Color_Correction` · `Despill` · `Edge_Fixes` · `Elements` · `FX` · `Key` · `Matte` · `Lens_Flare` · `Light_Setup` · `Light_Wrap` · `Output` · `Previous_Versions` · `References` · `Relight` · `Resources` · `Rig_Removal` · `Roto` · `Set_Extension` · `Stereo_Fixes` · `Temp` · `Test` · `Transformations`

---

## Customisation

Edit the `SETTINGS` dictionary at the top of `backdrop_draw.py`:

```python
SETTINGS = {
    "shortcut"      : "v",       # Keyboard shortcut
    "default_label" : "",        # Pre-filled label text
    "font_size"     : 42,        # Backdrop label font size
    "padding"       : 40,        # Extra space around the drawn area
    "presets"       : [...],     # List of preset label strings
    "preset_colors" : [...],     # List of (name, "#rrggbb") tuples
}
```

### Adding preset labels

```python
"presets": [
    "Additive_Key",
    "My_Custom_Label",   # <-- add your own here
    ...
],
```

### Adding preset colors

```python
"preset_colors": [
    ("Dark Gray", "#2a2a2a"),
    ("Teal",      "#0d4040"),   # <-- add your own here
    ...
],
```

---

## Troubleshooting

**The tool does not activate when I press `v`**
Make sure the Node Graph panel has focus (click inside it first). The shortcut only works when registered — check that `backdrop_draw.register()` is in your `menu.py` and that Nuke was restarted after installing.

**"Could not find the Node Graph" message**
The Node Graph must be visible in the current layout. Switch to a layout that shows the DAG panel and try again.

**The backdrop appears in the wrong position**
This can happen if you zoom or pan the Node Graph between pressing the shortcut and drawing. The tool captures the canvas state at the moment the shortcut is pressed — avoid panning/zooming between activation and drawing.

---

## License

MIT — free to use, modify, and distribute.
