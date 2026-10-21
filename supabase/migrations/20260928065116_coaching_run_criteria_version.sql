-- 과거 run의 기준은 추정하지 않는다. 새 코칭은 서버 question의 실제 버전을 저장한다.
alter table public.coaching_runs
add column criteria_version text
constraint coaching_runs_criteria_version_check
check (criteria_version is null or length(btrim(criteria_version)) > 0);
