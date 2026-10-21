import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from evals.run_model_comparison import (CandidateConfig, MockCandidateRunner,
    HardProviderTimeoutError, OpenAICompatibleRunner, build_expected_output,
    IsolatedProviderError, _provider_failure_state, load_dataset, run_comparison)
from evals.evaluation_records import MODELS, consistency


class EvaluationRecordsTest(unittest.TestCase):
    def setUp(self):
        self.cases = load_dataset(Path('evals/dataset.jsonl'))
        # GPT-5 exercises the candidate-specific strict schema and reasoning branch
        # through OpenAICompatibleRunner.generate(), not just its helper functions.
        self.config = CandidateConfig('basic', 'openai', 'openai/gpt-5-mini')

    def fake_runner(self, contents, cost=0.012):
        runner = object.__new__(OpenAICompatibleRunner)
        runner.config, runner.system_prompt = self.config, 'fixed skill'
        runner.max_completion_tokens = 768
        runner.isolate_calls = False
        self.requests = []
        def create(**request):
            self.requests.append(request)
            content = contents.pop(0)
            payload = {'id': 'gen-test', 'provider': 'test-provider', 'model': self.config.model,
                'usage': {'cost': cost, 'prompt_tokens': 100, 'completion_tokens': 30,
                    'completion_tokens_details': {'reasoning_tokens': 20},
                    'prompt_tokens_details': {'cached_tokens': 50, 'cache_write_tokens': 0}}}
            return SimpleNamespace(model_dump=lambda **kw: payload,
                choices=[SimpleNamespace(
                    finish_reason='length', message=SimpleNamespace(content=content)
                )])
        runner.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
        return runner

    def test_strict_request_and_accounting_survive_parse_retry(self):
        runner = self.fake_runner(['invalid json', json.dumps(build_expected_output(self.cases[0]))])
        report = run_comparison(self.cases[:1], [(self.config, runner)], max_calls=2)
        first, second = report['attempts']
        self.assertFalse(first['parse_valid'])
        self.assertTrue(second['validator_valid'])
        self.assertEqual(first['cost_usd'], 0.012)
        self.assertEqual(first['input_tokens'], 100)
        self.assertEqual(first['usage']['completion_tokens_details']['reasoning_tokens'], 20)
        self.assertEqual(first['provider'], 'test-provider')
        self.assertEqual(first['generation_id'], 'gen-test')
        self.assertEqual(first['finish_reason'], 'length')
        self.assertEqual(report['candidates']['basic']['cost_usd'], 0.024)
        for request in self.requests:
            self.assertNotIn('temperature', request)
            self.assertNotIn('reasoning', request)
            self.assertEqual(request['reasoning_effort'], 'minimal')
            self.assertEqual(request['max_completion_tokens'], 768)
            self.assertTrue(request['response_format']['json_schema']['strict'])
            self.assertEqual(request['extra_body'], {'provider': {'require_parameters': True}})
            self.assertNotIn('expected', request['messages'][1]['content'])
        self.assertNotIn('[계약 보정 요청]', self.requests[0]['messages'][1]['content'])
        self.assertIn('[계약 보정 요청]', self.requests[1]['messages'][1]['content'])
        self.assertIn('invalid json', self.requests[1]['messages'][1]['content'])

    def test_validator_failure_retains_usage_and_id_metric(self):
        raw = build_expected_output(self.cases[0])
        raw['next_actions'][0]['target_id'] = 'invented-id'
        report = run_comparison(self.cases[:1], [(self.config, self.fake_runner([json.dumps(raw)]))])
        record = report['attempts'][0]
        self.assertTrue(record['schema_valid'])
        self.assertFalse(record['validator_valid'])
        self.assertLess(record['metrics']['ids']['accuracy'], 1)
        self.assertEqual(record['cost_usd'], 0.012)

    def test_unknown_cost_and_repeat_links_versions(self):
        self.assertEqual(list(MODELS.values()).count('basic'), 3)
        self.assertEqual(list(MODELS.values()).count('premium'), 3)
        raw = json.dumps(build_expected_output(self.cases[0]))
        report = run_comparison(self.cases[:1], [(self.config, self.fake_runner([raw, raw], None))],
            repeats=2, parent_links={'basic:coach-normal-01:1': 'parent:case:1'})
        record = report['attempts'][0]
        self.assertIsNone(record['cost_usd'])
        self.assertEqual(record['cost_source'], 'unknown')
        self.assertEqual(record['parent_basic_execution_id'], 'parent:case:1')
        self.assertEqual(report['candidates']['basic']['unknown_cost_calls'], 2)
        self.assertEqual(report['candidates']['basic']['consistency_by_case'][self.cases[0].id]['label_agreement'], 1)
        self.assertEqual(record['metrics']['label_accuracy'], 1)
        self.assertEqual(record['metrics']['evidence_accuracy'], 1)
        self.assertIn('dataset_version', report['versions'])
        json.dumps(report)

    def test_schema_failure_and_zero_actual_cost(self):
        raw = build_expected_output(self.cases[0])
        del raw['intent_assessment']
        report = run_comparison(self.cases[:1], [(self.config, self.fake_runner([json.dumps(raw)], 0))])
        record = report['attempts'][0]
        self.assertTrue(record['parse_valid'])
        self.assertFalse(record['schema_valid'])
        self.assertIsNone(record['validator_valid'])
        self.assertEqual(record['cost_source'], 'usage.cost')
        self.assertEqual(record['cost_usd'], 0)

    def test_hard_timeout_terminates_isolated_call(self):
        class FakeParentConnection:
            def __init__(self):
                self.closed = False

            def poll(self, timeout):
                self.timeout = timeout
                return False

            def close(self):
                self.closed = True

        class FakeChildConnection:
            def close(self):
                pass

        class FakeProcess:
            def __init__(self, **kwargs):
                self.started = False
                self.terminated = False
                self.alive = True

            def start(self):
                self.started = True

            def terminate(self):
                self.terminated = True
                self.alive = False

            def join(self, timeout=None):
                pass

            def is_alive(self):
                return self.alive

        parent = FakeParentConnection()
        process = FakeProcess()
        context = SimpleNamespace(
            Pipe=lambda duplex: (parent, FakeChildConnection()),
            Process=lambda **kwargs: process,
        )
        runner = object.__new__(OpenAICompatibleRunner)
        runner.config = self.config
        runner.system_prompt = 'fixed skill'
        runner.api_key = 'not-a-real-key'
        runner.base_url = 'http://127.0.0.1:1/v1'
        runner.timeout_seconds = 0.01
        runner.max_completion_tokens = 768

        with patch('evals.run_model_comparison.multiprocessing.get_context', return_value=context):
            with self.assertRaises(HardProviderTimeoutError):
                runner._generate_isolated(self.cases[0])

        self.assertTrue(process.started)
        self.assertTrue(process.terminated)
        self.assertTrue(parent.closed)
        self.assertEqual(runner.last_record, {})

        class TimeoutRunner:
            last_record = {}

            def generate(self, case):
                raise HardProviderTimeoutError()

        report = run_comparison(self.cases[:1], [(self.config, TimeoutRunner())])
        record = report['attempts'][0]
        self.assertEqual(record['failure_state'], 'timeout')
        self.assertIsNone(record['cost_usd'])

    def test_isolated_provider_failure_returns_without_cost(self):
        runner = OpenAICompatibleRunner(
            self.config,
            system_prompt='fixed skill',
            api_key='not-a-real-key',
            base_url='http://127.0.0.1:1/v1',
            timeout_seconds=5,
            max_completion_tokens=32,
        )
        report = run_comparison(self.cases[:1], [(self.config, runner)])
        record = report['attempts'][0]
        self.assertEqual(record['failure_state'], 'provider_error')
        self.assertEqual(record['failure_reason'], 'IsolatedProviderError')
        self.assertIsNone(record['cost_usd'])
        self.assertEqual(record['cost_source'], 'unknown')

    def test_isolated_json_decode_error_is_a_schema_violation(self):
        self.assertEqual(
            _provider_failure_state(IsolatedProviderError('JSONDecodeError')),
            'schema_violation',
        )

    def test_consistency_does_not_count_failed_labels_as_agreement(self):
        records = [{'labels': {'intent': 'aligned'}, 'contract_valid': True},
                   {'labels': {'intent': 'partial'}, 'contract_valid': True},
                   {'labels': None, 'contract_valid': False}]
        self.assertEqual(consistency(records)['label_agreement'], 0)
        self.assertEqual(consistency(records)['valid_pairs'], 1)
        self.assertIsNone(consistency(records[-1:])['label_agreement'])
