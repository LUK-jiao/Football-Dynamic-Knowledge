"""
Graph Retriever for Football Knowledge Graph RAG System

Retrieves events from Neo4j based on structured query constraints.
"""

from typing import Dict, List, Any, Optional
from knowledge_graph.neo4j_writer import Neo4jWriter


class GraphRetriever:
    """
    Retrieves events from Neo4j knowledge graph based on parsed queries.
    
    Supports filtering by entities, time ranges, and constraint types.
    """
    
    def __init__(self, neo4j_writer: Neo4jWriter):
        """
        Initialize GraphRetriever.
        
        Args:
            neo4j_writer: Neo4jWriter instance for database access
        """
        self.writer = neo4j_writer
    
    def retrieve(self, parsed_query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Retrieve events based on parsed query.
        
        Args:
            parsed_query: Structured query from QueryAnalyzer
            
        Returns:
            List of event dictionaries with full context
        """
        entities = parsed_query.get("entities", [])
        time_range = parsed_query.get("time_range", {})
        constraint_types = parsed_query.get("constraint_types", [])
        intent = parsed_query.get("intent", "fact")
        limit = parsed_query.get("limit", 20)
        
        # Build Cypher query
        cypher_query = self._build_cypher_query(
            entities=entities,
            time_range=time_range,
            constraint_types=constraint_types,
            limit=limit
        )
        
        # Execute query
        events = self._execute_query(cypher_query)
        
        # If analysis intent, expand subgraph
        if intent == "analysis" and events:
            events = self._expand_subgraph(events, limit)
        
        return events
    
    def _build_cypher_query(
        self,
        entities: List[str],
        time_range: Dict[str, Optional[str]],
        constraint_types: List[str],
        limit: int
    ) -> Dict[str, Any]:
        """
        Build parameterized Cypher query.
        
        Args:
            entities: List of entity names to filter
            time_range: Time range with start and end dates
            constraint_types: List of constraint types
            limit: Maximum number of results
            
        Returns:
            Dictionary with 'query' (Cypher string) and 'parameters' (dict)
        """
        # Base query
        query_parts = []
        where_clauses = []
        parameters = {}
        
        # Match event
        query_parts.append("MATCH (e:Event)")
        
        # Filter by entities if specified
        if entities:
            query_parts.append("MATCH (e)-[:INVOLVES]->(entity:Entity)")
            where_clauses.append("entity.name IN $entities")
            parameters["entities"] = entities
        
        # Filter by constraint types if specified
        if constraint_types:
            query_parts.append("MATCH (c:ConstraintAnchor)-[:CONSTRAINS]->(e)")
            where_clauses.append("c.type IN $constraint_types")
            parameters["constraint_types"] = constraint_types
        
        # Filter by time range
        start_date = time_range.get("start")
        end_date = time_range.get("end")
        
        if start_date:
            where_clauses.append("e.event_date >= date($start_date)")
            parameters["start_date"] = start_date
        
        if end_date:
            where_clauses.append("e.event_date <= date($end_date)")
            parameters["end_date"] = end_date
        
        # Add WHERE clause if needed
        if where_clauses:
            query_parts.append("WHERE " + " AND ".join(where_clauses))
        
        # Get full event context
        query_parts.append("""
WITH DISTINCT e
OPTIONAL MATCH (e)-[:INVOLVES]->(ent:Entity)
OPTIONAL MATCH (e)-[:REPORTED_BY]->(src:Source)
OPTIONAL MATCH (con:ConstraintAnchor)-[:CONSTRAINS]->(e)
OPTIONAL MATCH (e)-[:HAS_TITLE_ANCHOR]->(title:TitleAnchor)
WITH e, 
     collect(DISTINCT ent.name) as entities,
     collect(DISTINCT src.source) as sources,
     collect(DISTINCT con.type) as constraints,
     collect(DISTINCT title.title) as titles
RETURN e.event_id as event_id,
       e.event_description as event_description,
       e.event_date as event_date,
       e.fact_type as fact_type,
       e.title_anchors as title_anchors,
       entities,
       sources,
       constraints,
       titles
ORDER BY e.event_date DESC
LIMIT $limit
        """)
        
        parameters["limit"] = limit
        
        query = "\n".join(query_parts)
        
        return {
            "query": query,
            "parameters": parameters
        }
    
    def _execute_query(self, cypher_query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Execute Cypher query and format results.
        
        Args:
            cypher_query: Dictionary with query and parameters
            
        Returns:
            List of formatted event dictionaries
        """
        query = cypher_query["query"]
        parameters = cypher_query["parameters"]
        
        with self.writer.driver.session() as session:
            result = session.run(query, parameters)
            
            events = []
            for record in result:
                event = {
                    "event_id": record["event_id"],
                    "event_description": record["event_description"],
                    "event_date": str(record["event_date"]) if record["event_date"] else None,
                    "fact_type": record["fact_type"],
                    "title_anchors": record["title_anchors"],
                    "entities": [e for e in record["entities"] if e],
                    "sources": [s for s in record["sources"] if s],
                    "constraints": [c for c in record["constraints"] if c],
                    "titles": [t for t in record["titles"] if t]
                }
                events.append(event)
            
            return events
    
    def _expand_subgraph(self, events: List[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
        """
        Expand subgraph for analysis queries.
        
        Finds related events through:
        1. Same title anchors
        2. Common entities
        
        Args:
            events: Initial event list
            limit: Maximum total events to return
            
        Returns:
            Expanded event list
        """
        if not events:
            return events
        
        # Get event IDs we already have
        existing_ids = {e["event_id"] for e in events}
        
        # Get title anchors from existing events
        title_anchors = set()
        for event in events:
            if event.get("titles"):
                title_anchors.update(event["titles"])
        
        # Find events with same title anchors
        if title_anchors:
            related_events = self._find_events_by_titles(list(title_anchors), limit)
            
            for event in related_events:
                if event["event_id"] not in existing_ids:
                    events.append(event)
                    existing_ids.add(event["event_id"])
                    
                    if len(events) >= limit:
                        break
        
        # Sort by date
        events.sort(key=lambda x: x["event_date"] or "9999-99-99", reverse=True)
        
        return events[:limit]
    
    def _find_events_by_titles(self, titles: List[str], limit: int) -> List[Dict[str, Any]]:
        """
        Find events by title anchors.
        
        Args:
            titles: List of title strings
            limit: Maximum results
            
        Returns:
            List of events
        """
        query = """
MATCH (t:TitleAnchor)<-[:HAS_TITLE_ANCHOR]-(e:Event)
WHERE t.title IN $titles
WITH DISTINCT e
OPTIONAL MATCH (e)-[:INVOLVES]->(ent:Entity)
OPTIONAL MATCH (e)-[:REPORTED_BY]->(src:Source)
OPTIONAL MATCH (con:ConstraintAnchor)-[:CONSTRAINS]->(e)
OPTIONAL MATCH (e)-[:HAS_TITLE_ANCHOR]->(title:TitleAnchor)
WITH e, 
     collect(DISTINCT ent.name) as entities,
     collect(DISTINCT src.source) as sources,
     collect(DISTINCT con.type) as constraints,
     collect(DISTINCT title.title) as titles
RETURN e.event_id as event_id,
       e.event_description as event_description,
       e.event_date as event_date,
       e.fact_type as fact_type,
       e.title_anchors as title_anchors,
       entities,
       sources,
       constraints,
       titles
ORDER BY e.event_date DESC
LIMIT $limit
        """
        
        with self.writer.driver.session() as session:
            result = session.run(query, titles=titles, limit=limit)
            
            events = []
            for record in result:
                event = {
                    "event_id": record["event_id"],
                    "event_description": record["event_description"],
                    "event_date": str(record["event_date"]) if record["event_date"] else None,
                    "fact_type": record["fact_type"],
                    "title_anchors": record["title_anchors"],
                    "entities": [e for e in record["entities"] if e],
                    "sources": [s for s in record["sources"] if s],
                    "constraints": [c for c in record["constraints"] if c],
                    "titles": [t for t in record["titles"] if t]
                }
                events.append(event)
            
            return events
    
    def get_entity_context(self, entity_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent events involving a specific entity.
        
        Args:
            entity_name: Name of the entity
            limit: Maximum events to return
            
        Returns:
            List of events
        """
        query = """
MATCH (entity:Entity {name: $entity_name})<-[:INVOLVES]-(e:Event)
WITH DISTINCT e
OPTIONAL MATCH (e)-[:INVOLVES]->(ent:Entity)
OPTIONAL MATCH (e)-[:REPORTED_BY]->(src:Source)
OPTIONAL MATCH (con:ConstraintAnchor)-[:CONSTRAINS]->(e)
OPTIONAL MATCH (e)-[:HAS_TITLE_ANCHOR]->(title:TitleAnchor)
WITH e, 
     collect(DISTINCT ent.name) as entities,
     collect(DISTINCT src.source) as sources,
     collect(DISTINCT con.type) as constraints,
     collect(DISTINCT title.title) as titles
RETURN e.event_id as event_id,
       e.event_description as event_description,
       e.event_date as event_date,
       e.fact_type as fact_type,
       e.title_anchors as title_anchors,
       entities,
       sources,
       constraints,
       titles
ORDER BY e.event_date DESC
LIMIT $limit
        """
        
        with self.writer.driver.session() as session:
            result = session.run(query, entity_name=entity_name, limit=limit)
            
            events = []
            for record in result:
                event = {
                    "event_id": record["event_id"],
                    "event_description": record["event_description"],
                    "event_date": str(record["event_date"]) if record["event_date"] else None,
                    "fact_type": record["fact_type"],
                    "title_anchors": record["title_anchors"],
                    "entities": [e for e in record["entities"] if e],
                    "sources": [s for s in record["sources"] if s],
                    "constraints": [c for c in record["constraints"] if c],
                    "titles": [t for t in record["titles"] if t]
                }
                events.append(event)
            
            return events
