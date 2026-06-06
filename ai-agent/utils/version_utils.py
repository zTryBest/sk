# -*- coding: utf-8 -*-

import re
from dataclasses import dataclass


@dataclass
class ParsedVersion:
    raw: str
    normalized: str
    parts: list[int]
    comparable: bool = True

    @property
    def major(self):
        if not self.parts:
            return None
        return self.parts[0]


def parse_version(version: str) -> ParsedVersion:
    raw = version or ""
    normalized = raw.strip().lower()
    normalized = re.sub(r"^[vV]", "", normalized)
    comparable = bool(
        re.fullmatch(r"\d+(?:\.\d+)*", normalized)
    )
    parts = [
        int(item)
        for item in re.findall(r"\d+", normalized)
    ]

    return ParsedVersion(
        raw=raw,
        normalized=normalized,
        parts=parts,
        comparable=comparable and bool(parts)
    )


def compare_version_parts(
        left: list[int],
        right: list[int]
) -> int:
    max_len = max(
        len(left),
        len(right)
    )

    padded_left = left + [0] * (max_len - len(left))
    padded_right = right + [0] * (max_len - len(right))

    if padded_left == padded_right:
        return 0

    return (
        1
        if padded_left > padded_right
        else -1
    )


def compare_versions(
        left: str,
        right: str
) -> int | None:
    parsed_left = parse_version(left)
    parsed_right = parse_version(right)
    if (
            not parsed_left.comparable
            or not parsed_right.comparable
    ):
        return None

    return compare_version_parts(
        parsed_left.parts,
        parsed_right.parts
    )


def version_lte(
        left: str,
        right: str
) -> bool:
    compared = compare_versions(left, right)
    return compared is not None and compared <= 0


def version_lt(
        left: str,
        right: str
) -> bool:
    compared = compare_versions(left, right)
    return compared is not None and compared < 0


def sort_versions(
        versions: list[str]
) -> list[str]:
    return sorted(
        versions,
        key=lambda item: parse_version(item).parts
    )


def _comparable_doc_versions(
        doc_versions: list[str]
) -> list[tuple[str, ParsedVersion]]:
    return [
        (
            item,
            parsed
        )
        for item in doc_versions
        for parsed in [parse_version(item)]
        if parsed.comparable
    ]


def find_nearest_doc_version(
        component_version: str,
        doc_versions: list[str]
):
    requested = parse_version(
        component_version
    )

    if not requested.comparable:
        return {
            "doc_version": None,
            "match_level": "INCOMPARABLE_VERSION",
            "confidence": 0.0,
            "risk": (
                f"Version {component_version} is not a plain numeric version; "
                "automatic version fallback is disabled."
            )
        }

    if not doc_versions:
        return {
            "doc_version": None,
            "match_level": "NO_DOC_VERSION",
            "confidence": 0.0,
            "risk": "No API document version exists for the current component."
        }

    parsed_docs = _comparable_doc_versions(
        doc_versions
    )

    exact = [
        item
        for item in parsed_docs
        if compare_version_parts(
            item[1].parts,
            requested.parts
        ) == 0
    ]

    if exact:
        return {
            "doc_version": exact[0][0],
            "match_level": "EXACT",
            "confidence": 1.0,
            "risk": ""
        }

    same_major = [
        item
        for item in parsed_docs
        if (
            requested.major is not None
            and item[1].major == requested.major
            and item[1].parts
        )
    ]

    lower = [
        item
        for item in same_major
        if compare_version_parts(
            item[1].parts,
            requested.parts
        ) < 0
    ]

    if lower:
        selected = max(
            lower,
            key=lambda item: item[1].parts
        )
        return {
            "doc_version": selected[0],
            "match_level": "NEAREST_LOWER_SAME_MAJOR",
            "confidence": 0.75,
            "risk": (
                f"{component_version} has no exact API document; "
                f"using nearest lower same-major version {selected[0]}."
            )
        }

    return {
        "doc_version": None,
        "match_level": "NO_COMPATIBLE_DOC_VERSION",
        "confidence": 0.0,
        "risk": (
            f"{component_version} has no exact or lower same-major API document. "
            "Higher document versions are not allowed."
        )
    }
