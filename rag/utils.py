"""
Utility functions for RAG system.
"""

from typing import List, Dict, Any
import json


def format_retrieved_events_table(events: List[Dict[str, Any]]) -> str:
    """
    Format retrieved events as a readable table.
    
    Args:
        events: List of event dictionaries
        
    Returns:
        Formatted table string
    """
    if not events:
        return "No events found."
    
    lines = []
    lines.append("\n" + "="*100)
    lines.append(f"{'ID':<15} {'Date':<12} {'Type':<20} {'Description':<50}")
    lines.append("="*100)
    
    for event in events:
        event_id = event.get('event_id', 'N/A')[:14]
        event_date = event.get('event_date', 'Unknown')[:11]
        constraints = event.get('constraints', [])
        constraint_type = constraints[0] if constraints else 'N/A'
        description = event.get('event_description', 'N/A')[:49]
        
        lines.append(f"{event_id:<15} {event_date:<12} {constraint_type:<20} {description:<50}")
    
    lines.append("="*100)
    lines.append(f"Total: {len(events)} events\n")
    
    return "\n".join(lines)


def save_response_to_file(response: Dict[str, Any], filepath: str):
    """
    Save GraphRAG response to JSON file.
    
    Args:
        response: Response dictionary from GraphRAG
        filepath: Output file path
    """
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(response, f, ensure_ascii=False, indent=2)
    
    print(f"✓ Response saved to {filepath}")


def load_queries_from_file(filepath: str) -> List[str]:
    """
    Load queries from text file (one per line).
    
    Args:
        filepath: Input file path
        
    Returns:
        List of query strings
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        queries = [line.strip() for line in f if line.strip()]
    
    return queries


def calculate_retrieval_metrics(retrieved_events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate metrics for retrieved events.
    
    Args:
        retrieved_events: List of retrieved events
        
    Returns:
        Dictionary with metrics
    """
    if not retrieved_events:
        return {
            "total_events": 0,
            "unique_entities": 0,
            "unique_sources": 0,
            "constraint_distribution": {},
            "date_range": None
        }
    
    unique_entities = set()
    unique_sources = set()
    constraint_counts = {}
    dates = []
    
    for event in retrieved_events:
        # Collect entities
        entities = event.get('entities', [])
        unique_entities.update(entities)
        
        # Collect sources
        sources = event.get('sources', [])
        unique_sources.update(sources)
        
        # Count constraints
        constraints = event.get('constraints', [])
        for constraint in constraints:
            constraint_counts[constraint] = constraint_counts.get(constraint, 0) + 1
        
        # Collect dates
        event_date = event.get('event_date')
        if event_date:
            dates.append(event_date)
    
    # Calculate date range
    date_range = None
    if dates:
        dates_sorted = sorted(dates)
        date_range = {
            "earliest": dates_sorted[0],
            "latest": dates_sorted[-1]
        }
    
    return {
        "total_events": len(retrieved_events),
        "unique_entities": len(unique_entities),
        "unique_sources": len(unique_sources),
        "constraint_distribution": constraint_counts,
        "date_range": date_range
    }


def print_response_summary(response: Dict[str, Any]):
    """
    Print a summary of GraphRAG response.
    
    Args:
        response: Response dictionary from GraphRAG
    """
    print("\n" + "="*80)
    print("GRAPHRAG RESPONSE SUMMARY")
    print("="*80)
    
    # Parsed query
    parsed_query = response.get('parsed_query', {})
    print("\n[Parsed Query]")
    print(f"  Entities: {parsed_query.get('entities', [])}")
    print(f"  Time Range: {parsed_query.get('time_range', {})}")
    print(f"  Constraints: {parsed_query.get('constraint_types', [])}")
    print(f"  Intent: {parsed_query.get('intent', 'N/A')}")
    print(f"  Limit: {parsed_query.get('limit', 'N/A')}")
    
    # Retrieved events
    events = response.get('retrieved_events', [])
    print(f"\n[Retrieved Events]")
    print(f"  Total Events: {len(events)}")
    
    if events:
        metrics = calculate_retrieval_metrics(events)
        print(f"  Unique Entities: {metrics['unique_entities']}")
        print(f"  Unique Sources: {metrics['unique_sources']}")
        print(f"  Constraint Distribution: {metrics['constraint_distribution']}")
        if metrics['date_range']:
            print(f"  Date Range: {metrics['date_range']['earliest']} to {metrics['date_range']['latest']}")
    
    # Answer
    answer = response.get('answer', '')
    print(f"\n[Answer]")
    print(f"  Length: {len(answer)} characters")
    print(f"\n{answer}")
    
    print("\n" + "="*80)
