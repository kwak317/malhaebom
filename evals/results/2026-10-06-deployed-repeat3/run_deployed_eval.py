import hashlib, inspect, json, os, re, sys, time
from pathlib import Path
from datetime import datetime, timezone
sys.path[:0] = ['/app/backend', '/app']
import httpx
from app.services.coaching_runtime import OpenAICompatibleJsonProvider, ProviderOutputContractError, CoachingProviderResult, load_managed_coaching_prompt, McpLlmCoachingService, build_coaching_service_from_env
from app.services.coaching_prompt import build_contract_repair_user_prompt
from app.services.coaching_skill import load_skill_bundle
from app.schemas.coaching import CoachingLLMOutput
from services.llm import OutputContractError, validate_and_build_response
from evals.coaching_dataset import load_dataset, score_response

OUT = Path('/results')
assert not (OUT/'responses.jsonl').exists(), 'Refuse to overwrite existing evaluation'
cases = load_dataset(OUT/'dataset.v2.jsonl')
assert len(cases) == 30
bundle = load_skill_bundle()
system, version = load_managed_coaching_prompt(None)
assert not os.getenv('LANGFUSE_PROMPT_NAME'), 'Managed prompt needs separate provenance verification'
http_records = []
def capture(response):
    response.read()
    try:
        data = response.json()
        choice = data.get('choices', [{}])[0]
        http_records.append({'status':response.status_code, 'content':choice.get('message',{}).get('content'), 'finish_reason':choice.get('finish_reason'), 'usage':data.get('usage'), 'provider':data.get('provider'), 'response_id':data.get('id')})
    except Exception:
        http_records.append({'status':response.status_code, 'json_response':False})
