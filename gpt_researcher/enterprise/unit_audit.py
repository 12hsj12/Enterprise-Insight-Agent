"""Stable Markdown audit units for writer-first evidence enforcement.

This module deliberately separates *finding* factual/recommendation coverage
from *editing* the report. Claim text may be aligned to a unit for audit
bookkeeping, but it is never returned as an edit span. Final rendering keeps
the Writer draft as the report body and may only qualify a complete high-risk
or recommendation unit.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import re
from typing import Iterable, Literal

from pydantic import BaseModel, ConfigDict, Field


class AuditUnitType(str, Enum):
    PROSE_SENTENCE = "prose_sentence"
    TABLE_CELL = "table_cell"
    LIST_ITEM = "list_item"
    HEADING = "heading"


class AuditUnitState(str, Enum):
    KEEP = "KEEP"
    LIMITED = "LIMITED"
    OMIT = "OMIT"
    UNRESOLVED = "UNRESOLVED"


class WriterAuditUnit(BaseModel):
    """One stable, original-position Markdown audit boundary."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    unit_id: str
    unit_type: AuditUnitType
    ordinal: int = Field(ge=0)
    start_offset: int = Field(ge=0)
    end_offset: int = Field(ge=0)
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    start_column: int = Field(ge=1)
    text: str
    claim_bearing: bool
    high_risk: bool
    recommendation: bool
    table_row: int | None = Field(default=None, ge=0)
    table_column: int | None = Field(default=None, ge=0)
    table_header: bool = False


