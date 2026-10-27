# stl-viewer

A small self-hosted web app for looking at STL files before you print them.
Drop a file in the browser, orbit it on a print-bed grid, and see its triangle
count, size, volume and whether it fits your bed. Every upload is kept so you
can reopen or download it later, and scripts can push models in over HTTP.

Pure WebGL in the browser; the server is Python's standard library plus numpy.

## Run

    python -m venv .venv && .venv/bin/pip install -r requirements.in
    .venv/bin/python app.py            # http://localhost:8765

or with Docker: `docker compose up -d --build` (uploads land in `./data`).

| Variable | Default | Meaning |
|---|---|---|
| `PORT` / `HOST` | `8765` / `0.0.0.0` | listen address |
| `UPLOAD_DIR` | `./uploads` | where uploads are kept |
| `BED_X` `BED_Y` `BED_Z` | `220` `220` `250` | build volume in mm (Ender 3 V2) |

## API

    curl -F file=@part.stl http://localhost:8765/api/models   # upload, returns stats
    curl http://localhost:8765/api/models                     # list stored models

Uploads are never overwritten or deleted by the app (a timestamp prefix keeps
each one), and files that don't parse as STL are rejected, not stored.

## Test

    .venv/bin/pip install -r requirements-dev.in && .venv/bin/python -m pytest

There is no authentication: run it on a trusted network or behind a reverse proxy.

Extracted from [PrinterFixer_AI](https://github.com/yvescl/PrinterFixer_AI). MIT licensed.
