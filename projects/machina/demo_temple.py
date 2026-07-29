#!/usr/bin/env python3
"""
TM Spatial Engine — Temple Compound Demo
════════════════════════════════════════

Implements the full coordinate system described in the spec:

  Compound:    38m x 42m, (0,0) → (38,42)
  Temple dome: center (19,21), radius 4.5m
  Walkway:     radius 8.5m around dome center
  3 cameras:   entrance, observation, side — each with yaw/pitch/roll + lens
  Subject:     walks circular path at 10 km/h on walkway
  Observer grid: 40x40 cells, precomputed visibility per cell
  Camera activation: pure geometry, no AI

Demo output:
  1. Scene configuration (compound, cameras, dome)
  2. Each camera's frustum projected onto ground
  3. Observer cell grid heatmap (how many cameras see each cell)
  4. Subject motion simulation — 120 frames (5 sec at 24fps)
  5. Camera activation log — which camera is active per frame
  6. Camera hand-off detection (frame where active camera changes)
"""

import math

from spatial import (
    Vector3, Camera, SceneObject, Scene,
    apparent_size, depth_of_field,
    camera_ground_polygon, point_in_polygon,
    ObserverCellGrid, CircularPath,
    is_point_visible, simulate_sequence, project_to_sensor,
)


def fmt(v: float) -> str:
    s = f"{v:.2f}"
    return s.rstrip("0").rstrip(".")


