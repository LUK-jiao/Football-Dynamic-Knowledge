"""
Integration script: Load extraction results into Neo4j
"""

import json
import sys
from pathlib import Path
from knowledge_graph.neo4j_writer import Neo4jWriter


def load_extraction_results(json_file_path: str) -> None:
    """
    Load extraction results from JSON file into Neo4j.
    
    Args:
        json_file_path: Path to extraction output JSON file
    """
    
    # Read extraction results
    with open(json_file_path, 'r', encoding='utf-8') as f:
        events = json.load(f)
    
    print(f"Loaded {len(events)} events from {json_file_path}")
    
    # Initialize writer and load data
    with Neo4jWriter() as writer:
        print("Initializing database constraints...")
        writer.initialize_constraints()
        
        print(f"Writing {len(events)} events to Neo4j...")
        writer.upsert_events(events)
        
        print("✅ Successfully loaded events into Neo4j")
        
        # Print statistics
        total_entities = set()
        total_constraints = set()
        total_sources = set()
        
        for event in events:
            for participant in event.get('participants', []):
                total_entities.add(participant['name'])
            for constraint in event.get('constraints', []):
                total_constraints.add(constraint['type'])
            for source in event.get('sources', []):
                source_name = source.get('name') or source.get('source')
                if source_name:
                    total_sources.add(source_name)
        
        print(f"\nStatistics:")
        print(f"  - Events: {len(events)}")
        print(f"  - Unique Entities: {len(total_entities)}")
        print(f"  - Unique Constraints: {len(total_constraints)}")
        print(f"  - Unique Sources: {len(total_sources)}")


def load_directory(directory_path: str) -> None:
    """
    Load all JSON files from a directory.
    
    Args:
        directory_path: Path to directory containing extraction JSON files
    """
    
    directory = Path(directory_path)
    json_files = list(directory.glob("*.json"))
    
    if not json_files:
        print(f"No JSON files found in {directory_path}")
        return
    
    print(f"Found {len(json_files)} JSON files")
    
    all_events = []
    for json_file in json_files:
        with open(json_file, 'r', encoding='utf-8') as f:
            events = json.load(f)
            all_events.extend(events)
        print(f"  ✓ Loaded {len(events)} events from {json_file.name}")
    
    print(f"\nTotal events to write: {len(all_events)}")
    
    with Neo4jWriter() as writer:
        writer.initialize_constraints()
        writer.upsert_events(all_events)
        print("✅ Successfully loaded all events into Neo4j")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python load_to_neo4j.py <json_file>")
        print("  python load_to_neo4j.py <directory>")
        sys.exit(1)
    
    path = sys.argv[1]
    
    if Path(path).is_file():
        load_extraction_results(path)
    elif Path(path).is_dir():
        load_directory(path)
    else:
        print(f"Error: {path} is not a valid file or directory")
        sys.exit(1)
