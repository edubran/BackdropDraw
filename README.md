# Backdrop Draw for Nuke

A Nuke tool by **Eduardo Brandao** — [eduardo@bosonpost.com.br](mailto:eduardo@bosonpost.com.br)

Draw a rubber-band area directly in the Node Graph to create a labeled, colored BackdropNode — fast, precise, and fully configurable per user.

---

## Features

- **Draw to create** — press the shortcut, click and drag to define the area
- **Preset label buttons** — click any preset to instantly fill the label field
- **Color swatches** — visual color squares with tooltip on hover
- **Random color** — one click for a random muted backdrop color
- **Custom color picker** — full color picker when you need something specific
- **Font size control** — adjust per backdrop, right in the dialog
- **Text alignment** — left, center, or right per backdrop
- **Auto z-order** — each new backdrop goes behind all existing ones automatically
- **Dialog near cursor** — the dialog appears where your mouse is for speed
- **Auto-focus label field** — start typing immediately, no extra clicks
- **Per-user settings** — configure via Edit > Backdrop Draw Settings, saved to JSON
- **Works in all layouts** — correctly identifies the DAG in any Nuke layout

---

## Requirements

- Nuke 12 or later
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

On startup you will see in the Script Editor:
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
| 4 | Click a **preset button** to fill the label, or type a custom name |
| 5 | Click a **color swatch**, press 🎲 for random, or ＋ for custom |
| 6 | Adjust **font size** and **text alignment** if needed |
| 7 | Press **Enter** or click **OK** — backdrop is created |

Press **Escape** at any time to cancel.

---

## Settings

Open **Edit > Backdrop Draw Settings** in the Nuke menu bar.

Settings are saved per-user at `~/.nuke/backdrop_draw_settings.json` and include:

| Setting | Description |
|---------|-------------|
| Shortcut key | The keyboard shortcut to activate the tool (requires restart) |
| Default font size | Starting font size in the dialog |
| Padding | Extra space added around the drawn area (canvas units) |
| Preset button columns | Number of columns in the preset grid (1–6) |
| Default text alignment | Left, Center, or Right |
| Preset Labels | One label per line — edit freely |
| Preset Colors | One color per line in format `Name #rrggbb` |

---

## Default Preset Labels

`Additive_Key` · `Bloom` · `Camera_Projection` · `Camera_Setup` · `CG` · `CG:Ambient` · `CG:Diffuse` · `CG:Reflection` · `CG:Refraction` · `CG:Shadow` · `CG:Specular` · `Cleanup` · `Controllers` · `Color_Correction` · `Despill` · `Edge_Fixes` · `Elements` · `FX` · `Key` · `Matte` · `Lens_Flare` · `Light_Setup` · `Light_Wrap` · `Output` · `Previous_Versions` · `References` · `Relight` · `Resources` · `Rig_Removal` · `Roto` · `Set_Extension` · `Stereo_Fixes` · `Temp` · `Test` · `Transformations`

---

## Troubleshooting

**The tool does not activate when I press `v`**
Make sure the Node Graph panel has focus (click inside it first). After changing the shortcut in Settings, a Nuke restart is required.

**"Could not find the Node Graph" message**
The Node Graph must be visible in the current layout. Switch to a layout that includes the DAG panel and try again.

**The backdrop appears in the wrong position**
The tool captures zoom and canvas position at the moment the shortcut is pressed. Avoid panning or zooming the Node Graph between pressing the shortcut and finishing the draw.

---

## License

MIT — free to use, modify, and distribute.
