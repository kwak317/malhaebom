create table public.job_postings (
    id uuid primary key default gen_random_uuid(),
    external_id text not null unique,
    company text not null,
    title text not null,
    source_url text not null,
    captured_at timestamptz not null,
    reviewed_at timestamptz not null,
    review_status text not null,
    data_origin text not null default 'reviewed',
    is_active boolean not null default true,
    created_at timestamptz not null default now(),
    constraint job_postings_review_status_check
        check (review_status in ('draft', 'reviewed', 'rejected')),
    constraint job_postings_data_origin_check
        check (data_origin in ('reviewed', 'demo'))
);

create table public.job_requirements (
    id uuid primary key default gen_random_uuid(),
    job_posting_id uuid not null references public.job_postings (id) on delete cascade,
    code text not null,
    requirement_text text not null,
    display_order smallint not null,
    created_at timestamptz not null default now(),
    constraint job_requirements_job_code_key unique (job_posting_id, code),
    constraint job_requirements_display_order_check check (display_order > 0)
);

create index job_requirements_job_posting_id_idx
on public.job_requirements (job_posting_id, display_order);

create table public.practice_sessions (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users (id) on delete cascade,
    job_posting_id uuid not null references public.job_postings (id),
    question_type text not null,
    question_id text,
    custom_question_text text,
    created_at timestamptz not null default now(),
    expires_at timestamptz not null default (now() + interval '24 hours'),
    constraint practice_sessions_question_type_check
        check (question_type in ('preset', 'custom')),
    constraint practice_sessions_question_check check (
        (
            question_type = 'preset'
            and question_id is not null
            and question_id ~ '^preset-[0-9]{2}$'
            and custom_question_text is null
        )
        or
        (
            question_type = 'custom'
            and question_id is null
            and custom_question_text is not null
            and length(btrim(custom_question_text)) between 1 and 200
        )
    )
);

create index practice_sessions_user_expires_at_idx
on public.practice_sessions (user_id, expires_at desc);

create index practice_sessions_job_posting_id_idx
on public.practice_sessions (job_posting_id);

create table public.practice_session_requirements (
    practice_session_id uuid not null references public.practice_sessions (id) on delete cascade,
    requirement_id uuid not null references public.job_requirements (id),
    created_at timestamptz not null default now(),
    primary key (practice_session_id, requirement_id)
);

create index practice_session_requirements_requirement_id_idx
on public.practice_session_requirements (requirement_id);

alter table public.job_postings enable row level security;
alter table public.job_requirements enable row level security;
alter table public.practice_sessions enable row level security;
alter table public.practice_session_requirements enable row level security;

revoke all on table public.job_postings from anon, authenticated;
revoke all on table public.job_requirements from anon, authenticated;
revoke all on table public.practice_sessions from anon, authenticated;
revoke all on table public.practice_session_requirements from anon, authenticated;

grant select on table public.job_postings to authenticated;
grant select on table public.job_requirements to authenticated;
grant select, insert, delete on table public.practice_sessions to authenticated;
grant select, insert, delete on table public.practice_session_requirements to authenticated;

create policy "authenticated_read_reviewed_job_postings"
on public.job_postings for select
to authenticated
using (review_status = 'reviewed' and is_active);

create policy "authenticated_read_reviewed_job_requirements"
on public.job_requirements for select
to authenticated
using (
    exists (
        select 1
        from public.job_postings
        where job_postings.id = job_requirements.job_posting_id
          and job_postings.review_status = 'reviewed'
          and job_postings.is_active
    )
);

create policy "users_read_active_own_practice_sessions"
on public.practice_sessions for select
to authenticated
using ((select auth.uid()) = user_id and expires_at > now());

create policy "users_insert_own_practice_sessions"
on public.practice_sessions for insert
to authenticated
with check (
    (select auth.uid()) = user_id
    and exists (
        select 1
        from public.job_postings
        where job_postings.id = practice_sessions.job_posting_id
          and job_postings.review_status = 'reviewed'
          and job_postings.is_active
    )
);

create policy "users_delete_own_practice_sessions"
on public.practice_sessions for delete
to authenticated
using ((select auth.uid()) = user_id);

create policy "users_read_own_practice_session_requirements"
on public.practice_session_requirements for select
to authenticated
using (
    exists (
        select 1
        from public.practice_sessions
        where practice_sessions.id = practice_session_requirements.practice_session_id
          and practice_sessions.user_id = (select auth.uid())
          and practice_sessions.expires_at > now()
    )
);

create policy "users_insert_own_practice_session_requirements"
on public.practice_session_requirements for insert
to authenticated
with check (
    exists (
        select 1
        from public.practice_sessions
        join public.job_requirements
          on job_requirements.id = practice_session_requirements.requirement_id
         and job_requirements.job_posting_id = practice_sessions.job_posting_id
        where practice_sessions.id = practice_session_requirements.practice_session_id
          and practice_sessions.user_id = (select auth.uid())
          and practice_sessions.expires_at > now()
    )
);

