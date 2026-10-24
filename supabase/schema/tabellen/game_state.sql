-- Erzeugt von tools/schema_abzug.py aus der Live-Datenbank. Nicht von Hand ändern.

create table public.game_state (
  id integer default 1 not null,
  status text default 'registration'::text not null,
  started_at timestamp with time zone,
  finished_at timestamp with time zone,
  winner_team_id uuid,
  admin_pin text default '2026'::text not null,
  prize_count integer default 3 not null,
  test_mode boolean default false not null,
  duration_min integer default 180 not null,
  case_hint text default 'Die Koffer stehen bei der Spielleitung an der letzten Station. Zeigt dort euren Platz-Bildschirm.'::text not null,
  background text default 'klassisch'::text not null,
  selfie_on boolean default false not null,
  photos_delete_on date,
  start_name text default 'Start'::text not null,
  start_lat double precision,
  start_lng double precision,
  test_start_name text default 'Start'::text not null,
  test_start_lat double precision,
  test_start_lng double precision,
  constraint game_state_background_check CHECK ((background = ANY (ARRAY['klassisch'::text, 'a'::text, 'b'::text, 'c'::text]))),
  constraint game_state_duration_min_check CHECK (((duration_min >= 10) AND (duration_min <= 720))),
  constraint game_state_id_check CHECK ((id = 1)),
  constraint game_state_pkey PRIMARY KEY (id),
  constraint game_state_prize_count_check CHECK (((prize_count >= 0) AND (prize_count <= 16))),
  constraint game_state_status_check CHECK ((status = ANY (ARRAY['registration'::text, 'drawn'::text, 'running'::text, 'finished'::text]))),
  constraint game_state_winner_team_id_fkey FOREIGN KEY (winner_team_id) REFERENCES teams(id) ON DELETE SET NULL
);

alter table public.game_state enable row level security;

CREATE TRIGGER game_state_pin_pruefen BEFORE UPDATE OF admin_pin ON public.game_state FOR EACH ROW EXECUTE FUNCTION game_state_pin_pruefen();

revoke all on table public.game_state from anon, authenticated;
