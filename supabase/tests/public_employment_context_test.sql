begin;
select plan(6);

select ok(
    (select prosecdef from pg_proc where oid = 'public.review_public_employment_recruitment(bigint,text,text,text,jsonb)'::regprocedure),
    'public employment review RPC uses definer rights for the server-owned catalog write'
);
select ok(
    has_function_privilege(
        'authenticated',
        'public.review_public_employment_recruitment(bigint,text,text,text,jsonb)',
        'execute'
    ),
    'permanent authenticated users can save their own public employment source'
);

insert into auth.users (id) values
    ('50000000-0000-4000-8000-000000000001'),
    ('50000000-0000-4000-8000-000000000002');

set local role authenticated;
select set_config(
    'request.jwt.claims',
    '{"sub":"50000000-0000-4000-8000-000000000001","is_anonymous":false}',
    true
);

select lives_ok(
    $$select public.review_public_employment_recruitment(
        992001,
        '테스트 기관',
        '테스트 개발자 공고',
        'https://recruit.example.org/jobs/992001',
        '[{"text":"API 오류 분석 경험","source_excerpt":"업무내용: API 오류 원인을 분석하고 개선한 경험"}]'::jsonb
    )$$,
    'user saves an AI-analyzed public employment requirement with source evidence'
);
select set_config(
    'test.public_job_id',
    (select id::text from public.job_postings where external_id = 'MPO-992001-50000000-0000-4000-8000-000000000001'),
    true
);
select set_config(
    'test.public_requirement_id',
    (select id::text from public.job_requirements where code = 'MPO-992001-R1'),
    true
);
select lives_ok(
    $$select public.create_practice_session(
        current_setting('test.public_job_id')::uuid,
        array[current_setting('test.public_requirement_id')::uuid],
        'preset',
        'preset-04',
        null
    )$$,
    'owner starts a practice session with the selected public employment requirement'
);

select set_config(
    'request.jwt.claims',
    '{"sub":"50000000-0000-4000-8000-000000000002","is_anonymous":false}',
    true
);
select results_eq(
    $$select count(*)::bigint from public.job_postings where external_id like 'MPO-992001-%'$$,
    array[0::bigint],
    'another user cannot read the owner-specific public employment job'
);
select throws_ok(
    $$select public.create_practice_session(
        current_setting('test.public_job_id')::uuid,
        array[current_setting('test.public_requirement_id')::uuid],
        'preset',
        'preset-04',
        null
    )$$,
    '22023',
    null,
    'another user cannot start a session from the owner-specific public employment job'
);

select * from finish();
rollback;
