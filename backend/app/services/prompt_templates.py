"""모델 운영 템플릿을 읽고 별도 도메인 규칙을 요청 시 결합한다."""

from __future__ import annotations

import re
from pathlib import Path


PROMPT_ROOT = Path(__file__).resolve().parents[3] / "prompts"


class PromptTemplateError(ValueError):
    pass


def load_prompt_template(name: str) -> str:
    path = (PROMPT_ROOT / name).resolve()
    if not path.is_relative_to(PROMPT_ROOT.resolve()):
        raise PromptTemplateError("Prompt는 prompts 폴더 안에 있어야 합니다.")
    try:
        template = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise PromptTemplateError("Prompt 파일을 읽지 못했습니다.") from error
    if not template.strip():
        raise PromptTemplateError("Prompt 파일이 비어 있습니다.")
    return template


def compose_skill_prompt(
    template: str, *, skill_text: str, skill_version: str, prompt_version: str,
) -> str:
    if template.count("{{skill_text}}") != 1 or not skill_text.strip():
        raise PromptTemplateError("Prompt에는 Skill 슬롯 하나와 별도 Skill 본문이 필요합니다.")
    values = {
        "skill_text": skill_text,
        "skill_version": skill_version,
        "prompt_version": prompt_version,
    }
    pattern = re.compile(r"\{\{(.*?)\}\}", re.DOTALL)
    placeholders = list(pattern.finditer(template))
    if (len(placeholders) != template.count("{{")
            or len(placeholders) != template.count("}}")):
        raise PromptTemplateError("Prompt에 지원하지 않는 변수 표기가 있습니다.")

    def substitute(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in values:
            raise PromptTemplateError("Prompt에 지원하지 않는 변수가 있습니다.")
        return values[key]

    # 삽입한 Skill 본문 안의 문자열은 다시 템플릿 변수로 처리하지 않는다.
    return pattern.sub(substitute, template)
