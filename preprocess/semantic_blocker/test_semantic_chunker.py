"""
Comprehensive Test Suite for Semantic Chunker

Tests:
1. Normal flow with valid LLM responses
2. LLM failure modes and fallback behavior
3. Edge cases (empty input, single sentence, etc.)
4. Window size variations
5. Statistics tracking
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from typing import List, Tuple
from semantic_chunker import (
    SemanticChunker,
    ChunkerConfig,
    BoundaryDecision,
    FallbackReason,
    LLMBackend
)


# ============================================================================
# Mock LLM Backend for Testing
# ============================================================================

class MockLLMBackend(LLMBackend):
    """Mock backend for controlled testing."""
    
    def __init__(self, responses: List[Tuple[str, bool]] = None):
        """
        Initialize with predefined responses.
        
        Args:
            responses: List of (output, success) tuples
                      If None, defaults to alternating SAME/NEW
        """
        self.responses = responses or []
        self.call_count = 0
        self.call_history = []
    
    def decide_boundary(
        self, 
        current_sentence: str, 
        previous_sentences: List[str]
    ) -> Tuple[str, bool]:
        """Return predefined response."""
        self.call_history.append({
            'current': current_sentence,
            'previous': previous_sentences
        })
        
        if self.responses:
            response = self.responses[self.call_count % len(self.responses)]
        else:
            # Default: alternate between SAME and NEW
            response = (
                "SAME_UNIT" if self.call_count % 2 == 0 else "NEW_UNIT",
                True
            )
        
        self.call_count += 1
        return response


# ============================================================================
# Test Cases
# ============================================================================

def test_basic_chunking():
    """Test basic chunking with all SAME_UNIT."""
    print("\n=== Test: Basic Chunking (All SAME_UNIT) ===")
    
    backend = MockLLMBackend([("SAME_UNIT", True)] * 10)
    chunker = SemanticChunker(backend)
    
    sentences = [
        "Arsenal won 2-1.",
        "Saka scored the winner.",
        "It was a brilliant goal."
    ]
    
    chunks = chunker.chunk(sentences)
    
    assert len(chunks) == 1, f"Expected 1 chunk, got {len(chunks)}"
    assert chunks[0] == sentences, "All sentences should be in one chunk"
    
    print("✓ All sentences grouped into single chunk")
    print(f"  Chunks: {chunks}")


def test_all_new_units():
    """Test chunking with all NEW_UNIT."""
    print("\n=== Test: All NEW_UNIT ===")
    
    backend = MockLLMBackend([("NEW_UNIT", True)] * 10)
    chunker = SemanticChunker(backend)
    
    sentences = [
        "Arsenal won 2-1.",
        "Liverpool lost at home.",
        "Chelsea signed a new player."
    ]
    
    chunks = chunker.chunk(sentences)
    
    assert len(chunks) == 3, f"Expected 3 chunks, got {len(chunks)}"
    assert all(len(chunk) == 1 for chunk in chunks), "Each chunk should have 1 sentence"
    
    print("✓ Each sentence becomes separate chunk")
    print(f"  Chunks: {chunks}")


def test_mixed_decisions():
    """Test with mixed SAME/NEW decisions."""
    print("\n=== Test: Mixed Decisions ===")
    
    # Pattern: SAME, NEW, SAME, NEW
    backend = MockLLMBackend([
        ("SAME_UNIT", True),
        ("NEW_UNIT", True),
        ("SAME_UNIT", True),
        ("NEW_UNIT", True)
    ])
    chunker = SemanticChunker(backend)
    
    sentences = [
        "S1", "S2", "S3", "S4", "S5"
    ]
    
    chunks = chunker.chunk(sentences)
    
    # Expected: [S1,S2], [S3,S4], [S5]
    assert len(chunks) == 3, f"Expected 3 chunks, got {len(chunks)}"
    assert len(chunks[0]) == 2, "First chunk should have 2 sentences"
    assert len(chunks[1]) == 2, "Second chunk should have 2 sentences"
    assert len(chunks[2]) == 1, "Third chunk should have 1 sentence"
    
    print("✓ Mixed decisions create correct chunks")
    print(f"  Chunks: {chunks}")


def test_invalid_llm_output():
    """Test fallback on invalid LLM output."""
    print("\n=== Test: Invalid LLM Output ===")
    
    # Responses: valid, invalid, valid
    backend = MockLLMBackend([
        ("SAME_UNIT", True),
        ("This is an explanation with multiple words", True),  # Invalid
        ("NEW_UNIT", True)
    ])
    
    config = ChunkerConfig(force_new_on_failure=True, log_failures=False)
    chunker = SemanticChunker(backend, config)
    
    sentences = ["S1", "S2", "S3", "S4"]
    chunks = chunker.chunk(sentences)
    
    stats = chunker.get_stats()
    
    print(f"✓ Fallback triggered {stats['fallback_count']} time(s)")
    print(f"  Fallback rate: {stats['fallback_rate']:.2%}")
    print(f"  Fallback reasons: {stats['fallback_reasons']}")
    print(f"  Chunks: {chunks}")
    
    assert stats['fallback_count'] > 0, "Should have triggered fallback"


def test_empty_llm_response():
    """Test fallback on empty LLM response."""
    print("\n=== Test: Empty LLM Response ===")
    
    backend = MockLLMBackend([
        ("SAME_UNIT", True),
        ("", True),  # Empty response
        ("NEW_UNIT", True)
    ])
    
    config = ChunkerConfig(force_new_on_failure=True, log_failures=False)
    chunker = SemanticChunker(backend, config)
    
    sentences = ["S1", "S2", "S3", "S4"]
    chunks = chunker.chunk(sentences)
    
    stats = chunker.get_stats()
    
    print(f"✓ Empty response handled")
    print(f"  Fallback count: {stats['fallback_count']}")
    print(f"  Chunks: {chunks}")
    
    assert FallbackReason.EMPTY_RESPONSE.value in stats['fallback_reasons']


def test_llm_api_failure():
    """Test fallback on API/network failure."""
    print("\n=== Test: LLM API Failure ===")
    
    backend = MockLLMBackend([
        ("SAME_UNIT", True),
        ("", False),  # API failure
        ("NEW_UNIT", True)
    ])
    
    config = ChunkerConfig(force_new_on_failure=True, log_failures=False)
    chunker = SemanticChunker(backend, config)
    
    sentences = ["S1", "S2", "S3", "S4"]
    chunks = chunker.chunk(sentences)
    
    stats = chunker.get_stats()
    
    print(f"✓ API failure handled")
    print(f"  Fallback count: {stats['fallback_count']}")
    print(f"  Chunks: {chunks}")
    
    assert FallbackReason.LLM_ERROR.value in stats['fallback_reasons']


def test_edge_case_empty_input():
    """Test with empty input."""
    print("\n=== Test: Edge Case - Empty Input ===")
    
    backend = MockLLMBackend()
    chunker = SemanticChunker(backend)
    
    chunks = chunker.chunk([])
    
    assert chunks == [], "Empty input should return empty list"
    print("✓ Empty input handled correctly")


def test_edge_case_single_sentence():
    """Test with single sentence."""
    print("\n=== Test: Edge Case - Single Sentence ===")
    
    backend = MockLLMBackend()
    chunker = SemanticChunker(backend)
    
    chunks = chunker.chunk(["Only sentence"])
    
    assert len(chunks) == 1, "Single sentence should return one chunk"
    assert chunks[0] == ["Only sentence"]
    print("✓ Single sentence handled correctly")


def test_window_size_variations():
    """Test different window sizes."""
    print("\n=== Test: Window Size Variations ===")
    
    for window_size in [1, 2, 3]:
        backend = MockLLMBackend([("SAME_UNIT", True)] * 10)
        config = ChunkerConfig(window_size=window_size)
        chunker = SemanticChunker(backend, config)
        
        sentences = ["S1", "S2", "S3", "S4", "S5"]
        chunks = chunker.chunk(sentences)
        
        # With all SAME_UNIT, should get one chunk regardless
        assert len(chunks) == 1, f"Window size {window_size}: expected 1 chunk"
        
        print(f"✓ Window size {window_size} works correctly")


def test_statistics_tracking():
    """Test that statistics are tracked correctly."""
    print("\n=== Test: Statistics Tracking ===")
    
    backend = MockLLMBackend([
        ("SAME_UNIT", True),
        ("NEW_UNIT", True),
        ("INVALID", True),  # Will fallback to NEW_UNIT
    ])
    
    config = ChunkerConfig(log_failures=False)
    chunker = SemanticChunker(backend, config)
    
    sentences = ["S1", "S2", "S3", "S4"]
    chunks = chunker.chunk(sentences)
    
    stats = chunker.get_stats()
    
    print(f"✓ Statistics tracked:")
    print(f"  Total decisions: {stats['total_decisions']}")
    print(f"  SAME_UNIT: {stats['same_unit_count']}")
    print(f"  NEW_UNIT: {stats['new_unit_count']}")
    print(f"  Fallbacks: {stats['fallback_count']}")
    print(f"  Fallback rate: {stats['fallback_rate']:.2%}")
    
    assert stats['total_decisions'] == 3
    assert stats['fallback_count'] == 1


def test_deterministic_behavior():
    """Test that same input produces same output."""
    print("\n=== Test: Deterministic Behavior ===")
    
    sentences = ["S1", "S2", "S3", "S4", "S5"]
    
    # Run twice with same backend configuration
    results = []
    for i in range(2):
        backend = MockLLMBackend([
            ("SAME_UNIT", True),
            ("NEW_UNIT", True),
            ("SAME_UNIT", True),
            ("NEW_UNIT", True)
        ])
        chunker = SemanticChunker(backend)
        chunks = chunker.chunk(sentences)
        results.append(chunks)
    
    assert results[0] == results[1], "Same input should produce same output"
    print("✓ Behavior is deterministic")
    print(f"  Run 1: {results[0]}")
    print(f"  Run 2: {results[1]}")


# ============================================================================
# Run All Tests
# ============================================================================

def run_all_tests():
    """Run all test cases."""
    print("="*70)
    print("SEMANTIC CHUNKER TEST SUITE")
    print("="*70)
    
    tests = [
        test_basic_chunking,
        test_all_new_units,
        test_mixed_decisions,
        test_invalid_llm_output,
        test_empty_llm_response,
        test_llm_api_failure,
        test_edge_case_empty_input,
        test_edge_case_single_sentence,
        test_window_size_variations,
        test_statistics_tracking,
        test_deterministic_behavior
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"\n✗ FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"\n✗ ERROR: {e}")
            failed += 1
    
    print("\n" + "="*70)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("="*70)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
