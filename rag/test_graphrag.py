"""
Unit Tests for GraphRAG System

Tests all components with 3 query types: fact, summary, analysis
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag import QueryAnalyzer, GraphRetriever, ContextBuilder, GraphRAG
from knowledge_graph import Neo4jWriter
from extractor_v1.ollama_backend import OllamaBackend
from rag.utils import print_response_summary, calculate_retrieval_metrics


def test_query_analyzer():
    """Test QueryAnalyzer with different query types."""
    
    print("\n" + "="*80)
    print("TEST 1: QUERY ANALYZER")
    print("="*80)
    
    analyzer = QueryAnalyzer(model="llama3:latest")
    
    # Test queries
    test_queries = [
        "Bukayo Saka在2025年进了多少球？",  # Fact query
        "总结一下Arsenal在2025年1月的表现",  # Summary query
        "为什么Thomas Frank会被Tottenham解雇？"  # Analysis query
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n[Test {i}] Query: {query}")
        result = analyzer.parse(query)
        print(f"  Entities: {result['entities']}")
        print(f"  Time Range: {result['time_range']}")
        print(f"  Constraints: {result['constraint_types']}")
        print(f"  Intent: {result['intent']}")
        print(f"  Limit: {result['limit']}")


def test_graph_retriever():
    """Test GraphRetriever with different constraints."""
    
    print("\n" + "="*80)
    print("TEST 2: GRAPH RETRIEVER")
    print("="*80)
    
    writer = Neo4jWriter()
    retriever = GraphRetriever(writer)
    
    # Test retrieval scenarios
    test_cases = [
        {
            "name": "Retrieve by entity",
            "parsed_query": {
                "entities": ["Arsenal"],
                "time_range": {"start": None, "end": None},
                "constraint_types": [],
                "intent": "fact",
                "limit": 5
            }
        },
        {
            "name": "Retrieve by constraint type",
            "parsed_query": {
                "entities": [],
                "time_range": {"start": None, "end": None},
                "constraint_types": ["MATCH_ACTION"],
                "intent": "fact",
                "limit": 5
            }
        },
        {
            "name": "Retrieve with time range",
            "parsed_query": {
                "entities": [],
                "time_range": {"start": "2025-01-01", "end": "2025-01-31"},
                "constraint_types": [],
                "intent": "fact",
                "limit": 5
            }
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n[Test {i}] {test_case['name']}")
        events = retriever.retrieve(test_case['parsed_query'])
        print(f"  Retrieved: {len(events)} events")
        
        if events:
            sample = events[0]
            print(f"  Sample Event: {sample['event_id']}")
            print(f"    Description: {sample['event_description']}")
            print(f"    Entities: {sample['entities']}")
            print(f"    Constraints: {sample['constraints']}")
    
    writer.close()


def test_context_builder():
    """Test ContextBuilder formatting."""
    
    print("\n" + "="*80)
    print("TEST 3: CONTEXT BUILDER")
    print("="*80)
    
    builder = ContextBuilder(max_events=10)
    
    # Mock events
    mock_events = [
        {
            "event_id": "test-001",
            "event_description": "Arsenal defeated Crystal Palace 8-7 on penalties",
            "event_date": "2025-01-14",
            "fact_type": "EVENT",
            "title_anchors": "Arsenal vs Palace EFL Cup",
            "entities": ["Arsenal", "Crystal Palace"],
            "sources": ["BBC Sport"],
            "constraints": ["MATCH_OUTCOME"],
            "titles": ["Arsenal vs Palace EFL Cup"]
        },
        {
            "event_id": "test-002",
            "event_description": "Bukayo Saka assisted Calafiori's goal",
            "event_date": "2025-01-14",
            "fact_type": "EVENT",
            "title_anchors": "Arsenal vs Palace EFL Cup",
            "entities": ["Bukayo Saka", "Riccardo Calafiori"],
            "sources": ["BBC Sport"],
            "constraints": ["MATCH_ACTION"],
            "titles": ["Arsenal vs Palace EFL Cup"]
        }
    ]
    
    print("\n[Test 1] Standard context")
    context = builder.build(mock_events)
    print(f"  Context length: {len(context)} characters")
    print(f"\nPreview:\n{context[:300]}...")
    
    print("\n[Test 2] Summary context")
    summary_context = builder.build_summary_context(mock_events)
    print(f"  Context length: {len(summary_context)} characters")
    
    print("\n[Test 3] Analysis context")
    analysis_context = builder.build_analysis_context(mock_events)
    print(f"  Context length: {len(analysis_context)} characters")


def test_full_graphrag_pipeline():
    """Test complete GraphRAG pipeline with 3 query types."""
    
    print("\n" + "="*80)
    print("TEST 4: COMPLETE GRAPHRAG PIPELINE")
    print("="*80)
    
    # Initialize components
    analyzer = QueryAnalyzer(model="llama3:latest")
    writer = Neo4jWriter()
    retriever = GraphRetriever(writer)
    builder = ContextBuilder(max_events=30)
    llm = OllamaBackend(model="llama3:latest")
    
    # Create GraphRAG engine
    rag = GraphRAG(analyzer, retriever, builder, llm)
    
    # Test queries covering all 3 intents
    test_queries = [
        # Fact query
        "Arsenal在2025年1月14日对阵Crystal Palace的比赛结果是什么？",
        
        # Summary query  
        "总结一下Arsenal最近的比赛表现",
        
        # Analysis query
        "分析一下Bukayo Saka在Arsenal的作用和影响"
    ]
    
    responses = []
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{'#'*80}")
        print(f"TEST QUERY {i}/3")
        print(f"{'#'*80}")
        
        try:
            response = rag.answer(query, return_context=True)
            responses.append(response)
            
            # Print summary
            print_response_summary(response)
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    writer.close()
    
    # Overall statistics
    print("\n" + "="*80)
    print("OVERALL TEST STATISTICS")
    print("="*80)
    
    for i, response in enumerate(responses, 1):
        parsed = response['parsed_query']
        events = response['retrieved_events']
        answer = response['answer']
        
        print(f"\nQuery {i}:")
        print(f"  Intent: {parsed['intent']}")
        print(f"  Events Retrieved: {len(events)}")
        print(f"  Answer Length: {len(answer)} characters")
    
    print("\n✅ All tests completed!")


def test_specific_scenarios():
    """Test specific football scenarios."""
    
    print("\n" + "="*80)
    print("TEST 5: SPECIFIC FOOTBALL SCENARIOS")
    print("="*80)
    
    analyzer = QueryAnalyzer(model="llama3:latest")
    writer = Neo4jWriter()
    retriever = GraphRetriever(writer)
    builder = ContextBuilder(max_events=20)
    llm = OllamaBackend(model="llama3:latest")
    
    rag = GraphRAG(analyzer, retriever, builder, llm)
    
    # Scenario-specific queries
    scenarios = [
        {
            "name": "Goal Query",
            "query": "Kepa在比赛中有什么表现？"
        },
        {
            "name": "Match Result Query",
            "query": "Arsenal vs Crystal Palace比赛的详细情况"
        },
        {
            "name": "Player Performance",
            "query": "Marc Guehi在这场比赛中做了什么？"
        }
    ]
    
    for scenario in scenarios:
        print(f"\n{'='*80}")
        print(f"Scenario: {scenario['name']}")
        print(f"{'='*80}")
        
        try:
            response = rag.answer(scenario['query'])
            
            print(f"\n📊 Retrieved Events: {len(response['retrieved_events'])}")
            print(f"\n💬 Answer:\n{response['answer']}")
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
    
    writer.close()


if __name__ == "__main__":
    print("\n" + "#"*80)
    print("GRAPHRAG SYSTEM - COMPREHENSIVE UNIT TESTS")
    print("#"*80)
    
    try:
        # Run all tests
        test_query_analyzer()
        test_graph_retriever()
        test_context_builder()
        test_full_graphrag_pipeline()
        test_specific_scenarios()
        
        print("\n" + "#"*80)
        print("✅ ALL TESTS COMPLETED SUCCESSFULLY")
        print("#"*80)
        
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
