"""Opt-in, scrubbed report-boundary capture for development replay.

The capture is never activated by the normal API. It records structured
authoring inputs, not prompts or provider credentials.
"""

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
import re
import traceback

from .calibration_capture import canonical_bytes, scrub


_active: ContextVar["ReportDiagnosticCapture | None"] = ContextVar(
    "report_diagnostic_capture", default=None
)
_FORBIDDEN_KEYS = re.compile(
    r"(?:authorization|api[_-]?key|token|secret|password|credential|"
    r"chain[_-]?of[_-]?thought|hidden[_-]?reasoning|system[_-]?prompt)", re.I
)


def _safe(value):
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    if isinstance(value, dict):
        return {scrub(str(key)): _safe(item) for key, item in value.items()
                if not _FORBIDDEN_KEYS.search(str(key))}
    if isinstance(value, (list, tuple)):
        return [_safe(item) for item in value]
    if isinstance(value, str):
        return scrub(value)
    return value


@dataclass
class ReportDiagnosticCapture:
    snapshots: dict = field(default_factory=dict)
    stages: list[str] = field(default_factory=list)
    current: dict = field(default_factory=dict)
    failure: dict | None = None

    @contextmanager
    def activate(self):
        token = _active.set(self)
        try:
            yield self
        finally:
            _active.reset(token)

    @contextmanager
    def stage(self, name: str):
        self.stages.append(name)
        try:
            yield
        except BaseException as exc:
            if self.failure is None:
                self.failure = _safe({
                    "stage_name": name,
                    "exception_type": type(exc).__name__,
                    "exception_message": str(exc),
                    "traceback": "".join(traceback.format_exception(exc)),
                    **self.current,
                })
            raise
        finally:
            self.stages.pop()

    def observe(self, name: str, value):
        self.snapshots[name] = _safe(value)

    def set_current(self, *, requirement_id=None, proposal_id=None, claim_id=None):
        self.current = _safe({
            "requirement_id": requirement_id,
            "proposal_id": proposal_id,
            "claim_id": claim_id,
        })

    def export(self, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            raise FileExistsError(path)
        path.write_bytes(canonical_bytes({
            "schema_version": "batch5-report-diagnostic/1.0.0",
            "failure": self.failure,
            "snapshots": self.snapshots,
            "claim_plan_generated": "registered_claim_plan" in self.snapshots,
        }))


def active_capture() -> ReportDiagnosticCapture | None:
    return _active.get()


@contextmanager
def diagnostic_stage(name: str):
    capture = active_capture()
    if capture is None:
        yield
    else:
        with capture.stage(name):
            yield
