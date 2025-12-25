"""
Example usage of refactored NLP-first sentence splitter.
Demonstrates improved handling of English sports news.
"""

from .splitter import SentenceSplitter


def print_example(title: str, text: str, splitter: SentenceSplitter):
    """Print splitting example with formatting."""
    print("\n" + "=" * 80)
    print(f"{title}")
    print("=" * 80)
    print(f"\nOriginal text:")
    print(text)
    print(f"\nSplit sentences:")
    
    sentences = splitter.split(text)
    for i, sent in enumerate(sentences, 1):
        print(f"{i}. {sent}")
    
    print(f"\nTotal: {len(sentences)} sentence(s)")


def main():
    """Run example splitting on English sports news."""
    
    # Initialize NLP-first splitter
    splitter = SentenceSplitter(enable_sports_rules=True, enable_fallback=True)
    
    print("=" * 80)
    print("NLP-FIRST SENTENCE SPLITTER - SPORTS NEWS EXAMPLES")
    print("Architecture: spaCy → Sports Rules → Fallback → Clean")
    print("=" * 80)
    
    # Example 1: EFL Cup Match Report (from requirement)
    text1 = (
        "Mikel Arteta's Arsenal side marched on to the EFL Cup semi-finals but did it "
        "the hard way by winning 8-7 on penalties against Crystal Palace, with Kepa "
        "Arrizabalaga saving the 16th spot-kick taken by Maxence Lacroix after 15 "
        "successful conversions."
    )
    print_example("Example 1: EFL Cup Match Report", text1, splitter)
    
    # Example 2: Score-heavy reporting
    text2 = (
        "Manchester City beat Arsenal 2–1 on Sunday, with Haaland scoring twice. "
        "The victory moved them to the top of the Premier League table."
    )
    print_example("Example 2: Score-Heavy Reporting", text2, splitter)
    
    # Example 3: Quote handling
    text3 = (
        "The coach said the team 'lacked intensity', but praised their second-half response. "
        '"We need to improve," he added.'
    )
    print_example("Example 3: Quote Handling", text3, splitter)
    
    # Example 4: Statistics-heavy sentence
    text4 = (
        "The Lakers shot 48.3% from the field, compared to Boston's 44.1%. "
        "LeBron James went 8-of-15 from the floor, including 3-of-6 from three-point range."
    )
    print_example("Example 4: Statistics-Heavy", text4, splitter)
    
    # Example 5: Complex match narrative
    text5 = (
        "Liverpool dominated possession throughout the match, creating numerous chances "
        "in the first half. However, they were unable to break down the resilient defense "
        "until the 78th minute, when Mohamed Salah finally found the breakthrough with a "
        "stunning strike from outside the box."
    )
    print_example("Example 5: Complex Match Narrative", text5, splitter)
    
    # Example 6: Transfer news with details
    text6 = (
        "Chelsea completed the signing of Cole Palmer from Manchester City for a fee "
        "believed to be around £40 million. The 21-year-old midfielder has signed a "
        "seven-year contract and will wear the number 20 shirt for the Blues."
    )
    print_example("Example 6: Transfer News", text6, splitter)
    
    # Example 7: Abbreviations (testing sports rules)
    text7 = (
        "The U.S. Men's National Team defeated Mexico 3-2 in the CONCACAF final. "
        "Coach John Doe said it was the team's best performance vs. a top opponent."
    )
    print_example("Example 7: Abbreviations", text7, splitter)
    
    # Example 8: Time markers
    text8 = (
        "The game was tied 1-1 until the 88th minute. Arsenal then scored twice in "
        "stoppage time to secure a dramatic 3-1 victory at the Emirates Stadium."
    )
    print_example("Example 8: Time Markers", text8, splitter)
    
    print("\n" + "=" * 80)
    print("COMPARISON: NLP-first vs Rule-first")
    print("=" * 80)
    print("\nKey Improvements:")
    print("1. Better handling of subordinate clauses")
    print("2. Preserved semantic completeness")
    print("3. Sports-specific patterns handled correctly")
    print("4. Quotes and dialogue preserved")
    print("5. Score/stat structures kept intact")
    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
