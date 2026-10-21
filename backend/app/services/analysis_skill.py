"""Load validated, versioned Skill text for source-grounded analysis services."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path


MAX_ANALYSIS_SKILL_BYTES = 64 * 1024


class AnalysisSkillError(ValueError):
    """Raised when an analysis Skill file cannot safely be used."""


@dataclass(frozen=True)
class AnalysisSkillBundle:
    skill_file: Path
    version: str
    text: str
    sha256: str


def load_analysis_skill(skill_file: Path) -> AnalysisSkillBundle:
    """Read one non-template Skill file and expose its stable version metadata."""

    resolved_file = skill_file.resolve()
    if not resolved_file.is_file():
        raise AnalysisSkillError("분석 Skill 파일이 없습니다.")
    try:
        if resolved_file.stat().st_size > MAX_ANALYSIS_SKILL_BYTES:
            raise AnalysisSkillError("분석 Skill 파일이 너무 큽니다.")
        text = resolved_file.read_text(encoding="utf-8")
    except UnicodeDecodeError as error:
        raise AnalysisSkillError("분석 Skill 파일은 UTF-8이어야 합니다.") from error
    except OSError as error:
        raise AnalysisSkillError("분석 Skill 파일을 읽지 못했습니다.") from error

    if not text.strip():
        raise AnalysisSkillError("분석 Skill 파일이 비어 있습니다.")
    if "<!--" in text:
        raise AnalysisSkillError("분석 Skill 파일에 미완성 placeholder가 있습니다.")

    frontmatter, delimiter, body = text.partition("\n---\n")
    if not delimiter or not frontmatter.startswith("---\n"):
        raise AnalysisSkillError("분석 Skill frontmatter가 필요합니다.")
    if not body.strip():
        raise AnalysisSkillError("분석 Skill 본문 규칙이 필요합니다.")
    metadata = _parse_frontmatter(frontmatter[4:])
    name = metadata.get("name", "").strip()
    version = metadata.get("version", "").strip()
    if not name or not version:
        raise AnalysisSkillError("분석 Skill에는 name과 version이 필요합니다.")

    return AnalysisSkillBundle(
        skill_file=resolved_file,
        version=version,
        text=body.strip(),
        sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
    )


def _parse_frontmatter(frontmatter: str) -> dict[str, str]:
    metadata: dict[str, str] = {}
    for line in frontmatter.splitlines():
        key, separator, value = line.partition(":")
        if not separator:
            continue
        normalized_key = key.strip()
        if normalized_key in {"name", "version"}:
            metadata[normalized_key] = value.strip().strip('"\'')
    return metadata
