# Schema-Abzug

Der heutige Stand der Datenbank (Schema `public`), erzeugt aus der Live-Datenbank.
**Wird erzeugt, nicht von Hand geändert.** Die Quelle der Wahrheit für die Spiellogik
sind weiter die Migrationen in `../migrations/`; dieser Ordner zeigt, was davon heute
tatsächlich gilt: je Funktion eine Datei mit der letzten Fassung und ihren Rechten.

- `funktionen/<name>.sql`: Funktionsdefinition (Überladungen hintereinander) und
  `revoke`/`grant` für `public`, `anon`, `authenticated`
- `tabellen/<name>.sql`: Spalten, Constraints, Indizes, RLS, Policies, Trigger, Tabellenrechte
- `sichten/<name>.sql`: Views

Nicht enthalten: Supabase-eigene Schemas, Funktionen und Tabellen aus Extensions,
Rechte für `postgres` und `service_role`, Sequenzen (stehen als `nextval(...)` im Default),
Tabelleninhalte.

## Neu erzeugen und prüfen

```
python tools/schema_abzug.py             # schreibt diesen Ordner neu
python tools/schema_abzug.py --pruefen   # Live gegen diesen Ordner, Exit 1 bei Abweichung
```

Beides liest nur (`tools/sql.py` im Modus read-only, nur Systemkataloge). Nach jeder
eingespielten Migration neu erzeugen und mitcommitten; `--pruefen` vor jedem Einspielen.
`--pruefen` meldet außerdem als Warnung, wo Migrationen und Live-Datenbank nicht
zusammenpassen.

## Rechte

Stand: 59 Funktionen (Trigger 2, intern 8, nur PIN 32, offen 17), 11 Tabellen, 1 Sichten.

- **offen**: `anon` darf aufrufen, die Funktion ruft `require_admin` nicht selbst auf
  (öffentlicher Zustand, Team-Funktionen mit Team-Code oder Token)
- **nur PIN**: `anon` darf aufrufen, der Körper ruft `require_admin` direkt auf
- **intern**: weder `public`, `anon` noch `authenticated` dürfen aufrufen
- **Trigger**: Trigger-Funktion

"nur PIN" ist aus dem Funktionstext abgeleitet (direkter Aufruf von `require_admin`),
nicht aus einer Zusicherung der Datenbank. Eine Funktion, die die PIN über eine andere
Hilfsfunktion prüft, steht als "offen".

