from typing import Any, Dict, List

import pytest

from extractor_v1.anchor_extractor import AnchorExtractor
from extractor_v1.event_decomposition import EventDecomposer
from extractor_v1.ollama_backend import OllamaBackend
from knowledge_graph.neo4j_writer import Neo4jWriter


class _FakeTx:
    def __init__(self) -> None:
        self.calls: List[Dict[str, Any]] = []

    def run(self, query: str, **kwargs: Any) -> None:
        self.calls.append({"query": query, "kwargs": kwargs})


def test_event_decomposer_postprocess_eventunit_fields() -> None:
    decomposer = EventDecomposer()
    decomposer.backend.decompose_events = lambda block: {
        "events": [
            {
                "event_id": "model-generated-id",
                "title_anchors": "Arsenal vs Chelsea",
                "event_description": "Arsenal beat Chelsea 2-1.",
                "block_text": "Arsenal beat Chelsea 2-1.",
                "source_name": "Sky Sports",
                "source_type": "MEDIA",
                "publish_date": "2025-01-14",
                "author": "Reporter",
            }
        ]
    }

    block = {
        "doc_id": "news-12345",
        "chunk_id": "news-12345:c001",
        "text": "Arsenal beat Chelsea 2-1.",
        "source_name": "Sky Sports",
        "source_type": "MEDIA",
        "publish_date": "2025-01-14",
        "author": "Reporter",
    }

    result = decomposer.decompose(block)
    event = result["events"][0]

    assert event["doc_id"] == "news-12345"
    assert event["chunk_id"] == "news-12345:c001"
    assert event["event_index"] == 1
    assert event["event_id"] == "news-12345:c001:e001"


def test_ollama_backend_decompose_events_chunk_id_alignment() -> None:
    backend = OllamaBackend(model="mock-model")
    backend._call_ollama = lambda messages: (
        '{"events":[{"event_id":"x","title_anchors":"A","event_description":"B","block_text":"B"}]}'
    )

    block = {
        "doc_id": "news-88",
        "chunk_id": "news-88:c002",
        "text": "Sample text.",
        "source_name": "BBC Sport",
        "source_type": "MEDIA",
        "publish_date": "2025-02-01",
        "author": "Author",
        "title": "Sample",
    }

    result = backend.decompose_events(block)
    event = result["events"][0]

    assert event["event_id"] == "news-88:c002:e001"
    assert event["chunk_id"] == "news-88:c002"
    assert event["doc_id"] == "news-88"
    assert event["event_index"] == 1
    assert event["source_name"] == "BBC Sport"
    assert event["source_type"] == "MEDIA"


def test_anchor_extractor_requires_eventunit_fields() -> None:
    extractor = AnchorExtractor()
    extractor.backend.extract_anchors = lambda event: {
        "event_id": event["event_id"],
        "title_anchors": event["title_anchors"],
        "event_description": event["event_description"],
        "participants": [],
        "fact_type": "EVENT",
        "constraints": [],
        "temporal_anchors": [],
        "sources": [],
    }

    bad_event = {
        "event_id": "news-1:c001:e001",
        "title_anchors": "x",
        "event_description": "x",
        "block_text": "x",
        "publish_date": "2025-01-01",
    }
    with pytest.raises(ValueError):
        extractor.extract_anchors(bad_event)

    ok_event = {
        "event_id": "news-1:c001:e001",
        "title_anchors": "x",
        "event_description": "x",
        "block_text": "x",
        "source_name": "Sky Sports",
        "source_type": "MEDIA",
        "publish_date": "2025-01-01",
        "author": "",
    }
    result = extractor.extract_anchors(ok_event)
    assert "inference_time" in result


def test_neo4j_writer_source_type_fallback_unknown() -> None:
    writer = Neo4jWriter.__new__(Neo4jWriter)
    writer._parse_date = lambda _: None

    tx = _FakeTx()
    payload = {
        "event_id": "news-1:c001:e001",
        "title_anchors": "A",
        "event_description": "B",
        "participants": [],
        "constraints": [],
        "temporal_anchors": [{"event_date": None, "valid_from": None, "valid_to": None}],
        "sources": [{"name": "Sky Sports", "publish_date": "2025-01-01", "author": ""}],
    }

    writer._upsert_event_tx(tx, payload)

    source_calls = [c for c in tx.calls if "source_id" in c["kwargs"]]
    assert source_calls
    assert source_calls[0]["kwargs"]["type"] == "UNKNOWN"
