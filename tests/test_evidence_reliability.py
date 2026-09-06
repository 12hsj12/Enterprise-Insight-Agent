from gpt_researcher.evidence.models import Evidence
from gpt_researcher.evidence.reliability import EvidenceReliabilityEvaluator


def test_official_domain_is_classified_correctly():
    evaluator = EvidenceReliabilityEvaluator()

    evidence = Evidence(
        evidence_id="ev_official",
        sub_query="test",
        title="OpenAI",
        url="https://openai.com/research",
        content="test content",
    )

    assessment = evaluator.evaluate(evidence)

    assert assessment.source_type == "official"
    assert assessment.authority_score == 1.0
    assert assessment.freshness_score is None


def test_authoritative_media_is_classified_correctly():
    evaluator = EvidenceReliabilityEvaluator()

    evidence = Evidence(
        evidence_id="ev_media",
        sub_query="test",
        title="Reuters",
        url="https://www.reuters.com/technology/example",
        content="test content",
    )

    assessment = evaluator.evaluate(evidence)

    assert assessment.source_type == "authoritative_media"
    assert assessment.authority_score == 0.85


def test_unknown_web_domain_falls_back_to_web():
    evaluator = EvidenceReliabilityEvaluator()

    evidence = Evidence(
        evidence_id="ev_web",
        sub_query="test",
        title="Example",
        url="https://example.com/article",
        content="test content",
    )

    assessment = evaluator.evaluate(evidence)

    assert assessment.source_type == "web"
    assert assessment.authority_score == 0.6


def test_missing_url_is_unknown():
    evaluator = EvidenceReliabilityEvaluator()

    evidence = Evidence(
        evidence_id="ev_unknown",
        sub_query="test",
        content="test content",
    )

    assessment = evaluator.evaluate(evidence)

    assert assessment.source_type == "unknown"
    assert assessment.authority_score == 0.3


def test_researcher_can_store_evidence_assessments():
    from gpt_researcher.agent import GPTResearcher

    researcher = object.__new__(GPTResearcher)
    researcher.evidence_assessments = []

    evaluator = EvidenceReliabilityEvaluator()
    evidence = Evidence(
        evidence_id="ev_store",
        sub_query="test",
        url="https://openai.com/research",
        content="test content",
    )

    assessment = evaluator.evaluate(evidence)
    researcher.add_evidence_assessments([assessment])

    stored = researcher.get_evidence_assessments()

    assert len(stored) == 1
    assert stored[0].evidence_id == "ev_store"
    assert stored[0].source_type == "official"
    assert stored[0].authority_score == 1.0


def test_official_subdomain_is_classified_correctly():
    evaluator = EvidenceReliabilityEvaluator()

    evidence = Evidence(
        evidence_id="ev_subdomain",
        sub_query="test",
        url="https://research.openai.com/example",
        content="test content",
    )

    assessment = evaluator.evaluate(evidence)

    assert assessment.source_type == "official"
    assert assessment.authority_score == 1.0


def test_deceptive_domain_is_not_classified_as_official():
    evaluator = EvidenceReliabilityEvaluator()

    evidence = Evidence(
        evidence_id="ev_fake",
        sub_query="test",
        url="https://fakeopenai.com/article",
        content="test content",
    )

    assessment = evaluator.evaluate(evidence)

    assert assessment.source_type == "web"
    assert assessment.authority_score == 0.6


def test_malformed_url_falls_back_to_unknown():
    evaluator = EvidenceReliabilityEvaluator()

    evidence = Evidence(
        evidence_id="ev_malformed",
        sub_query="test",
        url="not-a-valid-url",
        content="test content",
    )

    assessment = evaluator.evaluate(evidence)

    assert assessment.source_type == "unknown"
    assert assessment.authority_score == 0.3