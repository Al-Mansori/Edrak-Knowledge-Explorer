# app.py
from __future__ import annotations

import hashlib
import mimetypes
import threading
from pathlib import Path
from typing import Any, List, Optional

import pandas as pd
from fastapi import FastAPI, HTTPException, Query, Path as FPath
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from contextlib import asynccontextmanager

from kg_file_endpoints import create_kg_file_router
from kg_endpoints import KGFromLlamaIndex, create_kg_router
# --- your index utilities ---
from index import build_or_load_index, build_or_load_kg_index_from_markdown, build_or_load_kg_index_from_markdown_file, get_query_engine
from llama_index.core.vector_stores import MetadataFilters, ExactMatchFilter

# ---------- Config ----------
DATASET_ROOT = Path("publications_dataset").resolve()
CSV_PATH = DATASET_ROOT / "documents.csv"
PDF_DIR = DATASET_ROOT / "pdf"
CONTENT_LIST_DIR = DATASET_ROOT / "content_list"
SUMMARY_DIR = DATASET_ROOT / "summary"

mimetypes.add_type("application/pdf", ".pdf")
mimetypes.add_type("text/markdown", ".md")
mimetypes.add_type("application/json", ".json")

# ---------- Models ----------
class Document(BaseModel):
    id: str
    title: str
    pdf_filename: Optional[str] = None
    content_list_filename: Optional[str] = None
    summary_filename: Optional[str] = None
    pdf_url: Optional[str] = None
    content_list_url: Optional[str] = None
    summary_url: Optional[str] = None

class QASource(BaseModel):
    filename: Optional[str] = None
    source_type: Optional[str] = None
    page_idx: Optional[int] = None
    score: Optional[float] = None
    preview: Optional[str] = None

class QARequest(BaseModel):
    question: str
    top_k: int = 5
    only_file: Optional[str] = None
    response_mode: str = "compact"

class QAResponse(BaseModel):
    answer: str
    sources: List[QASource] = []

# ---------- Load CSV ----------
if not CSV_PATH.exists():
    raise RuntimeError(f"CSV not found at {CSV_PATH}")
df = pd.read_csv(CSV_PATH)
required_cols = {"Title", "pdf_filename", "content_list_filename", "summary_filename"}
missing = required_cols - set(df.columns)
if missing:
    raise RuntimeError(f"CSV missing required columns: {missing}")

def _row_id(row) -> str:
    basis = f"{row.get('Title','')}|{row.get('pdf_filename','')}|{row.get('content_list_filename','')}|{row.get('summary_filename','')}"
    return hashlib.sha1(basis.encode("utf-8")).hexdigest()[:12]

df["_id"] = df.apply(_row_id, axis=1)
ROW_BY_ID = {r["_id"]: r for _, r in df.iterrows()}

KG_BY_FILE: dict[str, Any] = {}           # filename -> KnowledgeGraphIndex
KG_PERSIST_BY_FILE: dict[str, str] = {}   # filename -> persist_dir


