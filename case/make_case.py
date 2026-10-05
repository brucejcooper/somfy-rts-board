# /// script
# requires-python = ">=3.12"
# dependencies = ["build123d==0.13.0"]
# ///
# Parametric slide-in case for the Somfy base board (ESP32-DevKitC + E07 CC1101).
# Run with:  uv run case/make_case.py [output folder]
#   Live view:  uv run case/view.py   (browser viewer; rebuilds whenever this file is saved)
#   Checks:     uv run case/check_case.py   (fit, wall thickness, overhangs, measurements)
#   uv reads the dependencies above and manages the environment itself - nothing to install or activate.
#
# Clearances are sized for JLC3DP MJF nylon (about +/-0.3 mm).
#
# Coordinates match case/Somfy-pcb.step (exported from KiCad with the user origin at
# the bottom-left board corner):
#   X = across the board (0 = ESP32 side edge), Y = along the board (0 = USB/SMA edge),
#   Z = through the board (0 = PCB underside, components on +Z).
# The PCB slides in from the open top (+Y) in side grooves; the USB and SMA exit through
# the bottom wall (-Y); a lid closes the top with countersunk M2.5 screws into the side walls.
import os
import sys

from build123d import Plane, Solid, Vector, Wire, export_step, export_stl, import_step

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else HERE

# ---- board (from KiCad) ----
PCB_W = 52.435          # board width (X)
PCB_L = 48.057          # board length (Y)
PCB_T = 1.6             # board thickness incl. mask
RAIL = 2.5              # copper/part-free strip along each side edge (KiCad keepout)

# ---- component envelope (measured from case/Somfy-pcb.step) ----
# check_case.py re-measures these from the board export and reports any that have gone stale.
TOP_MAX = 8.29          # tallest part above the PCB underside (WROOM shield)
BOT_MIN = -4.41         # DevKitC pin tails (clip them and you can shrink BACK_CLR)
ANT_YMAX = 54.28        # ESP32 antenna tip, past the top board edge
ANT_X = (9.07, 27.07)   # antenna span, keep lid features away from it
USB_C = (18.07, 6.09)   # micro-USB centre (X, Z)
SMA_C = (40.94, 4.895)  # SMA body centre (X, Z)

# ---- case parameters ----
WALL = 2.0              # front wall
BACK_WALL = 2.6         # back wall (thicker so the lower lid screws stay 2 mm from the lid edge)
CSK_EDGE = 2.0          # nylon between a countersink and the lid's outer faces
BOTTOM_WALL = 1.5       # wall with the USB/SMA openings (thin so the USB plug seats)
BITE = 2.0              # how far each board edge sits inside the groove
GROOVE_CLR = 0.4        # groove depth beyond the board edge
GROOVE_GAP = 0.3        # clearance above/below the board in the groove
SIDE_BEHIND = 5.0       # side wall material behind the groove (screws live here)
FRONT_CLR = 1.2         # air above the tallest part
BACK_CLR = 1.0          # air below the pin tails
END_CLR = 1.2           # air beyond the antenna tip
EDGE_STOP = 0.3         # groove floor sits at Y=0, bottom wall inner face this much lower
LID_T = 3.5             # leaves 2.0 mm under the countersinks (JLC3DP minimum wall 1.0, preferred 2.0)
LIP_DEPTH = 2.0         # locating lip on the lid that drops into the opening
LIP_T = 2.0
FIT = 0.3               # lid lip clearance
PRONG_GAP = 0.3         # lid prongs to the top board edge
USB_CUT = (12.0, 8.0)   # micro-USB plug overmould opening (W x H)
SMA_CUT = 7.0           # square opening around the 6.4 mm SMA body (snug, takes torque)
SCREW_PILOT = 2.1       # M2.5 self-tapping into PLA/PETG (use 3.6 for M2.5 heat-set inserts)
SCREW_CLEAR = 2.8
CSK_D = 5.2             # M2.5 countersunk head 4.7 + clearance, 90 deg
CSK_RELIEF = 0.0        # straight section at the countersink mouth; 0 for JLC3DP MJF (their checker flags it), 0.3 for home FDM printing face down
SCREW_DEPTH = 10.0
SCREW_INSET = 4.7       # screw centre from the outer side face: countersink 2.1 mm from the lid edge
FILLET = 2.0            # radius of the four long outer edges
SCREW_TOP_DROP = 3.0    # upper screws sit this far below the front wall's inner face (2.4 mm countersink-to-edge)
LEAD_IN = 0.8           # 45 deg flare at the groove mouths so the board finds the slot
USB_CUT_R = 1.5         # corner radius of the USB opening
SMA_CUT_R = 0.6         # corner radius of the SMA opening
# lid prongs press on the top board edge at both corners
PRONG_ANT_CLEAR_L = 3.0 # left prong stops this far short of the antenna
PRONG_ANT_CLEAR_R = 7.0 # right prong starts this far past the antenna (also clears the DevKitC board edge, x ~32.3)
PRONG_BELOW = 1.2       # prongs reach this far below the board underside...
PRONG_TOP_GAP = 0.2     # ...and stop this far below the board's top surface, clear of the header plastic

