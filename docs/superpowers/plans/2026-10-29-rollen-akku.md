# Rollen und Akku: Umsetzungsplan (29.10.2026)

> Für ausführende Agenten: superpowers:subagent-driven-development oder superpowers:executing-plans.
> Erstellt von einem Plan-Agenten (Opus) gegen den Code vom 29.10.2026. Offene Fragen F1 bis F6 unten
> sind vor dem Bau mit Friedrich zu klären.

**Ziel:** Die Rolle eines Handys (Teamleitung oder Mitlesen) kommt vom Server und wechselt ohne Tippen in beide
Richtungen. Die Teamleitung übergibt über ein Fenster mit Personen zum Antippen samt Akku. Jedes Handy meldet seinen
Akku; das Team sieht „Akku knapp“, die Teamleitung bekommt bei 20 % und 10 % das Übergabe-Fenster, die Spielleitung
sieht den Akku der Teamleitung in der Teamzeile.

**Aufbau:** Eine Migration ergänzt `participants` um Akku- und Kontaktspalten, `member_state` und `report_position`
um Parameter mit `default`, `team_state` und `admin_state` um neue Felder (kein bestehendes Feld ändert sich). Im
Frontend bleiben die Routen `#/team` (Code, `team_state`) und `#/public` (Token, `member_state`); neu ist ein stiller
Wechsel zwischen ihnen (`rolleWechseln`) per `history.replaceState`, wie in `mitLinkPruefen()`.

**Spezifikation:** `docs/superpowers/specs/2026-10-02-teststation-kompass-waechter-design.md`, „Teil 3“ und „Prüfen“.
**Mockups:** maßgeblich `mockups/rollen-akku-kompass.html`; in `mockups/akku-warnung.html` sind „Jonas Keller tippt
dann auf ‚Teamleitung‘“ und der Füllsatz „Damit euer Team nicht hängen bleibt“ überholt.

## 0. Wo die Spezifikation nicht mehr zum Code passt

| # | Spezifikation (02.10.) | Code heute | Vorschlag |
|---|---|---|---|
| A1 | Handy mit `sj.token` fragt immer `member_state` | nur in `#/public` (`mitlesen()`); Teamleitung fragt `team_state`, prüft per `leader_code` (`leitungNochDa`) | so lassen: Verlust über `leitungNochDa`, Gewinn über `member_state`; kein zusätzlicher Abruf |
| A2 | `team_state` liefert je Mitglied Akku | `team.members` ist Array von Namen, überall mit `includes`/`===` gelesen | `members` nicht ändern (alte Fassungen aus dem SW-Cache); neues Feld `geraete: [{name, angemeldet, verbunden, akku, laedt}]` |
| A3 | „in den letzten 2 Minuten nicht abgerufen“ | kein Zeitstempel | neue Spalte `participants.gesehen_at`; der Server rechnet `verbunden` und gibt `akku` nur bis 10 min Alter aus (Handyuhr egal) |
| A4 | Liste nur angemeldete Personen | `team_state` verrät keinen Token; `team_set_leader` lehnt Personen ohne Token ab (Audit) | `geraete[].angemeldet = token is not null`, Liste filtert danach |
| A5 | `member_state(+p_akku, p_laedt)`, `report_position(+…)` | `member_state(text)`, `report_position(text, float8, float8, float8, text)` | Signaturwechsel: alte Fassung droppen (sonst PGRST203), wie Nachtrag 30 |
| A6 | Akku der Teamleitung über `report_position` | kennt nur `p_code`; Notweg-Tablet (`sj.hand`) meldet mit demselben Code | Akku auf `teams.leader_participant_id`; mit `sj.hand` kein Akku; vor `running`/ohne GPS bleibt er unbekannt |
| A7 | zurück aufs Mitlesen statt Abmelden | `leitungNochDa` und `t-abgeben` melden ab („Du leitest gerade kein Team“) | ersetzen durch `rolleWechseln("mitglied", s)`, GPS läuft weiter |
| A8 | neue Leitung schaltet von selbst um | Mitglied muss „Zur Teamleitung“ / „loslegen“ tippen | `member_state` liefert `ichLeite`; Flanke false auf true schaltet still um |
| A9 | Übergabe-Fenster mit Personen | Panel mit `<select id="tneu">`, darauf bauen `waechter.py` und `audit2510.py` Teil 11 | echtes Fenster, Auswahl in `S.team.wahl`, `#tabgeben` bleibt; beide Prüfskripte anpassen |
| A10 | Texte „tippt auf ‚Teamleitung‘“ | im Abgeben-Panel, in der Meldung nach dem Abgeben, in `DANGER.leader.lead` | neu formulieren |
| A11 | Geräte-Test „Akku“ | schon da seit Suite 20 | entfällt |
| A12 | Offline-Warteschlange | gibt es nicht allgemein; nächster Abruf gleicht ab | Akku geht beim nächsten gelungenen Abruf mit; Übergabe im Funkloch zeigt Meldung im Fenster |
| A13 | kein Prüfskript genannt | | neu `tools/pruefstand/rollen_akku.py` (Port 8873) und `rollen_akku_db.py` |
| A14 | Abmelden der Teamleitung | `t-logout` setzt `sj.abgemeldet`, `leitungOhneCode` holt dann nichts | widerspricht „Rolle vom Server“, Frage F1 |

