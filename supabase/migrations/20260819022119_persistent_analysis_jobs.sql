create table public.analysis_jobs (
    id uuid primary key,
    user_id uuid not null references auth.users (id) on delete cascade,
    source_id text not null,
    practice_session_id uuid not null,
    question_type text not null,
    question_id text,
    custom_question_text text,
    attempt_no smallint not null,
    audio_path text not null,
    audio_content_type text,
    status text not null,
    result jsonb,
    delivery jsonb,
    error jsonb,
    created_at timestamptz not null default now(),
    completed_at timestamptz,
    expires_at timestamptz not null default (now() + interval '24 hours'),
    cleanup_attempted_at timestamptz,
    cleanup_error_code text,
    constraint analysis_jobs_question_type_check check (question_type in ('preset', 'custom')),
    constraint analysis_jobs_attempt_no_check check (attempt_no in (1, 2)),
    constraint analysis_jobs_question_check check (
        (question_type = 'preset' and question_id is not null and custom_question_text is null)
        or
        (question_type = 'custom' and question_id is null and length(btrim(custom_question_text)) between 1 and 200)
    ),
    constraint analysis_jobs_status_check check (status in ('queued', 'processing', 'completed', 'failed')),
    constraint analysis_jobs_user_session_attempt_key unique (user_id, practice_session_id, attempt_no)
);

insert into storage.buckets (id, name, public)
values ('analysis-audio', 'analysis-audio', false)
on conflict (id) do nothing;

revoke all on table public.analysis_jobs from anon, authenticated;
grant select, insert, update, delete on table public.analysis_jobs to authenticated;

alter table public.analysis_jobs enable row level security;

create policy "analysis_jobs_select_own"
on public.analysis_jobs for select to authenticated
using ((select auth.uid()) = user_id);

create policy "analysis_jobs_insert_own"
on public.analysis_jobs for insert to authenticated
with check ((select auth.uid()) = user_id);

create policy "analysis_jobs_update_own"
on public.analysis_jobs for update to authenticated
using ((select auth.uid()) = user_id)
with check ((select auth.uid()) = user_id);

create policy "analysis_jobs_delete_own"
on public.analysis_jobs for delete to authenticated
using ((select auth.uid()) = user_id);

create policy "analysis_audio_insert_own"
on storage.objects for insert to authenticated
with check (
    bucket_id = 'analysis-audio'
    and (storage.foldername(name))[1] = (select auth.uid()::text)
);

create policy "analysis_audio_select_own"
on storage.objects for select to authenticated
using (
    bucket_id = 'analysis-audio'
    and (storage.foldername(name))[1] = (select auth.uid()::text)
);

create policy "analysis_audio_delete_own"
on storage.objects for delete to authenticated
using (
    bucket_id = 'analysis-audio'
    and (storage.foldername(name))[1] = (select auth.uid()::text)
);

-- Hosted-project verification after `supabase db push`:
-- 1. Confirm public.analysis_jobs has RLS enabled.
-- 2. With two distinct authenticated JWTs, verify each can only read and delete
--    their own analysis_jobs row and analysis-audio/<their-auth-uid>/... object.
