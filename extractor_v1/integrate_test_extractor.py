"""
Integration Test: Preprocess Pipeline → Event Decomposition → Anchor Extractor

This test demonstrates the complete end-to-end pipeline:
1. Raw text → Sentence Splitter → Sentences
2. Sentences → Semantic Chunker → Semantic Blocks
3. Semantic Blocks → Event Decomposition → Events
4. Events → Anchor Extractor → Extracted Anchors

Uses real Ollama LLM for full pipeline validation.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from preprocess.sentence_splitter import SentenceSplitter
from preprocess.semantic_blocker import SemanticChunker, ChunkerConfig, GranularityMode, OllamaBackend as PreprocessBackend
from extractor_v1.anchor_extractor import AnchorExtractor
from extractor_v1.ollama_backend import OllamaBackend as ExtractorBackend
import logging
import json
from datetime import datetime
from typing import List, Dict, Any

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
            "chunk_type": chunk.chunk_type  # Keep track of chunk type
        }
        
        blocks.append(block)
    
    if filtered_count > 0:
        print(f"  ℹ️  Filtered out {filtered_count} quotes chunk(s)")
    
    return blocks


def print_extraction_results(results: List[Dict[str, Any]]):
    """Pretty print extraction results (adapted for flattened schema)."""
    
    print("\n" + "="*80)
    print("EXTRACTION RESULTS")
    print("="*80)
    
    for result in results:
        print(f"\n[Event {result['event_id']}]")
        print(f"Title: {result.get('title_anchors', 'N/A')}")
        print(f"Description: {result.get('event_description', 'N/A')[:100]}...")
        print(f"Fact Type: {result['fact_type']}")
        
        # Participants (now at top level)
        participants = result.get('participants', [])
        if participants:
            print(f"\nParticipants ({len(participants)}):")
            for p in participants:
                print(f"  • {p['name']} ({p['type']})")
        
        # Temporal Anchors (now at top level)
        temporal = result.get('temporal_anchors', [])
        if temporal:
            print(f"\nTemporal Anchors ({len(temporal)}):")
            for t in temporal:
                if t.get('event_date'):
                    print(f"  • Event Date: {t['event_date']}")
                if t.get('valid_from') or t.get('valid_to'):
                    print(f"  • Valid Period: {t.get('valid_from', '?')} → {t.get('valid_to', '?')}")
        
        # Sources (now at top level)
        sources = result.get('sources', [])
        if sources:
            print(f"\nSources ({len(sources)}):")
            for s in sources:
                source_type = s.get('type', 'UNKNOWN')
                source_name = s.get('source', 'N/A')
                print(f"  • {source_name} ({source_type})")
        
        # Constraints (now at top level, simplified structure)
        constraints = result.get('constraints', [])
        if constraints:
            print(f"\nConstraints ({len(constraints)}):")
            for c in constraints:
                print(f"  • {c['type']}")
        
        print("-"*80)


def test_full_pipeline_with_extraction():
    """Test complete pipeline: preprocess → decomposition → extraction."""
    
    print("="*80)
    print("INTEGRATION TEST: Full Pipeline (Preprocess → Decomposition → Extraction)")
    print("="*80)
    
    # ========================================================================
    # Test Case 1: Frank leaves Tottenham Hotspur - Coach Departure Announcement
    # ========================================================================
    print("\n[TEST 1] Frank leaves Tottenham Hotspur - Coach Departure Announcement")
    print("-"*80)
    
    raw_text = """
    Tottenham Hotspur have confirmed the departure of head coach Thomas Frank with immediate effect. The 52-year-old Dane joined Spurs last summer after a successful seven-year spell with Brentford. His appointment on 12 June 2025 followed the departure of Ange Postecoglou. Frank made an encouraging start, winning three of his first four Premier League matches and overseeing a narrow defeat to UEFA Champions League winners Paris Saint-Germain in the UEFA Super Cup. However, Spurs' form has dipped since, with Tuesday's 2-1 home defeat by Newcastle United proving to be the Dane's last match in charge. That result leaves Spurs 16th in the table, five points clear of the relegation zone. Frank leaves having overseen 13 wins, 11 draws and 14 losses in his 38 games in charge. There has already been much speculation over who could succeed Frank. Former Spurs manager Mauricio Pochettino, who took the club to a second-placed Premier League finish in 2016/17 and a Champions League final in 2018/19, is one possible candidate, although he will lead the United States Men's National Team in the upcoming FIFA World Cup this summer. Former Brighton & Hove Albion head coach Roberto De Zerbi has been mooted after leaving Marseille, as has ex-Spurs forward Robbie Keane, now coaching at Ferencvaros in Hungary, and former Barcelona head coach Xavi."""
    title = "Head coach leaves north London club after eight months in charge following 2-1 defeat to Newcastle"
    
    source_name = "BBC Sport"
    publish_date = "2025-02-12"
    
    print(f"\nSource: {source_name}")
    print(f"Date: {publish_date}")
    print(f"Title: {title}")
    print(f"\nOriginal text:")

    print(raw_text[:150] + "...")
    
    # ========================================================================
    # STEP 1: Sentence Splitting
    # ========================================================================
    print("\n[STEP 1] Sentence Splitting...")
    
    splitter = SentenceSplitter(min_length=10)
    sentences = splitter.split(raw_text)
    
    print(f"  ✓ Split into {len(sentences)} sentences")
    
    # ========================================================================
    # STEP 2: Semantic Chunking
    # ========================================================================
    print("\n[STEP 2] Semantic Chunking...")
    
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
    
    print(f"  ✓ Created {len(chunks)} semantic chunks:")
    for chunk in chunks:
        preview = ' '.join(chunk.sentences)
        print(f"    • Chunk {chunk.chunk_id} ({chunk.chunk_type}): {preview}")
    
    # ========================================================================
    # STEP 3: Format blocks for decomposition (filter quote_attribution)
    # ========================================================================
    print("\n[STEP 3] Formatting blocks for event decomposition...")
    
    blocks = format_semantic_blocks_for_decomposition(chunks, source_name, title, publish_date)
    print(f"  ✓ Formatted {len(blocks)} blocks for decomposition")
    
    # ========================================================================
    # STEP 4: Event Decomposition
    # ========================================================================
    print("\n[STEP 4] Decomposing blocks into events...")
    
    extractor_backend = ExtractorBackend(model="llama3:latest")
    
    # Decompose each block into events
    all_events = []
    total_decomp_time = 0.0
    
    for i, block in enumerate(blocks, 1):
        print(f"\n  Processing block {i}/{len(blocks)}...", end=" ")
        
        import time
        start_time = time.time()
        decomp_result = extractor_backend.decompose_events(block)
        decomp_time = time.time() - start_time
        total_decomp_time += decomp_time
        
        events = decomp_result.get('events', [])
        all_events.extend(events)
        
        print(f"✓ ({len(events)} events, {decomp_time:.2f}s)")
    
    print(f"\n  ✓ Decomposed {len(blocks)} blocks into {len(all_events)} events")
    print(f"  ✓ Total decomposition time: {total_decomp_time:.2f}s")
    print(f"  ✓ Average per block: {total_decomp_time/len(blocks):.2f}s")
    
    # ========================================================================
    # STEP 5: Anchor Extraction
    # ========================================================================
    print("\n[STEP 5] Extracting anchors from events...")
    
    extractor = AnchorExtractor(model="llama3:latest")
    
    # Extract anchors from all events
    results = []
    total_inference_time = 0.0
    
    for i, event in enumerate(all_events, 1):
        print(f"\n  Processing event {i}/{len(all_events)} [{event['event_id']}]...", end=" ")
        
        result = extractor.extract_anchors(event)
        results.append(result)
        
        inference_time = result.get('inference_time', 0)
        total_inference_time += inference_time
        
        print(f"✓ ({inference_time:.2f}s)")
    
    print(f"\n  ✓ Extracted anchors from {len(results)} events")
    print(f"  ✓ Total inference time: {total_inference_time:.2f}s")
    print(f"  ✓ Average per event: {total_inference_time/len(results):.2f}s")
    
    # ========================================================================
    # Display Results
    # ========================================================================
    print_extraction_results(results)
    
    # ========================================================================
    # Validation
    # ========================================================================
    print("\n" + "="*80)
    print("[VALIDATION]")
    print("="*80)
    
    assertions = [
        (len(sentences) > 0, "Should produce sentences"),
        (len(chunks) > 0, "Should produce semantic chunks"),
        (len(blocks) > 0, "Should produce blocks for decomposition"),
        (len(all_events) > 0, "Should produce events from decomposition"),
        (len(results) > 0, "Should produce extraction results"),
        (len(results) == len(all_events), "All events should be processed"),
        (all('participants' in r for r in results), "All results should have participants"),
        (all('fact_type' in r for r in results), "All results should have fact_type"),
    ]
    
    all_passed = True
    for condition, description in assertions:
        status = "✓" if condition else "✗"
        print(f"  {status} {description}")
        if not condition:
            all_passed = False
    
    # Check for common issues
    print("\n[Quality Checks]")
    
    # Check participants (now at top level)
    total_participants = sum(len(r.get('participants', [])) for r in results)
    print(f"  • Total participants extracted: {total_participants}")
    
    # Check constraints (now at top level)
    total_constraints = sum(len(r.get('constraints', [])) for r in results)
    print(f"  • Total constraints extracted: {total_constraints}")
    
    # Check for nickname conversion
    all_participant_names = [p['name'] for r in results for p in r.get('participants', [])]
    has_arsenal = 'Arsenal' in all_participant_names
    has_gunners = 'The Gunners' in all_participant_names or 'the Gunners' in all_participant_names
    
    print(f"  • Arsenal correctly identified: {'✓' if has_arsenal else '✗'}")
    print(f"  • 'The Gunners' converted: {'✓' if not has_gunners else '✗ (still using nickname)'}")
    
    if all_passed:
        print("\n" + "="*80)
        print("✓ ALL INTEGRATION TESTS PASSED")
        print("="*80)
        return True, results, total_inference_time, len(results)
    else:
        print("\n" + "="*80)
        print("✗ SOME TESTS FAILED")
        print("="*80)
        return False, results, total_inference_time, len(results)


def test_transfer_news():
    """Test pipeline with transfer news."""
    
    print("\n" + "="*80)
    print("[TEST 2] Transfer News - Taty Castellanos")
    print("="*80)
    
    raw_text = """
    West Ham United is delighted to announce the signing of Argentina international forward Taty Castellanos. 
