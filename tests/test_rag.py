"""Unit tests for RAG pipeline: chunking, metadata extraction, and retrieval."""

import tempfile
from pathlib import Path

from app.rag import (
    _estimate_tokens,
    _extract_sections,
    chunk_text,
    process_document,
)


def test_estimate_tokens():
    text = "Hello world this is a test string"
    tokens = _estimate_tokens(text)
    assert tokens > 0
    assert tokens == len(text) // 4


def test_extract_sections():
    markdown = """# Admissions Policy

## Eligibility Criteria
Candidates must have scored at least 60% in 10+2.

## Application Process
Applications must be submitted via the online portal.
"""
    sections = _extract_sections(markdown, "admissions.md")
    assert len(sections) == 2
    assert sections[0]["title"] == "Admissions Policy"
    assert sections[0]["section"] == "Eligibility Criteria"
    assert "60%" in sections[0]["text"]
    assert sections[1]["section"] == "Application Process"


def test_chunk_text():
    short_text = "This is a short paragraph that easily fits in one chunk."
    chunks = chunk_text(short_text, chunk_size=100, chunk_overlap=20)
    assert len(chunks) == 1
    assert chunks[0] == short_text

    # Long text with paragraphs
    paras = [f"Paragraph {i}: " + ("word " * 60) for i in range(10)]
    long_text = "\n\n".join(paras)
    chunks = chunk_text(long_text, chunk_size=100, chunk_overlap=20)
    assert len(chunks) > 1


def test_process_document_markdown():
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write("# Campus Hostel\n\n## Mess Timings\nBreakfast: 7:30 AM to 9:00 AM\nDinner: 7:30 PM to 9:30 PM\n")
        temp_path = f.name

    try:
        results = process_document(temp_path)
        assert len(results) >= 1
        assert "Mess Timings" in results[0]["metadata"]["section"]
        assert "Breakfast" in results[0]["text"]
    finally:
        Path(temp_path).unlink(missing_ok=True)
