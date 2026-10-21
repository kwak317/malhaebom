"""Local synthetic multi-turn evaluation. No product DB, Langfuse, or deployed API."""
from __future__ import annotations
import hashlib,json,os,re,time,statistics,threading,sys
from dataclasses import asdict
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import datetime,timezone,timedelta
from importlib.metadata import version
from openai import OpenAI
from jsonschema import Draft202012Validator

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'server-policy'))
from app.services.preparation_conversation_policy import decide_preparation_action,preparation_completion_message
from app.services.preparation_conversation_generation import generate_preparation_response
MODEL='google/gemini-3.5-flash-lite'
LOCK=threading.Lock()
P_VERSION='preparation-conversation-v3.1-local-candidate'
S_VERSION='preparation-conversation-v3.1-local-candidate'

def obj(props):return {'type':'object','additionalProperties':False,'properties':props,'required':list(props)}
def string(maximum=300):return {'type':'string','minLength':1,'maxLength':maximum}
def nullable(schema):return {'anyOf':[schema,{'type':'null'}]}
fact=obj({'kind':{'type':'string','enum':['company','period','role','responsibility','project','action','outcome','technology']},'value':string(),'source_message_id':string(),'source_excerpt':string()})
update=obj({'action':{'type':'string','enum':['propose','request_save','discard']},'draft_id':nullable(string()),'draft_version':nullable({'type':'integer','minimum':1}),'review_stage':nullable({'type':'string','enum':['collecting','awaiting_confirmation']}),'facts':{'type':'array','maxItems':12,'items':fact}})
SCHEMA=obj({'intent':{'type':'string','enum':['answer','clarify','correction','profile_update','change_step','out_of_scope','refusal','support']},'message':string(800),'follow_up_question':nullable(string(280)),'next_action':{'type':'string','enum':['stay','request_change_stage','request_skip','request_rerecord']},'requested_stage':nullable({'type':'string','enum':['ncs','readme','resume','interview']}),'profile_update':nullable(update)})
VALIDATOR=Draft202012Validator(SCHEMA)
source=(ROOT/'prompt-source.md').read_text()
skill=(ROOT/'skill-source.md').read_text().split('---',2)[2].strip()
system=source.split('## System 본문\n',1)[1].split('## 계약 예시',1)[0].strip()
values={'prompt_version':P_VERSION,'skill_version':S_VERSION,'skill_text':skill}
SYSTEM=re.sub(r'\{\{(.*?)\}\}',lambda m:values[m.group(1)],system)
(ROOT/'system_prompt.txt').write_text(SYSTEM)
(ROOT/'output-schema.json').write_text(json.dumps(SCHEMA,ensure_ascii=False,indent=2))
DATA=json.loads((ROOT/'scenarios.json').read_text())
KEY=os.getenv('OPENROUTER_API_KEY') or os.getenv('COACHING_LLM_API_KEY')
if not KEY:raise SystemExit('No local model credential configured.')

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save_line(path,data):
    with LOCK:
        with (ROOT/path).open('a') as f:f.write(json.dumps(data,ensure_ascii=False)+'\n')

