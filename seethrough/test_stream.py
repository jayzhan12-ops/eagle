#!/usr/bin/env python3
"""Test a wireless camera stream before wiring it into anything else.

    python3 -m seethrough.test_stream http://192.168.1.55:8080/video

If no path works, run with just the host and it will try common ones:

    python3 -m seethrough.test_stream 192.168.1.55:8080 --probe

Press q to quit, s to save a frame (useful as a calibration test shot).
"""

import argparse
import os
import sys
import time

# MUST be set before cv2 is imported. OpenCV's ffmpeg backend defaults to
# RTSP-over-UDP, which many phone camera servers refuse -- the connection
# then dies with "server closed". Forcing TCP fixes it in most cases.
os.environ.setdefault(
    'OPENCV_FFMPEG_CAPTURE_OPTIONS',
    'rtsp_transport;tcp|stimeout;5000000|max_delay;500000')

import cv2

# Paths used by common iOS/Android IP camera apps
COMMON_PATHS = [
    '/video', '/live', '/videofeed', '/stream', '/video.mjpg',
    '/mjpegfeed', '/cam.mjpg', '/',
]

# Phone camera servers commonly expose RTSP on 554 or 8554.
RTSP_CANDIDATES = ['/live', '/live.sdp', '/h264', '/stream', '/']
RTSP_PORTS = [554, 8554]


def _try(url):
    cap = cv2.VideoCapture(url)
    ok = False
    frame = None
    if cap.isOpened():
        ok, frame = cap.read()
    cap.release()
    return (ok and frame is not None), frame


def probe(host, user=None, pw=None):
    """Try common stream paths, HTTP first then RTSP, until one gives a frame."""
    scheme_given = '://' in host
    bare = host.split('://')[-1].rstrip('/')
    auth = f'{user}:{pw}@' if user else ''

    candidates = []
    if not scheme_given or host.startswith('http'):
        hostport = bare if ':' in bare else bare + ':8080'
        candidates += [f'http://{auth}{hostport}{p}' for p in COMMON_PATHS]
    if not scheme_given or host.startswith('rtsp'):
        h = bare.split(':')[0]
        for port in RTSP_PORTS:
            candidates += [f'rtsp://{auth}{h}:{port}{p}' for p in RTSP_CANDIDATES]

    print(f'probing {bare} ({len(candidates)} candidates) ...\n')
    for url in candidates:
        sys.stdout.write(f'  {url:<56}')
        sys.stdout.flush()
        ok, frame = _try(url)
        if ok:
            print(f'OK  {frame.shape[1]}x{frame.shape[0]}')
            return url
        print('--')
    return None


def run(url, seconds):
    cap = cv2.VideoCapture(url)
    # Keep the buffer tiny -- OpenCV will happily hand you 2s-old frames
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    if not cap.isOpened():
        print(f'\nCANNOT OPEN: {url}')
        print('  - does it play in your laptop browser?')
        print('  - same Wi-Fi network, not a guest network?')
        print('  - is the app still in the FOREGROUND, screen ON?')
        print('  - RTSP? transport is forced to TCP; check port 554 vs 8554')
        print('  - auth needed? pass --user admin --pw admin')
        return 1

    ok, frame = cap.read()
    if not ok:
        print('opened but no frames -- the app may need a different path')
        return 1

    h, w = frame.shape[:2]
    print(f'\nconnected: {w}x{h}')
    print('q = quit   s = save frame\n')

    n, dropped = 0, 0
    t0 = time.time()
    t_last = t0
    fps_window = []

    while True:
        t_read = time.time()
        ok, frame = cap.read()
        read_ms = (time.time() - t_read) * 1000
        if not ok:
            dropped += 1
            if dropped > 30:
                print('\nstream died')
                break
            continue

        n += 1
        now = time.time()
        dt = now - t_last
        t_last = now
        if dt > 0:
            fps_window.append(1.0 / dt)
            fps_window = fps_window[-30:]
        fps = sum(fps_window) / len(fps_window) if fps_window else 0

        view = frame.copy()
        bar = f'{w}x{h}   {fps:5.1f} fps   read {read_ms:5.1f} ms   frames {n}   dropped {dropped}'
        cv2.rectangle(view, (0, 0), (view.shape[1], 34), (0, 0, 0), -1)
        cv2.putText(view, bar, (10, 24), cv2.FONT_HERSHEY_SIMPLEX,
                    0.55, (120, 255, 180), 1)
        cv2.imshow('stream test', view)

        k = cv2.waitKey(1) & 0xFF
        if k == ord('q'):
            break
        if k == ord('s'):
            cv2.imwrite('stream_frame.png', frame)
            print('  saved stream_frame.png')
        if seconds and now - t0 > seconds:
            break

    cap.release()
    cv2.destroyAllWindows()

    elapsed = time.time() - t0
    print(f'\n{n} frames in {elapsed:.1f}s  ->  {n/elapsed:.1f} fps average')
    print(f'dropped reads: {dropped}')
    print('\nwant: 15+ fps, few drops. Below 10 fps, lower the app\'s resolution.')
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('url', help='full stream URL, or host:port with --probe')
    ap.add_argument('--probe', action='store_true',
                    help='try common stream paths on that host')
    ap.add_argument('--seconds', type=float, default=0,
                    help='auto-stop after N seconds (0 = until q)')
    ap.add_argument('--user', help='username, if the app requires auth')
    ap.add_argument('--pw', help='password (IP Camera Lite default: admin)')
    args = ap.parse_args()

    url = args.url
    if args.probe:
        found = probe(url, args.user, args.pw)
        if not found:
            print('\nno working path found.')
            print('open the app and read the exact URL it displays.')
            return 1
        print(f'\nworking URL: {found}\n')
        url = found

    return run(url, args.seconds)


if __name__ == '__main__':
    sys.exit(main())
