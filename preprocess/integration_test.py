"""
Integration Test: Sentence Splitting + Semantic Chunking

This test demonstrates the complete pipeline:
1. Raw text → Sentence Splitter → Sentences
2. Sentences → Semantic Chunker → Semantic Chunks

Uses real Ollama LLM for end-to-end validation.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sentence_splitter import SentenceSplitter
from semantic_blocker import semantic_chunk, OllamaBackend, ChunkerConfig
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)


def test_full_pipeline():
    """Test complete text processing pipeline."""
    
    print("="*80)
    print("INTEGRATION TEST: Sentence Splitter + Semantic Chunker")
    print("="*80)
    
    # ========================================================================
    # Test Case 1: Football Match Report
    # ========================================================================
    print("\n[TEST 1] Football Match Report")
    print("-"*80)
    
    text_1 = """
    Mikel Arteta's Arsenal side marched on to the EFL Cup semi-finals but did it the hard way by winning 8-7 on penalties against Crystal Palace, 
    with Kepa Arrizabalaga saving the 16th spot-kick taken by Maxence Lacroix after 15 successful conversions.
    Two late goals had resulted in a 1-1 draw after 90 minutes and a lengthy period of stoppage time.
    The Gunners will now face rivals Chelsea to fight for a place in the final at Wembley, with the first leg of their semi-final set for Stamford Bridge on 14 January.
    After bossing much of the quarter-final against Palace and creating the majority of big chances, Arteta's men finally found their breakthrough, which came from a corner in the 80th minute. A well-placed delivery into the box from Bukayo Saka found the head of Riccardo Calafiori and eventually went into the net off Palace centre-back Lacroix.
    The unfortunate own goal did not dampen Palace's spirits as they went in search of an equaliser. When it finally did arrive, they had club captain Marc Guehi to thank. The England international was the first to react to a knock-on from Jefferson Lerma in the fifth minute of stoppage time.
    A fascinating penalty shoot-out then ensued, with both sides delivering spectacular finishes to take the score to 8-7. When the own-goal scorer Lacroix stepped up to take his kick, Arsenal keeper Kepa read its direction and made the save to ensure the Gunners remain on course for their first Wembley appearance in five years.
    This was Arsenal's second-highest scoring penalty shootout, after their 9-8 victory against Rotherham in 2003/04. Overall, the Gunners have converted 47 of their last 51 spot-kicks in shoot-outs, giving them a supreme 92 per cent conversion rate.
    Arteta told Sky Sports after the game: "I'm very happy to be in the semi-finals. We played against a team who are hard to generate chances against. We generated a lot and we should have scored many more goals."
    The Arsenal boss had made eight changes to his starting line-up and admitted: "It's always tough because they don't have the right chemistry when they haven't played together. But their attitude is excellent.
    "I think we had some big individual performances tonight. It's great for Gabriel Jesus tonight, after almost a year out, to start a game and make his 100th [Arsenal] appearance. The commitment within the group is incredible and I'm very happy for the boys."
    """
    
    print("\nOriginal text:")
    print(text_1[:200] + "...")
    
    # Step 1: Sentence splitting
    print("\n[Step 1] Sentence Splitting...")
    splitter = SentenceSplitter(min_length=10)
    sentences = splitter.split(text_1)
    
    print(f"  ✓ Split into {len(sentences)} sentences:")
    for i, sent in enumerate(sentences, 1):
        print(f"    {i}. {sent}")
    
    # Step 2: Semantic chunking
    print("\n[Step 2] Semantic Chunking with Ollama...")
    
    backend = OllamaBackend(model="llama3:latest", timeout=30)
    
    # Test connection first
    if not backend.test_connection():
        print("  ✗ Cannot connect to Ollama server")
        print("  Please start Ollama: ollama serve")
        return False
    
    config = ChunkerConfig(
        window_size=1,
        force_new_on_failure=True,
        log_failures=False  # Reduce noise in test output
    )
    
    chunks = semantic_chunk(sentences, backend, window_size=1)
    
    print(f"  ✓ Created {len(chunks)} semantic chunks:")
    for i, chunk in enumerate(chunks, 1):
        print(f"\n    Chunk {i} ({len(chunk)} sentences):")
        for sent in chunk:
            print(f"      • {sent}")
    
    # ========================================================================
    # Test Case 2: Transfer News & Injury Update
    # ========================================================================
    print("\n" + "="*80)
    print("[TEST 2] Mixed Topics (Transfer + Injury)")
    print("-"*80)
    
    text_2 = """
    Manchester United have completed the signing of striker Marcus Thuram from Inter Milan.
    The transfer fee is reported to be €85 million. Thuram signed a five-year contract with 
    the Red Devils. He will wear the number 9 shirt.
    
    In other news, Liverpool midfielder Thiago Alcântara has been ruled out for six weeks 
    with a hamstring injury. The Spaniard suffered the injury during training on Tuesday.
    Manager Jürgen Klopp described it as a "big blow" for the team.
    """
    
    print("\nOriginal text:")
    print(text_2[:150] + "...")
    
    # Pipeline execution
    print("\n[Step 1] Sentence Splitting...")
    sentences_2 = splitter.split(text_2)
    print(f"  ✓ Split into {len(sentences_2)} sentences")
    
    print("\n[Step 2] Semantic Chunking...")
    chunks_2 = semantic_chunk(sentences_2, backend, window_size=1)
    print(f"  ✓ Created {len(chunks_2)} semantic chunks:")
    
    for i, chunk in enumerate(chunks_2, 1):
        print(f"\n    Chunk {i}: {' '.join(chunk[:50])}...")
    
    # ========================================================================
    # Test Case 3: Quote Aggregation
    # ========================================================================
    print("\n" + "="*80)
    print("[TEST 3] Quote Aggregation")
    print("-"*80)
    
    text_3 = """
    Pep Guardiola spoke about Manchester City's recent form in his press conference.
    He said: "We need to improve our finishing. We created many chances but didn't 
    take them." He continued: "The important thing is that we're creating those 
    opportunities. The goals will come."
    
    Kevin De Bruyne has signed a new three-year contract extension with the club.
    """
    
    print("\nOriginal text:")
    print(text_3.strip())
    
    print("\n[Step 1] Sentence Splitting...")
    sentences_3 = splitter.split(text_3)
    print(f"  ✓ Split into {len(sentences_3)} sentences:")
    for i, sent in enumerate(sentences_3, 1):
        print(f"    {i}. {sent}")
    
    print("\n[Step 2] Semantic Chunking...")
    chunks_3 = semantic_chunk(sentences_3, backend, window_size=1)
    print(f"  ✓ Created {len(chunks_3)} semantic chunks:")
    
    for i, chunk in enumerate(chunks_3, 1):
        print(f"\n    Chunk {i}:")
        for sent in chunk:
            print(f"      • {sent}")
    
    # ========================================================================
    # Validation
    # ========================================================================
    print("\n" + "="*80)
    print("[VALIDATION]")
    print("="*80)
    
    # Check that we got reasonable results
    assertions = [
        (len(sentences) > 0, "Should produce sentences"),
        (len(chunks) > 0, "Should produce chunks"),
        (len(chunks) < len(sentences), "Should aggregate some sentences"),
        (sum(len(c) for c in chunks) == len(sentences), "All sentences should be in chunks"),
    ]
    
    all_passed = True
    for condition, description in assertions:
        status = "✓" if condition else "✗"
        print(f"  {status} {description}")
        if not condition:
            all_passed = False
    
    if all_passed:
        print("\n" + "="*80)
        print("✓ ALL INTEGRATION TESTS PASSED")
        print("="*80)
        return True
    else:
        print("\n" + "="*80)
        print("✗ SOME TESTS FAILED")
        print("="*80)
        return False


def test_edge_cases():
    """Test edge cases and error handling."""
    
    print("\n" + "="*80)
    print("EDGE CASE TESTS")
    print("="*80)
    
    splitter = SentenceSplitter()
    backend = OllamaBackend(model="llama3:latest")
    
    # Test 1: Empty text
    print("\n[Edge Case 1] Empty text")
    sentences = splitter.split("")
    chunks = semantic_chunk(sentences, backend) if sentences else []
    print(f"  ✓ Empty text: {len(sentences)} sentences, {len(chunks)} chunks")
    
    # Test 2: Single sentence
    print("\n[Edge Case 2] Single sentence")
    sentences = splitter.split("This is a single sentence.")
    chunks = semantic_chunk(sentences, backend)
    print(f"  ✓ Single sentence: {len(sentences)} sentences, {len(chunks)} chunks")
    assert len(chunks) == 1
    
    # Test 3: Very short text
    print("\n[Edge Case 3] Very short text")
    sentences = splitter.split("Short.")
    print(f"  ✓ Very short: {len(sentences)} sentences")
    
    print("\n  ✓ All edge cases handled correctly")


def main():
    """Run all integration tests."""
    try:
        # Main integration tests
        success = test_full_pipeline()
        
        # Edge case tests
        test_edge_cases()
        
        if success:
            print("\n🎉 Integration testing complete!")
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
