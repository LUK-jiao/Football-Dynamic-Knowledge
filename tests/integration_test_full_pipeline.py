"""
Full Pipeline Integration Test: Preprocess → Extractor_v1 → Knowledge Graph

This test demonstrates the complete end-to-end pipeline:
1. Raw text → Sentence Splitter → Sentences
2. Sentences → Semantic Chunker → Semantic Blocks  
3. Semantic Blocks → Event Decomposition → Events
4. Events → Anchor Extractor → Extracted Facts (v2.0 flattened schema)
5. Extracted Facts → Neo4j Writer → Knowledge Graph

Uses real Ollama LLM and Neo4j database for full validation.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from preprocess.sentence_splitter import SentenceSplitter
from preprocess.semantic_blocker import SemanticChunker, ChunkerConfig, GranularityMode, OllamaBackend as PreprocessBackend
from extractor_v1.anchor_extractor import AnchorExtractor
from extractor_v1.ollama_backend import OllamaBackend as ExtractorBackend
from knowledge_graph.neo4j_writer import Neo4jWriter
import logging
import json
from datetime import datetime
from typing import List, Dict, Any
import time

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)


def format_semantic_blocks_for_decomposition(chunks: List[Any], source_name: str, title: str, publish_date: str) -> List[Dict[str, Any]]:
    """
    Convert semantic chunks from preprocess to blocks for event decomposition.
    
    Filters out quotes chunks as they don't contain extractable facts.
    
    Args:
        chunks: Semantic chunks from SemanticChunker
        source_name: Source name (e.g., "BBC Sport")
        title: Article title
        publish_date: Publication date in YYYY-MM-DD format
    
    Returns:
        List of blocks ready for Event Decomposition (excluding quotes blocks)
    """
    blocks = []
    filtered_count = 0
    
    for chunk in chunks:
        # Filter out quotes chunks (player/coach interviews, statements)
        if chunk.chunk_type == "quotes":
            filtered_count += 1
            continue
        
        # Combine all sentences in the chunk into text
        text = ' '.join(chunk.sentences)
        
        block = {
            "block_id": f"block_{chunk.chunk_id}",
            "text": text,
            "source": source_name,
            "title": title,
            "publish_date": publish_date,
            "chunk_type": chunk.chunk_type
        }
        
        blocks.append(block)
    
    if filtered_count > 0:
        print(f"  ℹ️  Filtered out {filtered_count} quotes chunk(s)")
    
    return blocks


def print_extraction_results(results: List[Dict[str, Any]]):
    """Pretty print extraction results (flattened v2.0 schema)."""
    
    print("\n" + "="*80)
    print("EXTRACTION RESULTS")
    print("="*80)
    
    for result in results:
        print(f"\n[Event {result['event_id']}]")
        print(f"Title: {result.get('title_anchors', 'N/A')}")
        print(f"Description: {result.get('event_description', 'N/A')[:100]}...")
        print(f"Fact Type: {result['fact_type']}")
        
        # Participants (top level)
        participants = result.get('participants', [])
        if participants:
            print(f"\nParticipants ({len(participants)}):")
            for p in participants:
                print(f"  • {p['name']} ({p['type']})")
        
        # Temporal Anchors (top level)
        temporal = result.get('temporal_anchors', [])
        if temporal:
            print(f"\nTemporal Anchors ({len(temporal)}):")
            for t in temporal:
                if t.get('event_date'):
                    print(f"  • Event Date: {t['event_date']}")
                if t.get('valid_from') or t.get('valid_to'):
                    print(f"  • Valid Period: {t.get('valid_from', '?')} → {t.get('valid_to', '?')}")
        
        # Sources (top level)
        sources = result.get('sources', [])
        if sources:
            print(f"\nSources ({len(sources)}):")
            for s in sources:
                source_type = s.get('type', 'UNKNOWN')
                source_name = s.get('source', 'N/A')
                print(f"  • {source_name} ({source_type})")
        
        # Constraints (top level)
        constraints = result.get('constraints', [])
        if constraints:
            print(f"\nConstraints ({len(constraints)}):")
            for c in constraints:
                print(f"  • {c['type']}")
        
        print("-"*80)


def print_neo4j_stats(writer: Neo4jWriter, event_ids: List[str]):
    """Print Neo4j graph statistics."""
    
    print("\n" + "="*80)
    print("NEO4J GRAPH STATISTICS")
    print("="*80)
    
    # Query node counts
    query_node_counts = """
    MATCH (e:Event)
    WITH count(e) as event_count
    MATCH (ent:Entity)
    WITH event_count, count(ent) as entity_count
    MATCH (s:Source)
    WITH event_count, entity_count, count(s) as source_count
    MATCH (c:ConstraintAnchor)
    WITH event_count, entity_count, source_count, count(c) as constraint_count
    MATCH (t:TitleAnchor)
    RETURN event_count, entity_count, source_count, constraint_count, count(t) as title_count
    """
    
    with writer.driver.session() as session:
        result = session.run(query_node_counts)
        stats = result.single()
        
        print(f"Node Counts:")
        print(f"  • Events: {stats['event_count']}")
        print(f"  • Entities: {stats['entity_count']}")
        print(f"  • Sources: {stats['source_count']}")
        print(f"  • Constraint Anchors: {stats['constraint_count']}")
        print(f"  • Title Anchors: {stats['title_count']}")
        
        # Query relationship counts
        query_rel_counts = """
        MATCH ()-[r:INVOLVES]->()
        WITH count(r) as involves_count
        MATCH ()-[r:REPORTED_BY]->()
        WITH involves_count, count(r) as reported_count
        MATCH ()-[r:CONSTRAINS]->()
        WITH involves_count, reported_count, count(r) as constrains_count
        MATCH ()-[r:HAS_TITLE_ANCHOR]->()
        RETURN involves_count, reported_count, constrains_count, count(r) as title_rel_count
        """
        
        result = session.run(query_rel_counts)
        rel_stats = result.single()
        
        print(f"\nRelationship Counts:")
        print(f"  • INVOLVES: {rel_stats['involves_count']}")
        print(f"  • REPORTED_BY: {rel_stats['reported_count']}")
        print(f"  • CONSTRAINS: {rel_stats['constrains_count']}")
        print(f"  • HAS_TITLE_ANCHOR: {rel_stats['title_rel_count']}")
        
        # Query entity types
        query_entity_types = """
        MATCH (e:Entity)
        RETURN labels(e) as labels, count(*) as count
        ORDER BY count DESC
        """
        
        result = session.run(query_entity_types)
        print(f"\nEntity Type Distribution:")
        for record in result:
            labels = [l for l in record['labels'] if l != 'Entity']
            if labels:
                print(f"  • {labels[0]}: {record['count']}")


def verify_graph_data(writer: Neo4jWriter, event_ids: List[str]):
    """Verify that data was correctly written to Neo4j."""
    
    print("\n" + "="*80)
    print("GRAPH DATA VERIFICATION")
    print("="*80)
    
    for event_id in event_ids[:3]:  # Check first 3 events
        print(f"\n[Verifying Event: {event_id}]")
        
        event_data = writer.get_event_full_view(event_id)
        
        if not event_data:
            print(f"  ✗ Event not found in graph!")
            continue
        
        event = event_data.get('event', {})
        entities = event_data.get('entities', [])
        sources = event_data.get('sources', [])
        constraints = event_data.get('constraints', [])
        titles = event_data.get('titles', [])
        
        print(f"  ✓ Event found: {event.get('title_anchors', 'N/A')[:50]}...")
        print(f"  ✓ Entities: {len(entities)}")
        print(f"  ✓ Sources: {len(sources)}")
        print(f"  ✓ Constraints: {len(constraints)}")
        print(f"  ✓ Titles: {len(titles)}")
        
        # Verify relationships
        if entities:
            print(f"    Sample entity: {entities[0].get('name')} ({entities[0].get('type')})")
        if sources:
            print(f"    Sample source: {sources[0].get('source')} ({sources[0].get('type')})")
        if constraints:
            print(f"    Sample constraint: {constraints[0].get('type')}")


def test_full_pipeline():
    """Test complete pipeline from raw text to knowledge graph."""
    
    print("="*80)
    print("FULL PIPELINE INTEGRATION TEST")
    print("Preprocess → Extractor_v1 → Knowledge Graph")
    print("="*80)
    
    # ========================================================================
    # Test Article: Arsenal vs Crystal Palace EFL Cup Match
    # ========================================================================
    
    raw_text = """
    Mikel Arteta's Arsenal side marched on to the EFL Cup semi-finals but did it the hard way by winning 8-7 on penalties against Crystal Palace, 
    with Kepa Arrizabalaga saving the 16th spot-kick taken by Maxence Lacroix after 15 successful conversions.
    Two late goals had resulted in a 1-1 draw after 90 minutes and a lengthy period of stoppage time.
    The Gunners will now face rivals Chelsea to fight for a place in the final at Wembley, with the first leg of their semi-final set for Stamford Bridge on 14 January.
    After bossing much of the quarter-final against Palace and creating the majority of big chances, Arteta's men finally found their breakthrough, which came from a corner in the 80th minute. A well-placed delivery into the box from Bukayo Saka found the head of Riccardo Calafiori and eventually went into the net off Palace centre-back Lacroix.
    The unfortunate own goal did not dampen Palace's spirits as they went in search of an equaliser. When it finally did arrive, they had club captain Marc Guehi to thank. The England international was the first to react to a knock-on from Jefferson Lerma in the fifth minute of stoppage time.
    A fascinating penalty shoot-out then ensued, with both sides delivering spectacular finishes to take the score to 8-7. When the own-goal scorer Lacroix stepped up to take his kick, Arsenal keeper Kepa read its direction and made the save to ensure the Gunners remain on course for their first Wembley appearance in five years.
    This was Arsenal's second-highest scoring penalty shootout, after their 9-8 victory against Rotherham in 2003/04. Overall, the Gunners have converted 47 of their last 51 spot-kicks in shoot-outs, giving them a supreme 92 per cent conversion rate.
    Arteta told Sky Sports after the game: "I'm very happy to be in the semi-finals. We played against a team who are hard to generate chances against. We generated a lot and we should have scored many more goals."
    The Arsenal boss had made eight changes to his starting line-up and admitted: "It's always tough because they don't have the right chemistry when they haven't played together. But their attitude is excellent."
    """
    
    title = "Arsenal Wins EFL Cup Quarter-Final Against Crystal Palace on Penalties"
    source_name = "BBC Sport"
    publish_date = "2025-01-14"
    
    print(f"\n📰 Article Info:")
    print(f"  Title: {title}")
    print(f"  Source: {source_name}")
    print(f"  Date: {publish_date}")
    print(f"  Length: {len(raw_text)} characters")
    
    # ========================================================================
    # STEP 1: Sentence Splitting
    # ========================================================================
    print("\n" + "="*80)
    print("STEP 1: SENTENCE SPLITTING")
    print("="*80)
    
    step1_start = time.time()
    
    splitter = SentenceSplitter(min_length=10)
    sentences = splitter.split(raw_text)
    
    step1_time = time.time() - step1_start
    
    print(f"✓ Split into {len(sentences)} sentences ({step1_time:.2f}s)")
    print(f"\nSample sentences:")
    for i, sent in enumerate(sentences[:3], 1):
        print(f"  {i}. {sent[:80]}...")
    
    # ========================================================================
    # STEP 2: Semantic Chunking
    # ========================================================================
    print("\n" + "="*80)
    print("STEP 2: SEMANTIC CHUNKING")
    print("="*80)
    
    step2_start = time.time()
    
    preprocess_backend = PreprocessBackend(
        model="gemma3:12b",
        timeout=30,
        temperature=0.05
    )
    
    config = ChunkerConfig(
        granularity=GranularityMode.MEDIUM,
        context_window=2,
        max_sentences_per_chunk=10,
        enable_structural_rules=False,
        enable_orphan_merge=False,
        log_scores=True
    )
    
    chunker = SemanticChunker(llm=preprocess_backend, config=config)
    chunks = chunker.chunk(sentences)
    
    step2_time = time.time() - step2_start
    
    print(f"✓ Created {len(chunks)} semantic chunks ({step2_time:.2f}s)")
    print(f"\nChunk breakdown:")
    for chunk in chunks:
        preview = ' '.join(chunk.sentences)[:80]
        print(f"  • Chunk {chunk.chunk_id} ({chunk.chunk_type}): {preview}...")
    
    # ========================================================================
    # STEP 3: Format Blocks for Decomposition
    # ========================================================================
    print("\n" + "="*80)
    print("STEP 3: FORMAT BLOCKS FOR DECOMPOSITION")
    print("="*80)
    
    blocks = format_semantic_blocks_for_decomposition(chunks, source_name, title, publish_date)
    print(f"✓ Formatted {len(blocks)} blocks (filtered quotes)")
    
    # ========================================================================
    # STEP 4: Event Decomposition
    # ========================================================================
    print("\n" + "="*80)
    print("STEP 4: EVENT DECOMPOSITION")
    print("="*80)
    
    step4_start = time.time()
    
    extractor_backend = ExtractorBackend(model="llama3:latest")
    
    all_events = []
    for i, block in enumerate(blocks, 1):
        print(f"  Processing block {i}/{len(blocks)}...", end=" ")
        
        decomp_result = extractor_backend.decompose_events(block)
        events = decomp_result.get('events', [])
        all_events.extend(events)
        
        print(f"✓ ({len(events)} events)")
    
    step4_time = time.time() - step4_start
    
    print(f"\n✓ Decomposed {len(blocks)} blocks into {len(all_events)} events ({step4_time:.2f}s)")
    print(f"  Average: {step4_time/len(blocks):.2f}s per block")
    
    # ========================================================================
    # STEP 5: Anchor Extraction
    # ========================================================================
    print("\n" + "="*80)
    print("STEP 5: ANCHOR EXTRACTION")
    print("="*80)
    
    step5_start = time.time()
    
    extractor = AnchorExtractor(model="llama3:latest")
    
    results = []
    for i, event in enumerate(all_events, 1):
        print(f"  Processing event {i}/{len(all_events)} [{event['event_id']}]...", end=" ")
        
        result = extractor.extract_anchors(event)
        results.append(result)
        
        inference_time = result.get('inference_time', 0)
        print(f"✓ ({inference_time:.2f}s)")
    
    step5_time = time.time() - step5_start
    
    print(f"\n✓ Extracted anchors from {len(results)} events ({step5_time:.2f}s)")
    print(f"  Average: {step5_time/len(results):.2f}s per event")
    
    # Display extraction results
    print_extraction_results(results)
    
    # ========================================================================
    # STEP 6: Write to Knowledge Graph
    # ========================================================================
    print("\n" + "="*80)
    print("STEP 6: WRITE TO KNOWLEDGE GRAPH (Neo4j)")
    print("="*80)
    
    step6_start = time.time()
    
    try:
        with Neo4jWriter() as writer:
            print("  Initializing constraints...", end=" ")
            writer.initialize_constraints()
            print("✓")
            
            print(f"  Writing {len(results)} events to Neo4j...", end=" ")
            writer.upsert_events(results)
            print("✓")
            
            step6_time = time.time() - step6_start
            
            print(f"\n✓ Successfully wrote to knowledge graph ({step6_time:.2f}s)")
            print(f"  Average: {step6_time/len(results):.2f}s per event")
            
            # Print statistics
            print_neo4j_stats(writer, [r['event_id'] for r in results])
            
            # Verify data integrity
            verify_graph_data(writer, [r['event_id'] for r in results])
            
    except Exception as e:
        print(f"\n✗ Failed to write to Neo4j: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # ========================================================================
    # PIPELINE SUMMARY
    # ========================================================================
    print("\n" + "="*80)
    print("PIPELINE SUMMARY")
    print("="*80)
    
    total_time = step1_time + step2_time + step4_time + step5_time + step6_time
    
    print(f"\nProcessing Times:")
    print(f"  1. Sentence Splitting:     {step1_time:>8.2f}s ({step1_time/total_time*100:>5.1f}%)")
    print(f"  2. Semantic Chunking:      {step2_time:>8.2f}s ({step2_time/total_time*100:>5.1f}%)")
    print(f"  3. Event Decomposition:    {step4_time:>8.2f}s ({step4_time/total_time*100:>5.1f}%)")
    print(f"  4. Anchor Extraction:      {step5_time:>8.2f}s ({step5_time/total_time*100:>5.1f}%)")
    print(f"  5. Knowledge Graph Write:  {step6_time:>8.2f}s ({step6_time/total_time*100:>5.1f}%)")
    print(f"  " + "-"*60)
    print(f"  Total Pipeline Time:       {total_time:>8.2f}s")
    
    print(f"\nOutput Statistics:")
    print(f"  • Input: {len(raw_text)} characters")
    print(f"  • Sentences: {len(sentences)}")
    print(f"  • Semantic Chunks: {len(chunks)}")
    print(f"  • Decomposed Events: {len(all_events)}")
    print(f"  • Extracted Facts: {len(results)}")
    print(f"  • Graph Nodes: Events + Entities + Sources + Anchors")
    
    # ========================================================================
    # VALIDATION
    # ========================================================================
    print("\n" + "="*80)
    print("VALIDATION")
    print("="*80)
    
    assertions = [
        (len(sentences) > 0, "Should produce sentences"),
        (len(chunks) > 0, "Should produce semantic chunks"),
        (len(blocks) > 0, "Should produce blocks for decomposition"),
        (len(all_events) > 0, "Should decompose into events"),
        (len(results) > 0, "Should extract anchors"),
        (len(results) == len(all_events), "All events should be processed"),
        (all('participants' in r for r in results), "All results should have participants"),
        (all('fact_type' in r for r in results), "All results should have fact_type"),
        (all('event_id' in r for r in results), "All results should have event_id"),
    ]
    
    all_passed = True
    for condition, description in assertions:
        status = "✓" if condition else "✗"
        print(f"  {status} {description}")
        if not condition:
            all_passed = False
    
    # Quality checks
    print("\n[Quality Checks]")
    
    total_participants = sum(len(r.get('participants', [])) for r in results)
    total_constraints = sum(len(r.get('constraints', [])) for r in results)
    total_sources = sum(len(r.get('sources', [])) for r in results)
    
    print(f"  • Total participants extracted: {total_participants}")
    print(f"  • Total constraints extracted: {total_constraints}")
    print(f"  • Total sources extracted: {total_sources}")
    
    if all_passed:
        print("\n" + "="*80)
        print("✅ FULL PIPELINE INTEGRATION TEST PASSED")
        print("="*80)
        return True
    else:
        print("\n" + "="*80)
        print("❌ SOME TESTS FAILED")
        print("="*80)
        return False


if __name__ == "__main__":
    success = test_full_pipeline()
    sys.exit(0 if success else 1)