| Funktion | Zugang | public | anon | authenticated |
|---|---|---|---|---|
| `admin_add_participant(p_pin text, p_name text)` | nur PIN | ja | ja | ja |
| `admin_add_participants(p_pin text, p_names text)` | nur PIN | ja | ja | ja |
| `admin_clear_participants(p_pin text)` | nur PIN | ja | ja | ja |
| `admin_clear_positions(p_pin text)` | nur PIN | ja | ja | ja |
| `admin_delete_participant(p_pin text, p_id uuid)` | nur PIN | ja | ja | ja |
| `admin_delete_photos(p_pin text)` | nur PIN | ja | ja | ja |
| `admin_delete_test_participants(p_pin text)` | nur PIN | ja | ja | ja |
| `admin_draw(p_pin text, p_teams integer, p_size integer)` | nur PIN | ja | ja | ja |
| `admin_finish(p_pin text)` | nur PIN | ja | ja | ja |
| `admin_photo(p_pin text, p_team uuid, p_position integer, p_full boolean, p_route text)` | nur PIN | ja | ja | ja |
| `admin_photos(p_pin text)` | nur PIN | ja | ja | ja |
| `admin_rename_participant(p_pin text, p_id uuid, p_name text)` | nur PIN | ja | ja | ja |
| `admin_reset(p_pin text)` | nur PIN | ja | ja | ja |
| `admin_resume(p_pin text)` | nur PIN | ja | ja | ja |
| `admin_save_station(p_pin text, p_id uuid, p_name text, p_lat double precision, p_lng double precision, p_radius integer, p_hint text, p_riddle text, p_answer text, p_digit integer, p_tip text, p_reveal_start integer, p_reveal_clear integer)` | nur PIN | ja | ja | ja |
| `admin_set_background(p_pin text, p_background text)` | nur PIN | ja | ja | ja |
| `admin_set_leader(p_pin text, p_team uuid, p_participant uuid)` | nur PIN | ja | ja | ja |
| `admin_set_pin(p_pin text, p_new text)` | nur PIN | ja | ja | ja |
| `admin_set_selfie(p_pin text, p_on boolean, p_delete_on date)` | nur PIN | ja | ja | ja |
| `admin_set_settings(p_pin text, p_duration_min integer, p_case_hint text)` | nur PIN | ja | ja | ja |
| `admin_set_start(p_pin text, p_route text, p_name text, p_lat double precision, p_lng double precision)` | nur PIN | ja | ja | ja |
| `admin_set_test_mode(p_pin text, p_on boolean)` | nur PIN | ja | ja | ja |
| `admin_solve_station(p_pin text, p_team uuid, p_position integer)` | nur PIN | ja | ja | ja |
| `admin_start(p_pin text)` | nur PIN | ja | ja | ja |
| `admin_state(p_pin text)` | nur PIN | ja | ja | ja |
| `admin_tracks(p_pin text, p_since timestamp with time zone)` | nur PIN | ja | ja | ja |
| `admin_unlock_station(p_pin text, p_team uuid, p_position integer)` | nur PIN | ja | ja | ja |
| `aktive_route()` | intern | nein | nein | nein |
| `answer_ok(p_answer text, p_solutions text)` | intern | nein | nein | nein |
| `check_in(p_code text, p_lat double precision, p_lng double precision, p_acc double precision)` | offen | ja | ja | ja |
| `current_station(p_team uuid)` | intern | nein | nein | nein |
| `device_test_echo(p_data text)` | offen | ja | ja | ja |
| `device_test_save(p_key text, p_payload jsonb)` | offen | ja | ja | ja |
| `dist_m(lat1 double precision, lng1 double precision, lat2 double precision, lng2 double precision)` | intern | nein | nein | nein |
| `game_state_pin_pruefen()` | Trigger | ja | ja | ja |
| `leader_code(p_token text)` | offen | ja | ja | ja |
| `lookup_participant(p_name text)` | offen | ja | ja | ja |
| `member_state(p_token text, p_akku integer, p_laedt boolean)` | offen | ja | ja | ja |
| `name_abstand(a text, b text)` | intern | nein | nein | nein |
| `norm(t text)` | intern | nein | nein | nein |
| `participants_name_key_pruefen()` | Trigger | ja | ja | ja |
| `public_state()` | offen | ja | ja | ja |
| `rb_befehl(p_pin text, p_befehl text)` | nur PIN | nein | ja | ja |
| `rb_ende(p_pin text)` | nur PIN | nein | ja | ja |
| `rb_poll(p_pin text, p_seit bigint)` | nur PIN | nein | ja | ja |
| `rb_status_holen(p_pin text)` | nur PIN | nein | ja | ja |
| `rb_status_setzen(p_pin text, p_status jsonb)` | nur PIN | nein | ja | ja |
| `register_participant(p_name text, p_token text)` | offen | ja | ja | ja |
| `report_position(p_code text, p_lat double precision, p_lng double precision, p_acc double precision, p_kompass text)` | offen | ja | ja | ja |
| `require_admin(p_pin text)` | intern | nein | nein | nein |
| `reveal_tip(p_code text)` | offen | ja | ja | ja |
| `submit_answer(p_code text, p_answer text, p_position integer)` | offen | ja | ja | ja |
| `submit_final(p_code text, p_value text, p_lat double precision, p_lng double precision, p_acc double precision)` | offen | ja | ja | ja |
| `team_by_code(p_code text)` | intern | nein | nein | nein |
| `team_photo(p_code text, p_token text, p_read_token text, p_position integer, p_full boolean)` | offen | ja | ja | ja |
| `team_selfie(p_code text, p_position integer, p_photo text, p_thumb text)` | offen | ja | ja | ja |
| `team_selfie_skip(p_code text, p_position integer)` | offen | ja | ja | ja |
| `team_set_leader(p_code text, p_name text)` | offen | ja | ja | ja |
| `team_state(p_code text)` | offen | ja | ja | ja |