def contract_errors(out,context):
    errors=[e.json_path+': '+e.message for e in VALIDATOR.iter_errors(out)]
    if errors:return errors
    def require(check,label):
        if not check:errors.append(label)
    action=out['next_action'];intent=out['intent'];u=out['profile_update'];pending=context['pending_profile_update']
    require(not re.search(r'[?？]',out['message']),'question_in_message')
    q=out['follow_up_question']
    if q:require(q.count('?')+q.count('？')<=1,'multiple_questions')
    if action=='stay':require(out['requested_stage'] is None,'stay_target')
    if action=='request_rerecord':require(intent=='change_step' and context['current_stage']=='first_coaching' and context['available_actions']['can_rerecord'] and out['requested_stage'] is None,'rerecord_gate')
    if action=='request_change_stage':require(intent=='change_step' and out['requested_stage'] in context['available_actions']['change_stage_targets'],'change_stage_gate')
    if action=='request_skip':require(intent=='change_step' and context['available_actions']['can_skip'] and out['requested_stage'] is None,'skip_gate')
    require((u is not None)==(intent=='profile_update'),'profile_intent_relationship')
    if intent=='clarify':require(q is not None and action=='stay','clarify_relationship')
    if intent in ['answer','correction','out_of_scope','refusal','support']:require(action=='stay','intent_stay')
    if u is None:return errors
    require(action=='stay' and out['requested_stage'] is None,'profile_stay')
    if u['action']=='propose':
        require(bool(q),'proposal_question_required')
        require(u['review_stage'] in ['collecting','awaiting_confirmation'],'proposal_review_stage')
        require(1<=len(u['facts'])<=12,'proposal_fact_count')
        if pending and pending['status'] in ['collecting','awaiting_confirmation']:
            require(u['draft_id']==pending['draft_id'] and u['draft_version']==pending['draft_version'],'latest_draft_propose')
        else:require(u['draft_id'] is None and u['draft_version'] is None,'new_draft_ids')
        sources={m['message_id']:m['text'] for m in context['source_messages']}
        for f in u['facts']:
            require(f['source_message_id'] in sources,'invalid_source_message_id')
            require(f['source_excerpt'] in sources.get(f['source_message_id'],''),'source_quote_not_exact')
    else:
        require(not u['facts'] and u['review_stage'] is None,'terminal_update_payload')
        require(bool(pending) and u['draft_id']==pending['draft_id'] and u['draft_version']==pending['draft_version'],'latest_draft_terminal')
        if u['action']=='request_save':require(bool(pending) and pending['status']=='awaiting_confirmation' and pending['confirmation_requested'] and context['available_actions']['can_save_profile'],'save_gate')
        if u['action']=='discard':require(bool(pending) and pending['status'] in ['collecting','awaiting_confirmation'],'discard_gate')
    return errors

def expected_errors(out,step,context):
    e=step['expected'];errors=[]
    if e['intents'] and out['intent'] not in e['intents']:errors.append('unexpected_intent:'+out['intent'])
    if out['next_action']!=e['next_action']:errors.append('unexpected_next_action:'+out['next_action'])
    u=out['profile_update'];a=u['action'] if u else None
    if e['profile_actions'] is not None and a not in e['profile_actions']:errors.append('unexpected_profile_action:'+str(a))
    if a=='request_save' and not e['confirms_current_summary']:errors.append('save_without_explicit_user_confirmation')
    if e['must_have_confirmation_draft']:
        p=context['pending_profile_update']
        if not p or p['status']!='awaiting_confirmation' or not p['confirmation_requested']:errors.append('previous_turn_did_not_request_summary_confirmation')
    if u and a=='propose':
        kinds={f['kind'] for f in u['facts']}
        for k in e['required_fact_kinds']:
            if k not in kinds:errors.append('missing_fact_kind:'+k)
    return errors

def apply_fixture(out,step,context,contract,saved):
    """Test-only state, never product persistence. Explicit expected consent is independent of LLM."""
    u=out['profile_update']
    if contract or u is None:return 'no_update'
    old=context['pending_profile_update']
    if u['action']=='propose':
        context['pending_profile_update']={'draft_id':old['draft_id'] if old and old['status'] in ['collecting','awaiting_confirmation'] else 'draft-'+context['fixture_id'],'draft_version':old['draft_version']+1 if old and old['status'] in ['collecting','awaiting_confirmation'] else 1,'facts':u['facts'],'summary':out['message'],'status':u['review_stage'],'confirmation_requested':u['review_stage']=='awaiting_confirmation'}
        return 'proposal_recorded_in_memory'
    if u['action']=='request_save':
        # Consent is checked by the real server policy, never by evaluation labels.
        key=(old['draft_id'],old['draft_version'])
        if key in saved:return 'duplicate_blocked'
        saved.add(key)
        context['confirmed_supplemental_context'].append({'draft_id':old['draft_id'],'draft_version':old['draft_version'],'facts':old['facts'],'source_type':'user_chat','user_confirmed':True,'source_message_ids':sorted({f['source_message_id'] for f in old['facts']})})
        old['status']='saved'
        return 'saved_to_test_memory_only'
    context['pending_profile_update']=None
    return 'unsaved_draft_discarded'

