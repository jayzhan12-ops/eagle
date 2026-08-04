"""Camera geometry: the foundation everything else stands on.

FRAME CONVENTIONS -- write these on paper and check every transform.

  World frame:   X right, Y forward, Z UP. Floor is z = 0. Right-handed.
  Camera frame:  OpenCV convention -- x right, y DOWN, z FORWARD (into scene).

  solvePnP returns rvec/tvec that map WORLD -> CAMERA:
      X_cam = R @ X_world + t

  So the camera's position in the world is:
      C = -R.T @ t

  And a ray direction in camera coords becomes world coords via:
      d_world = R.T @ d_cam

The single most common bug in this project is applying one of these
backwards. When something is mirrored or inside-out, come back here first.
"""

import json
from pathlib import Path

import cv2
import numpy as np


class Camera:
    """One camera: how it sees (intrinsics) and where it is (extrinsics)."""

    def __init__(self, name, K, dist, rvec=None, tvec=None, size=None):
        self.name = name
        self.K = np.asarray(K, dtype=np.float64).reshape(3, 3)
        self.dist = np.asarray(dist, dtype=np.float64).ravel()
        self.size = tuple(size) if size else None      # (width, height)
        self.rvec = None
        self.tvec = None
        if rvec is not None and tvec is not None:
            self.set_pose(rvec, tvec)

    # ------------------------------------------------------------------

    def set_pose(self, rvec, tvec):
        self.rvec = np.asarray(rvec, dtype=np.float64).reshape(3, 1)
        self.tvec = np.asarray(tvec, dtype=np.float64).reshape(3, 1)
        self.R, _ = cv2.Rodrigues(self.rvec)           # world -> camera
        self.Rt = self.R.T                             # camera -> world
        self.center = (-self.Rt @ self.tvec).ravel()   # camera position in world

    @property
    def located(self):
        return self.rvec is not None

    # ------------------------------------------------------------------

    def undistort_points(self, pts):
        """Pixel coords -> normalised camera coords, lens distortion removed."""
        pts = np.asarray(pts, dtype=np.float64).reshape(-1, 1, 2)
        return cv2.undistortPoints(pts, self.K, self.dist).reshape(-1, 2)

    def ray(self, u, v):
        """Pixel -> (origin, unit direction) in WORLD coordinates."""
        if not self.located:
            raise RuntimeError(f'{self.name}: pose unknown, run extrinsic calibration')
        xn, yn = self.undistort_points([[u, v]])[0]
        d_cam = np.array([xn, yn, 1.0])
        d_world = self.Rt @ d_cam
        d_world /= np.linalg.norm(d_world)
        return self.center.copy(), d_world

    def pixel_to_plane(self, u, v, z=0.0, max_range=40.0):
        """Where does the ray through this pixel hit the horizontal plane at height z?

        Returns (x, y, z) in world coords, or None if the ray never gets there.
        This is how a detection becomes a position: use the pixel where the
        person's feet meet the floor, and z=0.
        """
        origin, d = self.ray(u, v)
        if abs(d[2]) < 1e-9:
            return None                        # ray parallel to the plane
        s = (z - origin[2]) / d[2]
        if s <= 0 or s > max_range:
            return None                        # behind camera, or absurdly far
        return origin + s * d

    def project(self, points_world):
        """World points -> pixels. The inverse operation; used for verification."""
        if not self.located:
            raise RuntimeError(f'{self.name}: pose unknown')
        pts = np.asarray(points_world, dtype=np.float64).reshape(-1, 1, 3)
        img, _ = cv2.projectPoints(pts, self.rvec, self.tvec, self.K, self.dist)
        return img.reshape(-1, 2)

    def looks_at(self, distance=1.0):
        """Unit vector the camera is pointing, in world coords. For drawing."""
        return (self.Rt @ np.array([0.0, 0.0, 1.0])) * distance

    # ------------------------------------------------------------------

    def to_dict(self):
        d = {
            'name': self.name,
            'K': self.K.tolist(),
            'dist': self.dist.tolist(),
            'size': list(self.size) if self.size else None,
        }
        if self.located:
            d['rvec'] = self.rvec.ravel().tolist()
            d['tvec'] = self.tvec.ravel().tolist()
            d['center'] = self.center.tolist()
        return d

    @staticmethod
    def from_dict(d):
        return Camera(d['name'], d['K'], d['dist'],
                      d.get('rvec'), d.get('tvec'), d.get('size'))


class Room:
    """Everything room-specific lives here, in one JSON file.

    Move to a new room -> write a new JSON. No code changes. That is the
    whole point: the pipeline is generic, the room is data.
    """

    def __init__(self, name='room'):
        self.name = name
        self.cameras = {}
        self.markers = {}      # id -> (x, y, z) of marker centre in world
        self.marker_size = 0.15
        self.walls = []        # list of {p, n} plane dicts, filled in later

    def add_camera(self, cam):
        self.cameras[cam.name] = cam

    def save(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            'name': self.name,
            'marker_size': self.marker_size,
            'markers': {str(k): list(v) for k, v in self.markers.items()},
            'walls': self.walls,
            'cameras': {k: c.to_dict() for k, c in self.cameras.items()},
        }
        path.write_text(json.dumps(data, indent=2))
        return path

    @staticmethod
    def load(path):
        data = json.loads(Path(path).read_text())
        r = Room(data.get('name', 'room'))
        r.marker_size = data.get('marker_size', 0.15)
        r.markers = {int(k): tuple(v) for k, v in data.get('markers', {}).items()}
        r.walls = data.get('walls', [])
        for k, cd in data.get('cameras', {}).items():
            r.cameras[k] = Camera.from_dict(cd)
        return r


# ----------------------------------------------------------------------
# Multi-view triangulation -- for week 3, when one point is seen by two
# cameras and you want its true 3D position without assuming it is on
# the floor.
# ----------------------------------------------------------------------

def triangulate(observations):
    """observations: list of (Camera, (u, v)). Returns world point (3,).

    Solves for the 3D point minimising distance to all viewing rays
    (linear least squares). Needs at least two cameras.
    """
    if len(observations) < 2:
        raise ValueError('need at least two views')

    A = np.zeros((3, 3))
    b = np.zeros(3)
    I = np.eye(3)
    for cam, (u, v) in observations:
        o, d = cam.ray(u, v)
        M = I - np.outer(d, d)     # projects onto the plane normal to d
        A += M
        b += M @ o
    return np.linalg.solve(A, b)


def reprojection_error(cam, world_pts, pixel_pts):
    """Mean pixel distance between where points ARE and where we PREDICT them.

    The single most useful diagnostic in the project. Under 1 px is good,
    over 3 px means something is wrong with your calibration.
    """
    pred = cam.project(world_pts)
    obs = np.asarray(pixel_pts, dtype=np.float64).reshape(-1, 2)
    return float(np.mean(np.linalg.norm(pred - obs, axis=1)))
