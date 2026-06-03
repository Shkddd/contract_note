"""Knowledge base CRUD endpoints."""

from fastapi import APIRouter, HTTPException
from ..services.knowledge_base import (
    list_entries, get_entry, create_entry, update_entry,
    delete_entry, list_categories, semantic_search,
)
from ..models.schemas import KBEntryCreate, KBEntryUpdate, KBEntryResponse

router = APIRouter(prefix="/api/kb", tags=["knowledge_base"])


@router.get("/categories")
def get_categories():
    return {"categories": list_categories()}


@router.get("", response_model=list[KBEntryResponse])
def get_kb_entries(category: str = None, search: str = None):
    return list_entries(category=category, search=search)


@router.get("/{entry_id}", response_model=KBEntryResponse)
def get_kb_entry(entry_id: int):
    entry = get_entry(entry_id)
    if not entry:
        raise HTTPException(404, "条目不存在")
    return entry


@router.post("", response_model=KBEntryResponse)
def create_kb_entry(data: KBEntryCreate):
    return create_entry(
        title=data.title,
        category=data.category,
        content=data.content,
        risk_level=data.risk_level,
        tags=data.tags,
    )


@router.put("/{entry_id}", response_model=KBEntryResponse)
def update_kb_entry(entry_id: int, data: KBEntryUpdate):
    entry = update_entry(
        entry_id,
        title=data.title,
        category=data.category,
        content=data.content,
        risk_level=data.risk_level,
        tags=data.tags,
    )
    if not entry:
        raise HTTPException(404, "条目不存在")
    return entry


@router.delete("/{entry_id}")
def delete_kb_entry(entry_id: int):
    if not delete_entry(entry_id):
        raise HTTPException(404, "条目不存在")
    return {"message": "已删除"}


@router.get("/search/{query}")
def search_kb(query: str, top_k: int = 5):
    """Semantic search against knowledge base."""
    return semantic_search(query, top_k=top_k)
