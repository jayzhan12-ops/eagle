# CLAUDE.md — project context

Read this before doing anything. Then read `FULL_GUIDE.md` for the overall
plan and `WEEK1_STEPS.md` for the current week's procedure.

---

## What we are building

Occlusion-aware AR. A fixed camera in one room detects a person and reports
their **world coordinates**. An iPhone in the corridor, which knows its own
world coordinates from ArUco markers, renders a wireframe skeleton at that
position with depth testing disabled — so it appears to stand on the wall.

Nothing sees through walls. The effect comes from a shared coordinate frame
plus a rendering trick.

**Timeline:** 6 weeks. **Budget:** ~$50. **Owner:** a robotics engineering
technology student, comfortable with Python basics, new to computer vision.

---

## Current status

**Week 1 of 6. Geometry and calibration only.**

Already written and unit-tested:

| File | Purpose |
|---|---|
| `seethrough/geometry.py` | `Camera`, `Room`, `pixel_to_plane`, `triangulate` |
| `seethrough/make_markers.py` | Generates printable ArUco markers |
| `seethrough/calibrate_intrinsics.py` | Chessboard → K, dist |
| `seethrough/calibrate_extrinsics.py` | Markers → camera pose |
| `seethrough/verify.py` | The week 1 gate: click pixel → world coord |
| `seethrough/test_stream.py` | Tests wireless camera streams |
| `config/room.json` | All room-specific data |

**The week 1 goal is a single number:** click a floor point in the camera
view, get a world coordinate, and have it be within 10 cm of a tape-measure
reading at 2 m, 4 m and 6 m.

---

## Hard constraints

**Do not build ahead.** No detection, no tracking, no rendering, no
WebSocket server until week 1's gate passes. If asked for something from a
later week, say so and redirect to the current step.

**Do not add dependencies** beyond `opencv-contrib-python` and `numpy` in
week 1. Later weeks add `ultralytics`, `filterpy`, `scipy`, `websockets` —
not before.

**Do not restructure working code.** `geometry.py` is unit-tested with
exact round-trip results. If a change to it seems necessary, explain why
first.

**Do not silently change frame conventions.** See below.

**You cannot verify correctness.** You can confirm the code runs and the
numbers are self-consistent. Only the human with a tape measure can confirm
the numbers are *true*. Never tell them calibration succeeded based on
clean output alone — always point them back to the physical measurement.

---

## Frame conventions

These are load-bearing. Every mirrored-output bug traces back here.

```
World frame:   X right, Y forward, Z UP.  Floor is z = 0.  Right-handed.
Camera frame:  OpenCV convention -- x right, y DOWN, z FORWARD into scene.

solvePnP returns rvec/tvec mapping WORLD -> CAMERA:
    X_cam = R @ X_world + t

Camera position in world:      C = -R.T @ t
Ray direction camera -> world: d_world = R.T @ d_cam
```

`marker_corners_world()` in `calibrate_extrinsics.py` assumes markers lie
in a vertical plane facing **−Y**. If the user's markers face a different
direction, that function must be edited — the symptom is a mirrored or
inside-out solution.

---

## The core function

Everything depends on this. From `geometry.py`:

```python
s = (z - origin[2]) / d[2]
return origin + s * d
```

Given a pixel, build a ray from the camera through it, then find where that
ray crosses the horizontal plane at height `z`. For a person's feet, `z=0`
is the floor, so this converts a foot pixel into a floor position.

This is why the pipeline works with a single camera. It assumes the point
is on a known plane.

---

## Environment

```bash
source venv/bin/activate     # required in EVERY new terminal
pip install opencv-contrib-python numpy
```

`opencv-contrib-python`, **not** plain `opencv-python`. ArUco lives in
contrib. If `cv2.aruco` raises `AttributeError`, that's the cause.

Test camera: `cv2.VideoCapture(0)`. On Linux, `ls /dev/video*` lists
devices.

---

## Known gotchas — check these first when something is wrong

| Symptom | Cause |
|---|---|
| `cv2.aruco` missing | Wrong opencv package installed |
| Reprojection error > 3 px | `marker_size` in room.json doesn't match the printed square |
| Grid tilted or floating in verify | Marker positions in room.json are wrong |
| Left/right swapped | Marker facing direction in `marker_corners_world()` |
| Error grows with distance | Bad intrinsics — needs more chessboard views at image corners |
| Constant offset everywhere | Origin measured from a different corner than assumed |
| Nothing works in a new terminal | Forgot `source venv/bin/activate` |

**Printing:** markers must be printed at 100% scale with "fit to page" OFF,
then the printed black square measured with a ruler. That measured value
goes in `room.json` as `marker_size`, in metres. A 5% scale error becomes
30 cm of position error at 6 m.

---

## What is coming later

Do not implement these now. Listed only so present-day decisions do not
paint us into a corner.

- **Week 2** — YOLOv8-pose. Use **ankle keypoints** (indices 15, 16), not
  the bounding box centre, because feet are on the known floor plane. Add a
  fallback ladder: ankles → hips at 0.5 m → shoulders at 1.6 m, tagging
  which was used.
- **Week 3** — SORT. Constant-velocity Kalman (`filterpy`) plus Hungarian
  assignment (`scipy.optimize.linear_sum_assignment`). Posture from knee
  angle: standing 165–180°, sitting 80–110°.
- **Week 4** — iPhone streams frames to the laptop over a WebSocket. The
  laptop runs the **same** `solvePnP` on markers in that stream and returns
  the pose. Phone renders its own camera locally and fuses gyro at 60 Hz
  with laptop pose at ~5 Hz (complementary filter).
- **Week 5** — three.js rendering. `material.depthTest = false` plus high
  `renderOrder` is the entire see-through effect. Ray-cast against a
  hardcoded wall model: occluded → red wireframe, visible → cyan solid.
- **Week 6** — metrics, video, README.

Everything room-specific stays in `config/room.json`. New room means a new
JSON file, never new code.

---

## How to help

- Explain what code does when asked, line by line, in plain language. The
  user is learning, not just shipping.
- Prefer small, verifiable steps over large refactors.
- When a command fails, ask for the exact error text rather than guessing.
- Keep the user focused on the current step. This project's main risk is
  not technical difficulty — it is running out of the 6 weeks.
- If something is genuinely out of scope or a bad idea, say so plainly.
