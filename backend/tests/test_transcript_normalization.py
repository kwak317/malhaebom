import copy,json,unittest
import httpx
from openai import APIConnectionError, APIStatusError
from unittest.mock import Mock, patch
from types import SimpleNamespace
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.core.auth import AuthenticatedUser, create_require_authenticated_user
from app.services.persistent_analysis_jobs import PersistentAnalysisJobService
from app.services.transcript_normalization import install_transcript_normalization, TranscriptNormalizationService, PROMPT_SHA256
from pathlib import Path

ID='40000000-0000-4000-8000-000000000001'
OUTPUT={'transcript':'서버 성능이 부족한 줄 알았는데 확인해 보니','edit_log':[{'original':'서버가 딸리나 싶었는데 까보니','replacement':'서버 성능이 부족한 줄 알았는데 확인해 보니','edit_type':'사투리와 말투','reason':'표준어로 변경'}],'confirmations':[],'meaning_preservation_check':'의미를 유지했습니다.'}
def provider_output(value):
    edits=[]
    for e in value['edit_log']:
        edits.append({**e,'requires_confirmation':False,'applied':True})
    for c in value['confirmations']:
        matching=next((e for e in edits if e['original']==c['original'] and e['replacement']==c['replacement']),None)
        if matching:
            matching.update(requires_confirmation=True, applied=c['applied'],reason=c['reason'])
        else:
            edits.append({'original':c['original'],'replacement':c['replacement'],'edit_type':'추정','reason':c['reason'],'requires_confirmation':True,'applied':c['applied']})
    return {'transcript':value['transcript'],'edits':edits,'meaning_preservation_check':value['meaning_preservation_check']}

class NormalizationApiTest(unittest.TestCase):
    def setUp(self):
        self.app=FastAPI();self.app.state.coaching_observation_sink=SimpleNamespace(client=None)
        self.jobs=Mock(spec=PersistentAnalysisJobService)
        self.raw={'status':'completed','result':{'transcript':'사투리 원문'}}
        self.jobs.get.return_value=self.raw; self.app.state.analysis_jobs=self.jobs
        self.require_auth=create_require_authenticated_user(None)
        install_transcript_normalization(self.app,self.require_auth)
        self.convert=Mock();self.convert.normalize.return_value={**OUTPUT,'prompt_name':'malhaebom-transcript-normalization','prompt_version':1,'trace_id':'a'*32}
        self.app.state.transcript_normalization=self.convert
        self.app.dependency_overrides[self.require_auth]=lambda: AuthenticatedUser('owner','token')
        self.client=TestClient(self.app)
    def post(self,text='서버가 딸리나 싶었는데 까보니'):
        return self.client.post('/analysis-jobs/'+ID+'/normalize-transcript',json={'transcript':text})
    def test_success_does_not_mutate_raw_stt(self):
        original=copy.deepcopy(self.raw)
        self.assertEqual(self.post().status_code,200);self.assertEqual(self.raw,original)
        self.jobs.get.assert_called_once();self.convert.normalize.assert_called_once()
    def test_unowned_job_never_calls_model(self):
        self.jobs.get.side_effect=KeyError(ID)
        self.assertEqual(self.post().status_code,404);self.convert.normalize.assert_not_called()
    def test_incomplete_job_never_calls_model(self):
        self.raw['status']='failed';self.assertEqual(self.post().status_code,409);self.convert.normalize.assert_not_called()
    def test_invalid_input_never_calls_model(self):
        for text in [' ','가'*5001]:self.assertEqual(self.post(text).status_code,422)
        self.convert.normalize.assert_not_called()
    def test_provider_failure_has_safe_message(self):
        self.convert.normalize.side_effect=RuntimeError('secret provider failure')
        res=self.post();self.assertEqual(res.status_code,503);self.assertNotIn('secret',res.text)
    def test_unauthenticated_request(self):
        self.app.dependency_overrides.clear();self.assertEqual(self.post().status_code,401);self.convert.normalize.assert_not_called()
