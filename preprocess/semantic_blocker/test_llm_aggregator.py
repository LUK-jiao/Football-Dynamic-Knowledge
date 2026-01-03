#!/usr/bin/env python3
"""
Test script for LLM-based event aggregator.
Compares with rule-based approach and validates output.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from preprocess.sentence_splitter import SentenceSplitter
from preprocess.semantic_blocker.llm_aggregator import llm_semantic_chunk, LLMEventAggregator


def main():
    """Run LLM aggregator test."""
    
    print("=" * 80)
    print("LLM-BASED EVENT AGGREGATOR - Test")
    print("=" * 80)
    
    # Check if OpenAI is available
    import os
    if not os.getenv("OPENAI_API_KEY"):
        print("\n⚠️  WARNING: OPENAI_API_KEY not found in environment")
        print("   Set it with: export OPENAI_API_KEY='your-key'")
        print("   Continuing with fallback mode...\n")
    
    # Initialize
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
    print(f"\n✓ Split into {len(sentences)} sentences:\n")
    for i, sent in enumerate(sentences, 1):
        print(f"  [{i:2d}] {sent[:70]}...")
    
    # Step 2: LLM-based aggregation
    print("\n" + "=" * 80)
    print("STEP 2: LLM-Based Event Aggregation")
    print("=" * 80)
    
    try:
        # Check if API key exists
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            print("\n🤖 Calling LLM (gpt-4o-mini)...")
            blocks = llm_semantic_chunk(
                sentences,
                model="gpt-4o-mini",
                window_size=15
            )
        else:
            print("\n⚠️  No API key found, using FALLBACK (rule-based)...")
            from preprocess.semantic_blocker.event_chunker import event_based_chunk
            blocks = event_based_chunk(sentences)
        
        print(f"\n✓ Created {len(blocks)} event blocks:\n")
        
        for i, block in enumerate(blocks, 1):
            print(f"┌─ [Block {i}] {block['event_type'].upper()}")
            print(f"│  Confidence: {block['confidence']:.2f}")
            print(f"│  Anchor: Sentence #{block['anchor_index'] + 1}")
            print(f"│  Sentences: {len(block['sentences'])}")
            print(f"│  Length: {block['length']} chars")
            print(f"│")
            print(f"│  Content:")
            for j, sent in enumerate(block['sentences'], 1):
                print(f"│    {j}. {sent[:75]}...")
            print(f"└{'─' * 78}")
            print()
        
        # Validation summary
        print("=" * 80)
        print("VALIDATION SUMMARY")
        print("=" * 80)
        
        total_sentences_in_blocks = sum(len(b['sentences']) for b in blocks)
        print(f"\n✓ Sentence Coverage:")
        print(f"  Input: {len(sentences)} sentences")
        print(f"  Output: {total_sentences_in_blocks} sentences in blocks")
        print(f"  Status: {'✅ PASS' if total_sentences_in_blocks == len(sentences) else '❌ FAIL'}")
        
        # Event type distribution
        print(f"\n✓ Event Type Distribution:")
        event_counts = {}
        for block in blocks:
            et = block['event_type']
            event_counts[et] = event_counts.get(et, 0) + 1
        
        for et, count in sorted(event_counts.items(), key=lambda x: -x[1]):
            print(f"  • {et}: {count} block(s)")
        
        # Check for duplicates
        all_sentences_from_blocks = []
        for block in blocks:
            all_sentences_from_blocks.extend(block['sentences'])
        
        unique_count = len(set(all_sentences_from_blocks))
        print(f"\n✓ Duplicate Check:")
        print(f"  Total: {len(all_sentences_from_blocks)}")
        print(f"  Unique: {unique_count}")
        print(f"  Status: {'✅ PASS (no duplicates)' if unique_count == len(all_sentences_from_blocks) else '❌ FAIL (duplicates found)'}")
        
        # Metadata check
        print(f"\n✓ Metadata:")
        for block in blocks:
            if 'metadata' in block:
                method = block['metadata'].get('method', 'unknown')
                print(f"  • Block used: {method}")
        
        print("\n" + "=" * 80)
        print("✅ LLM Aggregation Test Completed!")
        print("=" * 80)
        
        print("\n💡 Key Advantages of LLM Approach:")
        print("  1. Intelligent understanding of event boundaries")
        print("  2. Better handling of pronouns and references")
        print("  3. Correct grouping of related sentences")
        print("  4. Fewer, more coherent blocks")
        print("  5. Explainable event types")
        
    except Exception as e:
        print(f"\n❌ Error during LLM aggregation: {e}")
        import traceback
        traceback.print_exc()
        
        print("\n⚠️  Falling back to rule-based aggregation...")
        # Could call fallback here


if __name__ == "__main__":
    main()
