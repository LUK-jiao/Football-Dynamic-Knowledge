"""Datasource layer exports."""

from datasource.news_repository import NewsRecord, PostgresNewsRepository, normalize_publish_date
from datasource.preprocess_adapter import PreprocessDocument, to_preprocess_document, to_preprocess_documents
from datasource.service import DataSourceService

__all__ = [
    "NewsRecord",
    "PostgresNewsRepository",
    "normalize_publish_date",
    "PreprocessDocument",
    "to_preprocess_document",
    "to_preprocess_documents",
    "DataSourceService",
]
