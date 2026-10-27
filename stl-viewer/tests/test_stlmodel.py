"""STL parsing (binary + ASCII, stats, blob layout) and the web app's routes."""
import json
import struct
import threading
from http.server import ThreadingHTTPServer

import pytest
import requests

import app
from stlmodel import parse_stl, stl_blob

TIMEOUT = 15


def _box_triangles(sx, sy, sz):
    """12 triangles of an axis-aligned box from the origin to (sx, sy, sz)."""
    v = {
        "000": (0, 0, 0), "100": (sx, 0, 0), "110": (sx, sy, 0), "010": (0, sy, 0),
        "001": (0, 0, sz), "101": (sx, 0, sz), "111": (sx, sy, sz), "011": (0, sy, sz),
    }
    faces = [
        ("000", "110", "100"), ("000", "010", "110"),   # bottom
        ("001", "101", "111"), ("001", "111", "011"),   # top
        ("000", "100", "101"), ("000", "101", "001"),   # front
        ("010", "011", "111"), ("010", "111", "110"),   # back
        ("000", "001", "011"), ("000", "011", "010"),   # left
        ("100", "110", "111"), ("100", "111", "101"),   # right
    ]
    return [[v[a], v[b], v[c]] for a, b, c in faces]


def _binary_stl(tris):
    out = [b"\0" * 80, struct.pack("<I", len(tris))]
    for t in tris:
        out.append(struct.pack("<3f", 0, 0, 0))            # normal (ignored)
        for pt in t:
            out.append(struct.pack("<3f", *pt))
        out.append(struct.pack("<H", 0))                   # attribute bytes
    return b"".join(out)


def _ascii_stl(tris):
    lines = ["solid test"]
    for t in tris:
        lines.append("facet normal 0 0 0")
        lines.append("  outer loop")
        for pt in t:
            lines.append(f"    vertex {pt[0]} {pt[1]} {pt[2]}")
        lines.append("  endloop")
        lines.append("endfacet")
    lines.append("endsolid test")
    return ("\n".join(lines)).encode()


def test_binary_cube_stats():
    verts, stats = parse_stl(_binary_stl(_box_triangles(20, 20, 20)))
    assert stats["triangles"] == 12
    assert stats["size_xyz"] == [20.0, 20.0, 20.0]
    assert stats["volume_cm3"] == pytest.approx(8.0, abs=0.01)   # 20^3 mm3 = 8 cm3
    assert stats["fits_bed"] is True


def test_ascii_cube_matches_binary():
    _, a = parse_stl(_ascii_stl(_box_triangles(20, 20, 20)))
    assert a["triangles"] == 12
    assert a["size_xyz"] == [20.0, 20.0, 20.0]
    assert a["volume_cm3"] == pytest.approx(8.0, abs=0.01)


def test_oversized_model_flagged_over_bed():
    _, stats = parse_stl(_binary_stl(_box_triangles(300, 50, 50)))
    assert stats["fits_bed"] is False          # 300mm > 220mm bed


def test_blob_header_and_arrays():
    blob, stats = stl_blob(_binary_stl(_box_triangles(10, 10, 10)), name="cube.stl")
    hl = struct.unpack_from("<I", blob, 0)[0]
    head = json.loads(blob[4:4 + hl])
    assert head["name"] == "cube.stl"
    assert head["n_vert"] == 12 * 3
    # header + positions(9 f32/tri) + normals(9 f32/tri)
    floats = 12 * 9 * 2
    assert len(blob) == 4 + hl + floats * 4


def test_garbage_raises():
    with pytest.raises(ValueError):
        parse_stl(b"this is not an STL file at all")


# ---- programmatic upload API (POST /api/models) -------------------------
@pytest.fixture(scope="module")
def api(tmp_path_factory):
    up = tmp_path_factory.mktemp("stl_uploads")
    old = app.UPLOAD_DIR
    app.UPLOAD_DIR = str(up)
    srv = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}", up
    srv.shutdown()
    app.UPLOAD_DIR = old


