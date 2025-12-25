"""
Conflict resolver between rule-based and NLP-based splitting.
Implements explicit decision logic for sentence boundary conflicts.
"""

from typing import List
from . import config


class SplitResolver:
    """Resolve conflicts between rule-based and NLP-based splits."""
    
    def resolve(self, rule_sentences: List[str], nlp_sentences: List[str]) -> List[str]:
        """
        Choose between rule-based and NLP-based splits.
        
        Decision logic:
        1. If NLP results are clearly over-split (too short/fragmentary), reject
        2. If NLP results reduce fact density significantly, accept（not over-split &nlp avg len < rule-based avg len)
        3. Default: prefer rule-based (primary logic)
        
        Args:
            rule_sentences: Sentences from rule splitter
            nlp_sentences: Sentences from NLP splitter
            
        Returns:
            Final chosen sentence list
        """
        # If NLP didn't produce results, use rules
        if not nlp_sentences:
            return rule_sentences
        
        # If rule splitting already fine-grained enough, prefer it,jugde by len，pick the one with more sentences
        if len(rule_sentences) >= len(nlp_sentences):
            return rule_sentences
        
        # Check if NLP over-split (created fragments),controlled by config.INVALID_START_WORDS
        if self._is_over_split(nlp_sentences):
            return rule_sentences
        
        # Check if NLP split genuinely helps reduce fact density
        if self._reduces_fact_density(rule_sentences, nlp_sentences):
            return nlp_sentences
        
        # Default: prefer rule-based
        return rule_sentences
    
    def _is_over_split(self, sentences: List[str]) -> bool:
        """
        Check if sentences appear over-split (fragments).
        
        Indicators:
        - Too many very short sentences
        - Sentences starting with invalid words
        - Sentences without verbs (heuristic: too few tokens)
        """
        if not sentences:
            return False
        
        # Count problematic sentences
        fragment_count = 0
        
        for sent in sentences:
            # Too short
            if len(sent) < config.MIN_SENTENCE_LENGTH:
                fragment_count += 1
                continue
            
            # Too few tokens
            tokens = sent.split()
            if len(tokens) < config.MIN_TOKENS:
                fragment_count += 1
                continue
            
            # Starts with invalid word
            first_word = tokens[0].lower().rstrip('.,;:!?')
            if first_word in config.INVALID_START_WORDS:
                fragment_count += 1
        
        # If more than 30% are fragments, consider over-split
        fragment_ratio = fragment_count / len(sentences)
        return fragment_ratio > 0.3
    
    def _reduces_fact_density(self, rule_sents: List[str], nlp_sents: List[str]) -> bool:
        """
        Check if NLP splitting genuinely reduces fact density.
        
        Heuristic: If NLP produces significantly shorter sentences on average,
        it may be splitting compound facts better.
        """
        if not rule_sents or not nlp_sents:
            return False
        
        rule_avg_len = sum(len(s) for s in rule_sents) / len(rule_sents)
        nlp_avg_len = sum(len(s) for s in nlp_sents) / len(nlp_sents)
        
        # If NLP sentences are significantly shorter
        # (suggests better fact separation)
        if nlp_avg_len < rule_avg_len * config.NLP_PREFERENCE_RATIO:
            # But not if they're creating fragments
            if not self._is_over_split(nlp_sents):
                return True
        
        return False
