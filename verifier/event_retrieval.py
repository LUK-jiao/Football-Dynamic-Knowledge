"""
Retriever helpers for truth validation candidate events.

Keeps high-recall retrieval logic independent from verifier scoring logic.
"""

from __future__ import annotations

from typing import Any, Dict, List

from knowledge_graph.neo4j_reader import Neo4jReader


def find_related_events_for_validation(
    new_event: Dict[str, Any],
    limit: int = 100,
    time_window_days: int = 30,
    reader: Neo4jReader | None = None,
) -> List[Dict[str, Any]]:
    """
    Retrieve related existing events from knowledge graph for truth validation.

    High-recall strategy:
    - participant overlap OR
    - within time window

    Args:
        new_event: Event payload to validate.
        limit: Maximum candidates to return.
        time_window_days: +/- date window around new event.
        reader: Optional injected Neo4jReader for lifecycle control/testing.

    Returns:
        List of verifier-compatible existing events.
    """
    if reader is not None:
        return reader.find_related_events_for_validation(
            new_event=new_event,
            limit=limit,
            time_window_days=time_window_days,
        )

    with Neo4jReader() as local_reader:
        return local_reader.find_related_events_for_validation(
            new_event=new_event,
            limit=limit,
            time_window_days=time_window_days,
        )
