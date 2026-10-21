alter policy "authenticated_read_reviewed_job_postings"
on public.job_postings
using (
    (((select auth.jwt()) ->> 'is_anonymous')::boolean is false)
    and review_status = 'reviewed'
    and is_active
);

alter policy "authenticated_read_reviewed_job_requirements"
on public.job_requirements
using (
    (((select auth.jwt()) ->> 'is_anonymous')::boolean is false)
    and exists (
        select 1
        from public.job_postings
        where job_postings.id = job_requirements.job_posting_id
          and job_postings.review_status = 'reviewed'
          and job_postings.is_active
    )
);

alter policy "users_read_active_own_practice_sessions"
on public.practice_sessions
using (
    (((select auth.jwt()) ->> 'is_anonymous')::boolean is false)
    and (select auth.uid()) = user_id
    and expires_at > now()
);

alter policy "users_insert_own_practice_sessions"
on public.practice_sessions
with check (
    (((select auth.jwt()) ->> 'is_anonymous')::boolean is false)
    and (select auth.uid()) = user_id
    and exists (
        select 1
        from public.job_postings
        where job_postings.id = practice_sessions.job_posting_id
          and job_postings.review_status = 'reviewed'
          and job_postings.is_active
    )
);

alter policy "users_delete_own_practice_sessions"
on public.practice_sessions
using (
    (((select auth.jwt()) ->> 'is_anonymous')::boolean is false)
    and (select auth.uid()) = user_id
);

alter policy "users_read_own_practice_session_requirements"
on public.practice_session_requirements
using (
    (((select auth.jwt()) ->> 'is_anonymous')::boolean is false)
    and exists (
        select 1
        from public.practice_sessions
        where practice_sessions.id = practice_session_requirements.practice_session_id
          and practice_sessions.user_id = (select auth.uid())
          and practice_sessions.expires_at > now()
    )
);

alter policy "users_insert_own_practice_session_requirements"
on public.practice_session_requirements
with check (
    (((select auth.jwt()) ->> 'is_anonymous')::boolean is false)
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

alter policy "users_delete_own_practice_session_requirements"
on public.practice_session_requirements
using (
    (((select auth.jwt()) ->> 'is_anonymous')::boolean is false)
    and exists (
        select 1
        from public.practice_sessions
        where practice_sessions.id = practice_session_requirements.practice_session_id
          and practice_sessions.user_id = (select auth.uid())
    )
);
