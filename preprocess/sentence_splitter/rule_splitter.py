"""
Rule-based sentence splitter (Primary Logic).
Uses strong/weak punctuation + trigger words.
"""

import re
from typing import List
from . import config


class RuleSplitter:
    """Rule-based sentence splitting using punctuation and trigger words."""
    
    def __init__(self):
        self.strong_punct = config.STRONG_PUNCTUATION
        self.weak_punct = config.WEAK_PUNCTUATION
        self.triggers = config.TRIGGER_WORDS
        
    def split(self, text: str) -> List[str]:
        """
        Split text using rule-based approach.
        
        Args:
            text: Input paragraph
            
        Returns:
            List of sentences split by rules
        """
        if not text or not text.strip():
            return []
        
        text = text.strip()
        
        # Step 1: Split by strong punctuation
        sentences = self._split_by_strong_punctuation(text)
        
        # Step 2: Split by coordinating conjunctions (but, and with comma)
        refined_sentences = []
        for sent in sentences:
            refined_sentences.extend(self._split_by_conjunctions(sent))
        
        # Step 3: Further split by weak punctuation + triggers
        final_sentences = []
        for sent in refined_sentences:
            final_sentences.extend(self._split_by_weak_punctuation(sent))
        
        return [s.strip() for s in final_sentences if s.strip()]
    
    def _split_by_conjunctions(self, text: str) -> List[str]:
        """
        Split by coordinating conjunctions like 'but', 'and' when they join independent clauses.
        """
        if not text or len(text) < config.MIN_SENTENCE_LENGTH:
            return [text]
        
        # Pattern: comma + but/and/yet/so + space
        # This catches ", but" and ", and" constructions
        pattern = r',\s+(but|and|yet|so)\s+'
        
        # Find all matches
        matches = list(re.finditer(pattern, text, re.IGNORECASE))
        
        if not matches:
            return [text]
        
        sentences = []
        start = 0
        
        for match in matches:
            # Split before the comma
            end = match.start()
            segment = text[start:end].strip()
            
            if segment and len(segment) >= config.MIN_SENTENCE_LENGTH:
                sentences.append(segment)
            
            # Next segment starts after comma+conjunction
            start = match.end()
        
        # Add remaining
        if start < len(text):
            segment = text[start:].strip()
            if segment and len(segment) >= config.MIN_SENTENCE_LENGTH:
                sentences.append(segment)
        
        return sentences if sentences else [text]
    
    def _split_by_strong_punctuation(self, text: str) -> List[str]:
        """Split by . ! ? while preserving abbreviations."""
        # Pattern to match strong punctuation followed by space and capital letter
        # Avoids splitting on abbreviations like "Mr." "Dr." etc.
        pattern = r'([.!?])\s+(?=[A-Z])'
        
        # Split but keep the punctuation
        parts = re.split(pattern, text)
        
        sentences = []
        i = 0
        while i < len(parts):
            if i + 1 < len(parts) and parts[i + 1] in self.strong_punct:
                # Combine text with its punctuation
                sentences.append(parts[i] + parts[i + 1])
                i += 2
            else:
                if parts[i].strip():
                    sentences.append(parts[i])
                i += 1
        
        return sentences
    
    def _split_by_weak_punctuation(self, text: str) -> List[str]:
        """
        Split by weak punctuation when followed by trigger words.
        This captures factual boundaries in complex sentences.
        """
        if not text or len(text) < config.MIN_SENTENCE_LENGTH:
            return [text]
        
        # Find all weak punctuation positions
        split_positions = []
        
        for i, char in enumerate(text):
            if char in self.weak_punct:
                # Check if followed by trigger word
                remaining = text[i+1:].lstrip()
                # Get context before punctuation to ensure it's a complete clause
                before = text[max(0, i-20):i].strip()
                
                if self._starts_with_trigger(remaining) and self._has_verb_before(before):
                    # Find the actual split position (after the punctuation and space)
                    next_word_start = i + 1
                    while next_word_start < len(text) and text[next_word_start].isspace():
                        next_word_start += 1
                    split_positions.append(next_word_start)
        
        # No weak splits found
        if not split_positions:
            return [text]
        
        # Perform splits
        sentences = []
        start = 0
        for pos in split_positions:
            segment = text[start:pos].strip()
            if segment and len(segment) >= config.MIN_SENTENCE_LENGTH:
                sentences.append(segment)
            start = pos
        
        # Add remaining
        if start < len(text):
            segment = text[start:].strip()
            if segment and len(segment) >= config.MIN_SENTENCE_LENGTH:
                sentences.append(segment)
        
        return sentences
    
    def _has_verb_before(self, text: str) -> bool:
        """
        Simple heuristic to check if text likely contains a verb.
        Looks for common verb patterns and word count.
        """
        if not text:
            return False
        
        words = text.lower().split()
        # Need at least subject + verb
        if len(words) < 2:
            return False
        
        # Common verb endings and auxiliary verbs
        verb_indicators = ['ed', 'ing', 'es', 's']
        auxiliaries = {'is', 'are', 'was', 'were', 'has', 'have', 'had', 'will', 'would', 'can', 'could', 'should'}
        
        for word in words:
            if word in auxiliaries:
                return True
            for ending in verb_indicators:
                if word.endswith(ending) and len(word) > len(ending) + 2:
                    return True
        
        return True  # Default to true for longer clauses
    
    def _starts_with_trigger(self, text: str) -> bool:
        """Check if text starts with a trigger word."""
        text_lower = text.lower()
        for trigger in self.triggers:
            # Match trigger as whole word at start
            if text_lower.startswith(trigger + ' ') or text_lower == trigger:
                return True
        return False
