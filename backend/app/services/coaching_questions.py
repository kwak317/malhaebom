"""화면의 기본 질문과 서버 소유 코칭 기준 연결."""

from __future__ import annotations

import json
import hashlib
import re
from functools import lru_cache
from pathlib import Path

from app.schemas.coaching import QuestionContext
from app.services.coaching_skill import load_skill_bundle


PRESET_QUESTION_IDS = frozenset(f"preset-{number:02d}" for number in range(1, 11))
RUBRICS_FILE = Path(__file__).resolve().parents[3] / "configs/feedback/question-rubrics.json"


@lru_cache(maxsize=1)
def _preset_questions() -> dict[str, QuestionContext]:
    rubrics = json.loads(RUBRICS_FILE.read_text(encoding="utf-8"))["rubrics"]
    catalog = load_skill_bundle().catalog
    questions = {}
    for rubric in rubrics:
        question_id = rubric["question_id"]
        if question_id not in PRESET_QUESTION_IDS:
            continue
        problem_solving = question_id == "preset-04"
        question_type = "problem_solving" if problem_solving else "preset_interview"
        definition = catalog.question_types[question_type]
        questions[question_id] = QuestionContext(
            question_id=question_id,
            text=rubric["question"],
            question_type=question_type,
            active_criterion_ids=(
                definition.allowed_criterion_ids if problem_solving
                else [concept["id"] for concept in rubric["required_concepts"]]
            ),
            criteria_version=definition.criteria_version or catalog.criteria_version,
        )
    if set(questions) != PRESET_QUESTION_IDS:
        raise ValueError("기본 질문 10개의 코칭 루브릭이 모두 필요합니다.")
    return questions


def get_preset_coaching_question(question_id: str) -> QuestionContext | None:
    question = _preset_questions().get(question_id)
    return question.model_copy(deep=True) if question else None


def is_custom_coaching_question_id(question_id: str) -> bool:
    return re.fullmatch(r"custom-[0-9a-f]{12}", question_id) is not None

def get_custom_coaching_question(question_id: str, text: str) -> QuestionContext | None:
    if not isinstance(text, str) or not 1 <= len(text.strip()) <= 200:
        return None
    expected = "custom-" + hashlib.md5(text.encode("utf-8")).hexdigest()[:12]
    if question_id != expected:
        return None
    catalog = load_skill_bundle().catalog
    definition = catalog.question_types["custom_interview"]
    return QuestionContext(
        question_id=question_id, text=text, question_type="custom_interview",
        active_criterion_ids=definition.allowed_criterion_ids,
        criteria_version=definition.criteria_version or catalog.criteria_version,
    )
