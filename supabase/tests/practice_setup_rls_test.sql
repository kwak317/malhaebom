begin;
select plan(19);

select ok(
    (select relrowsecurity from pg_class where oid = 'public.job_postings'::regclass),
    'job_postings has RLS enabled'
);
select ok(
    (select relrowsecurity from pg_class where oid = 'public.job_requirements'::regclass),
    'job_requirements has RLS enabled'
);
select ok(
    (select relrowsecurity from pg_class where oid = 'public.practice_sessions'::regclass),
    'practice_sessions has RLS enabled'
);
select ok(
    (select relrowsecurity from pg_class where oid = 'public.practice_session_requirements'::regclass),
    'practice_session_requirements has RLS enabled'
);

select ok(
    not has_table_privilege('anon', 'public.job_postings', 'select'),
    'signed-out users cannot read the reviewed job catalog'
);
select ok(
    has_table_privilege('authenticated', 'public.job_postings', 'select'),
    'signed-in users can read the reviewed job catalog'
);
select ok(
    not has_table_privilege('authenticated', 'public.job_postings', 'insert,update,delete'),
    'signed-in users cannot modify the server-owned job catalog'
);
select ok(
    has_table_privilege('authenticated', 'public.practice_sessions', 'select,insert,delete')
    and not has_table_privilege('authenticated', 'public.practice_sessions', 'update'),
    'signed-in users only receive the required practice session grants'
);
select ok(
    not (select prosecdef from pg_proc where oid = 'public.create_practice_session(uuid,uuid[],text,text,text)'::regprocedure),
    'practice session RPC uses invoker rights'
);

insert into auth.users (id) values
    ('30000000-0000-4000-8000-000000000001'),
    ('30000000-0000-4000-8000-000000000002');

set local role authenticated;
select set_config(
    'request.jwt.claims',
    '{"sub":"30000000-0000-4000-8000-000000000001","is_anonymous":false}',
    true
);

select results_eq(
    $$select count(*)::bigint from public.job_postings$$,
    array[3::bigint],
    'authenticated users see only the three active reviewed demo jobs'
);

select lives_ok(
    $$select public.create_practice_session(
        (select id from public.job_postings where external_id = 'DEMO-JOB-01-r1'),
        array[
            (select id from public.job_requirements where code = 'J01-R1'),
            (select id from public.job_requirements where code = 'J01-R2')
        ],
        'preset',
        'preset-04',
        null
    )$$,
    'owner creates an atomic session with one or two matching requirements'
);

select results_eq(
    $$select count(*)::bigint from public.practice_sessions$$,
    array[1::bigint],
    'owner reads the active session'
);

select set_config(
    'request.jwt.claims',
    '{"sub":"30000000-0000-4000-8000-000000000002","is_anonymous":false}',
    true
);
select results_eq(
    $$select count(*)::bigint from public.practice_sessions$$,
    array[0::bigint],
    'another user cannot read the owner session'
);

select throws_ok(
    $$select public.create_practice_session(
        (select id from public.job_postings where external_id = 'DEMO-JOB-01-r1'),
        array[(select id from public.job_requirements where code = 'J02-R1')],
        'preset',
        'preset-04',
        null
    )$$,
    '22023',
    null,
    'a requirement from another job is rejected'
);

select throws_ok(
    $$select public.create_practice_session(
        (select id from public.job_postings where external_id = 'DEMO-JOB-01-r1'),
        array[
            (select id from public.job_requirements where code = 'J01-R1'),
            (select id from public.job_requirements where code = 'J01-R2'),
            (select id from public.job_requirements where code = 'J02-R1')
        ],
        'preset',
        'preset-04',
        null
    )$$,
    '22023',
    null,
    'more than two requirements are rejected'
);

select throws_ok(
    $$select public.create_practice_session(
        (select id from public.job_postings where external_id = 'DEMO-JOB-01-r1'),
        array[(select id from public.job_requirements where code = 'J01-R1')],
        'preset',
        null,
        null
    )$$,
    '22023',
    null,
    'a preset session without a preset question id is rejected'
);

select throws_ok(
    $$select public.create_practice_session(
        (select id from public.job_postings where external_id = 'DEMO-JOB-01-r1'),
        array[(select id from public.job_requirements where code = 'J01-R1')],
        'custom',
        null,
        null
    )$$,
    '22023',
    null,
    'a custom session without question text is rejected'
);

select set_config(
    'request.jwt.claims',
    '{"sub":"30000000-0000-4000-8000-000000000002","is_anonymous":true}',
    true
);
select results_eq(
    $$select count(*)::bigint from public.job_postings$$,
    array[0::bigint],
    'anonymous authenticated users cannot read the reviewed job catalog'
);

select throws_ok(
    $$select public.create_practice_session(
        null,
        array[]::uuid[],
        'preset',
        'preset-04',
        null
    )$$,
    '42501',
    null,
    'anonymous authenticated users cannot create practice sessions'
);

select * from finish();
rollback;
