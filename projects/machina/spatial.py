"""
TM Spatial Engine — Coordinate-based spatial solver for cinematic scene graphs.

Core premise:
  Every object, prop, character, and camera exists at a coordinate (x, y, z)
  in a shared 3D space. All cinematic properties (apparent size, frame position,
  depth of field, camera activation, occlusion) are calculated deterministically
  from these coordinates — pure geometry, no guesswork.

This module is the foundation of the TM pipeline. Everything above it
(narrative → scene graph → compiler → prompt) builds on this spatial layer.
"""

from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Optional


# ═══════════════════════════════════════════════════════════════════════════════
# VECTOR3
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class Vector3:
    """A point or vector in 3D space. All units in meters."""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def __sub__(self, other: Vector3) -> Vector3:
        return Vector3(self.x - other.x, self.y - other.y, self.z - other.z)

    def __add__(self, other: Vector3) -> Vector3:
        return Vector3(self.x + other.x, self.y + other.y, self.z + other.z)

    def __mul__(self, scalar: float) -> Vector3:
        return Vector3(self.x * scalar, self.y * scalar, self.z * scalar)

    def __rmul__(self, scalar: float) -> Vector3:
        return self.__mul__(scalar)

    def __neg__(self) -> Vector3:
        return Vector3(-self.x, -self.y, -self.z)

    def __repr__(self) -> str:
        return f"({self.x:.2f}, {self.y:.2f}, {self.z:.2f})"

    def distance_to(self, other: Vector3) -> float:
        dx = self.x - other.x
        dy = self.y - other.y
        dz = self.z - other.z
        return math.sqrt(dx * dx + dy * dy + dz * dz)

    def dot(self, other: Vector3) -> float:
        return self.x * other.x + self.y * other.y + self.z * other.z

    def magnitude(self) -> float:
        return math.sqrt(self.x * self.x + self.y * self.y + self.z * self.z)

    def normalize(self) -> Vector3:
        m = self.magnitude()
        if m == 0:
            return Vector3(0, 0, 0)
        return Vector3(self.x / m, self.y / m, self.z / m)

    def cross(self, other: Vector3) -> Vector3:
        return Vector3(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x,
        )

    def lerp(self, other: Vector3, t: float) -> Vector3:
        """Linear interpolation toward other by factor t."""
        return Vector3(
            self.x + (other.x - self.x) * t,
            self.y + (other.y - self.y) * t,
            self.z + (other.z - self.z) * t,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# CAMERA (with rotation support)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Camera:
    """A camera with position, lens, sensor, and rotation.

    Coordinate convention:
      - World space: +x = East/right, +y = up, +z = North/forward
      - Camera starts looking along +z
      - Yaw: rotation around Y axis (positive = left/CCW from above)
      - Pitch: rotation around X axis (positive = tilt up)
      - Roll: rotation around Z axis (positive = roll clockwise from camera POV)
    """
    label: str = "Camera"
    position: Vector3 = Vector3(0, 1.7, 0)
    yaw_deg: float = 0.0
    pitch_deg: float = 0.0
    roll_deg: float = 0.0
    focal_length_mm: float = 50.0
    aperture: float = 2.8
    sensor_width_mm: float = 36.0
    sensor_height_mm: float = 24.0
    resolution_width: int = 1920
    resolution_height: int = 1080

    # ── Local axes in world space ────────────────────────────────────

    @property
    def _yaw_rad(self) -> float:
        return math.radians(self.yaw_deg)

    @property
    def _pitch_rad(self) -> float:
        return math.radians(self.pitch_deg)

    @property
    def _roll_rad(self) -> float:
        return math.radians(self.roll_deg)

    @property
    def forward(self) -> Vector3:
        """Forward direction vector in world space."""
        y, p = self._yaw_rad, self._pitch_rad
        return Vector3(
            math.sin(y) * math.cos(p),
            math.sin(p),
            math.cos(y) * math.cos(p),
        )

    @property
    def right(self) -> Vector3:
        """Right direction vector in world space (includes roll)."""
        y, p, r = self._yaw_rad, self._pitch_rad, self._roll_rad
        sy, cy = math.sin(y), math.cos(y)
        sp, cp = math.sin(p), math.cos(p)
        sr, cr = math.sin(r), math.cos(r)
        # Unrolled right (yaw only): (cos(yaw), 0, -sin(yaw))
        # Unrolled up (yaw then pitch): (-sin(yaw)*sin(pitch), cos(pitch), -cos(yaw)*sin(pitch))
        # Rolled right = unrolled_right * cos(roll) + unrolled_up * sin(roll)
        return Vector3(
            cy * cr + sy * sp * sr,
            cp * sr,
            -sy * cr + cy * sp * sr,
        )

    @property
    def up(self) -> Vector3:
        """Up direction vector in world space (includes roll)."""
        y, p, r = self._yaw_rad, self._pitch_rad, self._roll_rad
        sy, cy = math.sin(y), math.cos(y)
        sp, cp = math.sin(p), math.cos(p)
        sr, cr = math.sin(r), math.cos(r)
        # Rolled up = -unrolled_right * sin(roll) + unrolled_up * cos(roll)
        return Vector3(
            -cy * sr + sy * sp * cr,
            cp * cr,
            sy * sr + cy * sp * cr,
        )

    # ── Derived lens properties ──────────────────────────────────────

    @property
    def aspect(self) -> float:
        return self.resolution_width / self.resolution_height

    @property
    def hfov_deg(self) -> float:
        """Horizontal field of view (degrees)."""
        return math.degrees(2 * math.atan(self.sensor_width_mm / (2 * self.focal_length_mm)))

    @property
    def vfov_deg(self) -> float:
        """Vertical field of view (degrees)."""
        return math.degrees(2 * math.atan(self.sensor_height_mm / (2 * self.focal_length_mm)))

    @property
    def max_range_m(self) -> float:
        """Maximum useful detection distance. Defined as where a 1.8m subject
        occupies 5% of frame height."""
        return (self.focal_length_mm * 1.8) / (0.05 * self.sensor_height_mm)

    @property
    def hyperfocal_m(self) -> float:
        return (self.focal_length_mm ** 2) / (self.aperture * 0.03) / 1000.0

    # ── Transform ────────────────────────────────────────────────────

    def world_to_camera(self, point: Vector3) -> Vector3:
        """Transform a world-space point into camera space.

        In camera space: camera at origin, +x = right, +y = up, +z = forward.
        """
        rel = point - self.position
        return Vector3(
            rel.dot(self.right),
            rel.dot(self.up),
            rel.dot(self.forward),
        )

    def ray_from_pixel(self, nx: float, ny: float) -> Vector3:
        """Compute the world-space direction of a ray through normalized
        pixel coordinates nx, ny ∈ [-0.5, 0.5].

        Returns a unit direction vector in world space.
        """
        # Direction in camera space
        dx = nx * self.sensor_width_mm  / self.focal_length_mm
        dy = ny * self.sensor_height_mm / self.focal_length_mm
        cam_dir = Vector3(dx, dy, 1.0).normalize()

        # Transform to world space using camera axes
        return (self.right * cam_dir.x
              + self.up    * cam_dir.y
              + self.forward * cam_dir.z).normalize()


# ═══════════════════════════════════════════════════════════════════════════════
# SCENE OBJECT
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class SceneObject:
    """An object (prop, character, set piece) in the 3D scene.

    Bounding-box representation: position is the center of the object,
    width/height/depth are the extents along x/y/z in meters.
    """
    label: str
    position: Vector3
    width_m: float = 1.0
    height_m: float = 1.0
    depth_m: float = 1.0
    obj_type: str = "generic"


# ═══════════════════════════════════════════════════════════════════════════════
# SCENE
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Scene:
    """A complete 3D scene: multiple cameras + objects + boundaries."""
    name: str = "Untitled Scene"
    cameras: list[Camera] = field(default_factory=list)
    objects: list[SceneObject] = field(default_factory=list)
    world_min: Vector3 = Vector3(0, 0, 0)
    world_max: Vector3 = Vector3(38, 0, 42)  # x=east, y=up(0=ground), z=north


# ═══════════════════════════════════════════════════════════════════════════════
# PERSPECTIVE PROJECTION
# ═══════════════════════════════════════════════════════════════════════════════

def project_to_sensor(cam_point: Vector3, focal_mm: float) -> Optional[tuple[float, float]]:
    """Project camera-space point onto sensor. Returns (sx_mm, sy_mm) or None if behind camera."""
    if cam_point.z <= 0:
        return None
    return (focal_mm * cam_point.x / cam_point.z,
            focal_mm * cam_point.y / cam_point.z)


def sensor_to_frame(sx_mm: float, sy_mm: float, sw: float, sh: float) -> tuple[float, float]:
    """Sensor mm → normalized frame coords [-0.5, +0.5]."""
    return (sx_mm / sw, sy_mm / sh)


def is_point_visible(camera: Camera, world_point: Vector3) -> bool:
    """Check if a world-space point is visible to the camera (within frustum)."""
    cam_pt = camera.world_to_camera(world_point)
    sensor = project_to_sensor(cam_pt, camera.focal_length_mm)
    if sensor is None:
        return False
    sx, sy = sensor
    half_w = camera.sensor_width_mm / 2
    half_h = camera.sensor_height_mm / 2
    return abs(sx) <= half_w and abs(sy) <= half_h


# ═══════════════════════════════════════════════════════════════════════════════
# APPARENT SIZE
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ApparentSize:
    distance_m: float
    sensor_width_mm: float
    sensor_height_mm: float
    frame_occ_x: float
    frame_occ_y: float
    width_px: float
    height_px: float

    @property
    def occ_pct_x(self) -> float:
        return self.frame_occ_x * 100.0

    @property
    def occ_pct_y(self) -> float:
        return self.frame_occ_y * 100.0


def apparent_size(
    obj_w: float, obj_h: float, dist_m: float,
    focal_mm: float, sw: float, sh: float,
    rw: int, rh: int,
) -> ApparentSize:
    app_w = focal_mm * obj_w / dist_m
    app_h = focal_mm * obj_h / dist_m
    return ApparentSize(
        distance_m=round(dist_m, 3),
        sensor_width_mm=round(app_w, 3),
        sensor_height_mm=round(app_h, 3),
        frame_occ_x=round(app_w / sw, 6),
        frame_occ_y=round(app_h / sh, 6),
        width_px=round(app_w / sw * rw, 1),
        height_px=round(app_h / sh * rh, 1),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# DEPTH OF FIELD
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class DOFResult:
    hyperfocal_m: float
    near_m: float
    far_m: float
    total_m: float


def depth_of_field(aperture: float, focal_mm: float, dist_m: float,
                   coc_mm: float = 0.03) -> DOFResult:
    H = (focal_mm ** 2) / (aperture * coc_mm) / 1000.0
    if dist_m >= H:
        return DOFResult(round(H, 3), round(H / 2, 3), float("inf"), float("inf"))
    near = (H * dist_m) / (H + dist_m)
    far  = (H * dist_m) / (H - dist_m)
    return DOFResult(round(H, 3), round(near, 3), round(far, 3), round(far - near, 3))


# ═══════════════════════════════════════════════════════════════════════════════
# LENS SOLVER
# ═══════════════════════════════════════════════════════════════════════════════

def solve_focal_length(occ_y: float, obj_h: float, dist_m: float,
                       sensor_h: float = 24.0) -> float:
    return occ_y * dist_m * sensor_h / obj_h


# ═══════════════════════════════════════════════════════════════════════════════
# FRUSTUM → GROUND POLYGON
# ═══════════════════════════════════════════════════════════════════════════════

def camera_ground_polygon(camera: Camera, ground_y: float = 0.0,
                          max_dist: float = 50.0) -> list[Vector3]:
    """Compute the visible polygon on a ground plane (y=ground_y).

    Method: for each of the 4 frustum-corner rays, intersect the ray
    with the ground plane. Only returns points for rays that actually
    hit the ground (t >= 0). Upward-pointing rays are excluded.
    Returns 0-4 points in world space.
    """
    # Frustum corner directions in camera space
    hhfov = math.radians(camera.hfov_deg / 2)
    hvfov = math.radians(camera.vfov_deg / 2)

    corners_cam = [
        Vector3(-math.tan(hhfov),  math.tan(hvfov), 1.0).normalize(),  # TL
        Vector3( math.tan(hhfov),  math.tan(hvfov), 1.0).normalize(),  # TR
        Vector3( math.tan(hhfov), -math.tan(hvfov), 1.0).normalize(),  # BR
        Vector3(-math.tan(hhfov), -math.tan(hvfov), 1.0).normalize(),  # BL
    ]

    ground_points = []
    for d_cam in corners_cam:
        d_world = (camera.right * d_cam.x
                 + camera.up    * d_cam.y
                 + camera.forward * d_cam.z).normalize()

        if abs(d_world.y) < 1e-8:
            continue  # ray parallel to ground, skip

        t = (ground_y - camera.position.y) / d_world.y
        if t < 0:
            continue  # ray points away from ground, skip

        t = min(t, max_dist)
        ground_points.append(camera.position + d_world * t)

    return ground_points


# ═══════════════════════════════════════════════════════════════════════════════
# POINT-IN-POLYGON
# ═══════════════════════════════════════════════════════════════════════════════

def point_in_polygon(point: Vector3, polygon: list[Vector3]) -> bool:
    """Ray-casting point-in-polygon test. Polygon is a list of (x,z) points
    in CW or CCW order (y is ignored)."""
    x, z = point.x, point.z
    n = len(polygon)
    inside = False
    j = n - 1
    for i in range(n):
        xi, zi = polygon[i].x, polygon[i].z
        xj, zj = polygon[j].x, polygon[j].z
        if ((zi > z) != (zj > z)) and (x < (xj - xi) * (z - zi) / (zj - zi) + xi):
            inside = not inside
        j = i
    return inside


# ═══════════════════════════════════════════════════════════════════════════════
# OBSERVER CELL GRID
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class CellVisibility:
    """Precomputed visibility data for a single observer cell."""
    visible_to: list[str] = field(default_factory=list)   # camera labels
    distances: dict[str, float] = field(default_factory=dict)
    angles_deg: dict[str, float] = field(default_factory=dict)
    apparent_subject_height_px: dict[str, float] = field(default_factory=dict)


@dataclass
class ObserverCellGrid:
    """A precomputed grid of observer cells.

    Each cell stores visibility data to all cameras in the scene.
    Precomputed once per scene, lookup at runtime — O(1) per frame.
    """
    nx: int = 40                           # cells along x
    nz: int = 40                           # cells along z
    world_min: Vector3 = Vector3(0, 0, 0)  # world-space bounds (x=east, z=north)
    world_max: Vector3 = Vector3(38, 0, 42)
    cameras: list[Camera] = field(default_factory=list)
    subject_height_m: float = 1.8

    # Precomputed grid: cells[y][x] = CellVisibility
    cells: list[list[CellVisibility]] = field(init=False)

    def __post_init__(self):
        self._precompute()

    @property
    def cell_w(self) -> float:
        """Width of each cell in meters."""
        return (self.world_max.x - self.world_min.x) / self.nx

    @property
    def cell_h(self) -> float:
        """Height of each cell in meters."""
        return (self.world_max.z - self.world_min.z) / self.nz

    def cell_center(self, ix: int, iz: int, height: float = 0.0) -> Vector3:
        """World-space center of cell (ix, iz) at given height above ground."""
        return Vector3(
            self.world_min.x + (ix + 0.5) * self.cell_w,
            height,
            self.world_min.z + (iz + 0.5) * self.cell_h,
        )

    def world_to_cell(self, point: Vector3) -> tuple[int, int]:
        """Convert world coordinate to cell indices."""
        ix = int((point.x - self.world_min.x) / self.cell_w)
        iz = int((point.z - self.world_min.z) / self.cell_h)
        return max(0, min(self.nx - 1, ix)), max(0, min(self.nz - 1, iz))

    def _precompute(self) -> None:
        """Precompute visibility for every cell."""
        self.cells = [[CellVisibility() for _ in range(self.nx)] for _ in range(self.nz)]

        for iz in range(self.nz):
            for ix in range(self.nx):
                # Check visibility at waist height (subject center of mass)
                check_h = self.subject_height_m / 2.0
                center = self.cell_center(ix, iz, height=check_h)
                cell = self.cells[iz][ix]
                for cam in self.cameras:
                    dist = cam.position.distance_to(center)
                    # Range limit: skip if subject is too far for useful view
                    if dist > cam.max_range_m:
                        continue
                    if is_point_visible(cam, center):
                        cell.visible_to.append(cam.label)
                        cell.distances[cam.label] = round(dist, 2)
                        # Angle from camera to cell (horizontal)
                        rel = center - cam.position
                        angle = math.degrees(math.atan2(rel.x, rel.z)) - cam.yaw_deg
                        cell.angles_deg[cam.label] = round(angle, 1)
                        # Apparent size of a subject_height_m tall person
                        sz = apparent_size(
                            0.5, self.subject_height_m, dist,
                            cam.focal_length_mm,
                            cam.sensor_width_mm, cam.sensor_height_mm,
                            cam.resolution_width, cam.resolution_height,
                        )
                        cell.apparent_subject_height_px[cam.label] = round(sz.height_px, 1)

    def lookup(self, world_point: Vector3) -> CellVisibility:
        """O(1) lookup: get precomputed visibility for a world point."""
        ix, iz = self.world_to_cell(world_point)
        return self.cells[iz][ix]

    def active_camera(self, world_point: Vector3) -> Optional[str]:
        """Get the best camera for a given world point.

        Selection rule: among visible cameras, pick the one with the
        largest apparent subject height (most detailed view).
        Returns camera label or None if no camera sees the point.
        """
        cell = self.lookup(world_point)
        if not cell.visible_to:
            return None
        # Pick camera with largest apparent subject
        best = max(cell.visible_to,
                   key=lambda lbl: cell.apparent_subject_height_px.get(lbl, 0))
        return best


# ═══════════════════════════════════════════════════════════════════════════════
# SUBJECT MOTION
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class CircularPath:
    """A circular path in the x-z plane."""
    center: Vector3 = Vector3(19, 0, 21)
    radius_m: float = 8.5
    speed_kmh: float = 10.0       # km/h

    @property
    def speed_ms(self) -> float:
        """Speed in m/s."""
        return self.speed_kmh / 3.6

    @property
    def angular_velocity_rad_s(self) -> float:
        """Angular velocity in radians per second."""
        return self.speed_ms / self.radius_m

    def position_at(self, time_s: float, start_angle: float = 0.0) -> Vector3:
        """Get world-space position at time t (seconds from start)."""
        angle = start_angle + self.angular_velocity_rad_s * time_s
        return Vector3(
            self.center.x + self.radius_m * math.cos(angle),
            0.0,  # ground level
            self.center.z + self.radius_m * math.sin(angle),
        )

    def frame_at(self, frame: int, fps: float = 24.0,
                 start_angle: float = 0.0) -> Vector3:
        """Get world-space position at a specific frame number."""
        return self.position_at(frame / fps, start_angle)


# ═══════════════════════════════════════════════════════════════════════════════
# FRAME PROJECTION (backward-compat)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class FrameProjection:
    """Result of projecting a scene object onto the frame (backward compat)."""
    label: str
    visible: bool
    reason: str = ""
    distance_m: float = 0.0
    center_x: float = 0.0
    center_y: float = 0.0
    occ_x: float = 0.0
    occ_y: float = 0.0
    width_px: float = 0.0
    height_px: float = 0.0


def project_object(camera: Camera, obj: SceneObject) -> FrameProjection:
    """Project a scene object onto the camera frame (backward compat).

    Uses the new Camera.world_to_camera() which handles yaw/pitch/roll.
    """
    cam_center = camera.world_to_camera(obj.position)
    sensor_pt = project_to_sensor(cam_center, camera.focal_length_mm)

    if sensor_pt is None:
        return FrameProjection(label=obj.label, visible=False, reason="behind camera")

    cx, cy = sensor_to_frame(sensor_pt[0], sensor_pt[1],
                             camera.sensor_width_mm, camera.sensor_height_mm)
    dist = camera.position.distance_to(obj.position)
    sz = apparent_size(obj.width_m, obj.height_m, dist,
                       camera.focal_length_mm,
                       camera.sensor_width_mm, camera.sensor_height_mm,
                       camera.resolution_width, camera.resolution_height)

    return FrameProjection(
        label=obj.label, visible=True,
        distance_m=sz.distance_m,
        center_x=round(cx, 4),
        center_y=round(cy, 4),
        occ_x=sz.frame_occ_x,
        occ_y=sz.frame_occ_y,
        width_px=sz.width_px,
        height_px=sz.height_px,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# SCENE DESCRIBER (backward-compat)
# ═══════════════════════════════════════════════════════════════════════════════

def describe_scene(scene: Scene, top_down_extent: float = 25.0) -> str:
    """Generate a human-readable + ASCII visual description of the scene.

    Adapted to work with the new multi-camera Scene model (uses first camera).
    """
    lines: list[str] = []
    _ = lines.append

    cam = scene.cameras[0] if scene.cameras else Camera()
    _(f"╔══ SCENE: {scene.name} ══╗")
    _("")
    _("  Camera")
    _("    Position:          %s" % cam.position)
    _("    Yaw/Pitch/Roll:    %.0f° / %.0f° / %.0f°" % (cam.yaw_deg, cam.pitch_deg, cam.roll_deg))
    _("    Lens:              %.0f mm  f/%.1f" % (cam.focal_length_mm, cam.aperture))
    _("    FOV:               %.1f° (H) × %.1f° (V)" % (cam.hfov_deg, cam.vfov_deg))
    _("")

    _(f"  Objects ({len(scene.objects)})")
    _("    %-16s %-26s %-16s %8s  %10s  %10s" % (
        "Label", "Position (x,y,z) m", "Dim (W×H×D)", "Dist", "Occ %", "Screen px"))
    _("    " + "─" * 96)

    for obj in scene.objects:
        proj = project_object(cam, obj)
        if proj.visible:
            pos_str = "%7.1f,%7.1f,%7.1f" % (obj.position.x, obj.position.y, obj.position.z)
            dim_str = "%.1f×%.1f×%.1f" % (obj.width_m, obj.height_m, obj.depth_m)
            occ_str = "%.1f%% × %.1f%%" % (proj.occ_x * 100, proj.occ_y * 100)
            px_str = "%.0f × %.0f" % (proj.width_px, proj.height_px)
            _("    %-16s (%s)  %-16s  %5.2f m  %10s  %10s" % (
                obj.label, pos_str, dim_str, proj.distance_m, occ_str, px_str))
        else:
            _("    %-16s  %-26s  [%s]" % (obj.label, "BEHIND CAMERA", proj.reason))

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# FRAME ACTIVATION LOG
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class FrameActivation:
    """Result of a single frame's camera activation check."""
    frame: int
    subject_pos: Vector3
    active_cam: Optional[str]
    visible_to: list[str]


def simulate_sequence(
    path: CircularPath,
    grid: ObserverCellGrid,
    num_frames: int = 120,
    fps: float = 24.0,
    start_angle: float = 0.0,
) -> list[FrameActivation]:
    """Simulate camera activation across a sequence of frames.

    Returns a list of FrameActivation results, one per frame.
    Camera selection is pure geometry — no AI involved.
    """
    results = []
    for f in range(num_frames):
        pos = path.frame_at(f, fps, start_angle)
        cell = grid.lookup(pos)
        active = grid.active_camera(pos)
        results.append(FrameActivation(
            frame=f,
            subject_pos=pos,
            active_cam=active,
            visible_to=cell.visible_to.copy(),
        ))
    return results
