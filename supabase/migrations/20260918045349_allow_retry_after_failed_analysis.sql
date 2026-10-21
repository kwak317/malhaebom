alter table public.analysis_jobs
drop constraint if exists analysis_jobs_user_session_attempt_key;

create unique index analysis_jobs_user_session_attempt_active_key
on public.analysis_jobs (user_id, practice_session_id, attempt_no)
where status in ('queued', 'processing', 'completed');
