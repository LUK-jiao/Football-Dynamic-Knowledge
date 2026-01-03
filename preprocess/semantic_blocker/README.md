# Semantic Blocker - LLM-Based Event Aggregation

## Overview

LLM-based semantic aggregation module for football news. Groups sentences into coherent event blocks using intelligent language models.

## Key Features

- **LLM-Powered**: Uses OpenAI GPT or DeepSeek for intelligent grouping
- **Event-Aware**: Understands football events (goals, transfers, quotes, etc.)
- **Strict Constraints**: LLM only groups, never rewrites or summarizes
- **Sliding Window**: Processes 10-15 sentences at a time for efficiency
- **Robust Validation**: Ensures output integrity and completeness

## Quick Start

```python
from preprocess.semantic_blocker import llm_semantic_chunk

# Split text into sentences first
sentences = [
    "Arsenal won 2-1 against Chelsea.",
    "Saka scored in the 23rd minute.",
    "Arteta said: 'I'm proud of the team.'"
]

# Group into semantic blocks
blocks = llm_semantic_chunk(
    sentences,
    model="gpt-4o-mini",  # or "deepseek-chat"
    window_size=15
)

# Each block contains:
# - event_type: "match_result", "goal", "manager_quote", etc.
# - sentences: list of sentences
# - confidence: float 0-1
# - anchor_index: main sentence index
```

## Configuration

Set your API key:

```bash
# For OpenAI
export OPENAI_API_KEY="sk-..."

# Or for DeepSeek
export DEEPSEEK_API_KEY="sk-..."
```

## API

### `llm_semantic_chunk(sentences, model, api_key, window_size, max_retries)`

Main entry point for LLM-based aggregation.

**Parameters:**
- `sentences` (List[str]): Input sentences
- `model` (str): "gpt-4o-mini", "gpt-3.5-turbo", or "deepseek-chat"
- `api_key` (str, optional): API key (uses env var if not provided)
- `window_size` (int): Sentences per LLM call (default: 15)
- `max_retries` (int): Retry attempts on failure (default: 3)

**Returns:**
- List[dict]: Semantic blocks with event_type, sentences, confidence, etc.

### `LLMEventAggregator`

Low-level class for advanced usage.

```python
from preprocess.semantic_blocker import LLMEventAggregator

aggregator = LLMEventAggregator(
    model="gpt-4o-mini",
    api_key="sk-...",
    window_size=15
)

blocks = aggregator.aggregate(sentences)
```

## How It Works

1. **Sliding Window**: Splits sentences into overlapping windows (10-15 sentences)
2. **LLM Call**: Sends to GPT/DeepSeek with strict grouping-only prompt
3. **Validation**: Checks sentence coverage, no duplicates, valid event types
4. **Merge**: Combines results from all windows

## Strict Constraints

The LLM is constrained to:
- ✅ **Only group** sentences by same event
- ❌ **Never rewrite** or rephrase
- ❌ **Never summarize** or compress
- ❌ **Never invent** facts
- ❌ **Never extract** entities

## Event Types

Supports 9 main event types:
- `match_result`: Final scores and outcomes
- `goal`: Goal descriptions
- `penalty_shootout`: Penalty outcomes
- `manager_quote`: Coach/player interviews
- `player_performance`: Individual stats
- `fixture`: Upcoming matches
- `injury`: Injury updates
- `transfer`: Transfer news
- `general`: Other football events

## Testing

```bash
# Test the aggregator
python preprocess/semantic_blocker/test_llm_aggregator.py
```

## Architecture

```
sentences (list)
    ↓
llm_semantic_chunk()
    ↓
LLMEventAggregator
    ↓
_chunk_with_sliding_window()
    ↓
_call_llm() → GPT/DeepSeek API
    ↓
_validate_output()
    ↓
semantic blocks (list)
```

## Output Format

```python
{
    'event_type': 'goal',
    'sentences': [
        "Saka scored in the 23rd minute.",
        "It was a brilliant strike from outside the box."
    ],
    'confidence': 0.85,
    'anchor_index': 0,
    'length': 89,
    'metadata': {
        'method': 'llm',
        'model': 'gpt-4o-mini'
    }
}
```

## Error Handling

- **API Failure**: Retries with exponential backoff
- **Invalid JSON**: Logs error and returns empty block
- **Missing Sentences**: Validation catches coverage issues

## Performance

- **Speed**: ~2-3 seconds per 15 sentences (gpt-4o-mini)
- **Quality**: Superior to rule-based, better pronoun resolution
- **Cost**: ~$0.001 per 15 sentences (gpt-4o-mini)

## Dependencies

```
openai>=1.0.0
python-dotenv (optional, for .env files)
```
