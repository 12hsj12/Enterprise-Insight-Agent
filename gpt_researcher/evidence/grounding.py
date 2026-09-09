"""Deterministic post-generation grounding validation and bounded local repair."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import date

from .gate import ClaimGate
from .models import (
    Claim,
    ClaimEvidenceLink,
    ClaimEvidenceQualification,
    ClaimGateContext,
    ClaimGateDecision,
    ClaimGateResult,
    Evidence,
    GeneratedClaimOutputMode,
    GeneratedClaimRecord,
    GroundingEvidenceAuditMetadata,
    GroundingFinding,
    GroundingFindingCode,
    GroundingRepairAction,
    GroundingRepairOperation,
    GroundingRepairPlan,
    GroundingStatus,
    GroundingValidationResult,
)


DEFAULT_INFORMATION_CUTOFF = date(2026, 9, 5)


class GroundingValidator:
    """Audit whether structured final output preserved Claim Gate decisions.

    The validator performs no claim extraction, semantic entailment, hedging
    inference, source classification, or retrieval. Report generation must supply
    the emitted factual assertions and their citations as typed records.
    """

    def __init__(self, claim_gate: ClaimGate | None = None):
        self._claim_gate = claim_gate or ClaimGate()

    def validate(
        self,
        records: Iterable[GeneratedClaimRecord],
        *,
        claims: Iterable[Claim],
        evidences: Iterable[Evidence],
        links: Iterable[ClaimEvidenceLink],
        gate_results: Iterable[ClaimGateResult],
        qualifications: Iterable[ClaimEvidenceQualification] = (),
        gate_contexts: Mapping[str, ClaimGateContext] | None = None,
        audit_metadata: Iterable[GroundingEvidenceAuditMetadata] = (),
        cutoff_date: date = DEFAULT_INFORMATION_CUTOFF,
        repair_attempt: int = 0,
    ) -> GroundingValidationResult:
        if repair_attempt not in (0, 1):
            raise ValueError("repair_attempt must be 0 or 1")

        record_list = list(records)
        claims_by_id = self._index_unique(claims, "claim_id", "claim")
        evidences_by_id = self._index_unique(evidences, "evidence_id", "evidence")
        gates_by_id = self._index_unique(
            gate_results, "claim_id", "ClaimGateResult"
        )
        metadata_by_id = self._index_unique(
            audit_metadata, "evidence_id", "cutoff metadata"
        )
        link_list = list(links)
        qualification_list = list(qualifications)
        contexts = gate_contexts or {}
        findings: list[GroundingFinding] = []
        reapplied: list[ClaimGateResult] = []

        relations_by_claim_evidence: dict[tuple[str, str], set[str]] = {}
        for link in link_list:
            relations_by_claim_evidence.setdefault(
                (link.claim_id, link.evidence_id), set()
            ).add(link.relation)

        for record in record_list:
            claim = claims_by_id.get(record.claim_id)
            if claim is None:
                findings.append(self._finding(GroundingFindingCode.UNKNOWN_CLAIM, record))
                continue

            previous_gate = gates_by_id.get(record.claim_id)
            if previous_gate is None:
                findings.append(
                    self._finding(GroundingFindingCode.MISSING_GATE_RESULT, record)
                )
                continue

            if previous_gate.decision is ClaimGateDecision.OMIT:
                findings.append(
                    self._finding(GroundingFindingCode.OMITTED_CLAIM_EMITTED, record)
                )
            elif previous_gate.decision is ClaimGateDecision.RETRIEVE_MORE:
                findings.append(
                    self._finding(
                        GroundingFindingCode.RETRIEVE_MORE_CLAIM_EMITTED, record
                    )
                )
            elif (
                previous_gate.decision is ClaimGateDecision.HEDGE
                and record.output_mode is not GeneratedClaimOutputMode.HEDGED
            ):
                findings.append(
                    self._finding(
                        GroundingFindingCode.HEDGE_REQUIRED_BUT_UNQUALIFIED, record
                    )
                )

            effective_evidence_ids: set[str] = set()
            for evidence_id in record.cited_evidence_ids:
                if evidence_id not in evidences_by_id:
                    findings.append(
                        self._finding(
                            GroundingFindingCode.UNKNOWN_CITATION,
                            record,
                            evidence_id=evidence_id,
                        )
                    )
                    continue

                relations = relations_by_claim_evidence.get(
                    (record.claim_id, evidence_id)
                )
                if not relations:
                    findings.append(
                        self._finding(
                            GroundingFindingCode.CITATION_NOT_LINKED_TO_CLAIM,
                            record,
                            evidence_id=evidence_id,
                        )
                    )
                    continue

                is_support = "support" in relations
                metadata = metadata_by_id.get(evidence_id)
                if is_support and (
                    metadata is None or metadata.publication_date is None
                ):
                    findings.append(
                        GroundingFinding(
                            code=GroundingFindingCode.CUTOFF_UNVERIFIED,
                            claim_id=record.claim_id,
                            evidence_id=evidence_id,
                            blocking=False,
                            repairable=False,
                        )
                    )
                if (
                    is_support
                    and metadata is not None
                    and metadata.publication_date is not None
                    and metadata.publication_date > cutoff_date
                ):
                    findings.append(
                        self._finding(
                            GroundingFindingCode.POST_CUTOFF_EVIDENCE,
                            record,
                            evidence_id=evidence_id,
                        )
                    )
                    continue

                effective_evidence_ids.add(evidence_id)

            effective_evidences = [
                evidences_by_id[evidence_id]
                for evidence_id in sorted(effective_evidence_ids)
            ]
            effective_links = [
                link
                for link in link_list
                if link.claim_id == record.claim_id
                and link.evidence_id in effective_evidence_ids
            ]
            current_gate = self._claim_gate.evaluate(
                claim,
                effective_evidences,
                effective_links,
                qualification_list,
                contexts.get(record.claim_id),
            )
            reapplied.append(current_gate)

            if previous_gate.decision is ClaimGateDecision.EMIT:
                current_is_safe = current_gate.decision is ClaimGateDecision.EMIT
            elif previous_gate.decision is ClaimGateDecision.HEDGE:
                current_is_safe = current_gate.decision in (
                    ClaimGateDecision.EMIT,
                    ClaimGateDecision.HEDGE,
                )
            else:
                current_is_safe = True
            if not current_is_safe:
                findings.append(
                    self._finding(
                        GroundingFindingCode.INSUFFICIENT_FINAL_CITATIONS, record
                    )
                )

        blocking_claim_ids = {
            finding.claim_id for finding in findings if finding.blocking
        }
        known_emitted_ids = {
            record.claim_id
            for record in record_list
            if record.claim_id in claims_by_id and record.claim_id in gates_by_id
        }
        validated_claim_ids = tuple(sorted(known_emitted_ids - blocking_claim_ids))

        blocking_findings = [finding for finding in findings if finding.blocking]
        if not blocking_findings:
            status = GroundingStatus.PASS
            repairable_claim_ids: tuple[str, ...] = ()
            failed_claim_ids: tuple[str, ...] = ()
        elif repair_attempt == 0 and all(
            finding.repairable for finding in blocking_findings
        ):
            status = GroundingStatus.REPAIR_REQUIRED
            repairable_claim_ids = tuple(sorted(blocking_claim_ids))
            failed_claim_ids = ()
        else:
            status = GroundingStatus.FAIL
            repairable_claim_ids = ()
            failed_claim_ids = tuple(sorted(blocking_claim_ids))

        return GroundingValidationResult(
            status=status,
            validated_claim_ids=validated_claim_ids,
            findings=tuple(findings),
            repairable_claim_ids=repairable_claim_ids,
            failed_claim_ids=failed_claim_ids,
            reason_codes=tuple(dict.fromkeys(finding.code for finding in findings)),
            repair_attempt=repair_attempt,
            reapplied_gate_results=tuple(reapplied),
        )

    @staticmethod
    def create_repair_plan(
        result: GroundingValidationResult,
    ) -> GroundingRepairPlan:
        """Create the only permitted local repair plan for an initial audit."""

        if result.repair_attempt != 0:
            raise ValueError("No repair plan is allowed after the first repair pass")
        if result.status is not GroundingStatus.REPAIR_REQUIRED:
            raise ValueError("A repair plan requires repair_required status")

        remove_claim_codes = {
            GroundingFindingCode.UNKNOWN_CLAIM,
            GroundingFindingCode.MISSING_GATE_RESULT,
            GroundingFindingCode.OMITTED_CLAIM_EMITTED,
            GroundingFindingCode.RETRIEVE_MORE_CLAIM_EMITTED,
            GroundingFindingCode.INSUFFICIENT_FINAL_CITATIONS,
        }
        remove_claim_ids = {
            finding.claim_id
            for finding in result.findings
            if finding.blocking and finding.code in remove_claim_codes
        }
        actions: list[GroundingRepairAction] = [
            GroundingRepairAction(
                operation=GroundingRepairOperation.REMOVE_CLAIM,
                claim_id=claim_id,
            )
            for claim_id in sorted(remove_claim_ids)
        ]

        for finding in result.findings:
            if not finding.blocking or finding.claim_id in remove_claim_ids:
                continue
            if finding.code is GroundingFindingCode.HEDGE_REQUIRED_BUT_UNQUALIFIED:
                actions.append(
                    GroundingRepairAction(
                        operation=GroundingRepairOperation.MARK_CLAIM_HEDGED,
                        claim_id=finding.claim_id,
                    )
                )
            elif finding.code in {
                GroundingFindingCode.UNKNOWN_CITATION,
                GroundingFindingCode.CITATION_NOT_LINKED_TO_CLAIM,
                GroundingFindingCode.POST_CUTOFF_EVIDENCE,
            }:
                actions.append(
                    GroundingRepairAction(
                        operation=GroundingRepairOperation.REMOVE_INVALID_CITATION,
                        claim_id=finding.claim_id,
                        evidence_id=finding.evidence_id,
                    )
                )

        unique_actions = {
            (action.operation, action.claim_id, action.evidence_id): action
            for action in actions
        }
        operation_order = {
            GroundingRepairOperation.REMOVE_CLAIM: 0,
            GroundingRepairOperation.MARK_CLAIM_HEDGED: 1,
            GroundingRepairOperation.REMOVE_INVALID_CITATION: 2,
        }
        ordered = sorted(
            unique_actions.values(),
            key=lambda action: (
                action.claim_id,
                operation_order[action.operation],
                action.evidence_id or "",
            ),
        )
        return GroundingRepairPlan(actions=tuple(ordered))

    @staticmethod
    def apply_repair_plan(
        records: Iterable[GeneratedClaimRecord],
        plan: GroundingRepairPlan,
    ) -> list[GeneratedClaimRecord]:
        """Apply removals/mode changes only; never add claims or citations."""

        remove_claim_ids = {
            action.claim_id
            for action in plan.actions
            if action.operation is GroundingRepairOperation.REMOVE_CLAIM
        }
        hedge_claim_ids = {
            action.claim_id
            for action in plan.actions
            if action.operation is GroundingRepairOperation.MARK_CLAIM_HEDGED
        }
        removed_citations = {
            (action.claim_id, action.evidence_id)
            for action in plan.actions
            if action.operation is GroundingRepairOperation.REMOVE_INVALID_CITATION
        }

        repaired: list[GeneratedClaimRecord] = []
        for record in records:
            if record.claim_id in remove_claim_ids:
                continue
            citations = tuple(
                evidence_id
                for evidence_id in record.cited_evidence_ids
                if (record.claim_id, evidence_id) not in removed_citations
            )
            output_mode = (
                GeneratedClaimOutputMode.HEDGED
                if record.claim_id in hedge_claim_ids
                else record.output_mode
            )
            repaired.append(
                record.model_copy(
                    update={
                        "cited_evidence_ids": citations,
                        "output_mode": output_mode,
                    }
                )
            )
        return repaired

    @staticmethod
    def _finding(
        code: GroundingFindingCode,
        record: GeneratedClaimRecord,
        *,
        evidence_id: str | None = None,
    ) -> GroundingFinding:
        return GroundingFinding(
            code=code,
            claim_id=record.claim_id,
            evidence_id=evidence_id,
        )

    @staticmethod
    def _index_unique(items: Iterable, id_field: str, label: str) -> dict:
        indexed = {}
        for item in items:
            item_id = getattr(item, id_field)
            previous = indexed.get(item_id)
            if previous is not None and previous != item:
                raise ValueError(
                    f"Conflicting {label} objects share {id_field}={item_id!r}"
                )
            indexed[item_id] = item
        return indexed