class NormalizationServiceTest(unittest.TestCase):
    def setUp(self):
        prompt=(Path(__file__).resolve().parents[1]/'app/services/transcript_normalization_v3.txt').read_text()
        self.lf=Mock();self.lf.get_prompt.return_value=SimpleNamespace(prompt=prompt)
        self.llm=Mock(); self.service=TranscriptNormalizationService(self.lf,self.llm)
    def output(self,value):
        self.llm.chat.completions.create.return_value=SimpleNamespace(choices=[SimpleNamespace(finish_reason='stop',message=SimpleNamespace(content=json.dumps(provider_output(value))))],usage=None)
    def test_uses_pinned_managed_v3(self):
        self.output(OUTPUT);res=self.service.normalize('서버가 딸리나 싶었는데 까보니');self.assertEqual(res.transcript,OUTPUT['transcript'])
        self.lf.get_prompt.assert_called_once_with('malhaebom-transcript-normalization',version=3,type='text',cache_ttl_seconds=60)
    def test_prompt_drift_blocks_model(self):
        self.lf.get_prompt.return_value.prompt='changed'
        with self.assertRaises(RuntimeError):self.service.normalize('원문')
        self.llm.chat.completions.create.assert_not_called()
    def test_hallucinated_source_rejected(self):
        self.output(OUTPUT)
        with self.assertRaises(ValueError):self.service.normalize('다른 원문')
    def test_uncertain_edit_generates_matching_log(self):
        value={**OUTPUT,'edit_log':[], 'confirmations':[{'original':'까보니','replacement':'확인해 보니','reason':'추정','applied':True}]}
        self.output(value)
        result=self.service.normalize('서버가 딸리나 싶었는데 까보니')
        self.assertEqual(result.edit_log[0].original,result.confirmations[0].original)
        self.assertEqual(result.edit_log[0].replacement,result.confirmations[0].replacement)
        self.assertEqual(self.llm.chat.completions.create.call_count,1)

    def test_applied_uncertain_replacement_must_exist_in_final(self):
        value={**OUTPUT, 'edit_log':[{'original':'까보니','replacement':'조사해 보니','edit_type':'추정','reason':'추정'}], 'confirmations':[{'original':'까보니','replacement':'조사해 보니','reason':'추정','applied':True}]}
        self.output(value)
        with self.assertRaises(ValueError):self.service.normalize('서버가 딸리나 싶었는데 까보니')

    def test_confirmation_can_reference_part_of_a_sentence_edit(self):
        value={**OUTPUT,'confirmations':[{'original':'까보니','replacement':'확인해 보니','reason':'추정','applied':True}]}
        self.output(value)
        result=self.service.normalize('서버가 딸리나 싶었는데 까보니')
        self.assertEqual(len(result.confirmations),1)

    def test_rhetorical_tone_is_retried_and_rejected_if_unchanged(self):
        value={**OUTPUT,'transcript':'목록이 아닙니까.'}
        self.output(value)
        with self.assertRaises(ValueError):self.service.normalize('서버가 딸리나 싶었는데 까보니')
        self.assertEqual(self.llm.chat.completions.create.call_count,2)
    def test_retry_repairs_contract_once_with_previous_output(self):
        bad={**OUTPUT,'transcript':'목록이 아닙니까.'}
        def response(value):
            return SimpleNamespace(choices=[SimpleNamespace(finish_reason='stop',message=SimpleNamespace(content=json.dumps(provider_output(value))))],usage=None)
        self.llm.chat.completions.create.side_effect=[response(bad),response(OUTPUT)]
        result=self.service.normalize('서버가 딸리나 싶었는데 까보니')
        self.assertEqual(result.transcript,OUTPUT['transcript'])
        self.assertEqual(self.llm.chat.completions.create.call_count,2)
        second=self.llm.chat.completions.create.call_args.kwargs['messages'][1]['content']
        self.assertIn('previous_output',second)
    def test_provider_failure_is_not_retried(self):
        self.llm.chat.completions.create.side_effect=RuntimeError('provider unavailable')
        with self.assertRaises(RuntimeError):self.service.normalize('서버가 딸리나 싶었는데 까보니')
        self.assertEqual(self.llm.chat.completions.create.call_count,1)
    @patch('app.services.transcript_normalization.time.sleep')
    def test_transient_provider_failure_retries_once(self, sleep):
        self.output(OUTPUT)
        good=self.llm.chat.completions.create.return_value
        error=APIStatusError('temporary',response=httpx.Response(503,request=httpx.Request('POST','https://provider.example')),body=None)
        self.llm.chat.completions.create.side_effect=[error,good]
        self.assertEqual(self.service.normalize('서버가 딸리나 싶었는데 까보니').transcript,OUTPUT['transcript'])
        self.assertEqual(self.llm.chat.completions.create.call_count,2)
        sleep.assert_called_once_with(0.5)
    @patch('app.services.transcript_normalization.time.sleep')
    def test_connection_failure_stops_after_two_attempts(self, sleep):
        self.llm.chat.completions.create.side_effect=APIConnectionError(request=httpx.Request('POST','https://provider.example'))
        with self.assertRaises(APIConnectionError):self.service.normalize('원문')
        self.assertEqual(self.llm.chat.completions.create.call_count,2)
    def test_auth_and_credit_errors_do_not_retry(self):
        for status in (400,401,402,403):
            with self.subTest(status=status):
                self.llm.chat.completions.create.reset_mock()
                self.llm.chat.completions.create.side_effect=APIStatusError('permanent',response=httpx.Response(status,request=httpx.Request('POST','https://provider.example')),body=None)
                with self.assertRaises(APIStatusError):self.service.normalize('원문')
                self.assertEqual(self.llm.chat.completions.create.call_count,1)

    def test_unapplied_uncertain_source_must_remain(self):
        value={**OUTPUT,'confirmations':[{'original':'까보니','replacement':'확인해 보니','reason':'추정','applied':False}]}
        self.output(value)
        with self.assertRaises(ValueError):self.service.normalize('서버가 딸리나 싶었는데 까보니')

    def test_expanded_rhetorical_expression_is_rejected(self):
        value={**OUTPUT,'transcript':'속도만 빠르면 무엇 하겠습니까, 데이터가 정확해야 합니다.'}
        self.output(value)
        with self.assertRaises(ValueError):self.service.normalize('서버가 딸리나 싶었는데 까보니')
        self.assertEqual(self.llm.chat.completions.create.call_count,2)

    def test_polite_question_variant_is_rejected(self):
        value={**OUTPUT,'transcript':'자주 보는 목록이지 않습니까.'}
        self.output(value)
        with self.assertRaises(ValueError):self.service.normalize('서버가 딸리나 싶었는데 까보니')
        self.assertEqual(self.llm.chat.completions.create.call_count,2)

    def test_requested_model_low_and_5000_tokens(self):
        self.output(OUTPUT)
        self.service.normalize('서버가 딸리나 싶었는데 까보니')
        params=self.llm.chat.completions.create.call_args.kwargs
        self.assertEqual(params['model'],'google/gemini-3.1-pro-preview')
        self.assertEqual(params['max_tokens'],5000)
        self.assertEqual(params['extra_body']['reasoning']['effort'],'low')

    def raw_output(self, value, finish='stop', usage=None):
        self.llm.chat.completions.create.return_value=SimpleNamespace(choices=[SimpleNamespace(finish_reason=finish,message=SimpleNamespace(content=json.dumps(value)))],usage=usage)

    def test_provider_schema_has_only_one_edit_list(self):
        self.output(OUTPUT)
        self.service.normalize('서버가 딸리나 싶었는데 까보니')
        properties=self.llm.chat.completions.create.call_args.kwargs['response_format']['json_schema']['schema']['properties']
        self.assertEqual(set(properties),{'transcript','edits','meaning_preservation_check'})

    def test_applied_certain_replacement_is_also_validated(self):
        value=provider_output(OUTPUT);value['edits'][0]['replacement']='없는 수정 표현'
        self.raw_output(value)
        with self.assertRaises(ValueError): self.service.normalize('서버가 딸리나 싶었는데 까보니')
        self.assertEqual(self.llm.chat.completions.create.call_count,2)

    def test_unapplied_edit_is_confirmation_only(self):
        value={'transcript':'서버가 딸리나 싶었는데 까보니','edits':[{'original':'딸리나','replacement':'부족한가','edit_type':'추정','reason':'확인 필요','requires_confirmation':True,'applied':False}],'meaning_preservation_check':'원문 유지'}
        self.raw_output(value);result=self.service.normalize(value['transcript'])
        self.assertEqual(result.edit_log,[]);self.assertEqual(len(result.confirmations),1)
        self.assertFalse(result.confirmations[0].applied)

    def test_unflagged_deletion_is_rejected(self):
        value={'transcript':'서버가','edits':[{'original':'딸리나','replacement':'','edit_type':'삭제','reason':'추정 삭제','requires_confirmation':False,'applied':True}],'meaning_preservation_check':'의미 확인'}
        self.raw_output(value)
        with self.assertRaises(ValueError):self.service.normalize('서버가 딸리나')
        obs=self.lf.start_observation.return_value
        self.assertEqual(obs.update.call_args.kwargs['metadata']['failure_code'],'DELETION_NOT_FLAGGED')

    def test_invalid_json_logs_safe_code_and_usage(self):
        self.raw_output({'private':'원문비밀123'},usage=SimpleNamespace(prompt_tokens=50,completion_tokens=30))
        with self.assertLogs('app.services.transcript_normalization',level='WARNING') as logs:
            with self.assertRaises(ValueError):self.service.normalize('원문비밀123')
        text=' '.join(logs.output)
        self.assertIn('INVALID_JSON_SCHEMA',text);self.assertIn('input_tokens=50',text)
        self.assertNotIn('원문비밀123',text)
        calls=self.lf.start_observation.call_args_list
        self.assertEqual(calls[0].kwargs['metadata']['operation_id'],calls[1].kwargs['metadata']['operation_id'])
        self.assertEqual([c.kwargs['metadata']['attempt'] for c in calls],[1,2])

    def test_incomplete_output_logs_distinct_code(self):
        self.raw_output(provider_output(OUTPUT),finish='length')
        with self.assertRaises(ValueError):self.service.normalize('서버가 딸리나 싶었는데 까보니')
        self.assertEqual(self.lf.start_observation.return_value.update.call_args.kwargs['status_message'],'INCOMPLETE_OUTPUT')

    def test_old_duplicate_provider_contract_is_rejected(self):
        self.raw_output(OUTPUT)
        with self.assertRaises(ValueError):self.service.normalize('서버가 딸리나 싶었는데 까보니')

    def test_transport_then_validation_failure_stops_after_two_calls(self):
        error=APIStatusError('temporary',response=httpx.Response(503,request=httpx.Request('POST','https://provider.example')),body=None)
        self.raw_output({'invalid':'응답'})
        self.llm.chat.completions.create.side_effect=[error,self.llm.chat.completions.create.return_value]
        with patch('app.services.transcript_normalization.time.sleep'):
            with self.assertRaises(ValueError):self.service.normalize('원문')
        self.assertEqual(self.llm.chat.completions.create.call_count,2)
