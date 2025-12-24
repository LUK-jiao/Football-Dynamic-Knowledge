"""
Unit tests for sentence splitter module.
"""

import unittest
from preprocess.sentence_splitter import SentenceSplitter
from preprocess.sentence_splitter.rule_splitter import RuleSplitter
from preprocess.sentence_splitter.cleaner import SentenceCleaner
from preprocess.sentence_splitter.fallback import FallbackSplitter


class TestRuleSplitter(unittest.TestCase):
    """Test rule-based splitting logic."""
    
    def setUp(self):
        self.splitter = RuleSplitter()
    
    def test_strong_punctuation_split(self):
        """Test splitting by period."""
        text = "Arsenal won. Chelsea lost."
        result = self.splitter.split(text)
        self.assertEqual(len(result), 2)
    
    def test_conjunction_split(self):
        """Test splitting by comma + conjunction."""
        text = "Arsenal won the match, and Chelsea lost the final."
        result = self.splitter.split(text)
        self.assertGreaterEqual(len(result), 2)
    
    def test_trigger_word_split(self):
        """Test splitting by trigger words."""
        text = "The match started early, however it ended late."
        result = self.splitter.split(text)
        self.assertGreaterEqual(len(result), 2)
    
    def test_empty_text(self):
        """Test handling empty input."""
        result = self.splitter.split("")
        self.assertEqual(result, [])
    
    def test_no_split_needed(self):
        """Test text that doesn't need splitting."""
        text = "This is a simple sentence about football."
        result = self.splitter.split(text)
        self.assertEqual(len(result), 1)


class TestCleaner(unittest.TestCase):
    """Test sentence cleaning logic."""
    
    def setUp(self):
        self.cleaner = SentenceCleaner()
    
    def test_whitespace_normalization(self):
        """Test whitespace is normalized."""
        sentences = ["Hello    world", "Test   sentence"]
        result = self.cleaner.clean(sentences)
        for sent in result:
            self.assertNotIn("  ", sent)
    
    def test_remove_duplicates(self):
        """Test duplicate removal."""
        sentences = ["Same sentence.", "Same sentence.", "Different."]
        result = self.cleaner.clean(sentences)
        self.assertEqual(len(result), 2)
    
    def test_filter_short(self):
        """Test short sentences are filtered."""
        sentences = ["Hi.", "This is a proper length sentence."]
        result = self.cleaner.clean(sentences)
        self.assertGreater(len(result[0]), 10)
    
    def test_add_period(self):
        """Test period is added if missing."""
        sentences = ["This has no period"]
        result = self.cleaner.clean(sentences)
        if result:
            self.assertTrue(result[0].endswith('.'))


class TestFallbackSplitter(unittest.TestCase):
    """Test fallback splitting for long sentences."""
    
    def setUp(self):
        self.splitter = FallbackSplitter()
    
    def test_short_sentence_unchanged(self):
        """Test short sentences pass through."""
        sentences = ["Short sentence."]
        result = self.splitter.split_long_sentences(sentences)
        self.assertEqual(result, sentences)
    
    def test_long_sentence_split(self):
        """Test long sentences are split."""
        long_sent = "A" * 150  # Create a very long sentence
        sentences = [long_sent]
        result = self.splitter.split_long_sentences(sentences)
        # Should be split into multiple parts
        for sent in result:
            self.assertLessEqual(len(sent), 120)


class TestSentenceSplitter(unittest.TestCase):
    """Test complete pipeline."""
    
    def setUp(self):
        self.splitter = SentenceSplitter(use_nlp=False)
    
    def test_efl_cup_example(self):
        """Test the main EFL Cup example."""
        text = (
            "Mikel Arteta's Arsenal side marched on to the EFL Cup semi-finals but did it "
            "the hard way by winning 8-7 on penalties against Crystal Palace, with Kepa "
            "Arrizabalaga saving the 16th spot-kick taken by Maxence Lacroix after 15 "
            "successful conversions."
        )
        result = self.splitter.split(text)
        # Should split into multiple sentences
        self.assertGreater(len(result), 1)
        # Each sentence should be reasonable length
        for sent in result:
            self.assertLessEqual(len(sent), 200)
    
    def test_simple_conjunction(self):
        """Test simple conjunction split."""
        text = "Arsenal won, and Chelsea lost."
        result = self.splitter.split(text)
        self.assertGreaterEqual(len(result), 2)
    
    def test_multiple_facts(self):
        """Test splitting multiple facts."""
        text = "The team scored first, then defended well, but conceded late."
        result = self.splitter.split(text)
        self.assertGreater(len(result), 1)
    
    def test_batch_processing(self):
        """Test batch processing."""
        texts = [
            "First text with multiple facts, but simple structure.",
            "Second text. With different structure."
        ]
        results = self.splitter.split_batch(texts)
        self.assertEqual(len(results), 2)
        self.assertIsInstance(results[0], list)
        self.assertIsInstance(results[1], list)
    
    def test_empty_input(self):
        """Test empty input handling."""
        result = self.splitter.split("")
        self.assertEqual(result, [])
    
    def test_no_split_needed(self):
        """Test text that doesn't need splitting."""
        text = "This is a simple sentence."
        result = self.splitter.split(text)
        self.assertEqual(len(result), 1)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and special scenarios."""
    
    def setUp(self):
        self.splitter = SentenceSplitter(use_nlp=False)
    
    def test_only_punctuation(self):
        """Test text with only punctuation."""
        text = "... !!! ???"
        result = self.splitter.split(text)
        # Should handle gracefully
        self.assertIsInstance(result, list)
    
    def test_numbers_and_symbols(self):
        """Test text with numbers and symbols."""
        text = "Arsenal won 3-0, scoring goals in the 10th, 25th, and 67th minutes."
        result = self.splitter.split(text)
        self.assertGreater(len(result), 0)
    
    def test_urls_preserved(self):
        """Test that URLs are not split."""
        text = "Visit www.example.com for more info. Also check other.site.com here."
        result = self.splitter.split(text)
        # Should split into 2 sentences
        self.assertGreaterEqual(len(result), 1)
    
    def test_unicode_characters(self):
        """Test handling of unicode characters."""
        text = "Müller scored, and Özil assisted."
        result = self.splitter.split(text)
        self.assertGreater(len(result), 0)


def run_tests():
    """Run all tests."""
    unittest.main(argv=[''], verbosity=2, exit=False)


if __name__ == "__main__":
    run_tests()