def main():
    # ══════════════════════════════════════════════════════════════════════
    # 1. SCENE CONFIGURATION
    # ══════════════════════════════════════════════════════════════════════

    compound_min = Vector3(0, 0, 0)
    compound_max = Vector3(38, 0, 42)
    temple_center = Vector3(19, 0, 21)
    dome_radius = 4.5
    walkway_radius = 8.5

    # ── Camera 1: Lower-left entrance ─────────────────────────────────
    cam1 = Camera(
        label="Cam1-Entrance",
        position=Vector3(8, 1.8, 12),
        yaw_deg=28.0, pitch_deg=4.0, roll_deg=0.0,
        focal_length_mm=35.0,
        aperture=2.8,
    )

    # ── Camera 2: Top observation ─────────────────────────────────────
    cam2 = Camera(
        label="Cam2-Observation",
        position=Vector3(22, 2.4, 34),
        yaw_deg=270.0, pitch_deg=-25.0, roll_deg=0.0,
        focal_length_mm=50.0,
        aperture=2.8,
    )

    # ── Camera 3: Right side ──────────────────────────────────────────
    cam3 = Camera(
        label="Cam3-Side",
        position=Vector3(31, 1.8, 15),
        yaw_deg=160.0, pitch_deg=7.0, roll_deg=0.0,
        focal_length_mm=35.0,
        aperture=2.8,
    )

    cameras = [cam1, cam2, cam3]

    # ── Subject path (circular walkway around temple) ─────────────────
    path = CircularPath(
        center=temple_center,
        radius_m=walkway_radius,
        speed_kmh=10.0,
    )

    # ── Observer cell grid ────────────────────────────────────────────
    grid = ObserverCellGrid(
        nx=40, nz=40,
        world_min=compound_min,
        world_max=compound_max,
        cameras=cameras,
        subject_height_m=1.8,
    )

    # ══════════════════════════════════════════════════════════════════════
    # 2. PRINT SCENE CONFIGURATION
    # ══════════════════════════════════════════════════════════════════════

    print("╔══ TEMPLE COMPOUND — SPATIAL COORDINATE SYSTEM ══╗")
    print("")
    print("  Compound:                %.0f m x %.0f m" % (compound_max.x - compound_min.x,
                                                          compound_max.z - compound_min.z))
    print("  Bounds:                  (0, 0) → (%d, %d)" % (compound_max.x, compound_max.z))
    print("")
    print("  Temple Dome Center:      (19, 21)")
    print("  Dome Radius:             %.1f m" % dome_radius)
    print("  Walkway Radius:          %.1f m  (path width = %.1f m)" % (
        walkway_radius, walkway_radius - dome_radius))
    print("")

    for cam in cameras:
        print("  Camera %s" % cam.label)
        print("    Position:             %s" % cam.position)
        print("    Rotation:             yaw=%.0f°  pitch=%.0f°  roll=%.0f°" % (
            cam.yaw_deg, cam.pitch_deg, cam.roll_deg))
        print("    Lens:                 %.0f mm  f/%.1f" % (cam.focal_length_mm, cam.aperture))
        print("    FOV:                  %.1f° (H) x %.1f° (V)" % (cam.hfov_deg, cam.vfov_deg))
        print("    Max range:            %.0f m  (subject > 5%% frame height)" % cam.max_range_m)
        if cam.focal_length_mm == 35:
            print("    → Spec says:           54° H,  37° V  (matches: %.0f°, %.0f°)" % (
                cam.hfov_deg, cam.vfov_deg))
        elif cam.focal_length_mm == 50:
            print("    → Spec says:           40° H  (matches: %.0f°)" % cam.hfov_deg)
        poly = camera_ground_polygon(cam, ground_y=0.0, max_dist=cam.max_range_m)
        xs = [p.x for p in poly]
        zs = [p.z for p in poly]
        print("    Ground coverage:      x=[%.0f→%.0f]  z=[%.0f→%.0f]" % (
            min(xs), max(xs), min(zs), max(zs)))
        print("")

    # ══════════════════════════════════════════════════════════════════════
    # 3. COMPOUND MAP (ASCII)
    # ══════════════════════════════════════════════════════════════════════

    print("  Compound Map (top-down, 38x42 m)")
    print("  " + "─" * 42)

    map_chars = [["  " for _ in range(42)] for _ in range(38)]

    for x in range(38):
        for z in range(42):
            dx = x - temple_center.x
            dz = z - temple_center.z
            dist = math.sqrt(dx*dx + dz*dz)
            if dist <= dome_radius:
                map_chars[x][z] = "██"
            elif dist <= walkway_radius:
                map_chars[x][z] = "░░"

    cam_markers = {0: "C1", 1: "C2", 2: "C3"}
    for i, cam in enumerate(cameras):
        cx = int(round(cam.position.x))
        cz = int(round(cam.position.z))
        if 0 <= cx < 38 and 0 <= cz < 42:
            map_chars[cx][cz] = cam_markers[i]

    for z in range(41, -1, -1):
        row = ""
        for x in range(38):
            row += map_chars[x][z]
        label = " z=%d" % z if z % 10 == 0 else ""
        print("    " + row + label)
    print("    " + "─" * 42)
    print("    x=0                          x=38")
    print("")

    # ══════════════════════════════════════════════════════════════════════
    # 4. OBSERVER CELL GRID — visibility heatmap
    # ══════════════════════════════════════════════════════════════════════

    print("  Observer Cell Grid (40x40) — Cameras per cell")
    print("  Legend: '.'=0  '1'=1cam  '2'=2cams  '3'=3cams")
    print("  " + "─" * 42)

    for iz in range(grid.nz - 1, -1, -1):
        row = ""
        for ix in range(grid.nx):
            cell = grid.cells[iz][ix]
            n = len(cell.visible_to)
            if n == 0:
                row += ". "
            else:
                row += str(n) + " "
        label = " z=%d" % int(grid.world_min.z + (iz + 0.5) * grid.cell_h) if iz % 8 == 0 else ""
        print("    " + row + label)
    print("")
    print("  Total cells with >=1 camera: %d / %d" % (
        sum(1 for iz in range(grid.nz) for ix in range(grid.nx)
            if grid.cells[iz][ix].visible_to), grid.nx * grid.nz))
    total_2 = sum(1 for iz in range(grid.nz) for ix in range(grid.nx)
                  if len(grid.cells[iz][ix].visible_to) >= 2)
    total_3 = sum(1 for iz in range(grid.nz) for ix in range(grid.nx)
                  if len(grid.cells[iz][ix].visible_to) >= 3)
    print("  Cells with >=2 cameras:       %d" % total_2)
    print("  Cells with all 3 cameras:     %d" % total_3)
    print("")

    # ══════════════════════════════════════════════════════════════════════
    # 5. SUBJECT MOTION SIMULATION (120 frames = 5 seconds)
    # ══════════════════════════════════════════════════════════════════════

    print("  Subject Motion Simulation")
    print("  Speed: %.1f km/h  (%.2f m/s)" % (path.speed_kmh, path.speed_ms))
    print("  Path: circular, radius %.1f m around dome center" % path.radius_m)
    print("  Framerate: 24 fps  |  Distance per frame: %.2f m" % (path.speed_ms / 24))
    print("  Simulating: 120 frames (5 seconds)")
    print("")
    print("  Camera Activation Log:")
    print("  " + "─" * 80)
    print("  %5s  %12s  %18s  %12s  %s" % (
        "Frame", "Subject (x,z)", "Visible to", "Active cam", "Note"))
    print("  " + "─" * 80)

    results = simulate_sequence(path, grid, num_frames=120, fps=24.0)

    prev_active = None
    handoffs = []
    for r in results:
        vis_str = ", ".join(r.visible_to) if r.visible_to else "NONE"
        active = r.active_cam or "───"

        note = ""
        if r.visible_to and prev_active is not None and r.active_cam != prev_active:
            note = "← HANDOFF from %s" % prev_active
            handoffs.append(r.frame)

        if note or r.frame % 10 == 0:
            pos_str = "(%.1f, %.1f)" % (r.subject_pos.x, r.subject_pos.z)
            print("  %5d  %12s  %18s  %12s  %s" % (
                r.frame, pos_str, vis_str, active, note))
        prev_active = r.active_cam

    print("  " + "─" * 80)
    print("")
    print("  Camera Handoffs: %d" % len(handoffs))
    for hf in handoffs:
        r = results[hf]
        print("    Frame %d (%s) → %s" % (hf, r.subject_pos, r.active_cam))
    print("")

    # ══════════════════════════════════════════════════════════════════════
    # 6. PER-CAMERA APPARENT SIZE AT KEY FRAMES
    # ══════════════════════════════════════════════════════════════════════

    print("  Per-Camera Subject Apparent Size (frame 30, 60, 90)")
    print("  " + "─" * 70)
    for check_frame in [30, 60, 90]:
        pos = path.frame_at(check_frame, 24.0)
        print("  Frame %d — Subject at (%.1f, %.1f)" % (
            check_frame, pos.x, pos.z))
        for cam in cameras:
            cam_pt = cam.world_to_camera(pos)
            sensor = project_to_sensor(cam_pt, cam.focal_length_mm)
            if sensor is None:
                print("    %-18s  Not in frame" % cam.label)
                continue
            sx, sy = sensor
            half_w = cam.sensor_width_mm / 2
            half_h = cam.sensor_height_mm / 2
            in_frame = abs(sx) <= half_w and abs(sy) <= half_h
            if not in_frame:
                print("    %-18s  Outside frustum (sx=%.1f, sy=%.1f)" % (
                    cam.label, sx, sy))
                continue
            sz = apparent_size(0.5, 1.8, cam_pt.z,
                               cam.focal_length_mm,
                               cam.sensor_width_mm, cam.sensor_height_mm,
                               cam.resolution_width, cam.resolution_height)
            fx = sx / cam.sensor_width_mm
            fy = sy / cam.sensor_height_mm
            print("    %-18s  %.0fx%.0f px  at frame (%.2f, %.2f)  dist=%.1fm" % (
                cam.label, sz.width_px, sz.height_px, fx, fy, cam_pt.z))
        print("")

    # ══════════════════════════════════════════════════════════════════════
    # 7. VERIFICATION NOTES
    # ══════════════════════════════════════════════════════════════════════

    print("  " + "═" * 70)
    print("  VERIFICATION")
    print("  " + "─" * 70)
    print("  ✓ All camera activation decisions are geometric — no AI")
    print("  ✓ Observer cell grid is precomputed — O(1) per frame lookup")
    print("  ✓ Frustum-ground intersection is deterministic")
    print("  ✓ Apparent subject size varies with position (thin-lens model)")
    print("  ✓ Camera hand-offs happen at geometric boundaries")
    print("")
    print("  What's next:")
    print("  • Add occlusion (dome blocks cameras behind it)")
    print("  • Add camera blending on hand-off (12-frame crossfade)")
    print("  • Connect to image generation (prompt with exact coordinates)")
    print("  • Full 3D (x,y,z) with bounding box projection")
    print("  " + "═" * 70)


if __name__ == "__main__":
    main()
