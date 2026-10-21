from __future__ import annotations

import io
import os
import re
from pathlib import Path

from app.schemas.resume import ResumeAnalysisOutput, ResumeAnalysisResponse
from app.services.analysis_skill import load_analysis_skill
from app.services.prompt_templates import compose_skill_prompt, load_prompt_template
from app.services.coaching_runtime import CoachingProviderResult, OpenAICompatibleJsonProvider
from app.services.github_readme_analysis import MODEL_NAME
from app.services.loading_progress import report_progress

MAX_PDF_BYTES = 5 * 1024 * 1024
CONTACT = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|(?<!\d)(?:\+82[- .]?)?0\d{1,2}[- .]?\d{3,4}[- .]?\d{4}(?!\d)|\d{6}\s*-\s*[1-4]\d{6}")
PRIVATE_LINE = re.compile(r"(?:^|\s)(?:이름|성명|생년월일|생일|성별|주소|거주지|연락처|전화번호|이메일|name|gender|date of birth|address|phone|email)\s*[:：]", re.I)
DEFAULT_RESUME_SKILL_FILE = Path(__file__).resolve().parents[3] / "skills" / "resume-evidence" / "SKILL.md"


class ResumeAnalysisUnavailable(RuntimeError):
    pass


def redact_resume_text(text: str) -> str:
    # 사진과 PDF 메타데이터는 읽지 않는다. 비정형 이름까지 완전 익명화하는 기능은 아니다.
    return "\n".join(CONTACT.sub("[연락처 제외]", line)
                     for line in text.splitlines() if not PRIVATE_LINE.search(line))


def extract_resume_pages(data: bytes, *, redact_private: bool = True) -> list[str]:
    if len(data) > MAX_PDF_BYTES:
        raise ValueError("이력서는 5MB 이하 PDF로 제출해 주세요.")
    if not data.startswith(b"%PDF-"):
        raise ValueError("PDF 파일을 제출해 주세요.")
    try:
        from pypdf import PdfReader
    except ImportError:
        raise ResumeAnalysisUnavailable("PDF 분석 도구가 준비되지 않았습니다.") from None
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            raise ValueError("암호를 제거한 PDF로 제출해 주세요.")
        if not 1 <= len(reader.pages) <= 10:
            raise ValueError("이력서는 10페이지 이하로 제출해 주세요.")
        pages = []
        for page in reader.pages:
            content = page.get_contents()
            if content and len(content.get_data()) > 10 * 1024 * 1024:
                raise ValueError("PDF 페이지가 너무 큽니다. 용량을 줄여 제출해 주세요.")
            text = page.extract_text() or ""
            if redact_private:
                text = redact_resume_text(text)
            if len(text.strip()) < 10:
                raise ValueError("읽을 수 없는 페이지가 있어요. 스캔본 대신 텍스트를 선택할 수 있는 PDF로 제출해 주세요.")
            pages.append(text)
        if sum(map(len, pages)) > 30_000:
            raise ValueError("이력서 내용이 너무 깁니다. 30,000자 이하로 줄여 주세요.")
        return pages
    except ValueError:
        raise
    except Exception:
        raise ValueError("PDF를 읽지 못했습니다. 파일을 다시 저장해 제출해 주세요.") from None


class ResumeAnalysisService:
    def __init__(self, provider):
        self.provider = provider
        skill = load_analysis_skill(DEFAULT_RESUME_SKILL_FILE)
        self.system_prompt = compose_skill_prompt(load_prompt_template("resume-analysis.md"), skill_text=skill.text, skill_version=skill.version, prompt_version="resume-output-v1")

    def analyze(self, data: bytes) -> ResumeAnalysisResponse:
        report_progress("PDF에서 이력서 내용을 읽고 있어요…")
        pages = extract_resume_pages(data)
        report_progress("개인정보 제외 규칙을 적용하고 검토를 준비하고 있어요…")
        if self.provider is None:
            raise ResumeAnalysisUnavailable("이력서 분석 서비스를 준비하지 못했습니다.")
        prompt = "\n\n".join(f"[페이지 {i + 1}]\n{text}" for i, text in enumerate(pages))
        for attempt in range(2):
            try:
                report_progress("이력서의 기술과 경험을 확인하고 있어요…" if attempt == 0 else "추출 결과를 다시 확인하고 있어요…")
                raw = self.provider.generate(
                    system_prompt=self.system_prompt,
                    user_prompt=prompt + ("\n정확한 페이지/원문 인용과 JSON 형식을 다시 확인하세요." if attempt else ""),
                    schema=ResumeAnalysisOutput.model_json_schema(),
                )
                report_progress("추출한 정보와 PDF 원문 근거를 대조하고 있어요…")
                output = ResumeAnalysisOutput.model_validate(raw.output if isinstance(raw, CoachingProviderResult) else raw)
                for fact in output.facts:
                    if fact.page > len(pages) or " ".join(fact.source_excerpt.split()) not in " ".join(pages[fact.page - 1].split()):
                        raise ValueError("원문 인용 불일치")
                    if not fact.value.strip() or not fact.source_excerpt.strip() or " ".join(fact.value.split()) not in " ".join(fact.source_excerpt.split()):
                        raise ValueError("원문에 없는 내용")
                    if CONTACT.search(fact.value + fact.source_excerpt) or PRIVATE_LINE.search(fact.value + fact.source_excerpt):
                        raise ValueError("개인정보 포함")
                    if fact.category == "technology":
                        if not fact.keyword or fact.keyword.casefold() not in fact.source_excerpt.casefold():
                            raise ValueError("기술 원문 불일치")
                    elif fact.keyword is not None:
                        raise ValueError("기술 이외 검색어")
                return ResumeAnalysisResponse(facts=output.facts, model=MODEL_NAME)
            except Exception:
                if attempt == 1:
                    raise ResumeAnalysisUnavailable("이력서 근거를 확인하지 못했습니다. 다시 검토해 주세요.") from None
        raise ResumeAnalysisUnavailable("이력서 검토에 실패했습니다.")


def build_resume_analysis_service_from_env() -> ResumeAnalysisService:
    key = os.getenv("OPENROUTER_API_KEY", "").strip()
    provider = OpenAICompatibleJsonProvider(
        api_key=key, model_name=MODEL_NAME, base_url="https://openrouter.ai/api/v1",
        timeout_seconds=60.0, schema_name="malhaebom_resume_analysis", max_tokens=4096,
    ) if key else None
    return ResumeAnalysisService(provider)
