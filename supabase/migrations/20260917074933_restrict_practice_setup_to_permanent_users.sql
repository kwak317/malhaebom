drop policy "authenticated_read_reviewed_job_postings"
on public.job_postings;

create policy "authenticated_read_reviewed_job_postings"
on public.job_postings for select
to authenticated
using (
    (select (auth.jwt() ->> 'is_anonymous')::boolean) is false
    and review_status = 'reviewed'
    and is_active
);

drop policy "authenticated_read_reviewed_job_requirements"
on public.job_requirements;

create policy "authenticated_read_reviewed_job_requirements"
on public.job_requirements for select
to authenticated
using (
    (select (auth.jwt() ->> 'is_anonymous')::boolean) is false
    and exists (
        select 1
        from public.job_postings
        where job_postings.id = job_requirements.job_posting_id
          and job_postings.review_status = 'reviewed'
          and job_postings.is_active
    )
);

drop policy "users_read_active_own_practice_sessions"
on public.practice_sessions;

create policy "users_read_active_own_practice_sessions"
on public.practice_sessions for select
to authenticated
using (
    (select (auth.jwt() ->> 'is_anonymous')::boolean) is false
    and (select auth.uid()) = user_id
    and expires_at > now()
);

drop policy "users_insert_own_practice_sessions"
on public.practice_sessions;

create policy "users_insert_own_practice_sessions"
on public.practice_sessions for insert
to authenticated
with check (
    (select (auth.jwt() ->> 'is_anonymous')::boolean) is false
    and (select auth.uid()) = user_id
    and exists (
        select 1
        from public.job_postings
        where job_postings.id = practice_sessions.job_posting_id
          and job_postings.review_status = 'reviewed'
          and job_postings.is_active
    )
);

drop policy "users_delete_own_practice_sessions"
on public.practice_sessions;

create policy "users_delete_own_practice_sessions"
on public.practice_sessions for delete
to authenticated
using (
    (select (auth.jwt() ->> 'is_anonymous')::boolean) is false
    and (select auth.uid()) = user_id
);

drop policy "users_read_own_practice_session_requirements"
on public.practice_session_requirements;

create policy "users_read_own_practice_session_requirements"
on public.practice_session_requirements for select
to authenticated
using (
    (select (auth.jwt() ->> 'is_anonymous')::boolean) is false
    and exists (
        select 1
        from public.practice_sessions
        where practice_sessions.id = practice_session_requirements.practice_session_id
          and practice_sessions.user_id = (select auth.uid())
          and practice_sessions.expires_at > now()
    )
);

drop policy "users_insert_own_practice_session_requirements"
on public.practice_session_requirements;

create policy "users_insert_own_practice_session_requirements"
on public.practice_session_requirements for insert
to authenticated
with check (
    (select (auth.jwt() ->> 'is_anonymous')::boolean) is false
    and exists (
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

drop policy "users_delete_own_practice_session_requirements"
on public.practice_session_requirements;

create policy "users_delete_own_practice_session_requirements"
on public.practice_session_requirements for delete
to authenticated
using (
    (select (auth.jwt() ->> 'is_anonymous')::boolean) is false
    and exists (
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
    if (select auth.uid()) is null
       or (select (auth.jwt() ->> 'is_anonymous')::boolean) is not false then
        raise exception 'permanent authentication required' using errcode = '42501';
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
