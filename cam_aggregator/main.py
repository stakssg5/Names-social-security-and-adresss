from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from fastapi import Depends, FastAPI, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import or_

from .db import Base, engine, get_db
from .models import Agency, Camera

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
FEEDS_DIR = BASE_DIR / "feeds"
FEEDS_JSON = FEEDS_DIR / "public_feeds.json"

app = FastAPI(title="Public Webcam Aggregator", version="0.1.0")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

try:
    from fastapi.templating import Jinja2Templates  # type: ignore
except Exception:  # pragma: no cover
    Jinja2Templates = None  # type: ignore

templates = Jinja2Templates(directory=str(TEMPLATES_DIR)) if Jinja2Templates else None


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    _seed_database_if_empty()


def _seed_database_if_empty() -> None:
    if not FEEDS_JSON.exists():
        return
    db = next(get_db())
    try:
        agency_count = db.query(Agency).count()
        camera_count = db.query(Camera).count()
        if agency_count > 0 or camera_count > 0:
            return
        import json
        data = json.loads(FEEDS_JSON.read_text(encoding="utf-8"))
        agencies_by_slug: dict[str, Agency] = {}
        for entry in data:
            agency_name: str = entry.get("agency", "Unknown Agency").strip()
            agency_slug: str = entry.get("agency_slug") or agency_name.lower().replace(" ", "-")
            if agency_slug not in agencies_by_slug:
                agency = Agency(name=agency_name, slug=agency_slug)
                db.add(agency)
                db.flush()
                agencies_by_slug[agency_slug] = agency
            else:
                agency = agencies_by_slug[agency_slug]
            camera = Camera(
                name=entry.get("name", "Unnamed Camera").strip(),
                location=entry.get("location", "").strip() or None,
                stream_url=entry.get("stream_url", "").strip(),
                stream_type=(entry.get("stream_type", "hls").strip() or "hls").lower(),
                agency_id=agency.id,
            )
            db.add(camera)
        db.commit()
    finally:
        db.close()


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/cameras")
def search_cameras(
    q: Optional[str] = Query(default=None, description="Free-text search across name, agency, location"),
    db: Session = Depends(get_db),
):
    query = db.query(Camera).join(Agency)
    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                Camera.name.ilike(like),
                Camera.location.ilike(like),
                Agency.name.ilike(like),
                Agency.slug.ilike(like),
            )
        )
    query = query.order_by(Agency.name.asc(), Camera.name.asc())
    items: List[Camera] = query.all()
    return [
        {
            "id": c.id,
            "name": c.name,
            "location": c.location,
            "stream_url": c.stream_url,
            "stream_type": c.stream_type,
            "agency": {
                "id": c.agency.id,
                "name": c.agency.name,
                "slug": c.agency.slug,
            },
        }
        for c in items
    ]


@app.get("/cameras/{camera_id}", response_class=HTMLResponse)
def camera_view(camera_id: int, request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    camera: Optional[Camera] = db.query(Camera).filter(Camera.id == camera_id).first()
    if not camera:
        return HTMLResponse("Camera not found", status_code=404)
    return templates.TemplateResponse(
        "camera.html",
        {
            "request": request,
            "camera": camera,
            "agency": camera.agency,
        },
    )
