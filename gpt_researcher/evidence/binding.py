"""Deterministic assembly of explicit claim/evidence relationships."""

from collections.abc import Iterable

from .models import Claim, ClaimEvidenceLink, ClaimSupportSummary, Evidence


class ClaimEvidenceBinder:
    """Validate IDs, deduplicate exact links, and summarize relations.

    The binder does not infer a relation, source independence, evidence strength,
    or a gate action. Callers must supply every relation explicitly.
    """

    _RELATION_ORDER = {"support": 0, "conflict": 1, "unclear": 2}

    def __init__(self, claims: Iterable[Claim], evidences: Iterable[Evidence]):
        self._claims = self._unique_by_id(claims, "claim_id", "claim")
        self._evidences = self._unique_by_id(evidences, "evidence_id", "evidence")

    @staticmethod
    def _unique_by_id(items, id_field: str, label: str) -> dict:
        indexed = {}
        for item in items:
            item_id = getattr(item, id_field)
            previous = indexed.get(item_id)
            if previous is not None and previous != item:
                raise ValueError(f"Conflicting {label} objects share {id_field}={item_id!r}")
            indexed[item_id] = item
        return indexed

    def bind(
        self,
        claim_id: str,
        evidence_id: str,
        relation: str,
    ) -> ClaimEvidenceLink:
        """Build one validated explicit link between registered objects."""

        if claim_id not in self._claims:
            raise ValueError(f"Unknown claim_id: {claim_id}")
        if evidence_id not in self._evidences:
            raise ValueError(f"Unknown evidence_id: {evidence_id}")
        return ClaimEvidenceLink(
            claim_id=claim_id,
            claim=self._claims[claim_id].normalized_text,
            evidence_id=evidence_id,
            relation=relation,
        )

    def bind_many(
        self,
        links: Iterable[ClaimEvidenceLink],
    ) -> list[ClaimEvidenceLink]:
        """Validate, exactly deduplicate, and canonically order supplied links."""

        unique = {}
        for link in links:
            validated = self.bind(link.claim_id, link.evidence_id, link.relation)
            key = (validated.claim_id, validated.evidence_id, validated.relation)
            unique[key] = validated
        return sorted(
            unique.values(),
            key=lambda link: (
                link.claim_id,
                link.evidence_id,
                self._RELATION_ORDER[link.relation],
            ),
        )

    def summarize(
        self,
        links: Iterable[ClaimEvidenceLink],
    ) -> list[ClaimSupportSummary]:
        """Return one descriptive support summary for every registered claim."""

        validated = self.bind_many(links)
        by_claim: dict[str, dict[str, list[str]]] = {
            claim_id: {"support": [], "conflict": [], "unclear": []}
            for claim_id in self._claims
        }
        for link in validated:
            by_claim[link.claim_id][link.relation].append(link.evidence_id)

        return [
            ClaimSupportSummary(
                claim_id=claim_id,
                supporting_evidence_ids=tuple(relations["support"]),
                conflicting_evidence_ids=tuple(relations["conflict"]),
                unclear_evidence_ids=tuple(relations["unclear"]),
                has_valid_support=bool(relations["support"]),
            )
            for claim_id, relations in sorted(by_claim.items())
        ]