timeout = float(os.getenv('COACHING_LLM_TIMEOUT_SECONDS','25'))
client = httpx.Client(timeout=timeout, event_hooks={'response':[capture]})
provider = OpenAICompatibleJsonProvider(api_key=os.environ['COACHING_LLM_API_KEY'], model_name=os.environ['COACHING_LLM_MODEL'], base_url=os.environ['COACHING_LLM_BASE_URL'], timeout_seconds=timeout, max_transport_attempts=int(os.getenv('COACHING_LLM_MAX_TRANSPORT_ATTEMPTS','2')), backoff_seconds=float(os.getenv('COACHING_LLM_BACKOFF_SECONDS','0.5')), max_backoff_seconds=float(os.getenv('COACHING_LLM_MAX_BACKOFF_SECONDS','2.0')), http_client=client, prompt_version=version, skill_version=bundle.catalog.skill_version, require_provider_parameters=os.getenv('OPENROUTER_REQUIRE_PARAMETERS','true').lower() not in {'0','false','no','off'})
source_files = ['backend/app/services/coaching_runtime.py','backend/app/services/coaching_prompt.py','backend/app/services/coaching_skill.py','backend/app/schemas/coaching.py','backend/services/llm.py','skills/interview-coach/SKILL.md','skills/interview-coach/problem-solving.md','skills/interview-coach/criteria.json','evals/coaching_dataset.py','evals/semantic_grader.py']
manifest = {'started_at':datetime.now(timezone.utc).isoformat(),'model':provider.model_name,'prompt_version':version,'skill_version':bundle.catalog.skill_version,'criteria_version':bundle.catalog.criteria_version,'skill_bundle_sha256':bundle.sha256,'system_prompt_sha256':hashlib.sha256(system.encode()).hexdigest(),'dataset_sha256':hashlib.sha256((OUT/'dataset.v2.jsonl').read_bytes()).hexdigest(),'skill_example_themes':len(re.findall(r'^\d+\. ',bundle.skill_file.read_text().split('## 가상 긍정·부정 사례')[1],re.M)),'settings':{'timeout_seconds':timeout,'contract_attempts':2,'transport_attempts':provider.max_transport_attempts,'require_provider_parameters':provider.require_provider_parameters,'max_tokens':getattr(provider,'max_tokens',None),'case_cost_limit_usd':float(os.getenv('COACHING_LLM_MAX_COST_USD','0.10'))},'input_mode':'Original 30-case evaluator question + server_context; expectations excluded from LLM input; not authenticated HTTP/MCP/DB E2E','human_review':False,'source_hashes':{p:hashlib.sha256((Path('/app')/p).read_bytes()).hexdigest() for p in source_files}}
(OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
(OUT/'system_prompt.txt').write_text(system)
(OUT/'skill_bundle.txt').write_text(bundle.rules_text)
(OUT/'runtime_contract_loop.py.txt').write_text(inspect.getsource(McpLlmCoachingService.analyze))
(OUT/'runtime_provider_factory.py.txt').write_text(inspect.getsource(build_coaching_service_from_env))
print(json.dumps({'event':'plan','cases':30,'model':provider.model_name,'prompt':version,'skill_sha256':bundle.sha256,'themes':manifest['skill_example_themes'],'settings':manifest['settings']},ensure_ascii=False),flush=True)
rows=[]
for index, case in enumerate(cases,1):
    base=json.dumps({'question':case.question.model_dump(mode='json'),'server_context':case.context.model_dump(mode='json')},ensure_ascii=False)
    previous=None; violations=None; attempts=[]; final=None; score=None; total_cost=0.0; terminal=None
    started=time.perf_counter()
    for attempt in range(1,3):
        user=base if violations is None else build_contract_repair_user_prompt(base,previous,violations)
        http_records.clear(); raw=None; call_started=time.perf_counter(); entry={'attempt':attempt,'repair':violations is not None}
        try:
            result=provider.generate(system_prompt=system,user_prompt=user,schema=CoachingLLMOutput.model_json_schema(),contract_attempt=attempt)
            raw=result.output if isinstance(result,CoachingProviderResult) else result
            entry['raw_output']=raw
            if isinstance(result,CoachingProviderResult):
                entry.update(input_tokens=result.input_tokens,output_tokens=result.output_tokens,cost_usd=result.cost_usd)
                total_cost+=result.cost_usd or 0
            if total_cost>manifest['settings']['case_cost_limit_usd']: raise RuntimeError('Case cost limit exceeded')
            final=validate_and_build_response(raw,case.context)
            score=score_response(case,final).model_dump(mode='json')
            entry['contract_valid']=True
        except OutputContractError as e:
            violations=e.violations; previous=e.previous_output if isinstance(e,ProviderOutputContractError) else raw
            if isinstance(e,ProviderOutputContractError): total_cost+=e.cost_usd or 0
            entry.update(contract_valid=False,violations=violations,previous_output=previous,error_type=type(e).__name__)
            if attempt==2:terminal='COACHING_OUTPUT_SCHEMA_VIOLATION'
        except Exception as e:
            entry.update(contract_valid=False,error_type=type(e).__name__)
            terminal=type(e).__name__
        entry.update(latency_seconds=round(time.perf_counter()-call_started,3),http_responses=list(http_records))
        attempts.append(entry)
        if final is not None or terminal is not None:break
    policies=score['semantic_evaluation']['automatic_policy_checks'] if score else {}
    overall=bool(score and all(score['label_results'].values()) and score['evidence_correct']==score['evidence_total'] and all(v for v in policies.values() if v is not None))
    row={'index':index,'case_id':case.id,'category':case.category,'question':case.question.model_dump(mode='json'),'context':case.context.model_dump(mode='json'),'expected':case.expected.model_dump(mode='json'),'attempts':attempts,'response':final.model_dump(mode='json') if final else None,'score':score,'overall_automatic_pass':overall,'terminal_error':terminal,'latency_seconds':round(time.perf_counter()-started,3),'cost_usd_known':total_cost}
    rows.append(row)
    with (OUT/'responses.jsonl').open('a') as f:f.write(json.dumps(row,ensure_ascii=False)+'\n')
    print(json.dumps({'event':'case','index':index,'case_id':case.id,'contract_valid':final is not None,'overall':overall,'attempts':len(attempts),'error':terminal},ensure_ascii=False),flush=True)
    if sum(r['cost_usd_known'] for r in rows)>0.75:raise RuntimeError('Evaluation total cost safety ceiling exceeded')
summary={'cases':len(rows),'contract_valid':sum(r['response'] is not None for r in rows),'expected_labels_all_match':sum(bool(r['score']) and all(r['score']['label_results'].values()) for r in rows),'overall_automatic_pass':sum(r['overall_automatic_pass'] for r in rows),'contract_attempts':sum(len(r['attempts']) for r in rows),'transport_calls':sum(len(a['http_responses']) for r in rows for a in r['attempts']),'repair_cases':sum(len(r['attempts'])>1 for r in rows),'known_cost_usd':sum(r['cost_usd_known'] for r in rows),'category':{cat:{'count':sum(r['category']==cat for r in rows),'contract_valid':sum(r['category']==cat and r['response'] is not None for r in rows),'overall_pass':sum(r['category']==cat and r['overall_automatic_pass'] for r in rows)} for cat in ['normal','boundary','failure']},'finished_at':datetime.now(timezone.utc).isoformat()}
(OUT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
print(json.dumps({'event':'summary',**summary},ensure_ascii=False),flush=True)