create policy "users_delete_own_practice_session_requirements"
on public.practice_session_requirements for delete
to authenticated
using (
    exists (
        select 1
        from public.practice_sessions
        where practice_sessions.id = practice_session_requirements.practice_session_id
          and practice_sessions.user_id = (select auth.uid())
    )
);

create or replace function public.create_practice_session(
    p_job_posting_id uuid,
    p_requirement_ids uuid[],
    p_question_type text,
    p_question_id text,
    p_custom_question_text text
)
returns uuid
language plpgsql
security invoker
set search_path = ''
as $$
declare
    selected_count integer;
    created_session_id uuid;
begin
    if (select auth.uid()) is null then
        raise exception 'authentication required' using errcode = '42501';
    end if;

    selected_count := coalesce(array_length(p_requirement_ids, 1), 0);
    if selected_count not between 1 and 2
       or selected_count <> (
           select count(distinct requirement_id)
           from unnest(p_requirement_ids) as requirement_id
       ) then
        raise exception 'select one or two distinct requirements' using errcode = '22023';
    end if;

    if not exists (
        select 1
        from public.job_postings
        where id = p_job_posting_id
          and review_status = 'reviewed'
          and is_active
    ) then
        raise exception 'reviewed job posting not found' using errcode = '22023';
    end if;

    if selected_count <> (
        select count(*)
        from public.job_requirements
        where job_posting_id = p_job_posting_id
          and id = any(p_requirement_ids)
    ) then
        raise exception 'requirements must belong to the selected job posting' using errcode = '22023';
    end if;

    if not (
        (
            p_question_type = 'preset'
            and p_question_id is not null
            and p_question_id ~ '^preset-[0-9]{2}$'
            and p_custom_question_text is null
        )
        or
        (
            p_question_type = 'custom'
            and p_question_id is null
            and p_custom_question_text is not null
            and length(btrim(p_custom_question_text)) between 1 and 200
        )
    ) then
        raise exception 'invalid practice question' using errcode = '22023';
    end if;

    insert into public.practice_sessions (
        user_id,
        job_posting_id,
        question_type,
        question_id,
        custom_question_text
    ) values (
        (select auth.uid()),
        p_job_posting_id,
        p_question_type,
        p_question_id,
        case when p_custom_question_text is null then null else btrim(p_custom_question_text) end
    )
    returning id into created_session_id;

    insert into public.practice_session_requirements (practice_session_id, requirement_id)
    select created_session_id, requirement_id
    from unnest(p_requirement_ids) as requirement_id;

    return created_session_id;
end;
$$;

revoke all on function public.create_practice_session(uuid, uuid[], text, text, text)
from public, anon;
grant execute on function public.create_practice_session(uuid, uuid[], text, text, text)
to authenticated;

-- 실제 공고로 오인하지 않도록 제목·회사·출처에 가상 자료임을 명시한 개발용 카탈로그다.
insert into public.job_postings (
    external_id,
    company,
    title,
    source_url,
    captured_at,
    reviewed_at,
    review_status,
    data_origin,
    is_active
) values
    (
        'DEMO-JOB-01-r1',
        '말해봄 평가용 가상 회사',
        '연습용 신입 백엔드 개발자 공고 A',
        'https://example.invalid/demo-job-01',
        '2026-09-17T00:00:00Z',
        '2026-09-17T00:00:00Z',
        'reviewed',
        'demo',
        true
    ),
    (
        'DEMO-JOB-02-r1',
        '말해봄 평가용 가상 회사',
        '연습용 신입 백엔드 개발자 공고 B',
        'https://example.invalid/demo-job-02',
        '2026-09-17T00:00:00Z',
        '2026-09-17T00:00:00Z',
        'reviewed',
        'demo',
        true
    ),
    (
        'DEMO-JOB-03-r1',
        '말해봄 평가용 가상 회사',
        '연습용 신입 백엔드 개발자 공고 C',
        'https://example.invalid/demo-job-03',
        '2026-09-17T00:00:00Z',
        '2026-09-17T00:00:00Z',
        'reviewed',
        'demo',
        true
    )
on conflict (external_id) do nothing;

insert into public.job_requirements (
    job_posting_id,
    code,
    requirement_text,
    display_order
) select
    job_postings.id,
    seed.code,
    seed.requirement_text,
    seed.display_order
from (
    values
    (
        'DEMO-JOB-01-r1',
        'J01-R1',
        '백엔드 API 오류 분석 및 수정 경험',
        1
    ),
    (
        'DEMO-JOB-01-r1',
        'J01-R2',
        '수정 기능의 테스트 및 회귀 확인 경험',
        2
    ),
    (
        'DEMO-JOB-02-r1',
        'J02-R1',
        '조회 기능의 성능 분석 및 개선 경험',
        1
    ),
    (
        'DEMO-JOB-02-r1',
        'J02-R2',
        '변경 전후의 동작 및 성능 확인 경험',
        2
    ),
    (
        'DEMO-JOB-03-r1',
        'J03-R1',
        '배포 환경 또는 파일 처리 오류의 재현과 조치 경험',
        1
    )
) as seed(external_id, code, requirement_text, display_order)
join public.job_postings
  on job_postings.external_id = seed.external_id
on conflict (job_posting_id, code) do nothing;
