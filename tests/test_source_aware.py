import pytest

from gpt_researcher.context.source_aware import SourceAwareScorer

from langchain_core.documents import Document
from langchain_community.document_transformers.embeddings_redundant_filter import (
    get_stateful_documents,
)


def test_official_source_gets_higher_score_than_web():
    scorer = SourceAwareScorer(reliability_weight=0.2)

    official = scorer.score(
        similarity_score=0.8,
        url="https://openai.com/research/test",
    )
    web = scorer.score(
        similarity_score=0.8,
        url="https://example.com/test",
    )

    assert official.authority_score == 1.0
    assert web.authority_score == 0.6
    assert official.final_score > web.final_score


def test_similarity_remains_primary_signal():
    scorer = SourceAwareScorer(reliability_weight=0.2)

    highly_relevant_web = scorer.score(
        similarity_score=0.9,
        url="https://example.com/test",
    )
    weakly_relevant_official = scorer.score(
        similarity_score=0.5,
        url="https://openai.com/test",
    )

    assert highly_relevant_web.final_score > weakly_relevant_official.final_score


def test_zero_weight_matches_embedding_baseline():
    scorer = SourceAwareScorer(reliability_weight=0.0)

    result = scorer.score(
        similarity_score=0.73,
        url="https://openai.com/test",
    )

    assert result.final_score == pytest.approx(0.73)


def test_invalid_reliability_weight_raises_error():
    with pytest.raises(ValueError):
        SourceAwareScorer(reliability_weight=1.1)


def test_rank_documents_prefers_more_reliable_source_when_similarity_is_equal():
    scorer = SourceAwareScorer(reliability_weight=0.2)

    docs = get_stateful_documents([
        Document(
            page_content="web",
            metadata={"source": "https://example.com/test"},
        ),
        Document(
            page_content="official",
            metadata={"source": "https://openai.com/test"},
        ),
    ])

    for doc in docs:
        doc.state["query_similarity_score"] = 0.8

    ranked = scorer.rank_documents(docs)

    assert ranked[0].page_content == "official"
    assert ranked[1].page_content == "web"


def test_rank_documents_keeps_similarity_as_primary_signal():
    scorer = SourceAwareScorer(reliability_weight=0.2)

    docs = get_stateful_documents([
        Document(
            page_content="high_similarity_web",
            metadata={"source": "https://example.com/test"},
        ),
        Document(
            page_content="low_similarity_official",
            metadata={"source": "https://openai.com/test"},
        ),
    ])

    docs[0].state["query_similarity_score"] = 0.9
    docs[1].state["query_similarity_score"] = 0.5

    ranked = scorer.rank_documents(docs)

    assert ranked[0].page_content == "high_similarity_web"


def test_rank_documents_rejects_missing_similarity_score():
    scorer = SourceAwareScorer(reliability_weight=0.2)

    docs = get_stateful_documents([
        Document(
            page_content="missing_score",
            metadata={"source": "https://openai.com/test"},
        )
    ])

    with pytest.raises(ValueError, match="query_similarity_score"):
        scorer.rank_documents(docs)


@pytest.mark.asyncio
async def test_context_compressor_applies_source_aware_reranking(monkeypatch):
    from gpt_researcher.context.compression import ContextCompressor

    docs = get_stateful_documents([
        Document(
            page_content="web evidence",
            metadata={"source": "https://example.com/test"},
        ),
        Document(
            page_content="official evidence",
            metadata={"source": "https://openai.com/test"},
        ),
    ])

    for doc in docs:
        doc.state["query_similarity_score"] = 0.8

    class FakeRetriever:
        def invoke(self, query, **kwargs):
            return docs

    compressor = ContextCompressor(
        documents=[
            {
                "raw_content": "x" * 9000,
                "url": "https://example.com/raw",
            }
        ],
        embeddings=None,
        max_results=2,
        source_reliability_weight=0.2,
    )

    monkeypatch.setattr(
        compressor,
        "_ContextCompressor__get_contextual_retriever",
        lambda: FakeRetriever(),
    )

    result = await compressor.async_get_context(
        query="test query",
        max_results=2,
    )

    assert result.evidences[0].url == "https://openai.com/test"
    assert result.evidences[1].url == "https://example.com/test"


@pytest.mark.asyncio
async def test_baseline_keeps_fast_path(monkeypatch):
    from gpt_researcher.context.compression import ContextCompressor

    compressor = ContextCompressor(
        documents=[
            {
                "raw_content": "small document",
                "title": "Test",
                "url": "https://example.com/test",
            }
        ],
        embeddings=None,
        max_results=5,
        source_reliability_weight=0.0,
    )

    def fail_if_called():
        raise AssertionError("standard compression path should not be used")

    monkeypatch.setattr(
        compressor,
        "_ContextCompressor__get_contextual_retriever",
        fail_if_called,
    )

    result = await compressor.async_get_context(
        query="test query",
        max_results=5,
    )

    assert len(result.evidences) == 1
    assert result.evidences[0].url == "https://example.com/test"


@pytest.mark.asyncio
async def test_source_aware_mode_bypasses_fast_path(monkeypatch):
    from gpt_researcher.context.compression import ContextCompressor

    docs = get_stateful_documents([
        Document(
            page_content="official evidence",
            metadata={"source": "https://openai.com/test"},
        )
    ])
    docs[0].state["query_similarity_score"] = 0.8

    class FakeRetriever:
        def invoke(self, query, **kwargs):
            return docs

    compressor = ContextCompressor(
        documents=[
            {
                "raw_content": "small document",
                "title": "Test",
                "url": "https://example.com/test",
            }
        ],
        embeddings=None,
        max_results=5,
        source_reliability_weight=0.2,
    )

    monkeypatch.setattr(
        compressor,
        "_ContextCompressor__get_contextual_retriever",
        lambda: FakeRetriever(),
    )

    result = await compressor.async_get_context(
        query="test query",
        max_results=5,
    )

    assert len(result.evidences) == 1
    assert result.evidences[0].url == "https://openai.com/test"