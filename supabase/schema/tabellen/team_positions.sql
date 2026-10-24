-- Erzeugt von tools/schema_abzug.py aus der Live-Datenbank. Nicht von Hand ändern.

create table public.team_positions (
  team_id uuid not null,
  lat double precision not null,
  lng double precision not null,
  accuracy_m double precision,
  updated_at timestamp with time zone default now() not null,
  kompass text,
  constraint team_positions_pkey PRIMARY KEY (team_id),
  constraint team_positions_team_id_fkey FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE
);

alter table public.team_positions enable row level security;

revoke all on table public.team_positions from anon, authenticated;
