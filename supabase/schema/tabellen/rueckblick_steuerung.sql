-- Erzeugt von tools/schema_abzug.py aus der Live-Datenbank. Nicht von Hand ändern.

create table public.rueckblick_steuerung (
  id integer default 1 not null,
  nr bigint default 0 not null,
  befehl text,
  befehl_um timestamp with time zone,
  status jsonb,
  status_um timestamp with time zone,
  handy_um timestamp with time zone,
  constraint rueckblick_steuerung_id_check CHECK ((id = 1)),
  constraint rueckblick_steuerung_pkey PRIMARY KEY (id)
);

alter table public.rueckblick_steuerung enable row level security;

revoke all on table public.rueckblick_steuerung from anon, authenticated;
