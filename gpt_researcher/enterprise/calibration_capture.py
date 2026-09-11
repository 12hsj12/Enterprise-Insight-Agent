"""Opt-in observation of development calibration inputs; never a replay runner."""

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
import hashlib
import json
import os
import re


def canonical_bytes(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2,
                       allow_nan=False) + "\n").encode("utf-8")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


_active: ContextVar = ContextVar("development_calibration_capture", default=None)
_FIELDS = ("url", "source", "title", "publisher", "source_organization",
           "source_owner", "author", "publication_date", "source_type")


def scrub(text: str) -> str:
    """Remove credential-shaped data and configured secrets, never serialize env."""
    for name, value in os.environ.items():
        if re.search(r"key|token|secret|password|credential", name, re.I) and len(value) >= 8:
            text = text.replace(value, "[REDACTED]")
    text = re.sub(r"(?i)(authorization\s*[:=]\s*)(?:(?:bearer|basic)\s+)?[^\s,;]+", r"\1[REDACTED]", text)
    text = re.sub(r"(?i)(bearer\s+)[^\s,;]+", r"\1[REDACTED]", text)
    text = re.sub(r"(https?://)[^/\s:@]+:[^/\s@]+@", r"\1[REDACTED]@", text)
    text = re.sub(r"(?i)((?:api[_-]?key|token|password|secret)\s*[=:]\s*)[^\s&\"']+",
                  r"\1[REDACTED]", text)
    return text


def _text(value) -> str:
    if not isinstance(value, str):
        raise ValueError("Capture expects text")
    return scrub(value)


@dataclass
class CalibrationCapture:
    events: list[dict] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @contextmanager
    def activate(self):
        token = _active.set(self)
        try:
            yield self
        finally:
            _active.reset(token)

    def observe(self, stage, query, material):
        try:
            records = []
            for index, item in enumerate(material):
                metadata = item if stage == "pages_before_compression" else item.metadata
                content = (item.get("raw_content") or "") if stage == "pages_before_compression" else item.page_content
                content = _text(content)
                record = {key: _text(metadata[key]) for key in _FIELDS
                          if isinstance(metadata.get(key), str)}
                record["ignored_nontext_metadata_fields"] = [key for key in _FIELDS
                    if metadata.get(key) is not None and not isinstance(metadata.get(key), str)]
                record.update(position=index, content=content[:50000],
                              content_chars=len(content), content_truncated=len(content) > 50000,
                              full_sanitized_content_sha256=sha256(content.encode("utf-8")))
                if stage == "eligible_chunks_before_ranking":
                    value = getattr(item, "state", {}).get("query_similarity_score")
                    record["query_similarity_score"] = float(value) if value is not None else None
                records.append(record)
            event = {"stage": stage, "sub_query": _text(query), "records": records}
            # Detach every saved value and reject non-finite values atomically.
            self.events.append(json.loads(canonical_bytes(event)))
        except Exception:
            # No raw exception messages (they may contain credentials); observation
            # failures cannot change retrieval, ranking or downstream decisions.
            self.errors.append("capture_invalid_material")


def observe(stage, query, material):
    capture = _active.get()
    if capture is not None:
        capture.observe(stage, query, material)