## Globale Regeln

- Datenbank bleibt mit der vorigen App-Fassung verträglich: neue Parameter nur mit `default`, keine Felder entfernen.
- Jede neu angelegte oder gedroppte Funktion: `revoke all … from public, anon, authenticated; grant execute … to
  public, anon, authenticated;` (Muster `20261025090000_audit.sql`), `SECURITY DEFINER`, `SET search_path TO
  'public'`, am Ende `notify pgrst, 'reload schema';`.
- Vorlage ist `supabase/schema/funktionen/<name>.sql`. Vor dem Einspielen `python tools/schema_abzug.py --pruefen`,
  danach `python tools/schema_abzug.py` und mitcommitten. Jedes `UPDATE` mit `WHERE` (pg-safeupdate).
- Erst Datenbank, dann App; der Client fällt bei PGRST202 trotzdem auf die alte Signatur zurück.
- Texte: echte Umlaute, keine Gedankenstriche, „du“/„ihr“, `vorname()`, keine Füllsätze, `12 %` nicht umbrechen,
  Tippziele mindestens 42 px.
- Prüfstand im Vordergrund mit Timeout. Migration nicht einspielen und nicht pushen ohne Friedrichs Ja.

## Prüfschwerpunkte im Review

- Nach jedem Wechsel hat höchstens ein Handy mit Token ein `S.team.code`; das alte löscht `sj.code` und
  `sj.letzter.team` (sonst holt `letzterStand()` im Funkloch die Leitungsansicht zurück).
- Kein Hin und Her: Rollengewinn nur bei Flanke oder beim ersten Laden in `drawn`/`running`.
- Takt-Zähler `ZAEHL`: laufende Antworten der anderen Ansicht verfallen, kein `render()` mit halbem Zustand.
- Last: `member_state` schreibt; Drosselung höchstens eine Schreibung je 20 s und Person, außer der Akku ändert sich.
- Akku-Fenster öffnet nicht über Hochhalten, Hilfe-Blatt, Einmessen, Selfie-Kamera, Dialog oder beim Tippen.

## Task 1: Migration `supabase/migrations/20261029120000_rollen_akku.sql` und Probelauf

Dateien: Migration, `tools/pruefstand/rollen_akku_db.py`, `tools/pruefstand/rechte_db.py` (Migration anhängen).

1. Spalten (mehrfach ausführbar):
   ```sql
   alter table participants add column if not exists akku smallint;          -- 0..100, null = unbekannt (iPhone)
   alter table participants add column if not exists akku_laedt boolean;
   alter table participants add column if not exists akku_at timestamptz;
   alter table participants add column if not exists gesehen_at timestamptz; -- letzter member_state bzw. report_position
   ```
