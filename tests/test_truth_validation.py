"""
Unit tests for Truth Validation Model.
"""

import verifier.multi_source_verifier as verifier_module
from verifier.multi_source_verifier import MultiSourceVerifier


def test_initial_confidence_single_source():
    verifier = MultiSourceVerifier()
    event = {
        "event_id": "new-1",
        "sources": [{"source": "Club Official Site", "type": "OFFICIAL"}],
    }

    validated = verifier.validate_event(event, existing_events=[])

    assert validated["validation"]["initial_confidence"] == 1.0
    assert validated["validation"]["current_confidence"] == 1.0
    assert validated["validation"]["status"] == "accepted"


def test_initial_confidence_multi_source_accumulation():
    verifier = MultiSourceVerifier()
    event = {
        "event_id": "new-2",
        "sources": [
            {"source": "Sky Sports", "type": "MEDIA"},
            {"source": "BBC Sport", "type": "MEDIA"},
        ],
    }

    validated = verifier.validate_event(event, existing_events=[])

    # 1 - (1-0.8) * (1-0.55) = 0.91
    assert abs(validated["validation"]["initial_confidence"] - 0.91) < 1e-6


def test_support_propagation_increases_both_sides():
    verifier = MultiSourceVerifier(alpha=0.3, beta=0.4, support_threshold=0.3, conflict_threshold=0.95)

    new_event = {
        "event_id": "new-3",
        "event_description": "Arsenal won 2-1 against Chelsea.",
        "fact_type": "EVENT",
        "title_anchors": "Arsenal vs Chelsea",
        "participants": [{"name": "Arsenal"}, {"name": "Chelsea"}],
        "constraints": [{"type": "MATCH_OUTCOME"}],
        "temporal_anchors": [{"event_date": "2025-01-14"}],
        "sources": [{"source": "Sky Sports", "type": "MEDIA"}],
    }

    old_event = {
        "event_id": "old-3",
        "event_description": "Arsenal defeated Chelsea with score 2-1.",
        "fact_type": "EVENT",
        "title_anchors": "Arsenal vs Chelsea",
        "participants": [{"name": "Arsenal"}, {"name": "Chelsea"}],
        "constraints": [{"type": "MATCH_OUTCOME"}],
        "temporal_anchors": [{"event_date": "2025-01-14"}],
        "confidence_score": 0.6,
        "sources": [{"source": "BBC Sport", "type": "MEDIA"}],
    }

    validated = verifier.validate_event(new_event, existing_events=[old_event])

    assert validated["validation"]["current_confidence"] > validated["validation"]["initial_confidence"]
    updates = validated["validation"]["propagation"]["updated_existing_events"]
    assert len(updates) == 1
    assert updates[0]["new_confidence"] > updates[0]["old_confidence"]


def test_conflict_propagation_suppresses_lower_confidence():
    verifier = MultiSourceVerifier(alpha=0.3, beta=0.4, support_threshold=1.1, conflict_threshold=0.2)

    new_event = {
        "event_id": "new-4",
        "event_description": "Arsenal won 3-1 against Chelsea.",
        "fact_type": "EVENT",
        "title_anchors": "Arsenal vs Chelsea",
        "participants": [{"name": "Arsenal"}, {"name": "Chelsea"}],
        "constraints": [{"type": "MATCH_OUTCOME"}],
        "temporal_anchors": [{"event_date": "2025-01-14"}],
        "sources": [{"source": "Club Official Site", "type": "OFFICIAL"}],
    }

    old_event = {
        "event_id": "old-4",
        "event_description": "Arsenal lost 1-2 against Chelsea.",
        "fact_type": "EVENT",
        "title_anchors": "Arsenal vs Chelsea",
        "participants": [{"name": "Arsenal"}, {"name": "Chelsea"}],
        "constraints": [{"type": "MATCH_OUTCOME"}],
        "temporal_anchors": [{"event_date": "2025-01-14"}],
        "confidence_score": 0.4,
        "sources": [{"source": "Unknown Blog", "type": "BLOG"}],
    }

    validated = verifier.validate_event(new_event, existing_events=[old_event])

    conflicts = validated["validation"]["relation_analysis"]["conflicts"]
    assert len(conflicts) == 1

    updates = validated["validation"]["propagation"]["updated_existing_events"]
    assert len(updates) == 1
    assert updates[0]["new_confidence"] < updates[0]["old_confidence"]


def test_validation_output_contract_shape():
    verifier = MultiSourceVerifier()

    event = {
        "event_id": "new-5",
        "event_description": "Manager was appointed.",
        "fact_type": "EVENT",
        "participants": [{"name": "Mikel Arteta"}],
        "constraints": [{"type": "APPOINTMENT_EVENT"}],
        "temporal_anchors": [{"event_date": "2025-01-01"}],
        "sources": [{"source": "Sky Sports", "type": "MEDIA"}],
    }

    validated = verifier.validate_event(event, existing_events=[])
    v = validated["validation"]

    assert "initial_confidence" in v
    assert "current_confidence" in v
    assert "relation_analysis" in v
    assert "propagation" in v
    assert "supports" in v["relation_analysis"]
    assert "conflicts" in v["relation_analysis"]


def test_validate_event_auto_fetch_existing_events(monkeypatch):
    verifier = MultiSourceVerifier(alpha=0.3, beta=0.4, support_threshold=0.3, conflict_threshold=0.95)

    new_event = {
        "event_id": "new-auto-1",
        "event_description": "Arsenal won 2-1 against Chelsea.",
        "fact_type": "EVENT",
        "title_anchors": "Arsenal vs Chelsea",
        "participants": [{"name": "Arsenal"}, {"name": "Chelsea"}],
        "constraints": [{"type": "MATCH_OUTCOME"}],
        "temporal_anchors": [{"event_date": "2025-01-14"}],
        "sources": [{"source": "Sky Sports", "type": "MEDIA"}],
    }

    old_event = {
        "event_id": "old-auto-1",
        "event_description": "Arsenal defeated Chelsea with score 2-1.",
        "fact_type": "EVENT",
        "title_anchors": "Arsenal vs Chelsea",
        "participants": [{"name": "Arsenal"}, {"name": "Chelsea"}],
        "constraints": [{"type": "MATCH_OUTCOME"}],
        "temporal_anchors": [{"event_date": "2025-01-14"}],
        "confidence_score": 0.6,
        "sources": [{"source": "BBC Sport", "type": "MEDIA"}],
    }

    calls = {"count": 0}

    def fake_retrieval(new_event, limit=100, time_window_days=30, reader=None):
        calls["count"] += 1
        return [old_event]

    monkeypatch.setattr(verifier_module, "find_related_events_for_validation", fake_retrieval)

    validated = verifier.validate_event(new_event, existing_events=None)

    assert calls["count"] == 1
    updates = validated["validation"]["propagation"]["updated_existing_events"]
    assert len(updates) == 1
