#!/usr/bin/env python3
"""
Simple example of using LLM-based semantic blocker.
"""

import os
from preprocess.sentence_splitter import SentenceSplitter
from preprocess.semantic_blocker import llm_semantic_chunk

def main():
    # Sample football news
    text = """
    Arsenal beat Chelsea 2-1 in a thrilling match at Emirates Stadium.
    Bukayo Saka opened the scoring in the 23rd minute with a brilliant strike.
    Chelsea equalized through Cole Palmer in the 67th minute.
    But Gabriel Jesus secured the win with a header in the 89th minute.
    Manager Mikel Arteta said: "I'm very proud of the team's performance today."
    He added: "The resilience we showed was incredible."
    """
    
    print("=" * 80)
    print("LLM-Based Semantic Blocker - Example")
    print("=" * 80)
    
    # Step 1: Split into sentences
    print("\n[1] Splitting text into sentences...")
    splitter = SentenceSplitter()
    sentences = splitter.split(text)
    print(f"    ✓ Got {len(sentences)} sentences\n")
    
    # Step 2: Check API key
    if not os.getenv("OPENAI_API_KEY") and not os.getenv("DEEPSEEK_API_KEY"):
        print("⚠️  No API key found!")
        print("    Set OPENAI_API_KEY or DEEPSEEK_API_KEY to use LLM aggregation")
        print("    Example: export OPENAI_API_KEY='sk-...'")
        return
    
    # Step 3: Aggregate into semantic blocks
    print("[2] Aggregating into semantic blocks using LLM...")
    blocks = llm_semantic_chunk(
        sentences,
        model="gpt-4o-mini",
        window_size=15
    )
    
    print(f"    ✓ Created {len(blocks)} semantic blocks\n")
    
    # Step 4: Display results
    print("=" * 80)
    print("Results")
    print("=" * 80)
    
    for i, block in enumerate(blocks, 1):
        print(f"\n[Block {i}] {block['event_type'].upper()}")
        print(f"  Confidence: {block['confidence']:.2f}")
        print(f"  Sentences: {len(block['sentences'])}")
        print(f"  Content:")
        for sent in block['sentences']:
            print(f"    • {sent}")
    
    print("\n" + "=" * 80)
    print("✅ Done!")
    print("=" * 80)

if __name__ == "__main__":
    main()
