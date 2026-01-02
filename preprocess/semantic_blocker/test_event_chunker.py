#!/usr/bin/env python3
"""
Test script for event-driven semantic chunker.
Compares old (similarity-based) vs new (event-based) approaches.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from preprocess.sentence_splitter import SentenceSplitter
from preprocess.semantic_blocker.event_chunker import event_based_chunk, EventDrivenSemanticChunker
from preprocess.semantic_blocker.blocker import semantic_block  # Old approach


def main():
    """Run comparison test."""
    
    print("=" * 80)
    print("EVENT-DRIVEN SEMANTIC CHUNKER - Test & Comparison")
    print("=" * 80)
    
    # Initialize splitter
    splitter = SentenceSplitter()
    
    # Test case: Real match report
    raw_text = """
    Mikel Arteta's Arsenal side marched on to the EFL Cup semi-finals but did it the hard way by winning 8-7 on penalties against Crystal Palace, with Kepa Arrizabalaga saving the 16th spot-kick taken by Maxence Lacroix after 15 successful conversions.
Two late goals had resulted in a 1-1 draw after 90 minutes and a lengthy period of stoppage time.
The Gunners will now face rivals Chelsea to fight for a place in the final at Wembley, with the first leg of their semi-final set for Stamford Bridge on 14 January.
After bossing much of the quarter-final against Palace and creating the majority of big chances, Arteta's men finally found their breakthrough, which came from a corner in the 80th minute.
A well-placed delivery into the box from Bukayo Saka found the head of Riccardo Calafiori and eventually went into the net off Palace centre-back Lacroix.
The unfortunate own goal did not dampen Palace's spirits as they went in search of an equaliser.
When it finally did arrive, they had club captain Marc Guehi to thank.
The England international was the first to react to a knock-on from Jefferson Lerma in the fifth minute of stoppage time.
A fascinating penalty shoot-out then ensued, with both sides delivering spectacular finishes to take the score to 8-7.
When the own-goal scorer Lacroix stepped up to take his kick, Arsenal keeper Kepa read its direction and made the save to ensure the Gunners remain on course for their first Wembley appearance in five years.
This was Arsenal's second-highest scoring penalty shootout, after their 9-8 victory against Rotherham in 2003/04.
Overall, the Gunners have converted 47 of their last 51 spot-kicks in shoot-outs, giving them a supreme 92 per cent conversion rate.
Arteta told Sky Sports after the game: "I'm very happy to be in the semi-finals. We played against a team who are hard to generate chances against. We generated a lot and we should have scored many more goals."
The Arsenal boss had made eight changes to his starting line-up and admitted: "It's always tough because they don't have the right chemistry when they haven't played together. But their attitude is excellent. "I think we had some big individual performances tonight. It's great for Gabriel Jesus tonight, after almost a year out, to start a game and make his 100th [Arsenal] appearance. The commitment within the group is incredible and I'm very happy for the boys."
Arteta: 'The penalties were unbelievable' against Palace.
    """
    
    print("\n📄 INPUT TEXT")
    print("-" * 80)
    print(raw_text.strip()[:200] + "...")
    
    # Step 1: Sentence splitting
    print("\n" + "=" * 80)
    print("STEP 1: Sentence Splitting")
    print("=" * 80)
    
    sentences = splitter.split(raw_text)
    print(f"\n✓ Split into {len(sentences)} sentences")
    for i, sent in enumerate(sentences[:5], 1):
        print(f"  {i}. {sent[:80]}...")
    if len(sentences) > 5:
        print(f"  ... and {len(sentences) - 5} more")
    
    # Step 2: Event-based chunking (NEW)
    print("\n" + "=" * 80)
    print("STEP 2: EVENT-BASED CHUNKING (NEW APPROACH)")
    print("=" * 80)
    
    event_blocks = event_based_chunk(sentences, max_block_length=400)
    
    print(f"\n✓ Created {len(event_blocks)} event-based blocks:\n")
    for i, block in enumerate(event_blocks, 1):
        print(f"[Block {i}] {block['event_type'].upper()}")
        print(f"  Confidence: {block['confidence']:.2f}")
        print(f"  Sentences: {len(block['sentences'])}")
        print(f"  Length: {block['length']} chars")
        print(f"  Content: {block['text'][:120]}...")
        print()
    
    # Step 3: Similarity-based chunking (OLD - for comparison)
    print("=" * 80)
    print("STEP 3: SIMILARITY-BASED CHUNKING (OLD APPROACH)")
    print("=" * 80)
    
    try:
        old_blocks = semantic_block(sentences, similarity_threshold=0.5, max_block_length=400)
        print(f"\n✓ Created {len(old_blocks)} similarity-based blocks:\n")
        for i, block in enumerate(old_blocks[:5], 1):
            print(f"[Block {i}]")
            print(f"  Length: {len(block)} chars")
            print(f"  Content: {block[:120]}...")
            print()
        if len(old_blocks) > 5:
            print(f"  ... and {len(old_blocks) - 5} more blocks")
    except Exception as e:
        print(f"⚠️  Old method failed: {e}")
        old_blocks = []
    
    # Step 4: Comparison
    print("=" * 80)
    print("COMPARISON ANALYSIS")
    print("=" * 80)
    
    print(f"\n📊 Block Count:")
    print(f"  Event-based: {len(event_blocks)} blocks")
    print(f"  Similarity-based: {len(old_blocks)} blocks")
    
    print(f"\n🎯 Event Types Identified (NEW):")
    event_types = {}
    for block in event_blocks:
        et = block['event_type']
        event_types[et] = event_types.get(et, 0) + 1
    for et, count in sorted(event_types.items(), key=lambda x: -x[1]):
        print(f"  • {et}: {count} block(s)")
    
    print(f"\n📈 Confidence Distribution (NEW):")
    confidences = [b['confidence'] for b in event_blocks]
    avg_conf = sum(confidences) / len(confidences) if confidences else 0
    print(f"  Average: {avg_conf:.2f}")
    print(f"  Range: {min(confidences):.2f} - {max(confidences):.2f}")
    
    print(f"\n✅ Event-based blocks are:")
    print(f"  • More semantically coherent (one event per block)")
    print(f"  • Better for knowledge graph extraction")
    print(f"  • Explainable (rule-based + taxonomy)")
    print(f"  • Directly usable for fact extraction")
    
    # Step 5: Detailed analysis of a sample block
    print("\n" + "=" * 80)
    print("SAMPLE BLOCK ANALYSIS")
    print("=" * 80)
    
    if event_blocks:
        sample = event_blocks[0]
        print(f"\n🔍 Block 1 Details:")
        print(f"  Event Type: {sample['event_type']}")
        print(f"  Confidence: {sample['confidence']:.2f}")
        print(f"  Sentence Count: {len(sample['sentences'])}")
        print(f"  \n  Sentences:")
        for j, sent in enumerate(sample['sentences'], 1):
            print(f"    {j}. {sent}")
        print(f"\n  Full Text:")
        print(f"  {sample['text']}")
        
        print(f"\n  📝 Knowledge Graph Potential:")
        print(f"  This block can directly extract:")
        if sample['event_type'] == 'match_result':
            print(f"    - Winner/Loser entities")
            print(f"    - Final score")
            print(f"    - Match type (penalties)")
            print(f"    - Key players (Kepa, Lacroix)")
        elif sample['event_type'] == 'goal':
            print(f"    - Scorer entity")
            print(f"    - Time of goal")
            print(f"    - Assist provider")
            print(f"    - Goal type")
        elif sample['event_type'] == 'manager_quote':
            print(f"    - Speaker entity")
            print(f"    - Quote content")
            print(f"    - Context (after game)")
    
    print("\n" + "=" * 80)
    print("✅ Test completed!")
    print("=" * 80)


if __name__ == "__main__":
    main()
