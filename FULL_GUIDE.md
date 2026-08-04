# See-Through — the complete guide

Six weeks. Every week has four sections:

- **HAVE** — what must be on your desk before you start
- **DO** — the actual tasks
- **LEARN** — the ideas, explained plainly
- **EXPECT** — what appears on your screen, and the checkpoint

---

# BEFORE WEEK 1

## Shopping list

| Item | Why | $ |
|---|---|---|
| USB webcam, 1080p | Watches the room | 25 |
| Second USB webcam *(optional)* | Better accuracy, ID handoff demo | 25 |
| A4 paper + printer | Markers and chessboard | ~0 |
| Cardboard sheet, ~1m tall | The wall you see through | 0 |
| Tape measure | The most-used tool in this project | ~0 |
| Ruler | Measuring the printed markers | ~0 |
| Sticky tape | Putting markers up | ~0 |

**Already yours:** laptop, iPhone 16 Plus.

**Total: $25–50.** Buy the webcam today; nothing starts without it.

**Later, optional:** RPLidar C1 (~$72) in week 6, phone VR holder with
camera cutout (~$25) in week 6.

## Software

```bash
python3 -m venv venv
source venv/bin/activate
pip install opencv-contrib-python numpy
```

Later weeks add `ultralytics`, `filterpy`, `scipy`, `websockets`.

**`opencv-contrib-python`, not plain `opencv-python`.** The marker code
lives in contrib. This trips up almost everyone once.

## Knowledge you need on day one

- Running commands in a terminal
- Basic Python: variables, loops, functions, lists, dictionaries
- Editing a text file

That's it. Everything else you learn as you go.

---

# WEEK 1 — Geometry

**The foundation. Everything later inherits this week's accuracy.**

## HAVE

- Webcam, plugged in and confirmed working
- Printed markers (six), printed chessboard glued to card
- Tape measure and ruler
- A wall to put markers on
- The `seethrough` code

## DO

1. Print six markers at **100% scale**. Measure the printed black square
   with a ruler.
2. Print a chessboard, glue it to stiff card, measure one square.
3. Tape the markers to a wall — three at chest height, three at waist,
   spread wide.
4. Choose an origin (a floor corner). Write your axes on paper and stick it
   to the wall.
5. Measure each marker's centre position. Write them into `room.json`.
6. Run intrinsic calibration — 20+ chessboard views.
7. Run extrinsic calibration — point at markers, press space.
8. Run `verify` — click floor points, check with a tape measure.

Full literal steps are in `WEEK1_STEPS.md`.

## LEARN

**The pinhole camera model.** A camera turns 3D world points into 2D
pixels. If you know how it does that, you can run it backwards.

**Intrinsics — the shape of the lens.** Lenses bend light; straight lines
bow near the edges. The sensor's true centre isn't exactly the middle.
Calibration finds these numbers by showing the camera a pattern it already
knows the shape of. **Done once per camera, ever.**

**Extrinsics — where the camera is.** Six numbers: position (x, y, z) and
rotation (three angles). **Redone whenever the camera moves.**

**solvePnP.** Give it some 3D points you measured and where they appear in
the image, and it returns the camera's pose. This one function is used for
the fixed camera *and* later for the phone.

**Reprojection error — your quality score.** The software predicts where
each marker corner *should* appear using the pose it computed, then
compares to where it actually appeared. The average gap in pixels. Under
1px is good, over 3px means something is wrong.

**The ground-plane trick.** A photo is flat, so you can't tell small-and-
close from big-and-far. But if you know a point is **on the floor**, you
can draw a line from the lens through that pixel and see where it crosses
the floor. That's the position.

## EXPECT

**On screen:** an ugly window. Camera feed with a **green 1-metre grid**
drawn on your real floor. A second window showing a top-down map — green
lines, a dot for the camera, a cone for what it can see.

**When you click** a floor point, the terminal prints something like
`world (+0.512, +2.031, 0.000)`.

**It looks like nothing.** That's normal. This is plumbing.

### CHECKPOINT

Click floor points at 2m, 4m, 6m. Measure each with the tape measure.

**All three under 10cm.** Write the numbers down.

**Do not start week 2 until this passes.** A 2° error becomes 35cm at 10m,
and you will only discover it in week 5 when five things could be to blame.

