from __future__ import annotations
from app.services.loading_progress import report_progress

import base64
import binascii
import logging
import os
import re
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import quote, unquote, urlsplit, urlunsplit

import httpx
from pydantic import ValidationError

from app.schemas.github_readme import (
    GithubReadmeAnalysisOutput,
    GithubReadmeAnalysisRequest,
    GithubReadmeAnalysisResponse,
)
from app.services.coaching_errors import (
    CoachingCreditsError,
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
from services.llm import OutputContractError


MODEL_NAME = "google/gemini-3.1-flash-lite"
MAX_README_BYTES = 256 * 1024
MAX_GITHUB_RESPONSE_BYTES = 400 * 1024
_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]{1,100}$")
logger = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_GITHUB_README_SKILL_FILE = (
    PROJECT_ROOT / "skills" / "github-readme-evidence" / "SKILL.md"
)


class GithubReadmeNotFound(RuntimeError):
    pass


class GithubReadmeAnalysisUnavailable(RuntimeError):
    pass


class JsonReadmeProvider(Protocol):
    model_name: str

    def generate(
        self, *, system_prompt: str, user_prompt: str, schema: dict[str, object]
    ) -> dict[str, object]: ...


def readme_evidence_text(markdown: str) -> str:
    return " ".join(markdown.replace("**", "").replace("`", "").split())


def parse_github_readme_url(source_url: str) -> tuple[str, str, str | None, str | None, str]:
    try:
        parsed = urlsplit(source_url.strip())
        parts = [unquote(part) for part in parsed.path.split("/") if part]
        if (
            parsed.scheme != "https"
            or parsed.hostname not in {"github.com", "www.github.com"}
            or parsed.username or parsed.password or parsed.port
            or len(parts) < 2
            or not _NAME_PATTERN.fullmatch(parts[0])
            or not _NAME_PATTERN.fullmatch(parts[1])
            or parts[0] in {".", ".."} or parts[1] in {".", ".."}
        ):
            raise ValueError
        owner, repo = parts[:2]
        ref: str | None = None
        path: str | None = None
        if len(parts) != 2:
            if (
                len(parts) < 5 or parts[2] != "blob"
                or not _NAME_PATTERN.fullmatch(parts[3])
                or parts[3] in {".", ".."}
                or parts[-1].casefold() != "readme.md"
                or any(part in {".", ".."} or "/" in part or "\\" in part for part in parts[4:])
            ):
                raise ValueError
            ref = parts[3]
            path = "/".join(parts[4:])
        canonical_path = "/" + "/".join(quote(part, safe="") for part in parts)
        canonical_url = urlunsplit(("https", "github.com", canonical_path, "", ""))
        return owner, repo, ref, path, canonical_url
    except (ValueError, UnicodeError) as error:
        raise ValueError("GitHub 저장소 또는 README.md 주소를 확인해 주세요.") from error


class GithubReadmeFetcher:
    def __init__(self, http_client: Any | None = None) -> None:
        self.http = http_client or httpx.Client(
            timeout=10.0, follow_redirects=False, trust_env=False
        )

    def fetch(self, source_url: str) -> tuple[str, str, str]:
        owner, repo, ref, path, canonical_url = parse_github_readme_url(source_url)
        endpoint = f"https://api.github.com/repos/{quote(owner)}/{quote(repo)}"
        endpoint += f"/contents/{quote(path, safe='/')}" if path else "/readme"
        try:
            for attempt in range(2):
                try:
                    response = self.http.get(
                        endpoint,
                        params={"ref": ref} if ref else None,
                        headers={
                            "Accept": "application/vnd.github+json",
                            "User-Agent": "MalhaebomReadmeAnalysis/1.0",
                        },
                    )
                except httpx.HTTPError:
                    if attempt == 0:
                        continue
                    raise
                if response.status_code in {500, 502, 503, 504} and attempt == 0:
                    continue
                break
            if response.status_code == 404:
                raise GithubReadmeNotFound("공개 README.md를 찾지 못했습니다. 주소를 확인해 주세요.")
            if response.status_code != 200:
                raise GithubReadmeAnalysisUnavailable(
                    "GitHub README를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요."
                )
            if len(response.content) > MAX_GITHUB_RESPONSE_BYTES:
                raise GithubReadmeAnalysisUnavailable("README가 너무 커서 분석할 수 없습니다.")
            data = response.json()
            if (
                not isinstance(data, dict)
                or data.get("type") != "file"
                or data.get("encoding") != "base64"
                or not isinstance(data.get("content"), str)
                or not isinstance(data.get("size"), int)
                or data["size"] > MAX_README_BYTES
                or not isinstance(data.get("sha"), str)
            ):
                raise GithubReadmeAnalysisUnavailable("README 내용을 확인하지 못했습니다.")
            encoded = "".join(data["content"].split())
            raw = base64.b64decode(encoded, validate=True)
            if len(raw) > MAX_README_BYTES:
                raise GithubReadmeAnalysisUnavailable("README가 너무 커서 분석할 수 없습니다.")
            markdown = raw.decode("utf-8-sig")
            if len(markdown.strip()) < 20:
                raise GithubReadmeAnalysisUnavailable("분석할 README 내용이 부족합니다.")
            return markdown, data["sha"], canonical_url
        except (httpx.HTTPError, ValueError, KeyError, TypeError, UnicodeError, binascii.Error) as error:
            raise GithubReadmeAnalysisUnavailable(
                "GitHub README를 읽지 못했습니다. 잠시 후 다시 시도해 주세요."
            ) from error