# modelling tolerances (not design dimensions)
EPS = 0.01              # cutting tools overlap the faces they cut by this, to avoid zero-thickness slivers
THRU = 1.0              # cutting tools run this far past the material so they always cut through

# derived
X_IN0, X_IN1 = BITE, PCB_W - BITE                    # inner side faces
X_OUT0 = -GROOVE_CLR - SIDE_BEHIND
X_OUT1 = PCB_W + GROOVE_CLR + SIDE_BEHIND
Z_IN0, Z_IN1 = BOT_MIN - BACK_CLR, TOP_MAX + FRONT_CLR
Z_OUT0, Z_OUT1 = Z_IN0 - BACK_WALL, Z_IN1 + WALL
Y_IN0 = -EDGE_STOP
Y_OUT0 = Y_IN0 - BOTTOM_WALL
Y_TOP = ANT_YMAX + END_CLR                           # open end of the body
SCREW_X = X_OUT0 + SCREW_INSET, X_OUT1 - SCREW_INSET
SCREW_Z = (Z_IN1 - SCREW_TOP_DROP, Z_OUT0 + CSK_EDGE + CSK_D / 2)  # upper, lower; both clear of the groove band

ALONG_Y, AGAINST_Y = Vector(0, 1, 0), Vector(0, -1, 0)


def box(x0, x1, y0, y1, z0, z1):
    return Solid.make_box(x1 - x0, y1 - y0, z1 - z0, Plane((x0, y0, z0)))


def along(axis_dir, x, y, z):
    """A plane at (x, y, z) whose normal points along axis_dir, for cylinders and cones."""
    return Plane(origin=(x, y, z), z_dir=axis_dir)


def y_parallel(edge):
    return abs(edge.tangent_at(0).Y) > 0.99


def rounded_rect_prism(cx, cz, w, h, r, y0, y1):
    """Prism along Y with a rounded-rectangle cross-section in XZ."""
    b = box(cx - w / 2, cx + w / 2, y0, y1, cz - h / 2, cz + h / 2)
    return b.fillet(r, [e for e in b.edges() if y_parallel(e)])


def fillet_long_edges(shape, r):
    """Round the four outer edges that run along Y."""
    edges = []
    for e in shape.edges():
        p = e.position_at(0)
        if (y_parallel(e) and e.length > 1   # skip tiny edges left by other features
                and min(abs(p.X - X_OUT0), abs(p.X - X_OUT1)) < 1e-3
                and min(abs(p.Z - Z_OUT0), abs(p.Z - Z_OUT1)) < 1e-3):
            edges.append(e)
    try:
        return shape.fillet(r, edges)
    except Exception as ex:  # keep going with sharp edges rather than fail
        print('fillet skipped:', ex)
        return shape


def xz_rect(x0, x1, z0, z1, y):
    return Wire.make_polygon([(x0, y, z0), (x0, y, z1), (x1, y, z1), (x1, y, z0)], close=True)


# ---- body ----
body = box(X_OUT0, X_OUT1, Y_OUT0, Y_TOP, Z_OUT0, Z_OUT1)
body = fillet_long_edges(body, FILLET)
body -= box(X_IN0, X_IN1, Y_IN0, Y_TOP + THRU, Z_IN0, Z_IN1)
for gx0, gx1 in ((-GROOVE_CLR, X_IN0 + EPS), (X_IN1 - EPS, PCB_W + GROOVE_CLR)):
    body -= box(gx0, gx1, 0.0, Y_TOP + THRU, -GROOVE_GAP, PCB_T + GROOVE_GAP)
# lead-in at the groove mouths so the board finds the slot
for gx in (-GROOVE_CLR, PCB_W + GROOVE_CLR):
    inner = X_IN0 if gx < 0 else X_IN1
    lo, hi = sorted((gx, inner))
    bot = xz_rect(lo, hi, -GROOVE_GAP, PCB_T + GROOVE_GAP, Y_TOP + EPS - (LEAD_IN + EPS))
    top = xz_rect(lo, hi, -GROOVE_GAP - LEAD_IN, PCB_T + GROOVE_GAP + LEAD_IN, Y_TOP + EPS)
    body -= Solid.make_loft([bot, top], ruled=True)