2. `member_state` mit Signaturwechsel:
   ```sql
   drop function if exists public.member_state(text);
   create or replace function public.member_state(p_token text, p_akku integer default null, p_laedt boolean default null)
    returns json language plpgsql security definer set search_path to 'public' as $function$
   declare v participants; t teams; v_akku int := case when p_akku between 0 and 100 then p_akku end;
   begin
     -- Prüfungen wie bisher ('Unbekanntes Gerät.')
     update participants set gesehen_at = now(),
            akku       = coalesce(v_akku, akku),
            akku_laedt = case when v_akku is null then akku_laedt else coalesce(p_laedt, false) end,
            akku_at    = case when v_akku is null then akku_at else now() end
      where id = v.id
        and (gesehen_at is null or gesehen_at < now() - interval '20 seconds'
             or (v_akku is not null and (akku is distinct from v_akku or akku_laedt is distinct from coalesce(p_laedt, false))));
     if v.team_id is null then return json_build_object('name', v.name, 'team', null, 'ichLeite', false); end if;
     select * into t from teams where id = v.team_id;
     return ((team_state(t.code)::jsonb #- '{team,code}' #- '{team,readToken}')
             || jsonb_build_object('name', v.name, 'ichLeite', t.leader_participant_id = v.id))::json;
   end $function$;
   ```
   Rechte für `member_state(text, integer, boolean)`. `p_akku null` überschreibt keinen bekannten Stand.
3. `report_position` mit Signaturwechsel: alte Fassung mit 5 Parametern droppen, neue mit `p_akku integer default
   null, p_laedt boolean default null`. Reihenfolge: Status `running` → `team_by_code` → Akku auf
   `leader_participant_id` (nur gültiger Wert, setzt `gesehen_at`) → Positionsprüfung → Insert wie heute.
4. `team_state` (gleiche Signatur), neues Feld oben:
   ```sql
   'geraete', coalesce((select json_agg(json_build_object(
       'name', p.name,
       'angemeldet', p.token is not null,
       'verbunden', coalesce(p.gesehen_at > now() - interval '2 minutes', false),
       'akku',  case when p.akku_at > now() - interval '10 minutes' then p.akku end,
       'laedt', case when p.akku_at > now() - interval '10 minutes' then p.akku_laedt end) order by p.name)
     from participants p where p.team_id = t.id), '[]'::json),
   ```
5. `admin_state`: `participants[].hatHandy` (`token is not null`), `teams[].leaderAkku` (`{akku, laedt, at}` der
   Leitung, nur bis 10 min Alter).
6. Unverändert: `team_set_leader`, `admin_set_leader`, `leader_code`, `public_state`, `member_state_by_team`.
7. Probelauf `rollen_akku_db.py` im Muster von `eingaben_db.py` (DO-Block, `PROBELAUF_OK`, `--ohne` rot):
   alter Aufruf mit einem Argument; Akku setzen; ungültige Werte ignoriert; Drosselung; `geraete` mit
   `angemeldet`/`verbunden`/Alter; `report_position` mit und ohne Akku, nichts in `drawn`; `ichLeite` nach
   `team_set_leader`; `admin_state`-Felder; genau eine `member_state` und eine `report_position` in `pg_proc`;
   Rechte, `prosecdef`, `search_path`; alle bisherigen Felder von `team_state` und `admin_state` noch da.

Rückwärtsverträglich: alte App mit neuer Datenbank geht unverändert (neue Felder ignoriert); neue App mit alter
Datenbank fällt bei PGRST202 einmal zurück und merkt `DB_OHNE_AKKU`. `sw.js` bleibt unverändert.

## Task 2: Prüfstand-Grundlage (`mock.js`, Gerüst `rollen_akku.py`)

Gespielter Akku (`akku: {level, laedt}` oder `null` für iPhone, `window.__akku(level, laedt)` mit Events),
Team-Daten (`akkus`, `ohneHandy`, `offline`), `geraete`/`ichLeite`/`leaderAkku`/`hatHandy` (außer bei
`window.__ALTE_DB`), `__MEMBER_ARGS`, `__AKKU`, PGRST202 bei `__ALTE_DB`, `team_set_leader` setzt wirklich
`__leitung`. Szenarien `rolle-mitglied`, `rolle-leitung`, `akku-mitglied-knapp`, `akku-leitung-knapp-mitglied`,
`akku-laedt`, `admin-akku`.

## Task 3: Akku lesen und melden (`index.html`)

`AKKU = {level, laedt}`, `akkuStarten()` mit `navigator.getBattery` (ohne API still null), nicht für Spielleitung und
Rückblick. `akkuGeaendert()` prüft das Fenster, setzt bei Schwelle/Laden `S.gps.akkuNeu`, zeichnet nur bei
geändertem Hinweis neu. `mitlesen()` schickt `p_akku`/`p_laedt`; `maybeReport()` ebenso, außer mit `sj.hand`;
Rückfall bei PGRST202.

