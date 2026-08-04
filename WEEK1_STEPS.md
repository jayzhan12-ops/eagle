# Week 1 — every step, literally

Follow in order. Do not skip. Each step says what to do, what you should
see, and what to do when it goes wrong.

---

## STEP 0 — Install

Open a terminal.

```bash
cd ~
mkdir -p projects && cd projects
# put the seethrough folder here, then:
cd seethrough

python3 -m venv venv
source venv/bin/activate
pip install opencv-contrib-python numpy
```

**You should see:** `Successfully installed opencv-contrib-python numpy`

Check it worked:

```bash
python3 -c "import cv2; print(cv2.__version__); print(cv2.aruco)"
```

**You should see:** a version number, then something like
`<module 'cv2.aruco'>`

**If `cv2.aruco` fails:** you installed the wrong package.
```bash
pip uninstall opencv-python opencv-contrib-python -y
pip install opencv-contrib-python
```

**Every new terminal from now on needs `source venv/bin/activate` first.**

Check your webcam:

```bash
python3 -c "
import cv2
c = cv2.VideoCapture(0)
print('opened:', c.isOpened())
ok, f = c.read()
print('frame:', f.shape if ok else 'FAILED')
c.release()"
```

**You should see:** `opened: True` and `frame: (720, 1280, 3)` or similar.
If it says False, try device `1` or `2`. On Linux, `ls /dev/video*` lists them.

---

## STEP 1 — Print the markers

```bash
python3 -m seethrough.make_markers --count 6 --size-mm 150
```

**You should see:** `6 markers -> markers/` and six PNG files.

Open them and print all six.

**In the print dialogue — this matters more than anything else today:**
- Scale: **100%** or "Actual size"
- **Turn OFF** "Fit to page", "Shrink to fit", "Scale to fit"
- Paper: A4 or Letter, one marker per page

**Now take a ruler and measure the black square** on a printed page.
Measure the black part only, not the white border.

Write the number down. It will probably be 148mm or 151mm, not exactly 150.

**If you skip this:** every distance in your project is wrong by that
percentage. A 5% error is 30cm at 6 metres.

---

## STEP 2 — Print the chessboard

Search "opencv chessboard 9x6 pdf" and print one, or make one in a
spreadsheet: 10 columns × 7 rows of alternating black/white squares.

> **Why 10×7 for a "9×6" board:** the code counts *inner corners* — the
> points where four squares meet. A 10×7 grid of squares has 9×6 inner
> corners.

Print at 100% scale. **Measure one square with a ruler** — probably around
25mm. Write it down.

**Glue it to stiff cardboard.** A bent board gives a bad calibration and
you will not be able to tell from looking at it.

---

## STEP 3 — Put the markers on the wall

Pick the wall you will point the phone at.

Tape up **all six**:
- Three at roughly chest height (~1.4m)
- Three at roughly waist height (~0.7m)
- Spread horizontally as wide as the wall allows

**Rules:**
- Flat against the wall. No curling corners.
- Do not cover the white border — detection needs it.
- Spread beats quantity. Six markers clustered in one spot are worse than
  four in the corners.

---

## STEP 4 — Define your origin

You are inventing a coordinate system. Every measurement from now on is
relative to the point you choose here.

**Pick a floor corner of the room.** Mark it with tape. Write on the tape
`ORIGIN`.

**Decide your axes and write them on paper:**
```
Origin: floor corner nearest the door
X = right,  along the wall
Y = forward, away from that wall
Z = up
```

Stick that paper on the wall. You will refer to it constantly, and every
sign error you make this week will be resolved by looking at it.

---

## STEP 5 — Measure the markers

For each marker you need the **centre** of the black square, as three
numbers in **metres**.

Take a tape measure. For each marker:

1. **X** — horizontal distance from the origin corner, along the wall
2. **Y** — perpendicular distance out from the origin
3. **Z** — height from the floor to the marker's centre

**Worked example.** Origin is the left floor corner. The marker wall is
3.00m away from the origin, straight ahead. Marker 0 is 1.50m along that
wall to the *left* of where the origin's X=0 line meets it, and its centre
is 1.40m off the floor:

```
Marker 0 -> x = -1.50, y = 3.00, z = 1.40
```

All six markers on the same wall share the same **y**.

**Be accurate to a centimetre.** Errors here propagate into every camera
pose you compute.

---

## STEP 6 — Write room.json

```bash
nano config/room.json
```

```json
{
  "name": "my_room",
  "marker_size": 0.148,
  "markers": {
    "0": [-1.50, 3.00, 1.40],
    "1": [ 0.00, 3.00, 1.40],
    "2": [ 1.50, 3.00, 1.40],
    "3": [-1.50, 3.00, 0.70],
    "4": [ 0.00, 3.00, 0.70],
    "5": [ 1.50, 3.00, 0.70]
  },
  "walls": [],
  "cameras": {}
}
```

- `marker_size` is **your ruler measurement, in metres**. 148mm → `0.148`.
- Marker keys must match the ID printed on each page.
- Save with `Ctrl+O`, exit with `Ctrl+X`.

---

## STEP 7 — Check the marker facing direction

**This is the step people skip and then lose a day to.**

Open `seethrough/calibrate_extrinsics.py` and find
`marker_corners_world()`. It assumes markers sit in a vertical plane facing
**−Y** — i.e. you look at them while walking in the **+Y** direction.

Check against your paper from step 4: *standing at the origin, facing the
marker wall, am I facing +Y?*

- **Yes** → change nothing.
- **No** → the solution will come out mirrored. Easiest fix is to redefine
  your axes in step 4 so that you are.

**Symptom if wrong:** the camera position comes out on the wrong side of
the room, or left and right are swapped.

---

## STEP 8 — Intrinsic calibration

