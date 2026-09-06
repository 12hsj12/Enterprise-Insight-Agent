from urllib.parse import urlparse

from .models import Evidence, EvidenceAssessment
from .source_rules import (
    AUTHORITATIVE_DOMAINS,
    AUTHORITY_SCORES,
    OFFICIAL_DOMAINS,
)


class EvidenceReliabilityEvaluator:
    """Evaluate source reliability for structured evidence."""

    def classify_source_type(self, url: str) -> str:
        domain = urlparse(url).netloc.lower().removeprefix("www.")

        if any(domain == d or domain.endswith(f".{d}") for d in OFFICIAL_DOMAINS):
            return "official"

        if any(domain == d or domain.endswith(f".{d}") for d in AUTHORITATIVE_DOMAINS):
            return "authoritative_media"

        if domain:
            return "web"

        return "unknown"

    def get_authority_score(self, source_type: str) -> float:
        return AUTHORITY_SCORES.get(
            source_type,
            AUTHORITY_SCORES["unknown"],
        )

    def evaluate(self, evidence: Evidence) -> EvidenceAssessment:
        source_type = self.classify_source_type(evidence.url)

        return EvidenceAssessment(
            evidence_id=evidence.evidence_id,
            source_type=source_type,
            authority_score=self.get_authority_score(source_type),
            freshness_score=None,
        )