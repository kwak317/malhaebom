"""Assessment evidence and offline regrade regressions; no model requests."""
import json
import unittest
from copy import deepcopy
from test_coaching_eval import PROJECT_ROOT
from evals.coaching_dataset import load_dataset, score_response
from evals.run_model_comparison import build_expected_output, build_system_prompt
from evals.regrade_saved_results import regrade_record
from services.llm import validate_and_build_response, OutputContractError
from app.schemas.coaching import CoachingLLMOutput
from app.services.coaching_skill import load_skill_bundle
from pydantic import ValidationError


class PolicyAlignmentTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases=load_dataset(PROJECT_ROOT/'evals/dataset.v2.jsonl')

    def test_negative_evidence_allowed_and_source_still_checked(self):
        case=self.cases[20];output=build_expected_output(case)
        result=validate_and_build_response(output,case.context)
        self.assertEqual(result.criterion_assessments[2].assessment.value,'not_observed')
        self.assertEqual(score_response(case,result).accuracy,1)
        output['criterion_assessments'][2]['evidence'][0]['quote']='검증에 성공했습니다.'
        with self.assertRaises(OutputContractError):validate_and_build_response(output,case.context)

    def test_negative_evidence_never_requires_fabricated_source(self):
        case=self.cases[20];output=build_expected_output(case)
        output['criterion_assessments'][2]['evidence']=[]
        self.assertEqual(score_response(case,validate_and_build_response(output,case.context)).accuracy,1)
        output['criterion_assessments'][2]['needed']=None
        with self.assertRaises(ValidationError):CoachingLLMOutput.model_validate(output)

    def test_partial_quote_passes_v2_but_not_preserved_v1(self):
        for filename,exact in [('dataset.v2.jsonl',False),('dataset.jsonl',True)]:
            case=load_dataset(PROJECT_ROOT/'evals'/filename)[1]
            output=build_expected_output(case)
            output['criterion_assessments'][0]['evidence'][0]['quote']='p95가 1.8초까지 증가했습니다.'
            score=score_response(case,validate_and_build_response(output,case.context))
            self.assertEqual(score.evidence_correct==score.evidence_total,not exact)

    def test_real_quote_from_other_target_segment_fails_support(self):
        case=self.cases[1];output=build_expected_output(case)
        output['criterion_assessments'][0]['evidence']=deepcopy(output['criterion_assessments'][1]['evidence'])
        score=score_response(case,validate_and_build_response(output,case.context))
        self.assertLess(score.evidence_correct,score.evidence_total)
        self.assertTrue(all(score.label_results.values()))

    def test_one_good_quote_cannot_hide_unsupported_extra_quote(self):
        case=self.cases[1];output=build_expected_output(case)
        output['criterion_assessments'][0]['evidence']+=deepcopy(output['criterion_assessments'][1]['evidence'])
        score=score_response(case,validate_and_build_response(output,case.context))
        self.assertLess(score.evidence_correct,score.evidence_total)

    def test_intent_and_criteria_are_independent_even_off_topic(self):
        case=self.cases[19];output=build_expected_output(case)
        score=score_response(case,validate_and_build_response(output,case.context))
        self.assertEqual(case.expected.intent_label.value,'off_topic')
        self.assertTrue(all(v.value=='met' for v in case.expected.criterion_assessments.values()))
        self.assertEqual(score.judgement_correct,4)
        self.assertNotIn('status',score.label_results)

    def test_prompt_explicitly_delivers_policy(self):
        bundle=load_skill_bundle()
        prompt=build_system_prompt(bundle.rules_text,'coaching-output-v4.2',bundle.catalog.skill_version)
        self.assertIn(bundle.rules_text,prompt)
        for text in ['intent와 독립적으로','실제 경험이 없다고 단정하지 않는다',
                     '개인의 행동으로 바꾸지 않는다','확인·테스트 행위만 있고 실제 관찰 결과가 없거나']:
            self.assertIn(text,prompt)

    def record(self,case,raw,infra=False):
        return {'execution_id':'mock:1','model':'mock','tier':'basic','case_id':case.id,
                'raw_output':raw,'parsed_output':{'untrusted':'saved object'},
                'provider':'fixture','usage':{'cost':0.0123},'generation_id':'fixture-gen',
                'classification':{'infrastructure':infra,'quality_failure':not infra,'types':[]},
                'automatic_critical':{'detected':None}}

    def test_regrade_reads_original_raw_and_preserves_metadata(self):
        case=self.cases[20];record=self.record(case,json.dumps(build_expected_output(case)))
        before=deepcopy(record);result=regrade_record(record,case)
        self.assertTrue(result['regrade']['quality_success'])
        self.assertEqual(record,before)
        self.assertEqual(result['source_record'],before)
        self.assertTrue(all(v is None for v in result['regrade']['semantic_evaluation']['scores'].values()))

    def test_parse_failure_and_infrastructure_exclusion(self):
        case=self.cases[0]
        for infra in (False,True):
            result=regrade_record(self.record(case,'broken-json',infra),case)['regrade']
            self.assertEqual(result['quality_failure'],not infra)
            self.assertFalse(result['parse_valid'])
            self.assertFalse(result['quality_success'])
