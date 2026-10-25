-- Erzeugt von tools/schema_abzug.py aus der Live-Datenbank. Nicht von Hand ändern.

create table public.station_photos (
  team_id uuid not null,
  station_id uuid not null,
  photo bytea not null,
  thumb bytea not null,
  taken_at timestamp with time zone default now() not null,
  constraint station_photos_pkey PRIMARY KEY (team_id, station_id),
  constraint station_photos_team_id_station_id_fkey FOREIGN KEY (team_id, station_id) REFERENCES progress(team_id, station_id) ON DELETE CASCADE
);

alter table public.station_photos enable row level security;

revoke all on table public.station_photos from anon, authenticated;
