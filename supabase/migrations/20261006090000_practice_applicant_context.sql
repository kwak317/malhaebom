alter table public.practice_sessions add column applicant_context jsonb;

create or replace function public.create_practice_session_with_applicant_context(
    p_job_posting_id uuid,
    p_requirement_ids uuid[],
    p_question_type text,
    p_question_id text,
    p_custom_question_text text,
    p_applicant_context jsonb
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

    if p_applicant_context is null or jsonb_typeof(p_applicant_context) <> 'object'
       or octet_length(p_applicant_context::text) > 131072 then
        raise exception 'invalid applicant context' using errcode = '22023';
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
        custom_question_text,
        applicant_context
    ) values (
        (select auth.uid()),
        p_job_posting_id,
        p_question_type,
        p_question_id,
        case when p_custom_question_text is null then null else btrim(p_custom_question_text) end,
        p_applicant_context
    )
    returning id into created_session_id;

    insert into public.practice_session_requirements (practice_session_id, requirement_id)
    select created_session_id, requirement_id
    from unnest(p_requirement_ids) as requirement_id;

    return created_session_id;
end;
$$;

revoke all on function public.create_practice_session_with_applicant_context(uuid, uuid[], text, text, text, jsonb) from public, anon;
grant execute on function public.create_practice_session_with_applicant_context(uuid, uuid[], text, text, text, jsonb) to authenticated;
