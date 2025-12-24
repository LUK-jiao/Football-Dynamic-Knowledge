#!/usr/bin/env python3
"""
Standalone test script for sentence splitter.
Run from project root: python3 preprocess/test_splitter.py
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from preprocess.sentence_splitter import SentenceSplitter


def test_basic():
    """Test basic splitting functionality."""
    splitter = SentenceSplitter(use_nlp=False)
    
    print("=" * 80)
    print("SENTENCE SPLITTER TEST SUITE")
    print("=" * 80)
    
    # Test 1: EFL Cup example
    print("\n[Test 1] EFL Cup Match Report")
    text1 = (
        "Mikel Arteta's Arsenal side marched on to the EFL Cup semi-finals but did it "
        "the hard way by winning 8-7 on penalties against Crystal Palace, with Kepa "
        "Arrizabalaga saving the 16th spot-kick taken by Maxence Lacroix after 15 "
        "successful conversions."
    )
    result1 = splitter.split(text1)
    print(f"Input: {text1}")
    print(f"\nOutput ({len(result1)} sentences):")
    for i, sent in enumerate(result1, 1):
        print(f"  {i}. {sent}")
    
    # Test 2: Simple conjunction split
    print("\n[Test 2] Simple Conjunction")
    text2 = "Arsenal won the match, and Manchester United lost."
    result2 = splitter.split(text2)
    print(f"Input: {text2}")
    print(f"\nOutput ({len(result2)} sentences):")
    for i, sent in enumerate(result2, 1):
        print(f"  {i}. {sent}")
    
    # Test 3: Multiple facts with triggers
    print("\n[Test 3] Multiple Triggers")
    text3 = "The team scored first, then defended well, but conceded late in the game."
    result3 = splitter.split(text3)
    print(f"Input: {text3}")
    print(f"\nOutput ({len(result3)} sentences):")
    for i, sent in enumerate(result3, 1):
        print(f"  {i}. {sent}")
    
    # Test 4: Long sentence forcing fallback
    print("\n[Test 4] Long Sentence Fallback")
    text4 = (
        "The manager announced that the club had signed three new players during the "
        "transfer window, including a striker from Brazil, a midfielder from Spain, "
        "and a defender from Germany, all of whom are expected to make their debuts "
        "in the upcoming match against their local rivals."
    )
    result4 = splitter.split(text4)
    print(f"Input: {text4}")
    print(f"\nOutput ({len(result4)} sentences):")
    for i, sent in enumerate(result4, 1):
        print(f"  {i}. {sent}")
    
    # Test 5: Complex reporting
    print("\n[Test 5] Complex Match Report")
    text5 = (
        "Liverpool dominated possession throughout the match, creating numerous chances "
        "in the first half, however they were unable to break down the resilient defense, "
        "and it wasn't until the 78th minute that Mohamed Salah finally found the "
        "breakthrough with a stunning strike from outside the box."
    )
    result5 = splitter.split(text5)
    print(f"Input: {text5}")
    print(f"\nOutput ({len(result5)} sentences):")
    for i, sent in enumerate(result5, 1):
        print(f"  {i}. {sent}")
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    test_basic()
