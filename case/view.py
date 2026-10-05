# /// script
# requires-python = ">=3.12"
# dependencies = ["build123d==0.13.0", "ocp_vscode==4.1.0", "ocp_viewer==1.1.3"]
# ///
# Live 3D view of the case in a browser tab (OCP CAD Viewer).
#   Run with:  uv run case/view.py          (Ctrl+C to stop)
# Starts the viewer, opens http://localhost:3939/viewer, builds the case, and rebuilds whenever
# make_case.py is saved. Your camera position is kept between updates.
import os
import runpy
import signal
import subprocess
import sys
import time
import traceback
import webbrowser

from build123d import import_step
from ocp_vscode import Camera, port_check, set_port, show

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, 'make_case.py')
PORT = 3939
URL = 'http://localhost:%d/viewer' % PORT

viewer = None


def stop_viewer(*_):
    if viewer is not None and viewer.poll() is None:
        viewer.terminate()
    sys.exit(0)


signal.signal(signal.SIGTERM, stop_viewer)
signal.signal(signal.SIGHUP, stop_viewer)       # terminal window closed
if not port_check(PORT):
    viewer = subprocess.Popen([sys.executable, '-m', 'ocp_viewer', '--port', str(PORT)],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(60):
        if port_check(PORT):
            break
        time.sleep(0.25)
set_port(PORT)
OPEN_BROWSER = '--no-browser' not in sys.argv
if OPEN_BROWSER:
    webbrowser.open(URL)
print('viewer: %s' % URL)

BOARD_STEP = os.path.join(HERE, 'Somfy-pcb.step')               # not in git; see README
board = import_step(BOARD_STEP) if os.path.exists(BOARD_STEP) else None   # loaded once
if board is None:
    print('note: case/Somfy-pcb.step not found - showing the case without the board (see README)')


def build(first):
    started = time.time()
    try:
        sys.argv = [SCRIPT]                                      # make_case.py sees no options of ours
        g = runpy.run_path(SCRIPT, run_name='__main__')          # make_case.py, unchanged
    except Exception:
        traceback.print_exc()
        print('build FAILED - fix make_case.py and save again')
        return
    parts = [(g['body'], 'body', (0.80, 0.82, 0.86), 0.65), (g['lid'], 'lid', (0.25, 0.45, 0.70), 0.8)]
    if board is not None:
        parts.append((board, 'board', None, 1.0))
    show(*[p[0] for p in parts], names=[p[1] for p in parts],
         colors=[p[2] for p in parts], alphas=[p[3] for p in parts],
         reset_camera=Camera.RESET if first else Camera.KEEP)
    print('updated in %.1fs' % (time.time() - started))


try:
    last = os.path.getmtime(SCRIPT)
    build(first=True)
    print('watching %s - save it to rebuild, Ctrl+C to stop' % os.path.relpath(SCRIPT))
    while True:
        time.sleep(0.5)
        now = os.path.getmtime(SCRIPT)
        if now != last:
            last = now
            print('rebuilding...')
            build(first=False)
except KeyboardInterrupt:
    pass
finally:
    if viewer is not None and viewer.poll() is None:
        viewer.terminate()
