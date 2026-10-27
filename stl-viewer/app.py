#!/usr/bin/env python3
"""STL viewer: drop an STL in the browser, orbit it on a print-bed grid, see its
size / volume / whether it fits, and keep every upload so it can be reopened.

    python app.py                 # http://localhost:8765

Environment: PORT, HOST, UPLOAD_DIR, BED_X / BED_Y / BED_Z (mm).

Routes
    GET  /                  the viewer
    GET  /config.json       bed size, for the grid and the fit badge
    GET  /healthz           liveness probe
    GET  /api/models        JSON list of stored STLs with geometry stats
    POST /api/models        upload for scripts (raw body or `curl -F file=@x.stl`)
    POST /model/stl?name=   upload from the page; answers with the mesh blob
    GET  /model/data?name=  mesh blob of a stored STL
    GET  /model/file?name=  original stored STL (download)
"""
import json
import os
import re
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import stlmodel

HERE = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(HERE, "web")
UPLOAD_DIR = os.environ.get("UPLOAD_DIR", os.path.join(HERE, "uploads"))
MAX_UPLOAD = 200 * 1024 * 1024          # bytes; a 200 MB STL is already absurd


def save_upload(name, raw):
    """Persist an upload. Never overwrites: a timestamp prefix keeps every one."""
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", os.path.basename(name)) or "model.stl"
    if not safe.lower().endswith(".stl"):
        safe += ".stl"
    path = os.path.join(UPLOAD_DIR, datetime.now().strftime("%Y%m%d-%H%M%S_") + safe)
    with open(path, "wb") as fh:
        fh.write(raw)
    return path


def display_name(name):
    """Drop the save timestamp prefix for a readable label."""
    return re.sub(r"^\d{8}-\d{6}_", "", name)


def multipart_file(body, content_type):
    """Pull the first file part out of a multipart/form-data body so
    `curl -F file=@model.stl` works. Returns (filename, bytes), or ("", body)
    when the body is not multipart. Only the delimiter CRLF is trimmed, so
    binary STLs ending in 0x0d/0x0a survive intact."""
    m = re.search(r'boundary=("?)([^";]+)\1', content_type or "")
    if not m:
        return "", body
    delim = b"--" + m.group(2).encode()
    for section in body.split(delim):
        if section[:2] == b"\r\n":
            section = section[2:]
        head, sep, rest = section.partition(b"\r\n\r\n")
        if not sep or b"filename=" not in head:
            continue
        fm = re.search(rb'filename="([^"]*)"', head)
        fname = fm.group(1).decode("utf-8", "ignore") if fm else ""
        if rest.endswith(b"\r\n"):
            rest = rest[:-2]
        return fname, rest
    return "", body


_stats_cache = {}
_stats_lock = threading.Lock()


def _stored_stats(path):
    """Stats for a stored STL, cached by (name, mtime) so listing is cheap."""
    key = os.path.basename(path)
    try:
        token = str(os.stat(path).st_mtime)
    except OSError:
        return {"error": "unreadable"}
    with _stats_lock:
        hit = _stats_cache.get(key)
        if hit and hit[0] == token:
            return hit[1]
    try:
        with open(path, "rb") as fh:
            _v, s = stlmodel.parse_stl(fh.read())
        out = {k: s[k] for k in ("triangles", "size_xyz", "size_mm", "volume_cm3", "fits_bed")}
    except Exception as exc:
        out = {"error": str(exc)}
    with _stats_lock:
        _stats_cache[key] = (token, out)
    return out


def stored_models():
    """Every stored STL, newest first."""
    try:
        names = os.listdir(UPLOAD_DIR)
    except OSError:
        return []
    out = []
    for n in names:
        p = os.path.join(UPLOAD_DIR, n)
        if not n.lower().endswith(".stl") or not os.path.isfile(p):
            continue
        st = os.stat(p)
        rec = {"stored": n, "name": display_name(n), "bytes": st.st_size,
               "uploaded": datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds")}
        rec.update(_stored_stats(p))
        out.append(rec)
    out.sort(key=lambda r: r["uploaded"], reverse=True)
    return out


def stored_path(name):
    """Path of a stored STL by name; basename() keeps it inside UPLOAD_DIR."""
    name = os.path.basename(name or "")
    p = os.path.join(UPLOAD_DIR, name)
    return (name, p) if name.lower().endswith(".stl") and os.path.isfile(p) else (name, None)


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json", extra=None):
        if isinstance(body, str):
            body = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code, obj):
        self._send(code, json.dumps(obj))

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0) or 0)
        if length > MAX_UPLOAD:
            return None
        return self.rfile.read(length)

    def do_GET(self):
        url = urlparse(self.path)
        qs = parse_qs(url.query)
        if url.path in ("/", "/index.html"):
            with open(os.path.join(WEB_DIR, "index.html"), "rb") as fh:
                self._send(200, fh.read(), "text/html; charset=utf-8")
        elif url.path == "/config.json":
            self._json(200, {"bed": [stlmodel.BED_X, stlmodel.BED_Y, stlmodel.BED_Z]})
        elif url.path == "/healthz":
            self._json(200, {"ok": True})
        elif url.path == "/api/models":
            self._json(200, {"ok": True, "models": stored_models()})
        elif url.path in ("/model/data", "/model/file"):
            name, src = stored_path((qs.get("name") or [""])[0])
            if not src:
                return self._json(404, {"error": "not found"})
            with open(src, "rb") as fh:
                raw = fh.read()
            if url.path == "/model/file":
                return self._send(200, raw, "model/stl", {
                    "Content-Disposition": f'attachment; filename="{display_name(name)}"'})
            try:
                blob, _ = stlmodel.stl_blob(raw, display_name(name))
            except Exception as exc:
                return self._json(500, {"error": str(exc)})
            self._send(200, blob, "application/octet-stream")
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self):
        url = urlparse(self.path)
        if url.path not in ("/api/models", "/model/stl"):
            return self._json(404, {"error": "not found"})
        qs = parse_qs(url.query)
        body = self._read_body()
        if body is None:
            return self._json(413, {"ok": False, "error": "upload too large"})
        name = (qs.get("name") or [""])[0]
        raw = body
        if (self.headers.get("Content-Type") or "").startswith("multipart/form-data"):
            fname, raw = multipart_file(body, self.headers.get("Content-Type"))
            name = name or fname
        name = name or "model.stl"
        if not raw:
            return self._json(400, {"ok": False, "error": "empty upload"})
        try:
            blob, stats = stlmodel.stl_blob(raw, display_name(os.path.basename(name)))
        except Exception as exc:
            return self._json(400, {"ok": False, "error": str(exc)})
        saved = os.path.basename(save_upload(name, raw))      # only files that parsed
        if url.path == "/model/stl":
            return self._send(200, blob, "application/octet-stream")
        self._json(200, {"ok": True, "name": display_name(os.path.basename(name)),
                         "saved": saved, **stats})

    def log_message(self, fmt, *args):
        print(f"{self.address_string()} {fmt % args}", flush=True)


def main():
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", 8765))
    print(f"STL viewer on http://{host}:{port}  (uploads: {UPLOAD_DIR})", flush=True)
    ThreadingHTTPServer((host, port), Handler).serve_forever()


if __name__ == "__main__":
    main()
