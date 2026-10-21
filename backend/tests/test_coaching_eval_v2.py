"""v2 정답 정책, 독립 점수와 미검토 분모를 검증한다. 외부 API 없음."""
import unittest
from copy import deepcopy
from test_coaching_eval import PROJECT_ROOT
from evals.coaching_dataset import load_dataset, score_response, CoachingEvaluationCase
from evals.run_model_comparison import build_expected_output, run_comparison, CandidateConfig, MockCandidateRunner
from evals.semantic_grader import SemanticReview, evaluate_semantic, summarize_semantic
from services.llm import validate_and_build_response
from pydantic import ValidationError


class EvaluationV2Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = load_dataset(PROJECT_ROOT / 'evals/dataset.v2.jsonl')

    def test_version_selection_and_annotations(self):
        self.assertEqual(len(self.cases), 30)
        self.assertEqual([int(c.id[-2:]) for c in self.cases if c.expected.semantic],
                         [1,2,4,7,10,14,15,16,17,18,20,21,22,23,30])
        self.assertTrue(all(c.dataset_version == 'v2' and c.exclude_job_alignment_and_status for c in self.cases))
        self.assertTrue(all(c.expected.critical_failure_conditions for c in self.cases))
        self.assertTrue(all(c.dataset_version == 'v1' and c.expected.semantic is None
                            for c in load_dataset(PROJECT_ROOT / 'evals/dataset.jsonl')))

    def test_all_30_labels_and_valid_fixtures(self):
        # 독립 판정 정책으로 승인된 전체 intent/C/A/V 행렬.
        matrix = [
            ('aligned','met','met','not_observed'),('aligned','met','met','met'),
            ('aligned','met','met','met'),('aligned','met','met','partial'),
            ('aligned','met','met','met'),('aligned','met','met','not_observed'),
            ('aligned','met','met','met'),('aligned','met','met','met'),
            ('aligned','met','met','partial'),('aligned','met','met','not_observed'),
            ('aligned','met','met','met'),('aligned','met','met','met'),
            ('partial','partial','partial','not_observed'),('aligned','partial','not_observed','partial'),
            ('aligned','partial','met','partial'),('aligned','partial','undetermined','partial'),
            ('partial','not_observed','met','undetermined'),('aligned','partial','met','partial'),
            ('off_topic','met','met','partial'),('off_topic','met','met','met'),
            ('aligned','partial','met','not_observed'),('aligned','partial','met','not_observed'),
        ] + [('off_topic','not_observed','not_observed','not_observed')] * 4 + [
            ('undetermined','not_observed','not_observed','not_observed')] + [
            ('off_topic','not_observed','not_observed','not_observed')] * 3
        for case, expected in zip(self.cases, matrix):
            with self.subTest(case=case.id):
                labels = case.expected.criterion_assessments
                self.assertEqual((case.expected.intent_label.value, *(labels[k].value for k in
                                  ('problem_context','own_action','result_verification'))), expected)
                response = validate_and_build_response(build_expected_output(case), case.context)
                score = score_response(case,response)
                self.assertEqual(score.accuracy,1)
                self.assertEqual(score.judgement_total,4)

    def test_excluded_job_status_and_evidence_do_not_change_accuracy(self):
        case = self.cases[1]
        response = validate_and_build_response(build_expected_output(case),case.context)
        changed = response.model_copy(update={'status': type(response.status)('needs_more_info'),
                                             'job_alignment': [],
                                             'evidence': [e for e in response.evidence if e.source_type != 'job_alignment']})
        self.assertEqual(score_response(case,changed).accuracy,1)

    def test_review_is_explicit_and_critical_is_independent(self):
        case = self.cases[0]
        unreviewed = evaluate_semantic(case)
        review = {'reviewer':'human','rationale':'원문 대조',
                  'scores':{k:2 for k in ('reason','action','clarifying_question','hallucination')},
                  'critical_failure':True,'critical_failure_reasons':['허위 성과 진술 지시']}
        summary = summarize_semantic([unreviewed,evaluate_semantic(case,review=review)])
        self.assertEqual(summary['semantic']['reason'],{'reviewed':1,'mean':2})
        self.assertEqual(summary['critical_failure_rate'],1)
        self.assertIsNone(summarize_semantic([unreviewed])['critical_failure_rate'])
        for invalid in (-1,3,True,1.5,'2'):
            with self.subTest(score=invalid), self.assertRaises(ValidationError):
                SemanticReview.model_validate({**review,'scores':{'reason':invalid}})
        with self.assertRaises(ValueError):
            evaluate_semantic(self.cases[2],review=review)

    def test_annotation_references_are_validated(self):
        raw = deepcopy(self.cases[0].model_dump(mode='json'))
        raw['expected']['semantic']['reason']['support_segment_ids'] = ['missing']
        with self.assertRaises(ValidationError):
            CoachingEvaluationCase.model_validate(raw)

    def test_runner_keeps_case_run_review_separate(self):
        case = self.cases[0]
        config = CandidateConfig('mock','mock','expected')
        key = f'mock:{case.id}:2:1'
        report = run_comparison([case],[(config,MockCandidateRunner('expected'))],repeats=2,
            semantic_reviews={key:{'reviewer':'human','rationale':'원문 검토','scores':{'reason':1},'critical_failure':False}})
        self.assertEqual(report['versions']['dataset_version'],['v2'])
        self.assertNotIn('jobs',report['attempts'][0]['labels'])
        summary = report['candidates']['mock']['semantic_quality']
        self.assertEqual(summary['semantic']['reason'],{'reviewed':1,'mean':1})
        self.assertEqual(summary['critical_failure_rate'],0)
        with self.assertRaises(ValueError):
            run_comparison([case],[(config,MockCandidateRunner('expected'))],semantic_reviews={'wrong':{}})

    def test_automatic_checks_are_not_semantic_scores(self):
        case = self.cases[0]
        output = build_expected_output(case)
        output['clarifying_question'] = None
        output['next_actions'][0]['target_id'] = 'own_action'
        result = evaluate_semantic(case,output)
        self.assertFalse(result['automatic_policy_checks']['question_presence'])
        self.assertFalse(result['automatic_policy_checks']['action_targets'])
        self.assertTrue(all(value is None for value in result['scores'].values()))

    def test_critical_review_survives_contract_failure_and_retry(self):
        case = self.cases[0]
        class BrokenRunner:
            last_record = {}
            def generate(self, case):
                self.last_record = {'usage': {'cost': 0.01, 'prompt_tokens': 10}}
                return {},10,0,0.01
        config = CandidateConfig('broken','mock','expected')
        key = f'broken:{case.id}:1:1'
        report = run_comparison([case],[(config,BrokenRunner())],max_calls=2,
            semantic_reviews={key:{'reviewer':'human','rationale':'최초 응답 검토',
                                   'critical_failure':True,'critical_failure_reasons':['날조']}})
        self.assertEqual(len(report['attempts']),2)
        self.assertTrue(report['attempts'][0]['semantic_evaluation']['critical_failure'])
        self.assertIsNone(report['attempts'][1]['semantic_evaluation']['critical_failure'])
        self.assertEqual(sum(r['cost_usd'] for r in report['attempts']),0.02)
        self.assertEqual(report['candidates']['broken']['critical_failure_by_call']['critical_failure_count'],1)
