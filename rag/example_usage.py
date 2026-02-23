"""
Example Usage of GraphRAG System

Demonstrates how to use the complete GraphRAG pipeline.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag import QueryAnalyzer, GraphRetriever, ContextBuilder, GraphRAG, RAGLLMBackend
from knowledge_graph import Neo4jWriter


def simple_example():
    """Simple example of asking a question."""
    
    print("\n" + "="*80)
    print("SIMPLE GRAPHRAG EXAMPLE")
    print("="*80)
    
    # Initialize components
    analyzer = QueryAnalyzer(model="llama3:latest")
    writer = Neo4jWriter()
    retriever = GraphRetriever(writer)
    builder = ContextBuilder()
    llm = RAGLLMBackend(model="llama3:latest")
    
    # Create GraphRAG engine
    rag = GraphRAG(analyzer, retriever, builder, llm)
    
    # Ask a question
    query = "Arsenal在2025年1月14日的比赛结果是什么？"
    response = rag.answer(query)
    
    # Display answer
    print(f"\n📝 Question: {query}")
    print(f"\n💬 Answer:\n{response['answer']}")
    print(f"\n📊 Based on {len(response['retrieved_events'])} events from the knowledge graph")
    
    # Cleanup
    writer.close()


def batch_example():
    """Example of processing multiple queries."""
    
    print("\n" + "="*80)
    print("BATCH QUERY EXAMPLE")
    print("="*80)
    
    # Initialize
    analyzer = QueryAnalyzer(model="llama3:latest")
    writer = Neo4jWriter()
    retriever = GraphRetriever(writer)
    builder = ContextBuilder()
    llm = RAGLLMBackend(model="llama3:latest")
    
    rag = GraphRAG(analyzer, retriever, builder, llm)
    
    # Multiple queries
    queries = [
        "Arsenal最近的比赛结果",
        "Bukayo Saka的表现如何",
        "Crystal Palace在比赛中的表现"
    ]
    
    # Process batch
    responses = rag.batch_answer(queries)
    
    # Display results
    for i, (query, response) in enumerate(zip(queries, responses), 1):
        print(f"\n{'='*80}")
        print(f"Query {i}: {query}")
        print(f"{'='*80}")
        print(response['answer'])
    
    writer.close()


def interactive_example():
    """Example of interactive Q&A mode."""
    
    print("\n" + "="*80)
    print("INTERACTIVE MODE EXAMPLE")
    print("="*80)
    
    # Initialize
    analyzer = QueryAnalyzer(model="llama3:latest")
    writer = Neo4jWriter()
    retriever = GraphRetriever(writer)
    builder = ContextBuilder()
    llm = RAGLLMBackend(model="llama3:latest")
    
    rag = GraphRAG(analyzer, retriever, builder, llm)
    
    # Start interactive mode
    try:
        rag.interactive_mode()
    finally:
        writer.close()


def custom_retrieval_example():
    """Example of custom retrieval with specific constraints."""
    
    print("\n" + "="*80)
    print("CUSTOM RETRIEVAL EXAMPLE")
    print("="*80)
    
    writer = Neo4jWriter()
    retriever = GraphRetriever(writer)
    builder = ContextBuilder()
    
    # Custom parsed query (using new format)
    custom_query = {
        "entities": [
            {"name": "Arsenal", "entity_type": "Club"},
            {"name": "Crystal Palace", "entity_type": "Club"}
        ],
        "time_filter": {"mode": "event_date", "start": "2025-01-01", "end": "2025-01-31"},
        "constraint_types": ["MATCH_OUTCOME", "MATCH_ACTION"],
        "fact_types": ["EVENT"],
        "intent": "summary",
        "limit": 10
    }
    
    print("\nCustom Query Constraints:")
    print(f"  Entities: {custom_query['entities']}")
    print(f"  Time Filter: {custom_query['time_filter']}")
    print(f"  Constraint Types: {custom_query['constraint_types']}")
    
    # Retrieve events
    events = retriever.retrieve(custom_query)
    
    print(f"\n✓ Retrieved {len(events)} events")
    
    # Build context
    context = builder.build_summary_context(events)
    
    print(f"\n📄 Context:\n{context[:500]}...")
    
    writer.close()


def entity_focused_example():
    """Example of entity-focused retrieval."""
    
    print("\n" + "="*80)
    print("ENTITY-FOCUSED RETRIEVAL EXAMPLE")
    print("="*80)
    
    writer = Neo4jWriter()
    retriever = GraphRetriever(writer)
    
    # Get all events for a specific entity
    entity_name = "Arsenal"
    events = retriever.get_entity_context(entity_name, limit=15)
    
    print(f"\n✓ Found {len(events)} events for {entity_name}")
    
    if events:
        print(f"\nRecent events:")
        for i, event in enumerate(events[:5], 1):
            print(f"  {i}. [{event['event_date']}] {event['event_description'][:60]}...")
    
    writer.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="GraphRAG Example Usage")
    parser.add_argument(
        "--mode",
        choices=["simple", "batch", "interactive", "custom", "entity"],
        default="simple",
        help="Example mode to run"
    )
    
    args = parser.parse_args()
    
    if args.mode == "simple":
        simple_example()
    elif args.mode == "batch":
        batch_example()
    elif args.mode == "interactive":
        interactive_example()
    elif args.mode == "custom":
        custom_retrieval_example()
    elif args.mode == "entity":
        entity_focused_example()
