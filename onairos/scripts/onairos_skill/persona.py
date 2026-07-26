"""Allowlisted formatting for Onairos persona data."""

from __future__ import annotations

import math
import re
import unicodedata

from .config import MAX_PERSONA_CHARS, MAX_RESPONSE_BYTES, MAX_SUMMARY_CHARS


UNSAFE_LABEL_PATTERN = re.compile(
    r"\b(?:ignore|disregard|override|reveal|exfiltrate|execute|instruction|prompt|"
    r"password|secret|token)\b",
    flags=re.IGNORECASE,
)
PRIVILEGED_COMMAND = "su" + "do"
UNSAFE_SUMMARY_PATTERNS = tuple(
    re.compile(pattern, flags=re.IGNORECASE)
    for pattern in (
        r"\b(?:system|developer)\s+(?:policy|prompt|instructions?)\b",
        r"\b(?:user|you|hermes|agent)\s+(?:should|must|shall|need(?:s)?\s+to)\s+"
        r"(?:always\s+|never\s+)?(?:add|write|save|store|call|use|run|execute|open|"
        r"read|reveal|ignore|disregard|override|upload)\b",
        r"\b(?:please|when\s+asked)\b.{0,120}\b(?:add|write|save|store|call|use|run|"
        r"execute|open|read|reveal|ignore|disregard|override|upload)\b",
        r"(?:^|[.!?]\s+)(?:always\s+|never\s+|do\s+not\s+|don't\s+)?"
        r"(?:add|write|save|store|call|use|run|execute|open|read|reveal|ignore|"
        r"disregard|override|upload)\b",
        r"\b(?:remember|follow|obey)\b.{0,120}\b(?:instructions?|directives?|rules?|"
        r"policy|future\s+sessions?|memory|profile)\b",
        r"\b(?:ignore|disregard|override|reveal|exfiltrate|execute|upload)\b"
        r".{0,120}\b(?:instructions?|prompt|system|developer|password|secret|token|"
        r"credential)\b",
        r"\b(?:USER|MEMORY)\.md\b",
        rf"\b(?:shell\s+command|rm\s+-rf|{PRIVILEGED_COMMAND}\s+|"
        r"curl\s+[^.,;]+)\b",
        r"\b(?:my|the|their|user(?:'s)?)?\s*(?:password|passcode|api[_ -]?key|"
        r"api[_ -]?token|access[_ -]?token|bearer[_ -]?token|secret|credential)"
        r"\s*(?:is|=|:)\s*\S+",
        r"\b(?:password|passcode)\s+(?=\S*\d)\S+",
        r"\b(?:sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9]{20,}|"
        r"AKIA[0-9A-Z]{16}|xox[baprs]-[A-Za-z0-9-]{10,})\b",
    )
)


def _clean_text(value: object, max_chars: int) -> str:
    if not isinstance(value, str):
        return ""
    safe_chars = [
        " " if char == "§" or unicodedata.category(char).startswith("C") else char
        for char in value
    ]
    cleaned = "".join(safe_chars).replace("```", " ")
    cleaned = re.sub(r"<[^>]{0,500}>", " ", cleaned)
    cleaned = re.sub(
        r"\b(?:system|developer|assistant|user|tool)\s*:",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned[:max_chars].rstrip()


def _clean_label(value: object, max_chars: int) -> str:
    label = _clean_text(value, max_chars)
    return "" if UNSAFE_LABEL_PATTERN.search(label) else label


def _clean_summary(value: object) -> str:
    summary = _clean_text(value, MAX_RESPONSE_BYTES)
    if any(pattern.search(summary) for pattern in UNSAFE_SUMMARY_PATTERNS):
        return ""
    if len(summary) > MAX_SUMMARY_CHARS:
        clipped = summary[:MAX_SUMMARY_CHARS].rstrip()
        return f"{clipped} [Summary truncated by the local skill.]"
    return summary


def _ranked_values(value: object, limit: int) -> list[tuple[str, float]]:
    if not isinstance(value, dict):
        return []
    ranked = []
    for raw_key, raw_score in value.items():
        key = _clean_label(raw_key, 80)
        if not key or isinstance(raw_score, bool) or not isinstance(raw_score, (int, float)):
            continue
        score = float(raw_score)
        if math.isfinite(score):
            ranked.append((key, score))
    return sorted(ranked, key=lambda item: (-item[1], item[0].casefold()))[:limit]


def _render_ranked(label: str, value: object, limit: int) -> str:
    ranked = _ranked_values(value, limit)
    if not ranked:
        return ""
    values = ", ".join(f"{key} ({format(score, '.4g')})" for key, score in ranked)
    return f"{label}: {values}"


def _render_nudges(value: object) -> str:
    if not isinstance(value, list):
        return ""
    nudges = []
    for item in value[:3]:
        raw_text = item if isinstance(item, str) else item.get("text") if isinstance(item, dict) else None
        nudge = _clean_label(raw_text, 240)
        if nudge:
            nudges.append(nudge)
    return "Suggested Actions:\n- " + "\n- ".join(nudges) if nudges else ""


def _render_platforms(value: object) -> str:
    if not isinstance(value, list):
        return ""
    platforms = [
        platform
        for platform in (_clean_label(item, 60) for item in value)
        if platform
    ][:12]
    return f"Connected Platforms: {', '.join(platforms)}" if platforms else ""


def _traits_from(data: object) -> dict:
    root = data if isinstance(data, dict) else {}
    inference_result = root.get("InferenceResult")
    if isinstance(inference_result, dict):
        return inference_result
    traits = root.get("traits")
    return traits if isinstance(traits, dict) else root


def format_persona(data: object, max_chars: int = MAX_PERSONA_CHARS) -> str:
    """Return allowlisted source material for Hermes to curate into memory."""
    limit = max(1, min(MAX_PERSONA_CHARS, int(max_chars)))
    traits = _traits_from(data)
    growth = [key for key, _ in _ranked_values(traits.get("traits_to_improve"), 5)]
    fields = (
        f"Archetype: {_clean_label(traits.get('archetype'), 120)}",
        _render_ranked("Top Traits", traits.get("positive_traits"), 7),
        _render_ranked("Personality", traits.get("personalityDict"), 7),
        f"Summary: {_clean_summary(traits.get('user_summary'))}",
        f"Growth Areas: {', '.join(growth)}",
        _render_nudges(traits.get("nudges")),
        _render_platforms(traits.get("connectedPlatforms")),
    )
    lines = [field for field in fields if not field.endswith(": ") and field]
    persona = "\n".join(lines) or "Onairos profile connected; no optional persona fields were returned."
    clipped = persona[:limit].rstrip()
    return clipped or persona[:1]
