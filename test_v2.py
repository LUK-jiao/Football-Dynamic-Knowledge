"""
Test Semantic Chunker v2 on Arsenal Match Report
"""

import sys
sys.path.insert(0, 'preprocess')

from semantic_blocker.semantic_chunker_v2 import SemanticChunker, ChunkerConfig, GranularityMode
from semantic_blocker.ollama_backend_v2 import OllamaBackendV2
from sentence_splitter import SentenceSplitter

# Test text
text = """Mikel Arteta's Arsenal side marched on to the EFL Cup semi-finals but did it the hard way by winning 8-7 on penalties against Crystal Palace, with Kepa Arrizabalaga saving the 16th spot-kick taken by Maxence Lacroix after 15 successful conversions. Two late goals had resulted in a 1-1 draw after 90 minutes and a lengthy period of stoppage time. The Gunners will now face rivals Chelsea to fight for a place in the final at Wembley, with the first leg of their semi-final set for Stamford Bridge on 14 January.

After bossing much of the quarter-final against Palace and creating the majority of big chances, Arteta's men finally found their breakthrough, which came from a corner in the 80th minute. A well-placed delivery into the box from Bukayo Saka found the head of Riccardo Calafiori and eventually went into the net off Palace centre-back Lacroix. The unfortunate own goal did not dampen Palace's spirits as they went in search of an equaliser. When it finally did arrive, they had club captain Marc Guehi to thank. The England international was the first to react to a knock-on from Jefferson Lerma in the fifth minute of stoppage time.

A fascinating penalty shoot-out then ensued, with both sides delivering spectacular finishes to take the score to 8-7. When the own-goal scorer Lacroix stepped up to take his kick, Arsenal keeper Kepa read its direction and made the save to ensure the Gunners remain on course for their first Wembley appearance in five years.

This was Arsenal's second-highest scoring penalty shootout, after their 9-8 victory against Rotherham in 2003/04. Overall, the Gunners have converted 47 of their last 51 spot-kicks in shoot-outs, giving them a supreme 92 per cent conversion rate.

Arteta told Sky Sports after the game: "I'm very happy to be in the semi-finals. We played against a team who are hard to generate chances against. We generated a lot and we should have scored many more goals." The Arsenal boss had made eight changes to his starting line-up and admitted: "It's always tough because they don't have the right chemistry when they haven't played together. But their attitude is excellent. "I think we had some big individual performances tonight. It's great for Gabriel Jesus tonight, after almost a year out, to start a game and make his 100th [Arsenal] appearance. The commitment within the group is incredible and I'm very happy for the boys."
"""


def test_granularity_mode(mode: GranularityMode):
    """Test a specific granularity mode."""
    print(f"\n{'='*70}")
    print(f"Testing: {mode.value.upper()} granularity")
    print(f"{'='*70}")
    
    # Split into sentences
    splitter = SentenceSplitter()
    sentences = splitter.split(text)
    print(f"Input: {len(sentences)} sentences\n")
    
    # Initialize chunker
    backend = OllamaBackendV2(model="llama3:latest", temperature=0.2)
    config = ChunkerConfig(
        granularity=mode,
        context_window=2,
        max_sentences_per_chunk=5,
        enable_structural_rules=True,
        enable_orphan_merge=True,
        log_scores=False
    )
    chunker = SemanticChunker(llm=backend, config=config)
    
    # Chunk
    chunks = chunker.chunk(sentences)
    
    # Display results
    print(f"Output: {len(chunks)} chunks")
    print(f"Threshold: {config.break_threshold}\n")
    
    for chunk in chunks:
        print(f"[Chunk {chunk.chunk_id}] Type: {chunk.chunk_type}, Sentences: {len(chunk)}")
        for i, sent in enumerate(chunk.sentences, 1):
            preview = sent[:70] + "..." if len(sent) > 70 else sent
            print(f"  {i}. {preview}")
        print()
    
    # Statistics
    stats = chunker.get_stats()
    print(f"Statistics:")
    print(f"  - Total LLM calls: {stats['total_scores']}")
    print(f"  - LLM failures: {stats['llm_failures']}")
    print(f"  - Forced splits (size): {stats['forced_splits_size']}")
    print(f"  - Forced splits (structural): {stats['forced_splits_structural']}")
    print(f"  - Orphan merges: {stats['orphan_merges']}")
    if 'avg_score' in stats:
        print(f"  - Avg score: {stats['avg_score']:.2f}")
        print(f"  - Score range: [{stats['min_score']:.2f}, {stats['max_score']:.2f}]")


def main():
    """Test all granularity modes."""
    print("\n" + "="*70)
    print("SEMANTIC CHUNKER V2 - CONTINUOUS SCORING SYSTEM")
    print("="*70)
    
    # Test each mode
    for mode in [GranularityMode.MEDIUM, GranularityMode.FINE, GranularityMode.COARSE]:
        test_granularity_mode(mode)
    
    print("\n" + "="*70)
    print("✓ All tests completed")
    print("="*70)


if __name__ == "__main__":
    main()
