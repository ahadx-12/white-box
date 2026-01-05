from __future__ import annotations

import re
from collections.abc import Iterable

from trustai_core.packs.tariff.evidence.models import EvidenceSource
from trustai_core.packs.tariff.evidence.store import TariffEvidenceStore

TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9]+")
SECTION_BY_CHAPTER = {
    "64": "SEC12",
    "73": "SEC15",
    "84": "SEC16",
    "85": "SEC16",
}


class TariffEvidenceRetriever:
    def __init__(self, store: TariffEvidenceStore | None = None) -> None:
        self._store = store or TariffEvidenceStore()
        self._sources = list(self._store.list_sources())
        self._token_cache = {source.source_id: _tokenize(_source_text(source)) for source in self._sources}

    def retrieve(
        self,
        product_description: str,
        candidate_chapters: Iterable[str] | None = None,
        top_k: int = 10,
    ) -> list[EvidenceSource]:
        keywords = _tokenize(product_description)
        candidate_chapters = {chapter.strip() for chapter in candidate_chapters or [] if chapter}
        scored = []
        heading_chapters: set[str] = set()
        heading_scores: list[tuple[int, EvidenceSource]] = []
        for source in self._sources:
            score = len(keywords.intersection(self._token_cache[source.source_id]))
            chapter = _extract_chapter(source.source_id)
            if source.source_type in {"heading", "subheading"}:
                if score >= 2 or (chapter and chapter in candidate_chapters):
                    if chapter:
                        heading_chapters.add(chapter)
                heading_scores.append((score, source))
            scored.append((score, source))

        top_heading_chapters = {
            _extract_chapter(source.source_id)
            for score, source in sorted(
                heading_scores,
                key=lambda item: (-item[0], item[1].source_id),
            )[:top_k]
            if score > 0 and _extract_chapter(source.source_id)
        }
        heading_chapters.update(top_heading_chapters)

        forced = _collect_forced_sources(self._sources, heading_chapters, candidate_chapters)
        gri_sources = [source for source in self._sources if source.source_type == "gri"]
        forced.update({source.source_id: source for source in gri_sources})

        max_k = max(top_k, len(forced))
        ranked = sorted(
            [item for item in scored if item[1].source_id not in forced],
            key=lambda item: (-item[0], item[1].source_id),
        )

        result: list[EvidenceSource] = []
        for source in sorted(forced.values(), key=lambda item: item.source_id):
            result.append(source)
        for _, source in ranked:
            if len(result) >= max_k:
                break
            result.append(source)
        return result


def _collect_forced_sources(
    sources: Iterable[EvidenceSource],
    heading_chapters: set[str],
    candidate_chapters: set[str],
) -> dict[str, EvidenceSource]:
    forced: dict[str, EvidenceSource] = {}
    chapters = set(heading_chapters)
    chapters.update(candidate_chapters)
    sections = {SECTION_BY_CHAPTER.get(chapter) for chapter in chapters}
    for source in sources:
        chapter = _extract_chapter(source.source_id)
        if source.source_type in {"heading", "subheading"} and chapter in chapters:
            forced[source.source_id] = source
        if source.source_type == "chapter_note" and chapter in chapters:
            forced[source.source_id] = source
        if source.source_type == "section_note" and source.source_id.startswith(tuple(section for section in sections if section)):
            forced[source.source_id] = source
    return forced


def _source_text(source: EvidenceSource) -> str:
    return " ".join([source.title, source.text, source.source_id])


def _tokenize(text: str) -> set[str]:
    tokens = {token.lower() for token in TOKEN_PATTERN.findall(text)}
    return {token for token in tokens if len(token) >= 3}


def _extract_chapter(source_id: str) -> str | None:
    match = re.match(r"HTS\.(\d{2})", source_id)
    if match:
        return match.group(1)
    match = re.match(r"CH(\d{2})\.", source_id)
    if match:
        return match.group(1)
    return None
