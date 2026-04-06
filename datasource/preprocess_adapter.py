"""Adapters to align datasource output with preprocess input contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from datasource.news_repository import NewsRecord


@dataclass
class PreprocessDocument:
    """Normalized document for preprocess stage."""

    doc_id: str
    source_record_id: int
    url: str
    title: str
    raw_text: str
    source_name: str
    source_type: str
    publish_date: str
    author: str
    crawled_at: str
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "source_record_id": self.source_record_id,
            "url": self.url,
            "title": self.title,
            "raw_text": self.raw_text,
            "source_name": self.source_name,
            "source_type": self.source_type,
            "publish_date": self.publish_date,
            "author": self.author,
            "crawled_at": self.crawled_at,
            "metadata": self.metadata,
        }


def to_preprocess_document(record: NewsRecord) -> PreprocessDocument:
    """Convert a `NewsRecord` to preprocess-friendly payload."""
    publish_date = record.publish_date or record.crawled_at.strftime("%Y-%m-%d")
    return PreprocessDocument(
        doc_id=f"news-{record.id}",
        source_record_id=record.id,
        url=record.url,
        title=record.title,
        raw_text=record.content,
        source_name=record.source_name,
        source_type=record.source_type,
        publish_date=publish_date,
        author=record.author or "",
        crawled_at=record.crawled_at.isoformat(),
        metadata={
            "created_time": record.created_time.isoformat() if record.created_time else None,
            "updated_time": record.updated_time.isoformat() if record.updated_time else None,
        },
    )


def to_preprocess_documents(records: List[NewsRecord]) -> List[Dict[str, Any]]:
    """Batch convert records to preprocess dict payloads."""
    return [to_preprocess_document(r).to_dict() for r in records]
