begin;
select plan(6);

select ok(
    (select prosecdef from pg_proc where oid = 'public.review_mofe_recruitment(bigint,text,text,text,jsonb)'::regprocedure),
    'mofe review RPC uses definer rights for the server-owned catalog write'
);
select ok(
    has_function_privilege(
        'authenticated',
        'public.review_mofe_recruitment(bigint,text,text,text,jsonb)',
        'execute'
    ),
    'permanent authenticated users can save their own mofe source'
);

insert into auth.users (id) values
    ('50000000-0000-4000-8000-000000000003'),
    ('50000000-0000-4000-8000-000000000004');

set local role authenticated;
select set_config(
    'request.jwt.claims',
    '{"sub":"50000000-0000-4000-8000-000000000003","is_anonymous":false}',
    true
);

select lives_ok(
    $$select public.review_mofe_recruitment(
        993001,
        '테스트 공공기관',
        '테스트 백엔드 개발 공고',
        'https://www.data.go.kr/data/15125273/openapi.do',
        '[{"text":"API 오류 분석 경험","source_excerpt":"지원자격: API 오류 원인을 분석하고 개선한 경험"}]'::jsonb
    )$$,
    'user saves an AI-analyzed mofe requirement with source evidence'
);
select set_config(
    'test.mofe_job_id',
    (select id::text from public.job_postings where external_id = 'MOFE-993001-50000000-0000-4000-8000-000000000003'),
    true
);
select set_config(
    'test.mofe_requirement_id',
    (select id::text from public.job_requirements where code = 'MOFE-993001-R1'),
    true
);
select lives_ok(
    $$select public.create_practice_session(
        current_setting('test.mofe_job_id')::uuid,
        array[current_setting('test.mofe_requirement_id')::uuid],
        'preset',
        'preset-04',
        null
    )$$,
    'owner starts a practice session with the selected mofe requirement'
);

select set_config(
    'request.jwt.claims',
    '{"sub":"50000000-0000-4000-8000-000000000004","is_anonymous":false}',
    true
);
select results_eq(
    $$select count(*)::bigint from public.job_postings where external_id like 'MOFE-993001-%'$$,
    array[0::bigint],
    'another user cannot read the owner-specific mofe job'
);
select throws_ok(
    $$select public.create_practice_session(
        current_setting('test.mofe_job_id')::uuid,
        array[current_setting('test.mofe_requirement_id')::uuid],
        'preset',
        'preset-04',
        null
    )$$,
    '22023',
    null,
    'another user cannot start a session from the owner-specific mofe job'
);

select * from finish();
rollback;
