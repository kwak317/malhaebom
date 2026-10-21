from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Iterable


MAX_HINT_TERMS = 12
PROMPT_PREFIX = "기술 면접 답변입니다. 다음 기술 용어가 등장할 수 있습니다:"

TECH_TERM_ALIASES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Python", ("python",)),
    ("Java", ("java",)),
    ("Kotlin", ("kotlin",)),
    ("JavaScript", ("javascript", "java script")),
    ("TypeScript", ("typescript", "type script")),
    ("React", ("react", "react.js", "reactjs")),
    ("Next.js", ("next.js", "nextjs")),
    ("Node.js", ("node.js", "nodejs")),
    ("Spring Boot", ("spring boot", "springboot")),
    ("Spring", ("spring",)),
    ("FastAPI", ("fastapi", "fast api")),
    ("Django", ("django",)),
    ("Flask", ("flask",)),
    ("PostgreSQL", ("postgresql", "postgres")),
    ("MySQL", ("mysql",)),
    ("Redis", ("redis",)),
    ("Docker", ("docker",)),
    ("Kubernetes", ("kubernetes", "k8s")),
    ("AWS", ("aws", "amazon web services")),
    ("Azure", ("azure",)),
    ("GCP", ("gcp", "google cloud platform")),
    ("GitHub Actions", ("github actions",)),
    ("GitHub", ("github",)),
    ("Git", ("git",)),
    ("CI/CD", ("ci/cd", "ci cd", "ci-cd")),
    ("REST API", ("rest api", "restapi")),
    ("GraphQL", ("graphql",)),
    ("Kafka", ("kafka",)),
    ("RabbitMQ", ("rabbitmq", "rabbit mq")),
    ("SQL", ("sql",)),
    ("NoSQL", ("nosql", "no sql")),
    ("Linux", ("linux",)),
    ("CUDA", ("cuda",)),
    ("GPU", ("gpu",)),
    ("PyTorch", ("pytorch", "py torch")),
    ("TensorFlow", ("tensorflow", "tensor flow")),
    ("Whisper", ("whisper",)),
    ("CTranslate2", ("ctranslate2", "c translate 2")),
    ("LLM", ("llm",)),
    ("RAG", ("rag",)),
    ("MCP", ("mcp",)),
    ("Supabase", ("supabase",)),
    ("Vercel", ("vercel",)),
)

MORE_SPECIFIC_TERMS: dict[str, frozenset[str]] = {
    "Spring": frozenset({"Spring Boot"}),
    "Git": frozenset({"GitHub", "GitHub Actions"}),
    "GitHub": frozenset({"GitHub Actions"}),
}


@dataclass(frozen=True)
class SttPromptHints:
    terms: tuple[str, ...]
    initial_prompt: str | None


def _normalized_text(text: str) -> str:
    value = unicodedata.normalize("NFKC", text).lower()
    value = value.replace("·", " ").replace("_", " ")
    return re.sub(r"\s+", " ", value).strip()


def _alias_pattern(alias: str) -> re.Pattern[str]:
    normalized = _normalized_text(alias)
    escaped = re.escape(normalized)
    escaped = escaped.replace(r"\ ", r"[\s._/-]*")
    return re.compile(rf"(?<![a-z0-9]){escaped}(?![a-z0-9])", re.IGNORECASE)


def extract_tech_terms(
    context_texts: Iterable[str | None],
    *,
    max_terms: int = MAX_HINT_TERMS,
) -> tuple[str, ...]:
    if max_terms < 1:
        return ()

    texts = [
        _normalized_text(text)
        for text in context_texts
        if isinstance(text, str) and text.strip()
    ]
    if not texts:
        return ()

    matched: list[tuple[int, int, str]] = []
    for catalog_order, (canonical, aliases) in enumerate(TECH_TERM_ALIASES):
        first_position: int | None = None
        for text_index, text in enumerate(texts):
            for alias in aliases:
                match = _alias_pattern(alias).search(text)
                if match is None:
                    continue
                position = text_index * 1_000_000 + match.start()
                first_position = position if first_position is None else min(first_position, position)
        if first_position is not None:
            matched.append((first_position, catalog_order, canonical))

    matched_names = {canonical for _, _, canonical in matched}
    matched = [
        item
        for item in matched
        if not (
            MORE_SPECIFIC_TERMS.get(item[2], frozenset())
            & matched_names
        )
    ]
    matched.sort()
    selected: list[str] = []
    for _, _, canonical in matched:
        selected.append(canonical)
        if len(selected) >= max_terms:
            break
    return tuple(selected)


def build_stt_prompt_hints(
    context_texts: Iterable[str | None],
    *,
    max_terms: int = MAX_HINT_TERMS,
) -> SttPromptHints:
    terms = extract_tech_terms(context_texts, max_terms=max_terms)
    prompt = f"{PROMPT_PREFIX} {', '.join(terms)}." if terms else None
    return SttPromptHints(terms=terms, initial_prompt=prompt)
