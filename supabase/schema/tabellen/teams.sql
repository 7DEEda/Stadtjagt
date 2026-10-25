-- Erzeugt von tools/schema_abzug.py aus der Live-Datenbank. Nicht von Hand ändern.

create table public.teams (
  id uuid default gen_random_uuid() not null,
  name text not null,
  code text not null,
  leader_participant_id uuid,
  created_at timestamp with time zone default now() not null,
  read_token text default replace((gen_random_uuid())::text, '-'::text, ''::text),
  constraint teams_code_key UNIQUE (code),
  constraint teams_pkey PRIMARY KEY (id),
  constraint teams_read_token_key UNIQUE (read_token)
);

alter table public.teams enable row level security;

revoke all on table public.teams from anon, authenticated;
