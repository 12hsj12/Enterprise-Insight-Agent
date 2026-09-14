"""Conservative, deterministic enrichment of already-retrieved web evidence."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Iterable
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from .models import MetadataProvenanceKind, SourceRole


@dataclass(frozen=True)
class KnownSite:
    publisher: str
    role: SourceRole
    aliases: tuple[str, ...] = ()


# Exact hosts only. Hosting/community platforms and broad suffixes are excluded.
KNOWN_SITES: dict[str, KnownSite] = {
    "openai.com": KnownSite("OpenAI", SourceRole.FIRST_PARTY),
    "developers.openai.com": KnownSite(
        "OpenAI", SourceRole.FIRST_PARTY, ("OpenAI API", "OpenAI Platform")
    ),
    "docs.openai.com": KnownSite(
        "OpenAI", SourceRole.FIRST_PARTY, ("OpenAI API", "OpenAI Platform")
    ),
    "aws.amazon.com": KnownSite(
        "Amazon Web Services", SourceRole.FIRST_PARTY,
        ("AWS", "AWS Documentation", "Amazon Web Services, Inc."),
    ),
    "docs.aws.amazon.com": KnownSite(
        "Amazon Web Services", SourceRole.FIRST_PARTY,
        ("AWS", "AWS Documentation", "Amazon Web Services, Inc."),
    ),
    "cloud.google.com": KnownSite(
        "Google Cloud", SourceRole.FIRST_PARTY, ("Google Cloud Documentation",)
    ),
    "learn.microsoft.com": KnownSite(
        "Microsoft", SourceRole.FIRST_PARTY, ("Microsoft Learn",)
    ),
    "www.nist.gov": KnownSite(
        "National Institute of Standards and Technology",
        SourceRole.GOVERNMENT_OR_STANDARD_BODY,
        ("NIST",),
    ),
    "nist.gov": KnownSite(
        "National Institute of Standards and Technology",
        SourceRole.GOVERNMENT_OR_STANDARD_BODY,
        ("NIST",),
    ),
}

_PUBLISHED_LABEL = re.compile(
    r"(?im)(?:^|\n)\s*(?:published(?:\s+(?:on|date))?|publication\s+date|"
    r"发布日期)\s*[:：]?\s*(?:\n\s*)?"
    r"(?P<date>\d{4}[年/-]\d{1,2}[月/-]\d{1,2}日?"
    r"|[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4})(?=\s|$|[·|])"
)
_UPDATED_LABEL = re.compile(
    r"(?im)(?:^|\n)\s*(?:updated(?:\s+(?:on|date))?|last\s+updated|"
    r"更新日期)\s*[:：]?\s*(?:\n\s*)?"
    r"(?P<date>\d{4}[年/-]\d{1,2}[月/-]\d{1,2}日?"
    r"|[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4})(?=\s|$|[·|])"
)

_DATE_FORMATS = (
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%B %d, %Y",
    "%B %d %Y",
    "%b %d, %Y",
    "%b %d %Y",
)


def _clean_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    value = " ".join(value.split()).strip()
    return value or None


def _parse_date(value: Any) -> str | None:
    value = _clean_text(value)
    if value is None:
        return None
    candidate = value.replace("年", "-").replace("月", "-").replace("日", "")
    iso_candidate = candidate[:10]
    try:
        return date.fromisoformat(iso_candidate).isoformat()
    except ValueError:
        pass
    try:
        return datetime.strptime(candidate, "%Y-%m-%d").date().isoformat()
    except ValueError:
        pass
    without_time = re.split(r"[T\s]\d{1,2}:\d{2}", value, maxsplit=1)[0]
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(without_time.strip(), fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _name(value: Any) -> str | None:
    if isinstance(value, dict):
        return _clean_text(value.get("name"))
    if isinstance(value, list):
        for item in value:
            if resolved := _name(item):
                return resolved
        return None
    return _clean_text(value)


def _jsonld_objects(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        if "@graph" in value:
            yield from _jsonld_objects(value["@graph"])
    elif isinstance(value, list):
        for item in value:
            yield from _jsonld_objects(item)


def _schema_types(item: dict[str, Any]) -> set[str]:
    raw = item.get("@type", ())
    values = raw if isinstance(raw, list) else (raw,)
    return {str(value).casefold() for value in values if value}


def _schema_url(item: dict[str, Any]) -> str | None:
    for raw in (item.get("url"), item.get("mainEntityOfPage")):
        if isinstance(raw, dict):
            raw = raw.get("@id") or raw.get("url")
        if value := _clean_text(raw):
            return value
    return None


def _normalized_page_url(value: str) -> tuple[str, str, str, str]:
    parsed = urlparse(value)
    return (
        parsed.scheme.casefold(),
        (parsed.hostname or "").casefold(),
        parsed.path.rstrip("/") or "/",
        parsed.query,
    )


def extract_structured_html_metadata(
    html: str,
    *,
    page_url: str | None = None,
) -> dict[str, Any]:
    """Extract explicit metadata before main-content cleaning removes the head."""

    if not isinstance(html, str) or not html.strip():
        return {}
    soup = BeautifulSoup(html, "lxml")
    result: dict[str, str] = {}
    meta_values: dict[str, str] = {}
    for tag in soup.find_all("meta"):
        key = _clean_text(tag.get("property") or tag.get("name") or tag.get("itemprop"))
        value = _clean_text(tag.get("content"))
        if key and value:
            meta_values[key.casefold()] = value

    for key in ("article:published_time", "og:published_time", "datepublished"):
        if parsed := _parse_date(meta_values.get(key)):
            result["publication_date"] = parsed
            break
    for key in ("article:modified_time", "og:updated_time", "datemodified"):
        if parsed := _parse_date(meta_values.get(key)):
            result["updated_date"] = parsed
            break
    for key in ("publisher", "article:publisher"):
        if value := _clean_text(meta_values.get(key)):
            result["publisher"] = value
            break
    if value := _clean_text(meta_values.get("og:site_name")):
        result["site_name"] = value
    for key in ("author", "article:author", "byl"):
        if value := _clean_text(meta_values.get(key)):
            result["author"] = value
            break

    schema_objects = []
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            payload = json.loads(script.string or script.get_text() or "")
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        schema_objects.extend(_jsonld_objects(payload))

    article_types = {"article", "newsarticle", "blogposting", "report", "techarticle"}
    article_objects = [
        item for item in schema_objects if _schema_types(item) & article_types
    ]
    selected_article = None
    if page_url:
        expected_url = _normalized_page_url(page_url)
        url_bearing = [item for item in article_objects if _schema_url(item)]
        matching = [
            item for item in url_bearing
            if (item_url := _schema_url(item))
            and _normalized_page_url(item_url) == expected_url
        ]
        if len(matching) == 1:
            selected_article = matching[0]
        elif len(matching) > 1:
            result["metadata_conflict"] = True
        elif url_bearing:
            # An explicit non-matching URL identifies another article. Never
            # fall back merely because it is the only JSON-LD article object.
            result["metadata_conflict"] = True
    if (
        selected_article is None
        and len(article_objects) == 1
        and (not page_url or not _schema_url(article_objects[0]))
    ):
        selected_article = article_objects[0]
    elif selected_article is None and len(article_objects) > 1:
        result["metadata_conflict"] = True

    if selected_article is not None:
        if "publication_date" not in result:
            parsed = _parse_date(selected_article.get("datePublished"))
            if parsed:
                result["publication_date"] = parsed
        if "updated_date" not in result:
            parsed = _parse_date(selected_article.get("dateModified"))
            if parsed:
                result["updated_date"] = parsed
        if "publisher" not in result:
            publisher = _name(selected_article.get("publisher"))
            if publisher:
                result["publisher"] = publisher
        if "author" not in result:
            author = _name(selected_article.get("author"))
            if author:
                result["author"] = author
    return result


def _title_variants(title: str) -> tuple[str, ...]:
    values = [" ".join(title.split())]
    for separator in (" | ", " - ", " — ", " – "):
        if separator in values[0]:
            values.append(values[0].split(separator, 1)[0].strip())
    return tuple(value for value in dict.fromkeys(values) if len(value) >= 6)


def extract_visible_dates(text: str, *, title: str | None = None) -> dict[str, str]:
    """Accept only explicit dates associated with the current article header."""

    if not isinstance(text, str) or not isinstance(title, str) or not title.strip():
        return {}
    header = text[:5_000]
    lowered = header.casefold()
    matches = [
        (position, variant)
        for variant in _title_variants(title)
        if (position := lowered.find(variant.casefold())) >= 0
    ]
    if not matches:
        return {}
    start, matched_title = min(matches, key=lambda item: (item[0], -len(item[1])))
    boundary_pattern = (
        r"(?im)(?:^|\n)\s*(?:related articles?|recommended|you may also like|"
        r"latest articles?|comments?|sidebar|相关文章|推荐阅读)\s*[:：]?\s*(?:\n|$)"
    )
    if re.search(boundary_pattern, header[:start]):
        return {}
    # Plain extracted text has no DOM ownership. To avoid assigning a nearby
    # card's date to the page, accept only a date label that is the first
    # non-whitespace content immediately following the current title.
    header = header[start + len(matched_title) :].lstrip()
    result = {}
    published = _PUBLISHED_LABEL.match(header)
    updated = _UPDATED_LABEL.match(header)
    if published and (value := _parse_date(published.group("date"))):
        result["publication_date"] = value
        # A paired update label may immediately follow the published value.
        updated = _UPDATED_LABEL.match(header[published.end() :].lstrip())
    if updated and (value := _parse_date(updated.group("date"))):
        result["updated_date"] = value
    return result


def search_result_metadata(result: dict[str, Any]) -> dict[str, str]:
    """Normalize explicit provider metadata without treating generic timestamps as dates."""

    normalized = {}
    aliases = {
        "publication_date": ("publication_date", "published_date", "published_at", "date_published"),
        "updated_date": ("updated_date", "modified_date", "updated_at", "date_modified"),
        "publisher": ("publisher", "site_name"),
        "author": ("author", "author_name"),
    }
    for target, keys in aliases.items():
        for key in keys:
            value = result.get(key)
            resolved = _parse_date(value) if target.endswith("date") else _clean_text(value)
            if resolved:
                normalized[target] = resolved
                break
    return normalized


def _same_publisher(value: str, site: KnownSite) -> bool:
    key = re.sub(r"[^a-z0-9]", "", value.casefold())
    accepted = (site.publisher, *site.aliases)
    return any(key == re.sub(r"[^a-z0-9]", "", item.casefold()) for item in accepted)


def enrich_page_metadata(
    page: dict[str, Any],
    *,
    structured_metadata: dict[str, Any] | None = None,
    provider_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a copy with deterministic publisher/date resolution and provenance."""

    enriched = dict(page)
    structured = structured_metadata or {}
    provider = provider_metadata or {}
    visible = extract_visible_dates(
        str(page.get("raw_content") or page.get("content") or ""),
        title=_clean_text(page.get("title")),
    )
    host = (urlparse(str(page.get("url") or page.get("source") or "")).hostname or "").casefold()
    site = KNOWN_SITES.get(host)
    conflict = bool(
        page.get("metadata_conflict", False)
        or structured.get("metadata_conflict", False)
        or provider.get("metadata_conflict", False)
    )
    provenance = dict(page.get("metadata_provenance") or {})

    existing_publisher = _clean_text(page.get("publisher"))
    existing_identity = next(
        (
            value
            for field in ("source_owner", "source_organization")
            if (value := _clean_text(page.get(field)))
        ),
        None,
    )
    structured_publisher = _clean_text(structured.get("publisher"))
    structured_site_name = _clean_text(structured.get("site_name"))
    provider_publisher = _clean_text(provider.get("publisher"))
    candidates = [
        value
        for value in (
            structured_publisher,
            site.publisher if site else None,
            existing_identity,
            existing_publisher,
            structured_site_name,
            provider_publisher,
        )
        if value
    ]
    if len({value.casefold() for value in candidates}) > 1:
        aliases_match = site and all(_same_publisher(value, site) for value in candidates)
        conflict = conflict or not aliases_match
    if structured_publisher:
        publisher = structured_publisher
        provenance["publisher"] = MetadataProvenanceKind.HTML_STRUCTURED_METADATA.value
    elif site:
        publisher = site.publisher
        provenance["publisher"] = MetadataProvenanceKind.KNOWN_SITE_METADATA.value
    elif existing_publisher:
        publisher = existing_publisher
    elif structured_site_name:
        publisher = structured_site_name
        provenance["publisher"] = MetadataProvenanceKind.HTML_STRUCTURED_METADATA.value
    elif provider_publisher:
        publisher = provider_publisher
        provenance["publisher"] = MetadataProvenanceKind.SEARCH_RESULT_METADATA.value
    else:
        publisher = None
    if publisher:
        enriched["publisher"] = publisher
        # Existing qualification consumes source_organization before publisher.
        enriched.setdefault("source_organization", publisher)

    if site and publisher and _same_publisher(publisher, site) and not conflict:
        enriched["source_role"] = site.role.value
    elif publisher:
        enriched["source_role"] = SourceRole.THIRD_PARTY.value
    else:
        enriched["source_role"] = SourceRole.UNKNOWN.value

    for field in ("publication_date", "updated_date"):
        structured_value = _parse_date(structured.get(field))
        visible_value = visible.get(field)
        existing_value = _parse_date(page.get(field))
        provider_value = _parse_date(provider.get(field))
        date_candidates = [value for value in (
            structured_value, visible_value, existing_value, provider_value
        ) if value]
        if len(set(date_candidates)) > 1:
            conflict = True
        if structured_value:
            resolved = structured_value
            source = MetadataProvenanceKind.HTML_STRUCTURED_METADATA
        elif visible_value:
            resolved = visible_value
            source = MetadataProvenanceKind.HTML_VISIBLE_DATE
        elif existing_value:
            resolved = existing_value
            source = None
        elif provider_value:
            resolved = provider_value
            source = MetadataProvenanceKind.SEARCH_RESULT_METADATA
        else:
            resolved = None
            source = None
        if resolved:
            enriched[field] = resolved
            if source:
                provenance[field] = source.value

    structured_author = _clean_text(structured.get("author"))
    existing_author = _clean_text(page.get("author"))
    provider_author = _clean_text(provider.get("author"))
    author = structured_author or existing_author or provider_author
    if author:
        enriched["author"] = author
        if structured_author:
            provenance["author"] = MetadataProvenanceKind.HTML_STRUCTURED_METADATA.value
        elif provider_author and not existing_author:
            provenance["author"] = MetadataProvenanceKind.SEARCH_RESULT_METADATA.value

    enriched["metadata_provenance"] = provenance
    enriched["metadata_conflict"] = conflict
    return enriched
