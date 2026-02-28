from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.engine.rules.base import BaseRule

_REGISTRY: dict[str, "BaseRule"] = {}


def register(rule: "BaseRule") -> "BaseRule":
    _REGISTRY[rule.rule_id] = rule
    return rule


def get_all() -> list["BaseRule"]:
    return list(_REGISTRY.values())


def get_by_id(rule_id: str) -> "BaseRule | None":
    return _REGISTRY.get(rule_id)
