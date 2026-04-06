from datetime import datetime

from datasource.news_repository import NewsRecord, normalize_publish_date
from datasource.preprocess_adapter import to_preprocess_document
from datasource.service import DataSourceService


def _sample_record(**overrides):
    base = NewsRecord(
        id=1,
        url="https://example.com/news/1",
        title="Arsenal beat Chelsea",
        content="Arsenal defeated Chelsea 2-1 at Emirates.",
        publish_date="2025-01-14",
        source_name="Sky Sports",
        source_type="MEDIA",
        author="Reporter",
        crawled_at=datetime(2025, 1, 15, 8, 30, 0),
        created_time=datetime(2025, 1, 15, 8, 31, 0),
        updated_time=datetime(2025, 1, 15, 8, 31, 0),
    )
    for key, value in overrides.items():
        setattr(base, key, value)
    return base


def test_normalize_publish_date():
    assert normalize_publish_date("2025-01-14") == "2025-01-14"
    assert normalize_publish_date("2025/01/14") == "2025-01-14"
    assert normalize_publish_date("2025-01") == "2025-01-01"
    assert normalize_publish_date("2025") == "2025-01-01"
    assert normalize_publish_date("  ") is None
    assert normalize_publish_date("unknown") is None


def test_to_preprocess_document_fallback_publish_date():
    record = _sample_record(publish_date=None)
    doc = to_preprocess_document(record)

    assert doc.doc_id == "news-1"
    assert doc.source_record_id == 1
    assert doc.raw_text == record.content
    assert doc.publish_date == "2025-01-15"  # fallback to crawled_at date
    assert doc.crawled_at == "2025-01-15T08:30:00"
    assert "created_time" in doc.metadata


class _FakeRepository:
    def list_news(self, **kwargs):
        return [_sample_record(id=101), _sample_record(id=102)]

    def list_news_incremental(self, **kwargs):
        return [_sample_record(id=201)]


def test_datasource_service_returns_preprocess_docs():
    service = DataSourceService(repository=_FakeRepository())

    docs = service.fetch_documents_for_preprocess(limit=2)
    assert len(docs) == 2
    assert docs[0]["doc_id"] == "news-101"
    assert docs[0]["source_record_id"] == 101
    assert docs[0]["title"] == "Arsenal beat Chelsea"
    assert docs[0]["raw_text"]
    assert "metadata" in docs[0]

    inc_docs = service.fetch_incremental_documents(limit=1)
    assert len(inc_docs) == 1
    assert inc_docs[0]["doc_id"] == "news-201"
