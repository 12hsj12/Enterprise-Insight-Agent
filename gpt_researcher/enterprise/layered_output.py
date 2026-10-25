"""Deterministic disclosure modes beside the unchanged factual Gate path."""

from __future__ import annotations

from datetime import date
from enum import Enum
import re

from pydantic import BaseModel, ConfigDict, Field

from gpt_researcher.evidence.models import (
    ClaimGateDecision, ClaimGateResult, Evidence, GeneratedClaimRecord,
    GroundingEvidenceAuditMetadata, normalize_claim_text,
)


class OutputMode(str, Enum):
    VERIFIED_FACT = "VERIFIED_FACT"
    LIMITED_EVIDENCE = "LIMITED_EVIDENCE"
    AI_INFERENCE = "AI_INFERENCE"
    UNRESOLVED = "UNRESOLVED"


class SourceExcerpt(BaseModel):
    """A literal source passage tied to a rejected Claim's supporting link."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    claim_id: str
    requirement_id: str | None = None
    evidence_id: str
    excerpt: str = Field(min_length=1, max_length=500)


class EvidenceGroundedInference(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    inference_id: str = Field(min_length=1, max_length=100)
    requirement_id: str
    text: str = Field(min_length=1, max_length=1000)
    premise_claim_ids: tuple[str, ...] = Field(min_length=1)

    @property
    def output_mode(self) -> OutputMode:
        return OutputMode.AI_INFERENCE


class LimitedDisclosure(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    requirement_id: str | None = None
    claim_id: str
    evidence_id: str
    excerpt: str
    publisher: str | None = None
    publication_date_unverified: bool = False

    @property
    def output_mode(self) -> OutputMode:
        return OutputMode.LIMITED_EVIDENCE


class InferenceValidationSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    inference_count: int = 0
    invalid_inference_count: int = 0
    premise_failure_count: int = 0


def valid_limited_excerpt(
    source: SourceExcerpt, *, evidence: Evidence, gate: ClaimGateResult,
    support_ids: set[str], citation_ids: set[str],
    metadata: GroundingEvidenceAuditMetadata | None, cutoff: date,
    factual_record_survived: bool = True,
) -> bool:
    """Audit a source quote independently of factual Grounding validation.

    A literal quote can disclose what a source said. It cannot authorize the
    rejected Claim as a factual assertion, even if the source has high authority.
    An initially emitted Claim may use this path only after Grounding removed
    its factual record.
    """
    if gate.decision is ClaimGateDecision.EMIT and factual_record_survived:
        return False
    if source.evidence_id not in support_ids or source.evidence_id not in citation_ids:
        return False
    if metadata and metadata.publication_date and metadata.publication_date > cutoff:
        return False
    excerpt = normalize_claim_text(source.excerpt)
    content = normalize_claim_text(evidence.content)
    if not excerpt or len(excerpt) < 8 or not _complete_source_passage(excerpt, content):
        return False
    # A truncated sentence can silently change the meaning of a source. The
    # writer supplies a complete literal passage; runtime never truncates it.
    if excerpt.endswith(("…", "...")):
        return False
    return True


def _complete_source_passage(excerpt: str, content: str) -> bool:
    """Require quote edges at source sentence boundaries, including negation.

    Whitespace normalization is shared with the rendered quote. A sentence may
    start at the beginning of the source or after terminal punctuation, and
    may end at terminal punctuation or at the end of the source. Ambiguous
    fragments are rejected rather than trying to infer their missing context.
    """
    start = content.find(excerpt)
    while start >= 0:
        end = start + len(excerpt)
        before = content[:start].rstrip()
        after = content[end:]
        starts_sentence = start == 0 or (
            before.endswith((".", "!", "?", "。", "！", "？"))
            and (content[start - 1].isspace()
                 or before.endswith(("。", "！", "？")))
        )
        ends_sentence = end == len(content) or (
            excerpt.endswith((".", "!", "?", "。", "！", "？"))
            and (not after or after[0].isspace()
                 or excerpt.endswith(("。", "！", "？")))
        )
        if starts_sentence and ends_sentence:
            return True
        start = content.find(excerpt, start + 1)
    return False


_NUMERIC_LITERAL = re.compile(r"(?<![\w])\d+(?:[.,]\d+)*(?:%|ms|s)?(?![\w])")
_ACTION = re.compile(
    r"(?:(first)\s+)?(consider|validate|evaluate|compare|choose|test|pilot|assess)\s+"
    r"([A-Za-z][A-Za-z0-9_+-]{0,39})(?:\s+and\s+([A-Za-z][A-Za-z0-9_+-]{0,39}))?"
    r"(?:\s+(first))?",
    re.IGNORECASE,
)
_ENTITY_CUE = re.compile(
    r"(?:company|product|vendor|option|system|model|platform|candidate|the)\s+$",
    re.IGNORECASE,
)
_ENTITY_PREDICATE = re.compile(
    r"^\s+(?:is|was|has|had|does|did|can|will|uses|supports|offers|provides)\b",
    re.IGNORECASE,
)


def _target_in_premises(target: str, premise_texts: tuple[str, ...]) -> bool:
    """Bind an action target to an explicit entity, not an article/pronoun."""
    for premise in premise_texts:
        flags = 0 if len(target) <= 2 else re.IGNORECASE
        for match in re.finditer(rf"(?<!\w){re.escape(target)}(?!\w)", premise, flags):
            if len(target) > 2 or (len(target) == 2 and target not in {"US", "IT"}):
                return True
            if len(target) == 1 and target != target.upper():
                continue
            before = premise[:match.start()]
            after = premise[match.end():]
            if _ENTITY_CUE.search(before) or _ENTITY_PREDICATE.match(after):
                return True
    return False


def canonical_inference_text(text: str, premise_texts: tuple[str, ...]) -> str | None:
    """Render only a bounded recommendation; never pass Writer prose through.

    A premise label is replaced with fixed wording. A conditional is expressly
    hypothetical. The action may name only entities appearing in surviving
    factual premises. This grammar does not decide whether the advice is good.
    """
    candidate = text.strip()
    if not candidate or _NUMERIC_LITERAL.search(candidate):
        return None
    if re.search(r"https?://|www\.|[\[\]<>]|[;:!?\n—–]", candidate):
        return None
    candidate = candidate.removesuffix(".").strip()
    if "." in candidate:
        return None
    prefix = ""
    if candidate.casefold().startswith(("based on ", "given ")):
        label, separator, candidate = candidate.partition(",")
        if not separator or len(label) > 100 or not label.casefold().endswith((" premise", " premises")):
            return None
        prefix = "Based on the verified premise, "
        candidate = candidate.strip()
    elif candidate.casefold().startswith("if "):
        condition, separator, candidate = candidate.partition(",")
        if (not separator or len(condition) > 120 or len(condition) <= 3
                or not re.fullmatch(r"If [\w\s'-]+", condition, re.IGNORECASE)):
            return None
        prefix = condition + ", "
        candidate = candidate.strip()
    match = _ACTION.fullmatch(candidate)
    if match is None:
        return None
    before_first, verb, entity, second_entity, after_first = match.groups()
    if second_entity and verb.casefold() != "compare":
        return None
    if verb.casefold() == "compare" and second_entity is None:
        return None
    for target in (entity, second_entity):
        if target and not _target_in_premises(target, premise_texts):
            return None
    action = f"{verb.lower() if prefix else verb.capitalize()} {entity}"
    if second_entity:
        action += f" and {second_entity} against the decision requirements"
    elif before_first or after_first:
        action += " first"
    return prefix + action + "."


def validate_inferences(
    candidates: list[EvidenceGroundedInference], records: list[GeneratedClaimRecord],
    claim_requirements: dict[str, str], eligible_requirement_ids: set[str],
    *, limited_premise_texts: dict[str, str] | None = None,
) -> tuple[list[EvidenceGroundedInference], InferenceValidationSummary]:
    """Accept recommendations only when every premise is visible and audited.

    A premise may be a grounded factual record or a final, source-attributed
    LIMITED_EVIDENCE disclosure. The latter remains explicitly limited at
    rendering time; it never becomes a verified factual record here.
    """
    surviving = {record.claim_id: record for record in records}
    limited = limited_premise_texts or {}
    accepted: list[EvidenceGroundedInference] = []
    invalid = missing = 0
    seen_ids: set[str] = set()
    for inference in candidates:
        if inference.inference_id in seen_ids:
            invalid += 1
            continue
        seen_ids.add(inference.inference_id)
        if inference.requirement_id not in eligible_requirement_ids:
            invalid += 1
            continue
        if any(
            claim_id not in surviving and claim_id not in limited
            for claim_id in inference.premise_claim_ids
        ):
            invalid += 1
            missing += 1
            continue
        if any(claim_id not in claim_requirements for claim_id in inference.premise_claim_ids):
            invalid += 1
            missing += 1
            continue
        premise_texts = tuple(
            surviving[claim_id].rendered_text
            if claim_id in surviving else limited[claim_id]
            for claim_id in inference.premise_claim_ids
        )
        canonical = canonical_inference_text(inference.text, premise_texts)
        if canonical is None:
            invalid += 1
            continue
        accepted.append(inference.model_copy(update={"text": canonical}))
    return accepted, InferenceValidationSummary(
        inference_count=len(accepted), invalid_inference_count=invalid,
        premise_failure_count=missing,
    )
