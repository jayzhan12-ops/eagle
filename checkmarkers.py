import os
os.environ.setdefault('OPENCV_VIDEOIO_MSMF_ENABLE_HW_TRANSFORMS', '0')
import cv2

d = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_5X5_100)
detector = cv2.aruco.ArucoDetector(d, cv2.aruco.DetectorParameters())

cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

while True:
    ok, f = cap.read()
    if not ok:
        break
    corners, ids, _ = detector.detectMarkers(f)
    if ids is not None:
        cv2.aruco.drawDetectedMarkers(f, corners, ids)
        cv2.putText(f, f"found: {ids.ravel()}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
    cv2.imshow('markers', f)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()