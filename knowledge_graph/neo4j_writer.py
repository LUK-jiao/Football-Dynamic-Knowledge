"""
Neo4j Graph Persistence Layer for Football Knowledge Graph
"""

from typing import Dict, Any, List
from datetime import datetime
from neo4j.exceptions import Neo4jError

from knowledge_graph.neo4j_reader import Neo4jReader


class Neo4jWriter(Neo4jReader):
    """Neo4j graph database writer for football events."""
    
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
            source_name = source.get('name') or source.get('source')
            if not source_name:
                continue
            source_id = self._generate_source_id(source_name)
            publish_date = self._parse_date(source.get('publish_date'))
            author = source.get('author', '')
            
            tx.run("""
                MERGE (s:Source {source_id: $source_id})
                SET s.name = $name,
                    s.type = $type,
                    s.publish_date = $publish_date,
                    s.author = $author
                WITH s
                MATCH (e:Event {event_id: $event_id})
                MERGE (e)-[:REPORTED_BY]->(s)
            """,
                source_id=source_id,
                name=source_name,
                type=source.get('type', 'UNKNOWN'),
                publish_date=publish_date,
                author=author,
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
                source_name = source.get('name') or source.get('source')
                if not source_name:
                    continue
                source_id = self._generate_source_id(source_name)
                publish_date = self._parse_date(source.get('publish_date'))
                author = source.get('author', '')
                
                tx.run("""
                    MERGE (s:Source {source_id: $source_id})
                    SET s.name = $name,
                        s.type = $type,
                        s.publish_date = $publish_date,
                        s.author = $author
                    WITH s
                    MATCH (e:Event {event_id: $event_id})
                    MERGE (e)-[:REPORTED_BY]->(s)
                """,
                    source_id=source_id,
                    name=source_name,
                    type=source.get('type', 'UNKNOWN'),
                    publish_date=publish_date,
                    author=author,
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
    
    def upsert_validated_event(self, validated_event: Dict[str, Any]) -> None:
        """
        Persist validated event and apply confidence propagation results.

        This method performs the persistence-layer stage of truth validation:
        1) upsert new Event node with confidence fields
        2) update old events confidence when propagation changes exist
        3) create SUPPORTS / CONFLICTS relationships
        4) record confidence version metadata

        Args:
            validated_event: Event payload with `validation` section
        """
        with self.driver.session() as session:
            session.execute_write(self._upsert_validated_event_tx, validated_event)

    def _upsert_validated_event_tx(self, tx, validated_event: Dict[str, Any]) -> None:
        """Transaction function for validated event persistence."""
        validation = validated_event.get("validation", {})

        # 1) Upsert event itself via existing logic-compatible shape.
        event_payload = dict(validated_event)
        event_payload["confidence_score"] = validation.get(
            "current_confidence",
            validated_event.get("confidence_score")
        )
        self._upsert_event_tx(tx, event_payload)

        event_id = validated_event.get("event_id")
        if not event_id:
            return

        version = int(validation.get("version", 1))
        initial_conf = validation.get("initial_confidence")
        current_conf = validation.get("current_confidence")
        status = validation.get("status")

        tx.run(
            """
            MATCH (e:Event {event_id: $event_id})
            SET e.initial_confidence = $initial_confidence,
                e.current_confidence = $current_confidence,
                e.confidence_score = $current_confidence,
                e.confidence_version = $version,
                e.validation_status = $status,
                e.validated_at = datetime()
            """,
            event_id=event_id,
            initial_confidence=initial_conf,
            current_confidence=current_conf,
            version=version,
            status=status,
        )

        # 2) Update existing events confidence according to propagation outputs.
        propagation = validation.get("propagation", {})
        updated_existing = propagation.get("updated_existing_events", [])
        for item in updated_existing:
            old_id = item.get("event_id")
            new_confidence = item.get("new_confidence")
            if not old_id or new_confidence is None:
                continue
            tx.run(
                """
                MATCH (e:Event {event_id: $event_id})
                SET e.current_confidence = $current_confidence,
                    e.confidence_score = $current_confidence,
                    e.confidence_version = $version,
                    e.validated_at = datetime()
                """,
                event_id=old_id,
                current_confidence=new_confidence,
                version=version,
            )

        # 3) Create SUPPORTS / CONFLICTS relations.
        relation_analysis = validation.get("relation_analysis", {})
        supports = relation_analysis.get("supports", [])
        conflicts = relation_analysis.get("conflicts", [])

        for item in supports:
            target_id = item.get("event_id")
            if not target_id:
                continue
            tx.run(
                """
                MATCH (n:Event {event_id: $new_event_id})
                MATCH (o:Event {event_id: $old_event_id})
                MERGE (n)-[r:SUPPORTS]->(o)
                SET r.score = $score,
                    r.participant_overlap = $participant_overlap,
                    r.action_similarity = $action_similarity,
                    r.time_overlap = $time_overlap,
                    r.version = $version,
                    r.updated_at = datetime()
                """,
                new_event_id=event_id,
                old_event_id=target_id,
                score=item.get("score"),
                participant_overlap=item.get("participant_overlap"),
                action_similarity=item.get("action_similarity"),
                time_overlap=item.get("time_overlap"),
                version=version,
            )

        for item in conflicts:
            target_id = item.get("event_id")
            if not target_id:
                continue
            signals = item.get("signals", {})
            tx.run(
                """
                MATCH (n:Event {event_id: $new_event_id})
                MATCH (o:Event {event_id: $old_event_id})
                MERGE (n)-[r:CONFLICTS]->(o)
                SET r.score = $score,
                    r.negation_signal = $negation_signal,
                    r.numeric_signal = $numeric_signal,
                    r.uniqueness_signal = $uniqueness_signal,
                    r.version = $version,
                    r.updated_at = datetime()
                """,
                new_event_id=event_id,
                old_event_id=target_id,
                score=item.get("score"),
                negation_signal=signals.get("negation"),
                numeric_signal=signals.get("numeric"),
                uniqueness_signal=signals.get("uniqueness"),
                version=version,
            )