class GithubReadmeAnalysisService:
    def __init__(
        self, fetcher: GithubReadmeFetcher, provider: JsonReadmeProvider,
        *, max_attempts: int = 2, skill_file: Path = DEFAULT_GITHUB_README_SKILL_FILE,
    ) -> None:
        self.fetcher = fetcher
        self.provider = provider
        self.max_attempts = max_attempts
        try:
            self.skill = load_analysis_skill(skill_file)
        except AnalysisSkillError as error:
            raise GithubReadmeAnalysisUnavailable(
                "README 분석 Skill을 준비하지 못했습니다."
            ) from error

    def analyze(self, request: GithubReadmeAnalysisRequest) -> GithubReadmeAnalysisResponse:
        logger.info("github_readme_analysis skill_version=%s", self.skill.version)
        report_progress("GitHub README 원문을 불러오고 있어요…")
        markdown, readme_sha, source_url = self.fetcher.fetch(request.source_url)
        source_for_match = readme_evidence_text(markdown)
        prompt = (
            f"[README 시작]\n{markdown}\n[README 끝]"
        )
        last_error: Exception | None = None
        for attempt in range(self.max_attempts):
            retry_note = (
                "\n이전 결과의 원문 근거 또는 형식이 맞지 않았습니다. README에서 문구를 "
                "정확히 복사해 전체 JSON을 다시 반환하세요."
                if attempt else ""
            )
            try:
                report_progress("기술 스택과 프로젝트 흐름을 분석하고 있어요…" if not attempt else "README 분석 결과를 다시 점검하고 있어요…")
                raw = self.provider.generate(
                    system_prompt=build_readme_system_prompt(self.skill),
                    user_prompt=prompt + retry_note,
                    schema=GithubReadmeAnalysisOutput.model_json_schema(),
                )
                if isinstance(raw, CoachingProviderResult):
                    raw = raw.output
                report_progress("분석 내용과 README 원문 근거를 검증하고 있어요…")
                output = GithubReadmeAnalysisOutput.model_validate(raw)
                grounded_technologies = [
                    item for item in output.technology_stack
                    if " ".join(item.source_excerpt.split()) in source_for_match
                ]
                grounded_flows = [
                    item for item in output.project_flow
                    if " ".join(item.source_excerpt.split()) in source_for_match
                ]
                if (len(grounded_technologies) != len(output.technology_stack)
                        or len(grounded_flows) != len(output.project_flow)):
                    if attempt + 1 < self.max_attempts:
                        raise ValueError("README에 없는 원문 근거가 포함되었습니다.")
                    if not grounded_technologies or not grounded_flows:
                        raise ValueError("검증된 기술 또는 프로젝트 흐름이 없습니다.")
                    output = GithubReadmeAnalysisOutput(
                        technology_stack=grounded_technologies,
                        project_flow=grounded_flows,
                    )
                report_progress("README 분석 결과를 정리하고 있어요…")
                return GithubReadmeAnalysisResponse(
                    **output.model_dump(),
                    source_url=source_url,
                    readme_sha=readme_sha,
                    model=self.provider.model_name,
                )
            except CoachingCreditsError as error:
                raise GithubReadmeAnalysisUnavailable(
                    "OpenRouter 키의 크레딧 또는 사용 한도가 부족합니다. 키 설정을 확인해 주세요."
                ) from error
            except (CoachingProviderError, CoachingRateLimitError, CoachingTimeoutError) as error:
                raise GithubReadmeAnalysisUnavailable(
                    "Gemini 3.8 Flash 분석에 연결하지 못했습니다. 잠시 후 다시 시도해 주세요."
                ) from error
            except (OutputContractError, ValidationError, ValueError, TypeError) as error:
                last_error = error
        raise GithubReadmeAnalysisUnavailable(
            "README 원문에 근거한 분석 결과를 만들지 못했습니다. 다시 시도해 주세요."
        ) from last_error


class UnavailableGithubReadmeAnalysisService:
    def analyze(self, _: GithubReadmeAnalysisRequest) -> GithubReadmeAnalysisResponse:
        raise GithubReadmeAnalysisUnavailable("OpenRouter API 키가 설정되지 않았습니다.")


def build_github_readme_analysis_service_from_env() -> (
    GithubReadmeAnalysisService | UnavailableGithubReadmeAnalysisService
):
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        return UnavailableGithubReadmeAnalysisService()
    try:
        return GithubReadmeAnalysisService(
            GithubReadmeFetcher(),
            OpenAICompatibleJsonProvider(
                api_key=api_key,
                model_name=MODEL_NAME,
                base_url="https://openrouter.ai/api/v1",
                timeout_seconds=60.0,
                schema_name="malhaebom_github_readme_analysis",
                require_provider_parameters=(
                    os.getenv("OPENROUTER_REQUIRE_PARAMETERS", "true").strip().casefold()
                    not in {"0", "false", "no", "off"}
                ),
                max_tokens=3072,
            ),
        )
    except GithubReadmeAnalysisUnavailable:
        return UnavailableGithubReadmeAnalysisService()


def build_readme_system_prompt(skill: AnalysisSkillBundle) -> str:
    return compose_skill_prompt(
        load_prompt_template("github-readme-analysis.md"),
        skill_text=skill.text, skill_version=skill.version, prompt_version="readme-output-v2",
    )