## Task 4: Rolle vom Server (`index.html`)

`rolleWechseln("leitung" | "mitglied", st)` per `replaceState`, Einblendung `S.kurz` („Du leitest jetzt Team Fuchs“
bzw. „Jonas leitet jetzt das Team“), beim Wechsel aufs Mitlesen `sj.code`/`sj.letzter.team` löschen, GPS läuft
weiter. `rolleNachziehen()` nach `mitlesen()` (Flanke oder erstes Laden, nicht bei `sj.hand`). `leitungNochDa`
wechselt statt abzumelden. `S.rolle` in `leitungOhneCode`.

## Task 5: Übergabe-Fenster (`index.html`, `waechter.py`, `audit2510.py` Teil 11)

`waehlbar(st)` (nur angemeldete, verbunden zuerst; Rückfall `members`), `leitungAbgebbar` danach, `uebergabeHTML`
als Blatt mit Personenknöpfen (Akku, „Handy nicht verbunden“), Köpfe `abgeben` / `akku20` / `akku10`,
`#tabgeben` gesperrt ohne Wahl, Escape und Tipp daneben schließen. `team_set_leader` → `rolleWechseln("mitglied")`.
Altes `<select>`-Panel entfällt.

## Task 6: Akku-Hinweis und Akku-Fenster (`index.html`)

`akkuListe`, `akkuHinweisHTML` („Akku knapp: dein Handy 18 %, Julia 15 %“ plus passender Satz) oben im Reiter
Weg/Rätsel ab `running`. `akkuFensterPruefen()`: nur Teamleitung, kein `sj.hand`, `running`, nicht ladend,
`leitungAbgebbar`; je Schwelle einmal (`sj.akku`), wartet, solange etwas anderes offen ist.

## Task 7: Spielleitung (`index.html`)

`akkuVermerk` (Chip „Akku 18 %“ ab 20 %, nicht ladend), Detail „Akku der Teamleitung“, Auswahl mit „(kein eigenes
Handy)“, `DANGER.leader.lead` neu ohne „tippt“.

## Task 8: Prüfskript `rollen_akku.py` (Port 8873) und Gesamtlauf

Teile: Mitglied wird Leitung; Leitung gibt ab; Spielleitung nimmt weg; Notweg `sj.hand`; `sj.abgemeldet` (F1);
Akku-Fenster 20/10 je einmal, auch nach Neuladen; kein Fenster beim Laden; Hinweis bei knappem Mitglied; Leitung
knapp; Spielleitung; Meldungen mit Akku; alte Datenbank; iPhone ohne Akku; keine Gedankenstriche. Danach alle
bestehenden Prüfskripte grün, dann Code-Review.

## Task 9: Ausliefern (nach Friedrichs Ja)

`schema_abzug.py --pruefen` → `python tools/sql.py supabase/migrations/20261029120000_rollen_akku.sql` →
`schema_abzug.py`, `supabase/schema/` committen → App pushen.

## Task 10: Doku und Feldprobe

SPIEL.md (§2, §4, §6, §8), HANDOFF Nachtrag 39, Prüfstand-README. Feldprobe mit Android (Akku lesbar) und iPhone.

## Offene Fragen an Friedrich

- **F1** Abmelden der Teamleitung streichen (Ausweg ist „Leitung abgeben“, Abmelden nur noch am Notweg-Tablet)
  oder behalten (dann sperrt `sj.abgemeldet` bis zur nächsten Rollenänderung)? Empfehlung: streichen.
- **F2** Wirkt sofort im echten Spiel, nicht nur im Testmodus? Empfehlung: ja.
- **F3** Akku-Fenster je Schwelle einmal, wieder scharf nach Laden über 25 %?
- **F4** Umschalten schon nach dem Auslosen (`drawn`) oder erst ab dem Start? Empfehlung: ab `drawn`, Akku-Fenster
  erst ab `running`.
- **F5** Spielleitung: nur Vermerk oder unter 10 % auch unter „Braucht dich“?
- **F6** Wortlaut bei Übergabe an ein nicht verbundenes Handy („Jonas leitet jetzt das Team, sobald das Handy wieder
  verbunden ist.“); darf der Mitlese-Link Akku und „verbunden“ zeigen (Vorschlag: ja, nur eigenes Team)?
