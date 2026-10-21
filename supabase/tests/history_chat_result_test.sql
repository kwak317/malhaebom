begin;
create extension if not exists pgtap with schema extensions;
set local search_path = public, extensions;
select plan(8);

insert into auth.users (id) values
    ('91000000-0000-4000-8000-000000000001'),
    ('91000000-0000-4000-8000-000000000002');
insert into public.analysis_jobs
    (id, user_id, source_id, practice_session_id, question_type, question_id, attempt_no,
     audio_path, status, result, delivery, completed_at, expires_at)
values
    ('91000000-0000-4000-8000-000000000011', '91000000-0000-4000-8000-000000000001', 'history-test',
     '91000000-0000-4000-8000-000000000021', 'preset', 'preset-04', 1, 'test-only/first.wav',
     'completed', '{"text":"first original"}', '{"metrics":{"cpm":330}}', now() - interval '5 minutes', now() + interval '1 hour'),
    ('91000000-0000-4000-8000-000000000012', '91000000-0000-4000-8000-000000000001', 'history-test',
     '91000000-0000-4000-8000-000000000021', 'preset', 'preset-04', 2, 'test-only/second.wav',
     'completed', '{"text":"second original","content_feedback":{"kept":true}}', '{"metrics":{"cpm":310}}', now() - interval '5 minutes', now() + interval '1 hour');

set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"91000000-0000-4000-8000-000000000002"}', true);
select results_eq(
    $$update public.analysis_jobs set result = '{}'::jsonb
      where id = '91000000-0000-4000-8000-000000000012' returning id::text$$,
    array[]::text[], 'another owner cannot overwrite the conversation');
select results_eq(
    $$select id::text from public.analysis_jobs where source_id = 'history-test'$$,
    array[]::text[], 'another owner cannot read the records');

select set_config('request.jwt.claims', '{"sub":"91000000-0000-4000-8000-000000000001"}', true);
select results_eq(
    $$update public.analysis_jobs
      set result = result || '{"interview_chat":{"messages":[{"role":"assistant","message":"test-only summary"}]}}'::jsonb
      where id = '91000000-0000-4000-8000-000000000012'
        and user_id = auth.uid() and attempt_no = 2 and status = 'completed' and expires_at > now()
      returning id::text$$,
    array['91000000-0000-4000-8000-000000000012'], 'owner can store archive in existing result JSONB');
select results_eq(
    $$select result->>'text', result->'content_feedback'->>'kept', delivery->'metrics'->>'cpm'
      from public.analysis_jobs where id = '91000000-0000-4000-8000-000000000012'$$,
    $$values ('second original'::text, 'true'::text, '310'::text)$$,
    'original STT content feedback and metrics stay intact');
select results_eq(
    $$select (completed_at = now() - interval '5 minutes') and (expires_at = now() + interval '1 hour')
      from public.analysis_jobs where id = '91000000-0000-4000-8000-000000000012'$$,
    array[true], 'saving does not extend expiry or change analysis completion');
select results_eq(
    $$select result->>'text', result ? 'interview_chat' from public.analysis_jobs
      where id = '91000000-0000-4000-8000-000000000011'$$,
    $$values ('first original'::text, false)$$, 'first attempt remains unchanged');

reset role;
update public.analysis_jobs set expires_at = now() - interval '1 minute'
where id = '91000000-0000-4000-8000-000000000012';
set local role authenticated;
select results_eq(
    $$update public.analysis_jobs set result = '{}'::jsonb
      where id = '91000000-0000-4000-8000-000000000012' and expires_at > now() returning id::text$$,
    array[]::text[], 'expiry filter prevents archive update after expiry');
delete from public.analysis_jobs where practice_session_id = '91000000-0000-4000-8000-000000000021';
select results_eq(
    $$select id::text from public.analysis_jobs where source_id = 'history-test'$$,
    array[]::text[], 'deleting a practice removes its archive');
select * from finish();
rollback;
