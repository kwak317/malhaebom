create table public.question_tts_audio (
    id uuid primary key,
    user_id uuid not null references auth.users (id) on delete cascade,
    audio_path text not null unique,
    duration_ms integer not null check (duration_ms > 0),
    created_at timestamptz not null default now(),
    expires_at timestamptz not null default (now() + interval '24 hours'),
    cleanup_attempted_at timestamptz,
    cleanup_error_code text
);

insert into storage.buckets (id, name, public)
values ('question-tts-audio', 'question-tts-audio', false)
on conflict (id) do nothing;

revoke all on table public.question_tts_audio from anon, authenticated;
grant select, insert, delete on table public.question_tts_audio to authenticated;

alter table public.question_tts_audio enable row level security;

create policy "question_tts_audio_select_own"
on public.question_tts_audio for select to authenticated
using ((select auth.uid()) = user_id);

create policy "question_tts_audio_insert_own"
on public.question_tts_audio for insert to authenticated
with check ((select auth.uid()) = user_id);

create policy "question_tts_audio_delete_own"
on public.question_tts_audio for delete to authenticated
using ((select auth.uid()) = user_id);

create policy "question_tts_storage_insert_own"
on storage.objects for insert to authenticated
with check (
    bucket_id = 'question-tts-audio'
    and (storage.foldername(name))[1] = (select auth.uid()::text)
);

create policy "question_tts_storage_select_own"
on storage.objects for select to authenticated
using (
    bucket_id = 'question-tts-audio'
    and (storage.foldername(name))[1] = (select auth.uid()::text)
);

create policy "question_tts_storage_delete_own"
on storage.objects for delete to authenticated
using (
    bucket_id = 'question-tts-audio'
    and (storage.foldername(name))[1] = (select auth.uid()::text)
);

-- Hosted-project verification after the designated operator runs `supabase db push`:
-- 1. Confirm this table has RLS enabled and question-tts-audio remains private.
-- 2. With two authenticated users, confirm an owner can read/delete only their own row and object.
