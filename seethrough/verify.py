"""THE WEEK 1 GATE.

Click a point on the floor in the camera view. Read off the world coordinate.
Go measure that spot with a tape measure. If you are not within 10 cm across
the room, DO NOT proceed to week 2 -- every later stage inherits this error.

    python3 -m seethrough.verify --device 0 --name cam_a --room config/room.json

Left panel : live camera. Click the floor.
Right panel: top-down map. Cameras, markers, and your clicked points.
Keys: c = clear points, s = save screenshot, q = quit
"""
import argparse

import cv2
import numpy as np

from .geometry import Room

MAP_PX = 720
MARGIN = 1.5          # metres of padding around content


class TopDown:
    def __init__(self, room, size=MAP_PX):
        self.size = size
        pts = [c.center[:2] for c in room.cameras.values() if c.located]
        pts += [np.array(m[:2]) for m in room.markers.values()]
        pts = np.array(pts) if pts else np.zeros((1, 2))
        lo = pts.min(axis=0) - MARGIN
        hi = pts.max(axis=0) + MARGIN
        span = max(hi - lo)
        self.lo = lo
        self.scale = (size - 40) / span if span > 1e-6 else 50.0

    def to_px(self, xy):
        p = (np.asarray(xy[:2]) - self.lo) * self.scale
        return int(20 + p[0]), int(self.size - 20 - p[1])   # flip Y for screen


def draw_map(room, td, points):
    img = np.full((td.size, td.size, 3), 22, np.uint8)

    for m in range(-20, 21):
        p = td.to_px([m, m])
        cv2.line(img, (p[0], 0), (p[0], td.size), (38, 38, 38), 1)
        cv2.line(img, (0, p[1]), (td.size, p[1]), (38, 38, 38), 1)

    for mid, pos in room.markers.items():
        p = td.to_px(pos)
        cv2.rectangle(img, (p[0]-5, p[1]-5), (p[0]+5, p[1]+5), (60, 200, 255), -1)
        cv2.putText(img, str(mid), (p[0]+9, p[1]+4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (60, 200, 255), 1)

    for cam in room.cameras.values():
        if not cam.located:
            continue
        c = td.to_px(cam.center)
        fwd = cam.looks_at()
        for sign in (-1, 1):
            ang = np.arctan2(fwd[1], fwd[0]) + sign * np.radians(30)
            e = td.to_px(cam.center[:2] + 2.2 * np.array([np.cos(ang), np.sin(ang)]))
            cv2.line(img, c, e, (90, 130, 90), 1)
        cv2.circle(img, c, 7, (120, 255, 180), -1)
        cv2.putText(img, cam.name, (c[0]+10, c[1]-8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (120, 255, 180), 1)

    for i, w in enumerate(points):
        p = td.to_px(w)
        cv2.circle(img, p, 5, (80, 80, 255), -1)
        cv2.putText(img, f'{w[0]:+.2f},{w[1]:+.2f}', (p[0]+8, p[1]+4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, (140, 140, 255), 1)

    o = td.to_px([0, 0])
    cv2.drawMarker(img, o, (255, 255, 255), cv2.MARKER_CROSS, 14, 1)
    cv2.putText(img, f'1 m = {td.scale:.0f} px   origin = world (0,0)',
                (12, td.size - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.45,
                (150, 150, 150), 1)
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--device', default='0')
    ap.add_argument('--name', required=True)
    ap.add_argument('--room', required=True)
    ap.add_argument('--height', type=float, default=0.0,
                    help='plane height to intersect, metres (0 = floor)')
    args = ap.parse_args()

    room = Room.load(args.room)
    cam = room.cameras.get(args.name)
    if cam is None or not cam.located:
        raise SystemExit(f'camera "{args.name}" not calibrated in {args.room}')

    td = TopDown(room)
    points = []

    def on_click(event, x, y, flags, _):
        if event != cv2.EVENT_LBUTTONDOWN:
            return
        w = cam.pixel_to_plane(x, y, z=args.height)
        if w is None:
            print('  ray never reaches that plane (pointing above horizon?)')
            return
        points.append(w)
        d = np.linalg.norm(w[:2] - cam.center[:2])
        print(f'  pixel ({x:4d},{y:4d})  ->  world '
              f'({w[0]:+.3f}, {w[1]:+.3f}, {w[2]:.3f})   '
              f'{d:.2f} m from {cam.name}')

    src = int(args.device) if args.device.isdigit() else args.device
    cap = cv2.VideoCapture(src, cv2.CAP_DSHOW)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    if not cap.isOpened():
        raise SystemExit(f'cannot open {args.device}')

    cv2.namedWindow('camera')
    cv2.setMouseCallback('camera', on_click)
    print('Click the FLOOR in the camera window, then measure that spot.')
    print('c = clear   s = save   q = quit\n')

    while True:
        ok, frame = cap.read()
        if not ok:
            break

        view = frame.copy()
        # draw a 1 m world grid onto the floor -- the fastest visual sanity check
        for gx in range(-4, 5):
            a = cam.project([[gx, -4, args.height]])[0]
            b = cam.project([[gx, 8, args.height]])[0]
            cv2.line(view, tuple(np.int32(a)), tuple(np.int32(b)), (60, 90, 60), 1)
        for gy in range(-4, 9):
            a = cam.project([[-4, gy, args.height]])[0]
            b = cam.project([[4, gy, args.height]])[0]
            cv2.line(view, tuple(np.int32(a)), tuple(np.int32(b)), (60, 90, 60), 1)

        for w in points:
            p = cam.project([w])[0]
            cv2.circle(view, tuple(np.int32(p)), 6, (80, 80, 255), -1)

        cv2.imshow('camera', view)
        cv2.imshow('top-down', draw_map(room, td, points))

        k = cv2.waitKey(1) & 0xFF
        if k == ord('q'):
            break
        if k == ord('c'):
            points.clear()
        if k == ord('s'):
            cv2.imwrite('verify_camera.png', view)
            cv2.imwrite('verify_map.png', draw_map(room, td, points))
            print('  saved verify_camera.png / verify_map.png')

    cap.release()
    cv2.destroyAllWindows()


if __name__ == '__main__':
    main()
