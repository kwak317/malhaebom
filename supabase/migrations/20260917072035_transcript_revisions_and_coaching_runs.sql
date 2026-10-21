create table public.answer_revisions (
    id uuid primary key default gen_random_uuid(),
    analysis_job_id uuid not null references public.analysis_jobs (id) on delete cascade,
    user_id uuid not null references auth.users (id) on delete cascade,
    practice_session_id uuid not null,
    revision_no smallint not null,
    question_id text not null,
    confirmed_text text not null,
    answer_segments jsonb not null,
    delivery_metrics jsonb not null default '{}'::jsonb,
    confirmed_at timestamptz not null default now(),
    expires_at timestamptz not null,
    constraint answer_revisions_job_revision_key unique (analysis_job_id, revision_no),
    constraint answer_revisions_revision_no_check check (revision_no > 0),
    constraint answer_revisions_text_check
        check (length(btrim(confirmed_text)) between 1 and 5000),
    constraint answer_revisions_segments_check
        check (jsonb_typeof(answer_segments) = 'array' and jsonb_array_length(answer_segments) > 0)
);

create index answer_revisions_user_expires_at_idx
on public.answer_revisions (user_id, expires_at desc);

create index answer_revisions_practice_session_id_idx
on public.answer_revisions (practice_session_id, confirmed_at desc);

create table public.coaching_runs (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users (id) on delete cascade,
    answer_revision_id uuid not null references public.answer_revisions (id) on delete cascade,
    job_snapshot_id uuid not null,
    status text not null,
    response jsonb not null,
    model_name text not null,
    prompt_version text not null,
    skill_version text not null,
    created_at timestamptz not null default now(),
    expires_at timestamptz not null,
    constraint coaching_runs_status_check
        check (status in ('ok', 'needs_more_info', 'unsupported', 'unavailable'))
);

create index coaching_runs_user_created_at_idx
on public.coaching_runs (user_id, created_at desc);

create index coaching_runs_answer_revision_id_idx
on public.coaching_runs (answer_revision_id, created_at desc);

alter table public.answer_revisions enable row level security;
alter table public.coaching_runs enable row level security;

revoke all on table public.answer_revisions from anon, authenticated;
revoke all on table public.coaching_runs from anon, authenticated;

grant select on table public.answer_revisions to authenticated;
grant select on table public.coaching_runs to authenticated;

create policy "users_read_active_own_answer_revisions"
on public.answer_revisions for select
to authenticated
using (
    (((select auth.jwt()) ->> 'is_anonymous')::boolean is false)
    and (select auth.uid()) = user_id
    and expires_at > now()
);

create policy "users_read_active_own_coaching_runs"
on public.coaching_runs for select
to authenticated
using (
    (((select auth.jwt()) ->> 'is_anonymous')::boolean is false)
    and (select auth.uid()) = user_id
    and expires_at > now()
);

create or replace function public.create_answer_revision(
    p_analysis_job_id uuid,
    p_confirmed_text text,
    p_answer_segments jsonb
)
returns uuid
language plpgsql
security definer
set search_path = ''
as $$
declare
    source_job public.analysis_jobs%rowtype;
    next_revision_no smallint;
    created_revision_id uuid;
    resolved_question_id text;
begin
    if (select auth.uid()) is null
       or (select ((auth.jwt()) ->> 'is_anonymous')::boolean) is not false then
        raise exception 'permanent authentication required' using errcode = '42501';
    end if;

    if length(btrim(p_confirmed_text)) not between 1 and 5000
       or jsonb_typeof(p_answer_segments) <> 'array'
       or jsonb_array_length(p_answer_segments) = 0 then
        raise exception 'invalid confirmed transcript' using errcode = '22023';
    end if;

    select *
    into source_job
    from public.analysis_jobs
    where id = p_analysis_job_id
      and user_id = (select auth.uid())
      and status = 'completed'
      and expires_at > now()
    for update;

    if not found then
        raise exception 'completed analysis job not found' using errcode = '22023';
    end if;

    if source_job.question_type = 'preset' then
        resolved_question_id := source_job.question_id;
    else
        resolved_question_id := 'custom-' || substr(md5(source_job.custom_question_text), 1, 12);
    end if;

    select (coalesce(max(revision_no), 0) + 1)::smallint
    into next_revision_no
    from public.answer_revisions
    where analysis_job_id = p_analysis_job_id;

    insert into public.answer_revisions (
        analysis_job_id,
        user_id,
        practice_session_id,
        revision_no,
        question_id,
        confirmed_text,
        answer_segments,
        delivery_metrics,
        expires_at
    ) values (
        source_job.id,
        (select auth.uid()),
        source_job.practice_session_id,
        next_revision_no,
        resolved_question_id,
        btrim(p_confirmed_text),
        p_answer_segments,
        jsonb_strip_nulls(jsonb_build_object(
            'answer_duration_sec', source_job.delivery #> '{metrics,answer_duration_sec}',
            'speech_duration_sec', source_job.delivery #> '{metrics,speech_duration_sec}',
            'cpm', source_job.delivery #> '{metrics,cpm}',
            'long_silence_count', case
                when jsonb_typeof(source_job.delivery #> '{metrics,long_silences}') = 'array'
                then jsonb_array_length(source_job.delivery #> '{metrics,long_silences}')
                else 0
            end,
            'repetition_count', case
                when jsonb_typeof(source_job.delivery #> '{metrics,repetitions}') = 'array'
                then jsonb_array_length(source_job.delivery #> '{metrics,repetitions}')
                else 0
            end,
            'soft_ending_count', case
                when jsonb_typeof(source_job.delivery #> '{metrics,soft_endings}') = 'array'
                then jsonb_array_length(source_job.delivery #> '{metrics,soft_endings}')
                else 0
            end
        )),
        source_job.expires_at
    )
    returning id into created_revision_id;

    return created_revision_id;
end;
$$;

revoke all on function public.create_answer_revision(uuid, text, jsonb)
from public, anon;
grant execute on function public.create_answer_revision(uuid, text, jsonb)
to authenticated;
