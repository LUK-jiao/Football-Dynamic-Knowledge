"""
Sports-aware rule adjuster (POST-PROCESSING only).
Fixes NLP blind spots specific to English sports news.
Rules can only merge/adjust NLP output, NOT override segmentation.
"""

import re
from typing import List
from . import config


class SportsRuleAdjuster:
    """
    Post-processing rules for sports news specific patterns.
    
    Purpose: Fix NLP mistakes in sports-specific contexts
    Constraint: Can only merge/adjust, NOT re-segment
    
    Handles:
    - Abbreviations: U.S., No., Dr., vs.
    - Scores: won 3-2, beat them 5-0
    - Time markers: in the 78th minute
    - Stats: shooting 5-of-8, 48.3% from field
    - Quotes: preserve complete quoted statements
    """
    
    def __init__(self):
        self.sports_abbreviations = config.SPORTS_ABBREVIATIONS
        self.score_patterns = config.SCORE_PATTERNS
        
    def adjust(self, sentences: List[str], original_text: str = "") -> List[str]:
        """
        Apply sports-specific adjustments to NLP output.
        
        Args:
            sentences: Sentences from NLP splitter
            original_text: Original input (for context)
            
        Returns:
            Adjusted sentence list
        """
        if not sentences:
            return sentences
        
        # 1. Merge broken abbreviations
        sentences = self._merge_abbreviation_splits(sentences)
        
        # 2. Merge broken quotes
        sentences = self._merge_incomplete_quotes(sentences)
        
        # 3. Merge broken scores/stats
        sentences = self._merge_broken_scores(sentences)
        
        # 4. Fix time/date fragments
        sentences = self._merge_time_fragments(sentences)
        
        return sentences
    
    def _merge_abbreviation_splits(self, sentences: List[str]) -> List[str]:
        """
        Merge sentences incorrectly split at abbreviations.
        
        Example fix:
        ["The U.", "S. team won."] → ["The U.S. team won."]
        """
        if len(sentences) <= 1:
            return sentences
        
        result = []
        i = 0
        
        while i < len(sentences):
            current = sentences[i]
            
            # Check if current ends with common abbreviation pattern
            if i + 1 < len(sentences) and self._ends_with_abbrev(current):
                # Merge with next
                next_sent = sentences[i + 1]
                merged = current + " " + next_sent
                result.append(merged)
                i += 2
            else:
                result.append(current)
                i += 1
        
        return result
    
    def _ends_with_abbrev(self, text: str) -> bool:
        """Check if text ends with incomplete abbreviation."""
        # Common abbreviations that might be split
        abbrev_patterns = [
            r'\b[A-Z]\.$',  # Single letter abbrev: U., A., etc.
            r'\bNo\.$',     # Number abbreviation
            r'\bDr\.$',     # Doctor
            r'\bMr\.$',     # Mister
            r'\bMs\.$',     # Miss
            r'\bvs\.$',     # versus
            r'\bSt\.$',     # Saint
        ]
        
        for pattern in abbrev_patterns:
            if re.search(pattern, text):
                return True
        return False
    
    def _merge_incomplete_quotes(self, sentences: List[str]) -> List[str]:
        """
        Merge sentences that break quoted statements.
        
        Example fix:
        ['He said "we played well', 'and deserved to win."']
        → ['He said "we played well and deserved to win."']
        """
        if len(sentences) <= 1:
            return sentences
        
        result = []
        i = 0
        
        while i < len(sentences):
            current = sentences[i]
            
            # Check if current has unmatched opening quote
            if self._has_unmatched_quote(current) and i + 1 < len(sentences):
                # Merge with next sentences until quote closes
                merged = current
                i += 1
                while i < len(sentences):
                    merged += " " + sentences[i]
                    if self._quote_is_closed(merged):
                        break
                    i += 1
                result.append(merged)
                i += 1
            else:
                result.append(current)
                i += 1
        
        return result
    
    def _has_unmatched_quote(self, text: str) -> bool:
        """Check if text has unmatched opening quote."""
        # Count quotes
        double_quotes = text.count('"')
        single_quotes = text.count("'")
        
        # Check for opening quotes (various quote types)
        has_opening = '"' in text or "'" in text
        
        # Simple heuristic: odd number of quotes suggests unmatched
        return has_opening and (double_quotes % 2 == 1)
    
    def _quote_is_closed(self, text: str) -> bool:
        """Check if all quotes in text are closed."""
        double_quotes = text.count('"')
        return double_quotes % 2 == 0
    
    def _merge_broken_scores(self, sentences: List[str]) -> List[str]:
        """
        Merge sentences broken at score markers.
        
        Example fix:
        ["They won", "3-2 on penalties."] → ["They won 3-2 on penalties."]
        """
        if len(sentences) <= 1:
            return sentences
        
        result = []
        i = 0
        
        while i < len(sentences):
            current = sentences[i]
            
            # Check if next sentence starts with score pattern
            if i + 1 < len(sentences):
                next_sent = sentences[i + 1]
                if self._starts_with_score(next_sent):
                    # Merge
                    merged = current + " " + next_sent
                    result.append(merged)
                    i += 2
                    continue
            
            result.append(current)
            i += 1
        
        return result
    
    def _starts_with_score(self, text: str) -> bool:
        """Check if text starts with a score pattern."""
        score_patterns = [
            r'^\d+-\d+',  # 3-2, 5-0
            r'^\d+–\d+',  # 3–2 (em dash)
            r'^\d+\s*-\s*\d+',  # 3 - 2
            r'^\d+\.\d+%',  # 48.3%
            r'^\d+-of-\d+',  # 5-of-8
        ]
        
        for pattern in score_patterns:
            if re.match(pattern, text.strip()):
                return True
        return False
    
    def _merge_time_fragments(self, sentences: List[str]) -> List[str]:
        """
        Merge time/date fragments incorrectly split.
        
        Example fix:
        ["in the 78th", "minute"] → ["in the 78th minute"]
        """
        if len(sentences) <= 1:
            return sentences
        
        result = []
        i = 0
        
        while i < len(sentences):
            current = sentences[i]
            
            # Check if ends with ordinal number (78th, 2nd, etc.)
            if i + 1 < len(sentences) and re.search(r'\d+(st|nd|rd|th)$', current):
                next_sent = sentences[i + 1]
                # Check if next is time unit
                if next_sent.lower().startswith(('minute', 'second', 'hour', 'day')):
                    merged = current + " " + next_sent
                    result.append(merged)
                    i += 2
                    continue
            
            result.append(current)
            i += 1
        
        return result
