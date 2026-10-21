"""Offline evaluation records; no network calls or reference answers in requests."""
import hashlib
import json
from itertools import combinations

CONFIG_VERSION = "openrouter-six-v1"
GRADER_VERSION = "labels-support-evidence-semantic-critical-v4"
POLICY_VERSION = "independent-intent-observed-result-context-v3"
MODELS = {
    "qwen/qwen3.8-flash": "basic",
    "deepseek/deepseek-v4.1-flash": "basic",
    "google/gemini-3.8-flash": "basic",
    "deepseek/deepseek-v4-pro-0813": "premium",
    "anthropic/claude-sonnet-5": "premium",
    "openai/gpt-5.6-terra": "premium",
}
REQUEST_SETTINGS = {"temperature": "model_default", "reasoning": "model_default",
                    "provider": {"require_parameters": True}, "routing": "automatic"}


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def id_metrics(raw, context):
    """ID validity only; quote text and semantic relevance are separate checks."""
    if not isinstance(raw, dict):
        return None
    checks = []
    for key, field, expected in [("job_alignment", "requirement_id", context.requirement_ids),
                                  ("criterion_assessments", "criterion_id", context.active_criterion_ids)]:
        items = raw.get(key)
        if not isinstance(items, list) or not all(isinstance(i, dict) for i in items):
            return None
        ids = [i.get(field) for i in items]
        checks.append(len(ids) == len(expected) and set(str(i) for i in ids) == set(expected))
        for item in items:
            checks.append(isinstance(item.get("evidence"), list))
            for evidence in item.get("evidence", []) if isinstance(item.get("evidence"), list) else []:
                checks.append(isinstance(evidence, dict) and evidence.get("segment_id") in
                              {s.segment_id for s in context.answer_segments})
    checks.append(isinstance(raw.get("next_actions"), list))
    for action in raw.get("next_actions", []) if isinstance(raw.get("next_actions"), list) else []:
        allowed = {"criterion": context.active_criterion_ids,
                   "delivery_metric": context.allowed_delivery_metric_ids}
        checks.append(isinstance(action, dict) and action.get("target_id") in
                      allowed.get(str(action.get("target_type")), []))
    return {"correct": sum(checks), "total": len(checks), "accuracy": sum(checks) / len(checks)}


def label_signature(response, exclude_job_alignment_and_status=False):
    signature = {"intent": response.intent_assessment.label.value,
                 "criteria": {i.criterion_id: i.assessment.value for i in response.criterion_assessments}}
    if not exclude_job_alignment_and_status:
        signature.update(status=response.status.value,
                         jobs={i.requirement_id: i.label.value for i in response.job_alignment})
    return signature


def consistency(records):
    pairs = list(combinations(records, 2))
    valid_pairs = [(a, b) for a, b in pairs if a["labels"] is not None and b["labels"] is not None]
    return {"pairs": len(pairs), "valid_pairs": len(valid_pairs),
            "label_agreement": (sum(a["labels"] == b["labels"] for a, b in valid_pairs) /
                                len(valid_pairs)) if valid_pairs else None,
            "contract_agreement": (sum(a["contract_valid"] == b["contract_valid"] for a, b in pairs) /
                                   len(pairs)) if pairs else None}
