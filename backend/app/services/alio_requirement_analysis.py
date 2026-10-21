from __future__ import annotations

import ipaddress
import os
import re
import socket
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import urlparse

import httpx
from pydantic import ValidationError

from app.schemas.alio_recruitment import (
    AlioAnalyzedRequirement,
    AlioRecruitmentAnalysisRequest,
)
from app.schemas.practice_setup import PracticeSetupModel
from app.services.coaching_errors import (
    CoachingProviderError,
    CoachingRateLimitError,
    CoachingTimeoutError,
)
from app.services.prompt_templates import compose_skill_prompt, load_prompt_template
from app.services.coaching_runtime import CoachingProviderResult, OpenAICompatibleJsonProvider
from app.services.analysis_skill import (
    AnalysisSkillBundle,
    AnalysisSkillError,
    load_analysis_skill,
)


MAX_SOURCE_BYTES = 1_000_000
MAX_SOURCE_TEXT_CHARS = 30_000
MAX_EVIDENCE_EXCERPT_CHARS = 500
MAX_EVIDENCE_ANCHOR_MATCHES = 30
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_JOB_REQUIREMENT_SKILL_FILE = (
    PROJECT_ROOT / "skills" / "job-requirement-extraction" / "SKILL.md"
)
_EVIDENCE_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9+#]+|[가-힣]+")
_EVIDENCE_PARTICLE_SUFFIXES = (
    "으로",
    "에서",
    "에게",
    "부터",
    "까지",
    "처럼",
    "보다",
    "은",
    "는",
    "이",
    "가",
    "을",
    "를",
    "과",
    "와",
    "의",
    "에",
    "도",
    "로",
    "만",
    "등",
)
_EVIDENCE_STOPWORDS = {
    "지원",
    "지원자격",
    "자격",
    "요건",
    "요구사항",
    "우대",
    "우대사항",
    "경력",
    "신입",
    "채용",
    "관련",
    "직무",
    "업무",
    "경험",
    "보유",
    "가능",
    "이상",
    "이하",
    "및",
    "또는",
}


class AlioRequirementAnalysisUnavailable(RuntimeError):
    """공고 원문 또는 LLM 분석을 안전하게 완료할 수 없을 때 발생한다."""


class SourceTextFetcher(Protocol):
    def fetch(self, source_url: str) -> str: ...


class JsonRequirementProvider(Protocol):
    model_name: str

    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        schema: dict[str, object],
    ) -> dict[str, object]: ...


