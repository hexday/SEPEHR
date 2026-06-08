"""
SEPEHR Backend — News, Alerts, and Map API Endpoints
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.dependencies.auth import CurrentUser, RequireAdmin, RequirePublisher
from app.core.exceptions import NewsPostNotFoundException, NewsServerNotFoundException
from app.domain.enums.all import AlertSeverity, MapPointType, NewsPostStatus
from app.domain.models.all import EmergencyAlert, MapPoint, NewsCategory, NewsPost, NewsServer
from app.domain.schemas.auth import UserPublicSchema
from app.infrastructure.database.session import get_db
from app.infrastructure.websocket.manager import ws_manager

# ── News Schemas ──────────────────────────────────────────────────────────────

class NewsServerSchema(BaseModel):
    id: str
    name: str
    slug: str
    description: Optional[str] = None
    icon_url: Optional[str] = None
    is_active: bool
    sort_order: int
    category_count: int = 0

    class Config:
        from_attributes = True


class NewsCategorySchema(BaseModel):
    id: str
    server_id: str
    name: str
    slug: str
    description: Optional[str] = None
    color: Optional[str] = None
    sort_order: int

    class Config:
        from_attributes = True


class NewsPostSummarySchema(BaseModel):
    id: str
    server_id: str
    category_id: Optional[str] = None
    title: str
    slug: str
    summary: Optional[str] = None
    cover_image_url: Optional[str] = None
    status: NewsPostStatus
    published_at: Optional[datetime] = None
    created_at: datetime
    publisher: Optional[UserPublicSchema] = None

    class Config:
        from_attributes = True


class NewsPostDetailSchema(NewsPostSummarySchema):
    content: str
    video_url: Optional[str] = None
    category: Optional[NewsCategorySchema] = None


class CreateNewsServerRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    slug: str = Field(..., min_length=1, max_length=128, pattern=r"^[a-z0-9-]+$")
    description: Optional[str] = Field(None, max_length=1024)
    sort_order: int = 0


class CreateNewsCategoryRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    slug: str = Field(..., min_length=1, max_length=128, pattern=r"^[a-z0-9-]+$")
    description: Optional[str] = Field(None, max_length=512)
    color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    sort_order: int = 0


class CreateNewsPostRequest(BaseModel):
    server_id: str
    category_id: Optional[str] = None
    title: str = Field(..., min_length=1, max_length=512)
    summary: Optional[str] = Field(None, max_length=1024)
    content: str = Field(..., min_length=1)
    video_url: Optional[str] = Field(None, max_length=2048)
    publish: bool = False


# ── Alert Schemas ─────────────────────────────────────────────────────────────

class AlertSchema(BaseModel):
    id: str
    title: str
    content: str
    severity: AlertSeverity
    area_geojson: Optional[dict] = None
    is_active: bool
    expires_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class CreateAlertRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=512)
    content: str = Field(..., min_length=1)
    severity: AlertSeverity
    area_geojson: Optional[dict] = None
    expires_at: Optional[datetime] = None


# ── Map Schemas ───────────────────────────────────────────────────────────────

class MapPointSchema(BaseModel):
    id: str
    name: str
    type: MapPointType
    latitude: float
    longitude: float
    description: Optional[str] = None
    contact: Optional[str] = None
    address: Optional[str] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class CreateMapPointRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=256)
    type: MapPointType
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    description: Optional[str] = Field(None, max_length=2048)
    contact: Optional[str] = Field(None, max_length=256)
    address: Optional[str] = Field(None, max_length=512)


# ── News Routers ──────────────────────────────────────────────────────────────

news_router = APIRouter(prefix="/news", tags=["News"])


@news_router.get("/servers", response_model=list[NewsServerSchema])
async def list_news_servers(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> list[NewsServerSchema]:
    result = await db.execute(
        select(NewsServer)
        .where(NewsServer.is_active.is_(True), NewsServer.deleted_at.is_(None))
        .options(selectinload(NewsServer.categories))
        .order_by(NewsServer.sort_order)
    )
    servers = list(result.scalars().all())
    schemas = []
    for s in servers:
        schema = NewsServerSchema.model_validate(s)
        schema.category_count = len([c for c in s.categories if c.is_active])
        schemas.append(schema)
    return schemas


@news_router.get("/servers/{server_id}", response_model=NewsServerSchema)
async def get_news_server(
    server_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> NewsServerSchema:
    server = await db.scalar(
        select(NewsServer).where(
            NewsServer.id == server_id,
            NewsServer.is_active.is_(True),
            NewsServer.deleted_at.is_(None),
        )
    )
    if not server:
        raise NewsServerNotFoundException()
    return NewsServerSchema.model_validate(server)


@news_router.post("/servers", response_model=NewsServerSchema, status_code=201)
async def create_news_server(
    request_data: CreateNewsServerRequest,
    current_user: RequireAdmin,
    db: AsyncSession = Depends(get_db),
) -> NewsServerSchema:
    server = NewsServer(
        name=request_data.name,
        slug=request_data.slug,
        description=request_data.description,
        sort_order=request_data.sort_order,
        created_by=current_user.id,
    )
    db.add(server)
    await db.flush()
    return NewsServerSchema.model_validate(server)


@news_router.get("/servers/{server_id}/categories", response_model=list[NewsCategorySchema])
async def list_categories(
    server_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> list[NewsCategorySchema]:
    result = await db.execute(
        select(NewsCategory).where(
            NewsCategory.server_id == server_id,
            NewsCategory.is_active.is_(True),
        ).order_by(NewsCategory.sort_order)
    )
    return [NewsCategorySchema.model_validate(c) for c in result.scalars().all()]


@news_router.post("/servers/{server_id}/categories", response_model=NewsCategorySchema, status_code=201)
async def create_category(
    server_id: str,
    request_data: CreateNewsCategoryRequest,
    current_user: RequireAdmin,
    db: AsyncSession = Depends(get_db),
) -> NewsCategorySchema:
    category = NewsCategory(
        server_id=server_id,
        name=request_data.name,
        slug=request_data.slug,
        description=request_data.description,
        color=request_data.color,
        sort_order=request_data.sort_order,
    )
    db.add(category)
    await db.flush()
    return NewsCategorySchema.model_validate(category)


@news_router.get("/posts", response_model=list[NewsPostSummarySchema])
async def list_posts(
    current_user: CurrentUser,
    server_id: Optional[str] = Query(None),
    category_id: Optional[str] = Query(None),
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> list[NewsPostSummarySchema]:
    query = (
        select(NewsPost)
        .where(
            NewsPost.status == NewsPostStatus.PUBLISHED,
            NewsPost.deleted_at.is_(None),
        )
        .order_by(NewsPost.published_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if server_id:
        query = query.where(NewsPost.server_id == server_id)
    if category_id:
        query = query.where(NewsPost.category_id == category_id)

    result = await db.execute(query)
    return [NewsPostSummarySchema.model_validate(p) for p in result.scalars().all()]


@news_router.get("/posts/{post_id}", response_model=NewsPostDetailSchema)
async def get_post(
    post_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> NewsPostDetailSchema:
    post = await db.scalar(
        select(NewsPost)
        .where(NewsPost.id == post_id, NewsPost.deleted_at.is_(None))
        .options(selectinload(NewsPost.category))
    )
    if not post:
        raise NewsPostNotFoundException()
    return NewsPostDetailSchema.model_validate(post)


@news_router.post("/posts", response_model=NewsPostDetailSchema, status_code=201)
async def create_post(
    request_data: CreateNewsPostRequest,
    current_user: RequirePublisher,
    db: AsyncSession = Depends(get_db),
) -> NewsPostDetailSchema:
    from python_slugify import slugify

    slug = slugify(request_data.title, allow_unicode=True)
    post = NewsPost(
        server_id=request_data.server_id,
        category_id=request_data.category_id,
        publisher_id=current_user.id,
        title=request_data.title,
        slug=slug,
        summary=request_data.summary,
        content=request_data.content,
        video_url=request_data.video_url,
        status=NewsPostStatus.PUBLISHED if request_data.publish else NewsPostStatus.DRAFT,
        published_at=datetime.utcnow() if request_data.publish else None,
    )
    db.add(post)
    await db.flush()
    return NewsPostDetailSchema.model_validate(post)


# ── Alerts Router ─────────────────────────────────────────────────────────────

alerts_router = APIRouter(prefix="/alerts", tags=["Emergency Alerts"])


@alerts_router.get("", response_model=list[AlertSchema])
async def list_alerts(
    current_user: CurrentUser,
    active_only: bool = Query(True),
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
) -> list[AlertSchema]:
    query = (
        select(EmergencyAlert)
        .order_by(EmergencyAlert.created_at.desc())
        .limit(limit)
    )
    if active_only:
        query = query.where(EmergencyAlert.is_active.is_(True))
    result = await db.execute(query)
    return [AlertSchema.model_validate(a) for a in result.scalars().all()]


@alerts_router.post("", response_model=AlertSchema, status_code=201)
async def create_alert(
    request_data: CreateAlertRequest,
    current_user: RequireAdmin,
    db: AsyncSession = Depends(get_db),
) -> AlertSchema:
    alert = EmergencyAlert(
        title=request_data.title,
        content=request_data.content,
        severity=request_data.severity,
        area_geojson=request_data.area_geojson,
        expires_at=request_data.expires_at,
        issued_by=current_user.id,
        is_active=True,
    )
    db.add(alert)
    await db.flush()

    # Broadcast to all connected users
    alert_data = AlertSchema.model_validate(alert).model_dump(mode="json")
    await ws_manager.notify_alert(alert_data)

    return AlertSchema.model_validate(alert)


@alerts_router.patch("/{alert_id}/deactivate", response_model=AlertSchema)
async def deactivate_alert(
    alert_id: str,
    current_user: RequireAdmin,
    db: AsyncSession = Depends(get_db),
) -> AlertSchema:
    alert = await db.get(EmergencyAlert, alert_id)
    if not alert:
        from app.core.exceptions import NotFoundException
        raise NotFoundException("Alert not found")
    alert.is_active = False
    return AlertSchema.model_validate(alert)


# ── Map Router ────────────────────────────────────────────────────────────────

map_router = APIRouter(prefix="/map", tags=["Crisis Map"])


@map_router.get("/points", response_model=list[MapPointSchema])
async def list_map_points(
    current_user: CurrentUser,
    point_type: Optional[MapPointType] = Query(None),
    db: AsyncSession = Depends(get_db),
) -> list[MapPointSchema]:
    query = select(MapPoint).where(MapPoint.is_active.is_(True))
    if point_type:
        query = query.where(MapPoint.type == point_type)
    result = await db.execute(query)
    return [MapPointSchema.model_validate(p) for p in result.scalars().all()]


@map_router.post("/points", response_model=MapPointSchema, status_code=201)
async def create_map_point(
    request_data: CreateMapPointRequest,
    current_user: RequireModerator,
    db: AsyncSession = Depends(get_db),
) -> MapPointSchema:
    from app.api.v1.dependencies.auth import RequireModerator

    point = MapPoint(
        name=request_data.name,
        type=request_data.type,
        latitude=request_data.latitude,
        longitude=request_data.longitude,
        description=request_data.description,
        contact=request_data.contact,
        address=request_data.address,
        created_by=current_user.id,
    )
    db.add(point)
    await db.flush()
    return MapPointSchema.model_validate(point)


@map_router.patch("/points/{point_id}/deactivate", response_model=MapPointSchema)
async def deactivate_map_point(
    point_id: str,
    current_user: RequireModerator,
    db: AsyncSession = Depends(get_db),
) -> MapPointSchema:
    point = await db.get(MapPoint, point_id)
    if not point:
        from app.core.exceptions import NotFoundException
        raise NotFoundException("Map point not found")
    point.is_active = False
    return MapPointSchema.model_validate(point)
