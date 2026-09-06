"""Opt-in bounded local traces. Never collect queries, content, URLs or credentials."""

from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
import time

_active_trace: ContextVar["RunTrace | None"] = ContextVar("enterprise_trace", default=None)


def current_trace():
    return _active_trace.get()


class RunTrace:
    def __init__(self, run_id: str, max_events: int = 1000):
        self.run_id = run_id
        self.started_at = datetime.now(timezone.utc).isoformat()
        self.started = time.perf_counter()
        self.events = []
        self.max_events = max_events
        self.dropped_events = 0
        self.search_calls = 0
        self.search_failures = 0
        self.retrieval_calls = 0
        self.selected_evidence_count = 0

    def _append(self, event):
        if len(self.events) < self.max_events:
            self.events.append(event)
        else:
            self.dropped_events += 1

    @contextmanager
    def activate(self):
        token = _active_trace.set(self)
        try:
            yield self
        finally:
            _active_trace.reset(token)

    @contextmanager
    def stage(self, name: str):
        if name not in {"research", "report", "search", "retrieval"}:
            raise ValueError("Unknown trace stage")
        start = time.perf_counter()
        event = {"stage": name, "status": "completed"}
        try:
            yield
        except BaseException as exc:
            event.update(status="failed", error_type=type(exc).__name__)
            if name == "search":
                self.search_failures += 1
            raise
        finally:
            event["duration_s"] = time.perf_counter() - start
            self._append(event)

    def retrieval(self, result, weight: float, similarity_threshold: float):
        self.retrieval_calls += 1
        self.selected_evidence_count += len(result.evidences)
        self._append({
            "stage": "retrieval_selection", "source_reliability_weight": weight,
            "similarity_threshold": similarity_threshold, "selected_count": len(result.evidences),
            "scores": [d.model_dump() for d in result.retrieval_diagnostics],
        })

    def snapshot(self):
        return {
            "run_id": self.run_id, "started_at": self.started_at,
            "elapsed_s": time.perf_counter() - self.started,
            "search_calls": self.search_calls, "search_failures": self.search_failures,
            "search_count_scope": "ResearchConductor web searches; planning/MCP/provider internal retries excluded",
            "retrieval_calls": self.retrieval_calls, "selected_evidence_count": self.selected_evidence_count,
            "dropped_events": self.dropped_events, "events": list(self.events),
        }
