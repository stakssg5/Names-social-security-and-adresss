from __future__ import annotations

from pathlib import Path
from typing import List, Optional

import os
from fastapi import Depends, FastAPI, Query, Request, Form, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from .db import Base, engine, get_db
from .models import Agency, Camera, Tag

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
FEEDS_DIR = BASE_DIR / "feeds"
FEEDS_JSON = FEEDS_DIR / "public_feeds.json"
STORAGE_DIR = BASE_DIR / "storage"

app = FastAPI(title="Public Webcam Aggregator", version="0.1.0")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

try:
    from fastapi.templating import Jinja2Templates  # type: ignore
except Exception:  # pragma: no cover
    Jinja2Templates = None  # type: ignore

templates = Jinja2Templates(directory=str(TEMPLATES_DIR)) if Jinja2Templates else None

security = HTTPBasic()


def require_admin(credentials: HTTPBasicCredentials = Depends(security)) -> None:
    expected_user = os.getenv("ADMIN_USERNAME")
    expected_pass = os.getenv("ADMIN_PASSWORD")
    if not expected_user or not expected_pass:
        raise HTTPException(status_code=503, detail="Admin disabled: set ADMIN_USERNAME and ADMIN_PASSWORD env vars")
    is_ok = (credentials.username == expected_user) and (credentials.password == expected_pass)
    if not is_ok:
        raise HTTPException(status_code=401, detail="Unauthorized")


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
            # tags
            raw_tags = entry.get("tags")
            if isinstance(raw_tags, list):
                tag_names = [str(t).strip().lower() for t in raw_tags if str(t).strip()]
            elif isinstance(raw_tags, str):
                tag_names = [t.strip().lower() for t in raw_tags.split(",") if t.strip()]
            else:
                tag_names = []
            for tn in tag_names:
                t = db.query(Tag).filter(Tag.name == tn).first()
                if not t:
                    t = Tag(name=tn)
                    db.add(t)
                    db.flush()
                camera.tags.append(t)
        db.commit()
    finally:
        db.close()


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/cameras")
def search_cameras(
    q: Optional[str] = Query(default=None, description="Free-text search across name, agency, location"),
    agency: Optional[str] = Query(default=None, description="Filter by agency slug"),
    tag: Optional[str] = Query(default=None, description="Filter by tag name"),
    stream_type: Optional[str] = Query(default=None, description="Filter by stream type (hls|mjpeg|image|iframe)"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
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
    if agency:
        query = query.filter(Agency.slug == agency)
    if stream_type:
        query = query.filter(Camera.stream_type == stream_type.lower())
    if tag:
        query = query.join(Camera.tags).filter(Tag.name == tag)
    query = query.order_by(Agency.name.asc(), Camera.name.asc())
    items: List[Camera] = query.limit(limit).offset((page - 1) * limit).all()
    return [
        {
            "id": c.id,
            "name": c.name,
            "location": c.location,
            "stream_url": c.stream_url,
            "stream_type": c.stream_type,
            "tags": [t.name for t in getattr(c, "tags", [])],
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


@app.get("/api/agencies")
def list_agencies(db: Session = Depends(get_db)):
    rows = (
        db.query(Agency.id, Agency.name, Agency.slug, func.count(Camera.id).label("camera_count"))
        .outerjoin(Camera)
        .group_by(Agency.id)
        .order_by(Agency.name.asc())
        .all()
    )
    return [
        {"id": r.id, "name": r.name, "slug": r.slug, "camera_count": r.camera_count}
        for r in rows
    ]


@app.get("/api/tags")
def list_tags(db: Session = Depends(get_db)):
    rows = (
        db.query(Tag.id, Tag.name, func.count(Camera.id).label("camera_count"))
        .select_from(Tag)
        .outerjoin(Tag.cameras)
        .group_by(Tag.id)
        .order_by(Tag.name.asc())
        .all()
    )
    return [
        {"id": r.id, "name": r.name, "camera_count": r.camera_count}
        for r in rows
    ]


# --- Admin UI ---


@app.get("/admin", response_class=HTMLResponse)
def admin_index(request: Request, db: Session = Depends(get_db), _: None = Depends(require_admin)) -> HTMLResponse:
    agency_count = db.query(Agency).count()
    camera_count = db.query(Camera).count()
    tag_count = db.query(Tag).count()
    return templates.TemplateResponse(
        "admin/index.html",
        {"request": request, "agency_count": agency_count, "camera_count": camera_count, "tag_count": tag_count},
    )


@app.get("/admin/cameras/new", response_class=HTMLResponse)
def admin_new_camera(request: Request, db: Session = Depends(get_db), _: None = Depends(require_admin)) -> HTMLResponse:
    agencies = db.query(Agency).order_by(Agency.name.asc()).all()
    return templates.TemplateResponse("admin/new_camera.html", {"request": request, "agencies": agencies})


@app.post("/admin/cameras")
def admin_create_camera(
    request: Request,
    name: str = Form(...),
    location: Optional[str] = Form(None),
    stream_url: str = Form(...),
    stream_type: str = Form("hls"),
    existing_agency_slug: Optional[str] = Form(None),
    new_agency_name: Optional[str] = Form(None),
    tags_csv: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    stream_type = (stream_type or "hls").lower()
    if not existing_agency_slug and not new_agency_name:
        raise HTTPException(status_code=400, detail="Provide an agency (existing or new)")

    agency_obj: Optional[Agency] = None
    if new_agency_name:
        slug = new_agency_name.strip().lower().replace(" ", "-")
        agency_obj = db.query(Agency).filter(Agency.slug == slug).first()
        if not agency_obj:
            agency_obj = Agency(name=new_agency_name.strip(), slug=slug)
            db.add(agency_obj)
            db.flush()
    else:
        agency_obj = db.query(Agency).filter(Agency.slug == existing_agency_slug).first()
        if not agency_obj:
            raise HTTPException(status_code=400, detail="Unknown agency slug")

    cam = Camera(
        name=name.strip(),
        location=(location or "").strip() or None,
        stream_url=stream_url.strip(),
        stream_type=stream_type,
        agency_id=agency_obj.id,
    )
    db.add(cam)
    db.flush()

    # Tags
    if tags_csv:
        tag_names = [t.strip().lower() for t in tags_csv.split(",") if t.strip()]
        for tn in tag_names:
            tag_obj = db.query(Tag).filter(Tag.name == tn).first()
            if not tag_obj:
                tag_obj = Tag(name=tn)
                db.add(tag_obj)
                db.flush()
            cam.tags.append(tag_obj)

    db.commit()
    return RedirectResponse(url=f"/cameras/{cam.id}", status_code=303)


@app.get("/admin/import", response_class=HTMLResponse)
def admin_import_page(request: Request, _: None = Depends(require_admin)) -> HTMLResponse:
    return templates.TemplateResponse("admin/import.html", {"request": request})


def _get_or_create_agency(db: Session, agency_name: Optional[str], agency_slug: Optional[str]) -> Agency:
    if agency_slug:
        existing = db.query(Agency).filter(Agency.slug == agency_slug).first()
        if existing:
            return existing
    if agency_name:
        slug = (agency_slug or agency_name.strip().lower().replace(" ", "-"))
        existing = db.query(Agency).filter(Agency.slug == slug).first()
        if existing:
            return existing
        agency = Agency(name=agency_name.strip(), slug=slug)
        db.add(agency)
        db.flush()
        return agency
    raise HTTPException(status_code=400, detail="Agency name or slug required")


def _attach_tags(db: Session, camera: Camera, tags: Optional[List[str]]) -> None:
    if not tags:
        return
    for tn in [t.strip().lower() for t in tags if t and t.strip()]:
        tag_obj = db.query(Tag).filter(Tag.name == tn).first()
        if not tag_obj:
            tag_obj = Tag(name=tn)
            db.add(tag_obj)
            db.flush()
        if tag_obj not in camera.tags:
            camera.tags.append(tag_obj)


@app.post("/admin/import/json")
async def admin_import_json(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    import json
    payload = await file.read()
    try:
        items = json.loads(payload.decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {exc}")
    if not isinstance(items, list):
        raise HTTPException(status_code=400, detail="Expected a JSON array of feed objects")
    created = 0
    skipped = 0
    for entry in items:
        agency = _get_or_create_agency(db, entry.get("agency"), entry.get("agency_slug"))
        name = (entry.get("name") or "").strip()
        if not name:
            skipped += 1
            continue
        # Skip duplicates by name+agency
        existing = db.query(Camera).filter(Camera.name == name, Camera.agency_id == agency.id).first()
        if existing:
            skipped += 1
            continue
        cam = Camera(
            name=name,
            location=(entry.get("location") or "").strip() or None,
            stream_url=(entry.get("stream_url") or "").strip(),
            stream_type=(entry.get("stream_type") or "hls").strip().lower(),
            agency_id=agency.id,
        )
        db.add(cam)
        db.flush()
        # tags can be array or comma-separated string
        raw_tags = entry.get("tags")
        tags_list: Optional[List[str]] = None
        if isinstance(raw_tags, list):
            tags_list = [str(t) for t in raw_tags]
        elif isinstance(raw_tags, str):
            tags_list = [t.strip() for t in raw_tags.split(",") if t.strip()]
        _attach_tags(db, cam, tags_list)
        created += 1
    db.commit()
    return {"created": created, "skipped": skipped}


@app.post("/admin/import/csv")
async def admin_import_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    import csv
    text = (await file.read()).decode("utf-8", errors="replace")
    reader = csv.DictReader(text.splitlines())
    created = 0
    skipped = 0
    for row in reader:
        agency = _get_or_create_agency(db, row.get("agency"), row.get("agency_slug"))
        name = (row.get("name") or "").strip()
        if not name:
            skipped += 1
            continue
        existing = db.query(Camera).filter(Camera.name == name, Camera.agency_id == agency.id).first()
        if existing:
            skipped += 1
            continue
        cam = Camera(
            name=name,
            location=(row.get("location") or "").strip() or None,
            stream_url=(row.get("stream_url") or "").strip(),
            stream_type=(row.get("stream_type") or "hls").strip().lower(),
            agency_id=agency.id,
        )
        db.add(cam)
        db.flush()
        tags_csv = row.get("tags") or ""
        tags_list = [t.strip() for t in tags_csv.split(",") if t.strip()]
        _attach_tags(db, cam, tags_list)
        created += 1
    db.commit()
    return {"created": created, "skipped": skipped}


def _cleanup_orphan_tags(db: Session) -> int:
    # Remove tags that are no longer linked to any camera
    orphan_tags = (
        db.query(Tag)
        .outerjoin(Tag.cameras)
        .filter(Camera.id == None)  # noqa: E711
        .all()
    )
    count = 0
    for t in orphan_tags:
        db.delete(t)
        count += 1
    return count


@app.get("/admin/cameras", response_class=HTMLResponse)
def admin_list_cameras(request: Request, db: Session = Depends(get_db), _: None = Depends(require_admin)) -> HTMLResponse:
    cams = db.query(Camera).join(Agency).order_by(Agency.name.asc(), Camera.name.asc()).all()
    return templates.TemplateResponse("admin/cameras.html", {"request": request, "cameras": cams})


@app.post("/admin/cameras/{camera_id}/delete")
def admin_delete_camera(camera_id: int, db: Session = Depends(get_db), _: None = Depends(require_admin)):
    import shutil
    cam: Optional[Camera] = db.query(Camera).filter(Camera.id == camera_id).first()
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")
    # Remove any local storage for this camera if present
    cam_dir = STORAGE_DIR / f"camera_{camera_id}"
    try:
        if cam_dir.exists():
            shutil.rmtree(cam_dir, ignore_errors=True)
    except Exception:
        pass
    db.delete(cam)
    db.commit()
    _cleanup_orphan_tags(db)
    db.commit()
    return RedirectResponse(url="/admin/cameras", status_code=303)