def test_api_upload_raw_body(api):
    base, up = api
    stl = _binary_stl(_box_triangles(30, 40, 50))
    r = requests.post(base + "/api/models?name=part.stl", data=stl, timeout=TIMEOUT)
    assert r.status_code == 200
    j = r.json()
    assert j["ok"] is True
    assert j["triangles"] == 12
    assert j["size_xyz"] == [30.0, 40.0, 50.0]
    assert j["fits_bed"] is True
    assert j["saved"].endswith("part.stl")
    assert any(p.name.endswith("part.stl") for p in up.iterdir())    # kept on disk


def test_api_upload_multipart(api):
    base, _ = api
    stl = _binary_stl(_box_triangles(10, 10, 10))
    r = requests.post(base + "/api/models",
                      files={"file": ("cube.stl", stl, "application/sla")},
                      timeout=TIMEOUT)
    assert r.status_code == 200
    j = r.json()
    assert j["ok"] is True and j["triangles"] == 12
    assert j["saved"].endswith("cube.stl")


def test_api_upload_rejects_garbage(api):
    base, up = api
    before = len(list(up.iterdir()))
    r = requests.post(base + "/api/models?name=bad.stl",
                      data=b"definitely not an stl", timeout=TIMEOUT)
    assert r.status_code == 400
    assert r.json()["ok"] is False
    assert len(list(up.iterdir())) == before          # garbage is not stored


def test_api_list_and_fetch_saved(api):
    base, _ = api
    stl = _binary_stl(_box_triangles(15, 15, 15))
    up = requests.post(base + "/api/models?name=listme.stl", data=stl, timeout=TIMEOUT).json()
    stored = up["saved"]
    # it appears in the list, with cached geometry stats
    lst = requests.get(base + "/api/models", timeout=TIMEOUT).json()
    assert lst["ok"] is True
    match = [m for m in lst["models"] if m["stored"] == stored]
    assert match and match[0]["triangles"] == 12 and match[0]["fits_bed"] is True
    assert match[0]["name"] == "listme.stl"
    # and its mesh blob can be fetched back for the viewer
    r = requests.get(base + "/model/data", params={"name": stored}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.headers["Content-Type"].startswith("application/octet-stream")
    hl = struct.unpack_from("<I", r.content, 0)[0]
    assert json.loads(r.content[4:4 + hl])["triangles"] == 12


def test_model_data_missing_is_404(api):
    base, _ = api
    r = requests.get(base + "/model/data", params={"name": "nope.stl"}, timeout=TIMEOUT)
    assert r.status_code == 404


def test_index_is_the_viewer(api):
    base, _ = api
    r = requests.get(base + "/", timeout=TIMEOUT)
    assert r.status_code == 200
    assert "STL Viewer" in r.text and "text/html" in r.headers["Content-Type"]


def test_config_and_health(api):
    base, _ = api
    assert requests.get(base + "/config.json", timeout=TIMEOUT).json()["bed"] == [220.0, 220.0, 250.0]
    assert requests.get(base + "/healthz", timeout=TIMEOUT).json() == {"ok": True}


def test_download_returns_original_bytes(api):
    base, _ = api
    stl = _binary_stl(_box_triangles(12, 12, 12))
    stored = requests.post(base + "/api/models?name=dl.stl", data=stl, timeout=TIMEOUT).json()["saved"]
    r = requests.get(base + "/model/file", params={"name": stored}, timeout=TIMEOUT)
    assert r.status_code == 200 and r.content == stl
    assert 'filename="dl.stl"' in r.headers["Content-Disposition"]


def test_path_traversal_is_contained(api):
    base, _ = api
    r = requests.get(base + "/model/file", params={"name": "../../etc/passwd.stl"}, timeout=TIMEOUT)
    assert r.status_code == 404
