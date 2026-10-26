"""RAG module: document ingestion, chunking, ChromaDB storage and retrieval."""

import hashlib
import logging
import os
import re
from pathlib import Path
from typing import Optional

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import settings

logger = logging.getLogger("uniassist.rag")

# Module-level ChromaDB client and collection
_chroma_client: chromadb.ClientAPI | None = None
_collection: chromadb.Collection | None = None

COLLECTION_NAME = "uniassist_knowledge"


def get_chroma_client() -> chromadb.ClientAPI:
    """Return singleton persistent ChromaDB client."""
    global _chroma_client
    if _chroma_client is None:
        persist_dir = settings.chroma_persist_dir
        os.makedirs(persist_dir, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(
            path=persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        logger.info(f"ChromaDB initialized at {persist_dir}")
    return _chroma_client


def get_collection() -> chromadb.Collection:
    """Get or create the knowledge base collection."""
    global _collection
    if _collection is None:
        client = get_chroma_client()
        _collection = client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(f"Collection '{COLLECTION_NAME}' has {_collection.count()} documents")
    return _collection


def get_index_count() -> int:
    """Return the number of documents in the index."""
    try:
        return get_collection().count()
    except Exception:
        return 0


# ── Chunking ────────────────────────────────────────────────────────────────

def _estimate_tokens(text: str) -> int:
    """Rough token estimate (1 token ≈ 4 chars for English)."""
    return len(text) // 4


def _extract_sections(content: str, filename: str) -> list[dict]:
    """
    Split markdown content into sections based on headings.
    
    Returns list of dicts: {title, section, text, source}
    """
    # Extract top-level title
    title_match = re.match(r"^#\s+(.+)", content)
    doc_title = title_match.group(1).strip() if title_match else filename

    sections = []
    current_section = "Introduction"
    current_text = []

    for line in content.split("\n"):
        heading_match = re.match(r"^#{1,3}\s+(.+)", line)
        if heading_match:
            # Save previous section if it has content
            text = "\n".join(current_text).strip()
            if text:
                sections.append({
                    "title": doc_title,
                    "section": current_section,
                    "text": text,
                    "source": filename,
                })
            current_section = heading_match.group(1).strip()
            current_text = []
        else:
            current_text.append(line)

    # Don't forget the last section
    text = "\n".join(current_text).strip()
    if text:
        sections.append({
            "title": doc_title,
            "section": current_section,
            "text": text,
            "source": filename,
        })

    return sections


def chunk_text(
    text: str,
    chunk_size: int = 500,
    chunk_overlap: int = 80,
) -> list[str]:
    """
    Split text into chunks of approximately `chunk_size` tokens
    with `chunk_overlap` token overlap. Splits on paragraph/sentence boundaries.
    """
    if _estimate_tokens(text) <= chunk_size:
        return [text.strip()] if text.strip() else []

    # Split on double newlines (paragraphs) first
    paragraphs = re.split(r"\n\s*\n", text)
    
    chunks = []
    current_chunk: list[str] = []
    current_tokens = 0

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        para_tokens = _estimate_tokens(para)

        if current_tokens + para_tokens > chunk_size and current_chunk:
            chunks.append("\n\n".join(current_chunk))
            # Keep overlap: take last paragraph(s) for overlap
            overlap_tokens = 0
            overlap_parts: list[str] = []
            for p in reversed(current_chunk):
                overlap_tokens += _estimate_tokens(p)
                overlap_parts.insert(0, p)
                if overlap_tokens >= chunk_overlap:
                    break
            current_chunk = overlap_parts
            current_tokens = overlap_tokens

        current_chunk.append(para)
        current_tokens += para_tokens

    if current_chunk:
        chunks.append("\n\n".join(current_chunk))

    return [c.strip() for c in chunks if c.strip()]


def process_document(filepath: str) -> list[dict]:
    """
    Read a document file and return chunked sections with metadata.
    
    Supports: .md, .txt, .pdf, .docx
    Returns list of dicts: {id, text, metadata}
    """
    path = Path(filepath)
    filename = path.name
    content = ""

    if path.suffix.lower() == ".pdf":
        try:
            from pypdf import PdfReader
            reader = PdfReader(str(path))
            content = "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as e:
            logger.error(f"Failed to read PDF {filename}: {e}")
            return []

    elif path.suffix.lower() == ".docx":
        try:
            from docx import Document
            doc = Document(str(path))
            content = "\n".join(para.text for para in doc.paragraphs)
        except Exception as e:
            logger.error(f"Failed to read DOCX {filename}: {e}")
            return []

    elif path.suffix.lower() in (".md", ".txt"):
        content = path.read_text(encoding="utf-8")

    else:
        logger.warning(f"Unsupported file type: {path.suffix}")
        return []

    if not content.strip():
        logger.warning(f"Empty document: {filename}")
        return []

    # Extract sections and chunk
    sections = _extract_sections(content, filename)
    results = []

    for section in sections:
        chunks = chunk_text(
            section["text"],
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
        )
        for i, chunk in enumerate(chunks):
            chunk_id = hashlib.md5(
                f"{filename}:{section['section']}:{i}".encode()
            ).hexdigest()
            results.append({
                "id": chunk_id,
                "text": chunk,
                "metadata": {
                    "source": section["source"],
                    "title": section["title"],
                    "section": section["section"],
                    "chunk_index": i,
                },
            })

    return results


def ingest_documents(knowledge_dir: str | None = None) -> int:
    """
    Ingest all documents from the knowledge base directory into ChromaDB.
    
    Returns the number of chunks ingested.
    """
    kb_dir = Path(knowledge_dir or settings.knowledge_base_dir)
    if not kb_dir.exists():
        logger.error(f"Knowledge base directory not found: {kb_dir}")
        return 0

    collection = get_collection()

    # Clear existing data
    existing = collection.count()
    if existing > 0:
        logger.info(f"Clearing {existing} existing documents...")
        # Delete all existing
        all_ids = collection.get()["ids"]
        if all_ids:
            collection.delete(ids=all_ids)

    all_chunks = []
    supported = {".md", ".txt", ".pdf", ".docx"}

    for filepath in sorted(kb_dir.iterdir()):
        if filepath.suffix.lower() in supported:
            chunks = process_document(str(filepath))
            all_chunks.extend(chunks)
            logger.info(f"Processed {filepath.name}: {len(chunks)} chunks")

    if not all_chunks:
        logger.warning("No chunks to ingest!")
        return 0

    # Batch insert into ChromaDB
    batch_size = 100
    for i in range(0, len(all_chunks), batch_size):
        batch = all_chunks[i: i + batch_size]
        collection.add(
            ids=[c["id"] for c in batch],
            documents=[c["text"] for c in batch],
            metadatas=[c["metadata"] for c in batch],
        )

    total = collection.count()
    logger.info(f"Ingested {total} chunks from {kb_dir}")
    return total


def retrieve(
    query: str,
    top_k: int | None = None,
) -> list[dict]:
    """
    Retrieve relevant chunks for a query.
    
    Returns list of dicts: {text, metadata, score}
    Score is cosine distance (lower = more similar).
    """
    k = top_k or settings.top_k
    collection = get_collection()

    if collection.count() == 0:
        logger.warning("Empty collection, no results to return")
        return []

    results = collection.query(
        query_texts=[query],
        n_results=min(k, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    retrieved = []
    if results and results["documents"]:
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            retrieved.append({
                "text": doc,
                "metadata": meta,
                "score": dist,  # cosine distance
            })

    return retrieved
