import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from langchain_core.documents import Document

from gpt_researcher.config import Config
from gpt_researcher.context.compression import ContextCompressor
from gpt_researcher.context.retriever import SearchAPIRetriever
from gpt_researcher.prompts import PromptFamily
from gpt_researcher.skills.context_manager import ContextManager


def test_config_default_file_and_env(tmp_path, monkeypatch):
    monkeypatch.delenv("SOURCE_RELIABILITY_WEIGHT", raising=False)
    monkeypatch.delenv("CONFIG_PATH", raising=False)
    assert Config().source_reliability_weight == 0
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"SOURCE_RELIABILITY_WEIGHT": 0.2}))
    assert Config(str(path)).source_reliability_weight == 0.2
    monkeypatch.setenv("SOURCE_RELIABILITY_WEIGHT", "0.1")
    assert Config(str(path)).source_reliability_weight == 0.1
    monkeypatch.setenv("SOURCE_RELIABILITY_WEIGHT", "nan")
    with pytest.raises(ValueError, match="SOURCE_RELIABILITY_WEIGHT"):
        Config(str(path))


async def test_zero_weight_standard_path_preserves_order(monkeypatch):
    docs = [Document(page_content="first", metadata={"source": "https://example.com"}),
            Document(page_content="second", metadata={"source": "https://openai.com"})]
    compressor = ContextCompressor([{"raw_content": "x" * 9000}], None,
                                   source_reliability_weight=0)
    monkeypatch.setattr(compressor, "_ContextCompressor__get_contextual_retriever",
                        lambda: SimpleNamespace(invoke=lambda *a, **k: docs))
    result = await compressor.async_get_context("query")
    assert [e.content for e in result.evidences] == ["first", "second"]
    assert [e.url for e in result.evidences] == [d.metadata["source"] for d in docs]


def test_standard_retriever_source_alias():
    docs = SearchAPIRetriever(pages=[{"source": "https://example.com", "raw_content": "x"}]).invoke("q")
    assert docs[0].metadata["source"] == "https://example.com"


@pytest.mark.parametrize("kwargs,expected_weight", [({}, 0.2), ({"source_reliability_weight": 0.1}, 0.1)])
async def test_context_manager_registers_evidence_and_forwards_weight(monkeypatch, kwargs, expected_weight):
    from gpt_researcher.evidence import EvidenceContext, Evidence
    evidence = Evidence(evidence_id="one", sub_query="q", url="https://openai.com", content="text")
    captured = {}
    def compressor(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(async_get_context=AsyncMock(return_value=EvidenceContext(context="text", evidences=[evidence])))
    monkeypatch.setattr("gpt_researcher.skills.context_manager.ContextCompressor", compressor)
    evidences, assessments = [], []
    researcher = SimpleNamespace(verbose=False, cfg=SimpleNamespace(source_reliability_weight=0.2),
        memory=SimpleNamespace(get_embeddings=lambda: None), prompt_family=PromptFamily, kwargs=kwargs,
        add_costs=lambda c: None, add_evidences=evidences.extend, add_evidence_assessments=assessments.extend)
    await ContextManager(researcher).get_similar_content_by_query("q", [])
    assert captured["source_reliability_weight"] == expected_weight
    assert researcher.kwargs == kwargs
    assert evidences == [evidence]
    assert assessments[0].evidence_id == "one"


async def test_written_context_uses_written_compressor(monkeypatch):
    monkeypatch.setattr("gpt_researcher.skills.context_manager.WrittenContentCompressor",
        lambda **kw: SimpleNamespace(async_get_context=AsyncMock(return_value=["section"])))
    researcher = SimpleNamespace(verbose=False, memory=SimpleNamespace(get_embeddings=lambda: None),
                                 kwargs={}, add_costs=lambda c: None)
    result = await ContextManager(researcher).get_similar_written_contents_by_draft_section_titles("q", [], [])
    assert result == ["section"]
