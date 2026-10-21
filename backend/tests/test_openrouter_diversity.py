import unittest

from evals.openrouter_diversity import (
    developer_for,
    exclusion_reason,
    failure_classification,
    select_candidates,
)


def model(model_id, *, output=("text",), parameters=("response_format",), price=1.0):
    return {
        "model_id": model_id,
        "canonical_slug": model_id,
        "developer": developer_for(model_id),
        "input_modalities": ["text"],
        "output_modalities": list(output),
        "supported_parameters": list(parameters),
        "output_usd_per_million": price,
        "created": 1,
    }


class OpenRouterDiversityTest(unittest.TestCase):
    def test_user_alias_keeps_canonical_developer(self):
        self.assertEqual(developer_for("~anthropic/claude-haiku-latest"), "anthropic")
        self.assertEqual(developer_for("meta/model"), "meta-llama")

    def test_excludes_non_text_and_obvious_aliases(self):
        self.assertEqual(exclusion_reason(model("google/image", output=("text", "image"))),
                         "NON_TEXT_CHAT_MODEL")
        self.assertEqual(exclusion_reason(model("openai/model:batch")), "ALIAS_OR_ROUTER")
        self.assertEqual(exclusion_reason(model("openrouter/auto")), "ALIAS_OR_ROUTER")
        self.assertEqual(exclusion_reason(model("openai/safeguard")), "SPECIALIZED_NON_CHAT")
        self.assertEqual(exclusion_reason(model("cohere/chat", parameters=())), "NO_STRUCTURED_OUTPUT")

    def test_selection_round_robins_developers_before_second_model(self):
        candidates = [
            model("openai/a"), model("openai/b"), model("google/a"), model("qwen/a")
        ]
        selected = select_candidates(candidates, max_models=3, per_developer=2, max_output_price=2)
        self.assertEqual({item["developer"] for item in selected}, {"openai", "google", "qwen"})

    def test_failure_classification_does_not_persist_provider_message(self):
        self.assertEqual(failure_classification({"contract_valid": False,
                                                 "failure_state": "schema_violation",
                                                 "failure_reason": "secret-like text"}),
                         ("CONTRACT_VIOLATION", "schema_violation"))
        self.assertEqual(failure_classification({"contract_valid": False,
                                                 "failure_state": "provider_error",
                                                 "http_status": 403}),
                         ("POLICY_RESTRICTED", "HTTP_403"))


if __name__ == "__main__":
    unittest.main()
