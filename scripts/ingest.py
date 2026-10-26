#!/usr/bin/env python3
"""Build or rebuild the ChromaDB vector index from knowledge base documents."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.rag import ingest_documents
from app.config import settings


def main():
    """Run the ingestion pipeline."""
    kb_dir = Path(settings.knowledge_base_dir)
    
    print("=" * 50)
    print("  UniAssist Knowledge Base Ingestion")
    print("=" * 50)
    print(f"Knowledge base directory: {kb_dir.resolve()}")
    
    if not kb_dir.exists():
        print(f"ERROR: Directory not found: {kb_dir}")
        sys.exit(1)
    
    files = list(kb_dir.iterdir())
    supported = [f for f in files if f.suffix.lower() in {".md", ".txt", ".pdf", ".docx"}]
    print(f"Found {len(supported)} supported document(s)")
    
    for f in sorted(supported):
        print(f"  - {f.name} ({f.stat().st_size:,} bytes)")
    
    print("\nIngesting...")
    count = ingest_documents()
    
    if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

    print(f"\n[OK] Successfully ingested {count} chunks")
    print(f"  ChromaDB directory: {Path(settings.chroma_persist_dir).resolve()}")


if __name__ == "__main__":
    main()

