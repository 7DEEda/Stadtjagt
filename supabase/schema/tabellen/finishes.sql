-- Erzeugt von tools/schema_abzug.py aus der Live-Datenbank. Nicht von Hand ändern.

create table public.finishes (
  team_id uuid not null,
  place integer not null,
  finished_at timestamp with time zone default now() not null,
  constraint finishes_pkey PRIMARY KEY (team_id),
  constraint finishes_place_check CHECK ((place >= 1)),
  constraint finishes_place_key UNIQUE (place),
  constraint finishes_team_id_fkey FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE
);

alter table public.finishes enable row level security;

revoke all on table public.finishes from anon, authenticated;