```bash
python3 -m seethrough.calibrate_intrinsics \
  --device 0 --cols 9 --rows 6 --square-mm 25 \
  --out calib/cam_a.json
```

Use **your measured square size** for `--square-mm`.

**You should see:** a window with your camera feed and `captured: 0`.

**Now the procedure.** Hold the chessboard up. When the software finds it,
coloured lines appear over the corners and the counter turns green.
Press **SPACE** to capture.

Capture **at least 20 views**, varying every time:

| Vary | How |
|---|---|
| Distance | Close (fills frame), medium, far |
| Angle | Tilt left, right, up, down, ~30–45° |
| **Position** | **Board in each corner of the image** |
| Rotation | Turn the board 45°, 90° |

**The corners matter most.** Lens distortion is strongest at the image
edges, and a calibration built only from centred views will look fine and
be wrong. Aim for at least 8 of your 20 views with the board touching an
edge or corner.

Press **Q** when done.

**You should see:**
```
RMS reprojection error: 0.3412 px
worst single view: 0.512 px
saved -> calib/cam_a.json
```

| RMS | Verdict |
|---|---|
| < 0.5 | Excellent, continue |
| 0.5–1.0 | Fine, continue |
| 1.0–1.5 | Usable, but redo if you have time |
| > 1.5 | **Redo.** |

**If it's bad:**
- Board bent → glue it to something rigid
- Camera not focused → most webcams autofocus, hold still and let it settle
- Wrong `--square-mm` → measure again
- Too few corner views → recapture with more edge coverage

---

## STEP 9 — Extrinsic calibration

Put the camera where it will live. Aim it into the room so it sees the
markers **and** the floor area where people will walk.

```bash
python3 -m seethrough.calibrate_extrinsics \
  --device 0 --name cam_a \
  --intrinsics calib/cam_a.json \
  --room config/room.json
```

**You should see:** the camera feed with green outlines and ID numbers on
detected markers, and text reading `known markers visible: 4 [0, 1, 3, 4]`.

Wait until it's green with **3 or more**. Press **SPACE**.

**You should see:**
```
  camera position : [-0.42  -1.85   1.62] m
  looking towards : [ 0.12   0.94  -0.31]
  reprojection    : 1.34 px  (16/16 inliers)
  saved -> config/room.json
```

**Sanity-check the position by hand.** Is the camera really about 0.4m left
of your origin line, 1.85m back from the marker wall, 1.62m off the floor?
Measure it. If it says the camera is 8 metres away, something is wrong.

| Reprojection | Verdict |
|---|---|
| < 1.5 px | Excellent |
| 1.5–3 px | Fine |
| > 3 px | Wrong `marker_size`, or wrong marker positions |

Press **Q** to exit.

---

## STEP 10 — THE GATE

```bash
python3 -m seethrough.verify \
  --device 0 --name cam_a --room config/room.json
```

Two windows open: the camera view and the top-down map.

### 10a — Look at the grid first

A **green 1-metre grid** is drawn on the floor in the camera view.

**Does it line up with your real floor?** Follow one grid line — is it
parallel to your wall? Does a grid intersection fall where you'd expect?

- Grid looks reasonable → continue.
- Grid tilted, floating in the air, or wildly skewed → **stop.** Your pose
  is wrong. Go to the failure table below.

This ten-second check catches most problems before you get out the tape
measure.

### 10b — Click and measure

Click a point on the floor in the camera window. The terminal prints:

```
  pixel ( 640, 520)  ->  world (+0.512, +2.031, 0.000)   2.09 m from cam_a
```

That means: the point you clicked is **0.512m right of origin, 2.031m
forward.**

Now **walk over with the tape measure** and check it.

Do this for **three points**, roughly 2m, 4m, and 6m from the camera.
Record the error for each.

### 10c — The verdict

**PASS: all three errors under 10cm.** Write the numbers down. Week 1 is
done.

**FAIL: any error over 10cm.** Diagnose:

| Symptom | Cause | Fix |
|---|---|---|
| Grid tilted or floating | Marker positions wrong in `room.json` | Re-measure |
| Error grows with distance | Bad intrinsics | Redo step 8, more corner views |
| Left/right swapped | Marker facing direction | Step 7 |
| Same offset everywhere | Origin measured from wrong corner | Re-check step 4 |
| Reprojection was > 3 px | `marker_size` wrong | Re-measure the print |
| Error only when far | Too few markers, or clustered | Spread them wider |

---

## STEP 11 — Record and film

Write these three numbers somewhere permanent. They are the first row of
your evaluation table.

```
Intrinsic RMS:        _____ px
Extrinsic reprojection: _____ px
World error @ 2m:     _____ cm
World error @ 4m:     _____ cm
World error @ 6m:     _____ cm
```

Then:

```bash
# in verify, press 's'
```

That saves `verify_camera.png` and `verify_map.png`.

**Film 20 seconds** of the grid on the floor and the top-down map. It looks
like nothing now. In week 6 it is the "here is the foundation" shot in your
video, and you will not be able to recreate it once the code has moved on.

---

## Time estimate

| Steps | Time |
|---|---|
| 0–2 (install, print) | 1 hour |
| 3–7 (place, measure, config) | 2 hours |
| 8 (intrinsics) | 1 hour if it works |
| 9 (extrinsics) | 20 minutes if it works |
| 10 (gate) | 30 minutes |

**About half a day if nothing goes wrong.** Budget two days, because
something will.

---

## The rule

**Do not start week 2 until step 10 passes.**

A 2° pose error becomes 35cm at 10m. You will not notice it now. You will
notice it in week 5, when the skeleton lands in the wrong place and you
have five subsystems to blame.

Fix it here, where there is exactly one thing that can be wrong.
