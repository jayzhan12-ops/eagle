"""Find the fastest working camera configuration.

    python probe.py 1

Tries every combination of backend, codec and resolution, measures the real
frame rate for each, and prints a table. No guessing.

Takes about a minute. Some combinations will fail or hang briefly -- that is
expected and handled.
"""

import os
import sys
import time

# Some Windows systems need this for MSMF to behave. Must be set before cv2
# is imported.
os.environ.setdefault('OPENCV_VIDEOIO_MSMF_ENABLE_HW_TRANSFORMS', '0')

import cv2

IDX = int(sys.argv[1]) if len(sys.argv) > 1 else 0
SECONDS = 2.0

BACKENDS = [
    ('DSHOW', cv2.CAP_DSHOW),
    ('MSMF', cv2.CAP_MSMF),
    ('ANY', cv2.CAP_ANY),
]

CODECS = ['MJPG', None]          # None = leave whatever the driver picks

SIZES = [(1280, 720), (960, 540), (800, 600), (640, 480)]


def measure(backend_id, codec, w, h):
    """Open with these settings, measure fps for a couple of seconds."""
    cap = cv2.VideoCapture(IDX, backend_id)
    if not cap.isOpened():
        cap.release()
        return None

    # FOURCC before resolution -- the driver picks a format when the
    # resolution is set, and asking afterwards is often ignored.
    if codec:
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*codec))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, w)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)
    cap.set(cv2.CAP_PROP_FPS, 30)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    ok, _ = cap.read()
    if not ok:
        cap.release()
        return None

    aw = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    ah = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fc = int(cap.get(cv2.CAP_PROP_FOURCC))
    got_codec = ''.join(chr((fc >> (8 * i)) & 0xFF) for i in range(4)).strip()

    # throw away the first few frames while exposure settles
    for _ in range(5):
        cap.read()

    n = 0
    t0 = time.time()
    while time.time() - t0 < SECONDS:
        ok, _ = cap.read()
        if not ok:
            break
        n += 1
    elapsed = time.time() - t0
    cap.release()

    return {
        'w': aw, 'h': ah,
        'codec': got_codec or '?',
        'fps': n / elapsed if elapsed > 0 else 0,
    }


def main():
    print(f'probing camera {IDX} -- about a minute\n')
    print(f'{"backend":8} {"asked":10} {"got":10} {"codec":6} {"fps":>6}')
    print('-' * 46)

    results = []
    for bname, bid in BACKENDS:
        for codec in CODECS:
            for w, h in SIZES:
                asked = f'{w}x{h}'
                want = codec or 'auto'
                try:
                    r = measure(bid, codec, w, h)
                except Exception:
                    r = None

                if r is None:
                    print(f'{bname:8} {asked:10} {"-":10} {want:6} {"fail":>6}')
                    continue

                got = f'{r["w"]}x{r["h"]}'
                print(f'{bname:8} {asked:10} {got:10} '
                      f'{r["codec"]:6} {r["fps"]:6.1f}')
                results.append((bname, codec, w, h, r))

    if not results:
        print('\nnothing worked. Is another program holding the camera?')
        print('Close Zoom / Teams / Discord / Windows Camera and retry.')
        return

    print('\n' + '=' * 46)

    # best overall, and best at 720p or better
    best = max(results, key=lambda x: x[4]['fps'])
    big = [r for r in results if r[4]['w'] >= 1280 and r[4]['fps'] >= 15]

    def show(tag, item):
        bname, codec, w, h, r = item
        print(f'\n{tag}')
        print(f'  {bname}, {codec or "auto"} codec, {r["w"]}x{r["h"]}, '
              f'{r["fps"]:.1f} fps (actual codec {r["codec"]})')
        backend_const = {'DSHOW': 'cv2.CAP_DSHOW',
                         'MSMF': 'cv2.CAP_MSMF',
                         'ANY': 'cv2.CAP_ANY'}[bname]
        print('\n  Use this:')
        print(f'    cap = cv2.VideoCapture({IDX}, {backend_const})')
        if codec:
            print(f"    cap.set(cv2.CAP_PROP_FOURCC, "
                  f"cv2.VideoWriter_fourcc(*'{codec}'))")
        print(f'    cap.set(cv2.CAP_PROP_FRAME_WIDTH, {r["w"]})')
        print(f'    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, {r["h"]})')

    show('FASTEST OVERALL', best)

    if big:
        best_big = max(big, key=lambda x: x[4]['fps'])
        if best_big is not best:
            show('BEST AT 720p OR ABOVE', best_big)
    else:
        print('\nNothing managed 15+ fps at 720p or above.')
        print('Use the fastest lower resolution above -- 640x480 is fine for')
        print('this project. Your markers are 204mm, so detection range is')
        print('still good.')

    print('\nNote: if all rows are slow, check the room lighting. Long')
    print('exposure caps frame rate mechanically -- 1/5s exposure = 5fps')
    print('regardless of settings.')


if __name__ == '__main__':
    main()