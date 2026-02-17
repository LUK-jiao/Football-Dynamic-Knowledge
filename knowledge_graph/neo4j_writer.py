"""
Neo4j Graph Persistence Layer for Football Knowledge Graph
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, date
from neo4j import GraphDatabase, Driver, Session, Result
from neo4j.exceptions import Neo4jError
import os


class Neo4jWriter:
    """Neo4j graph database writer for football events."""
    
    def __init__(
        self,
        uri: str = "bolt://localhost:7687",
        user: str = "neo4j",
        password: str = "password"
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
    
    def initialize_constraints(self) -> None:
        """Create all uniqueness constraints."""
        constraints = [
            "CREATE CONSTRAINT event_id_unique IF NOT EXISTS FOR (e:Event) REQUIRE e.event_id IS UNIQUE",
            "CREATE CONSTRAINT entity_id_unique IF NOT EXISTS FOR (e:Entity) REQUIRE e.entity_id IS UNIQUE",
            "CREATE CONSTRAINT source_id_unique IF NOT EXISTS FOR (s:Source) REQUIRE s.source_id IS UNIQUE",
            "CREATE CONSTRAINT constraint_type_unique IF NOT EXISTS FOR (c:ConstraintAnchor) REQUIRE c.type IS UNIQUE",
            "CREATE CONSTRAINT title_unique IF NOT EXISTS FOR (t:TitleAnchor) REQUIRE t.title IS UNIQUE"
        ]
        
        with self.driver.session() as session:
            for constraint in constraints:
                try:
                    session.run(constraint)
                except Neo4jError as e:
                    print(f"Constraint creation warning: {e}")
    
    def _generate_entity_id(self, name: str) -> str:
        """Generate entity_id from name."""
        return name.lower().replace(" ", "_")
    
    def _generate_source_id(self, source_name: str) -> str:
        """Generate source_id from source name."""
        return source_name.lower().replace(" ", "_")
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[date]:
        """Parse date string to date object."""
        if not date_str:
            return None
        try:
            if len(date_str) == 4:  # YYYY
                return date(int(date_str), 1, 1)
            elif len(date_str) == 7:  # YYYY-MM
                parts = date_str.split('-')
                return date(int(parts[0]), int(parts[1]), 1)
            else:  # YYYY-MM-DD
                parts = date_str.split('-')
                return date(int(parts[0]), int(parts[1]), int(parts[2]))
        except (ValueError, IndexError):
            return None
    
    def upsert_event(self, event_payload: Dict[str, Any]) -> None:
        """
        Insert or update a single event with all relationships.
        
        Args:
            event_payload: Event data in extraction format
        """
        with self.driver.session() as session:
            session.execute_write(self._upsert_event_tx, event_payload)
    
    def _upsert_event_tx(self, tx, event_payload: Dict[str, Any]) -> None:
        """Transaction function for upserting a single event."""
        
        # Extract temporal anchors
        temporal = event_payload.get('temporal_anchors', [{}])[0] if event_payload.get('temporal_anchors') else {}
        event_date_str = temporal.get('event_date')
        valid_from_str = temporal.get('valid_from')
        valid_to_str = temporal.get('valid_to')
        
        # Parse dates
        event_date = self._parse_date(event_date_str)
        valid_from = self._parse_date(valid_from_str)
        valid_to = self._parse_date(valid_to_str)
        
        # Prepare event properties
        event_props = {
            'event_id': event_payload['event_id'],
            'title': event_payload.get('title_anchors', ''),
            'description': event_payload.get('event_description', ''),
            'fact_type': event_payload.get('fact_type', 'EVENT'),
            'inference_time': event_payload.get('inference_time'),
            'event_date': event_date,
            'valid_from': valid_from,
            'valid_to': valid_to,
            'confidence_score': event_payload.get('confidence_score'),
            'created_at': datetime.now()
        }
        
        # Create Event node
        tx.run("""
            MERGE (e:Event {event_id: $event_id})
            SET e.title = $title,
                e.description = $description,
                e.fact_type = $fact_type,
                e.inference_time = $inference_time,
                e.event_date = $event_date,
                e.valid_from = $valid_from,
                e.valid_to = $valid_to,
                e.confidence_score = $confidence_score,
                e.created_at = $created_at
        """, **event_props)
        
        # Process participants (entities)
        participants = event_payload.get('participants', [])
        for participant in participants:
            entity_id = self._generate_entity_id(participant['name'])
            entity_type = participant['type']
            
            tx.run("""
                MERGE (e:Entity {entity_id: $entity_id})
                SET e.name = $name,
                    e:""" + entity_type + """
                WITH e
                MATCH (ev:Event {event_id: $event_id})
                MERGE (ev)-[:INVOLVES]->(e)
            """, 
                entity_id=entity_id,
                name=participant['name'],
                event_id=event_payload['event_id']
            )
        
        # Process sources
        sources = event_payload.get('sources', [])
        for source in sources:
            source_id = self._generate_source_id(source['source'])
            publish_date = self._parse_date(source.get('publish_date'))
            
            tx.run("""
                MERGE (s:Source {source_id: $source_id})
                SET s.name = $name,
                    s.type = $type,
                    s.publish_date = $publish_date
                WITH s
                MATCH (e:Event {event_id: $event_id})
                MERGE (e)-[:REPORTED_BY]->(s)
            """,
                source_id=source_id,
                name=source['source'],
                type=source['type'],
                publish_date=publish_date,
                event_id=event_payload['event_id']
            )
        
        # Process constraints
        constraints = event_payload.get('constraints', [])
        for constraint in constraints:
            tx.run("""
                MERGE (c:ConstraintAnchor {type: $type})
                WITH c
                MATCH (e:Event {event_id: $event_id})
                MERGE (e)-[:CONSTRAINS]->(c)
            """,
                type=constraint['type'],
                event_id=event_payload['event_id']
            )
        
        # Process title anchor
        title_anchors = event_payload.get('title_anchors')
        if title_anchors and title_anchors.strip():
            tx.run("""
                MERGE (t:TitleAnchor {title: $title})
                WITH t
                MATCH (e:Event {event_id: $event_id})
                MERGE (e)-[:HAS_TITLE_ANCHOR]->(t)
            """,
                title=title_anchors,
                event_id=event_payload['event_id']
            )
    
    def upsert_events(self, events: List[Dict[str, Any]]) -> None:
        """
        Batch upsert multiple events in a single transaction.
        
        Args:
            events: List of event payloads
        """
        if not events:
            return
        
        with self.driver.session() as session:
            session.execute_write(self._upsert_events_tx, events)
    
    def _upsert_events_tx(self, tx, events: List[Dict[str, Any]]) -> None:
        """Transaction function for batch upserting events."""
        
        # Prepare event data
        events_data = []
        for event_payload in events:
            temporal = event_payload.get('temporal_anchors', [{}])[0] if event_payload.get('temporal_anchors') else {}
            
            event_date = self._parse_date(temporal.get('event_date'))
            valid_from = self._parse_date(temporal.get('valid_from'))
            valid_to = self._parse_date(temporal.get('valid_to'))
            
            events_data.append({
                'event_id': event_payload['event_id'],
                'title': event_payload.get('title_anchors', ''),
                'description': event_payload.get('event_description', ''),
                'fact_type': event_payload.get('fact_type', 'EVENT'),
                'inference_time': event_payload.get('inference_time'),
                'event_date': event_date,
                'valid_from': valid_from,
                'valid_to': valid_to,
                'confidence_score': event_payload.get('confidence_score'),
                'created_at': datetime.now(),
                'participants': event_payload.get('participants', []),
                'sources': event_payload.get('sources', []),
                'constraints': event_payload.get('constraints', [])
            })
        
        # Batch create events
        tx.run("""
            UNWIND $events AS event
            MERGE (e:Event {event_id: event.event_id})
            SET e.title = event.title,
                e.description = event.description,
                e.fact_type = event.fact_type,
                e.inference_time = event.inference_time,
                e.event_date = event.event_date,
                e.valid_from = event.valid_from,
                e.valid_to = event.valid_to,
                e.confidence_score = event.confidence_score,
                e.created_at = event.created_at
        """, events=events_data)
        
        # Batch create entities and relationships
        for event_data in events_data:
            for participant in event_data['participants']:
                entity_id = self._generate_entity_id(participant['name'])
                entity_type = participant['type']
                
                tx.run("""
                    MERGE (e:Entity {entity_id: $entity_id})
                    SET e.name = $name,
                        e:""" + entity_type + """
                    WITH e
                    MATCH (ev:Event {event_id: $event_id})
                    MERGE (ev)-[:INVOLVES]->(e)
                """,
                    entity_id=entity_id,
                    name=participant['name'],
                    event_id=event_data['event_id']
                )
            
            for source in event_data['sources']:
                source_id = self._generate_source_id(source['source'])
                publish_date = self._parse_date(source.get('publish_date'))
                
                tx.run("""
                    MERGE (s:Source {source_id: $source_id})
                    SET s.name = $name,
                        s.type = $type,
                        s.publish_date = $publish_date
                    WITH s
                    MATCH (e:Event {event_id: $event_id})
                    MERGE (e)-[:REPORTED_BY]->(s)
                """,
                    source_id=source_id,
                    name=source['source'],
                    type=source['type'],
                    publish_date=publish_date,
                    event_id=event_data['event_id']
                )
            
            for constraint in event_data['constraints']:
                tx.run("""
                    MERGE (c:ConstraintAnchor {type: $type})
                    WITH c
                    MATCH (e:Event {event_id: $event_id})
                    MERGE (e)-[:CONSTRAINS]->(c)
                """,
                    type=constraint['type'],
                    event_id=event_data['event_id']
                )
            
            if event_data['title'] and event_data['title'].strip():
                tx.run("""
                    MERGE (t:TitleAnchor {title: $title})
                    WITH t
                    MATCH (e:Event {event_id: $event_id})
                    MERGE (e)-[:HAS_TITLE_ANCHOR]->(t)
                """,
                    title=event_data['title'],
                    event_id=event_data['event_id']
                )
    
    def get_event_full_view(self, event_id: str) -> Optional[Dict[str, Any]]:
        """Get complete event with all relationships."""
        with self.driver.session() as session:
            result = session.run("""
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
            """, event_id=event_id)
            
            record = result.single()
            if not record:
                return None
            
            event = dict(record['e'])
            return {
                'event': event,
                'entities': [dict(e) for e in record['entities'] if e],
                'sources': [dict(s) for s in record['sources'] if s],
                'constraints': [dict(c) for c in record['constraints'] if c],
                'titles': [dict(t) for t in record['titles'] if t]
            }
    
    def get_entity_events(self, entity_id: str) -> List[Dict[str, Any]]:
        """Get all events involving a specific entity."""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (e:Event)-[:INVOLVES]->(entity:Entity {entity_id: $entity_id})
                RETURN e
                ORDER BY e.created_at DESC
            """, entity_id=entity_id)
            
            return [dict(record['e']) for record in result]
    
    def get_events_by_anchor(self, anchor_type: str) -> List[Dict[str, Any]]:
        """Get all events with a specific constraint anchor."""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (e:Event)-[:CONSTRAINS]->(c:ConstraintAnchor {type: $anchor_type})
                RETURN e
                ORDER BY e.created_at DESC
            """, anchor_type=anchor_type)
            
            return [dict(record['e']) for record in result]
    
    def get_events_by_title_anchor(self, title: str) -> List[Dict[str, Any]]:
        """Get all events with a specific title anchor."""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (e:Event)-[:HAS_TITLE_ANCHOR]->(t:TitleAnchor {title: $title})
                RETURN e
                ORDER BY e.created_at DESC
            """, title=title)
            
            return [dict(record['e']) for record in result]
    
    def get_events_by_time_range(
        self, 
        start_date: Optional[date] = None, 
        end_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """Get events within a time range."""
        with self.driver.session() as session:
            if start_date and end_date:
                result = session.run("""
                    MATCH (e:Event)
                    WHERE e.event_date >= $start_date AND e.event_date <= $end_date
                    RETURN e
                    ORDER BY e.event_date DESC
                """, start_date=start_date, end_date=end_date)
            elif start_date:
                result = session.run("""
                    MATCH (e:Event)
                    WHERE e.event_date >= $start_date
                    RETURN e
                    ORDER BY e.event_date DESC
                """, start_date=start_date)
            elif end_date:
                result = session.run("""
                    MATCH (e:Event)
                    WHERE e.event_date <= $end_date
                    RETURN e
                    ORDER BY e.event_date DESC
                """, end_date=end_date)
            else:
                result = session.run("""
                    MATCH (e:Event)
                    WHERE e.event_date IS NOT NULL
                    RETURN e
                    ORDER BY e.event_date DESC
                """)
            
            return [dict(record['e']) for record in result]