The 27-year-old joins the Hammers from Italian club Lazio on a four-and-a-half year contract with the option for 
a further year. An aggressive, deep-lying forward capable of scoring and creating goals, linking play and working
 hard for his team, Castellanos has enjoyed a superb career in the MLS, La Liga and Serie A and will now bring his 
 all-round qualities to the Premier League. Born in Mendoza and capped twice by his country, Castellanos won the MLS 
 Cup and Golden Boot with New York City FC in 2021 before netting four goals in a single game for Girona against Real Madrid 
 in La Liga in 2023. He then scored 14 times last season as Lazio finished seventh in Serie A and reached the UEFA Europa League quarter-finals. 
 Identified as a key target by Head Coach Nuno Espírito Santo, the Hammers’ new No11 — who has signed in time to be 
 available for Tuesday evening’s Premier League match against Nottingham Forest at London Stadium — is now looking forward to pulling on a West Ham 
 shirt and showing the Claret and Blue Army what he can do. “I'm really happy because it's a very important challenge for me personally and I've 
 come to contribute, to try to help the team as much as I can,” said Castellanos. “Every match is a battle, and I'm here to contribute that, 
 to try to bring that energy, that fighting spirit I have inside, so that every match is as important and as tough as possible. I hope to 
 give my all to the fans. I've always defended the jersey of every team with the utmost responsibility, and 
 I want to tell them that I'm going to give everything, to defend this jersey, and obviously, to achieve our goals day after day. That's 
 the most important thing.” Everyone at West Ham United would like to welcome Taty and his family to East London, and wishes him every success for his career in Claret and Blue.
