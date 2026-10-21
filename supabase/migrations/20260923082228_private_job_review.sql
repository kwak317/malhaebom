alter table public.job_postings
    drop constraint job_postings_data_origin_check;

alter table public.job_postings
    add constraint job_postings_data_origin_check
    check (data_origin in ('reviewed', 'demo', 'alio', 'public_job', 'mofe_job', 'private_job'));

drop policy "authenticated_read_reviewed_job_postings"
on public.job_postings;

create policy "authenticated_read_reviewed_job_postings"
on public.job_postings for select
to authenticated
using (
    ((select auth.jwt() ->> 'is_anonymous')::boolean is false)
    and review_status = 'reviewed'
    and is_active
    and (
        data_origin not in ('alio', 'public_job', 'mofe_job', 'private_job')
        or reviewed_by_user_id = (select auth.uid())
    )
);

drop policy "authenticated_read_reviewed_job_requirements"
on public.job_requirements;

create policy "authenticated_read_reviewed_job_requirements"
on public.job_requirements for select
to authenticated
using (
    ((select auth.jwt() ->> 'is_anonymous')::boolean is false)
    and exists (
        select 1
        from public.job_postings
        where job_postings.id = job_requirements.job_posting_id
          and job_postings.review_status = 'reviewed'
          and job_postings.is_active
          and (
              job_postings.data_origin not in ('alio', 'public_job', 'mofe_job', 'private_job')
              or job_postings.reviewed_by_user_id = (select auth.uid())
          )
    )
);

drop policy "users_insert_own_practice_sessions"
on public.practice_sessions;

create policy "users_insert_own_practice_sessions"
on public.practice_sessions for insert
to authenticated
with check (
    ((select auth.jwt() ->> 'is_anonymous')::boolean is false)
    and (select auth.uid()) = user_id
    and exists (
        select 1
        from public.job_postings
        where job_postings.id = practice_sessions.job_posting_id
          and job_postings.review_status = 'reviewed'
          and job_postings.is_active
          and (
              job_postings.data_origin not in ('alio', 'public_job', 'mofe_job', 'private_job')
              or reviewed_by_user_id = (select auth.uid())
          )
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
          and (
              data_origin not in ('alio', 'public_job', 'mofe_job', 'private_job')
              or reviewed_by_user_id = (select auth.uid())
          )
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

create function public.review_private_job_recruitment(
    p_reviewer_id uuid,
    p_source text,
    p_posting_id text,
    p_company text,
    p_title text,
    p_source_url text,
    p_requirements jsonb
)
returns uuid
language plpgsql
security invoker
set search_path = ''
as $$
declare
    created_job_id uuid;
    external_job_id text;
    expected_url text;
    item record;
    requirement_text text;
    source_excerpt text;
begin
    if p_reviewer_id is null
       or p_source is null or p_source not in ('saramin', 'jobkorea')
       or p_posting_id is null or p_posting_id !~ '^[0-9]{1,12}$'
       or p_company is null or length(btrim(p_company)) not between 1 and 200
       or p_title is null or length(btrim(p_title)) not between 1 and 300
       or p_source_url is null
       or p_requirements is null or jsonb_typeof(p_requirements) <> 'array'
       or jsonb_array_length(p_requirements) not between 1 and 5 then
        raise exception 'invalid private job review input' using errcode = '22023';
    end if;

    expected_url := case p_source
        when 'saramin' then format('https://www.saramin.co.kr/zf_user/jobs/view?rec_idx=%s', p_posting_id)
        else format('https://m.jobkorea.co.kr/Recruit/GI_Read/%s', p_posting_id)
    end;
    if p_source_url <> expected_url then
        raise exception 'invalid private job source URL' using errcode = '22023';
    end if;

    for item in
        select value from jsonb_array_elements(p_requirements)
    loop
        requirement_text := btrim(item.value ->> 'text');
        source_excerpt := btrim(item.value ->> 'source_excerpt');
        if jsonb_typeof(item.value) <> 'object'
           or requirement_text is null or length(requirement_text) not between 2 and 300
           or source_excerpt is null or length(source_excerpt) not between 2 and 500 then
            raise exception 'invalid private job requirement evidence' using errcode = '22023';
        end if;
    end loop;

    external_job_id := format('PRIVATE-%s-%s-%s', upper(p_source), p_posting_id, p_reviewer_id);
    insert into public.job_postings (
        external_id, company, title, source_url, captured_at, reviewed_at,
        review_status, data_origin, is_active, reviewed_by_user_id
    ) values (
        external_job_id, btrim(p_company), btrim(p_title), p_source_url, now(), now(),
        'reviewed', 'private_job', true, p_reviewer_id
    )
    on conflict (external_id) do nothing
    returning id into created_job_id;

    if created_job_id is null then
        select id into created_job_id
        from public.job_postings
        where external_id = external_job_id;
        return created_job_id;
    end if;

    insert into public.job_requirements (
        job_posting_id, code, requirement_text, source_excerpt, display_order
    )
    select
        created_job_id,
        format('PRIVATE-%s-%s-R%s', upper(p_source), p_posting_id, requirement.ordinality),
        btrim(requirement.value ->> 'text'),
        btrim(requirement.value ->> 'source_excerpt'),
        requirement.ordinality
    from jsonb_array_elements(p_requirements) with ordinality as requirement(value, ordinality);

    return created_job_id;
end;
$$;

revoke all on function public.review_private_job_recruitment(uuid, text, text, text, text, text, jsonb)
from public, anon, authenticated;
grant execute on function public.review_private_job_recruitment(uuid, text, text, text, text, text, jsonb)
to service_role;
