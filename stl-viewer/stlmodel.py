"""Parse STL meshes (binary and ASCII) into triangle geometry for the browser
viewer, plus a small stats report. numpy does the heavy lifting."""
import json
import os
import struct

import numpy as np

# Build volume (mm) used to judge "fits on bed". Defaults to an Ender 3 V2;
# override with BED_X / BED_Y / BED_Z.
BED_X = float(os.environ.get("BED_X", 220))
BED_Y = float(os.environ.get("BED_Y", 220))
BED_Z = float(os.environ.get("BED_Z", 250))


def _looks_binary(raw):
    """Binary STL detection. An ASCII file starts with 'solid', but so can some
    binary writers, so trust the exact size match (80B header + u32 count +
    50B/triangle) over the magic word."""
    if len(raw) < 84:
        return False
    if raw[:5].lower() == b"solid":
        ntri = struct.unpack_from("<I", raw, 80)[0]
        return len(raw) == 84 + ntri * 50
    return True


def _parse_binary(raw):
    ntri = struct.unpack_from("<I", raw, 80)[0]
    # Don't trust the count blindly - clamp to what the buffer can hold.
    avail = (len(raw) - 84) // 50
    ntri = max(0, min(ntri, avail))
    # 50 bytes/triangle: normal (3 f32) + 3 vertices (3x3 f32) + 2-byte attr.
    dt = np.dtype([("n", "<f4", (3,)), ("v", "<f4", (3, 3)), ("attr", "<u2")])
    data = np.frombuffer(raw, dtype=dt, count=ntri, offset=84)
    return np.ascontiguousarray(data["v"], dtype=np.float32)


def _parse_ascii(raw):
    verts = []
    for line in raw.decode("utf-8", "ignore").splitlines():
        p = line.split()
        if len(p) == 4 and p[0] == "vertex":
            try:
                verts.append((float(p[1]), float(p[2]), float(p[3])))
            except ValueError:
                continue
    a = np.asarray(verts, dtype=np.float32)
    if a.shape[0] < 3:
        return np.empty((0, 3, 3), dtype=np.float32)
    a = a[: a.shape[0] - a.shape[0] % 3]        # whole triangles only
    return a.reshape(-1, 3, 3)


def parse_stl(raw):
    """Return (verts, stats). verts is an (N, 3, 3) float32 array of triangle
    corners in mm. Raises ValueError if no triangles are found."""
    if isinstance(raw, str):
        raw = raw.encode("utf-8", "ignore")
    verts = _parse_binary(raw) if _looks_binary(raw) else _parse_ascii(raw)
    if verts.shape[0] == 0:
        raise ValueError("no triangles found - not a valid STL?")
    return verts, _stats(verts)


def _stats(verts):
    pts = verts.reshape(-1, 3)
    lo = pts.min(axis=0)
    hi = pts.max(axis=0)
    size = hi - lo
    # Enclosed volume via the divergence theorem: sum(v0 . (v1 x v2)) / 6.
    v0, v1, v2 = verts[:, 0], verts[:, 1], verts[:, 2]
    vol_mm3 = float(abs(np.einsum("ij,ij->i", v0, np.cross(v1, v2)).sum()) / 6.0)
    fits = bool(size[0] <= BED_X and size[1] <= BED_Y and size[2] <= BED_Z)
    return {
        "triangles": int(verts.shape[0]),
        "bbox_min": [round(float(x), 3) for x in lo],
        "bbox_max": [round(float(x), 3) for x in hi],
        "size_xyz": [round(float(x), 2) for x in size],
        "size_mm": " x ".join(f"{x:.1f}" for x in size) + " mm",
        "volume_cm3": round(vol_mm3 / 1000.0, 2),
        "bed": [BED_X, BED_Y, BED_Z],
        "fits_bed": fits,
    }


def stl_blob(raw, name=""):
    """(blob, stats) for the browser viewer.

    Blob layout mirrors parse_gcode_paths:
        <u4 header-len><json header (space-padded to 4)><pos f32><normal f32>
    Positions and per-vertex normals are both 9 floats per triangle
    (3 vertices x xyz); the normal is the face normal repeated per vertex.
    """
    verts, stats = parse_stl(raw)
    e1 = verts[:, 1] - verts[:, 0]
    e2 = verts[:, 2] - verts[:, 0]
    fn = np.cross(e1, e2)
    ln = np.linalg.norm(fn, axis=1, keepdims=True)
    ln[ln == 0] = 1.0
    fn = (fn / ln).astype(np.float32)
    norms = np.repeat(fn[:, None, :], 3, axis=1)         # (N, 3, 3)

    pos = np.ascontiguousarray(verts, dtype="<f4").ravel()
    nrm = np.ascontiguousarray(norms, dtype="<f4").ravel()

    header = dict(stats)
    header["name"] = name
    header["n_vert"] = int(verts.shape[0] * 3)
    hjson = json.dumps(header).encode()
    hjson += b" " * (-len(hjson) % 4)                    # keep floats 4-aligned
    blob = struct.pack("<I", len(hjson)) + hjson + pos.tobytes() + nrm.tobytes()
    return blob, stats
