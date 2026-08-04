# See-Through — Week 1: Geometry

The foundation. Every later week inherits this week's accuracy, so the gate
at the bottom is not optional.

## Install

```bash
python3 -m venv venv && source venv/bin/activate
pip install opencv-contrib-python numpy
```

`opencv-contrib-python`, not plain `opencv-python` — ArUco lives in contrib.

## Frame conventions

Write these down. Check every transform against them.

```
World:   X right, Y forward, Z UP.  Floor = z 0.  Right-handed.
Camera:  x right, y DOWN, z FORWARD  (OpenCV convention)

solvePnP gives world -> camera:   X_cam = R @ X_world + t
Camera position in world:         C = -R.T @ t
Ray direction to world:           d_world = R.T @ d_cam
```

When something comes out mirrored or inside-out, it is one of these applied
backwards. It always is.

## Step 1 — Print markers

```bash
python3 -m seethrough.make_markers --count 6 --size-mm 150
```

Print at **100% scale**. Turn off "fit to page" — it silently rescales and
every measurement afterwards is wrong by that factor. Then take a ruler and
**measure the printed black square**. Put the real number in `room.json` as
`marker_size` (in metres).

Stick them on one wall. Two heights, three across, well spread. Spread beats
quantity: six markers clustered together are worse than four in the corners.

## Step 2 — Measure the room

Pick an origin — a floor corner is easiest. Measure each marker's **centre**
and write it into `config/room.json`:

```json
"markers": {
  "0": [-1.50, 3.00, 1.40]
}
```

That's x, y, z in metres. Be careful here: a 2cm error in a marker position
propagates into every camera pose that uses it.

`marker_corners_world()` in `calibrate_extrinsics.py` assumes markers are on a
wall facing **-Y**. If yours face a different direction, edit that function.
Getting it wrong produces a mirrored solution — confusing to debug, trivial to
fix once you know.

## Step 3 — Intrinsics, once per camera ever

```bash
python3 -m seethrough.calibrate_intrinsics --device 0 --out calib/cam_a.json
```

Print a 9×6 chessboard on rigid card. Hold it at many angles and distances.
**Fill the frame corners** — that's where lens distortion lives and where a
calibration usually goes wrong. 20+ views.

Target: RMS under 0.5 px. Over 1.5 px, recapture.

This never needs redoing. Not when you move the camera, not in a new room.

## Step 4 — Extrinsics, once per room

```bash
python3 -m seethrough.calibrate_extrinsics \
  --device 0 --name cam_a \
  --intrinsics calib/cam_a.json --room config/room.json
```

Aim the camera so it sees 2+ markers, 3+ is much better. Press SPACE.
It prints the camera position and reprojection error, and writes into the
room file.

Repeat with `--name cam_b` for the second camera.

## Step 5 — THE GATE

```bash
python3 -m seethrough.verify --device 0 --name cam_a --room config/room.json
```

A green 1-metre grid is drawn on the floor in the camera view. **First check:
does that grid line up with real features in your room?** If it's skewed or
floating, stop — the pose is wrong.

Then click floor points. Each prints a world coordinate. Go measure that exact
spot with a tape measure.

**Pass:** under 10cm error at 2m, 4m and 6m from the camera.

**If you fail:**

| Symptom | Cause |
|---|---|
| Grid tilted or floating | Marker positions in the JSON are wrong |
| Error grows with distance | Intrinsics — recalibrate, more corner coverage |
| Mirrored / inside-out | Marker facing direction in `marker_corners_world` |
| Constant offset everywhere | Origin measured from the wrong corner |
| Reprojection > 3 px | Wrong `marker_size` — did you measure the print? |

**Do not start week 2 until this passes.** A 2° pose error becomes 35cm at
10m, and you will not discover it until week 5 when the demo looks broken.

## Record for your README

- Intrinsic RMS per camera (px)
- Extrinsic reprojection error per camera (px)
- Measured world error at 2m / 4m / 6m (cm)

These are the first numbers in your evaluation table.

## What's here

```
seethrough/
  geometry.py               Camera + Room. All transforms. Unit-tested.
  make_markers.py           Printable ArUco generator
  calibrate_intrinsics.py   Chessboard -> K, dist
  calibrate_extrinsics.py   Markers -> camera pose in world
  verify.py                 The gate: click pixel, get world coordinate
config/room.json            Everything room-specific. New room = new file.
```

`geometry.py` also has `triangulate()` — two cameras, one point, no
ground-plane assumption. That's week 3's tool, already built and tested.

Nothing about the room is hardcoded. New room means a new JSON, not new code.
That's what makes step 6 (trajectory calibration, no markers) a drop-in later:
it produces the same `rvec`/`tvec`, just from your walking path instead of
printed squares.
