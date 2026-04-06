"""
Neo4j read-side access layer for football knowledge graph.

Contains query-oriented methods and candidate retrieval for truth validation.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple

from neo4j import Driver, GraphDatabase


class Neo4jReader:
    """Neo4j graph database reader for football events."""

    def __init__(
        self,
        uri: str = "bolt://localhost:7687",
        user: str = "neo4j",
        password: str = "password",
    ):
        self.driver: Driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        """Close the database connection."""
        if self.driver:
            self.driver.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def _parse_date(self, date_str: Optional[str]) -> Optional[date]:
        """Parse date string to date object."""
        if not date_str:
            return None
        try:
            if len(date_str) == 4:  # YYYY
                return date(int(date_str), 1, 1)
            if len(date_str) == 7:  # YYYY-MM
                year, month = date_str.split("-")
                return date(int(year), int(month), 1)
            year, month, day = date_str.split("-")
            return date(int(year), int(month), int(day))
        except (ValueError, IndexError):
            return None

    def _extract_new_event_query_context(
        self,
        new_event: Dict[str, Any],
        time_window_days: int,
    ) -> Tuple[List[str], Optional[str], Optional[str], Optional[str]]:
        """Extract participants and date window from new event payload."""
        participants = new_event.get("participants") or []
        participant_names_lower = [
            str(p.get("name", "")).strip().lower()
            for p in participants
            if p.get("name")
        ]

        anchor = (new_event.get("temporal_anchors") or [{}])[0]
        anchor_date = (
            self._parse_date(anchor.get("event_date"))
            or self._parse_date(anchor.get("valid_from"))
            or self._parse_date(anchor.get("valid_to"))
            or self._parse_date(new_event.get("publish_date"))
        )

        start_date = None
        end_date = None
        if anchor_date:
            start_date = (anchor_date - timedelta(days=time_window_days)).isoformat()
            end_date = (anchor_date + timedelta(days=time_window_days)).isoformat()

        event_id = new_event.get("event_id")
        return participant_names_lower, start_date, end_date, event_id

    def find_related_events_for_validation(
        self,
        new_event: Dict[str, Any],
        limit: int = 100,
        time_window_days: int = 30,
    ) -> List[Dict[str, Any]]:
        """
        Find high-recall related events for truth validation.

        Strategy (OR recall):
        - participant overlap hit OR
        - within time window hit

        Args:
            new_event: Incoming event payload for validation.
            limit: Maximum candidate events to return.
            time_window_days: +/- days around new event date.

        Returns:
            Verifier-compatible event dictionaries.
        """
        participant_names_lower, start_date, end_date, new_event_id = self._extract_new_event_query_context(
            new_event,
            time_window_days,
        )

        # AND logic requires both participant condition and time window condition.
        if not participant_names_lower or not (start_date and end_date):
            return []

        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (e:Event)
                OPTIONAL MATCH (e)-[:INVOLVES]->(ent:Entity)
                OPTIONAL MATCH (e)-[:REPORTED_BY]->(src0:Source)
                WITH e,
                     collect(DISTINCT ent) AS ents,
                     collect(DISTINCT src0) AS src_candidates
                WITH e,
                     ents,
                     src_candidates,
                     coalesce(e.event_date, head([s IN src_candidates WHERE s.publish_date IS NOT NULL | s.publish_date])) AS effective_date,
                     [n IN [x IN ents | toLower(x.name)] WHERE n IN $participant_names_lower] AS matched_participants,
                     CASE
                         WHEN $start_date IS NOT NULL AND $end_date IS NOT NULL
                              AND coalesce(e.event_date, head([s IN src_candidates WHERE s.publish_date IS NOT NULL | s.publish_date])) IS NOT NULL
                         THEN coalesce(e.event_date, head([s IN src_candidates WHERE s.publish_date IS NOT NULL | s.publish_date])) >= date($start_date)
                              AND coalesce(e.event_date, head([s IN src_candidates WHERE s.publish_date IS NOT NULL | s.publish_date])) <= date($end_date)
                         ELSE false
                     END AS time_hit
                WHERE
                    ($new_event_id IS NULL OR e.event_id <> $new_event_id)
                    AND (
                        size($participant_names_lower) > 0
                        AND size(matched_participants) > 0
                        AND time_hit
                    )
                OPTIONAL MATCH (e)-[:INVOLVES]->(ent2:Entity)
                OPTIONAL MATCH (e)-[:REPORTED_BY]->(src:Source)
                OPTIONAL MATCH (e)-[:CONSTRAINS]->(con:ConstraintAnchor)
                OPTIONAL MATCH (e)-[:HAS_TITLE_ANCHOR]->(title:TitleAnchor)
                WITH e,
                     effective_date,
                     size(matched_participants) AS participant_hits,
                     time_hit,
                     collect(DISTINCT ent2) AS entities,
                     collect(DISTINCT src) AS sources,
                     collect(DISTINCT con) AS constraints,
                     collect(DISTINCT title) AS titles
                RETURN e,
                       effective_date,
                       participant_hits,
                       time_hit,
                       entities,
                       sources,
                       constraints,
                       titles
                ORDER BY participant_hits DESC, time_hit DESC, effective_date DESC
                LIMIT $limit
                """,
                participant_names_lower=participant_names_lower,
                start_date=start_date,
                end_date=end_date,
                new_event_id=new_event_id,
                limit=limit,
            )

            candidates: List[Dict[str, Any]] = []
            for record in result:
                event = dict(record["e"])
                entities = [dict(e) for e in record["entities"] if e]
                sources = [dict(s) for s in record["sources"] if s]
                constraints = [dict(c) for c in record["constraints"] if c]
                titles = [dict(t) for t in record["titles"] if t]

                mapped = {
                    "event_id": event.get("event_id"),
                    "event_description": event.get("description") or event.get("event_description"),
                    "fact_type": event.get("fact_type"),
                    "title_anchors": event.get("title") or event.get("title_anchors"),
                    "participants": [
                        {"name": e.get("name"), "type": e.get("type")}
                        for e in entities
                        if e.get("name")
                    ],
                    "constraints": [
                        {"type": c.get("type")}
                        for c in constraints
                        if c.get("type")
                    ],
                    "temporal_anchors": [
                        {
                            "event_date": (
                                str(event.get("event_date"))
                                if event.get("event_date")
                                else (str(record.get("effective_date")) if record.get("effective_date") else None)
                            ),
                            "valid_from": str(event.get("valid_from")) if event.get("valid_from") else None,
                            "valid_to": str(event.get("valid_to")) if event.get("valid_to") else None,
                        }
                    ],
                    "sources": [
                        {
                            "name": s.get("name") or s.get("source"),
                            "source": s.get("name") or s.get("source"),
                            "type": s.get("type"),
                            "author": s.get("author"),
                            "publish_date": str(s.get("publish_date")) if s.get("publish_date") else None,
                        }
                        for s in sources
                        if s.get("name") or s.get("source")
                    ],
                    "confidence_score": event.get("current_confidence")
                    if event.get("current_confidence") is not None
                    else event.get("confidence_score"),
                    "_retrieval_meta": {
                        "participant_hits": record["participant_hits"],
                        "time_hit": record["time_hit"],
                        "effective_date": str(record["effective_date"]) if record["effective_date"] else None,
                        "title_candidates": [t.get("title") for t in titles if t.get("title")],
                    },
                }
                candidates.append(mapped)

            return candidates

    def get_event_full_view(self, event_id: str) -> Optional[Dict[str, Any]]:
        """Get complete event with all relationships."""
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (e:Event {event_id: $event_id})
                OPTIONAL MATCH (e)-[:INVOLVES]->(entity:Entity)
                OPTIONAL MATCH (e)-[:REPORTED_BY]->(source:Source)
                OPTIONAL MATCH (e)-[:CONSTRAINS]->(constraint:ConstraintAnchor)
                OPTIONAL MATCH (e)-[:HAS_TITLE_ANCHOR]->(title:TitleAnchor)
                RETURN e,
                       collect(DISTINCT entity) AS entities,
                       collect(DISTINCT source) AS sources,
                       collect(DISTINCT constraint) AS constraints,
                       collect(DISTINCT title) AS titles
                """,
                event_id=event_id,
            )

            record = result.single()
            if not record:
                return None

            event = dict(record["e"])
            return {
                "event": event,
                "entities": [dict(e) for e in record["entities"] if e],
                "sources": [dict(s) for s in record["sources"] if s],
                "constraints": [dict(c) for c in record["constraints"] if c],
                "titles": [dict(t) for t in record["titles"] if t],
            }

    def get_entity_events(self, entity_id: str) -> List[Dict[str, Any]]:
        """Get all events involving a specific entity."""
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (e:Event)-[:INVOLVES]->(entity:Entity {entity_id: $entity_id})
                RETURN e
                ORDER BY e.created_at DESC
                """,
                entity_id=entity_id,
            )

            return [dict(record["e"]) for record in result]

    def get_events_by_anchor(self, anchor_type: str) -> List[Dict[str, Any]]:
        """Get all events with a specific constraint anchor."""
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (e:Event)-[:CONSTRAINS]->(c:ConstraintAnchor {type: $anchor_type})
                RETURN e
                ORDER BY e.created_at DESC
                """,
                anchor_type=anchor_type,
            )

            return [dict(record["e"]) for record in result]

    def get_events_by_title_anchor(self, title: str) -> List[Dict[str, Any]]:
        """Get all events with a specific title anchor."""
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (e:Event)-[:HAS_TITLE_ANCHOR]->(t:TitleAnchor {title: $title})
                RETURN e
                ORDER BY e.created_at DESC
                """,
                title=title,
            )

            return [dict(record["e"]) for record in result]

    def get_events_by_time_range(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        """Get events within a time range."""
        with self.driver.session() as session:
            if start_date and end_date:
                result = session.run(
                    """
                    MATCH (e:Event)
                    WHERE e.event_date >= $start_date AND e.event_date <= $end_date
                    RETURN e
                    ORDER BY e.event_date DESC
                    """,
                    start_date=start_date,
                    end_date=end_date,
                )
            elif start_date:
                result = session.run(
                    """
                    MATCH (e:Event)
                    WHERE e.event_date >= $start_date
                    RETURN e
                    ORDER BY e.event_date DESC
                    """,
                    start_date=start_date,
                )
            elif end_date:
                result = session.run(
                    """
                    MATCH (e:Event)
                    WHERE e.event_date <= $end_date
                    RETURN e
                    ORDER BY e.event_date DESC
                    """,
                    end_date=end_date,
                )
            else:
                result = session.run(
                    """
                    MATCH (e:Event)
                    WHERE e.event_date IS NOT NULL
                    RETURN e
                    ORDER BY e.event_date DESC
                    """
                )

            return [dict(record["e"]) for record in result]
