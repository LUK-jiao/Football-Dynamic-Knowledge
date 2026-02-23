"""
Context Builder for Football Knowledge Graph RAG System

Builds structured text context from retrieved events for LLM consumption.
"""

from typing import List, Dict, Any


class ContextBuilder:
    """
    Builds structured text context from event lists.
    
    Formats events into readable text for LLM processing.
    """
    
    def __init__(self, max_events: int = 30):
        """
        Initialize ContextBuilder.
        
        Args:
            max_events: Maximum number of events to include
        """
        self.max_events = max_events
    
    def build(self, events: List[Dict[str, Any]]) -> str:
        """
        Build context string from events.
        
        Args:
            events: List of event dictionaries from GraphRetriever
            
        Returns:
            Formatted context string
        """
        if not events:
            return "No relevant events found."
        
        # Deduplicate by event_id
        events = self._deduplicate_events(events)
        
        # Sort by date (most recent first)
        events = self._sort_events_by_date(events)
        
        # Limit to max_events
        events = events[:self.max_events]
        
        # Merge consecutive same-date events
        events = self._merge_same_date_events(events)
        
        # Format into text
        context_parts = []
        for i, event in enumerate(events, 1):
            event_text = self._format_event(i, event)
            context_parts.append(event_text)
        
        context = "\n\n".join(context_parts)
        
        return context
    
    def _deduplicate_events(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Remove duplicate events by event_id.
        
        Args:
            events: Event list
            
        Returns:
            Deduplicated event list
        """
        seen_ids = set()
        unique_events = []
        
        for event in events:
            event_id = event.get("event_id")
            if event_id and event_id not in seen_ids:
                seen_ids.add(event_id)
                unique_events.append(event)
        
        return unique_events
    
    def _sort_events_by_date(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Sort events by date (most recent first).
        
        Args:
            events: Event list
            
        Returns:
            Sorted event list
        """
        return sorted(
            events,
            key=lambda x: x.get("event_date") or "9999-99-99",
            reverse=True
        )
    
    def _merge_same_date_events(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Merge consecutive events with same date.
        
        Groups events that occurred on the same day together.
        
        Args:
            events: Sorted event list
            
        Returns:
            Event list with merged date groups
        """
        if not events:
            return events
        
        merged = []
        current_date = None
        current_group = []
        
        for event in events:
            event_date = event.get("event_date")
            
            if event_date == current_date:
                current_group.append(event)
            else:
                if current_group:
                    merged.extend(current_group)
                current_group = [event]
                current_date = event_date
        
        if current_group:
            merged.extend(current_group)
        
        return merged
    
    def _format_event(self, index: int, event: Dict[str, Any]) -> str:
        """
        Format single event into text.
        
        Args:
            index: Event number
            event: Event dictionary
            
        Returns:
            Formatted event text
        """
        lines = []
        
        lines.append(f"[Event {index}]")
        lines.append(f"Event ID: {event.get('event_id', 'N/A')}")
        
        event_date = event.get("event_date")
        if event_date:
            lines.append(f"Date: {event_date}")
        else:
            lines.append("Date: Unknown")
        
        # Type information
        fact_type = event.get("fact_type", "N/A")
        constraints = event.get("constraints", [])
        if constraints:
            type_info = f"{fact_type} ({', '.join(constraints)})"
        else:
            type_info = fact_type
        lines.append(f"Type: {type_info}")
        
        # Title
        title_anchors = event.get("title_anchors")
        if title_anchors:
            lines.append(f"Title: {title_anchors}")
        
        # Description
        description = event.get("event_description", "N/A")
        lines.append(f"Description: {description}")
        
        # Entities
        entities = event.get("entities", [])
        if entities:
            lines.append(f"Entities: {', '.join(entities)}")
        
        # Source
        sources = event.get("sources", [])
        if sources:
            lines.append(f"Source: {', '.join(sources)}")
        
        return "\n".join(lines)
    
    def build_summary_context(self, events: List[Dict[str, Any]]) -> str:
        """
        Build context optimized for summary queries.
        
        Groups events by constraint type for better summarization.
        
        Args:
            events: Event list
            
        Returns:
            Formatted summary context
        """
        if not events:
            return "No relevant events found."
        
        # Deduplicate and sort
        events = self._deduplicate_events(events)
        events = self._sort_events_by_date(events)
        events = events[:self.max_events]
        
        # Group by constraint type
        grouped = self._group_by_constraint_type(events)
        
        # Format grouped events
        context_parts = []
        
        for constraint_type, type_events in grouped.items():
            context_parts.append(f"=== {constraint_type} Events ===")
            
            for i, event in enumerate(type_events, 1):
                event_text = self._format_event_compact(i, event)
                context_parts.append(event_text)
        
        return "\n\n".join(context_parts)
    
    def _group_by_constraint_type(self, events: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Group events by their constraint types.
        
        Args:
            events: Event list
            
        Returns:
            Dictionary mapping constraint type to events
        """
        grouped = {}
        
        for event in events:
            constraints = event.get("constraints", ["UNKNOWN"])
            
            # Use first constraint type as primary
            constraint_type = constraints[0] if constraints else "UNKNOWN"
            
            if constraint_type not in grouped:
                grouped[constraint_type] = []
            
            grouped[constraint_type].append(event)
        
        return grouped
    
    def _format_event_compact(self, index: int, event: Dict[str, Any]) -> str:
        """
        Format event in compact form for summaries.
        
        Args:
            index: Event number
            event: Event dictionary
            
        Returns:
            Compact formatted event text
        """
        event_id = event.get('event_id', 'N/A')
        event_date = event.get("event_date", "Unknown")
        description = event.get("event_description", "N/A")
        entities = event.get("entities", [])
        
        entity_str = ", ".join(entities) if entities else "N/A"
        
        return f"{index}. [{event_id}] ({event_date}) {description} | Entities: {entity_str}"
    
    def build_analysis_context(self, events: List[Dict[str, Any]]) -> str:
        """
        Build context optimized for analysis queries.
        
        Includes temporal ordering and relationship information.
        
        Args:
            events: Event list
            
        Returns:
            Formatted analysis context
        """
        if not events:
            return "No relevant events found."
        
        # Deduplicate
        events = self._deduplicate_events(events)
        
        # Sort by date (chronological for analysis)
        events = sorted(
            events,
            key=lambda x: x.get("event_date") or "0000-00-00",
            reverse=False  # Oldest first for timeline
        )
        
        events = events[:self.max_events]
        
        # Format with timeline focus
        context_parts = ["=== Event Timeline ===\n"]
        
        for i, event in enumerate(events, 1):
            event_text = self._format_event(i, event)
            context_parts.append(event_text)
        
        return "\n\n".join(context_parts)
