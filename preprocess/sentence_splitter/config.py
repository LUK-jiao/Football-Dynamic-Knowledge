"""
Configuration for sentence splitting pipeline.
Defines triggers, thresholds, and splitting rules.
"""

# Strong punctuation marks for sentence boundaries
STRONG_PUNCTUATION = {'.', '!', '?'}

# Weak punctuation that may indicate sentence boundaries with context
WEAK_PUNCTUATION = {',', ';', ':'}

# Trigger words that indicate sentence boundary when appearing after weak punctuation
# These are semantic indicators common in sports/news reporting
TRIGGER_WORDS = {
    # Coordinating conjunctions (strong indicators)
    'but', 'and', 'yet', 'so', 'or',
    
    # Time/sequence markers
    'after', 'before', 'during', 'while', 'when', 'then', 'later', 'earlier',
    
    # Action verbs (sports specific)
    'scored', 'saved', 'passed', 'missed', 'won', 'lost', 'drew', 'defeated',
    'announced', 'confirmed', 'stated', 'said', 'added', 'explained', 'revealed',
    'kicked', 'headed', 'assisted', 'defended', 'attacked',
    
    # Transition markers
    'however', 'meanwhile', 'additionally', 'furthermore', 'moreover',
    'therefore', 'consequently', 'nevertheless', 'nonetheless',
    
    # Prepositions indicating new clause
    'with', 'by', 'from', 'to', 'in', 'on', 'at',
    
    # Causal markers
    'because', 'since', 'as', 'although', 'though', 'if', 'unless',
    
    # Result markers
    'resulting', 'leading', 'causing', 'making',
}

# Maximum sentence length before fallback splitting kicks in
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