---

# WEEK 2 — People become coordinates

## HAVE

- Week 1 passed, with numbers written down
- `pip install ultralytics`
- A friend, or space to walk around in yourself

## DO

1. Run YOLOv8-pose on the webcam. Watch it draw skeletons on people.
2. Learn the output: 17 keypoints, each with a confidence score.
3. Take the **ankle** keypoints (indices 15 and 16), average them.
4. Feed that pixel to `cam.pixel_to_plane(u, v, z=0)`.
5. Print the world coordinate. Stand still, watch it settle.
6. Combine into one script: camera window + top-down map with a moving dot.
7. Stand on marked floor spots, record the error at 2m, 4m, 6m.
8. Add the fallback ladder: if ankles are hidden, use hips at 0.5m; if
   those are hidden, use shoulders at 1.6m. Tag which method was used.

## LEARN

**What YOLO pose does.** A neural network that looks at an image and marks
17 points on each person: nose, eyes, ears, shoulders, elbows, wrists,
hips, knees, ankles. Each point comes with a confidence between 0 and 1.
**You are only using it. You are not training anything.**

**Why ankles, not the middle of the box.** The centre of a person floats in
mid-air — you have no idea how high it is, so you can't project it. The
feet touch the floor, and the floor's height you already know. That's the
whole reason this works with one camera.

**Confidence thresholds.** YOLO reports keypoints even when it's guessing.
Below about 0.4, throw them away. A guessed ankle produces a confidently
wrong position, which is worse than no position.

**Graceful degradation.** Sometimes the feet are hidden behind a desk. A
good system says "I'm less sure" instead of failing. That's what the
fallback ladder is for — and saying so in your README is the kind of thing
that reads as engineering.

## EXPECT

**On screen:** the camera window now has a green box around the person and
a stick figure drawn on them. A dot at their feet labelled `(3.21, 1.08)`.
On the map, a red dot that follows them around.

**The feeling:** this is the first week it feels like a system rather than
a script. Watching a dot glide across a map while a real person walks is
oddly satisfying.

**Speed:** roughly 10–20 fps on a laptop CPU with the small model. Fine.

### CHECKPOINT

Walk around. One dot follows you. Stand on a measured spot — the printed
coordinate matches within about 15cm.

---

# WEEK 3 — Tracking

**The week that makes this read as real perception work.**

## HAVE

- Week 2 working
- `pip install filterpy scipy`
- A friend, so two people can be in frame

## DO

1. Build a Kalman filter — state is `[x, y, vx, vy]`, constant velocity.
2. Build the assignment step — cost matrix of distances, solved with
   `scipy.optimize.linear_sum_assignment`.
3. Add the track lifecycle: tentative → confirmed after 3 hits → deleted
   after 5 misses.
4. Add posture detection from knee angles.
5. Test with two people crossing paths. Count ID switches.
6. Optional: second camera, and use `triangulate()` when both see someone.

## LEARN

**Kalman filter — predicting and correcting.** Instead of only storing
"where are they," you also store "how fast are they moving." Each frame:

- **Predict:** "moving right at 1 m/s, 0.1s passed, so they're 10cm
  further right."
- **Correct:** the real detection arrives, and you blend it with the
  prediction, weighted by how much you trust each.

Two payoffs: it **smooths jitter**, and it **survives gaps** — if YOLO
misses a frame, the prediction carries you through.

**Hungarian algorithm — who is who.** Frame 1: two people, IDs 1 and 2.
Frame 2: two detections. Which is which?

The naive answer — match each to its nearest — fails when people cross,
because both detections end up nearest the same track and the IDs swap.
The Hungarian algorithm solves the **whole assignment at once**, minimising
total distance. One line of scipy.

**Track lifecycle — ignoring noise.** YOLO occasionally hallucinates a
person for one frame. So a new detection stays **tentative** and invisible
until seen three frames running. And a track that vanishes isn't deleted
immediately — it coasts on prediction for five frames. This stops
flickering ghosts and stops you losing people who blink out momentarily.

**Posture from geometry.** Three points — hip, knee, ankle — form an angle.
Standing: nearly straight, 165–180°. Sitting: bent, 80–110°. Combine with
the velocity you already have from the Kalman filter:

