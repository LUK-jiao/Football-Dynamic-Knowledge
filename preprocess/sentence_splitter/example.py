"""
Example usage of the sentence splitter.
Demonstrates the complete pipeline on sports news text.
"""

from .splitter import SentenceSplitter


def main():
    """Run example splitting on sports news."""
    
    # Initialize splitter
    splitter = SentenceSplitter(use_nlp=True)
    
    # Example 1: Complex sports news with multiple facts
    text1 = (
        "After bossing much of the quarter-final against Palace and creating "
        "the majority of big chances, Arteta's men finally found their breakthrough, "
        "which came from a corner in the 80th minute. A well-placed delivery into the box from Bukayo Saka "
        "found the head of Riccardo Calafiori and eventually went into the net off Palace centre-back Lacroix. "   
        )
    
    print("=" * 80)
    print("Example 1: EFL Cup Match Report")
    print("=" * 80)
    print("\nOriginal text:")
    print(text1)
    print("\nSplit sentences:")
    sentences1 = splitter.split(text1)
    for i, sent in enumerate(sentences1, 1):
        print(f"{i}. {sent}")
    
    # Example 2: Multiple actions in sequence
    text2 = (
        "Manchester United secured a crucial victory at Old Trafford, scoring two goals "
        "in quick succession during the second half, with Marcus Rashford opening the "
        "scoring in the 67th minute, and Bruno Fernandes adding a second just three "
        "minutes later."
    )
    
    print("\n" + "=" * 80)
    print("Example 2: Match Report with Sequential Goals")
    print("=" * 80)
    print("\nOriginal text:")
    print(text2)
    print("\nSplit sentences:")
    sentences2 = splitter.split(text2)
    for i, sent in enumerate(sentences2, 1):
        print(f"{i}. {sent}")
    
    # Example 3: Complex announcement with multiple clauses
    text3 = (
        "The club announced the signing of the Brazilian forward on a four-year deal, "
        "confirmed the departure of two senior players, and revealed plans for stadium "
        "expansion that will increase capacity to 65,000 seats by 2026."
    )
    
    print("\n" + "=" * 80)
    print("Example 3: Club Announcement")
    print("=" * 80)
    print("\nOriginal text:")
    print(text3)
    print("\nSplit sentences:")
    sentences3 = splitter.split(text3)
    for i, sent in enumerate(sentences3, 1):
        print(f"{i}. {sent}")
    
    # Example 4: Long compound sentence
    text4 = (
        "Liverpool dominated possession throughout the match, creating numerous chances "
        "in the first half, however they were unable to break down the resilient defense, "
        "and it wasn't until the 78th minute that Mohamed Salah finally found the "
        "breakthrough with a stunning strike from outside the box."
    )
    
    print("\n" + "=" * 80)
    print("Example 4: Match Narrative with Multiple Phases")
    print("=" * 80)
    print("\nOriginal text:")
    print(text4)
    print("\nSplit sentences:")
    sentences4 = splitter.split(text4)
    for i, sent in enumerate(sentences4, 1):
        print(f"{i}. {sent}")
    
    # Example 5: Transfer news with details
    text5 = (
        "Chelsea completed the signing of Cole Palmer from Manchester City for a fee "
        "believed to be around £40 million, the 21-year-old midfielder has signed a "
        "seven-year contract and will wear the number 20 shirt for the Blues."
    )
    
    print("\n" + "=" * 80)
    print("Example 5: Transfer News")
    print("=" * 80)
    print("\nOriginal text:")
    print(text5)
    print("\nSplit sentences:")
    sentences5 = splitter.split(text5)
    for i, sent in enumerate(sentences5, 1):
        print(f"{i}. {sent}")
    
    # Show statistics
    print("\n" + "=" * 80)
    print("Pipeline Statistics")
    print("=" * 80)
    all_sentences = sentences1 + sentences2 + sentences3 + sentences4 + sentences5
    print(f"Total sentences produced: {len(all_sentences)}")
    print(f"Average sentence length: {sum(len(s) for s in all_sentences) / len(all_sentences):.1f} chars")
    print(f"Shortest sentence: {min(len(s) for s in all_sentences)} chars")
    print(f"Longest sentence: {max(len(s) for s in all_sentences)} chars")


if __name__ == "__main__":
    main()
