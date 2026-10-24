-- Erzeugt von tools/schema_abzug.py aus der Live-Datenbank. Nicht von Hand ändern.

create table public.progress (
  team_id uuid not null,
  station_id uuid not null,
  checked_in_at timestamp with time zone,
  solved_at timestamp with time zone,
  failed_attempts integer default 0 not null,
  locked_until timestamp with time zone,
  pauses integer default 0 not null,
  tip_at timestamp with time zone,
  selfie_at timestamp with time zone,
  last_wrong text,
  constraint progress_pkey PRIMARY KEY (team_id, station_id),
  constraint progress_station_id_fkey FOREIGN KEY (station_id) REFERENCES stations_alle(id) ON DELETE CASCADE,
  constraint progress_team_id_fkey FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE
);

alter table public.progress enable row level security;

revoke all on table public.progress from anon, authenticated;
