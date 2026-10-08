# XRay — status and next steps

Read this first, then `CLAUDE.md` and `GOTCHAS.md` in the project folder.

**Date:** 8 Oct 2026 · **Week 1 of 6, ~70% done** · **Target: finish October**

---

## The project

Occlusion-aware AR. A fixed webcam in a dorm room detects a person and
reports their **world coordinates**. An iPhone in the hallway, which knows
its own world coordinates from printed ArUco markers, renders a wireframe
skeleton at that position with depth testing disabled — so the figure
appears to stand on the wall.

Nothing sees through the wall. The effect comes from two devices sharing one
coordinate frame, plus a rendering trick.

---

## Environment — locked, do not change

| | |
|---|---|
| OS | Windows, PowerShell, VS Code. Use `python`, not `python3` |
| Project path | `C:\dev\oreleye` (moved off OneDrive deliberately) |
| Camera | Logitech Brio 100, USB, fixed focus |
| **Device index** | **1** (0 is the laptop's built-in) |
| **Backend** | **`cv2.CAP_DSHOW`** |
| **Resolution** | **640×480** |
| Deps | `opencv-contrib-python`, `numpy` |

### Why these exact settings

A 24-combination probe of backend × codec × resolution found:

- **MSMF** gave 30 fps at 1280×720 in the probe, but **hangs forever** when
  the actual scripts open the camera. Unusable.
- **DSHOW** at 1280×720 gives **5 fps** — it falls back to uncompressed
  YUY2, which exceeds USB bandwidth at that size.
- **DSHOW at 640×480 gives 30 fps.** That is the working combination.

**Intrinsics are resolution-dependent.** Calibrating at 640×480 and running
at 720p makes the focal length wrong by a factor of two. 640×480 is now the
project's resolution everywhere, permanently.

---

## Done

**Markers** — 5 printed, IDs 0–4, `DICT_5X5_100`, one per A4 sheet with wide
white margins. Verified detecting live, including at steep angles and long
range.

**Marker size: 174 mm.** Asked the generator for 200 mm; the print came out
174. That is a 13% scale error which would have put every position ~45 cm
out at 3.5 m. Caught by measuring the printed black square with a ruler.
`marker_size` in the config must be `0.174`.

**Intrinsic calibration — RMS 0.574 px**, worst single view 1.494 px, 20+
views, saved to `calib/cam_a.json`. Chessboard was the OpenCV 9×6
inner-corner PDF at `--square-mm 28.5`.

*(Note: the assumed chessboard square size does not affect intrinsics — it
only scales per-view board distance, which calibration discards. Verified
with synthetic data. The 174 mm marker size, by contrast, is load-bearing:
it sets real-world scale.)*

**One bug fixed:** `calibrate_intrinsics.py` crashed after a successful
calibration, in the per-view error loop. `cv2.norm` rejected mismatched
array types under OpenCV 5.0. Replaced with a numpy equivalent:

```python
errs = []
for i in range(len(obj_pts)):
    proj, _ = cv2.projectPoints(obj_pts[i], rvecs[i], tvecs[i], K, dist)
    obs = img_pts[i].reshape(-1, 2)
    pred = proj.reshape(-1, 2)
    errs.append(float(np.mean(np.linalg.norm(pred - obs, axis=1))))
```

---

## Scope — settled, don't reopen

- **One camera.** No triangulation. `triangulate()` exists in `geometry.py`
  and is unit-tested but will not be exercised.
- **Standing and walking subjects only** for the demo. Seated people
  degrade to the hip-height fallback; that goes in the README as a stated
  limitation, not a demo shot.
- **Markers stay.** They are the world-frame reference — the role GNSS fills
  in fielded systems. At room scale the accuracy requirement (~10 cm) is
  tighter than GPS provides.
- No ROS, no robot, no SLAM, no lidar.

### Room layout

- Camera inside the dorm room, on a chair or desk
- **Markers on the face of the bathroom block** — the surface pointing back
  toward the doorway. Parallel to the door wall, so **Y is constant** for
  all five and X varies.
- Those markers face −Y, which matches what `marker_corners_world()`
  assumes. No code change needed, provided Y is defined as "into the room."
- Origin at the door frame's floor corner
- Hallway markers (IDs **5–8**, never reuse 0–4) come in week 4

---

## NEXT — finish week 1

### 1. Fix two files

`calibrate_extrinsics.py` and `verify.py` still open the camera at 1280×720.
Both need:

```python
cap = cv2.VideoCapture(src, cv2.CAP_DSHOW)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
```

Do this before going to the room.

### 2. Check the camera's view

```powershell
python view.py 1 --small
```

Confirm: the bathroom-block face is in frame with space for five markers
spread out, and **feet are visible everywhere someone might stand.** The
whole method projects ankles to the floor — furniture hiding the lower half
of the room means dead zone.

Also re-test marker detection at 640×480 from 4–5 m. Earlier range testing
was at 720p; half the pixels means roughly half the range.

### 3. Tape the markers

3 at ~1.4 m, 2 at ~0.7 m, staggered horizontally so the bottom row is not
directly under the top. Spread as wide as the face allows — clustered
markers give a mathematically weak pose where small pixel errors become
large position errors.

Mark each marker's centre in pen on the white margin before taping. Saves
arithmetic and prevents a mistyped coordinate.

### 4. Origin and axes

Tape the door frame's floor corner, write `ORIGIN` on it.

Write the axes on paper and tape it to the wall:

```
Origin: door frame, floor corner
X = right along the wall
Y = into the room
Z = up
```

Not in your head. Every sign error this week gets resolved by looking at it.

### 5. Measure

Three numbers per marker, to the **centre of the black square**, in metres:

- **Y once** — perpendicular from origin to that face. Same for all five.
- **X each** — sideways from the origin line. Note: X = 0 is the
  perpendicular projection of the origin onto that face, **not** the
  nearest corner. Mark that spot with tape first.
- **Z each** — floor to centre.

Centimetre accuracy.

### 6. Write `config/room.json`

```json
{
  "name": "dorm",
  "marker_size": 0.174,
  "markers": {
    "0": [-1.40, 1.90, 1.42],
    "1": [-0.90, 1.90, 1.42],
    "2": [-0.40, 1.90, 1.42],
    "3": [-1.15, 1.90, 0.72],
    "4": [-0.65, 1.90, 0.72]
  },
  "walls": [],
  "cameras": {}
}
```

Real measured numbers, not these.

### 7. Extrinsic calibration

```powershell
python -m seethrough.calibrate_extrinsics --device 1 --name cam_a --intrinsics calib/cam_a.json --room config/room.json
```

Aim so **3 or more** markers are visible, press **SPACE once**, press **Q**.
This is one capture, not 20 — that was intrinsics.

Sanity-check the printed camera position against where it physically is.
Reprojection under 3 px.

### 8. THE GATE

```powershell
python -m seethrough.verify --device 1 --name cam_a --room config/room.json
```

**First, look at the green 1 m grid** drawn on the floor in the camera view.
Tilted, floating, or skewed means the pose is wrong — stop there, measuring
is pointless.

Then click floor points at ~2 m and ~4 m and check each with a tape measure.

**Pass: under 10 cm. Do not start week 2 otherwise.** A 2° pose error is
35 cm at 10 m — invisible now, obvious in week 5 when five subsystems could
be to blame.

### 9. Record

```
Intrinsic RMS:           0.574 px   ✓
Worst single view:       1.494 px   ✓
Extrinsic reprojection:  ___ px
World error @ 2m:        ___ cm
World error @ 4m:        ___ cm
```

Press `s` in verify to save screenshots. **Film 20 seconds** of the grid and
the top-down map — it looks like nothing now, but in week 6 it is the
"here's the foundation" shot and cannot be recreated.

---

## After week 1

**Week 2 — people become coordinates.** YOLOv8-pose (`ultralytics`). Take
the **ankle keypoints** (indices 15, 16), not the bounding box centre — feet
are on the known floor plane; the box centre floats at unknown height. Feed
to `cam.pixel_to_plane(u, v, z=0)`.

Build the **fallback ladder** from the start, since there is only one
camera: ankles → z=0 · knees → 0.45 · hips → 0.95 · shoulders → 1.40 · head
→ 1.65. Tag each estimate with the tier used and widen its uncertainty ring.
Reject keypoints below ~0.4 confidence.

**Week 3 — SORT tracking.** Constant-velocity Kalman (`filterpy`) +
Hungarian assignment (`scipy.optimize.linear_sum_assignment`). Lifecycle:
tentative → confirmed after 3 hits → deleted after 5 misses. Posture from
knee angle (standing 165–180°, sitting 80–110°) combined with Kalman
velocity.

**Week 4 — phone pose.** iPhone streams frames to the laptop; the laptop
runs the **same** `solvePnP` and returns the pose over WebSocket. Phone
renders its own camera locally (background never lags) and fuses gyro at
60 Hz with laptop pose at ~5 Hz. Hallway markers go up here.

iOS gotchas: HTTPS required (use ngrok) · `playsinline` and `muted` on the
video element · `DeviceMotionEvent.requestPermission()` must be inside a tap
handler · Low Power Mode off · handle `visibilitychange`.

Checkpoint: a virtual cube stays planted on a table while you walk around
it. If it swims, week 5 cannot work.

**Week 5 — the render.** three.js, `material.depthTest = false` + high
`renderOrder` — that single line is the entire see-through effect. Ray-cast
against a hardcoded wall model (measure the room, write planes into JSON):
occluded → red wireframe, visible → cyan solid. Plus compass, radar,
staleness fading, sensor health panel.

**Week 6 — measure, record, write.** Record on day 1, not day 7.

---

## Rules

1. **Three checkpoints gate everything:** week 1 under 10 cm · week 3 IDs
   survive a crossing · week 4 the cube doesn't swim. Fail one, stop.
2. **Film something every week**, even the ugly grid.
3. **Cut order if behind:** staleness → full skeletons → phone display (use
   laptop + mouse-look) → live demo (use a recording).
4. A finished simple version beats an unfinished ambitious one.

---

## For Claude Code

- Explain commands and code in plain language — I'm new to computer vision.
- Small verifiable steps. Show output, confirm, continue.
- Ask for exact error text rather than guessing.
- **Do not build ahead** of the current week.
- **Do not modify `seethrough/geometry.py`** — it is unit-tested with exact
  round-trip results.
- **You cannot verify accuracy.** You can confirm code runs and numbers are
  self-consistent. Only the tape measure confirms they are *true*. A
  mistyped marker position produces perfectly clean output and 40 cm of
  error. Never report calibration as successful based on clean output alone.

---

## CV entry — current honest version

```
XRay — Occlusion-Aware AR Localization | Python, OpenCV, NumPy, ArUco
Jul 2026 – Present
· Built a world-space camera-geometry pipeline implementing lens
  correction, coordinate transforms, and monocular ground-plane projection.
· Achieved 0.57-pixel calibration RMS across 20+ views and implemented
  ArUco/solvePnP camera localization with reprojection-error diagnostics.
```

Already cut: "multi-view triangulation" (one camera, never exercised) and
the HTTP/RTSP bullet (stream never worked; USB was used instead).

**Add after the gate passes:** world-position accuracy in cm, as bullet one.
That is the number that says the system works — 0.57 px RMS is an
intermediate diagnostic that only means something to someone who has done
calibration.

Earn back later: SORT tracking (week 3), world-locked rendering with
end-to-end latency (week 5), and the RTSP bullet if the phone stream works
in week 4.
