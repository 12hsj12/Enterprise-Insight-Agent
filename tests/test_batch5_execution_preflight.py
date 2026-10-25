import asyncio

import pytest

from scripts.run_development_calibration import (
    IDS,
    effective_payload,
    iter_manifest_requests,
    preflight,
    validate_manifest,
)
from gpt_researcher.enterprise.workflow import IntelligenceRequest


def test_fixed_manifest_preflight_builds_full_v2_payloads():
    payloads = list(iter_manifest_requests(preflight()))

    assert [case["id"] for case, _ in payloads] == list(IDS)
    assert len(payloads) == len(set(case["id"] for case, _ in payloads)) == 6
    assert all(payload["enable_v2_execution"] is True for _, payload in payloads)
    assert all(payload["enable_v2_evidence_selection"] is True for _, payload in payloads)


def test_mock_runner_invokes_each_fixed_case_once_without_live_services():
    invocations = []

    async def mock_runner(case, payload):
        invocations.append((case["id"], payload))

    async def run():
        for case, payload in iter_manifest_requests(preflight()):
            await mock_runner(case, payload)

    asyncio.run(run())

    assert [case_id for case_id, _ in invocations] == list(IDS)
    assert {case_id: sum(item[0] == case_id for item in invocations) for case_id in IDS} == dict.fromkeys(IDS, 1)
    assert len(invocations) == 6


def test_duplicate_manifest_is_rejected_before_any_runner_invocation():
    calls = 0

    async def mock_runner(case, payload):
        nonlocal calls
        calls += 1

    async def run():
        cases = preflight()
        duplicated_cases = (cases[0], cases[0], *cases[2:])
        with pytest.raises(ValueError, match="duplicate"):
            for case, payload in iter_manifest_requests(duplicated_cases):
                await mock_runner(case, payload)
        assert calls == 0

    asyncio.run(run())


@pytest.mark.parametrize("field", ["enable_v2_execution", "enable_v2_evidence_selection"])
def test_disabled_v2_flags_fail_before_any_runner_invocation(field):
    values = {"enable_v2_execution": True, "enable_v2_evidence_selection": True}
    values[field] = False
    request = IntelligenceRequest(target="preflight target", **values)

    with pytest.raises(ValueError, match=field):
        effective_payload(request)