COACH={'question_id':'preset-04','answer_revision_id':'first-answer-1','coaching_run_id':'coaching-1','question_text':'프로젝트 개발 중 발생한 문제를 어떻게 해결했나요?','answer_text':'재고 프로젝트의 API 오류 원인을 로그로 확인하고 코드를 수정했습니다.','coaching_result':{'gaps':[{'criterion':'결과 확인','reason':'코드를 수정한 행동은 있으나 수정 후 확인한 조건과 결과는 현재 답변에서 드러나지 않음','source_excerpt':'재고 프로젝트의 API 오류 원인을 로그로 확인하고 코드를 수정했습니다.'}]},'delivery':{'cpm':350,'reference_cpm':320,'long_silences':0,'repetitions':0,'measurement_limit':'참고값이며 채용 기준이 아님'}}

def run_case(case,repeat):
    cid=case['id'];runid=f'{cid}-R{repeat}'
    context={'fixture_id':runid,'current_stage':case['stage'],'event':'message','current_item':'현재 검토 항목','verified_context':{},'coaching_context':COACH if case['stage']=='first_coaching' else None,'user_statements':[],'source_messages':[],'pending_profile_update':None,'confirmed_supplemental_context':[],'conversation_history':[],'available_actions':{'can_skip':False,'can_rerecord':case['stage']=='first_coaching','can_save_profile':True,'change_stage_targets':[]},'user_message':None}
    saved=set();results=[]
    client=OpenAI(api_key=KEY,base_url='https://openrouter.ai/api/v1',timeout=45,max_retries=0)
    for index,step in enumerate(case['turns'],1):
        text=step['message'];mid=f'{runid}-user-{index}'
        context['source_messages'].append({'message_id':mid,'text':text})
        context['user_message']=text
        request={k:v for k,v in context.items() if k!='fixture_id'}
        request=json.loads(json.dumps(request,ensure_ascii=False))
        def generate():
            response=client.chat.completions.create(model=MODEL,messages=[{'role':'system','content':SYSTEM},{'role':'user','content':json.dumps(request,ensure_ascii=False)}],response_format={'type':'json_schema','json_schema':{'name':'malhaebom_preparation_conversation','strict':True,'schema':SCHEMA}},extra_body={'provider':{'require_parameters':True}},max_tokens=2200)
            return response.model_dump(mode='json')
        start=time.perf_counter()
        generated=generate_preparation_response(generate)
        elapsed=time.perf_counter()-start
        attempts=[asdict(a) for a in generated.attempts]
        out=generated.output
        first=generated.attempts[0]
        first_out=first.output
        first_contract=contract_errors(first_out,request) if isinstance(first_out,dict) else ['no_valid_JSON_response']
        first_behavior=expected_errors(first_out,step,request) if isinstance(first_out,dict) and not list(VALIDATOR.iter_errors(first_out)) else ['not_scoreable']
        contract=contract_errors(out,request) if isinstance(out,dict) else ['no_valid_JSON_response']
        behavior=expected_errors(out,step,request) if isinstance(out,dict) and not list(VALIDATOR.iter_errors(out)) else ['not_scoreable']
        decision=None;policy_errors=[];server_contract=['no_server_response'];effective=None;server_completion=None
        if out:
            try:
                decision=decide_preparation_action(out,request)
                effective=dict(out,message=decision.message,follow_up_question=decision.follow_up_question)
                server_contract=contract_errors(effective,request)
            except Exception as err:policy_errors=[str(err) if isinstance(err,ValueError) else type(err).__name__]
        if decision and not server_contract and not policy_errors:
            effect=apply_fixture(effective,step,context,[],saved)
        else:effect='invalid_response_not_applied'
        if decision and decision.action in ['request_save','discard'] and not server_contract:
            succeeded=effect in ['saved_to_test_memory_only','unsaved_draft_discarded']
            server_completion=preparation_completion_message(decision,succeeded=succeeded)
        context['conversation_history'].append({'role':'user','message':text})
        display=server_completion or (decision.message if decision and not server_contract else generated.failure_message or '응답을 확인하지 못했어요. 현재 단계를 유지합니다.')
        display_question=decision.follow_up_question if decision and not server_contract else None
        context['conversation_history'].append({'role':'assistant','message':display,'follow_up_question':display_question})
        raw=generated.attempts[-1].provider_response
        usage=raw.get('usage') if raw else None
        failure={'type':generated.attempts[-1].error,'http_status':generated.attempts[-1].http_status} if generated.attempts[-1].error else None
        costs=[a.provider_response.get('usage',{}).get('cost') for a in generated.attempts if a.provider_response]
        cost=sum(c for c in costs if isinstance(c,(float,int)))
        rec={'run_id':runid,'scenario_id':cid,'repeat':repeat,'turn':index,'input':request,'expected':step['expected'],'attempts':attempts,'recovered':generated.recovered,'first_output':first_out,'first_contract_errors':first_contract,'first_behavior_errors':first_behavior,'raw_provider_response':raw,'output':out,'server_output':effective,'server_decision':asdict(decision) if decision else None,'server_policy_errors':policy_errors,'server_contract_errors':server_contract,'server_display_message':display,'server_completion_in_test_memory':server_completion,'error':failure,'latency_seconds':elapsed,'usage':usage,'known_cost_USD':cost,'contract_errors':contract,'behavior_errors':behavior,'fixture_effect':effect,'fixture_state_after':{'pending_profile_update':context['pending_profile_update'],'confirmed_supplemental_context':context['confirmed_supplemental_context']}}
        save_line('responses.jsonl',rec)
        results.append({'turn':index,'first_pass':not first_contract and not first_behavior,'pass':not contract and not behavior,'service_pass':not server_contract and not policy_errors and not behavior,'contract_errors':contract,'behavior_errors':behavior,'latency_seconds':elapsed})
    client.close()
    record={'run_id':runid,'scenario_id':cid,'title':case['title'],'repeat':repeat,'first_passed':all(r['first_pass'] for r in results),'passed':all(r['pass'] for r in results),'service_passed':all(r['service_pass'] for r in results),'turns':results,'fixture_saved_experiences':len(context['confirmed_supplemental_context']),'saved_context':context['confirmed_supplemental_context']}
    save_line('runs.jsonl',record)
    print(json.dumps({'completed':runid,'first_passed':record['first_passed'],'service_passed':record['service_passed'],'failed_turns':[r['turn'] for r in results if not r['service_pass']]},ensure_ascii=False),flush=True)
    return record

