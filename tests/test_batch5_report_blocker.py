"""TC_001 diagnostic writer shape at the report registration boundary.

The fixture keeps the actual requirement, writer atoms, opaque evidence ID,
unique-prefix citation, and literal source passage, without page text.
"""

from datetime import date
import json
from pathlib import Path

import pytest

from gpt_researcher.enterprise.integration import (
    ClaimProposal, _resolve_writer_evidence_prefix, integrate_claims,
    register_proposal, render_report,
)
from gpt_researcher.enterprise.requirements import ResearchRequirement
from gpt_researcher.enterprise.report_diagnostics import ReportDiagnosticCapture
from gpt_researcher.evidence.models import Evidence, EvidenceContext


FIXTURE = Path(__file__).parent / "fixtures" / "batch5_tc_report_boundary.json"
CUTOFF = date(2026, 9, 5)


def diagnostic_inputs():
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    requirements = [ResearchRequirement.model_validate(item) for item in data["requirements"]]
    evidences = [Evidence.model_validate(item) for item in data["evidences"]]
    proposal = ClaimProposal.model_validate(data["proposal"])
    return data, proposal, requirements, evidences


def test_tc_real_comparative_shape_reaches_report_without_unlabelled_claim():
    data, proposal, requirements, evidences = diagnostic_inputs()
    # Before repair, R2_ivfflat_tuning caused ValueError:
    # "Comparative requirement claim lacks comparative risk type".
    plan = register_proposal(proposal, data["scope_id"], evidences, requirements)
    assert plan.invalid_comparative_claim_input_count == 1
    assert plan.resolved_writer_evidence_prefix_count == 5
    assert len(plan.items) == 1
    assert plan.items[0].links[0].evidence_id == evidences[0].evidence_id
    assert plan.items[0].cited_evidence_ids == [evidences[0].evidence_id]

    execution = integrate_claims(EvidenceContext(context="", evidences=evidences), plan, CUTOFF)
    report = render_report(execution)
    assert execution.invalid_comparative_claim_input_count == 1
    assert execution.evidence_context.claim_gate_results[0].decision.value != "emit"
    assert execution.layered_output_summary["verified_fact"] == 0
    assert execution.layered_output_summary["limited_evidence"] == 1
    assert "IVFFlat recall is described as more sensitive to tuning" not in report
    assert "Compared with HNSW, IVFFlat is usually lighter" in report
    assert all(result.status.value == "pass" for result in
               execution.evidence_context.grounding_validation_results)


def test_rejected_comparative_atom_cannot_survive_as_excerpt_or_inference():
    data, proposal, requirements, evidences = diagnostic_inputs()
    proposal.source_excerpts.append(proposal.source_excerpts[0].model_copy(update={
        "claim_reference_id": "R2_ivfflat_tuning",
    }))
    proposal.inferences = ClaimProposal.model_validate({
        "claims": [],
        "inferences": [{"inference_id": "bad_premise", "requirement_id": "R2",
                        "text": "Consider IVFFlat.",
                        "premise_claim_ids": ["R2_ivfflat_tuning"]}],
    }).inferences
    plan = register_proposal(proposal, data["scope_id"], evidences, requirements)
    assert len(plan.source_excerpts) == 1
    assert not plan.inferences
    assert plan.invalid_inference_input_count == 1
    execution = integrate_claims(EvidenceContext(context="", evidences=evidences), plan, CUTOFF)
    assert not execution.surviving_inferences


def test_prefix_resolution_requires_unique_runtime_id():
    actual = "ev_87d217fa2e07e448"
    assert _resolve_writer_evidence_prefix("ev_87d2", {actual}) == actual
    assert _resolve_writer_evidence_prefix("ev_87d2", {
        actual, "ev_87d2aaaaaaaaaaaa",
    }) == "ev_87d2"
    assert _resolve_writer_evidence_prefix("ev_87", {actual}) == "ev_87"
    assert _resolve_writer_evidence_prefix("ev_unknown", {actual}) == "ev_unknown"


def test_unknown_evidence_reference_still_fails_closed():
    data, proposal, requirements, evidences = diagnostic_inputs()
    proposal.claims[0].relations[0].evidence_id = "ev_dead"
    proposal.claims[0].cited_evidence_ids = ["ev_dead"]
    plan = register_proposal(proposal, data["scope_id"], evidences, requirements)
    with pytest.raises(ValueError, match="Unknown qualification evidence ID"):
        integrate_claims(EvidenceContext(context="", evidences=evidences), plan, CUTOFF)


def test_report_diagnostic_saves_stage_message_traceback_without_secrets(tmp_path):
    capture = ReportDiagnosticCapture()
    with capture.activate():
        capture.observe("writer_structured_response", {
            "claims": [], "Authorization": "Bearer fixture-secret-value",
            "chain_of_thought": "private fixture reasoning",
        })
        with pytest.raises(ValueError, match="fixture boundary"):
            with capture.stage("register_proposal"):
                capture.set_current(requirement_id="R2", proposal_id="R2_ivfflat_tuning")
                raise ValueError("fixture boundary")
    path = tmp_path / "report_diagnostic.json"
    capture.export(path)
    artifact = path.read_text(encoding="utf-8")
    assert '"stage_name": "register_proposal"' in artifact
    assert '"exception_message": "fixture boundary"' in artifact
    assert "ValueError: fixture boundary" in artifact
    assert '"requirement_id": "R2"' in artifact
    assert "fixture-secret-value" not in artifact
    assert "private fixture reasoning" not in artifact