| State | Test |
|---|---|
| WALKING | legs straight + speed > 0.4 m/s |
| STANDING | legs straight + speed < 0.2 m/s |
| SITTING | knee angle < 120° |
| CROUCHING | knee angle < 120° + hips low |

Smooth over about five frames or it flickers mid-stride.

## EXPECT

**On screen:** each person now has a number that stays with them. `ID 3`
walks across the room and stays `ID 3`. Two people cross paths and keep
their numbers. Labels read `ID 3 · WALKING` and change to `SITTING` when
they sit.

**The dot stops jittering** — that's the Kalman filter smoothing.

### CHECKPOINT

Two people cross paths, several minutes, near-zero ID switches. Occlude one
for a second — the track survives and picks them up again.

---

# WEEK 4 — Where is the phone

**The hardest week. Least visible progress. Push through it.**

## HAVE

- Week 3 working
- iPhone with a camera-streaming app (Iriun, or an IP camera app)
- `pip install websockets`
- Phone camera calibrated with the chessboard, same as the webcam

## DO

1. Get the phone's camera stream into OpenCV. Confirm 15+ fps.
2. Calibrate the phone camera's intrinsics — same chessboard script.
   **Lock it to one lens.** Switching between wide and ultrawide changes
   the numbers and silently breaks everything.
3. Run `solvePnP` on markers in the phone's stream. Print the position.
   Walk around and watch it track.
4. Set up a WebSocket server on the laptop and a web page on the phone.
   Send the pose at about 10Hz.
5. Build a basic three.js scene on the phone: its own camera as the
   background, a cube at world origin, camera driven by the received pose.
6. Add gyro. Use `DeviceMotion` for fast rotation at 60Hz, the laptop's
   pose for absolute correction at ~5Hz.

## LEARN

**Why the work is split.** Head rotation is fast, walking is slow. So the
**fast** channel (gyro) runs locally on the phone with no delay, and the
**slow** channel (absolute position) can afford a network round trip.

**Complementary filter.** Two sensors with opposite flaws:

- Gyro: fast and smooth, but **drifts** — after a minute it thinks you've
  turned 10° when you haven't.
- Markers: perfectly accurate, never drift, but **slow** and only work when
  a marker is in view.

Combine them: use the gyro for motion, and continuously nudge it back
toward the marker answer. Roughly
`angle = 0.98 × (angle + gyro×dt) + 0.02 × marker_angle`.

**WebSocket.** A phone line that stays open. Normal web requests are
letters — send one, get one back, done. A WebSocket stays connected so the
laptop can push updates continuously without being asked each time.

**iOS gotchas — write these down:**
- HTTPS is required. Plain `http://` silently refuses. Use ngrok.
- `playsinline` and `muted` on the video element, or iOS takes it
  fullscreen and your overlay disappears.
- `DeviceMotionEvent.requestPermission()` must be called **inside a tap
  handler**. On page load it throws.
- Turn off Low Power Mode. It halves your framerate for no visible reason.
- Handle `visibilitychange` — Safari kills the camera when backgrounded.

## EXPECT

**On screen:** a plain three.js scene. Your phone's camera view with a
grey cube sitting on your table.

**The feeling:** frustrating. Nothing looks impressive and you'll spend
most of the week on sign errors and coordinate frames. That's normal —
OpenCV uses z-forward y-down, three.js uses y-up. You will lose a day to
this. Everyone does.

### CHECKPOINT

Put the cube on your table. **Walk around the table.** The cube stays
planted, like a real object.

If it swims, slides, or drifts away — **stop.** Week 5 cannot work on top
of a bad pose, and you won't be able to tell what's wrong once skeletons
are involved.

---

# WEEK 5 — See through the wall

**The payoff week.**

## HAVE

- Week 4 checkpoint passed — the cube doesn't swim
- Cardboard sheet propped up as a wall
- A friend to walk behind it
- Your room's walls measured

## DO

1. Replace the cube with skeletons, drawn from the tracked keypoints at
   their world positions.
2. Set `material.depthTest = false` and a high `renderOrder`.
3. Measure your room's walls, write the planes into a JSON file.
4. Ray-cast from the phone to each person. Does the line cross a wall?
   - Yes → **red wireframe**
   - No → **cyan solid**
5. Add the HUD: compass strip, range readout, posture label, sensor health
   panel.
