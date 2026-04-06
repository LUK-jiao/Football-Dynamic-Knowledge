"""Datasource service that fetches remote news and prepares preprocess inputs."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from datasource.news_repository import PostgresNewsRepository
from datasource.preprocess_adapter import to_preprocess_documents


class DataSourceService:
    """High-level datasource service for pipeline usage."""

    def __init__(self, repository: Optional[PostgresNewsRepository] = None):
        self.repository = repository or PostgresNewsRepository()

    def fetch_documents_for_preprocess(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
        source_name: Optional[str] = None,
        source_type: Optional[str] = None,
        since_crawled_at: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        records = self.repository.list_news(
            limit=limit,
            offset=offset,
            source_name=source_name,
            source_type=source_type,
            since_crawled_at=since_crawled_at,
        )
        return to_preprocess_documents(records)

    def fetch_incremental_documents(
        self,
        *,
        last_crawled_at: Optional[datetime] = None,
        last_id: Optional[int] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        records = self.repository.list_news_incremental(
            last_crawled_at=last_crawled_at,
            last_id=last_id,
            limit=limit,
        )
        return to_preprocess_documents(records)

    def fetch_documents_by_ids(self, ids: List[int]) -> List[Dict[str, Any]]:
        """Fetch specific news rows by DB id and convert to preprocess documents."""
        records = self.repository.get_news_by_ids(ids)
        return to_preprocess_documents(records)
