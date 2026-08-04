"""Generate printable ArUco markers.

Print at 100% scale (NO 'fit to page'), then MEASURE the printed square
with a ruler. Printers lie. Put the measured size in your room JSON.

    python3 -m seethrough.make_markers --count 6 --size-mm 150
"""
import argparse
from pathlib import Path

import cv2
import numpy as np

DICT = cv2.aruco.DICT_5X5_100


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--count', type=int, default=6)
    ap.add_argument('--size-mm', type=float, default=150.0)
    ap.add_argument('--dpi', type=int, default=300)
    ap.add_argument('--out', default='markers')
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    d = cv2.aruco.getPredefinedDictionary(DICT)

    px = int(args.size_mm / 25.4 * args.dpi)
    quiet = px // 6                      # white border, required for detection

    for i in range(args.count):
        img = cv2.aruco.generateImageMarker(d, i, px)
        canvas = np.full((px + 2*quiet, px + 2*quiet), 255, np.uint8)
        canvas[quiet:quiet+px, quiet:quiet+px] = img
        cv2.putText(canvas, f'ID {i}  {args.size_mm:.0f}mm',
                    (quiet, quiet - 12), cv2.FONT_HERSHEY_SIMPLEX,
                    quiet / 90.0, 0, 2)
        cv2.imwrite(str(out / f'marker_{i:02d}.png'), canvas)

    print(f'{args.count} markers -> {out}/')
    print(f'Print at 100% scale. Then MEASURE one and record the real size.')


if __name__ == '__main__':
    main()
