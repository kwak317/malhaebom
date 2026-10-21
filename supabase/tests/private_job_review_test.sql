begin;
select plan(8);

select ok(
    not (select prosecdef from pg_proc where oid = 'public.review_private_job_recruitment(uuid,text,text,text,text,text,jsonb)'::regprocedure),
    'private job review RPC uses invoker privileges'
);
select ok(
    has_function_privilege('service_role', 'public.review_private_job_recruitment(uuid,text,text,text,text,text,jsonb)', 'execute'),
    'backend service role can save a verified private job'
);
select ok(
    not has_function_privilege('authenticated', 'public.review_private_job_recruitment(uuid,text,text,text,text,text,jsonb)', 'execute'),
    'browser JWT cannot mark an unverified private job as reviewed'
);

insert into auth.users (id) values
    ('50000000-0000-4000-8000-000000000013'),
    ('50000000-0000-4000-8000-000000000014');

set local role service_role;
select lives_ok(
    $$select public.review_private_job_recruitment(
        '50000000-0000-4000-8000-000000000013',
        'saramin', '993001', '테스트 기업', '신입 백엔드 개발자',
        'https://www.saramin.co.kr/zf_user/jobs/view?rec_idx=993001',
        '[{"text":"REST API 서버 개발","source_excerpt":"REST API 서버 개발"}]'::jsonb
    )$$,
    'backend saves a reviewed posting with source-grounded requirements'
);
select set_config(
    'test.private_job_id',
    (select id::text from public.job_postings where external_id = 'PRIVATE-SARAMIN-993001-50000000-0000-4000-8000-000000000013'),
    true
);
select set_config(
    'test.private_requirement_id',
    (select id::text from public.job_requirements where code = 'PRIVATE-SARAMIN-993001-R1'),
    true
);

reset role;
set local role authenticated;
select set_config(
    'request.jwt.claims',
    '{"sub":"50000000-0000-4000-8000-000000000013","is_anonymous":false}',
    true
);
select results_eq(
    $$select count(*)::bigint from public.job_postings where external_id like 'PRIVATE-SARAMIN-993001-%'$$,
    array[1::bigint],
    'owner can read the reviewed private job'
);
select lives_ok(
    $$select public.create_practice_session(
        current_setting('test.private_job_id')::uuid,
        array[current_setting('test.private_requirement_id')::uuid],
        'preset', 'preset-04', null
    )$$,
    'owner can start the existing practice flow'
);

select set_config(
    'request.jwt.claims',
    '{"sub":"50000000-0000-4000-8000-000000000014","is_anonymous":false}',
    true
);
select results_eq(
    $$select count(*)::bigint from public.job_postings where external_id like 'PRIVATE-SARAMIN-993001-%'$$,
    array[0::bigint],
    'another user cannot read the selected private job'
);
select throws_ok(
    $$select public.create_practice_session(
        current_setting('test.private_job_id')::uuid,
        array[current_setting('test.private_requirement_id')::uuid],
        'preset', 'preset-04', null
    )$$,
    '22023', null,
    'another user cannot start a session from the private job'
);

select * from finish();
rollback;
