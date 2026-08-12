"""
Modelos Pydantic — requests e responses da API.
"""
from typing import Optional, List, Any
from pydantic import BaseModel, Field


# ===================================
# CAPTURA
# ===================================
class CaptureTextRequest(BaseModel):
    text: str
    context: Optional[str] = None


class CaptureLinkRequest(BaseModel):
    url: str
    note: Optional[str] = None


class CaptureResponse(BaseModel):
    id: str
    status: str
    title: Optional[str] = None
    message: Optional[str] = None


# ===================================
# CONTEÚDOS
# ===================================
class ContentUpdateRequest(BaseModel):
    title: Optional[str] = None
    summary: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    intent: Optional[str] = None
    is_reviewed: Optional[bool] = None


class ContentOut(BaseModel):
    id: str
    content_type: str
    title: Optional[str] = None
    summary: Optional[str] = None
    original_text: Optional[str] = None
    transcription: Optional[str] = None
    extracted_text: Optional[str] = None
    source_url: Optional[str] = None
    source_platform: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    intent: Optional[str] = None
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    duration: Optional[int] = None
    thumbnail_url: Optional[str] = None
    status: str
    error_message: Optional[str] = None
    is_reviewed: bool
    created_at: Optional[str] = None
    processed_at: Optional[str] = None
    updated_at: Optional[str] = None
    tags: Optional[List[str]] = None
    projects: Optional[List[str]] = None


# ===================================
# BUSCA / ASK
# ===================================
class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    answer: str
    contents: List[Any]
    total_found: int


class SearchResponse(BaseModel):
    results: List[Any]
    total: int


# ===================================
# PROJETOS
# ===================================
class ProjectCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None


class ProjectOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    is_active: bool = True
    created_at: Optional[str] = None


# ===================================
# CLASSIFICAÇÃO (resultado do LLM)
# ===================================
class ClassificationResult(BaseModel):
    title: str = Field(default="Sem título")
    summary: str = Field(default="")
    category: str = Field(default="Outros")
    subcategory: str = Field(default="")
    tags: List[str] = Field(default_factory=list)
    intent: Optional[str] = Field(default="lembrar")
    projects: List[str] = Field(default_factory=list)
    language: str = Field(default="pt")


# ===================================
# STATS
# ===================================
class StatsResponse(BaseModel):
    total: int
    by_type: dict
    by_category: dict
    pending: int
    unreviewed: int
    recent_7d: int
    top_tags: List[dict]
