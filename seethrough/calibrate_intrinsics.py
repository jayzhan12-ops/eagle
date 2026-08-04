"""Intrinsic calibration: what shape are this camera's lens and sensor?

Do this ONCE per camera, ever. It does not change when you move the camera
or change rooms. Save the result and reuse forever.

    python3 -m seethrough.calibrate_intrinsics --device 0 --out calib/cam_a.json

Hold a printed chessboard at MANY angles and distances. Fill the frame.
Tilt it. Corners of the image matter most -- that is where distortion lives.
Press SPACE to capture, Q when you have 20+ good views.
"""
import argparse
import json
from pathlib import Path

import cv2
import numpy as np


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--device', default='0')
    ap.add_argument('--cols', type=int, default=9, help='INNER corners across')
    ap.add_argument('--rows', type=int, default=6, help='INNER corners down')
    ap.add_argument('--square-mm', type=float, default=25.0)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()

    src = int(args.device) if args.device.isdigit() else args.device
    cap = cv2.VideoCapture(src, cv2.CAP_DSHOW)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    if not cap.isOpened():
        raise SystemExit(f'cannot open {args.device}')

    pattern = (args.cols, args.rows)
    objp = np.zeros((args.rows * args.cols, 3), np.float32)
    objp[:, :2] = np.mgrid[0:args.cols, 0:args.rows].T.reshape(-1, 2)
    objp *= args.square_mm / 1000.0

    obj_pts, img_pts = [], []
    size = None
    crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)

    print('SPACE = capture   Q = finish   need 20+ varied views')
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        size = gray.shape[::-1]
        found, corners = cv2.findChessboardCorners(
            gray, pattern,
            cv2.CALIB_CB_ADAPTIVE_THRESH + cv2.CALIB_CB_NORMALIZE_IMAGE)

        view = frame.copy()
        if found:
            cv2.drawChessboardCorners(view, pattern, corners, found)
        col = (0, 255, 0) if found else (0, 0, 255)
        cv2.putText(view, f'captured: {len(obj_pts)}', (12, 32),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, col, 2)
        cv2.imshow('intrinsics', view)

        k = cv2.waitKey(1) & 0xFF
        if k == ord('q'):
            break
        if k == ord(' ') and found:
            fine = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), crit)
            obj_pts.append(objp.copy())
            img_pts.append(fine)
            print(f'  captured {len(obj_pts)}')

    cap.release()
    cv2.destroyAllWindows()

    if len(obj_pts) < 8:
        raise SystemExit(f'only {len(obj_pts)} views -- need at least 8, prefer 20')

    rms, K, dist, rvecs, tvecs = cv2.calibrateCamera(
        obj_pts, img_pts, size, None, None)

    # per-view error tells you if one bad capture is poisoning the result
    errs = []
    errs = []
    for i in range(len(obj_pts)):
        proj, _ = cv2.projectPoints(obj_pts[i], rvecs[i], tvecs[i], K, dist)
        obs = img_pts[i].reshape(-1, 2)
        pred = proj.reshape(-1, 2)
        errs.append(float(np.mean(np.linalg.norm(pred - obs, axis=1))))

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        'K': K.tolist(), 'dist': dist.ravel().tolist(),
        'size': list(size), 'rms_px': float(rms),
        'views': len(obj_pts),
        'per_view_error_px': errs,
    }, indent=2))

    print(f'\nRMS reprojection error: {rms:.4f} px')
    print(f'  < 0.5  excellent')
    print(f'  < 1.0  fine')
    print(f'  > 1.5  recapture -- check focus and pattern flatness')
    print(f'worst single view: {max(errs):.3f} px')
    print(f'saved -> {out}')


if __name__ == '__main__':
    main()
