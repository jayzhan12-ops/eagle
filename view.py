"""Camera viewer with FPS readout.

    python view.py 1            # MJPEG, 1280x720  (try this first)
    python view.py 1 --raw      # no MJPEG, for comparison
    python view.py 1 --small    # 640x480, tests whether it's bandwidth
    python view.py 1 --mf       # Media Foundation instead of DirectShow

Press q to quit. NOT Ctrl+C -- that leaves the camera locked.
"""

import sys
import time

import cv2

# ---- read the command line -------------------------------------------
args = [a for a in sys.argv[1:]]
idx = 0
for a in args:
    if not a.startswith('--'):
        idx = int(a)

use_mjpg = '--raw' not in args
small = '--small' in args
backend = cv2.CAP_MSMF if '--mf' in args else cv2.CAP_DSHOW

W, H = (640, 480) if small else (1280, 720)

# ---- open the camera -------------------------------------------------
cap = cv2.VideoCapture(idx, backend)
if not cap.isOpened():
    print(f'cannot open camera {idx}')
    print('  another program may have it -- close Zoom / Teams / Discord')
    sys.exit(1)

# ORDER MATTERS. FOURCC must be set BEFORE resolution, or the camera
# falls back to raw YUY2, which needs far more USB bandwidth than the
# cable can carry at 720p -- and the frame rate collapses.
if use_mjpg:
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))

cap.set(cv2.CAP_PROP_FRAME_WIDTH, W)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, H)
cap.set(cv2.CAP_PROP_FPS, 30)

# Keep the buffer at 1 frame so read() returns the newest image rather
# than working through a backlog.
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

# ---- report what we actually got -------------------------------------
aw = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
ah = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
afps = cap.get(cv2.CAP_PROP_FPS)
fourcc = int(cap.get(cv2.CAP_PROP_FOURCC))
codec = ''.join(chr((fourcc >> (8 * i)) & 0xFF) for i in range(4))

print(f'camera {idx}')
print(f'  backend   : {"MSMF" if backend == cv2.CAP_MSMF else "DSHOW"}')
print(f'  resolution: {aw}x{ah}   (asked {W}x{H})')
print(f'  codec     : {codec.strip()}   (asked {"MJPG" if use_mjpg else "raw"})')
print(f'  fps claim : {afps}')
print('\nq = quit,  s = save a frame\n')

# ---- loop ------------------------------------------------------------
n = 0
t0 = time.time()
recent = []
last = t0

while True:
    ok, frame = cap.read()
    if not ok:
        print('read failed -- camera disconnected?')
        break

    now = time.time()
    dt = now - last
    last = now
    if dt > 0:
        recent.append(1.0 / dt)
        recent = recent[-30:]          # rolling window
    inst = sum(recent) / len(recent) if recent else 0

    n += 1
    avg = n / (now - t0)

    label = f'{inst:5.1f} fps now   {avg:5.1f} avg   {aw}x{ah} {codec.strip()}'
    cv2.rectangle(frame, (0, 0), (frame.shape[1], 34), (0, 0, 0), -1)
    cv2.putText(frame, label, (10, 24), cv2.FONT_HERSHEY_SIMPLEX,
                0.6, (120, 255, 180), 1)

    cv2.imshow(f'camera {idx}', frame)

    k = cv2.waitKey(1) & 0xFF
    if k == ord('q'):
        break
    if k == ord('s'):
        cv2.imwrite('frame.png', frame)
        print('  saved frame.png')

cap.release()
cv2.destroyAllWindows()

print(f'\n{n} frames in {time.time()-t0:.1f}s  ->  {avg:.1f} fps average')
if avg < 12:
    print('\nSTILL SLOW. Work through these in order:')
    print('  1. Turn the room lights up. Dim light means long exposure,')
    print('     which caps fps mechanically -- 1/8s exposure = 8fps max.')
    print('  2. Plug into a USB 3.0 port directly, no hub.')
    print('  3. Try:  python view.py {} --small'.format(idx))
    print('     If that is fast, it is a bandwidth problem.')
    print('  4. Try:  python view.py {} --mf'.format(idx))