#!/usr/bin/env python3
"""
Integration example: sentence_splitter + semantic_blocker
Demonstrates the complete pipeline from raw text to semantic blocks.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from preprocess.sentence_splitter import SentenceSplitter
from preprocess.semantic_blocker import semantic_block


def main():
    """Run integration example."""
    
    print("=" * 80)
    print("INTEGRATION: sentence_splitter + semantic_blocker")
    print("=" * 80)
    
    # Initialize splitter
    splitter = SentenceSplitter()
    
    # ========================================================================
    # Real-world Example: Complex Match Report
    # ========================================================================
    print("\n[Real-world Example] Match Report Processing")
    print("-" * 80)
    
    raw_text = """
    Manchester City secured a thrilling 4-3 victory over Real Madrid in the 
    Champions League quarter-final first leg at the Etihad Stadium on Tuesday night. 
    Erling Haaland opened the scoring in the 22nd minute with a powerful header from 
    a Kevin De Bruyne cross. The Norwegian striker added a second just before halftime, 
    bringing his season tally to 45 goals in all competitions. However, Real Madrid 
    fought back in the second half. Vinicius Junior pulled one back in the 58th minute 
    with a brilliant solo effort, beating three defenders before slotting past Ederson. 
    Karim Benzema then equalized in the 67th minute from the penalty spot after being 
    fouled by Kyle Walker. Meanwhile, City manager Pep Guardiola made tactical changes, 
    bringing on Phil Foden and Julian Alvarez to regain control. The substitutions paid 
    off as Foden scored twice in quick succession in the 78th and 82nd minutes. Real 
    Madrid grabbed a late consolation through Rodrygo in stoppage time, setting up an 
    exciting second leg at the Santiago Bernabeu next week.
    """
    
    print("\n📄 RAW TEXT:")
    print(raw_text.strip())
    
    # Step 1: Sentence splitting
    print("\n" + "=" * 80)
    print("STEP 1: Sentence Splitting")
    print("=" * 80)
    
    sentences = splitter.split(raw_text)
    print(f"\n✓ Split into {len(sentences)} sentences:\n")
    for i, sent in enumerate(sentences, 1):
        print(f"{i:2d}. {sent}")
    
    # Step 2: Semantic blocking
    print("\n" + "=" * 80)
    print("STEP 2: Semantic Blocking")
    print("=" * 80)
    
    blocks = semantic_block(sentences, similarity_threshold=0.5, max_block_length=350)
    print(f"\n✓ Grouped into {len(blocks)} semantic blocks:\n")
    for i, block in enumerate(blocks, 1):
        print(f"\n[Block {i}]")
        print(f"{block}")
        print(f"({len(block)} chars)")
    
    # Step 3: Analysis
    print("\n" + "=" * 80)
    print("ANALYSIS")
    print("=" * 80)
    
    print(f"\n📊 Statistics:")
    print(f"  • Original text: {len(raw_text)} characters")
    print(f"  • Sentences: {len(sentences)}")
    print(f"  • Semantic blocks: {len(blocks)}")
    print(f"  • Avg sentences per block: {len(sentences) / len(blocks):.1f}")
    print(f"  • Avg block length: {sum(len(b) for b in blocks) / len(blocks):.0f} chars")
    
    print(f"\n🎯 Block Topics (inferred):")
    topics = [
        "1. Match outcome and context",
        "2. Haaland's first-half goals",
        "3. Real Madrid's comeback - Vinicius",
        "4. Real Madrid's comeback - Benzema penalty",
        "5. City's tactical changes",
        "6. Foden's decisive goals",
        "7. Late consolation and preview"
    ]
    for topic in topics[:len(blocks)]:
        print(f"  {topic}")
    
    print("\n" + "=" * 80)
    print("✓ Pipeline completed successfully!")
    print("=" * 80)
    
    # ========================================================================
    # Use Case: Event Extraction Ready
    # ========================================================================
    print("\n[Use Case] Ready for Event Extraction")
    print("-" * 80)
    
    print("\nEach semantic block is now ready for downstream processing:")
    print("  • Fact extraction")
    print("  • Named entity recognition")
    print("  • Relation extraction")
    print("  • Knowledge graph construction")
    
    print(f"\nExample - Processing Block 1:")
    print(f"  Input: {blocks[0][:100]}...")
    print(f"  Potential extractions:")
    print(f"    - Event: 'Match victory'")
    print(f"    - Winner: 'Manchester City'")
    print(f"    - Loser: 'Real Madrid'")
    print(f"    - Score: '4-3'")
    print(f"    - Competition: 'Champions League quarter-final'")
    print(f"    - Venue: 'Etihad Stadium'")
    print(f"    - Date: 'Tuesday night'")


if __name__ == "__main__":
    main()
