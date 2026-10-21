-- Server-owned draft/consent state. Clients can read their active rows but cannot write state.
create table public.preparation_conversations (
    id uuid primary key,
    user_id uuid not null references auth.users(id) on delete cascade,
    practice_session_id uuid references public.practice_sessions(id) on delete cascade,
    version integer not null default 1 check (version > 0),
    state jsonb not null default '{}'::jsonb check (jsonb_typeof(state) = 'object' and octet_length(state::text) <= 1048576),
    created_at timestamptz not null default now(),
    expires_at timestamptz not null default now() + interval '24 hours',
    constraint preparation_expiry check (expires_at <= created_at + interval '24 hours')
);
create index preparation_session_owner_idx on public.preparation_conversations(practice_session_id, user_id);
create index preparation_expiry_idx on public.preparation_conversations(expires_at);
alter table public.preparation_conversations enable row level security;
revoke all on public.preparation_conversations from public, anon, authenticated;
grant select on public.preparation_conversations to authenticated;
grant all on public.preparation_conversations to service_role;
create policy preparation_owner_read on public.preparation_conversations for select to authenticated
    using ((select auth.uid()) = user_id and expires_at > now());

-- The 24-hour access boundary also has scheduled physical deletion.
create extension if not exists pg_cron with schema pg_catalog;
select cron.schedule('preparation-conversation-retention', '17 * * * *',
    $$delete from public.preparation_conversations where expires_at <= now()$$);
