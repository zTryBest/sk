# -*- coding: utf-8 -*-

import re
from dataclasses import dataclass


@dataclass
class ParsedVersion:
    raw: str
    normalized: str
    parts: list[int]

    @property
    def major(self):
        if not self.parts:
            return None

        return self.parts[0]


def parse_version(version: str) -> ParsedVersion:
    raw = version or ""
    normalized = raw.strip().lower()
    normalized = re.sub(r"^[vV]", "", normalized)
    parts = [
        int(item)
        for item in re.findall(r"\d+", normalized)
    ]

    return ParsedVersion(
        raw=raw,
        normalized=normalized,
        parts=parts
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


def sort_versions(
        versions: list[str]
) -> list[str]:
    return sorted(
        versions,
        key=lambda item: parse_version(item).parts
    )


def find_nearest_doc_version(
        component_version: str,
        doc_versions: list[str]
):
    requested = parse_version(
        component_version
    )

    if not doc_versions:
        return {
            "doc_version": None,
            "match_level": "NO_DOC_VERSION",
            "confidence": 0.0,
            "risk": "当前组件没有任何接口文档版本。"
        }

    exact = [
        item
        for item in doc_versions
        if parse_version(item).normalized == requested.normalized
    ]

    if exact:
        return {
            "doc_version": exact[0],
            "match_level": "EXACT",
            "confidence": 1.0,
            "risk": ""
        }

    parsed_docs = [
        (
            item,
            parse_version(item)
        )
        for item in doc_versions
    ]

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
                f"{component_version} 无精确接口文档，当前使用同 major "
                f"最近低版本 {selected[0]} 的契约推断。"
            )
        }

    higher = [
        item
        for item in same_major
        if compare_version_parts(
            item[1].parts,
            requested.parts
        ) > 0
    ]

    if higher:
        selected = min(
            higher,
            key=lambda item: item[1].parts
        )
        return {
            "doc_version": selected[0],
            "match_level": "NEAREST_HIGHER_SAME_MAJOR",
            "confidence": 0.6,
            "risk": (
                f"{component_version} 无精确接口文档，当前使用同 major "
                f"最近高版本 {selected[0]} 的契约推断，请注意该版本可能包含新增接口。"
            )
        }

    return {
        "doc_version": None,
        "match_level": "NO_SAME_MAJOR_DOC_VERSION",
        "confidence": 0.0,
        "risk": (
            f"{component_version} 无同 major 接口文档，未自动跨 major 兜底。"
        )
    }
