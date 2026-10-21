create index if not exists analysis_jobs_history_lookup_idx
on public.analysis_jobs (user_id, completed_at desc)
where status = 'completed';
