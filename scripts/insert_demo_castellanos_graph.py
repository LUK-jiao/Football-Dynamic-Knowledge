import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from knowledge_graph.neo4j_writer import Neo4jWriter


def main() -> None:
    # Fixed demo IDs so chapter screenshot/description can reference stable nodes.
    e1_id = "demo-westham-castellanos:e001"
    e2_id = "demo-westham-castellanos:e002"

    event_1 = {
        "event_id": e1_id,
        "title_anchors": "West Ham signs Taty Castellanos",
        "event_description": "West Ham United announce the signing of Argentina forward Taty Castellanos.",
        "fact_type": "EVENT",
        "participants": [
            {"name": "West Ham United", "type": "CLUB"},
            {"name": "Taty Castellanos", "type": "PLAYER"},
        ],
        "constraints": [
            {"type": "PLAYER_MOVEMENT"},
            {"type": "CONTRACT_SIGNING"},
        ],
        "temporal_anchors": [
            {"event_date": "2025-01-15", "valid_from": "2025-01-15", "valid_to": None}
        ],
        "sources": [
            {
                "name": "Premier League Official",
                "type": "OFFICIAL",
                "author": "",
                "publish_date": "2025-01-15",
            }
        ],
        "confidence_score": 0.88,
    }

    event_2 = {
        "event_id": e2_id,
        "title_anchors": "Castellanos career highlights",
        "event_description": "Castellanos won MLS Cup and Golden Boot in 2021 and scored four against Real Madrid in 2023.",
        "fact_type": "EVENT",
        "participants": [
            {"name": "Taty Castellanos", "type": "PLAYER"},
            {"name": "New York City FC", "type": "CLUB"},
            {"name": "Girona", "type": "CLUB"},
            {"name": "Real Madrid", "type": "CLUB"},
        ],
        "constraints": [
            {"type": "CAREER_ACHIEVEMENT"},
            {"type": "PERFORMANCE_RECORD"},
        ],
        "temporal_anchors": [
            {"event_date": "2023-04-25", "valid_from": "2021-01-01", "valid_to": None}
        ],
        "sources": [
            {
                "name": "Premier League Official",
                "type": "OFFICIAL",
                "author": "",
                "publish_date": "2025-01-15",
            }
        ],
        "confidence_score": 0.79,
    }

    with Neo4jWriter() as writer:
        writer.initialize_constraints()

        # Idempotent reset for this demo pair only
        with writer.driver.session() as session:
            session.run(
                """
                MATCH (e:Event)
                WHERE e.event_id IN $event_ids
                DETACH DELETE e
                """,
                event_ids=[e1_id, e2_id],
            )

        writer.upsert_event(event_1)
        writer.upsert_event(event_2)

        with writer.driver.session() as session:
            summary = session.run(
                """
                MATCH (e:Event)
                WHERE e.event_id IN $event_ids
                OPTIONAL MATCH (e)-[:INVOLVES]->(ent:Entity)
                OPTIONAL MATCH (e)-[:REPORTED_BY]->(src:Source)
                OPTIONAL MATCH (e)-[:CONSTRAINS]->(con:ConstraintAnchor)
                RETURN e.event_id AS event_id,
                       count(DISTINCT ent) AS entity_count,
                       count(DISTINCT src) AS source_count,
                       count(DISTINCT con) AS constraint_count
                ORDER BY event_id
                """,
                event_ids=[e1_id, e2_id],
            ).data()

        print("Inserted demo events:")
        for row in summary:
            print(
                f"- {row['event_id']}: entities={row['entity_count']}, "
                f"sources={row['source_count']}, constraints={row['constraint_count']}"
            )


if __name__ == "__main__":
    main()
