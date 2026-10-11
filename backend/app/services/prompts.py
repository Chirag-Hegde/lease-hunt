"""Versioned prompt files: backend/app/prompts/<task>.md with YAML frontmatter.

Format:
    ---
    task: clause_risk
    version: 2
    ---
    <system prompt>
    ===USER===
    <user prompt template with {placeholders}>
"""

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"

_USER_DELIMITER = "===USER==="


@dataclass(frozen=True)
class Prompt:
    task: str
    version: str
    system: str
    template: str

    def render(self, **kwargs: object) -> str:
        return self.template.format(**kwargs)


@lru_cache(maxsize=64)
def load_prompt(task: str) -> Prompt:
    path = PROMPTS_DIR / f"{task}.md"
    raw = path.read_text(encoding="utf-8")
    if not raw.startswith("---"):
        raise ValueError(f"prompt file {path} is missing frontmatter")
    _, frontmatter, body = raw.split("---", 2)
    meta = yaml.safe_load(frontmatter)
    system, _, template = body.partition(_USER_DELIMITER)
    return Prompt(
        task=str(meta.get("task", task)),
        version=str(meta.get("version", "1")),
        system=system.strip(),
        template=template.strip(),
    )