class UnitAuditRecord(BaseModel):
    """Final state of a unit after existing Gate/Grounding results are applied."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    unit_id: str
    unit_type: AuditUnitType
    ordinal: int = Field(ge=0)
    start_offset: int = Field(ge=0)
    end_offset: int = Field(ge=0)
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    claim_bearing: bool
    high_risk: bool
    recommendation: bool
    state: AuditUnitState
    action: Literal["keep", "replace", "omit"]
    claim_ids: tuple[str, ...] = ()
    inference_id: str | None = None
    reason_codes: tuple[str, ...] = ()


_TABLE_SEPARATOR = re.compile(r"^\s*:?-{3,}:?\s*$")
_LIST_ITEM = re.compile(r"^(?P<indent>\s*)(?P<marker>(?:[-*+] |\d+[.)] ))")
_REFERENCE_TITLES = {"references", "sources", "bibliography", "参考文献"}

# These signals identify factual propositions, not presentation metadata.  The
# input is normalized by ``classification_text`` before these patterns run, so
# citation years and ordered-list markers cannot manufacture a risk signal.
_NUMERIC_FACT_PATTERN = re.compile(
    r"(?:[$€£¥]\s*\d)|"
    r"(?<![\w-])\d+(?:[.,:/-]\d+)*(?:\s*(?:%|ms|sec(?:onds?)?|minutes?|"
    r"hours?|days?|k|m|b|tb|gb|mb|tokens?|users?|requests?|qps|tps|vectors?|"
    r"parameters?|params?|dimensions?|points?|samples?|problems?|rows?|nodes?))?(?!\w)|"
    r"\b(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
    r"jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|"
    r"dec(?:ember)?)\s+\d{1,2}(?:,\s*\d{4})?\b",
    re.IGNORECASE,
)

_OBJECTIVE_RISK_PATTERN = re.compile(
    r"\b(?:released?|launched?|available|availability|outperforms?|faster|slower|"
    r"market\s+share|benchmarks?|rank(?:ed|ing)?|largest|smallest|best|worst|"
    r"prices?|pricing|costs?|sla|uptime|throughput|latency|context\s+window|"
    r"guarantees?|always|never|eliminates?|zero[- ]risk|causes?|because|due\s+to|"
    r"leads?\s+to|results?\s+in|drives?|reduces?|increases?)\b|"
    r"(?:发布|上线|可用|不可用|市场份额|基准|跑分|领先|最快|最大|最小|排名|"
    r"价格|费用|成本|服务等级|吞吐|延迟|上下文窗口|模型能力|"
    r"保证|始终|从不|导致|因为|由于|因此|带来|降低|提高|增加)",
    re.IGNORECASE,
)

_CAPABILITY_PATTERN = re.compile(
    r"\b(?!evidence\b|analysis\b|report\b|section\b|table\b|source\b)"
    r"[A-Z][A-Za-z0-9_.+/-]*(?:\s+[A-Z][A-Za-z0-9_.+/-]*){0,5}\s+"
    r"(?:supports?|offers?|provides?|accepts?|handles?|integrates?|includes?|"
    r"enables?|allows?|lacks?|is\s+compatible|is\s+capable\s+of)\b|"
    r"(?:平台|产品|模型|服务|公司|厂商|系统)[^\u3002！？\n]{0,40}"
    r"(?:支持|提供|能够|具备|兼容|缺少)",
    re.IGNORECASE,
)

_COMPANY_ACTION_PATTERN = re.compile(
    r"\b(?:[A-Z][A-Za-z0-9_.&+/-]*(?:\s+[A-Z][A-Za-z0-9_.&+/-]*){0,5})\s+"
    r"(?:announced?|acquired?|merged|partnered|invested|raised|filed|sued|"
    r"discontinued?|deprecated?|withdrew|suspended|resumed|committed|promised|"
    r"changed|increased|decreased|cut|reduced|expanded|closed|opened)\b|"
    r"(?:公司|企业|厂商|供应商)[^。！？\n]{0,50}"
    r"(?:宣布|收购|合并|合作|投资|融资|起诉|停止|下线|弃用|撤回|暂停|恢复|"
    r"承诺|调整|上调|下调|削减|扩张|关闭|开放)",
    re.IGNORECASE,
)

# Recommendation wording is an analytical decision, not a factual claim.  This
# narrower pattern is used only at finalization to find objective facts newly
# embedded in advice (numbers, status, capability, benchmarks, or company
# actions) without treating words such as "choose" or "best fit" as facts.
_RECOMMENDATION_OBJECTIVE_FACT_PATTERN = re.compile(
    r"\b(?:released?|launched?|available|availability|market\s+share|benchmarks?|"
    r"prices?|pricing|sla|uptime|throughput|latency|outperforms?|faster|slower|"
    r"supports?|offers?|provides?|accepts?|handles?|integrates?|includes?|enables?|"
    r"allows?|lacks?|guarantees?)\b|"
    r"(?:发布|上线|可用|不可用|市场份额|基准|跑分|价格|费用|服务等级|吞吐|延迟|"
    r"支持|提供|能够|具备|兼容|缺少|保证)",
    re.IGNORECASE,
)

_STRONG_COMPARISON_PATTERN = re.compile(
    r"\b(?:is|are|was|were)\s+(?:(?:objectively|materially|significantly|"
    r"demonstrably)\s+)?(?:more|less|higher|lower|stronger|weaker|better|"
    r"worse|faster|slower|safer|cheaper|costlier)\b|"
    r"\b(?:compared\s+with|compared\s+to|versus|vs\.?|differs?\s+(?:from|in))\b|"
    r"(?:优于|劣于|高于|低于|强于|弱于|快于|慢于|相比|不同于)",
    re.IGNORECASE,
)

RECOMMENDATION_PATTERN = re.compile(
    r"\b(?:we\s+(?:recommend|advise|suggest)|(?:our\s+)?recommendation\s+is|"
    r"should\s+(?:therefore\s+)?(?:be\s+)?(?:choose|chosen|select|selected|adopt|adopted|use|used|"
    r"migrate|migrated|move|moved|switch|switched|replace|replaced|prefer|preferred|"
    r"consider|considered|pilot|piloted|deploy|deployed|standardize|standardized|"
    r"prioritize|prioritized|report|reported|treat|treated|verify|verified|consult|"
    r"collapse|collapsed|map|mapped|attach|attached|state|stated)|"
    r"(?:must|ought\s+to)\s+(?:choose|select|adopt|use|migrate|move|switch|replace|"
    r"prefer|consider|pilot|deploy|standardize|prioritize|verify|report)|"
    r"(?:^|[;:—-]\s*)(?:choose|select|adopt|prefer|consider|pilot|deploy|"
    r"standardize|prioritize|migrate\s+to|move\s+to|switch\s+to|"
    r"replace\s+.+\s+with)\b|"
    r"\b(?:only\s+)?consider\s+(?:migrating|adopting|using|deploying|switching)\b|"
    r"(?:is|are|remains?)\s+(?:the\s+)?(?:best|preferred|right|correct|ideal|honest|"
    r"better[- ]supported)\s+(?:choice|option|fit|answer|destination|starting\s+point)|"
    r"becomes?\s+(?:more\s+)?(?:justified|attractive|appropriate|preferable)\s+when|"
    r"(?:is|are)\s+better\s+suited\b|go\s+with\b|sensible\s+default|"
    r"defensible\s+architecture|recommended\s+(?:default|for)|more\s+attractive|"
    r"this\s+recommendation\b)|"
    r"(?:建议|推荐|应当|应该|宜(?:采用|选择|部署|迁移)|优先选择|首选|可考虑|"
    r"选用|采用.+作为|迁移(?:至|到)|切换(?:至|到)|替换为|部署|开展试点)",
    re.IGNORECASE,
)

_IMPERATIVE_MIGRATION = re.compile(
    r"^(?:(?:first|second|third|fourth|finally|next|then)\s*,?\s*)?"
    r"(?:(?:choose|select|adopt|use|migrate|move|switch|replace|prefer|consider|"
    r"pilot|deploy|standardize|prioritize)\b|"
    r"(?:preserve|pin|record|build|require|write|backfill|run|flip|keep|collapse|"
    r"exploit)\b[^.!?。！？]{0,80}\b(?:embedding|model|version|dimension|collection|"
    r"vector|store|read|export|migration|supplier|vendor|service|database|backend|"
    r"cutover|index|data|path|contract)\b)",
    re.IGNORECASE,
)

_TABLE_FACT_CONTEXT = re.compile(
    r"price|pricing|cost|rate|discount|dimension|index|hybrid|scal|consistency|"
    r"operational|network|model|provider|context|api|billing|capacity|latency|"
    r"throughput|sla|availability|metric|checkpoint|prompt|accuracy|independence|"
    r"credibility|result|score|release|status|capabil|governance|isolation|"
    r"security|compliance|residency|engine|burden|transparency|参数|价格|成本|"
    r"延迟|吞吐|模型|能力|状态|发布|索引|网络|合规|一致性",
    re.IGNORECASE,
)

_DECISION_SECTION = re.compile(
    r"recommend|migration|decision|selection|conclusion|synthesis|judg(?:e)?ment|"
    r"operating\s+posture|选型|迁移|建议|决策|结论",
    re.IGNORECASE,
)

_SECTION_SELECTION_PATTERN = re.compile(
    r"\b(?:is|are|remains?|becomes?)\b[^.!?]{0,100}\b(?:choice|option|default|"
    r"destination|answer|starting\s+point|alternative|middle\s+path|safer\s+position)\b|"
    r"\b(?:where|if|when|for)\b[^.!?]{0,180}\b(?:preferentially|favou?rs?|earns?|"
    r"choose|select|adopt|use|migrate|managed\s+service|search\s+engine|pgvector|"
    r"milvus|qdrant|weaviate|bedrock|azure\s+openai)\b",
    re.IGNORECASE,
)


def markdown_visible_text(value: str) -> str:
    """Remove presentation-only Markdown while retaining the authored words."""

    value = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", value)
    value = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", value)
    value = re.sub(r"<https?://[^>]+>", " ", value)
    value = re.sub(r"https?://\S+", " ", value)
    value = re.sub(r"[`*_~]", "", value)
    return re.sub(r"\s+", " ", value).strip()


def classification_text(value: str) -> str:
    """Return authored prose without citation or Markdown numbering metadata."""

    # Linked citations deliberately retain their author/year label in rendered
    # prose, but those labels are provenance metadata rather than claim values.
    value = re.sub(
        r"\[[^\]]*(?:(?:19|20)\d{2}|n\.d\.)[^\]]*\]\([^)]*\)",
        " ", value, flags=re.IGNORECASE,
    )
    # The ED golden artifacts use compact, unlinked author-year citations.
    value = re.sub(
        r"\([^()\n]*(?:(?:19|20)\d{2}|n\.d\.)[^()\n]*\)",
        " ", value, flags=re.IGNORECASE,
    )
    visible = markdown_visible_text(value)
    return re.sub(
        r"^(?:#{1,6}\s+|[-*+]\s+|\d+[.)]\s+)", "", visible,
    ).strip()


def alignment_text(value: str) -> str:
    visible = markdown_visible_text(value).casefold()
    return " ".join(re.findall(r"[\w%]+", visible, flags=re.UNICODE))


def is_recommendation(value: str, section_title: str = "") -> bool:
    candidate = classification_text(value)
    if RECOMMENDATION_PATTERN.search(candidate):
        return True
    if re.match(
        r"^condition\b[^:]{0,160}:\s*(?:start|prefer|choose|select|adopt|use|"
        r"migrate|move|switch|deploy)",
        candidate,
        flags=re.IGNORECASE,
    ):
        return True
    if _IMPERATIVE_MIGRATION.search(candidate):
        return True
    return bool(
        section_title
        and _DECISION_SECTION.search(section_title)
        and _SECTION_SELECTION_PATTERN.search(candidate)
    )


def is_high_risk(value: str) -> bool:
    """Identify only assertions that need the strict final-output gate.

    Ordinary background facts and explanatory analysis intentionally stay out
    of this classifier. The strict boundary is reserved for objective numeric,
    status, ranking, comparison, causal, company-action, and strong product
    capability assertions.
    """

    candidate = classification_text(value)
    if not candidate:
        return False
    if re.match(
        r"^(?:this|the)\s+(?:section|table|comparison|analysis|report|discussion)\b",
        candidate,
        flags=re.IGNORECASE,
    ):
        return False
    return bool(
        _NUMERIC_FACT_PATTERN.search(candidate)
        or _OBJECTIVE_RISK_PATTERN.search(candidate)
        or _CAPABILITY_PATTERN.search(candidate)
        or _COMPANY_ACTION_PATTERN.search(candidate)
        or _STRONG_COMPARISON_PATTERN.search(candidate)
    )


def is_high_risk_table_value(value: str, context: str) -> bool:
    """Classify terse table assertions without gating uncertainty placeholders."""

    candidate = classification_text(value)
    if not candidate or re.fullmatch(
        r"(?:unknown|varies|depends|not specified|not available|n/?a|tbd|"
        r"deployment[- ]specific|未知|不确定|视情况而定|未说明|暂无)",
        candidate,
        flags=re.IGNORECASE,
    ):
        return False
    if is_high_risk(candidate):
        return True
    return bool(
        _TABLE_FACT_CONTEXT.search(context)
        and re.fullmatch(
            r"(?:yes|no|supported|unsupported|available|unavailable|required|"
            r"optional|included|excluded|primary|secondary|native|managed|"
            r"是|否|支持|不支持|可用|不可用|必需|可选|包含|不包含|原生|托管)",
            candidate,
            flags=re.IGNORECASE,
        )
    )


def is_claim_bearing(value: str, section_title: str = "") -> bool:
    visible = classification_text(value)
    if re.match(
        r"^(?:this|the)\s+(?:section|table|comparison|analysis|report|discussion)\b",
        visible,
        flags=re.IGNORECASE,
    ) and not is_recommendation(visible, section_title):
        return False
    if re.search(
        r"\b(?:supplied (?:source|corpus)|information cutoff|source set|references|"
        r"methodological note|evidence base|scope of (?:this|the) analysis)\b",
        visible,
        flags=re.IGNORECASE,
    ) and not is_recommendation(visible, section_title):
        return False
    return bool(
        is_recommendation(visible, section_title)
        or is_high_risk(visible)
    )


def _line_number(value: str, offset: int) -> int:
    return value.count("\n", 0, offset) + 1


def _unit(
    draft: str,
    unit_type: AuditUnitType,
    ordinal: int,
    start: int,
    end: int,
    *,
    claim_bearing: bool | None = None,
    high_risk: bool | None = None,
    recommendation: bool | None = None,
    table_row: int | None = None,
    table_column: int | None = None,
    table_header: bool = False,
    section_title: str = "",
) -> WriterAuditUnit:
    text = draft[start:end]
    payload = f"unit-audit:v1\0{unit_type.value}\0{start}\0{end}\0{text}"
    unit_id = f"unit_{ordinal:05d}_{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:16]}"
    start_line = _line_number(draft, start)
    end_line = _line_number(draft, max(start, end - 1))
    line_start = draft.rfind("\n", 0, start) + 1
    return WriterAuditUnit(
        unit_id=unit_id,
        unit_type=unit_type,
        ordinal=ordinal,
        start_offset=start,
        end_offset=end,
        start_line=start_line,
        end_line=end_line,
        start_column=start - line_start + 1,
        text=text,
        claim_bearing=(
            is_claim_bearing(text, section_title)
            if claim_bearing is None else claim_bearing
        ),
        high_risk=is_high_risk(text) if high_risk is None else high_risk,
        recommendation=(
            is_recommendation(text, section_title)
            if recommendation is None else recommendation
        ),
        table_row=table_row,
        table_column=table_column,
        table_header=table_header,
    )


def _is_table_row(line: str) -> bool:
    body = line.rstrip("\r\n")
    return "|" in body and len(re.split(r"(?<!\\)\|", body)) >= 2


def _is_table_separator(line: str) -> bool:
    body = line.rstrip("\r\n").strip().strip("|")
    cells = re.split(r"(?<!\\)\|", body)
    return len(cells) >= 2 and all(_TABLE_SEPARATOR.fullmatch(cell) for cell in cells)


def _cell_spans(line: str, line_start: int) -> list[tuple[int, int]]:
    body = line.rstrip("\r\n")
    pipes = [index for index, char in enumerate(body)
             if char == "|" and (index == 0 or body[index - 1] != "\\")]
    boundaries = [-1, *pipes, len(body)]
    spans: list[tuple[int, int]] = []
    for left, right in zip(boundaries, boundaries[1:]):
        raw_start, raw_end = left + 1, right
        segment = body[raw_start:raw_end]
        if not segment.strip():
            continue
        leading = len(segment) - len(segment.lstrip())
        trailing = len(segment.rstrip())
        spans.append((line_start + raw_start + leading, line_start + raw_start + trailing))
    return spans


def _sentence_spans(draft: str, start: int, end: int) -> Iterable[tuple[int, int]]:
    block = draft[start:end]
    cursor = 0
    boundary = re.compile(
        r"(?P<terminal>[.!?。！？])(?P<closers>[\"'”’)\]]*)\s+"
        r"(?=(?:[\"'“‘(\[*_`]*[A-Za-z0-9\u3400-\u9fff]))"
    )

    def protected_period(match: re.Match[str]) -> bool:
        if match.group("terminal") != ".":
            return False
        prefix = block[:match.start("terminal") + 1]
        token_match = re.search(r"([A-Za-z.]+)\s*$", prefix)
        token = token_match.group(1).casefold() if token_match else ""
        if token == "ms." and token_match:
            before_token = prefix[:token_match.start(1)].rstrip()
            if before_token and before_token[-1].isdigit():
                return False
        if re.fullmatch(r"(?:[a-z]\.){2,}", token):
            return True
        if re.fullmatch(r"[a-z]\.", token):
            return True
        return token in {
            "dr.", "mr.", "mrs.", "ms.", "prof.", "sr.", "jr.",
            "st.", "vs.", "fig.", "eq.", "no.", "approx.", "dept.",
        }

    for match in boundary.finditer(block):
        if protected_period(match):
            continue
        raw_start, raw_end = cursor, match.end("closers")
        while raw_start < raw_end and block[raw_start].isspace():
            raw_start += 1
        while raw_end > raw_start and block[raw_end - 1].isspace():
            raw_end -= 1
        if raw_end > raw_start:
            yield start + raw_start, start + raw_end
        cursor = match.end()
    raw_start, raw_end = cursor, len(block)
    while raw_start < raw_end and block[raw_start].isspace():
        raw_start += 1
    while raw_end > raw_start and block[raw_end - 1].isspace():
        raw_end -= 1
    if raw_end > raw_start:
        yield start + raw_start, start + raw_end


@dataclass(frozen=True)
class _Line:
    index: int
    start: int
    end: int
    text: str


def split_markdown_audit_units(draft: str) -> list[WriterAuditUnit]:
    """Split a Writer draft into deterministic, non-overlapping audit units."""

    raw_lines = draft.splitlines(keepends=True)
    lines: list[_Line] = []
    offset = 0
    for index, text in enumerate(raw_lines):
        lines.append(_Line(index=index, start=offset, end=offset + len(text), text=text))
        offset += len(text)
    if offset < len(draft):
        lines.append(_Line(index=len(lines), start=offset, end=len(draft), text=draft[offset:]))

    table_rows: dict[int, tuple[bool, list[str], str]] = {}
    index = 0
    while index + 1 < len(lines):
        if _is_table_row(lines[index].text) and _is_table_separator(lines[index + 1].text):
            header_spans = _cell_spans(lines[index].text, lines[index].start)
            headers = [markdown_visible_text(draft[start:end]) for start, end in header_spans]
            table_rows[index] = (True, headers, "")
            row_index = index + 2
            while row_index < len(lines) and _is_table_row(lines[row_index].text):
                spans = _cell_spans(lines[row_index].text, lines[row_index].start)
                row_label = markdown_visible_text(draft[spans[0][0]:spans[0][1]]) if spans else ""
                table_rows[row_index] = (False, headers, row_label)
                row_index += 1
            index = row_index
            continue
        index += 1

    units: list[WriterAuditUnit] = []
    ordinal = 0
    in_fence = False
    in_references = False
    current_section_title = ""

    def add(unit_type: AuditUnitType, start: int, end: int, **kwargs) -> None:
        nonlocal ordinal
        kwargs.setdefault("section_title", current_section_title)
        units.append(_unit(draft, unit_type, ordinal, start, end, **kwargs))
        ordinal += 1

    index = 0
    while index < len(lines):
        line = lines[index]
        stripped = line.text.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            index += 1
            continue
        if in_fence:
            index += 1
            continue
        if stripped.startswith("#"):
            title = re.sub(r"^#+\s*", "", stripped).strip()
            in_references = title.casefold() in _REFERENCE_TITLES
            heading_level = len(stripped) - len(stripped.lstrip("#"))
            # The report title is frozen Writer structure, not a factual body
            # assertion even when it names a benchmark, model, or pricing topic.
            if not in_references and heading_level > 1 and is_recommendation(
                title, current_section_title
            ):
                end = line.end - len(line.text) + len(line.text.rstrip("\r\n"))
                add(AuditUnitType.HEADING, line.start, end)
            if not in_references:
                current_section_title = title
            index += 1
            continue
        if in_references:
            index += 1
            continue
        if index in table_rows:
            is_header, headers, row_label = table_rows[index]
            spans = _cell_spans(line.text, line.start)
            for column, (start, end) in enumerate(spans):
                text = draft[start:end]
                context = " ".join((
                    headers[column] if column < len(headers) else "",
                    row_label,
                ))
                bearing = False if is_header else (
                    is_claim_bearing(text, current_section_title)
                    or (column > 0 and bool(_TABLE_FACT_CONTEXT.search(context)))
                )
                add(
                    AuditUnitType.TABLE_CELL, start, end,
                    claim_bearing=bearing,
                    high_risk=False if is_header else is_high_risk_table_value(text, context),
                    recommendation=is_recommendation(text, current_section_title),
                    table_row=index,
                    table_column=column,
                    table_header=is_header,
                )
            index += 1
            continue
        if _is_table_separator(line.text):
            index += 1
            continue
        list_match = _LIST_ITEM.match(line.text.rstrip("\r\n"))
        if list_match:
            end = line.end
            next_index = index + 1
            while next_index < len(lines):
                continuation = lines[next_index]
                continuation_text = continuation.text.rstrip("\r\n")
                if not continuation_text.strip() or _LIST_ITEM.match(continuation_text):
                    break
                indentation = len(continuation_text) - len(continuation_text.lstrip())
                if indentation <= len(list_match.group("indent")):
                    break
                end = continuation.end
                next_index += 1
            add(AuditUnitType.LIST_ITEM, line.start, end)
            index = next_index
            continue
        if not stripped:
            index += 1
            continue

        # Consecutive ordinary lines form one Markdown paragraph.  Sentences,
        # not source-extractor atoms, are its edit boundaries.
        paragraph_start = line.start
        paragraph_end = line.end
        next_index = index + 1
        while next_index < len(lines):
            candidate = lines[next_index]
            candidate_stripped = candidate.text.strip()
            if (
                not candidate_stripped
                or candidate_stripped.startswith(("#", "```"))
                or _LIST_ITEM.match(candidate.text.rstrip("\r\n"))
                or next_index in table_rows
                or _is_table_separator(candidate.text)
            ):
                break
            paragraph_end = candidate.end
            next_index += 1
        for start, end in _sentence_spans(draft, paragraph_start, paragraph_end):
            add(AuditUnitType.PROSE_SENTENCE, start, end)
        index = next_index

    return units


def claim_text_span_in_unit(unit: WriterAuditUnit, claim_text: str) -> tuple[int, int] | None:
    """Return a unit-local coverage span, never an edit span."""

    visible_unit = markdown_visible_text(unit.text)
    visible_claim = markdown_visible_text(claim_text)
    aligned_unit = alignment_text(visible_unit)
    aligned_claim = alignment_text(visible_claim)
    if not aligned_claim:
        return None
    start = aligned_unit.find(aligned_claim)
    while start >= 0:
        before = aligned_unit[max(0, start - 80):start]
        end = start + len(aligned_claim)
        embedded = (
            (start > 0 and aligned_claim[0].isascii() and aligned_claim[0].isalnum()
             and aligned_unit[start - 1].isalnum())
            or (end < len(aligned_unit) and aligned_claim[-1].isascii()
                and aligned_claim[-1].isalnum() and aligned_unit[end].isalnum())
        )
        negated = re.search(
            r"\b(?:no|not|never|false|denies|denied|cannot|can\s+t|doesn\s+t|"
            r"don\s+t|didn\s+t|isn\s+t|aren\s+t|fails?\s+to|without|unknown|"
            r"unverified)\b[^.!?。！？]{0,30}$|"
            r"(?:并非|不是|否认|错误|没有|无法|不能|不|未|无)"
            r"[^。！？]{0,24}$",
            before,
            flags=re.IGNORECASE,
        )
        if not embedded and not negated:
            return start, start + len(aligned_claim)
        start = aligned_unit.find(aligned_claim, start + 1)
    return None


def find_claim_unit(units: Iterable[WriterAuditUnit], claim_text: str) -> WriterAuditUnit | None:
    matches = [unit for unit in units if claim_text_span_in_unit(unit, claim_text) is not None]
    return min(
        matches,
        key=lambda unit: (len(alignment_text(unit.text)), unit.ordinal),
        default=None,
    )


def has_uncovered_claim_signal(unit: WriterAuditUnit, claim_texts: Iterable[str]) -> bool:
    """Detect risky/factual residue after unit-local claim coverage is masked.

    This checker only decides the unit state.  It never deletes or returns a
    substring, which keeps coverage enforcement separate from rendering.
    """

    aligned = alignment_text(unit.text)
    if not aligned:
        return unit.claim_bearing
    covered = [False] * len(aligned)
    for claim_text in claim_texts:
        claim = alignment_text(claim_text)
        if not claim:
            continue
        start = aligned.find(claim)
        while start >= 0:
            for index in range(start, min(len(aligned), start + len(claim))):
                covered[index] = True
            start = aligned.find(claim, start + 1)
    residue = "".join(" " if covered[index] else char for index, char in enumerate(aligned))
    residue = re.sub(r"\s+", " ", residue).strip()
    if not residue:
        return False
    return bool(
        RECOMMENDATION_PATTERN.search(residue)
        or _IMPERATIVE_MIGRATION.search(residue)
        or is_high_risk(residue)
    )


def has_uncovered_recommendation_fact_signal(
    unit: WriterAuditUnit,
    audited_fact_texts: Iterable[str],
) -> bool:
    """Detect only new objective facts inside an authored recommendation.

    Already-audited factual text is masked for this diagnostic only.  The
    function never returns an edit span and never sends the recommendation or
    its premises through ClaimGate or Grounding a second time.
    """

    aligned = alignment_text(unit.text)
    if not aligned:
        return False
    covered = [False] * len(aligned)
    for fact_text in audited_fact_texts:
        fact = alignment_text(fact_text)
        if not fact:
            continue
        start = aligned.find(fact)
        while start >= 0:
            for index in range(start, min(len(aligned), start + len(fact))):
                covered[index] = True
            start = aligned.find(fact, start + 1)
    residue = "".join(
        " " if covered[index] else char for index, char in enumerate(aligned)
    )
    residue = re.sub(r"\s+", " ", residue).strip()
    if not residue:
        return False
    return bool(
        _NUMERIC_FACT_PATTERN.search(residue)
        or _RECOMMENDATION_OBJECTIVE_FACT_PATTERN.search(residue)
        or _COMPANY_ACTION_PATTERN.search(residue)
    )


def apply_unit_replacements(
    draft: str,
    replacements: dict[str, str | None],
    units: Iterable[WriterAuditUnit],
) -> str:
    """Apply only complete-unit replacements, from the end of the draft."""

    selected = [unit for unit in units if unit.unit_id in replacements]
    for unit in sorted(selected, key=lambda item: item.start_offset, reverse=True):
        replacement = replacements[unit.unit_id]
        if replacement is None:
            replacement = "—" if unit.unit_type is AuditUnitType.TABLE_CELL else ""
        if unit.unit_type is AuditUnitType.LIST_ITEM and replacement:
            match = _LIST_ITEM.match(unit.text.rstrip("\r\n"))
            newline = "\n" if unit.text.endswith("\n") else ""
            if match and not _LIST_ITEM.match(replacement):
                replacement = match.group(0) + replacement.strip() + newline
        elif unit.unit_type is AuditUnitType.HEADING and replacement:
            marker = re.match(r"^#{1,6}\s+", unit.text)
            if marker and not replacement.lstrip().startswith("#"):
                replacement = marker.group(0) + replacement.strip()
        draft = draft[:unit.start_offset] + replacement + draft[unit.end_offset:]
    return draft
