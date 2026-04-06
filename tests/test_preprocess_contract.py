from preprocess.sentence_splitter import SentenceSplitter
from preprocess.semantic_blocker.semantic_chunker import SemanticChunker, ChunkerConfig, LLMBackend


class _DeterministicLLM(LLMBackend):
    def score_boundary(self, current_sentence, previous_sentences):
        return (0.1, True)


def _article_document():
    return {
        "doc_id": "news-42",
        "title": "Arsenal update",
        "raw_text": "Arsenal won the match. Saka scored a goal. The manager praised the team.",
        "source_name": "BBC Sport",
        "source_type": "MEDIA",
        "publish_date": "2025-01-14",
        "author": "Reporter",
        "metadata": {"created_time": "2025-01-15T00:00:00"},
    }


def test_split_document_returns_prechunk_inputs():
    splitter = SentenceSplitter(min_length=5)
    units = splitter.split_document(_article_document())

    assert len(units) >= 2
    assert units[0].sentence_id.startswith("news-42-s")
    assert units[0].sentence_order == 1
    assert units[0].sentence_text


def test_chunk_document_returns_semantic_chunk_documents():
    splitter = SentenceSplitter(min_length=5)
    prechunk_inputs = splitter.split_document(_article_document())

    chunker = SemanticChunker(llm=_DeterministicLLM(), config=ChunkerConfig(max_sentences_per_chunk=5))
    docs = chunker.chunk_document(_article_document(), prechunk_inputs)

    assert len(docs) == 1
    assert docs[0].doc_id == "news-42"
    assert docs[0].block_id.startswith("news-42-block")
    assert docs[0].block_text
    payload = docs[0].to_event_decomposition_input()
    assert payload["source_name"] == "BBC Sport"
    assert payload["source_type"] == "MEDIA"
    assert payload["author"] == "Reporter"
