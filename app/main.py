from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .catalog import CatalogRepository
from .engine import ConsumerGraphEngine
from .models import ChangeRequest, WritebackRequest
from .writeback import save_writeback

ROOT = Path(__file__).resolve().parents[1]
catalog = CatalogRepository(ROOT / "data" / "demo_graph.json")
engine = ConsumerGraphEngine(catalog)

app = FastAPI(title="ConsumerGraph", version="0.1.0")
app.mount("/static", StaticFiles(directory=ROOT / "app" / "static"), name="static")


@app.get("/")
def index():
    return FileResponse(ROOT / "app" / "static" / "index.html")


@app.get("/api/health")
def health():
    return {"status": "ok", "mode": "deterministic-demo"}


@app.get("/api/assets")
def assets():
    return [asset.model_dump(exclude={"queries"}) for asset in catalog.catalog.assets]


@app.get("/api/assets/{asset_id}/convergence")
def convergence(asset_id: str):
    try:
        return engine.convergence(asset_id)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc


@app.get("/api/assets/{asset_id}/contract")
def contract(asset_id: str):
    try:
        return engine.infer_contract(asset_id)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc


@app.post("/api/change/analyze")
def analyze(request: ChangeRequest):
    try:
        return engine.analyze_change(request)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.post("/api/change/writeback")
def writeback(request: WritebackRequest):
    try:
        return save_writeback(request.analysis, ROOT / "runtime")
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(500, str(exc)) from exc

