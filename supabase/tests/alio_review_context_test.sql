begin;
select plan(11);

select ok(
    (select prosecdef from pg_proc where oid = 'public.review_alio_recruitment(bigint,text,text,text,jsonb)'::regprocedure),
    'ALIO review RPC uses definer rights for the server-owned catalog write'
);
select ok(
    has_function_privilege(
        'authenticated',
        'public.review_alio_recruitment(bigint,text,text,text,jsonb)',
        'execute'
    ),
    'permanent authenticated users can review their own ALIO source'
);
select ok(
    not has_function_privilege(
        'anon',
        'public.review_alio_recruitment(bigint,text,text,text,jsonb)',
        'execute'
    ),
    'signed-out users cannot use the ALIO review RPC'
);

insert into auth.users (id) values
    ('40000000-0000-4000-8000-000000000001'),
    ('40000000-0000-4000-8000-000000000002');

set local role authenticated;
select set_config(
    'request.jwt.claims',
    '{"sub":"40000000-0000-4000-8000-000000000001","is_anonymous":false}',
    true
);

select lives_ok(
    $$select public.review_alio_recruitment(
        991001,
        '테스트 공사',
        '테스트 백엔드 개발자 공고',
        'https://recruit.example.org/jobs/991001',
        '[{"text":"API 오류 분석 경험","source_excerpt":"지원자격: API 오류 원인을 분석하고 개선한 경험"}]'::jsonb
    )$$,
    'reviewer saves a source-confirmed ALIO requirement'
);

select results_eq(
    $$select count(*)::bigint
      from public.job_postings
     where external_id = 'ALIO-991001-40000000-0000-4000-8000-000000000001'
       and reviewed_by_user_id = '40000000-0000-4000-8000-000000000001'$$,
    array[1::bigint],
    'reviewed ALIO job is owned by the reviewer'
);
select is(
    (
        select source_excerpt
        from public.job_requirements
        where code = 'ALIO-991001-R1'
    ),
    '지원자격: API 오류 원인을 분석하고 개선한 경험',
    'requirement keeps the source excerpt entered by the reviewer'
);

select set_config(
    'test.alio_job_id',
    (select id::text from public.job_postings where external_id = 'ALIO-991001-40000000-0000-4000-8000-000000000001'),
    true
);
select set_config(
    'test.alio_requirement_id',
    (select id::text from public.job_requirements where code = 'ALIO-991001-R1'),
    true
);

select lives_ok(
    $$select public.create_practice_session(
        current_setting('test.alio_job_id')::uuid,
        array[current_setting('test.alio_requirement_id')::uuid],
        'preset',
        'preset-04',
        null
    )$$,
    'reviewer starts a first-answer practice session from the reviewed requirement'
);

select set_config(
    'request.jwt.claims',
    '{"sub":"40000000-0000-4000-8000-000000000002","is_anonymous":false}',
    true
);
select results_eq(
    $$select count(*)::bigint
      from public.job_postings
     where data_origin = 'alio' and external_id like 'ALIO-991001-%'$$,
    array[0::bigint],
    'another user cannot read the reviewer-owned ALIO job'
);
select throws_ok(
    $$select public.create_practice_session(
        current_setting('test.alio_job_id')::uuid,
        array[current_setting('test.alio_requirement_id')::uuid],
        'preset',
        'preset-04',
        null
    )$$,
    '22023',
    null,
    'another user cannot create a session from the reviewer-owned ALIO job'
);

select throws_ok(
    $$select public.review_alio_recruitment(
        991003,
        '테스트 공사',
        '테스트 공고',
        'ftp://recruit.example.org/jobs/991003',
        '[{"text":"API 오류 분석 경험","source_excerpt":"지원자격: API 오류 원인을 분석하고 개선한 경험"}]'::jsonb
    )$$,
    '22023',
    null,
    'review source URL must use HTTP or HTTPS'
);

select set_config(
    'request.jwt.claims',
    '{"sub":"40000000-0000-4000-8000-000000000002","is_anonymous":true}',
    true
);
select throws_ok(
    $$select public.review_alio_recruitment(
        991002,
        '테스트 공사',
        '테스트 공고',
        'https://www.alio.go.kr/recruitment/991002',
        '[{"text":"API 오류 분석 경험","source_excerpt":"지원자격: API 오류 원인을 분석하고 개선한 경험"}]'::jsonb
    )$$,
    '42501',
    null,
    'anonymous authenticated users cannot save ALIO reviews'
);

select * from finish();
rollback;
