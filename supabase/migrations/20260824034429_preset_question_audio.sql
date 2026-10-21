insert into storage.buckets (id, name, public)
values ('preset-question-audio', 'preset-question-audio', false)
on conflict (id) do update set public = false;
