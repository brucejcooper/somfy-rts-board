# /// script
# requires-python = ">=3.12"
# dependencies = ["build123d==0.13.0"]
# ///
# Renders the case + board with F3D from the STEP files written by make_case.py.
# Run with:  uv run case/render_case.py
#   (needs F3D:  brew install f3d)
#
# Writes renders/*.png. For a live, rotatable view use:  uv run case/view.py
import os
import shutil
import subprocess
import sys

from build123d import Color, Compound, Location, Plane, Solid, export_step, import_step

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'renders')
os.makedirs(OUT, exist_ok=True)

F3D = shutil.which('f3d') or '/opt/homebrew/bin/f3d'
BODY_COLOUR = Color(0.92, 0.93, 0.95)   # F3D renders direct colours a little dark
LID_COLOUR = Color(0.35, 0.58, 0.88)

body = import_step(os.path.join(HERE, 'SomfyCase-body.step'))
lid = import_step(os.path.join(HERE, 'SomfyCase-lid.step'))
PCB_STEP = os.path.join(HERE, 'Somfy-pcb.step')            # not in git; see README to regenerate it
if not os.path.exists(PCB_STEP):
    sys.exit('case/Somfy-pcb.step not found - the renders need the board model (see README)')
pcb = import_step(PCB_STEP)                                # keeps KiCad's component colours
body.color, lid.color = BODY_COLOUR, LID_COLOUR

# front wall (component side) removed, to see the board sitting in the grooves
bb = body.bounding_box()
front_cut = Solid.make_box(bb.size.X + 2, bb.size.Y + 10, 5, Plane((bb.min.X - 1, bb.min.Y - 1, 9.0)))
body_cut = body - front_cut
body_cut.color = BODY_COLOUR
lid_cut = lid - front_cut
lid_cut.color = LID_COLOUR


def moved(shape, dy, colour=None):
    m = shape.moved(Location((0, dy, 0)))
    if colour is not None:
        m.color = colour
    return m


ISO = '-1,-0.8,-1.3'          # looking at the component side from front-right-top (Y is up)
SCENES = [
    # name,               parts,                                                         camera direction
    ('1-cutaway',         [body_cut, lid_cut, pcb],                                        ISO),
    ('2-assembled',       [body, lid, pcb],                                                ISO),
    ('3-bottom-ports',    [body, lid, pcb],                                                '-0.7,0.9,-1.0'),
    ('4-exploded',        [body, moved(lid, 45, LID_COLOUR), moved(pcb, 26)],              ISO),
    ('5-open-top',        [body, pcb],                                                     '-0.25,-1,-0.35'),
]

for old in os.listdir(OUT):
    if old.endswith('.png'):
        os.remove(os.path.join(OUT, old))

for name, parts, direction in SCENES:
    scene = os.path.join(OUT, name + '.step')
    export_step(Compound(children=parts), scene)
    png = os.path.join(OUT, name + '.png')
    subprocess.run([F3D, scene, '--no-config', '--output', png, '--resolution', '1800,1500',
                    '--up', '+Y', '--camera-direction', direction, '--camera-zoom-factor', '0.9',
                    '--background-color', '1,1,1', '--anti-aliasing', 'ssaa',
                    '--ambient-occlusion', '--grid=false', '--axis=false', '--filename=false',
                    # STEP colours arrive as a per-face RGB array; show them directly
                    '--scalar-coloring', '--coloring-by-cells', '--coloring-array', 'Colors',
                    '--coloring-component=-2', '--light-intensity', '1.6'],
                   check=True, capture_output=True)
    os.remove(scene)
    print('rendered', os.path.relpath(png, HERE))
