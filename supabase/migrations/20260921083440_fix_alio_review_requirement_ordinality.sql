create or replace function public.review_alio_recruitment(
    p_announcement_id bigint,
    p_company text,
    p_title text,
    p_source_url text,
    p_requirements jsonb
)
returns uuid
language plpgsql
security definer
set search_path = ''
as $$
declare
    reviewer_id uuid;
    created_job_id uuid;
    external_job_id text;
    item record;
    requirement_text text;
    source_excerpt text;
begin
    reviewer_id := (select auth.uid());
    if reviewer_id is null
       or (select (auth.jwt() ->> 'is_anonymous')::boolean) is not false then
        raise exception 'permanent authentication required' using errcode = '42501';
    end if;

    if p_announcement_id <= 0
       or length(btrim(p_company)) not between 1 and 200
       or length(btrim(p_title)) not between 1 and 300
       or p_source_url !~* '^https?://[^/@[:space:]]+([/?#]|$)'
       or jsonb_typeof(p_requirements) <> 'array'
       or jsonb_array_length(p_requirements) not between 1 and 5 then
        raise exception 'invalid ALIO review input' using errcode = '22023';
    end if;

    for item in
        select value, ordinality
        from jsonb_array_elements(p_requirements) with ordinality
    loop
        requirement_text := btrim(item.value ->> 'text');
        source_excerpt := btrim(item.value ->> 'source_excerpt');
        if jsonb_typeof(item.value) <> 'object'
           or length(requirement_text) not between 2 and 300
           or length(source_excerpt) not between 2 and 500 then
            raise exception 'invalid ALIO requirement evidence' using errcode = '22023';
        end if;
    end loop;

    external_job_id := format('ALIO-%s-%s', p_announcement_id, reviewer_id);
    if exists (
        select 1
        from public.job_postings
        where external_id = external_job_id
    ) then
        raise exception 'ALIO recruitment already reviewed' using errcode = '23505';
    end if;

    insert into public.job_postings (
        external_id,
        company,
        title,
        source_url,
        captured_at,
        reviewed_at,
        review_status,
        data_origin,
        is_active,
        reviewed_by_user_id
    ) values (
        external_job_id,
        btrim(p_company),
        btrim(p_title),
        btrim(p_source_url),
        now(),
        now(),
        'reviewed',
        'alio',
        true,
        reviewer_id
    )
    returning id into created_job_id;

    insert into public.job_requirements (
        job_posting_id,
        code,
        requirement_text,
        source_excerpt,
        display_order
    )
    select
        created_job_id,
        format('ALIO-%s-R%s', p_announcement_id, requirement_item.ordinality),
        btrim(requirement_item.value ->> 'text'),
        btrim(requirement_item.value ->> 'source_excerpt'),
        requirement_item.ordinality
    from jsonb_array_elements(p_requirements) with ordinality as requirement_item(value, ordinality);

    return created_job_id;
end;
$$;
