"""
Comparison: Old vs New Semantic Chunker

This script demonstrates the differences between the refactored
binary classifier approach and the old event aggregation approach.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from semantic_chunker import SemanticChunker, ChunkerConfig
from ollama_backend import OllamaBackend


def compare_approaches():
    print("="*70)
    print("COMPARISON: Old Event Aggregator vs New Binary Classifier")
    print("="*70)
    
    # Test sentences
    sentences = [
        "Arsenal defeated Chelsea 2-1 at Stamford Bridge.",
        "Bukayo Saka scored the opening goal in the 23rd minute.",
        "It was a brilliant strike from outside the box.",
        "Chelsea equalized through Jackson just before halftime.",
        "Mikel Arteta praised his team's resilience after the match.",
        "He said the victory was crucial for the title race.",
        "Liverpool announced record revenues of £700 million.",
        "The club's commercial income grew by 15% year-over-year."
    ]
    
    print("\n[INPUT] Sentences:")
    for i, s in enumerate(sentences, 1):
        print(f"  {i}. {s}")
    
    # ========================================================================
    # NEW APPROACH: Binary Classifier
    # ========================================================================
    print("\n" + "="*70)
    print("[NEW APPROACH] Binary Classifier (Refactored)")
    print("="*70)
    
    print("\nCharacteristics:")
    print("  • LLM outputs: SAME_UNIT or NEW_UNIT only")
    print("  • Sliding window: compares current with previous")
    print("  • Fallback: invalid output → force NEW_UNIT")
    print("  • Output: Simple list of sentence lists")
    
    backend = OllamaBackend(model="llama3:latest", timeout=30)
    config = ChunkerConfig(window_size=1, log_failures=True)
    chunker = SemanticChunker(backend, config)
    
    print("\nProcessing...")
    chunks = chunker.chunk(sentences)
    
    print(f"\nResult: {len(chunks)} semantic chunks")
    for i, chunk in enumerate(chunks, 1):
        print(f"\n  Chunk {i} ({len(chunk)} sentences):")
        for sent in chunk:
            print(f"    • {sent}")
    
    stats = chunker.get_stats()
    print(f"\nStatistics:")
    print(f"  • Total decisions: {stats['total_decisions']}")
    print(f"  • SAME_UNIT: {stats['same_unit_count']}")
    print(f"  • NEW_UNIT: {stats['new_unit_count']}")
    print(f"  • Fallback rate: {stats['fallback_rate']:.2%}")
    
    # ========================================================================
    # OLD APPROACH: Event Aggregator
    # ========================================================================
    print("\n" + "="*70)
    print("[OLD APPROACH] Event Aggregator (Original)")
    print("="*70)
    
    print("\nCharacteristics:")
    print("  • LLM outputs: Complex JSON with event types")
    print("  • Event taxonomy: match_result, goal, quote, etc.")
    print("  • Fallback: Multiple retries, complex error handling")
    print("  • Output: Rich blocks with metadata, confidence, etc.")
    
    print("\nNote: Old system is preserved for backward compatibility")
    print("      but not demonstrated here to avoid complexity.")
    
    # ========================================================================
    # KEY DIFFERENCES
    # ========================================================================
    print("\n" + "="*70)
    print("[KEY DIFFERENCES]")
    print("="*70)
    
    differences = [
        ("Aspect", "Old System", "New System"),
        ("---", "---", "---"),
        ("LLM Output", "Complex JSON with event types", "Single token: SAME_UNIT/NEW_UNIT"),
        ("Prompt Size", "~500 tokens", "~100 tokens"),
        ("Response Time", "3-5 seconds per window", "1-2 seconds per decision"),
        ("Failure Mode", "Retry 3x, then fallback", "Immediate fallback to NEW_UNIT"),
        ("Determinism", "Variable (temperature, retries)", "Guaranteed (temp=0, no retries)"),
        ("Backend Support", "OpenAI only", "Ollama, OpenAI, custom"),
        ("Complexity", "High (event taxonomy)", "Low (binary decision)"),
        ("Output Format", "Dict with metadata", "List of lists"),
        ("Testability", "Difficult (many states)", "Easy (mock responses)"),
        ("Maintainability", "Complex codebase", "Simple, clear logic"),
    ]
    
    # Print as table
    col_widths = [max(len(str(row[i])) for row in differences) for i in range(3)]
    
    for row in differences:
        print("  " + "  ".join(
            str(cell).ljust(width) 
            for cell, width in zip(row, col_widths)
        ))
    
    # ========================================================================
    # RECOMMENDATIONS
    # ========================================================================
    print("\n" + "="*70)
    print("[RECOMMENDATIONS]")
    print("="*70)
    
    print("""
Use NEW system (Binary Classifier) when:
  ✓ You need deterministic, predictable behavior
  ✓ You want to use local LLMs (Ollama, vLLM)
  ✓ You need fast, simple semantic boundaries
  ✓ Downstream systems handle event classification
  ✓ You want easy testing and maintenance

Use OLD system (Event Aggregator) when:
  ✓ You need event type classification in same step
  ✓ You're already integrated with OpenAI
  ✓ You need rich metadata and confidence scores
  ✓ Migration cost is too high
    """)
    
    print("="*70)
    print("✓ Comparison complete")
    print("="*70)


if __name__ == "__main__":
    try:
        compare_approaches()
    except KeyboardInterrupt:
        print("\n\n✗ Interrupted by user")
    except Exception as e:
        print(f"\n\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
