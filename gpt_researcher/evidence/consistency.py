from .models import (
    ClaimEvidenceLink,
    Evidence,
    EvidenceConsistencyAssessment,
)


class EvidenceConsistencyEvaluator:
    """Evaluate consistency relationships across multiple evidences."""

    def evaluate(
        self,
        evidences: list[Evidence],
        links: list[ClaimEvidenceLink] | None = None,
    ) -> EvidenceConsistencyAssessment:
        evidence_ids = [evidence.evidence_id for evidence in evidences]

        if not links:
            return EvidenceConsistencyAssessment(
                evidence_ids=evidence_ids,
                status="insufficient",
            )

        valid_evidence_ids = set(evidence_ids)

        supporting_ids = [
            link.evidence_id
            for link in links
            if link.relation == "support"
            and link.evidence_id in valid_evidence_ids
        ]

        conflicting_ids = [
            link.evidence_id
            for link in links
            if link.relation == "conflict"
            and link.evidence_id in valid_evidence_ids
        ]

        evidence_by_id = {
            evidence.evidence_id: evidence
            for evidence in evidences
        }

        supporting_urls = {
            evidence_by_id[evidence_id].url
            for evidence_id in supporting_ids
            if evidence_by_id[evidence_id].url
        }

        if conflicting_ids:
            status = "conflict"
        elif len(supporting_urls) >= 2:
            status = "supported"
        else:
            status = "insufficient"

        return EvidenceConsistencyAssessment(
            evidence_ids=evidence_ids,
            status=status,
            supporting_evidence_ids=supporting_ids,
            conflicting_evidence_ids=conflicting_ids,
        )