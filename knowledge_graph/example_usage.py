"""
Example usage of Neo4j Writer
"""

from knowledge_graph.neo4j_writer import Neo4jWriter
from datetime import date


def example_single_event():
    """Example: Write a single event."""
    
    event = {
        "event_id": "001-1",
        "title_anchors": "De Ligt Transfer to Manchester United",
        "event_description": "Matthijs de Ligt completes €50m move from Bayern Munich to Manchester United on July 30, 2024.",
        "participants": [
            {"type": "Person", "name": "Matthijs de Ligt"},
            {"type": "Club", "name": "Manchester United"},
            {"type": "Club", "name": "Bayern Munich"}
        ],
        "fact_type": "EVENT",
        "constraints": [
            {"type": "PLAYER_MOVEMENT"},
            {"type": "CONTRACT_EVENT"}
        ],
        "temporal_anchors": [
            {
                "event_date": "2024-07-30",
                "valid_from": None,
                "valid_to": None
            }
        ],
        "sources": [
            {
                "type": "MEDIA",
                "source": "BBC Sport",
                "publish_date": "2024-07-30"
            }
        ],
        "inference_time": 1.234
    }
    
    with Neo4jWriter() as writer:
        # Initialize constraints
        writer.initialize_constraints()
        
        # Write event
        writer.upsert_event(event)
        
        # Query back
        result = writer.get_event_full_view("001-1")
        print("Event Full View:", result)


def example_batch_events():
    """Example: Write multiple events in batch."""
    
    events = [
        {
            "event_id": "002-1",
            "title_anchors": "Arsenal vs Chelsea Match",
            "event_description": "Arsenal won 2-1 against Chelsea.",
            "participants": [
                {"type": "Club", "name": "Arsenal"},
                {"type": "Club", "name": "Chelsea"}
            ],
            "fact_type": "EVENT",
            "constraints": [
                {"type": "MATCH_OUTCOME"}
            ],
            "temporal_anchors": [
                {"event_date": "2024-08-01", "valid_from": None, "valid_to": None}
            ],
            "sources": [
                {"type": "OFFICIAL", "source": "Premier League", "publish_date": "2024-08-01"}
            ],
            "inference_time": 2.1
        },
        {
            "event_id": "002-2",
            "title_anchors": "Saka Goal",
            "event_description": "Bukayo Saka scored the winning goal.",
            "participants": [
                {"type": "Person", "name": "Bukayo Saka"},
                {"type": "Club", "name": "Arsenal"}
            ],
            "fact_type": "EVENT",
            "constraints": [
                {"type": "MATCH_ACTION"}
            ],
            "temporal_anchors": [
                {"event_date": "2024-08-01", "valid_from": None, "valid_to": None}
            ],
            "sources": [
                {"type": "MEDIA", "source": "Sky Sports", "publish_date": "2024-08-01"}
            ],
            "inference_time": 1.8
        }
    ]
    
    with Neo4jWriter() as writer:
        writer.initialize_constraints()
        writer.upsert_events(events)
        
        # Query entity events
        saka_events = writer.get_entity_events("bukayo_saka")
        print(f"Saka Events: {len(saka_events)}")


def example_queries():
    """Example: Various query functions."""
    
    with Neo4jWriter() as writer:
        # Get events by constraint anchor
        transfer_events = writer.get_events_by_anchor("PLAYER_MOVEMENT")
        print(f"Transfer Events: {len(transfer_events)}")
        
        # Get events by title
        title_events = writer.get_events_by_title_anchor("De Ligt Transfer to Manchester United")
        print(f"Title Events: {len(title_events)}")
        
        # Get events by time range
        events_in_range = writer.get_events_by_time_range(
            start_date=date(2024, 7, 1),
            end_date=date(2024, 8, 31)
        )
        print(f"Events in July-August 2024: {len(events_in_range)}")


if __name__ == "__main__":
    example_single_event()
    example_batch_events()
    example_queries()
