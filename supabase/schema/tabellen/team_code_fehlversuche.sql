-- Erzeugt von tools/schema_abzug.py aus der Live-Datenbank. Nicht von Hand ändern.

create table public.team_code_fehlversuche (
  quelle text not null,
  seit timestamp with time zone default now() not null,
  anzahl integer default 0 not null,
  constraint team_code_fehlversuche_pkey PRIMARY KEY (quelle)
);

alter table public.team_code_fehlversuche enable row level security;

revoke all on table public.team_code_fehlversuche from anon, authenticated;