# USB and SMA openings through the bottom wall
# USB opening is clipped at the front wall's inner face so it leaves no bridge when printed upright
usb_cut = rounded_rect_prism(USB_C[0], USB_C[1], USB_CUT[0], USB_CUT[1], USB_CUT_R, Y_OUT0 - THRU, Y_IN0 + EPS)
body -= usb_cut & box(X_OUT0, X_OUT1, Y_OUT0 - 2 * THRU, Y_IN0 + THRU, Z_OUT0, Z_IN1)
body -= rounded_rect_prism(SMA_C[0], SMA_C[1], SMA_CUT, SMA_CUT, SMA_CUT_R, Y_OUT0 - THRU, Y_IN0 + EPS)
# lid screw pilot holes in the side walls
for sx in SCREW_X:
    for sz in SCREW_Z:
        body -= Solid.make_cylinder(SCREW_PILOT / 2, SCREW_DEPTH + EPS, along(AGAINST_Y, sx, Y_TOP + EPS, sz))
body = body.clean()

# ---- lid ----
lid = box(X_OUT0, X_OUT1, Y_TOP, Y_TOP + LID_T, Z_OUT0, Z_OUT1)
lid = fillet_long_edges(lid, FILLET)
lip_outer = box(X_IN0 + FIT, X_IN1 - FIT, Y_TOP - LIP_DEPTH, Y_TOP + EPS, Z_IN0 + FIT, Z_IN1 - FIT)
lip_inner = box(X_IN0 + FIT + LIP_T, X_IN1 - FIT - LIP_T, Y_TOP - LIP_DEPTH - THRU, Y_TOP + 2 * EPS,
                Z_IN0 + FIT + LIP_T, Z_IN1 - FIT - LIP_T)
lid += lip_outer - lip_inner
# hold-down prongs that rest on the top board edge at both corners, away from the antenna
PRONG_Z = (-PRONG_BELOW, PCB_T - PRONG_TOP_GAP)
for px0, px1 in ((X_IN0 + FIT, ANT_X[0] - PRONG_ANT_CLEAR_L), (ANT_X[1] + PRONG_ANT_CLEAR_R, X_IN1 - FIT)):
    lid += box(px0, px1, PCB_L + PRONG_GAP, Y_TOP + EPS, *PRONG_Z)
csk_h = (CSK_D - SCREW_CLEAR) / 2
for sx in SCREW_X:
    for sz in SCREW_Z:
        lid -= Solid.make_cylinder(SCREW_CLEAR / 2, LID_T + 2 * THRU, along(ALONG_Y, sx, Y_TOP - THRU, sz))
        lid -= Solid.make_cone(SCREW_CLEAR / 2, CSK_D / 2 + EPS, csk_h + EPS,
                               along(ALONG_Y, sx, Y_TOP + LID_T - CSK_RELIEF - csk_h, sz))
        if CSK_RELIEF > 0:
            lid -= Solid.make_cylinder(CSK_D / 2, CSK_RELIEF + EPS,
                                       along(ALONG_Y, sx, Y_TOP + LID_T - CSK_RELIEF, sz))
lid = lid.clean()

# ---- checks against the real board/components ----
# Somfy-pcb.step is not in git (it embeds the ESP32-DevKitC vendor model); see README to regenerate it.
PCB_STEP = os.path.join(HERE, 'Somfy-pcb.step')
if os.path.exists(PCB_STEP):
    pcb = import_step(PCB_STEP)
    for name, shp in (('body', body), ('lid', lid)):
        hits = []
        for s in pcb.solids():
            if s.bounding_box().overlaps(shp.bounding_box()):
                common = shp & s
                v = common.volume if common is not None else 0.0
                if v > 1e-3:
                    hits.append('%.1f mm3 @ %s' % (v, s.bounding_box()))
        print('%s interference: %s' % (name, hits or 'none'))
else:
    print('interference check skipped: case/Somfy-pcb.step not found (see README)')

ob = body.bounding_box()
print('body outer  %.2f x %.2f x %.2f mm (W x L x D)' % (ob.size.X, ob.size.Y, ob.size.Z))
print('closed case %.2f x %.2f x %.2f mm' % (ob.size.X, ob.size.Y + LID_T, ob.size.Z))

# ---- save ----
os.makedirs(OUT, exist_ok=True)
for name, shp in (('body', body), ('lid', lid)):
    # written under a temporary name and swapped in, so nothing ever reads a half-written file
    for ext, writer in (('stl', lambda f: export_stl(shp, f, tolerance=0.05)), ('step', lambda f: export_step(shp, f))):
        final = os.path.join(OUT, 'SomfyCase-%s.%s' % (name, ext))
        tmp = os.path.join(OUT, '.tmp-SomfyCase-%s.%s' % (name, ext))
        writer(tmp)
        os.replace(tmp, final)
print('saved to', OUT)

