begin;

create extension if not exists pgtap with schema extensions;

select plan(4);

select ok(
    not exists (
        select 1
        from pg_constraint
        where conrelid = 'public.analysis_jobs'::regclass
          and conname = 'analysis_jobs_user_session_attempt_key'
    ),
    'the unconditional attempt uniqueness constraint is removed'
);

select ok(
    exists (
        select 1
        from pg_index
        where indexrelid = 'public.analysis_jobs_user_session_attempt_active_key'::regclass
          and indpred is not null
    ),
    'active attempts use a partial unique index'
);

insert into auth.users (id)
values ('40000000-0000-4000-8000-000000000001');

insert into public.analysis_jobs (
    id,
    user_id,
    source_id,
    practice_session_id,
    question_type,
    question_id,
    attempt_no,
    audio_path,
    status
)
values (
    '41000000-0000-4000-8000-000000000001',
    '40000000-0000-4000-8000-000000000001',
    'failed-source',
    '42000000-0000-4000-8000-000000000001',
    'preset',
    'preset-04',
    1,
    '40000000-0000-4000-8000-000000000001/failed/original.wav',
    'failed'
);

select lives_ok(
    $$insert into public.analysis_jobs (
        id,
        user_id,
        source_id,
        practice_session_id,
        question_type,
        question_id,
        attempt_no,
        audio_path,
        status
    ) values (
        '41000000-0000-4000-8000-000000000002',
        '40000000-0000-4000-8000-000000000001',
        'retry-source',
        '42000000-0000-4000-8000-000000000001',
        'preset',
        'preset-04',
        1,
        '40000000-0000-4000-8000-000000000001/retry/original.wav',
        'queued'
    )$$,
    'a failed attempt can be recorded again with the same attempt number'
);

select throws_ok(
    $$insert into public.analysis_jobs (
        id,
        user_id,
        source_id,
        practice_session_id,
        question_type,
        question_id,
        attempt_no,
        audio_path,
        status
    ) values (
        '41000000-0000-4000-8000-000000000003',
        '40000000-0000-4000-8000-000000000001',
        'duplicate-source',
        '42000000-0000-4000-8000-000000000001',
        'preset',
        'preset-04',
        1,
        '40000000-0000-4000-8000-000000000001/duplicate/original.wav',
        'processing'
    )$$,
    '23505',
    null,
    'two active jobs cannot occupy the same practice attempt'
);

select * from finish();
rollback;