"""
    title="Taty Castellanos Joins West Ham United - Official Announcement"
    
    source_name = "West Ham Official"
    publish_date = "2025-01-09"
    
    print(f"\nSource: {source_name}")
    print(f"Date: {publish_date}")
    print(f"Title: {title}")
    
    # Pipeline
    splitter = SentenceSplitter(min_length=10)
    sentences = splitter.split(raw_text)
    print(f"\n[STEP 1] Split into {len(sentences)} sentences")
    
    preprocess_backend = PreprocessBackend(model="gemma3:12b", timeout=30, temperature=0.2)
    config = ChunkerConfig(granularity=GranularityMode.MEDIUM, log_scores=False)
    chunker = SemanticChunker(llm=preprocess_backend, config=config)
    
    chunks = chunker.chunk(sentences)
    print(f"[STEP 2] Created {len(chunks)} semantic chunks")
    for chunk in chunks:
        preview = ' '.join(chunk.sentences)
        print(f"  • Chunk {chunk.chunk_id} ({chunk.chunk_type}): {preview}")
    
    blocks = format_semantic_blocks_for_decomposition(chunks, source_name, title, publish_date)
    print(f"[STEP 3] Formatted {len(blocks)} blocks for decomposition")
    
    # Event Decomposition
    extractor_backend = ExtractorBackend(model="llama3:latest")
    all_events = []
    
    print(f"[STEP 4] Decomposing blocks into events...")
    import time
    for block in blocks:
        decomp_result = extractor_backend.decompose_events(block)
        all_events.extend(decomp_result.get('events', []))
    
    print(f"  ✓ Decomposed {len(blocks)} blocks into {len(all_events)} events")
    
    # Anchor Extraction
    extractor = AnchorExtractor(model="llama3:latest")
    
    results = []
    total_time = 0.0
    
    print(f"[STEP 5] Extracting anchors from events...")
    for i, event in enumerate(all_events, 1):
        print(f"  Processing event {i}/{len(all_events)} [{event['event_id']}]...", end=" ")
        result = extractor.extract_anchors(event)
        results.append(result)
        inference_time = result.get('inference_time', 0)
        total_time += inference_time
        print(f"✓ ({inference_time:.2f}s)")
    
    print(f"\n  ✓ Extracted anchors from {len(results)} events")
    print(f"  ✓ Total inference time: {total_time:.2f}s")
    if len(results) > 0:
        print(f"  ✓ Average per event: {total_time/len(results):.2f}s")
    
    print_extraction_results(results)
    
    return True, results, total_time, len(results)


def save_results_to_file(results: List[Dict[str, Any]], test_name: str):
    """Save extraction results to JSON file."""
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"extractor_v1/output/integrate_test_{test_name}_{timestamp}.json"
    
    output_dir = os.path.dirname(filename)
    os.makedirs(output_dir, exist_ok=True)
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Results saved to: {filename}")


def main():
    """Run all integration tests."""
    
    try:
        # Test 1: Match report
        success1, results1, time1, blocks1 = test_full_pipeline_with_extraction()
        
        if success1:
            save_results_to_file(results1, "arsenal_palace_match")
        
        # Test 2: Transfer news
        success2, results2, time2, blocks2 = test_transfer_news()
        
        if success2:
            save_results_to_file(results2, "castellanos_transfer")
        
        # Final summary
        print("\n" + "="*80)
        print("INTEGRATION TEST SUMMARY")
        print("="*80)
        print(f"  Test 1 (Match Report): {'✓ PASSED' if success1 else '✗ FAILED'}")
        if success1:
            print(f"    - Blocks processed: {blocks1}")
            print(f"    - Total time: {time1:.2f}s")
            print(f"    - Average per block: {time1/blocks1 if blocks1 > 0 else 0:.2f}s")
        
        print(f"\n  Test 2 (Transfer News): {'✓ PASSED' if success2 else '✗ FAILED'}")
        if success2:
            print(f"    - Blocks processed: {blocks2}")
            print(f"    - Total time: {time2:.2f}s")
            print(f"    - Average per block: {time2/blocks2 if blocks2 > 0 else 0:.2f}s")
        
        # Overall statistics
        if success1 and success2:
            total_blocks = blocks1 + blocks2
            total_time = time1 + time2
            print(f"\n  Overall Statistics:")
            print(f"    - Total blocks: {total_blocks}")
            print(f"    - Total time: {total_time:.2f}s")
            print(f"    - Average per block: {total_time/total_blocks if total_blocks > 0 else 0:.2f}s")
        
        if success1 and success2:
            print("\n🎉 All integration tests passed!")
            print("="*80)
            return 0
        else:
            print("\n⚠️  Some tests failed")
            return 1
            
    except KeyboardInterrupt:
        print("\n\n✗ Interrupted by user")
        return 1
    except Exception as e:
        print(f"\n\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
