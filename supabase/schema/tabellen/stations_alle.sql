-- Erzeugt von tools/schema_abzug.py aus der Live-Datenbank. Nicht von Hand ändern.

create table public.stations_alle (
  id uuid default gen_random_uuid() not null,
  position integer not null,
  name text not null,
  lat double precision,
  lng double precision,
  radius_m integer default 50 not null,
  location_hint text default ''::text not null,
  riddle text default ''::text not null,
  answer text default ''::text not null,
  digit integer default 0 not null,
  tip text default ''::text not null,
  reveal_start_m integer,
  reveal_clear_m integer,
  route text default 'echt'::text not null,
  constraint stations_digit_check CHECK (((digit >= 0) AND (digit <= 9))),
  constraint stations_pkey PRIMARY KEY (id),
  constraint stations_reveal_pruefen CHECK ((((reveal_start_m IS NULL) AND (reveal_clear_m IS NULL)) OR ((reveal_clear_m > 0) AND (reveal_start_m > reveal_clear_m) AND (reveal_start_m <= 5000)))),
  constraint stations_route_position_key UNIQUE (route, "position"),
  constraint stations_route_pruefen CHECK ((route = ANY (ARRAY['echt'::text, 'test'::text])))
);

alter table public.stations_alle enable row level security;

revoke all on table public.stations_alle from anon, authenticated;