# ---------- Lifespan ----------
_engine_lock = threading.Lock()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup/shutdown lifecycle for the app.
    """
    global VEC_INDEX, DEFAULT_ENGINE, KG_BY_FILE, KG_PERSIST_BY_FILE

    with _engine_lock:
        VEC_INDEX = build_or_load_index(
            content_list_dir=str(CONTENT_LIST_DIR),
            persist_dir="./.llamaindex_store",
            rebuild=False,
        )
        
        # NEW: preload per-file KG indexes
        KG_BY_FILE = {}
        KG_PERSIST_BY_FILE = {}
        persist_root = Path("./.kg_single").resolve()
        persist_root.mkdir(parents=True, exist_ok=True)

        for md_path in sorted(SUMMARY_DIR.glob("*.md")):
            persist_dir = ".kg_single"
            idx = build_or_load_kg_index_from_markdown_file(
                md_path=str(md_path),
                rebuild=False,
                max_triplets_per_chunk=5,
            )
            KG_BY_FILE[md_path.name] = idx
            KG_PERSIST_BY_FILE[md_path.name] = persist_dir

        # Mount router
        def _get_index_by_file(file_name: str):
            return KG_BY_FILE.get(file_name)

        def _list_files():
            # returns list[(file_name, persist_dir)]
            return [(fn, KG_PERSIST_BY_FILE.get(fn)) for fn in sorted(KG_BY_FILE.keys())]

        app.include_router(create_kg_file_router(
            get_index_by_file=_get_index_by_file,
            list_files=_list_files,
            prefix="/kg/file",
        ))

        
        
        
        KG_INDEX = build_or_load_kg_index_from_markdown(
            summary_dir=str(SUMMARY_DIR),
            persist_dir="./.kg_from_summary",
            rebuild=False,
            max_triplets_per_chunk=5,
        )
        
        kg_router = create_kg_router(KGFromLlamaIndex(lambda: KG_INDEX), prefix="/kg")
        app.include_router(kg_router)

        DEFAULT_ENGINE = get_query_engine(
            index=VEC_INDEX,
            top_k=5,
            response_mode="compact",
            include_sources=True,
        )
    yield
    # nothing special to cleanup yet
    with _engine_lock:
        VEC_INDEX = None
        DEFAULT_ENGINE = None

# ---------- App ----------
app = FastAPI(title="Publications API", version="1.2.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Helpers ----------
def _safe_join(base: Path, filename: str) -> Path:
    if not filename or not isinstance(filename, str):
        raise HTTPException(status_code=404, detail="File not specified")
    p = (base / filename).resolve()
    try:
        p.relative_to(base.resolve())
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid filename")
    if not p.exists() or not p.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return p

def _to_doc_model(row) -> Document:
    doc = Document(
        id=row["_id"],
        title=row.get("Title") or "",
        pdf_filename=row.get("pdf_filename"),
        content_list_filename=row.get("content_list_filename"),
        summary_filename=row.get("summary_filename"),
    )
    if doc.pdf_filename:
        doc.pdf_url = f"/files/pdf/{doc.pdf_filename}"
    if doc.content_list_filename:
        doc.content_list_url = f"/files/content-list/{doc.content_list_filename}"
    if doc.summary_filename:
        doc.summary_url = f"/files/summary/{doc.summary_filename}"
    return doc

# ---------- Endpoints ----------
@app.get("/documents", response_model=List[Document])
def list_documents(
    q: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    subset = df
    if q:
        mask = subset["Title"].fillna("").str.contains(q, case=False, na=False)
        subset = subset[mask]
    subset = subset.iloc[skip : skip + limit]
    return [_to_doc_model(r) for _, r in subset.iterrows()]

@app.get("/documents/{doc_id}", response_model=Document)
def get_document(doc_id: str = FPath(...)):
    row = ROW_BY_ID.get(doc_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return _to_doc_model(row)

@app.get("/files/pdf/{filename}")
def get_pdf(filename: str = FPath(...)):
    file_path = _safe_join(PDF_DIR, filename)
    return FileResponse(file_path, media_type="application/pdf", filename=file_path.name)

@app.get("/files/content-list/{filename}")
def get_content_list(filename: str = FPath(...)):
    file_path = _safe_join(CONTENT_LIST_DIR, filename)
    return FileResponse(file_path, media_type="application/json", filename=file_path.name)

@app.get("/files/summary/{filename}")
def get_summary(filename: str = FPath(...)):
    file_path = _safe_join(SUMMARY_DIR, filename)
    return FileResponse(file_path, media_type="text/markdown", filename=file_path.name)

@app.post("/qa", response_model=QAResponse)
def ask_question(payload: QARequest):
    global VEC_INDEX, DEFAULT_ENGINE
    if not payload.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    with _engine_lock:
        if payload.only_file:
            stem = Path(payload.only_file).stem
            filters = MetadataFilters(filters=[ExactMatchFilter(key="filename", value=stem)])
            engine = VEC_INDEX.as_query_engine(
                similarity_top_k=payload.top_k,
                response_mode=payload.response_mode,
                include_sources=True,
                filters=filters,
            )
        else:
            engine = VEC_INDEX.as_query_engine(
                similarity_top_k=payload.top_k,
                response_mode=payload.response_mode,
                include_sources=True,
            )

    resp = engine.query(payload.question)
    answer_text = getattr(resp, "response", None) or str(resp)

    sources: List[QASource] = []
    if hasattr(resp, "source_nodes") and resp.source_nodes:
        for s in resp.source_nodes:
            meta = s.metadata or {}
            preview = s.node.get_content()[:200].replace("\n", " ")
            sources.append(
                QASource(
                    filename=meta.get("filename"),
                    source_type=meta.get("source_type"),
                    page_idx=meta.get("page_idx"),
                    score=getattr(s, "score", None),
                    preview=preview + ("…" if len(preview) == 200 else ""),
                )
            )
    return QAResponse(answer=answer_text, sources=sources)

@app.get("/health")
def health():
    return {"status": "ok", "documents": len(df)}
