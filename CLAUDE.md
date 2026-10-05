# Somfy RTS radio board - notes for Claude

KiCad 10 carrier board (ESP32-DevKitC + Ebyte E07-M1101D-SMA CC1101, for ESPSomfy RTS) and a
3D-printed slide-in case modelled in build123d. Read README.md first for wiring and layout; this file
holds the design intent and the traps.

## Workflow

- Case: edit `case/make_case.py` (all dimensions are named settings at the top), watch it in
  `uv run case/view.py`, then **always run `uv run case/check_case.py`** before calling a change done.
  Every script declares its own pinned dependencies (uv inline metadata) - never add a venv.
- Board changed? Re-export `case/Somfy-pcb.step` (command in README), then run `check_case.py`: its
  "measurements vs board" line says if `TOP_MAX`, `USB_C`, `SMA_C`, `ANT_*` etc. need updating.
- KiCad files: if KiCad has the project open (`~Somfy.*.lck` files exist), do NOT edit
  `.kicad_pcb/.kicad_sch/.kicad_pro` on disk - KiCad overwrites them on save. Either ask the user to
  close the project, or edit the open board live through the KiCad MCP / IPC API (it is enabled).
  Verify with `kicad-cli sch erc` and `kicad-cli pcb drc --schematic-parity` (both should be clean
  apart from the Espressif footprint's small silkscreen labels).
- Renders: `uv run case/render_case.py` (F3D) for the case; `kicad-cli pcb render` for `images/`.

## Coordinates (case and board must agree)

Case geometry is in the board's own frame: origin at the bottom-left board corner, X across the board,
Y along it (0 = USB/SMA edge), Z through it (0 = PCB underside). This only works because the board STEP
is exported with `--user-origin 54.102x106.3244mm` - keep that exact origin if the board moves in KiCad.

## Design decisions (deliberate - don't "fix" these)

- **Print service**: JLC3DP **MJF PA12**. Clearances (`FIT`, `GROOVE_GAP`, `PRONG_GAP` 0.3,
  `GROOVE_CLR` 0.4, `SMA_CUT` 7.0) are sized for its +/-0.3 mm tolerance.
- **Walls**: JLC3DP rejected walls under 1 mm and prefers 2 mm. Every lid wall is >= 2.0 mm; that is
  why `LID_T` = 3.5, `LIP_T` = 2.0, `SIDE_BEHIND` = 5.0, `BACK_WALL` = 2.6 and the screw placement
  (`SCREW_INSET`, `CSK_EDGE`). `CSK_RELIEF` must stay 0 for JLC3DP (their checker flagged the 0.3 mm
  step); 0.3 is only for home FDM printing face down.
- **Bottom wall is 1.5 mm on purpose** so the micro-USB plug seats; JLC3DP accepts it (>= 1.0).
- **Screws**: 4 x M2.5 x 10 countersunk, self-tapping into 2.1 mm pilots in the side walls.
- **ESP32 antenna overhangs the top board edge by design** (Espressif guidance) - no copper under it,
  and keep lid features (prongs, screws) away from `ANT_X`.
- **PCB**: 2.5 mm rule-area keepouts down both sides are the slide rails; side margins to parts are
  equal (3.87 mm); bottom corners chamfered 1 mm as a lead-in. DevKitC is soldered directly, so the
  project footprint uses 1.0 mm holes / 1.6 mm pads (Espressif's 0.8 mm holes don't fit header pins).
- **Edge clearance**: board setup minimum is JLCPCB's 0.3 mm. There is intentionally no
  `Somfy.kicad_dru`: a footprint-specific rule (`A.Parent.Reference`) broke KiCad's Python DRC
  (`WriteDRCReport returned failure`). GND pour clearance is 0.3 mm so it flows between header pins.
- **Radio**: GDO0 -> GPIO13 (TX), GDO2 -> **GPIO4** (RX; not ESPSomfy's default 12, a strapping pin).
- **Logo**: `branding/mechination-logo-silk.svg` is the brand logo minus its background. The MCP
  `import_svg_logo` tool imports letter counters as separate filled polygons (they fill in); the fix
  was adding them as holes through the IPC API (KiCad stores them as keyhole outlines).

## Not in git (and why)

- `3dshapes/ESP32-DevKitC-32D.step` (SnapEDA/DigiKey model; licence forbids redistribution) and
  `case/Somfy-pcb.step` (it embeds that model). The repo is public - never commit either. Scripts
  run without them (board checks are skipped with a note).
- `jlcpcb/` - JLCPCB plugin fabrication export, regenerated from KiCad.

## Tooling traps

- **FreeCAD 1.1.4 crashes** (OpenCascade mesher, SIGSEGV) when loading/re-meshing parts in the GUI -
  don't use it as a viewer. Live view is OCP CAD Viewer in the browser (`view.py`).
- F3D ignores STEP colours unless given `--scalar-coloring --coloring-by-cells
  --coloring-array Colors --coloring-component=-2` (already in `render_case.py`).
- uv script deps must be **pinned**: an unpinned dependency made uv rebuild the environment on every
  run (~60 s startups).
- When testing `view.py` in the background: Python's output to a file is block-buffered (use
  `PYTHONUNBUFFERED=1`), and signalling `uv` does not stop the Python child - kill the child too, or
  stray watchers keep rebuilding on every save.

## Git

Public repo: `ssh://git@git.8bitcloud.com:222/bruce/somfy-rts-board.git` (Forgejo). The Forgejo
token available to Claude cannot create repositories and push-to-create is disabled - new repos must
be created by the user in the web UI.
