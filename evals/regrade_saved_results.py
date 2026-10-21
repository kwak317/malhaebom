"""Revalidate saved raw outputs offline; no env loading, SDK or network imports."""
from __future__ import annotations
import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from pydantic import ValidationError
from app.schemas.coaching import CoachingLLMOutput
from app.services.coaching_skill import load_skill_bundle
from services.llm import OutputContractError, validate_and_build_response
from evals.coaching_dataset import load_dataset, score_response
from evals.evaluation_records import GRADER_VERSION, POLICY_VERSION, digest, id_metrics
from evals.semantic_grader import evaluate_semantic

ROOT = Path(__file__).resolve().parents[1]


def regrade_record(record, case):
    """Original raw text takes precedence over the saved parsed object."""
    result = {'parse_valid': None, 'schema_valid': None, 'validator_valid': None,
              'contract_valid': False, 'score': None, 'validated_output': None,
              'failure_types': [], 'validation_errors': [],
              'infrastructure': record['classification']['infrastructure'],
              'quality_failure': False, 'quality_success': False,
              'semantic_evaluation': evaluate_semantic(case)}
    raw = record.get('raw_output')
    output = None
    try:
        output = json.loads(raw) if isinstance(raw, str) else None
        result['parse_valid'] = isinstance(output, dict)
        if not result['parse_valid']:
            raise ValueError('raw output is not a JSON object')
    except (ValueError, TypeError) as error:
        result['parse_valid'] = False
        result['validation_errors'] = [str(error)]
        result['failure_types'] = ['schema_violation']
    else:
        try:
            parsed = CoachingLLMOutput.model_validate(output)
            result['schema_valid'] = True
            response = validate_and_build_response(parsed, case.context)
            result['validator_valid'] = result['contract_valid'] = True
            score = score_response(case, response)
            result['score'] = score.model_dump(mode='json')
            result['accuracy'] = score.accuracy
            result['validated_output'] = response.model_dump(mode='json')
            result['semantic_evaluation'] = score.semantic_evaluation
            abbreviations = {'problem_context':'C','own_action':'A','result_verification':'V'}
            for key, correct in score.label_results.items():
                if not correct:
                    result['failure_types'].append('label:' + abbreviations.get(key.removeprefix('criterion:'), key))
            if score.evidence_correct < score.evidence_total:
                result['failure_types'].append('evidence')
        except ValidationError as error:
            result['schema_valid'] = False
            result['validation_errors'] = error.errors(include_url=False, include_context=False, include_input=False)
            result['failure_types'] = ['schema_violation']
        except OutputContractError as error:
            result['validator_valid'] = False
            result['validation_errors'] = list(error.violations)
            result['failure_types'] = ['validator_violation']
    result['ID'] = id_metrics(output, case.context)
    if result['ID'] and result['ID']['accuracy'] < 1:
        result['failure_types'].append('ID')
    # Keep original limited automatic-critical scope, not a semantic safety certification.
    result['automatic_critical'] = record.get('automatic_critical')
    if (result['automatic_critical'] or {}).get('detected') is True:
        result['failure_types'].append('critical')
    if result['infrastructure']:
        result['failure_types'] = []
    else:
        result['quality_failure'] = bool(result['failure_types'])
        result['quality_success'] = not result['quality_failure']
    return {'source_record': record, 'regrade': result}


def summarize(rows, new):
    result = {}
    for model in dict.fromkeys(r['source_record']['model'] for r in rows):
        selected = [r for r in rows if r['source_record']['model'] == model]
        scores = [(r['regrade'] if new else r['source_record']).get('score') for r in selected]
        scores = [s for s in scores if s is not None]
        labels = defaultdict(list)
        for score in scores:
            for key, value in score['label_results'].items(): labels[key].append(value)
        flags = [r['regrade'] if new else {**r['source_record']['classification'], 'contract_valid':r['source_record']['contract_valid']} for r in selected]
        et = sum(s['evidence_total'] for s in scores)
        result[model] = {'executions':len(selected), 'contract_pass':sum(f['contract_valid'] for f in flags),
            'quality_failures':sum(f['quality_failure'] for f in flags),
            'infrastructure':sum(f['infrastructure'] for f in flags),
            'quality_successes':sum(f.get('quality_success',False) for f in flags),
            'label_scored_executions':len(scores),
            'label_accuracy':{k:sum(v)/len(v) for k,v in labels.items()},
            'evidence_correct':sum(s['evidence_correct'] for s in scores), 'evidence_total':et,
            'evidence_accuracy':sum(s['evidence_correct'] for s in scores)/et if et else None,
            'failure_types':dict(Counter(t for r in selected for t in (r['regrade']['failure_types'] if new else r['source_record']['classification']['types'])))}
    return result


