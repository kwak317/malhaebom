#!/usr/bin/env python3
"""합성 평가셋과 후보 Prompt를 Langfuse에 재현 가능하게 동기화한다."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid4, uuid5


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
for import_path in (PROJECT_ROOT, BACKEND_ROOT):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from app.services.coaching_observability import (  # noqa: E402
    DEFAULT_PROMPT_VERSION,
    DEFAULT_SKILL_VERSION,
    CoachingGenerationObservation,
    CoachingObservation,
    CoachingValidationObservation,
    LangfuseCoachingObservationSink,
)
from app.services.coaching_prompt import load_coaching_prompt_template  # noqa: E402
from evals.coaching_dataset import CoachingEvaluationCase, load_dataset  # noqa: E402


DEFAULT_PROMPT_NAME = "malhaebom-coaching"
DEFAULT_PROMPT_LABEL = "candidate"
DEFAULT_DATASET_NAME = "malhaebom-coaching-eval-v2"
DEFAULT_DATASET_PATH = PROJECT_ROOT / "evals" / "dataset.v2.jsonl"


@dataclass(frozen=True)
class LangfuseAssetPlan:
    prompt_name: str
    prompt_label: str
    prompt_version: str
    skill_version: str
    prompt_text: str
    prompt_sha256: str
    dataset_name: str
    dataset_path: Path
    dataset_sha256: str
    cases: tuple[CoachingEvaluationCase, ...]


def build_plan(
    *,
    prompt_name: str,
    prompt_label: str,
    dataset_name: str,
    dataset_path: Path,
) -> LangfuseAssetPlan:
    prompt_text = load_coaching_prompt_template(
        os.getenv("COACHING_PROMPT_VERSION", DEFAULT_PROMPT_VERSION).strip() or DEFAULT_PROMPT_VERSION
    )
    cases = tuple(load_dataset(dataset_path))
    return LangfuseAssetPlan(
        prompt_name=prompt_name,
        prompt_label=prompt_label,
        prompt_version=os.getenv(
            "COACHING_PROMPT_VERSION", DEFAULT_PROMPT_VERSION
        ).strip()
        or DEFAULT_PROMPT_VERSION,
        skill_version=os.getenv(
            "COACHING_SKILL_VERSION", DEFAULT_SKILL_VERSION
        ).strip()
        or DEFAULT_SKILL_VERSION,
        prompt_text=prompt_text,
        prompt_sha256=hashlib.sha256(prompt_text.encode("utf-8")).hexdigest(),
        dataset_name=dataset_name,
        dataset_path=dataset_path,
        dataset_sha256=hashlib.sha256(dataset_path.read_bytes()).hexdigest(),
        cases=cases,
    )


def _is_not_found(error: Exception) -> bool:
    return getattr(error, "status_code", None) == 404


def sync_prompt(client: Any, plan: LangfuseAssetPlan) -> tuple[Any, str]:
    config = {
        "prompt_version": plan.prompt_version,
        "skill_version": plan.skill_version,
        "prompt_sha256": plan.prompt_sha256,
    }
    try:
        current = client.get_prompt(
            plan.prompt_name,
            label=plan.prompt_label,
            type="text",
            cache_ttl_seconds=0,
        )
    except Exception as error:
        if not _is_not_found(error):
            raise
        current = None
    if (
        current is not None
        and getattr(current, "prompt", None) == plan.prompt_text
        and getattr(current, "config", None) == config
    ):
        return current, "unchanged"
    created = client.create_prompt(
        name=plan.prompt_name,
        prompt=plan.prompt_text,
        labels=[plan.prompt_label],
        tags=["malhaebom", "coaching"],
        type="text",
        config=config,
        commit_message=(
            f"{plan.prompt_version}; skill={plan.skill_version}; "
            f"sha256={plan.prompt_sha256[:12]}"
        ),
    )
    return created, "created"


def ensure_dataset(client: Any, plan: LangfuseAssetPlan) -> str:
    try:
        client.get_dataset(plan.dataset_name, fetch_items_page_size=100)
        return "existing"
    except Exception as error:
        if not _is_not_found(error):
            raise
    client.create_dataset(
        name=plan.dataset_name,
        description=(
            "말해봄 코칭 합성 평가셋 30건. 실제 사용자 원문이나 개인정보를 포함하지 않음."
        ),
        metadata={
            "dataset_version": "v2",
            "dataset_sha256": plan.dataset_sha256,
            "case_count": len(plan.cases),
        },
    )
    return "created"


def _dataset_item_id(dataset_name: str, case_id: str) -> str:
    return str(
        uuid5(
            NAMESPACE_URL,
            f"https://malhaebom.local/langfuse/{dataset_name}/{case_id}",
        )
    )


def sync_dataset_items(client: Any, plan: LangfuseAssetPlan) -> int:
    for case in plan.cases:
        client.create_dataset_item(
            id=_dataset_item_id(plan.dataset_name, case.id),
            dataset_name=plan.dataset_name,
            input={
                "question": case.question.model_dump(mode="json"),
                "context": case.context.model_dump(mode="json"),
            },
            expected_output=case.expected.model_dump(mode="json"),
            metadata={
                "case_id": case.id,
                "category": case.category,
                "dataset_version": case.dataset_version,
                "annotation_provenance": case.annotation_provenance,
                "note": case.note,
                "why": case.why,
                "synthetic": True,
                "dataset_sha256": plan.dataset_sha256,
            },
        )
    return len(plan.cases)


def send_smoke_trace(client: Any, plan: LangfuseAssetPlan, prompt: Any) -> str:
    trace_id = uuid4().hex
    sink = LangfuseCoachingObservationSink(client, managed_prompt=prompt)
    sink.record_generation(
        CoachingGenerationObservation(
            trace_id=trace_id,
            model="langfuse-smoke/no-provider-call",
            prompt_version=f"{plan.prompt_name}@{getattr(prompt, 'version', 'unknown')}",
            skill_version=plan.skill_version,
            contract_attempt=1,
            transport_attempt=1,
            outcome="success",
            latency_ms=0,
            input_tokens=0,
            output_tokens=0,
            cost_usd=0,
            output_is_json_object=True,
        )
    )
    sink.record_validation(
        CoachingValidationObservation(
            trace_id=trace_id,
            prompt_version=f"{plan.prompt_name}@{getattr(prompt, 'version', 'unknown')}",
            skill_version=plan.skill_version,
            contract_attempt=1,
            valid=True,
            error_count=0,
            latency_ms=0,
        )
    )
    sink.record(
        CoachingObservation(
            trace_id=trace_id,
            model="langfuse-smoke/no-provider-call",
            prompt_version=f"{plan.prompt_name}@{getattr(prompt, 'version', 'unknown')}",
            skill_version=plan.skill_version,
            status="smoke_ok",
            latency_ms=0,
            input_tokens=0,
            output_tokens=0,
            cost_usd=0,
        )
    )
    client.flush()
    return trace_id


def verify_smoke_trace(
    client: Any,
    *,
    trace_id: str,
    prompt_name: str,
    prompt_version: int,
) -> dict[str, object]:
    """Observations API v2에서 세 관측과 Prompt 연결을 확인한다."""

    for attempt in range(10):
        now = datetime.now(UTC)
        result = client.api.observations.get_many(
            trace_id=trace_id,
            from_start_time=now - timedelta(minutes=5),
            to_start_time=now + timedelta(minutes=1),
            fields="core,basic,model,prompt",
            limit=20,
        )
        observations = list(result.data)
        generation = next(
            (
                item
                for item in observations
                if str(getattr(item, "name", "")) == "coaching.provider"
            ),
            None,
        )
        prompt_linked = bool(
            generation is not None
            and getattr(generation, "prompt_name", None) == prompt_name
            and getattr(generation, "prompt_version", None) == prompt_version
        )
        if len(observations) == 3 and prompt_linked:
            return {
                "observation_count": len(observations),
                "observation_names": sorted(
                    str(getattr(item, "name", "")) for item in observations
                ),
                "prompt_linked": True,
            }
        if attempt < 9:
            time.sleep(1)
    raise RuntimeError("Langfuse smoke trace 또는 Prompt 연결을 확인하지 못했습니다.")


def create_client_from_env() -> Any:
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY", "").strip()
    secret_key = os.getenv("LANGFUSE_SECRET_KEY", "").strip()
    base_url = (
        os.getenv("LANGFUSE_BASE_URL", "").strip()
        or os.getenv("LANGFUSE_HOST", "").strip()
    ).rstrip("/")
    if not public_key or not secret_key or not base_url:
        raise ValueError(
            "LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_BASE_URL가 필요합니다."
        )
    from langfuse import Langfuse

    return Langfuse(
        public_key=public_key,
        secret_key=secret_key,
        base_url=base_url,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Langfuse에 실제 반영")
    parser.add_argument("--smoke-trace", action="store_true", help="redacted smoke trace 전송")
    parser.add_argument("--prompt-name", default=DEFAULT_PROMPT_NAME)
    parser.add_argument("--prompt-label", default=DEFAULT_PROMPT_LABEL)
    parser.add_argument(
        "--dataset-name",
        default=os.getenv("LANGFUSE_DATASET_NAME", DEFAULT_DATASET_NAME),
    )
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET_PATH)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    plan = build_plan(
        prompt_name=args.prompt_name,
        prompt_label=args.prompt_label,
        dataset_name=args.dataset_name,
        dataset_path=args.dataset,
    )
    summary: dict[str, object] = {
        "mode": "apply" if args.apply else "dry-run",
        "prompt_name": plan.prompt_name,
        "prompt_label": plan.prompt_label,
        "prompt_version": plan.prompt_version,
        "prompt_sha256": plan.prompt_sha256,
        "dataset_name": plan.dataset_name,
        "dataset_sha256": plan.dataset_sha256,
        "dataset_cases": len(plan.cases),
    }
    if not args.apply:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0

    client = create_client_from_env()
    try:
        if not client.auth_check():
            raise RuntimeError("Langfuse 인증에 실패했습니다.")
        prompt, prompt_status = sync_prompt(client, plan)
        dataset_status = ensure_dataset(client, plan)
        item_count = sync_dataset_items(client, plan)
        trace_id = send_smoke_trace(client, plan, prompt) if args.smoke_trace else None
        trace_verification = (
            verify_smoke_trace(
                client,
                trace_id=trace_id,
                prompt_name=plan.prompt_name,
                prompt_version=int(getattr(prompt, "version")),
            )
            if trace_id is not None
            else None
        )
        summary.update(
            {
                "auth": "ok",
                "prompt_status": prompt_status,
                "prompt_remote_version": getattr(prompt, "version", None),
                "dataset_status": dataset_status,
                "dataset_items_upserted": item_count,
                "smoke_trace_id": trace_id,
                "smoke_trace_verification": trace_verification,
            }
        )
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0
    finally:
        client.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
