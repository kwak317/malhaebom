#!/usr/bin/env python3
"""One checkpointed D11 prompt A/B provider call per invocation (no CLI args).

Six initial calls plus one bounded retry for each contract-failed case.
Do not retry interrupted/inflight calls automatically, to avoid duplicate billing.
Single-reviewer provisional comparison; never promotes the official dataset.
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "backend")]
from app.services.coaching_prompt import prompt_sha256
from app.services.coaching_skill import load_skill_bundle
from evals.coaching_dataset import load_dataset
from evals.environment import load_evaluation_env, resolve_provider_credentials
from evals.run_model_comparison import CandidateConfig, OpenAICompatibleRunner, build_system_prompt, run_comparison

CASE_PATH = ROOT / "evals/d11_injection_candidates.jsonl"
REVIEW_PATH = ROOT / "local-results/d11-human-review-2026-10-07/human-review.user-filled.json"
OUT = ROOT / "local-results/d11-injection-ab-20261008"
MODEL = "google/gemini-3.5-flash-lite"
PAIR = (("before_v4", "coaching-output-v4"), ("after_v5", "coaching-v5-skill-owned"))
MAX_NEW_PROVIDER_CALLS = 6
MAX_KNOWN_COST_USD = 0.15
MAX_TOKENS = 4096
TIMEOUT_SECONDS = 18
RETRY_TIMEOUT_SECONDS = 20


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare():
    cases = load_dataset(CASE_PATH)
    payload = json.loads(REVIEW_PATH.read_text(encoding="utf-8"))
    reviews = payload.get("reviews", [])
    if len(cases) != 3 or len(reviews) != 3:
        raise ValueError("Expected 3 cases and 3 human reviews")
    by_id = {r["case_id"]: r for r in reviews}
    if len(by_id) != 3 or set(by_id) != {c.id for c in cases}:
        raise ValueError("Review IDs differ")
    for c in cases:
        r = by_id[c.id]
        if not (r.get("approved") is True and
                all(r.get(k) for k in ("reviewer", "reviewed_at", "input_disposition", "independent_rationale", "final_expected"))):
            raise ValueError("Incomplete prior human review")
        expected = r["final_expected"]
        if (expected["status"] != c.expected.status or
            expected["intent_label"] != c.expected.intent_label.value or
            expected["criterion_assessments"] != {k: v.value for k,v in c.expected.criterion_assessments.items()}):
            raise ValueError("Human-reviewed labels do not match frozen candidate")
    return cases


def atomic_json(path, data):
    tmp = path.with_suffix(".writing")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def summarize(tasks):
    rows = []
    totals = {name: {"valid": 0, "label_pass": 0, "known_cost": 0.0,
                     "latencies": [], "failure": 0} for name, _ in PAIR}
    for i, (label, _, case) in enumerate(tasks):
        path = OUT / f"result-{i:02d}.json"
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        a = data["attempt"]
        retry_path = OUT / f"retry-{i:02d}.json"
        if retry_path.exists():
            retry = json.loads(retry_path.read_text(encoding="utf-8"))
            totals[label]["known_cost"] += float(a.get("cost_usd") or 0.0)
            a = retry["attempt"]
        ok = bool(a.get("contract_valid"))
        score = a.get("score") or {}
        checks = score.get("label_results") or {}
        label_pass = bool(checks and all(checks.values()))
        totals[label]["valid"] += int(ok)
        totals[label]["label_pass"] += int(label_pass)
        totals[label]["known_cost"] += float(a.get("cost_usd") or 0.0)
        totals[label]["latencies"].append(float(a.get("latency_ms", 0)))
        totals[label]["failure"] += int(not label_pass)
        rows.append({"id": case.id, "label": label, "contract": ok,
                     "labels_all_match": label_pass,
                     "intent_and_cav": checks,
                     "latency_ms": a.get("latency_ms"),
                     "cost_usd": a.get("cost_usd"),
                     "failure_state": a.get("failure_state")})
    pending_retries = [i for i in range(len(tasks))
                       if (OUT / f"result-{i:02d}.json").exists()
                       and not json.loads((OUT / f"result-{i:02d}.json").read_text(encoding="utf-8"))["attempt"].get("contract_valid")
                       and not (OUT / f"retry-{i:02d}.json").exists()]
    complete = len(rows) == len(tasks) and not pending_retries
    def percentile(x, fraction):
        x=sorted(x)
        return x[max(0,__import__("math").ceil(len(x)*fraction)-1)] if x else None
    output = {"status": "PROVISIONAL_COMPLETE" if complete else "INCOMPLETE",
              "independent_review": False,
              "rows": rows,
              "pending_retries": pending_retries,
              "conditions": {name: {
                  "executions": len(d["latencies"]),
                  "contract_pass": d["valid"],
                  "intent_cav_all_match": d["label_pass"],
                  "known_cost_usd": round(d["known_cost"], 7),
                  "p95_latency_ms": percentile(d["latencies"], 0.95)
              } for name, d in totals.items()},
              "prior_interrupted_execution": "one initial run timed out after manifest; external usage/charges unknown"}
    atomic_json(OUT / "summary.json", output)
    lines = ["# D11 신규 인젝션 3건 Prompt v4/v5 전후 실험",
             "", f"- 상태: **{output['status']}** (단일 검토자 기준; 독립 평가 아님)",
             "- 변경 변수: Prompt v4 → v5만 변경. 동일 Gemini 3.5 Flash-Lite / Skill / Dataset / 4,096-token / strict schema.",
             "- 각 조건 3건씩 1차 호출, 계약 실패만 최대 1회 재호출. 최초 일괄 실행은 원격 30초 제한으로 중단되었고 과금 여부는 확인 불가.",
             "- 이 실험은 production/서비스 E2E를 재현하지 않으며 인젝션 탈취 여부 전부를 사람 판정한 것은 아니다.",
             "",
             "| 사례 | 이전 v4 계약/판정 | 이후 v5 계약/판정 |",
             "|---|---|---|"]
    for case in (c for label, version, c in tasks if label == "before_v4"):
        mapped={}
        for row in rows:
            if row["id"]==case.id:
                mapped[row["label"]] = ("계약 " + ("PASS" if row["contract"] else "FAIL") +
                                        ", C/A/V·intent " + ("PASS" if row["labels_all_match"] else "FAIL"))
        lines.append("| " + case.id + " | " + mapped.get("before_v4", "미실행") + " | " + mapped.get("after_v5", "미실행") + " |")
    lines += ["", "| 지표 | 이전 v4 | 이후 v5 |", "|---|---:|---:|"]
    for field in ("contract_pass", "intent_cav_all_match", "known_cost_usd", "p95_latency_ms"):
        lines.append(f"| {field} | {output['conditions']['before_v4'][field]} | {output['conditions']['after_v5'][field]} |")
    (OUT / "D11_SUMMARY.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
    return output


def main():
    cases = prepare()
    skill = load_skill_bundle(ROOT/"skills/interview-coach/SKILL.md")
    tasks = [(label, version, c) for label,version in PAIR for c in cases]
    provenance={label:{"prompt":version, "skill":skill.catalog.skill_version,
                       "prompt_sha256":prompt_sha256(build_system_prompt(skill.rules_text, version, skill.catalog.skill_version))}
                for label,version in PAIR}
    manifest_path = OUT / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    if manifest:
        if (manifest.get("case_sha256") != digest(CASE_PATH) or
            manifest.get("human_review_sha256") != digest(REVIEW_PATH)):
            raise ValueError("Dataset/review differs from frozen manifest")
        for label in provenance:
            if manifest["prompt_versions"][label]["prompt_sha256"] != provenance[label]["prompt_sha256"]:
                raise ValueError("Prompt hash differs from frozen manifest")
    else:
        OUT.mkdir(parents=True, exist_ok=False)
        atomic_json(manifest_path, {
            "status":"SINGLE_REVIEWER_PROVISIONAL",
            "case_sha256": digest(CASE_PATH),
            "human_review_sha256":digest(REVIEW_PATH),
            "prompt_versions":{label:{"prompt_sha256":val["prompt_sha256"]} for label,val in provenance.items()},
            "independent_reviewer_confirmed":False})
    known_cost=0.0
    for i in range(len(tasks)):
        for kind in ("result", "retry"):
            file=OUT/f"{kind}-{i:02d}.json"
            if file.exists():
                data=json.loads(file.read_text(encoding="utf-8"))
                known_cost += float(data["attempt"].get("cost_usd") or 0)
    if known_cost >= MAX_KNOWN_COST_USD:
        raise ValueError("Configured cost limit exhausted")
    for i,(label,version,case) in enumerate(tasks):
        result=OUT/f"result-{i:02d}.json"
        inflight=OUT/f"inflight-{i:02d}.json"
        if result.exists() or inflight.exists():
            continue
        load_evaluation_env()
        key,url=resolve_provider_credentials(require_openrouter=True)
        system=build_system_prompt(skill.rules_text,version,skill.catalog.skill_version)
        runner=OpenAICompatibleRunner(
            CandidateConfig(label,"openai",MODEL),
            system_prompt=system, api_key=key, base_url=url,
            timeout_seconds=TIMEOUT_SECONDS, max_completion_tokens=MAX_TOKENS)
        atomic_json(inflight,{"started":datetime.now(timezone.utc).isoformat(),
                               "case":case.id,"prompt":label,
                               "if_interrupted":"DO_NOT_RETRY_WITHOUT_COST_AUDIT"})
        print(f"Starting {label}/{case.id}, one bounded call (<= {TIMEOUT_SECONDS}s)",flush=True)
        report=run_comparison([case],[(CandidateConfig(label,"openai",MODEL),runner)],
                              repeats=1,max_calls=1, configuration={
                              "prompt_version":version,
                              "prompt_sha256":prompt_sha256(system),
                              "skill_version":skill.catalog.skill_version,
                              "skill_bundle_sha256":skill.sha256,
                              "criteria_version":skill.catalog.criteria_version})
        a=report["attempts"][0]
        atomic_json(result,{"prompt":label,"case":case.id,"attempt":a,
                            "summary":report["candidates"][label]})
        inflight.unlink()
        aggregate=summarize(tasks)
        print(json.dumps({"completed": f"{label}/{case.id}", "contract":a.get("contract_valid"),
             "labels":(a.get("score") or {}).get("label_results"),
             "cost_usd":a.get("cost_usd"),
             "completed_count":len(aggregate["rows"]),
             "total_expected":len(tasks)},ensure_ascii=False),flush=True)
        return 0
    for i, (label, version, case) in enumerate(tasks):
        result = OUT / f"result-{i:02d}.json"
        retry = OUT / f"retry-{i:02d}.json"
        inflight = OUT / f"inflight-retry-{i:02d}.json"
        if not result.exists() or retry.exists() or inflight.exists():
            continue
        prior = json.loads(result.read_text(encoding="utf-8"))["attempt"]
        if prior.get("contract_valid"):
            continue
        load_evaluation_env()
        key, url = resolve_provider_credentials(require_openrouter=True)
        system = build_system_prompt(skill.rules_text, version, skill.catalog.skill_version)
        runner = OpenAICompatibleRunner(
            CandidateConfig(label, "openai", MODEL),
            system_prompt=system, api_key=key, base_url=url,
            timeout_seconds=RETRY_TIMEOUT_SECONDS, max_completion_tokens=MAX_TOKENS)
        atomic_json(inflight, {"started": datetime.now(timezone.utc).isoformat(),
                                "case": case.id, "prompt": label,
                                "if_interrupted": "DO_NOT_RETRY_WITHOUT_COST_AUDIT"})
        print(f"Retrying once {label}/{case.id} (<={RETRY_TIMEOUT_SECONDS}s)", flush=True)
        report = run_comparison([case], [(CandidateConfig(label, "openai", MODEL), runner)],
                                repeats=1, max_calls=1)
        attempt = report["attempts"][0]
        atomic_json(retry, {"prompt": label, "case": case.id, "attempt": attempt,
                            "summary": report["candidates"][label]})
        inflight.unlink()
        aggregate = summarize(tasks)
        print(json.dumps({"retried": f"{label}/{case.id}",
                          "contract": attempt.get("contract_valid"),
                          "labels": (attempt.get("score") or {}).get("label_results"),
                          "cost_usd": attempt.get("cost_usd"),
                          "pending_retries": aggregate["pending_retries"]}, ensure_ascii=False), flush=True)
        return 0
    aggregate=summarize(tasks)
    print(json.dumps({"status":aggregate["status"],"completed":len(aggregate["rows"]),
                      "expected":len(tasks)}, ensure_ascii=False),flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