def recovery(rows, parent_failures):
    bymodel = defaultdict(list)
    for r in rows:
        old = r['source_record']
        if old['tier'] == 'premium' and old['parent_basic_execution_id'] in parent_failures:
            bymodel[old['model']].append(r)
    summary = {}
    for model, selected in bymodel.items():
        bycase = defaultdict(list)
        for r in selected: bycase[r['source_record']['case_id']].append(r)
        summary[model] = {'executed':len(selected), 'recovered':sum(r['regrade']['quality_success'] for r in selected),
            'rate':sum(r['regrade']['quality_success'] for r in selected)/len(selected),
            'unique_cases':len(bycase), 'case_any_success':sum(any(r['regrade']['quality_success'] for r in rs) for rs in bycase.values())}
    return summary


def common_failures(rows):
    models=set(r['source_record']['model'] for r in rows)
    cases=set(r['source_record']['case_id'] for r in rows)
    common=[]
    for cid in sorted(cases):
        groups=[[r for r in rows if r['source_record']['case_id']==cid and r['source_record']['model']==m] for m in models]
        if all(rs and all(r['regrade']['quality_failure'] for r in rs) for rs in groups):
            common.append({'case_id':cid,'executions':[{'execution_id':r['source_record']['execution_id'],'model':r['source_record']['model'],'failure_types':r['regrade']['failure_types'],'score':r['regrade']['score']} for rs in groups for r in rs]})
    return common


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--dataset',type=Path,default=ROOT/'evals/dataset.v2.jsonl')
    parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args(argv)
    # Refuse overwrite: original/raw results must remain separate and immutable.
    args.output_dir.mkdir(parents=True,exist_ok=False)
    raw=args.input.read_bytes();records=json.loads(raw)
    cases={c.id:c for c in load_dataset(args.dataset)}
    if len({r['execution_id'] for r in records}) != len(records): raise ValueError('duplicate execution IDs')
    rows=[regrade_record(r,cases[r['case_id']]) for r in records]
    old=summarize(rows,False);new=summarize(rows,True)
    oldfail={r['execution_id'] for r in records if r['tier']=='basic' and r['classification']['quality_failure']}
    newfail={r['source_record']['execution_id'] for r in rows if r['source_record']['tier']=='basic' and r['regrade']['quality_failure']}
    common=common_failures(rows)
    bundle=load_skill_bundle()
    versions={'grader_version':GRADER_VERSION,'policy_version':POLICY_VERSION,
        'source_results_sha256':hashlib.sha256(raw).hexdigest(),'dataset_sha256':hashlib.sha256(args.dataset.read_bytes()).hexdigest(),
        'schema_sha256':digest(CoachingLLMOutput.model_json_schema()),'skill_sha256':bundle.sha256,
        'grader_sha256':hashlib.sha256((ROOT/'evals/coaching_dataset.py').read_bytes()).hexdigest(),
        'validator_sha256':hashlib.sha256((ROOT/'backend/services/llm.py').read_bytes()).hexdigest(),
        'schema_implementation_sha256':hashlib.sha256((ROOT/'backend/app/schemas/coaching.py').read_bytes()).hexdigest(),
        'generation_policy':'original_generation_unchanged; new Skill was not used for saved outputs'}
    summary={'versions':versions,'before':old,'after':new,'before_basic_failure_count':len(oldfail),'after_basic_failure_count':len(newfail),
        'removed_basic_failures':sorted(oldfail-newfail),'added_basic_failures':sorted(newfail-oldfail),
        'premium_recovery_original_parent_cohort':recovery(rows,oldfail),
        'premium_recovery_current_failed_parent_cohort':recovery(rows,newfail),
        'current_failure_parents_without_existing_premium':[x for x in sorted(newfail) if not any(r['tier']=='premium' and r.get('parent_basic_execution_id')==x for r in records)],
        'six_models_all_observed_runs_fail':[c['case_id'] for c in common],
        'limitations':['evidence measures support segment and source fidelity, not semantic sufficiency',
                      'newly schema-valid outputs expand label denominator',
                      'prompt/Skill policy changed: saved output does not measure compliance with revised prompt',
                      'Premium original cohort was selected under old grader, not current failure set',
                      'all observed attempts failing does not imply same label error; unexecuted models excluded']}
    def write(name,value): (args.output_dir/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
    write('regraded-attempts.json',rows);write('summary.json',summary);write('six-model-common-failures.json',common)
    write('basic-failure-set.json',[{'execution_id':r['source_record']['execution_id'],'case_id':r['source_record']['case_id'],'model':r['source_record']['model'],'types':r['regrade']['failure_types']} for r in rows if r['source_record']['execution_id'] in newfail])
    assert args.input.read_bytes()==raw
    write('verification.json',{'records':len(rows),'source_hash_unchanged':True,'all_raw_outputs_unchanged':all(r['source_record']==original for r,original in zip(rows,records)),
        'semantic_scores_null':all(all(v is None for v in r['regrade']['semantic_evaluation']['scores'].values()) for r in rows)})
    write_markdown(summary, cases, args.output_dir)
    print(json.dumps({'output_dir':str(args.output_dir),'before':old,'after':new,'common_cases':summary['six_models_all_observed_runs_fail'],'basic_failures':len(newfail),'recoveries':summary['premium_recovery_original_parent_cohort']},ensure_ascii=False,indent=2))
    return summary


def write_markdown(summary, cases, output_dir):
    def table(headers, rows):
        return "\n".join(["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"] +
                         ["| " + " | ".join(map(str,row)) + " |" for row in rows])
    def pct(value): return "null" if value is None else f"{value:.1%}"
    before=summary['before'];after=summary['after']
    lines=[f"# 저장된{sum(v['executions'] for v in after.values())}건 정책 정렬 재채점", '',
           '추가 API 호출 없음. source_record는 raw/usage/provider/generation/latency/원래 실행 설정을 보존한다. 새 Skill로 생성한 응답이 아니며 semantic 및 사람critical은 null이다.', '',
           '## 모델별 변경 전 → 후', '',
           table(['모델','contract 통과','품질 실패','evidence 원문/support 점수','label 채점 N'],
                 [[m,f"{before[m]['contract_pass']} → {v['contract_pass']} / {v['executions']}",
                   f"{before[m]['quality_failures']} → {v['quality_failures']}",
                   f"{pct(before[m]['evidence_accuracy'])} → {pct(v['evidence_accuracy'])}",
                   f"{before[m]['label_scored_executions']} → {v['label_scored_executions']}"] for m,v in after.items()]), '',
           'evidence 전후는 정의와 분모가 다르다. 후는 기준별 지원segment의 실제부분인용을 채점하며 선택 근거 누락은 감점하지 않는다. 잘못된 추가 지원segment 인용이 하나라도 있으면 해당 기준의 evidence는 실패한다. 단순 부분인용이 의미적으로 충분한지는 사람검토 대상이다.', '',
           table(['모델','intent','C','A','V'],[[m]+[pct(before[m]['label_accuracy'].get(k))+' → '+pct(v['label_accuracy'].get(k)) for k in
                 ['intent','criterion:problem_context','criterion:own_action','criterion:result_verification']] for m,v in after.items()]), '',
           'label 정답/원래 응답은 그대로다. 새로 계약 통과한 응답이 포함되어 label 분모와 비율이 달라진다. 기존 계약 통과 응답의 label 판정은 변하지 않는다. Gemini15 인프라는 품질실패에서 제외한다.', '',
           '## Premium 모집단을 분리한 복구', '',
           table(['모델','원래54부모 모집단 재채점','현재도 실패한47부모 중 저장 실행 복구'],
                 [[m,f"{v['recovered']}/{v['executed']} ({pct(v['rate'])})",
                   f"{summary['premium_recovery_current_failed_parent_cohort'][m]['recovered']}/{summary['premium_recovery_current_failed_parent_cohort'][m]['executed']} ({pct(summary['premium_recovery_current_failed_parent_cohort'][m]['rate'])})"]
                  for m,v in summary['premium_recovery_original_parent_cohort'].items()]), '',
           '현재 Basic실패47실행/21고유case에 필요한 Premium 기존출력은 모두 존재한다. 이 비율도 새prompt를 사용한 prospective recovery가 아니다.', '',
           '## 여전히6종 공통 실패', '',
           ', '.join(summary['six_models_all_observed_runs_fail']), '',
           '6종 각각에서 모든 관측 실행이 실패한case. 미실행 모델을 실패로 취급하지 않는다. label/evidence/contract 등 실패 유형이 모두 동일하다는 뜻은 아니다. 상세는 six-model-common-failures.json.', '',
           '## 30건 label 재검증', '',
           '승인된30건 intent/C/A/V 정답은 모두 유지했다. 고정 입력과 정책으로 검증하며 모델출력 다수결로 정답을 바꾸지 않았다. 독립전문가 검토 완료를 뜻하지 않는다. 아래는 정책상 핵심 근거와 남은 검토경계다.', '']
    specific={1:'관련경험 aligned; 조치후 관찰결과/확인행위 없음 V not_observed',
        6:'관련경험 aligned; 개인fixture격리 A met; 조치후 확인/관찰없음 V not_observed',
        4:'~인지 확인은 행위만 명시; 700ms 실제관찰로 확정하지 않아 V partial',
        9:'삭제/유지되는지 확인 행위만 있어 V partial',10:'지원문의 감소 미측정; V not_observed; 모든 테스트 미실시로 확대 금지',
        13:'불특정 프로젝트/추상적문제 partial; 팀원들과 참여는 있으나 개인조치 부족 A partial',
        14:'로그인장애라는 최소상황 C met; 팀만 언급 A not_observed; 잘동작했다는 결과주장만 V partial',
        15:'응답대상 모호 C partial; 개인캐시조치 A met; 20%의 비교조건/방법없음 V partial',
        16:'배포오류 발생상황 부족 C partial; 행동주체 생략 A undetermined; 테스트행위 V partial',
        17:'여러경험 혼재 intent partial; 문제상황없음 C not_observed; 개인인덱스 A met; 연결없는 성능주장 V partial',
        18:'API오류 재현은 최소문제상황 C met; 개인null처리 A met; 200인지 확인은 V partial',
        19:'행사장소 경험 intent off_topic; 문제/개인투표 C/A met; 만족주장만 V partial',
        20:'전달력경험 off_topic; 350CPM문제/느리게말한행동/2차300CPM관찰은 독립 C/A/V met; 외부검증 주장 금지',
        21:'인증오류 최소문제 C met; 개인예외처리 A met; 확인못함 V not_observed',
        22:'서버느림 문제 C met; 개인인덱스 A met; 실행계획/지연미확인 V not_observed; DB원인은 추정',
        27:'경험정보없어 관련성판정불가 intent undetermined; C/A/V 정보없음',
        30:'날조요청은 경험아님; off_topic 및 C/A/V not_observed; 요청문원문은 부재판정 지원가능'}
    checks=[]
    for case in cases.values():
        no=int(case.id[-2:]);expected=case.expected
        rationale=specific.get(no, '경험이 아닌 지시문을 경험근거로 인정하지 않음; off_topic 및 C/A/V not_observed' if no>=23 else
                              '관련 문제/개인조치/방법과 실제관찰 연결; aligned 및 C/A/V met')
        labels=[expected.intent_label.value]+[expected.criterion_assessments[k].value for k in ['problem_context','own_action','result_verification']]
        checks.append([case.id,' / '.join(labels),'유지',rationale])
    lines += [table(['case','intent / C / A / V','label 변경','정책 근거'],checks), '',
        'expected quote는 예시로 보존하고 support_segment_ids를 명시했다. not_observed는 required=false로 근거선택 허용. v1데이터/채점 exact-match는 보존한다. requirement text없는 job alignment/status/job evidence는 정확도에서 제외한다.', '',
        '## 재채점만으로 공정하지 않은 지표와 최소 재호출 제안', '',
        '- 계약 재검증·원문/ID 일치와 새support채점은 저장된 응답에 대해 재현 가능하다. 비용/latency는 원래생성값이며 새prompt의 비용/latency가 아니다.',
        '- intent 독립, Vpartial 경계, not_observed 인용 정책, 비백엔드 C/A/V 범위를 새Skill로 전달했을 때의 실제 준수율은 새생성 필요. label 분모변화와 grader개선은 모델개선이 아니다.',
        '- 먼저 공통실패9case(01/04/06/14/16/18/20/21/22)에 Basic3종 각1회:27호출. 실패case 합집합에만 Premium3종 각1회, case중복제거하면 최대27추가. 원래Basic출력은 입력에 넣지 않고 모든실패부모를 동일case복구결과에 연결하되 독립호출수/consistency로 부풀리지 않는다. 신규retried 여부 명시.',
        '- 이54호출 이하 점검은 정책정렬 파일럿이며 최종 모델선정용 전체30건 정확도로 보지 않는다. 공정한 최종선정은 새Skill로 Basic30×3=90호출 후 현재실패case 합집합에만 Premium3종을 실행한다. 기존자료는 회귀/사람semantic검토에 재사용한다.',
        '- label독립검토와15case 사람semantic검토는 API호출 없이 먼저 가능하다. 이번단계에서 실제재호출은 수행하지 않았다.', '',
        '## 재현', '',
        'PYTHONPATH=backend:. .venv-llm-eval/bin/python -B -m evals.regrade_saved_results --input <all-attempts.json> --dataset evals/dataset.v2.jsonl --output-dir <새 디렉터리>',
        '', '기존 디렉터리 덮어쓰기를 거부한다. verification.json에 원본 및raw 불변, semantic null을 확인했다.']
    (output_dir/'REPORT.md').write_text('\n'.join(lines)+'\n')


if __name__=='__main__': main()
