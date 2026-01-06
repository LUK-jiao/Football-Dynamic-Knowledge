"""
Example: Semantic Chunker with Ollama

This example demonstrates the refactored semantic chunker:
- Sliding window boundary detection
- LLM as binary classifier (SAME_UNIT vs NEW_UNIT)
- Robust fallback on LLM failures
- Statistics tracking
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import logging
from semantic_chunker import SemanticChunker, ChunkerConfig
from ollama_backend import OllamaBackend

# Configure logging to see fallback events
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)


def main():
    print("="*70)
    print("SEMANTIC CHUNKER - OLLAMA EXAMPLE")
    print("="*70)
    
    # Initialize Ollama backend
    print("\n[1] Initializing Ollama backend...")
    backend = OllamaBackend(
        model="llama3:latest",
        timeout=30,
        temperature=0.0  # Deterministic
    )
    
    # Test connection
    if not backend.test_connection():
        print("✗ Cannot connect to Ollama server")
        print("  Please start Ollama: ollama serve")
        return
    
    # Configure chunker
    config = ChunkerConfig(
        window_size=1,  # Compare with previous 1 sentence
        force_new_on_failure=True,  # Conservative fallback
        log_failures=True  # Log all fallback events
    )
    
    chunker = SemanticChunker(backend, config)
    
    # Example 1: Football match report
    print("\n[2] Example 1: Match Report")
    print("-" * 70)
    
    sentences_1 = [
        "Arsenal defeated Chelsea 2-1 at Stamford Bridge.",
        "Bukayo Saka scored the opening goal in the 23rd minute.",
        "It was a brilliant strike from outside the box.",
        "Chelsea equalized through Jackson just before halftime.",
        "Mikel Arteta praised his team's resilience after the match.",
        "He said the victory was crucial for the title race."
    ]
    
    print("\nInput sentences:")
    for i, sent in enumerate(sentences_1, 1):
        print(f"  {i}. {sent}")
    
    print("\nProcessing...")
    chunks_1 = chunker.chunk(sentences_1)
    
    print(f"\nOutput: {len(chunks_1)} semantic chunk(s)")
    for i, chunk in enumerate(chunks_1, 1):
        print(f"\n  Chunk {i}:")
        for sent in chunk:
            print(f"    • {sent}")
    
    # Example 2: Mixed topics (should create separate chunks)
    print("\n[3] Example 2: Mixed Topics")
    print("-" * 70)
    
    sentences_2 = [
        "Liverpool announced a record revenue for the fiscal year.",
        "The club earned over £700 million in total income.",
        "Manchester United signed a new striker from Italy.",
        "The transfer fee was reported to be €80 million.",
        "Arsenal's women's team won their match 3-0.",
        "Miedema scored twice in the victory."
    ]
    
    print("\nInput sentences:")
    for i, sent in enumerate(sentences_2, 1):
        print(f"  {i}. {sent}")
    
    print("\nProcessing...")
    chunks_2 = chunker.chunk(sentences_2)
    
    print(f"\nOutput: {len(chunks_2)} semantic chunk(s)")
    for i, chunk in enumerate(chunks_2, 1):
        print(f"\n  Chunk {i}:")
        for sent in chunk:
            print(f"    • {sent}")
    
    # Example 3: Coreference resolution
    print("\n[4] Example 3: Coreference & Ellipsis")
    print("-" * 70)
    
    sentences_3 = [
        "Mohamed Salah scored a hat-trick against Manchester United.",
        "He completed it in just 32 minutes.",
        "The Egyptian forward now has 15 goals this season.",
        "Klopp was asked about rotation in the post-match interview.",
        "He refused to confirm his starting lineup for the next game."
    ]
    
    print("\nInput sentences:")
    for i, sent in enumerate(sentences_3, 1):
        print(f"  {i}. {sent}")
    
    print("\nProcessing...")
    chunks_3 = chunker.chunk(sentences_3)
    
    print(f"\nOutput: {len(chunks_3)} semantic chunk(s)")
    for i, chunk in enumerate(chunks_3, 1):
        print(f"\n  Chunk {i}:")
        for sent in chunk:
            print(f"    • {sent}")
    
    # Show statistics
    print("\n[5] Chunking Statistics")
    print("-" * 70)
    stats = chunker.get_stats()
    
    print(f"\nTotal decisions made: {stats['total_decisions']}")
    print(f"  • SAME_UNIT: {stats['same_unit_count']}")
    print(f"  • NEW_UNIT: {stats['new_unit_count']}")
    print(f"\nFallback events: {stats['fallback_count']}")
    print(f"  • Fallback rate: {stats['fallback_rate']:.2%}")
    
    if stats['fallback_reasons']:
        print(f"\nFallback reasons breakdown:")
        for reason, count in stats['fallback_reasons'].items():
            print(f"  • {reason}: {count}")
    
    print("\n" + "="*70)
    print("✓ Example completed successfully")
    print("="*70)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n✗ Interrupted by user")
    except Exception as e:
        print(f"\n\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
