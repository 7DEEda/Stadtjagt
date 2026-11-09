-- Erzeugt von tools/schema_abzug.py aus der Live-Datenbank. Nicht von Hand ändern.

create table public.notweg_schluessel (
  token text not null,
  team_id uuid not null,
  erstellt timestamp with time zone default now() not null,
  gilt_bis timestamp with time zone not null,
  constraint notweg_schluessel_pkey PRIMARY KEY (token),
  constraint notweg_schluessel_team_id_fkey FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE
);

alter table public.notweg_schluessel enable row level security;

revoke all on table public.notweg_schluessel from anon, authenticated;
