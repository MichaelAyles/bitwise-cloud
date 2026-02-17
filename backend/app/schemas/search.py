import uuid

from pydantic import BaseModel


class SearchRequest(BaseModel):
    query: str
    doc_ids: list[uuid.UUID] | None = None
    top_k: int = 10


class SearchResult(BaseModel):
    score: float
    text: str
    document_id: uuid.UUID
    document_title: str
    page_number: int | None
    section: str | None


class SearchResponse(BaseModel):
    results: list[SearchResult]
    query: str
    total: int


class RegisterSearchRequest(BaseModel):
    name: str
    doc_ids: list[uuid.UUID] | None = None
