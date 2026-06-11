"""Serve the SimpleBrain mobile web UI as static files via FastAPI."""
from __future__ import annotations
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse


def mount_ui(app: FastAPI, ui_dir: Path | None = None) -> None:
    """Mount the ui/ directory on /ui and redirect / to index.html."""
    if ui_dir is None:
        ui_dir = Path(__file__).parent.parent.parent / "ui"

    if not ui_dir.exists():
        return

    app.mount("/ui", StaticFiles(directory=str(ui_dir), html=True), name="ui")

    @app.get("/")
    def _root():
        index = ui_dir / "index.html"
        if index.exists():
            return FileResponse(str(index))
        return {"message": "SimpleBrain API", "docs": "/docs"}
