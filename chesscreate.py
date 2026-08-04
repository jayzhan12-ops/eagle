#!/usr/bin/env python3
"""Generate a printable calibration chessboard.

    python make_chessboard.py                       # 9x6 corners, 25mm
    python make_chessboard.py --cols 9 --rows 6 --square-mm 25

WHY THIS EXISTS
---------------
Two things go wrong with downloaded chessboards:

  1. You don't know whether "9x6" means squares or inner corners.
     This script is explicit: --cols and --rows are INNER CORNERS, which
     is what OpenCV wants.

  2. Printers scale. You still have to measure the result -- but instead
     of measuring one small square with a ruler (imprecise), this sheet
     prints a 100 mm reference bar. Measure THAT, and the script tells
     you how to compute your true square size.

     Measuring a 100 mm line to the nearest millimetre is 1% accurate.
     Measuring a 25 mm square to the nearest millimetre is 4% accurate.
     At 6 metres that difference is 18 cm of position error.
"""

import argparse

import cv2
import numpy as np


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cols', type=int, default=9,
                    help='INNER corners across (squares across minus 1)')
    ap.add_argument('--rows', type=int, default=6,
                    help='INNER corners down (squares down minus 1)')
    ap.add_argument('--square-mm', type=float, default=25.0)
    ap.add_argument('--dpi', type=int, default=300)
    ap.add_argument('--out', default='chessboard.png')
    args = ap.parse_args()

    # inner corners -> squares
    sq_x = args.cols + 1
    sq_y = args.rows + 1

    px_per_mm = args.dpi / 25.4
    s = int(round(args.square_mm * px_per_mm))     # square side in pixels

    board_w = sq_x * s
    board_h = sq_y * s

    margin = int(round(12 * px_per_mm))            # 12 mm white border
    footer = int(round(26 * px_per_mm))            # room for label + scale bar

    W = board_w + 2 * margin
    H = board_h + 2 * margin + footer

    img = np.full((H, W), 255, np.uint8)

    # ---- the board itself ------------------------------------------
    for r in range(sq_y):
        for c in range(sq_x):
            if (r + c) % 2 == 0:                   # top-left square black
                y0 = margin + r * s
                x0 = margin + c * s
                img[y0:y0 + s, x0:x0 + s] = 0

    # ---- 100 mm reference bar --------------------------------------
    # Measure this after printing. It is the whole point of the sheet.
    bar_mm = 100.0
    bar_px = int(round(bar_mm * px_per_mm))
    by = margin + board_h + int(round(9 * px_per_mm))
    bx = margin

    cv2.line(img, (bx, by), (bx + bar_px, by), 0, max(2, s // 40))
    tick = int(round(3.5 * px_per_mm))
    for mm in range(0, 101, 10):
        tx = bx + int(round(mm * px_per_mm))
        long_tick = (mm % 50 == 0)
        cv2.line(img, (tx, by), (tx, by - (tick * 2 if long_tick else tick)),
                 0, max(2, s // 50))

    fs = s / 90.0                                  # font scale, size-relative
    cv2.putText(img, 'MEASURE THIS BAR: should be 100 mm',
                (bx, by + int(round(7 * px_per_mm))),
                cv2.FONT_HERSHEY_SIMPLEX, fs, 0, max(1, s // 60))

    # ---- label -----------------------------------------------------
    label = (f'{args.cols}x{args.rows} INNER CORNERS  '
             f'({sq_x}x{sq_y} squares)   nominal {args.square_mm:.1f} mm')
    cv2.putText(img, label,
                (bx, by + int(round(15 * px_per_mm))),
                cv2.FONT_HERSHEY_SIMPLEX, fs, 0, max(1, s // 60))

    cv2.imwrite(args.out, img)

    # ---- instructions ----------------------------------------------
    print(f'saved {args.out}')
    print(f'  {args.cols}x{args.rows} inner corners = '
          f'{sq_x}x{sq_y} squares')
    print(f'  nominal square: {args.square_mm} mm')
    print(f'  image: {W}x{H} px at {args.dpi} dpi '
          f'= {W/px_per_mm:.0f}x{H/px_per_mm:.0f} mm on paper')

    if W / px_per_mm > 200 or H / px_per_mm > 287:
        print('\n  WARNING: larger than A4 printable area.')
        print('  Reduce --square-mm or the board will be clipped.')

    print('\nPRINT: 100% scale, "fit to page" OFF.')
    print('THEN: measure the 100 mm bar with a ruler.')
    print('\n  If the bar measures exactly 100 mm:')
    print(f'    your square size is {args.square_mm} mm')
    print('\n  If it measures something else, say 102 mm:')
    print(f'    true square = {args.square_mm} * 102 / 100 = '
          f'{args.square_mm * 1.02:.2f} mm')
    print('\nUse that number for --square-mm when calibrating.')
    print(f'And use --cols {args.cols} --rows {args.rows}')


if __name__ == '__main__':
    main()