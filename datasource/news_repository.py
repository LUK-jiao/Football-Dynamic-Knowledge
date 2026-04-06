"""PostgreSQL datasource reader for remote crawler news table.

This module provides:
1) A typed record model for rows in `news` table.
2) Repository methods for list/incremental reads.
3) Date normalization helpers for downstream preprocess alignment.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Iterable, List, Mapping, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from core.config import get_settings


@dataclass
class NewsRecord:
    """Normalized row from `news` table."""

    id: int
    url: str
    title: str
    content: str
    publish_date: Optional[str]
    source_name: str
    source_type: str
    author: Optional[str]
    crawled_at: datetime
    created_time: Optional[datetime]
    updated_time: Optional[datetime]


def normalize_publish_date(value: Optional[str]) -> Optional[str]:
    """Normalize publish_date text into `YYYY-MM-DD` when possible.

    Accepted examples:
    - 2025-01-14
    - 2025/01/14
    - 2025-01
    - 2025

    Returns `None` when value is empty or unparseable.
    """
    if not value:
        return None

    raw = value.strip()
    if not raw:
        return None

    candidates = [
        ("%Y-%m-%d", "%Y-%m-%d"),
        ("%Y/%m/%d", "%Y-%m-%d"),
        ("%Y-%m", "%Y-%m-01"),
        ("%Y/%m", "%Y-%m-01"),
        ("%Y", "%Y-01-01"),
    ]

    for input_fmt, output_fmt in candidates:
        try:
            dt = datetime.strptime(raw, input_fmt)
            return dt.strftime(output_fmt)
        except ValueError:
            continue

    # If already starts with ISO date prefix, keep date part.
    if len(raw) >= 10 and raw[4] == "-" and raw[7] == "-":
        return raw[:10]

    return None


class PostgresNewsRepository:
    """Read-only repository for `public.news` table."""

    def __init__(self, database_url: Optional[str] = None, *, engine: Optional[Engine] = None):
        settings = get_settings()
        self.database_url = database_url or settings.database_url
        self.engine = engine or create_engine(self.database_url, pool_pre_ping=True, future=True)

    def list_news(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
        source_name: Optional[str] = None,
        source_type: Optional[str] = None,
        since_crawled_at: Optional[datetime] = None,
    ) -> List[NewsRecord]:
        """Fetch news records with optional filters and pagination."""
        where: List[str] = []
        params: Dict[str, Any] = {
            "limit": max(1, min(limit, 2000)),
            "offset": max(offset, 0),
        }

        if source_name:
            where.append("source_name = :source_name")
            params["source_name"] = source_name

        if source_type:
            where.append("source_type = :source_type")
            params["source_type"] = source_type

        if since_crawled_at:
            where.append("crawled_at >= :since_crawled_at")
            params["since_crawled_at"] = since_crawled_at

        where_sql = f"WHERE {' AND '.join(where)}" if where else ""

        query = text(
            f"""
            SELECT id, url, title, content, publish_date, source_name, source_type, author,
                   crawled_at, created_time, updated_time
            FROM news
            {where_sql}
            ORDER BY crawled_at DESC, id DESC
            LIMIT :limit OFFSET :offset
            """
        )

        with self.engine.connect() as conn:
            rows = conn.execute(query, params).mappings().all()

        return [self._to_record(row) for row in rows]

    def list_news_incremental(
        self,
        *,
        last_crawled_at: Optional[datetime] = None,
        last_id: Optional[int] = None,
        limit: int = 100,
    ) -> List[NewsRecord]:
        """Incremental fetch based on `(crawled_at, id)` cursor."""
        params: Dict[str, Any] = {"limit": max(1, min(limit, 2000))}
        cursor_where = ""

        if last_crawled_at and last_id is not None:
            cursor_where = (
                "WHERE (crawled_at > :last_crawled_at) "
                "OR (crawled_at = :last_crawled_at AND id > :last_id)"
            )
            params["last_crawled_at"] = last_crawled_at
            params["last_id"] = last_id

        query = text(
            f"""
            SELECT id, url, title, content, publish_date, source_name, source_type, author,
                   crawled_at, created_time, updated_time
            FROM news
            {cursor_where}
            ORDER BY crawled_at ASC, id ASC
            LIMIT :limit
            """
        )

        with self.engine.connect() as conn:
            rows = conn.execute(query, params).mappings().all()

        return [self._to_record(row) for row in rows]

    def get_news_by_ids(self, ids: Iterable[int]) -> List[NewsRecord]:
        """Fetch records by id list."""
        id_list = [int(v) for v in ids]
        if not id_list:
            return []

        query = text(
            """
            SELECT id, url, title, content, publish_date, source_name, source_type, author,
                   crawled_at, created_time, updated_time
            FROM news
            WHERE id = ANY(:ids)
            ORDER BY id ASC
            """
        )

        with self.engine.connect() as conn:
            rows = conn.execute(query, {"ids": id_list}).mappings().all()

        return [self._to_record(row) for row in rows]

    @staticmethod
    def _to_record(row: Mapping[str, Any]) -> NewsRecord:
        return NewsRecord(
            id=int(row["id"]),
            url=row["url"],
            title=row["title"],
            content=row["content"],
            publish_date=normalize_publish_date(row.get("publish_date")),
            source_name=row.get("source_name") or "Premier League",
            source_type=row.get("source_type") or "OFFICIAL",
            author=row.get("author"),
            crawled_at=row["crawled_at"],
            created_time=row.get("created_time"),
            updated_time=row.get("updated_time"),
        )
