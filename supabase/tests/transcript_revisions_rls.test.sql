begin;

create extension if not exists pgtap with schema extensions;

select plan(13);

select has_table('public', 'answer_revisions', 'answer_revisions table exists');
select has_table('public', 'coaching_runs', 'coaching_runs table exists');
select has_function(
    'public',
    'create_answer_revision',
    array['uuid', 'text', 'jsonb'],
    'answer revision RPC exists'
);
select ok(
    (select relrowsecurity from pg_class where oid = 'public.answer_revisions'::regclass),
    'answer_revisions has RLS enabled'
);
select ok(
    (select relrowsecurity from pg_class where oid = 'public.coaching_runs'::regclass),
    'coaching_runs has RLS enabled'
);
select ok(
    not has_table_privilege('anon', 'public.answer_revisions', 'select'),
    'anonymous users cannot read answer revisions'
);
select ok(
    has_table_privilege('authenticated', 'public.answer_revisions', 'select'),
    'authenticated users can read revisions through RLS'
);
select ok(
    not has_table_privilege('authenticated', 'public.answer_revisions', 'insert'),
    'authenticated users cannot bypass the confirmation RPC'
);
select ok(
    not has_table_privilege('authenticated', 'public.answer_revisions', 'update'),
    'confirmed revisions cannot be updated by clients'
);
select ok(
    not has_table_privilege('authenticated', 'public.coaching_runs', 'insert'),
    'only the server can persist validated coaching runs'
);

select ok(
    position('is_anonymous' in (
        select pg_get_expr(polqual, polrelid)
        from pg_policy
        where polrelid = 'public.answer_revisions'::regclass
          and polname = 'users_read_active_own_answer_revisions'
    )) > 0,
    'answer revision reads reject anonymous authenticated users'
);

select ok(
    position('is_anonymous' in (
        select pg_get_expr(polqual, polrelid)
        from pg_policy
        where polrelid = 'public.coaching_runs'::regclass
          and polname = 'users_read_active_own_coaching_runs'
    )) > 0,
    'coaching run reads reject anonymous authenticated users'
);

select ok(
    position('is_anonymous' in pg_get_functiondef(
        'public.create_answer_revision(uuid,text,jsonb)'::regprocedure
    )) > 0,
    'answer revision RPC rejects anonymous authenticated users'
);

select * from finish();
rollback;