6. Add staleness: fresh = solid; 1–3s old = dimmed with an age counter; out
   of coverage = frozen dashed ghost; after 15s = fade out.
7. Full dress rehearsal with the cardboard.

## LEARN

**depthTest = false — the entire x-ray trick.** Normally graphics hide
things that are behind other things. That's the depth test. Turning it off
means "draw this on top, always."

The skeleton really is at its true position **behind** the wall. You're
just refusing to hide it. That is the whole effect, and it's one line.

**Ray-casting for occlusion.** How you decide red or cyan. Draw a line from
your phone to the person. Does it cross a wall plane? If yes, they're
hidden and the marker is inferred (red). If no, you can see them yourself
(cyan).

**Why staleness matters.** A system that shows three-second-old data as if
it were live is lying to you. Fading and labelling old information is
honest, and it's what separates a real system from a demo.

## EXPECT

**On screen:** your actual wall, live — and standing on it, a **red
wireframe figure**, person-height, 17 joints connected by lines. Small text
above: `PERSON · WALKING · 4.2m · 87%`. A compass across the top. A radar
circle bottom-left. `CAM_A ● live · 240ms` in the corner.

They step left, it steps left. They sit, it sits and the label changes.

**Then they walk out through the door** — and the figure snaps to **cyan
solid** and lands on their real body, which you can now see with your own
eyes.

**The feeling:** the first time you see a skeleton through cardboard you
will make an involuntary noise.

### CHECKPOINT

Person behind cardboard → red skeleton, correct spot, moves with them.
Person steps out → cyan, lined up with their real body.

---

# WEEK 6 — Measure, record, ship

## HAVE

- A working demo
- A friend to help film
- Time. Do not schedule anything else.

## DO

**Day 1 — RECORD. Before polishing anything.**

Multiple takes. Three angles: the phone screen, the laptop map, and a wide
shot showing the room and the cardboard. The money shot is red → cyan as
they step out.

**Day 2 — Measure everything:**
- Calibration: reprojection error, world error at 2/4/6m
- Tracking: ID switches per minute, detection rate, MOTA if you annotate a
  short clip
- Latency: p50 and p99, end to end
- Phone pose: jitter standing still, drift over 60s

**Day 3 — README:** architecture diagram, metrics table, honest limitations.

**Day 4 — Writeup:** the worst bug you hit and how you found it.
Interviewers probe for this; it separates people who built something from
people who followed a tutorial.

**Days 5–7 — Buffer.** You will need it.

## LEARN

**Why numbers matter more than features.** "MOTA 0.71, 3 ID switches over
4 minutes, p99 latency 62ms" reads completely differently from "it works
well." It says you tested rather than assumed. Perception teams live on
evaluation numbers.

**Why naming limitations helps you.** "Ground-plane assumption fails on
stairs; stereo depth would fix it" shows you know exactly where your
system's edges are. That's a senior trait and it's very visible at your
level.

## EXPECT

**Realistic numbers:**

| Metric | Expect |
|---|---|
| Calibration reprojection | 0.4–0.8 px |
| World position error | 8–15 cm |
| Latency, end to end | 150–250 ms |
| People tracked at once | 1–3 |
| Working range | one room, 3–6 m |

**It will look worse than the Anduril screenshot.** Theirs has thermal
imaging, purpose-built optics, and a team of engineers. Yours is a slightly
jittery skeleton on a phone screen.

**That is a success.** You reproduced the mechanism for $50, and anyone
technical who watches understands exactly what you did.

---

# THE RULES

**1. Three checkpoints gate everything:**
- Week 1: under 10cm against a tape measure
- Week 3: IDs stable through a crossing
- Week 4: the cube doesn't swim

Fail one, stop. Do not build on it.

**2. Film something every week.** Even the ugly grid in week 1. If week 5
goes wrong you still have five weeks of visible progress and an honest
writeup — which reads better than you'd think.

**3. Cut in this order if you fall behind:**
second camera → full skeletons → staleness → phone display (use the laptop
screen) → live demo (use a recording).

**4. A finished simple version beats an unfinished ambitious one**, by a
very wide margin.

---

# START HERE

Buy the webcam. Print the markers at 100% scale. Measure one with a ruler.

Then open `WEEK1_STEPS.md` and follow it from step 0.
