# /// script
# requires-python = ">=3.12"
# dependencies = ["build123d==0.13.0"]
# ///
# Fit and printability checks for the Somfy case.
# Run with:  uv run case/check_case.py [folder with SomfyCase-body.step / -lid.step]
#
#   - board insertion: slide the real board (Somfy-pcb.step) down the grooves and look for collisions
#   - minimum wall thickness (rays cast inward from points spread over every face)
#   - overhangs steeper than 45 deg in the print orientations (body on its USB/SMA wall, lid face down)
import os
import sys

from build123d import Edge, Vector, import_step

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = sys.argv[1] if len(sys.argv) > 1 else HERE
MIN_WALL = 2.0          # report walls thinner than this (JLC3DP minimum 1.0, preferred 2.0)

body = import_step(os.path.join(SRC, 'SomfyCase-body.step'))
lid = import_step(os.path.join(SRC, 'SomfyCase-lid.step'))
PCB_STEP = os.path.join(HERE, 'Somfy-pcb.step')    # not in git; see README to regenerate it
pcb_solids = import_step(PCB_STEP).solids() if os.path.exists(PCB_STEP) else None


def volume_of(shape):
    return shape.volume if shape is not None else 0.0


# ---- board insertion sweep ----
if pcb_solids is None:
    print('insertion sweep skipped: case/Somfy-pcb.step not found (see README)')
else:
    hits = []
    body_bb = body.bounding_box()
    for step in range(140):
        dy = step * 0.5
        for s in pcb_solids:
            moved = s.moved_by((0, dy, 0)) if hasattr(s, 'moved_by') else s.translate(Vector(0, dy, 0))
            if moved.bounding_box().overlaps(body_bb) and volume_of(body & moved) > 1e-3:
                hits.append(dy)
    print('insertion sweep (0-70 mm): %s' % ('no collisions' if not hits else 'collides at %s mm' % sorted(set(hits))))


# ---- wall thickness ----
def thinnest(shape, samples=9):
    found = []
    for f in shape.faces():
        for i in range(samples):
            for j in range(samples):
                u, v = (i + 0.5) / samples, (j + 0.5) / samples
                p = f.position_at(u, v)
                if not f.is_inside(p):
                    continue
                n = f.normal_at(u, v)
                ray = Edge.make_line(p - n * 0.002, p - n * 30)
                inside = shape & ray
                if inside is None:
                    continue
                for e in inside.edges():
                    if min((e.position_at(0) - p).length, (e.position_at(1) - p).length) < 0.01:
                        found.append((e.length, p))
    found.sort(key=lambda t: t[0])
    return found


for name, shape in (('body', body), ('lid', lid)):
    walls = thinnest(shape)
    thin = [(t, p) for t, p in walls if t < MIN_WALL - 0.005]
    print('%s: thinnest wall %.2f mm (%d samples); under %.1f mm: %s' % (
        name, walls[0][0], len(walls), MIN_WALL,
        'none' if not thin else ', '.join('%.2f @ (%.1f, %.1f, %.1f)' % (t, p.X, p.Y, p.Z) for t, p in thin[:6])))

# ---- overhangs in the print orientation ----
for name, shape, up in (('body', body, Vector(0, 1, 0)), ('lid', lid, Vector(0, -1, 0))):
    bed = min(Vector(v).dot(up) for v in shape.vertices())
    bad = []
    for f in shape.faces():
        n = f.normal_at(f.center())
        height = f.center().dot(up) - bed
        if -n.dot(up) > 0.71 and height > 0.05:
            bad.append((round(f.area, 2), round(height, 2)))
    print('%s: overhangs over 45 deg when printed %s: %s' % (
        name, 'on its USB/SMA wall' if name == 'body' else 'face down', bad or 'none'))

print('solids: body %d, lid %d; valid: body %s, lid %s' % (
    len(body.solids()), len(lid.solids()), body.is_valid, lid.is_valid))
