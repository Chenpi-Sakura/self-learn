"""资源 CRUD 路由（Task 1）。

单账户约定：所有资源归属 KEEP_STUDENT（无登录鉴权，见 memory no-auth-no-login）。
软删语义：DELETE 只置 deleted_at，list/get 过滤 deleted_at IS NULL。
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from sqlalchemy import select

from selflearn.domain.resource import Resource
from selflearn.infra.db import get_session_factory
from selflearn.infra.seed_account import KEEP_STUDENT
from selflearn.schemas.resource import (
    ResourceListItem,
    ResourceResponse,
    ResourceUpdate,
    ResourceUploadItem,
    ResourceUploadResponse,
)

router = APIRouter(prefix="/api/resources", tags=["resources"])

MAX_FILES = 4
MAX_BYTES = 10 * 1024 * 1024  # 10MB


@router.post("/upload", response_model=ResourceUploadResponse)
async def upload_resources(
    files: list[UploadFile] = File(...),
) -> ResourceUploadResponse:
    if len(files) > MAX_FILES:
        raise HTTPException(status_code=400, detail=f"max {MAX_FILES} files")
    if not files:
        raise HTTPException(status_code=400, detail="at least one file")

    for f in files:
        if not (f.filename or "").lower().endswith(".md"):
            raise HTTPException(status_code=400, detail=f"only .md accepted: {f.filename}")

    uploaded: list[ResourceUploadItem] = []
    factory = get_session_factory()
    async with factory() as session:
        for f in files:
            body = await f.read()
            if len(body) > MAX_BYTES:
                raise HTTPException(status_code=400, detail=f"{f.filename} too large")
            r = Resource(
                student_id=UUID(KEEP_STUDENT),
                name=f.filename or "untitled.md",
                content_md=body.decode("utf-8", errors="replace"),
                size_bytes=len(body),
            )
            session.add(r)
            await session.flush()
            uploaded.append(
                ResourceUploadItem(id=r.id, name=r.name, size_bytes=r.size_bytes)
            )
        await session.commit()
    return ResourceUploadResponse(uploaded=uploaded)


@router.get("/list")
async def list_resources() -> dict[str, list[ResourceListItem]]:
    factory = get_session_factory()
    async with factory() as session:
        rows = (
            await session.execute(
                select(Resource)
                .where(Resource.deleted_at.is_(None))
                .order_by(Resource.name)
            )
        ).scalars().all()
        return {"items": [ResourceListItem.model_validate(r) for r in rows]}


@router.get("/{resource_id}", response_model=ResourceResponse)
async def get_resource(resource_id: UUID) -> ResourceResponse:
    factory = get_session_factory()
    async with factory() as session:
        r = (
            await session.execute(
                select(Resource).where(
                    Resource.id == resource_id, Resource.deleted_at.is_(None)
                )
            )
        ).scalar_one_or_none()
        if r is None:
            raise HTTPException(status_code=404, detail="not found")
        return ResourceResponse.model_validate(r)


def _would_create_cycle(old_name: str, new_name: str) -> bool:
    """防止把文件移到自身子路径（a/x → a/x/y）。"""
    return new_name.startswith(old_name + "/")


@router.put("/{resource_id}", response_model=ResourceResponse)
async def update_resource(resource_id: UUID, body: ResourceUpdate) -> ResourceResponse:
    factory = get_session_factory()
    async with factory() as session:
        r = (
            await session.execute(
                select(Resource).where(
                    Resource.id == resource_id, Resource.deleted_at.is_(None)
                )
            )
        ).scalar_one_or_none()
        if r is None:
            raise HTTPException(status_code=404, detail="not found")
        if r.name != body.name:
            if _would_create_cycle(r.name, body.name):
                raise HTTPException(status_code=400, detail="cycle rename rejected")
            r.name = body.name
            await session.commit()
            await session.refresh(r)
        return ResourceResponse.model_validate(r)


@router.delete("/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resource(resource_id: UUID) -> None:
    factory = get_session_factory()
    async with factory() as session:
        r = (
            await session.execute(
                select(Resource).where(
                    Resource.id == resource_id, Resource.deleted_at.is_(None)
                )
            )
        ).scalar_one_or_none()
        if r is None:
            raise HTTPException(status_code=404, detail="not found")
        r.deleted_at = datetime.now(timezone.utc)
        await session.commit()
