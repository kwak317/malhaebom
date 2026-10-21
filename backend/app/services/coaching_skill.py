"""고정 코칭 Skill 묶음 로딩과 서버 문맥 검증."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.coaching import QuestionContext


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SKILL_FILE = PROJECT_ROOT / "skills" / "interview-coach" / "SKILL.md"


class CoachingSkillError(ValueError):
    """Skill 파일 또는 서버 질문 문맥이 고정 계약과 맞지 않는 오류."""


class SkillModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class QuestionTypeDefinition(SkillModel):
    reference: str = Field(min_length=1)
    allowed_criterion_ids: list[str] = Field(min_length=1)
    criteria_version: str | None = Field(default=None, min_length=1)


class CriterionDefinition(SkillModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    met: str = Field(min_length=1)
    partial: str = Field(min_length=1)
    not_observed: str = Field(min_length=1)
    undetermined: str = Field(min_length=1)
    needed: str = Field(min_length=1)


class CriteriaCatalog(SkillModel):
    schema_version: Literal[1]
    skill_version: str = Field(min_length=1)
    criteria_version: str = Field(min_length=1)
    review_status: Literal["team_draft", "externally_reviewed"]
    scope: str = Field(min_length=1)
    question_types: dict[str, QuestionTypeDefinition]
    criteria: list[CriterionDefinition] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_references(self) -> Self:
        criterion_ids = [item.id for item in self.criteria]
        if len(criterion_ids) != len(set(criterion_ids)):
            raise ValueError("criteria에 중복 criterion id가 있습니다")
        known_ids = set(criterion_ids)
        for question_type, definition in self.question_types.items():
            active_ids = definition.allowed_criterion_ids
            if len(active_ids) != len(set(active_ids)):
                raise ValueError(f"{question_type}에 중복 criterion id가 있습니다")
            unknown = sorted(set(active_ids) - known_ids)
            if unknown:
                raise ValueError(
                    f"{question_type}가 알 수 없는 criterion id를 참조합니다: "
                    + ", ".join(unknown)
                )
        return self


@dataclass(frozen=True)
class SkillBundle:
    skill_file: Path
    catalog: CriteriaCatalog
    rules_text: str
    sha256: str

    @property
    def criterion_ids(self) -> set[str]:
        return {item.id for item in self.catalog.criteria}

    def validate_question_context(self, question: QuestionContext) -> None:
        definition = self.catalog.question_types.get(question.question_type)
        if definition is None:
            raise CoachingSkillError(
                f"지원하지 않는 question_type입니다: {question.question_type}"
            )
        expected_version = definition.criteria_version or self.catalog.criteria_version
        if question.criteria_version != expected_version:
            raise CoachingSkillError(
                "질문의 criteria_version이 Skill 카탈로그와 다릅니다: "
                f"{question.criteria_version} != {expected_version}"
            )
        active_ids = question.active_criterion_ids
        if len(active_ids) != len(set(active_ids)):
            raise CoachingSkillError("질문에 중복 active criterion id가 있습니다")
        unknown = sorted(set(active_ids) - set(definition.allowed_criterion_ids))
        if unknown:
            raise CoachingSkillError(
                "질문에 허용되지 않은 active criterion id가 있습니다: "
                + ", ".join(unknown)
            )


def load_skill_bundle(skill_file: Path = DEFAULT_SKILL_FILE) -> SkillBundle:
    skill_file = skill_file.resolve()
    root = skill_file.parent
    criteria_file = root / "criteria.json"
    if not skill_file.is_file() or not criteria_file.is_file():
        raise CoachingSkillError("SKILL.md와 criteria.json이 모두 필요합니다")

    skill_text = skill_file.read_text(encoding="utf-8")
    if not skill_text.startswith("---\n") or "# {도메인} Skill" in skill_text:
        raise CoachingSkillError("SKILL.md frontmatter가 없거나 템플릿 상태입니다")
    if "<!--" in skill_text:
        raise CoachingSkillError("SKILL.md에 미완성 placeholder 주석이 있습니다")

    try:
        catalog = CriteriaCatalog.model_validate_json(
            criteria_file.read_text(encoding="utf-8")
        )
    except Exception as error:
        raise CoachingSkillError(
            f"criteria.json이 유효하지 않습니다: {error}"
        ) from error

    referenced_texts: list[tuple[str, str]] = []
    for definition in catalog.question_types.values():
        reference_file = (root / definition.reference).resolve()
        try:
            reference_file.relative_to(root)
        except ValueError as error:
            raise CoachingSkillError(
                "Skill 참조 파일은 skills 폴더 안에 있어야 합니다"
            ) from error
        if not reference_file.is_file():
            raise CoachingSkillError(
                f"Skill 참조 파일이 없습니다: {definition.reference}"
            )
        referenced_texts.append(
            (definition.reference, reference_file.read_text(encoding="utf-8"))
        )

    criteria_text = json.dumps(
        catalog.model_dump(mode="json"), ensure_ascii=False, sort_keys=True
    )
    sections = [
        ("SKILL.md", skill_text),
        *referenced_texts,
        ("criteria.json", criteria_text),
    ]
    rules_text = "\n\n".join(f"[{name}]\n{text}" for name, text in sections)
    digest = hashlib.sha256(rules_text.encode("utf-8")).hexdigest()
    return SkillBundle(
        skill_file=skill_file,
        catalog=catalog,
        rules_text=rules_text,
        sha256=digest,
    )
