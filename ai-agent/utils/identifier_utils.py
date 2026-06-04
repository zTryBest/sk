# -*- coding: utf-8 -*-


def normalize_identifier(value: str | None) -> str:
    return (value or "").strip().upper()


def normalize_identifier_map(
        values: dict[str, str] | None
) -> dict[str, str]:
    if not values:
        return {}

    return {
        normalize_identifier(key): value
        for key, value in values.items()
    }
