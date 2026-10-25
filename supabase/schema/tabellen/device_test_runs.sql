-- Erzeugt von tools/schema_abzug.py aus der Live-Datenbank. Nicht von Hand ändern.

create table public.device_test_runs (
  run_key text not null,
  created_at timestamp with time zone default now() not null,
  updated_at timestamp with time zone default now() not null,
  suite_version integer default 0 not null,
  label text default ''::text not null,
  payload jsonb not null,
  constraint device_test_runs_pkey PRIMARY KEY (run_key),
  constraint device_test_runs_run_key_check CHECK ((run_key ~ '^[A-Z0-9]{12}$'::text))
);

alter table public.device_test_runs enable row level security;

revoke all on table public.device_test_runs from anon, authenticated;
