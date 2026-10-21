create table public.ncs_backend_snapshots (
  id text primary key check (id = 'backend'),
  payload jsonb not null check (jsonb_typeof(payload) = 'object' and jsonb_typeof(payload->'options') = 'array' and jsonb_array_length(payload->'options') = 9)
);
alter table public.ncs_backend_snapshots enable row level security;
revoke all on public.ncs_backend_snapshots from public, anon, authenticated;
grant select, insert, update on public.ncs_backend_snapshots to service_role;
comment on table public.ncs_backend_snapshots is 'Server-only last validated official NCS response for explicit retry.';
