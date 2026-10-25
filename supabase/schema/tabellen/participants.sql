-- Erzeugt von tools/schema_abzug.py aus der Live-Datenbank. Nicht von Hand ändern.

create table public.participants (
  id uuid default gen_random_uuid() not null,
  name text not null,
  name_key text not null,
  team_id uuid,
  created_at timestamp with time zone default now() not null,
  token text,
  constraint participants_name_key_key UNIQUE (name_key),
  constraint participants_pkey PRIMARY KEY (id),
  constraint participants_team_id_fkey FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE SET NULL,
  constraint participants_token_key UNIQUE (token)
);

alter table public.participants enable row level security;

CREATE TRIGGER participants_name_key_pruefen BEFORE INSERT OR UPDATE OF name, name_key ON public.participants FOR EACH ROW EXECUTE FUNCTION participants_name_key_pruefen();

revoke all on table public.participants from anon, authenticated;