manifest={'started_at':datetime.now(timezone(timedelta(hours=9))).isoformat(),'execution':'local Docker SDK requests to OpenRouter only','model':MODEL,'prompt_version':P_VERSION,'skill_version':S_VERSION,'hashes':{n:digest(ROOT/n) for n in ['prompt-source.md','skill-source.md','scenarios.json','output-schema.json','system_prompt.txt','run_eval.py','server-policy/app/schemas/preparation_conversation.py','server-policy/app/services/preparation_conversation_policy.py','server-policy/app/services/preparation_conversation_generation.py']},'scenario_count':len(DATA),'repeats':3,'scheduled_turns':sum(len(c['turns']) for c in DATA)*3,'concurrency':3,'settings':{'temperature':'model_default','reasoning':'model_default','max_tokens':2200,'provider_require_parameters':True,'SDK_retries':0,'JSON_or_schema_retries_max':1,'semantic_or_state_repairs':0},'server_policy':'server-policy/app/services/preparation_conversation_policy.py','libraries':{m:version(m) for m in ['openai','jsonschema']},'proof_boundaries':['Real provider responses to manually authored synthetic messages','Test-only in-memory draft and save simulator','No product API, DB, user auth, STT, browser, production or Langfuse verification'],'grader':'hand-authored intent/action/consent expectations plus deterministic schema and source-quote validation; semantic quality requires human review'}
(ROOT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
print(json.dumps({'started':True,'scenarios':12,'repeats':3,'model_requests':manifest['scheduled_turns']},ensure_ascii=False),flush=True)
with ThreadPoolExecutor(max_workers=3) as pool:
    futures=[pool.submit(run_case,c,r) for r in [1,2,3] for c in DATA]
    for future in as_completed(futures):future.result()
records=[json.loads(l) for l in (ROOT/'responses.jsonl').read_text().splitlines()]
runs=[json.loads(l) for l in (ROOT/'runs.jsonl').read_text().splitlines()]
latencies=[r['latency_seconds'] for r in records]
all_attempts=[a for r in records for a in r['attempts']]
known_costs=[a['provider_response'].get('usage',{}).get('cost') for a in all_attempts if a['provider_response']]
known_costs=[c for c in known_costs if isinstance(c,(int,float))]
summary={'scenario_runs':len(runs),'first_passed_runs':sum(r['first_passed'] for r in runs),'passed_runs':sum(r['passed'] for r in runs),'service_passed_runs':sum(r['service_passed'] for r in runs),'conversation_turns':len(records),'model_requests':len(all_attempts),'retry_requests':len(all_attempts)-len(records),'recovered_turns':sum(r['recovered'] for r in records),'first_valid_contract_turns':sum(not r['first_contract_errors'] for r in records),'first_expected_behavior_turns':sum(not r['first_contract_errors'] and not r['first_behavior_errors'] for r in records),'valid_contract_turns':sum(not r['contract_errors'] for r in records),'expected_behavior_turns':sum(not r['behavior_errors'] and not r['contract_errors'] for r in records),'service_passed_turns':sum(not r['server_contract_errors'] and not r['server_policy_errors'] and not r['behavior_errors'] for r in records),'trimmed_invitation_turns':sum((r['server_decision'] or {}).get('response_source')=='server_trimmed_invitation' for r in records),'fixed_guidance_turns':sum((r['server_decision'] or {}).get('response_source')=='server_fixed' for r in records),'generation_failures':sum(r['error'] is not None for r in records),'first_generation_failures':sum(a['error'] is not None for a in [r['attempts'][0] for r in records]),'latency_p50_seconds':statistics.median(latencies),'latency_p95_seconds':sorted(latencies)[int(.95*(len(latencies)-1))],'TTFT':'not measured','known_cost_USD':sum(known_costs),'cost_known_requests':len(known_costs),'by_scenario':[{'id':c['id'],'title':c['title'],'first_passed_repeats':sum(r['first_passed'] for r in runs if r['scenario_id']==c['id']),'passed_repeats':sum(r['passed'] for r in runs if r['scenario_id']==c['id']),'service_passed_repeats':sum(r['service_passed'] for r in runs if r['scenario_id']==c['id']),'repeat_results':[{k:r[k] for k in ['repeat','first_passed','passed','service_passed','fixture_saved_experiences']} for r in sorted(runs,key=lambda r:r['repeat']) if r['scenario_id']==c['id']]} for c in DATA]}
(ROOT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
print(json.dumps(summary,ensure_ascii=False),flush=True)
