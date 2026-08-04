"""Extrinsic calibration: WHERE is this camera in the room?

Needs intrinsics already done, plus markers stuck on walls at positions
you have MEASURED with a tape measure and written into the room JSON.

    python3 -m seethrough.calibrate_extrinsics \
        --device 0 --name cam_a \
        --intrinsics calib/cam_a.json --room config/room.json

Point the camera so it sees at least 2 markers (3+ is much better).
Press SPACE to solve, Q to quit.

This is the step the trajectory method will eventually replace. Keep it --
it is your ground truth for measuring how good the markerless version is.
"""
import argparse
import json
from pathlib import Path

import cv2
import numpy as np

from .geometry import Camera, Room

DICT = cv2.aruco.DICT_5X5_100


def marker_corners_world(centre, size):
    """The 4 corners of a wall-mounted marker, in world coords.

    Assumes the marker lies in a vertical plane facing -Y (i.e. stuck on a
    wall you look at while facing +Y), corners ordered as OpenCV expects:
    top-left, top-right, bottom-right, bottom-left.

    If your markers face a different direction, edit this. Getting it wrong
    gives you a mirrored solution, which is a very confusing bug.
    """
    cx, cy, cz = centre
    h = size / 2.0
    return np.array([
        [cx - h, cy, cz + h],
        [cx + h, cy, cz + h],
        [cx + h, cy, cz - h],
        [cx - h, cy, cz - h],
    ], dtype=np.float64)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--device', default='0')
    ap.add_argument('--name', required=True)
    ap.add_argument('--intrinsics', required=True)
    ap.add_argument('--room', required=True)
    args = ap.parse_args()

    intr = json.loads(Path(args.intrinsics).read_text())
    K = np.array(intr['K'], float)
    dist = np.array(intr['dist'], float)

    room = Room.load(args.room)
    if not room.markers:
        raise SystemExit('room JSON has no markers -- measure them first')

    d = cv2.aruco.getPredefinedDictionary(DICT)
    params = cv2.aruco.DetectorParameters()
    params.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX
    detector = cv2.aruco.ArucoDetector(d, params)

    src = int(args.device) if args.device.isdigit() else args.device
    cap = cv2.VideoCapture(src, cv2.CAP_DSHOW)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    if not cap.isOpened():
        raise SystemExit(f'cannot open {args.device}')

    print('SPACE = solve pose   Q = quit')
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        corners, ids, _ = detector.detectMarkers(frame)

        view = frame.copy()
        known = []
        if ids is not None:
            cv2.aruco.drawDetectedMarkers(view, corners, ids)
            known = [int(i) for i in ids.ravel() if int(i) in room.markers]

        cv2.putText(view, f'known markers visible: {len(known)} {known}',
                    (12, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                    (0, 255, 0) if len(known) >= 2 else (0, 0, 255), 2)
        cv2.imshow('extrinsics', view)

        k = cv2.waitKey(1) & 0xFF
        if k == ord('q'):
            break
        if k != ord(' ') or len(known) < 2:
            continue

        obj, img = [], []
        for c, i in zip(corners, ids.ravel()):
            i = int(i)
            if i not in room.markers:
                continue
            obj.append(marker_corners_world(room.markers[i], room.marker_size))
            img.append(c.reshape(4, 2))
        obj = np.vstack(obj).astype(np.float64)
        img = np.vstack(img).astype(np.float64)

        ok_pnp, rvec, tvec, inliers = cv2.solvePnPRansac(
            obj, img, K, dist, flags=cv2.SOLVEPNP_ITERATIVE,
            reprojectionError=3.0, confidence=0.999, iterationsCount=200)
        if not ok_pnp:
            print('solvePnP failed -- try seeing more markers')
            continue

        rvec, tvec = cv2.solvePnPRefineLM(obj, img, K, dist, rvec, tvec)

        cam = Camera(args.name, K, dist, rvec, tvec, intr.get('size'))
        pred = cam.project(obj)
        err = float(np.mean(np.linalg.norm(pred - img, axis=1)))

        print(f'\n  camera position : {np.round(cam.center, 3)} m')
        print(f'  looking towards : {np.round(cam.looks_at(), 3)}')
        print(f'  reprojection    : {err:.2f} px  '
              f'({len(inliers) if inliers is not None else len(obj)}/{len(obj)} inliers)')
        if err > 3.0:
            print('  WARNING: high error. Check marker positions in the room JSON.')

        room.add_camera(cam)
        room.save(args.room)
        print(f'  saved -> {args.room}')

    cap.release()
    cv2.destroyAllWindows()


if __name__ == '__main__':
    main()
