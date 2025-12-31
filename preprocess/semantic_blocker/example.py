#!/usr/bin/env python3
"""
Example usage of semantic_blocker module.
Demonstrates how to group sentences into coherent semantic blocks.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from preprocess.sentence_splitter import SentenceSplitter
from preprocess.semantic_blocker import semantic_block


def main():
    """Run semantic blocking examples."""
    
    print("=" * 80)
    print("SEMANTIC BLOCKER - Example Usage")
    print("=" * 80)
    
    # Initialize sentence splitter
    splitter = SentenceSplitter()
    
    # ========================================================================
    # Example 1: Match Report with Multiple Events
    # ========================================================================
    print("\n[Example 1] Match Report - Multiple Events")
    print("-" * 80)
    
    text1 = """
    Chelsea defeated Manchester United 3-2 in a thrilling encounter at Stamford Bridge.
    The Blues took an early lead through Raheem Sterling in the 15th minute.
    Marcus Rashford equalized for United before halftime.
    However, Chelsea dominated the second half.
    Cole Palmer scored twice to secure the victory.
    Meanwhile, Arsenal won their match 2-0 against Tottenham.
    The Gunners extended their lead at the top of the table.
    """
    
    sentences1 = splitter.split(text1)
    print(f"\nInput sentences ({len(sentences1)}):")
    for i, sent in enumerate(sentences1, 1):
        print(f"  {i}. {sent}")
    
    blocks1 = semantic_block(sentences1, similarity_threshold=0.6)
    print(f"\nSemantic blocks ({len(blocks1)}):")
    for i, block in enumerate(blocks1, 1):
        print(f"  Block {i}: {block}")
    
    # ========================================================================
    # Example 2: Transfer News - Same Subject
    # ========================================================================
    print("\n[Example 2] Transfer News - Same Subject")
    print("-" * 80)
    
    text2 = """
    Manchester City completed the signing of Josko Gvardiol from RB Leipzig.
    The 21-year-old defender signed a five-year contract.
    He will wear the number 24 shirt.
    Gvardiol expressed his excitement about joining the Premier League champions.
    """
    
    sentences2 = splitter.split(text2)
    print(f"\nInput sentences ({len(sentences2)}):")
    for i, sent in enumerate(sentences2, 1):
        print(f"  {i}. {sent}")
    
    blocks2 = semantic_block(sentences2, similarity_threshold=0.5)
    print(f"\nSemantic blocks ({len(blocks2)}):")
    for i, block in enumerate(blocks2, 1):
        print(f"  Block {i}: {block}")
    
    # ========================================================================
    # Example 3: Mixed Topics with Discourse Markers
    # ========================================================================
    print("\n[Example 3] Mixed Topics - Discourse Markers")
    print("-" * 80)
    
    text3 = """
    Liverpool secured a comfortable 4-1 victory over Brentford.
    Mohamed Salah scored a hat-trick in the first half.
    However, injury concerns remain for the Reds.
    Virgil van Dijk suffered a hamstring strain and will be assessed.
    Meanwhile, Real Madrid announced the departure of Eden Hazard.
    The Belgian winger's contract was terminated by mutual consent.
    """
    
    sentences3 = splitter.split(text3)
    print(f"\nInput sentences ({len(sentences3)}):")
    for i, sent in enumerate(sentences3, 1):
        print(f"  {i}. {sent}")
    
    blocks3 = semantic_block(sentences3, similarity_threshold=0.6)
    print(f"\nSemantic blocks ({len(blocks3)}):")
    for i, block in enumerate(blocks3, 1):
        print(f"  Block {i}: {block}")
    
    # ========================================================================
    # Example 4: Time-based Event Separation
    # ========================================================================
    print("\n[Example 4] Time-based Events")
    print("-" * 80)
    
    text4 = """
    Arsenal took the lead in the 23rd minute through Bukayo Saka.
    The England international finished a swift counter-attack.
    Later, Manchester City equalized through Erling Haaland.
    The Norwegian striker headed home from a Kevin De Bruyne cross.
    In the 89th minute, Gabriel Martinelli scored the winner for Arsenal.
    """
    
    sentences4 = splitter.split(text4)
    print(f"\nInput sentences ({len(sentences4)}):")
    for i, sent in enumerate(sentences4, 1):
        print(f"  {i}. {sent}")
    
    blocks4 = semantic_block(sentences4, similarity_threshold=0.6)
    print(f"\nSemantic blocks ({len(blocks4)}):")
    for i, block in enumerate(blocks4, 1):
        print(f"  Block {i}: {block}")
    
    print("\n" + "=" * 80)
    print("Example completed!")
    print("=" * 80)


if __name__ == "__main__":
    main()
