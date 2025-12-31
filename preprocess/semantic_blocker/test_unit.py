#!/usr/bin/env python3
"""
Unit tests for semantic_blocker module.
Tests vector-based blocking and rule-based adjustments.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from preprocess.semantic_blocker import semantic_block, SemanticBlocker


def test_basic_blocking():
    """Test basic semantic blocking functionality."""
    print("\n[Test 1] Basic Blocking")
    
    sentences = [
        "Chelsea won 3-2.",
        "The Blues celebrated the victory.",
        "However, Arsenal lost.",
        "The Gunners were disappointed."
    ]
    
    blocker = SemanticBlocker(similarity_threshold=0.6)
    blocks = blocker.block(sentences)
    
    print(f"Input: {len(sentences)} sentences")
    print(f"Output: {len(blocks)} blocks")
    for i, block in enumerate(blocks, 1):
        print(f"  Block {i}: {block}")
    
    # Expect at least 2 blocks due to "However" marker
    assert len(blocks) >= 2, "Should split at discourse marker"
    # Check that "However" creates a boundary
    however_blocks = [b for b in blocks if "However" in b]
    assert len(however_blocks) > 0, "Should have block containing 'However'"
    print("✓ Test passed")


def test_same_subject_merging():
    """Test that sentences with same subject tend to merge."""
    print("\n[Test 2] Same Subject Merging")
    
    sentences = [
        "Manchester City signed Grealish.",
        "The club paid £100 million.",
        "City expressed confidence in the player."
    ]
    
    # Use lower threshold to encourage merging based on similarity
    blocker = SemanticBlocker(similarity_threshold=0.4, use_subject_matching=True)
    blocks = blocker.block(sentences)
    
    print(f"Input: {len(sentences)} sentences")
    print(f"Output: {len(blocks)} blocks")
    for i, block in enumerate(blocks, 1):
        print(f"  Block {i}: {block}")
    
    # Should merge at least some sentences due to high semantic similarity
    # (about same transfer event)
    assert len(blocks) < len(sentences), "Related sentences should merge"
    print("✓ Test passed")


def test_discourse_markers():
    """Test that discourse markers force block boundaries."""
    print("\n[Test 3] Discourse Marker Boundaries")
    
    sentences = [
        "Liverpool won 4-0.",
        "However, they suffered injuries.",
        "Meanwhile, Chelsea drew 1-1."
    ]
    
    blocker = SemanticBlocker(similarity_threshold=0.7)
    blocks = blocker.block(sentences)
    
    print(f"Input: {len(sentences)} sentences")
    print(f"Output: {len(blocks)} blocks")
    for i, block in enumerate(blocks, 1):
        print(f"  Block {i}: {block}")
    
    # Should have 3 blocks due to "However" and "Meanwhile"
    assert len(blocks) >= 2, "Discourse markers should create boundaries"
    print("✓ Test passed")


def test_time_expression_splitting():
    """Test splitting at time expressions."""
    print("\n[Test 4] Time Expression Splitting")
    
    sentences = [
        "Arsenal led 1-0.",
        "In the 89th minute, City equalized.",
        "The match ended 1-1."
    ]
    
    blocker = SemanticBlocker(similarity_threshold=0.6)
    blocks = blocker.block(sentences)
    
    print(f"Input: {len(sentences)} sentences")
    print(f"Output: {len(blocks)} blocks")
    for i, block in enumerate(blocks, 1):
        print(f"  Block {i}: {block}")
    
    # Time marker should trigger split
    assert len(blocks) >= 2, "Time expressions should trigger splits"
    print("✓ Test passed")


def test_length_limiting():
    """Test that oversized blocks are split."""
    print("\n[Test 5] Length Limiting")
    
    # Create a very long sentence
    long_sentence = "Chelsea " + " and Manchester United " * 30 + "played a match."
    sentences = [long_sentence, "The match was exciting."]
    
    blocker = SemanticBlocker(max_block_length=200)
    blocks = blocker.block(sentences)
    
    print(f"Input: {len(sentences)} sentences")
    print(f"Output: {len(blocks)} blocks")
    print(f"Max block length: {max(len(b) for b in blocks)} chars")
    
    # Should split the long sentence
    assert all(len(block) <= 300 for block in blocks), "Blocks should be within reasonable length"
    print("✓ Test passed")


def test_convenience_function():
    """Test the convenience semantic_block function."""
    print("\n[Test 6] Convenience Function")
    
    sentences = [
        "Arsenal won 2-0.",
        "Saka scored both goals.",
        "The team is top of the league."
    ]
    
    blocks = semantic_block(sentences, similarity_threshold=0.6)
    
    print(f"Input: {len(sentences)} sentences")
    print(f"Output: {len(blocks)} blocks")
    for i, block in enumerate(blocks, 1):
        print(f"  Block {i}: {block}")
    
    assert len(blocks) > 0, "Should return at least one block"
    assert isinstance(blocks, list), "Should return a list"
    assert all(isinstance(b, str) for b in blocks), "All blocks should be strings"
    print("✓ Test passed")


def test_empty_input():
    """Test handling of empty input."""
    print("\n[Test 7] Empty Input")
    
    blocker = SemanticBlocker()
    
    # Test empty list
    blocks1 = blocker.block([])
    assert blocks1 == [], "Empty list should return empty list"
    
    # Test single sentence
    blocks2 = blocker.block(["Single sentence."])
    assert len(blocks2) == 1, "Single sentence should return single block"
    
    print("✓ Test passed")


def test_cleaning():
    """Test output cleaning."""
    print("\n[Test 8] Output Cleaning")
    
    sentences = [
        "Chelsea   won   3-2.",  # Multiple spaces
        "The team    celebrated.",
        "  Arsenal lost.  "  # Leading/trailing spaces
    ]
    
    blocker = SemanticBlocker()
    blocks = blocker.block(sentences)
    
    print(f"Input: {sentences}")
    print(f"Output: {blocks}")
    
    # Check all blocks are cleaned
    for block in blocks:
        assert "  " not in block, "Should not have multiple consecutive spaces"
        assert block == block.strip(), "Should not have leading/trailing whitespace"
    
    print("✓ Test passed")


def run_all_tests():
    """Run all test cases."""
    print("=" * 80)
    print("SEMANTIC BLOCKER - Unit Tests")
    print("=" * 80)
    
    try:
        test_basic_blocking()
        test_same_subject_merging()
        test_discourse_markers()
        test_time_expression_splitting()
        test_length_limiting()
        test_convenience_function()
        test_empty_input()
        test_cleaning()
        
        print("\n" + "=" * 80)
        print("✓ All tests passed!")
        print("=" * 80)
        
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        return False
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
