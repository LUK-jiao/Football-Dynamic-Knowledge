#!/usr/bin/env python3
"""
Integration example: sentence_splitter + semantic_blocker
Demonstrates the complete pipeline from raw text to semantic blocks.
"""

import sys
import os

# Add parent directory to path，os.path.dirname就是得到根目录
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
    Mikel Arteta's Arsenal side marched on to the EFL Cup semi-finals but did it the hard way by winning 8-7 on penalties against Crystal Palace, with Kepa Arrizabalaga saving the 16th spot-kick taken by Maxence Lacroix after 15 successful conversions.
Two late goals had resulted in a 1-1 draw after 90 minutes and a lengthy period of stoppage time.
The Gunners will now face rivals Chelsea to fight for a place in the final at Wembley, with the first leg of their semi-final set for Stamford Bridge on 14 January.
After bossing much of the quarter-final against Palace and creating the majority of big chances, Arteta's men finally found their breakthrough, which came from a corner in the 80th minute. A well-placed delivery into the box from Bukayo Saka found the head of Riccardo Calafiori and eventually went into the net off Palace centre-back Lacroix.
The unfortunate own goal did not dampen Palace's spirits as they went in search of an equaliser. When it finally did arrive, they had club captain Marc Guehi to thank. The England international was the first to react to a knock-on from Jefferson Lerma in the fifth minute of stoppage time.
A fascinating penalty shoot-out then ensued, with both sides delivering spectacular finishes to take the score to 8-7. When the own-goal scorer Lacroix stepped up to take his kick, Arsenal keeper Kepa read its direction and made the save to ensure the Gunners remain on course for their first Wembley appearance in five years.
This was Arsenal's second-highest scoring penalty shootout, after their 9-8 victory against Rotherham in 2003/04. Overall, the Gunners have converted 47 of their last 51 spot-kicks in shoot-outs, giving them a supreme 92 per cent conversion rate.
Arteta told Sky Sports after the game: "I'm very happy to be in the semi-finals. We played against a team who are hard to generate chances against. We generated a lot and we should have scored many more goals."
The Arsenal boss had made eight changes to his starting line-up and admitted: "It's always tough because they don't have the right chemistry when they haven't played together. But their attitude is excellent.
"I think we had some big individual performances tonight. It's great for Gabriel Jesus tonight, after almost a year out, to start a game and make his 100th [Arsenal] appearance. The commitment within the group is incredible and I'm very happy for the boys."
Arteta: 'The penalties were unbelievable' against Palace.
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
    
    # # Step 3: Analysis
    # print("\n" + "=" * 80)
    # print("ANALYSIS")
    # print("=" * 80)
    
    # print(f"\n📊 Statistics:")
    # print(f"  • Original text: {len(raw_text)} characters")
    # print(f"  • Sentences: {len(sentences)}")
    # print(f"  • Semantic blocks: {len(blocks)}")
    # print(f"  • Avg sentences per block: {len(sentences) / len(blocks):.1f}")
    # print(f"  • Avg block length: {sum(len(b) for b in blocks) / len(blocks):.0f} chars")
    
    # print(f"\n🎯 Block Topics (inferred):")
    # topics = [
    #     "1. Match outcome and context",
    #     "2. Haaland's first-half goals",
    #     "3. Real Madrid's comeback - Vinicius",
    #     "4. Real Madrid's comeback - Benzema penalty",
    #     "5. City's tactical changes",
    #     "6. Foden's decisive goals",
    #     "7. Late consolation and preview"
    # ]
    # for topic in topics[:len(blocks)]:
    #     print(f"  {topic}")
    
    # print("\n" + "=" * 80)
    # print("✓ Pipeline completed successfully!")
    # print("=" * 80)
    
    # # ========================================================================
    # # Use Case: Event Extraction Ready
    # # ========================================================================
    # print("\n[Use Case] Ready for Event Extraction")
    # print("-" * 80)
    
    # print("\nEach semantic block is now ready for downstream processing:")
    # print("  • Fact extraction")
    # print("  • Named entity recognition")
    # print("  • Relation extraction")
    # print("  • Knowledge graph construction")
    
    # print(f"\nExample - Processing Block 1:")
    # print(f"  Input: {blocks[0][:100]}...")
    # print(f"  Potential extractions:")
    # print(f"    - Event: 'Match victory'")
    # print(f"    - Winner: 'Manchester City'")
    # print(f"    - Loser: 'Real Madrid'")
    # print(f"    - Score: '4-3'")
    # print(f"    - Competition: 'Champions League quarter-final'")
    # print(f"    - Venue: 'Etihad Stadium'")
    # print(f"    - Date: 'Tuesday night'")


if __name__ == "__main__":
    main()
