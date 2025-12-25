"""
Configuration for sentence splitting pipeline.
Refactored for NLP-first, sports-aware architecture.
"""

# ============================================================================
# NLP Configuration
# ============================================================================

# spaCy model to use (PRIMARY splitting engine)
SPACY_MODEL = "en_core_web_sm"  # Change to "en_core_web_trf" for better accuracy

# ============================================================================
# Sports-Specific Rules (POST-PROCESSING only)
# ============================================================================

# Sports abbreviations that should NOT trigger splits
SPORTS_ABBREVIATIONS = {
    'U.S.', 'U.K.', 'vs.', 'No.', 'Dr.', 'Mr.', 'Ms.', 'St.',
    'Jr.', 'Sr.', 'Inc.', 'Ltd.', 'Co.', 'Corp.',
    'UEFA', 'FIFA', 'NBA', 'NFL', 'MLB', 'NHL',
}

# Score patterns (for merge detection)
SCORE_PATTERNS = [
    r'\d+-\d+',  # 3-2, 5-0
    r'\d+–\d+',  # 3–2 (em dash)
    r'\d+\s*-\s*\d+',  # 3 - 2
    r'\d+\.\d+%',  # 48.3%
    r'\d+-of-\d+',  # 5-of-8
    r'\d+:\d+',  # 2:1 (another score format)
]

# Time markers that shouldn't be split
TIME_MARKERS = {
    'minute', 'minutes', 'second', 'seconds', 'hour', 'hours',
    'day', 'days', 'week', 'weeks', 'month', 'months', 'year', 'years',
}

# ============================================================================
# Fallback Splitting Configuration
# ============================================================================

# Maximum sentence length before fallback splitting kicks in
# Set higher for NLP-first architecture (trust NLP more)
MAX_SENTENCE_LENGTH = 150  # Increased from 100

# Minimum sentence length to be considered valid
MIN_SENTENCE_LENGTH = 10

# Minimum tokens required for a valid sentence
MIN_TOKENS = 3

# ============================================================================
# Cleaning Configuration
# ============================================================================

# Words that should not start a sentence (likely fragments)
INVALID_START_WORDS = {'and', 'but', 'or', 'with', 'by', 'after'}

# ============================================================================
# Legacy configurations (kept for backwards compatibility)
# ============================================================================

# Strong punctuation marks for sentence boundaries
STRONG_PUNCTUATION = {'.', '!', '?'}

# Weak punctuation that may indicate sentence boundaries with context
WEAK_PUNCTUATION = {',', ';', ':'}

# Trigger words (mostly deprecated in NLP-first architecture)
TRIGGER_WORDS = {
    'but', 'however', 'meanwhile', 'therefore', 'consequently',
    'nevertheless', 'nonetheless',
}

# NLP preference ratio (deprecated - NLP is now primary)
NLP_PREFERENCE_RATIO = 0.6

# Maximum facts per sentence (heuristic)
MAX_FACTS_PER_SENTENCE = 2

MAX_SENTENCE_LENGTH = 100

# Minimum sentence length to be considered valid
MIN_SENTENCE_LENGTH = 10

# Threshold for considering NLP split over rule split
# If NLP produces sentences with avg length significantly shorter, may prefer it
NLP_PREFERENCE_RATIO = 0.6  # NLP avg < ratio * Rule avg

# Minimum tokens required for a valid sentence
MIN_TOKENS = 3

# Words that should not start a sentence (likely fragments)
INVALID_START_WORDS = {'and', 'but', 'or', 'with', 'by', 'after'}

# Maximum number of facts per sentence (heuristic based on conjunctions)
MAX_FACTS_PER_SENTENCE = 2