class _VisibleTextParser(HTMLParser):
    _HIDDEN_TAGS = {"script", "style", "noscript", "template", "svg"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._hidden_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.casefold() in self._HIDDEN_TAGS:
            self._hidden_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.casefold() in self._HIDDEN_TAGS and self._hidden_depth:
            self._hidden_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._hidden_depth:
            self.parts.append(data)


class SecureHtmlSourceFetcher:
    """공고 원문만 가져오도록 내부망과 리디렉션을 차단한다."""

    def __init__(
        self,
        http_client: httpx.Client | Any | None = None,
        *,
        resolver: Any = socket.getaddrinfo,
    ) -> None:
        self.http = http_client or httpx.Client(
            timeout=10.0,
            follow_redirects=False,
            trust_env=False,
        )
        self.resolver = resolver

    def fetch(self, source_url: str) -> str:
        _require_public_https_url(source_url, self.resolver)
        try:
            request = self.http.build_request(
                "GET",
                source_url,
                headers={
                    "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9",
                    "User-Agent": "MalhaebomJobAnalysis/1.0",
                },
            )
            response = self.http.send(request, stream=True)
        except httpx.TimeoutException as error:
            raise AlioRequirementAnalysisUnavailable(
                "공고 원문을 가져오는 시간이 초과되었습니다."
            ) from error
        except httpx.HTTPError as error:
            raise AlioRequirementAnalysisUnavailable(
                "공고 원문에 연결하지 못했습니다."
            ) from error

        try:
            if response.status_code != 200:
                raise AlioRequirementAnalysisUnavailable(
                    "공고 원문을 가져오지 못했습니다."
                )
            content_type = response.headers.get("content-type", "").casefold()
            if not content_type.startswith(("text/html", "application/xhtml+xml", "text/plain")):
                raise AlioRequirementAnalysisUnavailable(
                    "텍스트 형식의 공고 원문만 AI로 분석할 수 있습니다."
                )
            raw = _read_limited_body(response)
        finally:
            response.close()

        try:
            document = raw.decode("utf-8")
        except UnicodeDecodeError:
            document = raw.decode("euc-kr", errors="replace")
        source_text = _visible_text(document) if "html" in content_type else _normalize_text(document)
        if len(source_text) < 20:
            raise AlioRequirementAnalysisUnavailable(
                "공고 원문에서 분석할 텍스트를 찾지 못했습니다."
            )
        return source_text[:MAX_SOURCE_TEXT_CHARS]


class AlioRequirementAnalysisService:
    def __init__(
        self,
        source_fetcher: SourceTextFetcher,
        provider: JsonRequirementProvider,
        *,
        max_attempts: int = 2,
        skill_file: Path = DEFAULT_JOB_REQUIREMENT_SKILL_FILE,
    ) -> None:
        self.source_fetcher = source_fetcher
        self.provider = provider
        self.max_attempts = max_attempts
        try:
            self.skill = load_analysis_skill(skill_file)
        except AnalysisSkillError as error:
            raise AlioRequirementAnalysisUnavailable(
                "공고 요구사항 분석 Skill을 준비하지 못했습니다."
            ) from error

    def analyze(
        self,
        request: AlioRecruitmentAnalysisRequest,
        *,
        source_text: str | None = None,
    ) -> list[AlioAnalyzedRequirement]:
        source_text = source_text or self.source_fetcher.fetch(request.source_url)
        source_text = _normalize_text(source_text)
        if len(source_text) < 20:
            raise AlioRequirementAnalysisUnavailable(
                "공고 원문에서 분석할 텍스트를 찾지 못했습니다."
            )
        user_prompt = _analysis_prompt(request, source_text)
        last_error: ValueError | None = None
        for attempt in range(self.max_attempts):
            retry_note = ""
            if last_error is not None:
                retry_note = (
                    "\n이전 결과는 원문 근거 검증을 통과하지 못했습니다. 다음 사유를 "
                    "고쳐 전체 JSON 객체를 다시 반환하세요: " + str(last_error)
                )
            try:
                raw = self.provider.generate(
                    system_prompt=build_requirement_system_prompt(self.skill),
                    user_prompt=user_prompt + retry_note,
                    schema=AlioRequirementAnalysisOutput.model_json_schema(),
                )
                if isinstance(raw, CoachingProviderResult):
                    raw = raw.output
                output = AlioRequirementAnalysisOutput.model_validate(raw)
                requirements = _align_source_evidence(
                    output.requirements, source_text
                )
                _validate_source_evidence(requirements, source_text)
                return requirements
            except (
                CoachingProviderError,
                CoachingRateLimitError,
                CoachingTimeoutError,
            ) as error:
                raise AlioRequirementAnalysisUnavailable(
                    "공고 요구사항 분석 모델에 연결하지 못했습니다. 잠시 후 다시 시도해 주세요."
                ) from error
            except (ValidationError, ValueError, TypeError) as error:
                last_error = ValueError(str(error))
                if attempt + 1 >= self.max_attempts:
                    break
        raise AlioRequirementAnalysisUnavailable(
            "AI가 원문 근거가 있는 요구사항을 만들지 못했습니다. 다른 공고를 선택해 주세요."
        ) from last_error


class UnavailableAlioRequirementAnalysisService:
    def __init__(self, message: str) -> None:
        self.message = message

    def analyze(
        self, _: AlioRecruitmentAnalysisRequest, *, source_text: str | None = None
    ) -> list[AlioAnalyzedRequirement]:
        raise AlioRequirementAnalysisUnavailable(self.message)


class AlioRequirementAnalysisOutput(PracticeSetupModel):
    requirements: list[AlioAnalyzedRequirement]


def build_alio_requirement_analysis_service_from_env() -> (
    AlioRequirementAnalysisService | UnavailableAlioRequirementAnalysisService
):
    provider_name = (
        os.getenv("JOB_REQUIREMENT_ANALYSIS_PROVIDER", "").strip().casefold()
        or os.getenv("COACHING_PROVIDER", "").strip().casefold()
        or "openrouter"
    )
    model_name = (
        os.getenv("JOB_REQUIREMENT_ANALYSIS_LLM_MODEL", "").strip()
        or os.getenv("COACHING_LLM_MODEL", "").strip()
        or os.getenv("COACHING_MODEL", "").strip()
    )
    if provider_name == "ollama":
        api_key = os.getenv("JOB_REQUIREMENT_ANALYSIS_LLM_API_KEY", "").strip() or "ollama"
        base_url = (
            os.getenv("JOB_REQUIREMENT_ANALYSIS_OLLAMA_URL", "").strip()
            or os.getenv("COACHING_OLLAMA_URL", "http://127.0.0.1:11434").strip()
        )
        if not base_url.rstrip("/").endswith("/v1"):
            base_url = f"{base_url.rstrip('/')}/v1"
        default_timeout = "180"
    else:
        api_key = (
            os.getenv("JOB_REQUIREMENT_ANALYSIS_LLM_API_KEY", "").strip()
            or os.getenv("COACHING_LLM_API_KEY", "").strip()
            or os.getenv("OPENROUTER_API_KEY", "").strip()
        )
        base_url = (
            os.getenv("JOB_REQUIREMENT_ANALYSIS_LLM_BASE_URL", "").strip()
            or os.getenv("COACHING_LLM_BASE_URL", "https://openrouter.ai/api/v1").strip()
        )
        default_timeout = "25"
    if not api_key or not model_name:
        return UnavailableAlioRequirementAnalysisService(
            "공고 요구사항 분석 모델이 설정되지 않았습니다."
        )
    try:
        timeout_seconds = float(
            os.getenv("JOB_REQUIREMENT_ANALYSIS_LLM_TIMEOUT_SECONDS", "").strip()
            or os.getenv("COACHING_LLM_TIMEOUT_SECONDS", "").strip()
            or default_timeout
        )
        provider = OpenAICompatibleJsonProvider(
            api_key=api_key,
            model_name=model_name,
            base_url=base_url,
            timeout_seconds=timeout_seconds,
            schema_name="malhaebom_job_requirement_analysis",
            require_provider_parameters=(
                os.getenv("OPENROUTER_REQUIRE_PARAMETERS", "true").strip().casefold()
                not in {"0", "false", "no", "off"}
            ),
        )
    except ValueError:
        return UnavailableAlioRequirementAnalysisService(
            "공고 요구사항 분석 모델 설정을 확인해 주세요."
        )
    try:
        return AlioRequirementAnalysisService(SecureHtmlSourceFetcher(), provider)
    except AlioRequirementAnalysisUnavailable:
        return UnavailableAlioRequirementAnalysisService(
            "공고 요구사항 분석 Skill을 준비하지 못했습니다."
        )


def _require_public_https_url(source_url: str, resolver: Any) -> None:
    parsed = urlparse(source_url)
    hostname = parsed.hostname
    if (
        parsed.scheme != "https"
        or not hostname
        or parsed.username
        or parsed.password
    ):
        raise AlioRequirementAnalysisUnavailable(
            "AI 분석에는 HTTPS 공고 원문 URL만 사용할 수 있습니다."
        )
    try:
        addresses = {
            item[4][0] for item in resolver(hostname, 443, type=socket.SOCK_STREAM)
        }
    except OSError as error:
        raise AlioRequirementAnalysisUnavailable(
            "공고 원문 주소를 확인하지 못했습니다."
        ) from error
    if not addresses or any(not ipaddress.ip_address(address).is_global for address in addresses):
        raise AlioRequirementAnalysisUnavailable(
            "공개 HTTPS 공고 원문만 AI로 분석할 수 있습니다."
        )


def _read_limited_body(response: Any) -> bytes:
    content_length = response.headers.get("content-length")
    if content_length and content_length.isdigit() and int(content_length) > MAX_SOURCE_BYTES:
        raise AlioRequirementAnalysisUnavailable("공고 원문이 너무 커서 분석할 수 없습니다.")
    body = bytearray()
    for chunk in response.iter_bytes():
        body.extend(chunk)
        if len(body) > MAX_SOURCE_BYTES:
            raise AlioRequirementAnalysisUnavailable("공고 원문이 너무 커서 분석할 수 없습니다.")
    return bytes(body)


def _visible_text(document: str) -> str:
    parser = _VisibleTextParser()
    try:
        parser.feed(document)
        parser.close()
    except ValueError as error:
        raise AlioRequirementAnalysisUnavailable(
            "공고 원문 텍스트를 처리하지 못했습니다."
        ) from error
    return _normalize_text(" ".join(parser.parts))


def _normalize_text(value: str) -> str:
    return " ".join(value.split())


def _align_source_evidence(
    requirements: list[AlioAnalyzedRequirement], source_text: str
) -> list[AlioAnalyzedRequirement]:
    """모델의 요약된 인용을 실제 공고의 연속된 문구로 안전하게 되돌린다."""
    return [
        requirement.model_copy(
            update={
                "source_excerpt": _find_source_excerpt(
                    requirement, source_text
                )
            }
        )
        for requirement in requirements
    ]


def _find_source_excerpt(
    requirement: AlioAnalyzedRequirement, source_text: str
) -> str:
    requested_excerpt = _normalize_text(requirement.source_excerpt)
    source_normalized = _normalize_text(source_text)
    exact_start = source_normalized.casefold().find(requested_excerpt.casefold())
    if exact_start >= 0:
        return source_normalized[exact_start : exact_start + len(requested_excerpt)]

    requirement_tokens = _evidence_tokens(requirement.text)
    if not requirement_tokens:
        raise ValueError("요구사항에서 원문 근거를 찾을 단어가 없습니다.")
    anchor_tokens = list(
        dict.fromkeys(
            [*requirement_tokens, *_evidence_tokens(requested_excerpt)]
        )
    )
    required_matches = _minimum_evidence_matches(requirement_tokens)
    best_score: tuple[int, int, int] | None = None
    best_candidate: str | None = None
    source_folded = source_normalized.casefold()

    for anchor in anchor_tokens:
        matches = re.finditer(re.escape(anchor), source_folded)
        for index, match in enumerate(matches):
            if index >= MAX_EVIDENCE_ANCHOR_MATCHES:
                break
            candidate = _evidence_window(
                source_normalized, match.start(), match.end()
            )
            candidate_folded = candidate.casefold()
            requirement_match_count = sum(
                token in candidate_folded for token in requirement_tokens
            )
            if requirement_match_count < required_matches:
                continue
            quote_match_count = sum(
                token in candidate_folded
                for token in _evidence_tokens(requested_excerpt)
            )
            score = (requirement_match_count, quote_match_count, -len(candidate))
            if best_score is None or score > best_score:
                best_score = score
                best_candidate = candidate

    if best_candidate is None:
        raise ValueError("요구사항과 연결되는 원문 근거를 찾지 못했습니다.")
    return best_candidate


def _evidence_tokens(value: str) -> list[str]:
    tokens: list[str] = []
    for raw_token in _EVIDENCE_TOKEN_PATTERN.findall(value.casefold()):
        token = _strip_evidence_particle(raw_token)
        if len(token) >= 2 and token not in _EVIDENCE_STOPWORDS:
            tokens.append(token)
    return list(dict.fromkeys(tokens))


def _strip_evidence_particle(token: str) -> str:
    for suffix in _EVIDENCE_PARTICLE_SUFFIXES:
        if token.endswith(suffix) and len(token) > len(suffix) + 1:
            return token[: -len(suffix)]
    return token


def _minimum_evidence_matches(tokens: list[str]) -> int:
    if len(tokens) <= 1:
        return 1
    return max(2, (len(tokens) * 3 + 4) // 5)


def _evidence_window(source_text: str, start: int, end: int) -> str:
    left_limit = max(0, start - 160)
    right_limit = min(len(source_text), end + 320)
    left_boundary = source_text.rfind(" ", 0, left_limit)
    right_boundary = source_text.find(" ", right_limit)
    excerpt_start = left_boundary + 1 if left_boundary >= 0 else 0
    excerpt_end = right_boundary if right_boundary >= 0 else len(source_text)
    excerpt = source_text[excerpt_start:excerpt_end].strip()
    if len(excerpt) <= MAX_EVIDENCE_EXCERPT_CHARS:
        return excerpt
    clipped = excerpt[:MAX_EVIDENCE_EXCERPT_CHARS]
    last_space = clipped.rfind(" ")
    return clipped[:last_space].strip() if last_space >= 2 else clipped.strip()


def _validate_source_evidence(
    requirements: list[AlioAnalyzedRequirement], source_text: str
) -> None:
    if not 1 <= len(requirements) <= 5:
        raise ValueError("요구사항은 1~5개여야 합니다.")
    source_for_match = _normalize_text(source_text)
    seen: set[tuple[str, str]] = set()
    for requirement in requirements:
        key = (requirement.text.casefold(), requirement.source_excerpt.casefold())
        if key in seen:
            raise ValueError("동일한 요구사항 또는 원문 근거가 중복되었습니다.")
        seen.add(key)
        if _normalize_text(requirement.source_excerpt) not in source_for_match:
            raise ValueError("원문에 없는 근거 문구가 포함되었습니다.")


def build_requirement_system_prompt(skill: AnalysisSkillBundle) -> str:
    return compose_skill_prompt(
        load_prompt_template("job-requirement-analysis.md"),
        skill_text=skill.text, skill_version=skill.version, prompt_version="requirement-output-v2",
    )


def _analysis_prompt(request: AlioRecruitmentAnalysisRequest, source_text: str) -> str:
    return (
        f"[기관명]\n{request.company}\n[공고 제목]\n{request.title}\n"
        f"[원문 시작]\n{source_text}\n[원문 끝]"
    )
