#!/usr/bin/env python3
"""
Simple example of the refactored sentence splitter.
Shows that spaCy alone is sufficient for excellent sentence splitting.
"""

from preprocess.sentence_splitter import SentenceSplitter


def main():
    """Run simplified examples."""
    
    print("=" * 80)
    print("SIMPLIFIED SENTENCE SPLITTER")
    print("Architecture: spaCy + Basic Cleaning (that's it!)")
    print("=" * 80)
    
    splitter = SentenceSplitter()
    
    # Example 1: Real match report
    print("\n[Example 1] Real Match Report")
    print("-" * 80)
    
    text1 = """
    Mikel Arteta's Arsenal side marched on to the EFL Cup semi-finals but did it 
    the hard way by winning 8-7 on penalties against Crystal Palace, with Kepa 
    Arrizabalaga saving the 16th spot-kick taken by Maxence Lacroix after 15 
    successful conversions.
    Two late goals had resulted in a 1-1 draw after 90 minutes and a lengthy 
    period of stoppage time.
    The Gunners will now face rivals Chelsea to fight for a place in the final 
    at Wembley, with the first leg of their semi-final set for Stamford Bridge 
    on 14 January.
    """
    
    sentences1 = splitter.split(text1)
    print(f"\nInput: {len(text1)} chars")
    print(f"Output: {len(sentences1)} sentences")
    for i, sent in enumerate(sentences1, 1):
        print(f"  {i}. {sent}")
    
    # Example 2: Complex cases
    print("\n[Example 2] Complex Cases")
    print("-" * 80)
    
    test_cases = [
        ("U.S. Team beats Mexico 3-2.", "Abbreviations"),
        ("Coach said \"We need to improve.\" He was frustrated.", "Quotes"),
        ("Lakers shot 48.3% from field. LeBron went 8-of-15.", "Statistics"),
        ("Chelsea won, and United lost, but Arsenal drew.", "Conjunctions"),
    ]
    
    for text, label in test_cases:
        sentences = splitter.split(text)
        print(f"\n{label}:")
        print(f"  Input:  {text}")
        print(f"  Output: {len(sentences)} sentence(s)")
        for i, sent in enumerate(sentences, 1):
            print(f"    {i}. {sent}")
    
    # Example 3: Batch processing
    print("\n[Example 3] Batch Processing")
    print("-" * 80)
    
    texts = [
        "Arsenal won 3-2. The team celebrated.",
        "Chelsea lost 0-1. The manager was disappointed.",
        "Liverpool drew 2-2. Both teams played well."
    ]
    
    results = splitter.split_batch(texts)
    print(f"\nProcessed {len(texts)} texts:")
    for i, (text, sentences) in enumerate(zip(texts, results), 1):
        print(f"  Text {i}: {len(sentences)} sentences")
        for j, sent in enumerate(sentences, 1):
            print(f"    {j}. {sent}")
    
    print("\n" + "=" * 80)
    print("✓ All examples completed!")
    print("=" * 80)
    print("\nKey takeaway: spaCy alone is sufficient!")
    print("No need for complex rules, fallbacks, or subject splitters.")


if __name__ == "__main__":
    main()
