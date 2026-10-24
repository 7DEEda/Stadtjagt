-- Erzeugt von tools/schema_abzug.py aus der Live-Datenbank. Nicht von Hand ändern.

create table public.position_log (
  id bigint default nextval('position_log_id_seq'::regclass) not null,
  team_id uuid not null,
  lat double precision not null,
  lng double precision not null,
  accuracy_m double precision,
  recorded_at timestamp with time zone default now() not null,
  constraint position_log_pkey PRIMARY KEY (id),
  constraint position_log_team_id_fkey FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE
);

CREATE INDEX position_log_team_time ON public.position_log USING btree (team_id, recorded_at);

alter table public.position_log enable row level security;

revoke all on table public.position_log from anon, authenticated;
