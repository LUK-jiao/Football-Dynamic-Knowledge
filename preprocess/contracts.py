"""Canonical data contracts for preprocess module."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PreChunkInput:
    """Sentence-level unit produced by splitter and consumed by chunker."""

    sentence_id: str
    sentence_order: int
    sentence_text: str


@dataclass
class SemanticChunkDocument:
    """Chunk-level document produced by semantic chunker for extractor input."""

    doc_id: str
    block_id: str
    block_text: str
    title: str
    source_name: str
    source_type: str
    publish_date: str
    author: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_event_decomposition_input(self) -> Dict[str, Any]:
        """Convert to extractor event decomposition input shape."""
        payload: Dict[str, Any] = {
            "doc_id": self.doc_id,
            "block_id": self.block_id,
            "text": self.block_text,
            "title": self.title,
            "source_name": self.source_name,
            "source_type": self.source_type,
            "publish_date": self.publish_date,
            "author": self.author,
        }
        if self.metadata:
            payload["metadata"] = self.metadata
        return payload


def build_prechunk_inputs(sentences: List[str], *, doc_id: str) -> List[PreChunkInput]:
    """Build ordered sentence units from plain sentence strings."""
    return [
        PreChunkInput(
            sentence_id=f"{doc_id}-s{idx:03d}",
            sentence_order=idx,
            sentence_text=sentence,
        )
        for idx, sentence in enumerate(sentences, start=1)
        if sentence and sentence.strip()
    ]


def from_datasource_document(document: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize datasource article document into preprocess-required fields."""
    return {
        "doc_id": document.get("doc_id", ""),
        "title": document.get("title", ""),
        "raw_text": document.get("raw_text", ""),
        "source_name": document.get("source_name", ""),
        "source_type": document.get("source_type", ""),
        "publish_date": document.get("publish_date", ""),
        "author": document.get("author", ""),
        "metadata": document.get("metadata") or {},
    }


def build_semantic_chunk_documents(
    *,
    doc_id: str,
    title: str,
    source_name: str,
    source_type: str,
    publish_date: str,
    author: str,
    chunk_texts: List[str],
    metadata: Optional[Dict[str, Any]] = None,
) -> List[SemanticChunkDocument]:
    """Construct semantic chunk documents from generated chunk texts."""
    return [
        SemanticChunkDocument(
            doc_id=doc_id,
            block_id=f"{doc_id}-block{idx:03d}",
            block_text=text,
            title=title,
            source_name=source_name,
            source_type=source_type,
            publish_date=publish_date,
            author=author,
            metadata=metadata or {},
        )
        for idx, text in enumerate(chunk_texts, start=1)
        if text and text.strip()
    ]
