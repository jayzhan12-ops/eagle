# GOTCHAS — check here first when something breaks

Ordered by how likely they are to hit you.

---

## 1. Setup

**Wrong OpenCV package.** `pip install opencv-contrib-python`, not
`opencv-python`. ArUco only exists in contrib.
→ *Symptom:* `AttributeError: module 'cv2' has no attribute 'aruco'`
→ *Fix:* uninstall both, reinstall contrib.

**Both installed at once.** They conflict. Pick one.
```powershell
pip uninstall opencv-python opencv-contrib-python -y
pip install opencv-contrib-python
```

**`python3` vs `python`.** On Windows it's `python`. On Linux it's
`python3`. Don't copy commands blindly between them.

**Project on OneDrive.** OneDrive syncs files mid-write and locks them.
→ *Symptom:* random permission errors that look like code bugs
→ *Fix:* keep the project at `C:\dev\qyraneye` or similar. Never in
OneDrive, Dropbox, or Google Drive.

**Missing `seethrough` folder.** If `import seethrough.geometry` fails, the
package didn't extract. Check `dir seethrough` shows `geometry.py` and
friends. The inner folder must keep the name `seethrough` — that's the
module name.

---

## 2. Camera

**Only one program can hold a camera.** Windows grants exclusive access.
→ *Symptom:* `cap.isOpened()` is False, or frames are all black
→ *Fix:* close Zoom, Teams, Discord, Skype, Windows Camera app. Check the
system tray.

**Never quit with Ctrl+C.** It skips `cap.release()` and the camera stays
locked until the process fully dies.
→ *Always press `q`* in the window. If you do get stuck, close the terminal
entirely or kill python in Task Manager.

**`imshow` without `waitKey` shows nothing.** `waitKey` is what triggers the
redraw.
```python
cv2.imshow('win', frame)
cv2.waitKey(1)          # <- required, not optional
```

**Cameras default to 640x480.** You must ask for more:
```python
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
```
And it's a *request*. Read back with `cap.get()` to see what you actually
got.

**Use `cv2.CAP_DSHOW` on Windows.** Without it, opening a camera often
stalls for 5+ seconds.
```python
cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)
```

**Camera index changes.** Unplug and replug and it may shift. Re-check
before assuming.

**Don't move the camera after calibrating extrinsics.** A 1cm bump makes
every position wrong, and nothing warns you. Mount it solidly and note the
date you calibrated.

---

## 3. Printing and measuring

**"Fit to page" is the single most expensive mistake in this project.**
Turn it OFF. Set scale to 100%.
→ A 2% print error is 12cm of position error at 6m.

**Always measure the printed result.** Never trust the number you typed into
the generator. My print came out 204mm when I asked for 200mm.

**Measure the black square only.** Outer edge of the black border to outer
edge. Not the paper, not the white margin. The white area is just whatever
was left of the page and means nothing.

**Metres in the config, millimetres on the ruler.**
204mm → `"marker_size": 0.204`
Getting this wrong by a factor of 1000 produces spectacular nonsense.

**Quiet zone.** Markers need at least one cell width of white all around, or
detection fails. Don't trim the paper to the black edge.

**Glue the chessboard to something rigid.** Foam board or a clipboard. NOT
corrugated cardboard — it warps with humidity and you cannot see it. A 2mm
bow silently ruins your calibration.

**Write the ID on each marker sheet in pen.** You will not enjoy decoding
binary patterns while up a ladder.

---

## 4. Calibration

**Intrinsics and extrinsics are different things.** Don't mix them up.
- Intrinsics = lens shape. Chessboard. **Once per camera, ever.**
- Extrinsics = camera position. Wall markers. **Every time it moves.**

**9x6 means inner corners, not squares.** A "9x6" board is a 10x7 grid of
squares. Inner corners are where four squares meet.

**Get the board into the image CORNERS.** Distortion is strongest at the
edges. A calibration from 20 centred views looks fine and is wrong. Aim for
8+ views with the board touching an edge.

**Check the worst single view, not just RMS.** If RMS is 0.4 but one view is
3.0, that view was blurry or misdetected and it's dragging the model.
Recapture.

**Hold still when capturing.** Motion blur destroys corner precision.

**Don't recalibrate intrinsics after extrinsics.** The extrinsics depend on
the intrinsics. Change one, redo the other.

---

## 5. Coordinate frames

**This is where the subtle bugs live.**

**Write your axes on paper and tape it to the wall.**
```
Origin: floor corner by the door
X = along the wall, right
Y = into the kitchen
Z = up
```
Every sign error gets resolved by looking at that paper instead of guessing.

**Marker facing direction.** `marker_corners_world()` in
`calibrate_extrinsics.py` assumes markers face −Y.
→ *Symptom:* left/right swapped, or the camera solves to the wrong side of
the room
→ *Fix:* edit that function, or redefine your axes so it holds.

**Origin must be reachable from both rooms.** Put it at the doorframe. If
it's in the middle of the kitchen you cannot measure the corridor markers
from it.

**All markers on one wall share the same Y.** Good sanity check on your
numbers.

**OpenCV is z-forward, y-down. three.js is y-up.** You will lose a day to
this in week 4. Everyone does. It's not a bug in the code.

---

## 6. Working with Claude Code

**It cannot verify accuracy.** It can confirm the code ran and the numbers
are self-consistent. It cannot know they are *true*. A mistyped marker
position gives clean output and 40cm of error.
→ *Only the tape measure decides.*

**It will build ahead if you let it.** Say "week 1 only, do not implement
detection or tracking."

**Give it the exact error text.** Not "it didn't work." The specific wording
is the diagnosis.

**Don't let it refactor `geometry.py`.** It's unit-tested with exact
round-trip results. Changes there break the foundation silently.

**Long-running agent = usually a loop.** If it's grinding, stop it, ask what
it's doing, and give it one narrow task instead.

---

## 7. Project discipline

**Do not pass a checkpoint you failed.**
- Week 1: under 10cm vs tape measure
- Week 3: IDs survive a crossing
- Week 4: the cube doesn't swim

A 2° error becomes 35cm at 10m. You will not notice now. You will notice in
week 5 with five subsystems to blame.

**Commit when something works**, not when it's finished.
```powershell
git commit -am "intrinsics calibrated, RMS 0.31"
```

**Film something every week**, even the ugly grid. If week 5 goes wrong you
still have visible progress and an honest writeup.

**Write down every number you measure.** Marker positions, print size, RMS,
reprojection error, world error. These become your README's metrics table,
and that table is where half the CV value lives.

**Room-specific data goes in `config/room.json`, never hardcoded.** New room
should mean a new JSON file, not new code.

---

## Quick triage

| Symptom | Look at |
|---|---|
| `cv2.aruco` missing | §1 wrong package |
| Camera won't open | §2 another program has it |
| Window shows nothing | §2 missing `waitKey` |
| Both cameras 640x480 | §2 didn't request resolution |
| Markers not detected | §3 quiet zone, or wrong dictionary |
| RMS above 1.5 | §4 corner coverage, bent board |
| Reprojection above 3px | §3 wrong `marker_size` |
| Grid tilted in verify | §5 marker positions wrong |
| Left/right swapped | §5 marker facing direction |
| Error grows with distance | §4 bad intrinsics |
| Constant offset everywhere | §5 wrong origin corner |
