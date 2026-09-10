"""Deterministic, classifier-independent claim evidence-strength enforcement."""

from __future__ import annotations

from collections.abc import Iterable
from types import MappingProxyType
from typing import Mapping

from .binding import ClaimEvidenceBinder
from .models import (
    Claim,
    ClaimEvidenceLink,
    ClaimEvidenceQualification,
    ClaimGateContext,
    ClaimGateDecision,
    ClaimGateReasonCode,
    ClaimGateResult,
    ClaimRiskType,
    Evidence,
    EvidenceStrengthRule,
    ResolvedClaimGateObligations,
)


RISK_MINIMUM_RULES: Mapping[ClaimRiskType, EvidenceStrengthRule] = MappingProxyType(
    {
        ClaimRiskType.NUMERIC_VALUE: (
            EvidenceStrengthRule.PRIMARY_OR_TWO_INDEPENDENT
        ),
        ClaimRiskType.DATE_OR_TIME_WINDOW: (
            EvidenceStrengthRule.PRIMARY_OR_TWO_INDEPENDENT
        ),
        ClaimRiskType.RELEASE_STATUS_AVAILABILITY: (
            EvidenceStrengthRule.PRIMARY_OR_TWO_INDEPENDENT
        ),
        ClaimRiskType.COMPARATIVE_CLAIM: EvidenceStrengthRule.TWO_INDEPENDENT,
        ClaimRiskType.SUPERLATIVE_OR_RANKING: EvidenceStrengthRule.TWO_INDEPENDENT,
        ClaimRiskType.MARKET_METRIC: (
            EvidenceStrengthRule.PRIMARY_OR_TWO_INDEPENDENT
        ),
        ClaimRiskType.BENCHMARK_OR_PERFORMANCE: (
            EvidenceStrengthRule.PRIMARY_PLUS_INDEPENDENT
        ),
        ClaimRiskType.CONFLICT_SENSITIVE_CLAIM: (
            EvidenceStrengthRule.CONFLICT_SIDES_PLUS_ADJUDICATOR
        ),
    }
)

_VALID_SUPPORT = "valid_support"
_PRIMARY_OR_TWO_INDEPENDENT = "primary_or_two_independent_support"
_TWO_INDEPENDENT = "two_independent_support_groups"
_PRIMARY_PLUS_INDEPENDENT = "primary_plus_different_independence_group"
_ALL_MATERIAL_SIDES = "all_required_material_sides"
_INDEPENDENT_ADJUDICATOR = "independent_adjudicating_support"


