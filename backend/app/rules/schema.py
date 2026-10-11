"""Jurisdiction rule packs: versioned YAML files, one per state.

A rule fires when any trigger regex matches the clause text (and no safe
pattern does). Rules without a verified official source are marked
verified=false and must be presented as "worth asking about", never as
"illegal"."""

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

from app.agents.contracts import ClauseType, Severity

RULES_DIR = Path(__file__).resolve().parent


@dataclass(frozen=True)
class JurisdictionRule:
    id: str
    clause_type: ClauseType
    severity: Severity
    triggers: tuple[str, ...]
    safe_patterns: tuple[str, ...]
    explanation: str
    why_it_matters: str
    suggested_ask: str | None
    jurisdiction_note: str
    source_url: str | None
    verified: bool

    def matches(self, text: str) -> bool:
        lowered = text.lower()
        if any(re.search(p, lowered, re.IGNORECASE) for p in self.safe_patterns):
            return False
        return any(re.search(p, lowered, re.IGNORECASE) for p in self.triggers)


@dataclass(frozen=True)
class ClauseDefault:
    severity: Severity
    explanation: str
    why_it_matters: str
    suggested_ask: str | None


@dataclass(frozen=True)
class RulePack:
    state: str
    version: str
    rules: tuple[JurisdictionRule, ...]
    defaults: dict[str, ClauseDefault]

    def rules_for(self, clause_type: ClauseType) -> list[JurisdictionRule]:
        return [r for r in self.rules if r.clause_type == clause_type]

    def default_for(self, clause_type: ClauseType) -> ClauseDefault | None:
        return self.defaults.get(clause_type)


@lru_cache(maxsize=8)
def load_rule_pack(state: str = "california") -> RulePack:
    path = RULES_DIR / f"{state}.yaml"
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    rules = tuple(
        JurisdictionRule(
            id=r["id"],
            clause_type=r["clause_type"],
            severity=r["severity"],
            triggers=tuple(r.get("triggers", [])),
            safe_patterns=tuple(r.get("safe_patterns", [])),
            explanation=r["explanation"],
            why_it_matters=r["why_it_matters"],
            suggested_ask=r.get("suggested_ask"),
            jurisdiction_note=r["jurisdiction_note"],
            source_url=r.get("source_url"),
            verified=bool(r.get("verified", False)),
        )
        for r in raw.get("rules", [])
    )
    defaults = {
        clause_type: ClauseDefault(
            severity=d.get("severity", "info"),
            explanation=d["explanation"],
            why_it_matters=d["why_it_matters"],
            suggested_ask=d.get("suggested_ask"),
        )
        for clause_type, d in raw.get("defaults", {}).items()
    }
    return RulePack(
        state=str(raw.get("state", state)),
        version=str(raw.get("version", "1")),
        rules=rules,
        defaults=defaults,
    )
