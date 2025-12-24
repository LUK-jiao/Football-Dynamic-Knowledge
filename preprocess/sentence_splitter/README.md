# Sentence Splitter Module

Production-grade sentence splitting system for fact extraction from sports news and reports.

## Architecture

```
Original Paragraph
    ↓
[1] Rule-based Splitting (PRIMARY)
    ↓
[2] NLP Validation (spaCy)
    ↓
[3] Conflict Resolution
    ↓
[4] Fallback Length Splitting
    ↓
[5] Output Cleaning
    ↓
Fact-oriented Sentences
```

## Installation

### Required Dependencies

```bash
pip install beautifulsoup4 lxml
```

### Optional (for NLP validation)

```bash
pip install spacy
python -m spacy download en_core_web_sm
```

## Usage

### Basic Usage

```python
from sentence_splitter import SentenceSplitter

splitter = SentenceSplitter()
text = "Arsenal won 8-7 on penalties, with Kepa saving the decisive spot-kick."
sentences = splitter.split(text)
# Output: ['Arsenal won 8-7 on penalties.', 'Kepa saved the decisive spot-kick.']
```

### Without NLP Layer

```python
splitter = SentenceSplitter(use_nlp=False)
```

### Batch Processing

```python
texts = ["Paragraph 1...", "Paragraph 2..."]
results = splitter.split_batch(texts)
```

## Module Structure

### `config.py`
Configuration for triggers, thresholds, and rules.

### `rule_splitter.py`
Primary splitting logic using:
- Strong punctuation (. ! ?)
- Weak punctuation + trigger words (, ; :)

### `nlp_splitter.py`
spaCy-based validation layer for complex sentences.

### `resolver.py`
Conflict resolution between rule and NLP splits:
- Detects NLP over-splitting
- Evaluates fact density reduction
- Defaults to rule-based output

### `fallback.py`
Force-splits sentences exceeding max length:
- Tries natural boundaries first
- Preserves semantic integrity

### `cleaner.py`
Output normalization:
- Whitespace normalization
- Punctuation fixes
- Duplicate removal

### `splitter.py`
Unified interface orchestrating the complete pipeline.

## Configuration

Edit `config.py` to customize:

```python
MAX_SENTENCE_LENGTH = 100      # Force split threshold
MIN_SENTENCE_LENGTH = 10       # Minimum valid length
TRIGGER_WORDS = {...}          # Semantic boundary markers
```

## Testing

```bash
cd preprocess
python -m sentence_splitter.example
```

## Design Principles

1. **Rule-based Primary**: NLP is validation only, not primary logic
2. **Explicit Resolution**: Clear decision logic for conflicts
3. **Fact-oriented**: Each sentence should contain ≤2 facts
4. **Fallback Safety**: No sentence exceeds max length
5. **Production Ready**: Handles edge cases, clean output

## Output Characteristics

- Single-fact sentences preferred
- Grammatical correctness not required
- Optimized for NER and event extraction
- Consistent punctuation and spacing
- No duplicates or fragments