class ClaimGate:
    """Evaluate explicit links and qualifications without retrieval or inference."""

    def evaluate(
        self,
        claim: Claim,
        evidences: Iterable[Evidence],
        links: Iterable[ClaimEvidenceLink],
        qualifications: Iterable[ClaimEvidenceQualification] = (),
        context: ClaimGateContext | None = None,
        *,
        resolved_obligations: ResolvedClaimGateObligations | None = None,
    ) -> ClaimGateResult:
        gate_context = context or ClaimGateContext()
        obligations = resolved_obligations or self._resolve_obligations(
            claim, gate_context
        )
        evidence_list = list(evidences)
        binder = ClaimEvidenceBinder([claim], evidence_list)
        known_evidence_ids = {evidence.evidence_id for evidence in evidence_list}

        relevant_links = [
            link
            for link in links
            if link.claim_id == claim.claim_id
            and link.evidence_id in known_evidence_ids
        ]
        valid_links = binder.bind_many(relevant_links)
        support_ids = tuple(
            sorted(
                {
                    link.evidence_id
                    for link in valid_links
                    if link.relation == "support"
                }
            )
        )
        conflict_ids = tuple(
            sorted(
                {
                    link.evidence_id
                    for link in valid_links
                    if link.relation == "conflict"
                }
            )
        )

        qualification_by_id = self._index_qualifications(
            qualifications, known_evidence_ids
        )
        required_rules = obligations.evidence_strength_rules
        satisfied: list[str] = []
        unmet: list[str] = []

        for rule in required_rules:
            evaluations = self._evaluate_rule(
                rule,
                support_ids,
                conflict_ids,
                qualification_by_id,
                obligations,
            )
            for requirement, is_satisfied in evaluations:
                (satisfied if is_satisfied else unmet).append(requirement)

        if obligations.required_entity_ids:
            for entity_id in obligations.required_entity_ids:
                requirement = f"comparable_primary:{entity_id}"
                covered = any(
                    qualification.is_primary_source is True
                    and entity_id in qualification.supported_entity_ids
                    for evidence_id in support_ids
                    if (qualification := qualification_by_id.get(evidence_id)) is not None
                )
                (satisfied if covered else unmet).append(requirement)

        decision, reason_codes = self._decision(
            support_ids=support_ids,
            unmet=unmet,
            satisfied=satisfied,
            allow_retrieve_more=gate_context.allow_retrieve_more,
        )
        result = ClaimGateResult(
            claim_id=claim.claim_id,
            decision=decision,
            applicable_risk_types=claim.risk_types,
            required_rules=required_rules,
            resolved_obligations=obligations,
            satisfied_requirements=tuple(satisfied),
            unmet_requirements=tuple(unmet),
            supporting_evidence_ids=support_ids,
            conflicting_evidence_ids=conflict_ids,
            reason_codes=reason_codes,
        )
        # Local import avoids coupling the evidence model layer to an
        # observability backend. Recording is strictly fail-open.
        try:
            from gpt_researcher.enterprise.trace import current_trace

            trace = current_trace()
            if trace is not None:
                trace.try_record_claim_gate(claim, result)
        except Exception:
            pass
        return result

    @staticmethod
    def _index_qualifications(
        qualifications: Iterable[ClaimEvidenceQualification],
        known_evidence_ids: set[str],
    ) -> dict[str, ClaimEvidenceQualification]:
        indexed: dict[str, ClaimEvidenceQualification] = {}
        for qualification in qualifications:
            if qualification.evidence_id not in known_evidence_ids:
                continue
            previous = indexed.get(qualification.evidence_id)
            if previous is not None and previous != qualification:
                raise ValueError(
                    "Conflicting qualifications share evidence_id="
                    f"{qualification.evidence_id!r}"
                )
            indexed[qualification.evidence_id] = qualification
        return indexed

    @staticmethod
    def _resolve_obligations(
        claim: Claim,
        context: ClaimGateContext,
    ) -> ResolvedClaimGateObligations:
        rules = [RISK_MINIMUM_RULES[risk_type] for risk_type in claim.risk_types]
        if context.required_unit_rule is not None:
            rules.append(context.required_unit_rule)
        if not rules:
            rules.append(EvidenceStrengthRule.STANDARD)
        required_rules = tuple(dict.fromkeys(rules))
        conflict_required = (
            EvidenceStrengthRule.CONFLICT_SIDES_PLUS_ADJUDICATOR in required_rules
        )
        return ResolvedClaimGateObligations(
            evidence_strength_rules=required_rules,
            required_entity_ids=context.required_entity_ids,
            required_material_side_ids=(
                context.required_material_side_ids if conflict_required else ()
            ),
            requires_independent_adjudicator=conflict_required,
        )

    @staticmethod
    def _evaluate_rule(
        rule: EvidenceStrengthRule,
        support_ids: tuple[str, ...],
        conflict_ids: tuple[str, ...],
        qualifications: dict[str, ClaimEvidenceQualification],
        obligations: ResolvedClaimGateObligations,
    ) -> tuple[tuple[str, bool], ...]:
        support_qualifications = [
            qualifications[evidence_id]
            for evidence_id in support_ids
            if evidence_id in qualifications
        ]
        support_groups = {
            qualification.independence_group_id
            for qualification in support_qualifications
            if qualification.independence_group_id is not None
        }
        primary_qualifications = [
            qualification
            for qualification in support_qualifications
            if qualification.is_primary_source is True
        ]

        if rule is EvidenceStrengthRule.STANDARD:
            return ((_VALID_SUPPORT, bool(support_ids)),)
        if rule is EvidenceStrengthRule.PRIMARY_OR_TWO_INDEPENDENT:
            return (
                (
                    _PRIMARY_OR_TWO_INDEPENDENT,
                    bool(primary_qualifications) or len(support_groups) >= 2,
                ),
            )
        if rule is EvidenceStrengthRule.TWO_INDEPENDENT:
            return ((_TWO_INDEPENDENT, len(support_groups) >= 2),)
        if rule is EvidenceStrengthRule.PRIMARY_PLUS_INDEPENDENT:
            satisfied = any(
                primary.independence_group_id is not None
                and any(
                    group != primary.independence_group_id
                    for group in support_groups
                )
                for primary in primary_qualifications
            )
            return ((_PRIMARY_PLUS_INDEPENDENT, satisfied),)
        if rule is EvidenceStrengthRule.CONFLICT_SIDES_PLUS_ADJUDICATOR:
            linked_ids = set(support_ids) | set(conflict_ids)
            represented_sides = {
                side_id
                for evidence_id in linked_ids
                if (qualification := qualifications.get(evidence_id)) is not None
                for side_id in qualification.material_side_ids
            }
            sides_satisfied = bool(obligations.required_material_side_ids) and set(
                obligations.required_material_side_ids
            ).issubset(represented_sides)
            adjudicator_satisfied = any(
                qualification.is_independent_adjudicator is True
                for qualification in support_qualifications
            )
            evaluations = [(_ALL_MATERIAL_SIDES, sides_satisfied)]
            if obligations.requires_independent_adjudicator:
                evaluations.append((_INDEPENDENT_ADJUDICATOR, adjudicator_satisfied))
            return tuple(evaluations)
        raise AssertionError(f"Unhandled evidence strength rule: {rule}")

    @staticmethod
    def _decision(
        *,
        support_ids: tuple[str, ...],
        unmet: list[str],
        satisfied: list[str],
        allow_retrieve_more: bool,
    ) -> tuple[ClaimGateDecision, tuple[ClaimGateReasonCode, ...]]:
        if not unmet:
            return (
                ClaimGateDecision.EMIT,
                (ClaimGateReasonCode.ALL_REQUIREMENTS_SATISFIED,),
            )

        if (
            unmet == [_INDEPENDENT_ADJUDICATOR]
            and _ALL_MATERIAL_SIDES in satisfied
        ):
            return (
                ClaimGateDecision.HEDGE,
                (
                    ClaimGateReasonCode.EVIDENCE_REQUIREMENTS_UNMET,
                    ClaimGateReasonCode.CONFLICT_UNADJUDICATED,
                ),
            )

        if allow_retrieve_more:
            return (
                ClaimGateDecision.RETRIEVE_MORE,
                (
                    ClaimGateReasonCode.EVIDENCE_REQUIREMENTS_UNMET,
                    ClaimGateReasonCode.RETRIEVAL_AVAILABLE,
                ),
            )
        reasons = [ClaimGateReasonCode.EVIDENCE_REQUIREMENTS_UNMET]
        if not support_ids:
            reasons.append(ClaimGateReasonCode.NO_VALID_SUPPORT)
        return ClaimGateDecision.OMIT, tuple(reasons)
