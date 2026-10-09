# Umbau "Weiterentwicklung" Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Die Stadtjagd-App bekommt den Aufbau der freigegebenen Variante "Weiterentwicklung": am Handy Kopf mit Ziffern, feste Aktionsleiste und drei Tabs; in der Spielleitung Karte und Teamliste nebeneinander in voller Breite, mit "Braucht dich", "Zuletzt" und der Zeitachse als eigenem Reiter.

**Architecture:** Alles bleibt in `index.html` (ein Datei-Client, Vanilla JS, `render()` baut `#app` alle 10 s neu). Neue Hilfsfunktionen werden neben ihre heutigen Nachbarn gesetzt, die IDs, auf die `liveUpdate()`, `render()` und die Prüfskripte zugreifen (`#needle`, `#dist`, `#umkreis`, `#gnote`, `#tcheck`, `#tans`, `#tfin`, `#map`, `#tlrows`, `#tlslider`), bleiben unverändert. Am Server kommt nur ein Feld dazu (`failedAttempts` je Team in `admin_state`). Geprüft wird ohne Datenbank gegen `tools/pruefstand/mock.js` mit einem neuen Prüfskript `tools/pruefstand/umbau.py`, dazu die vorhandenen Prüfskripte und `shoot.py`.

**Tech Stack:** HTML/CSS/Vanilla JS, Leaflet 1.9.4 (unpkg), Supabase RPC (PostgreSQL plpgsql), Python 3 + Playwright (Kanal chrome) für den Prüfstand.

**Spec:** Freigegebene Mockups `mockups/design-varianten/v-weiter.html` (Handy: `#unterwegs`, `#raetsel`; Spielleitung: `#admin`) und `mockups/design-varianten/admin-karte.html` (Vergleich, Abschnitte "Was sich ändert" und "Was bleibt"); Entscheidung in `HANDOFF.md`, Abschnitt "Stand zum Fortsetzen (05.10.2026)". Die Mockups liegen lokal, nicht im Repo.

## Global Constraints

- Keine em-/en-dashes (U+2014/U+2013) in Texten, die Nutzer sehen; echte Umlaute; alle Dateien UTF-8.
- Kein Füll-Text in Oberflächen (TSE-CLAUDE.md, 05.10.2026): nur Fakt, Folge oder konkreter Schritt.
- Kennungen einzeilig: Team-Code, Uhrzeiten, Zeitspannen, "Station 2", Meter-Angaben mit `white-space: nowrap`.
- Animation 0,16 s, `cubic-bezier(.32,.72,.4,1)`; `prefers-reduced-motion` respektieren.
- Look bleibt: Token aus `design-system/MASTER.md` und `index.html` (`--paper`, `--card`, `--ink`, `--flag`, Barlow / Barlow Semi Condensed), Hell und Dunkel.
- Klickziele mindestens 44 px hoch am Handy, 42 px in der Spielleitung.
- Prüfskripte und `shoot.py` immer im Vordergrund mit `timeout` starten, nie im Hintergrund.
- Leaflet und OpenStreetMap bleiben die Karte der Spielleitung; das gezeichnete Kartenbild im Mockup ist Platzhalter.
- Nach jedem `create` einer SQL-Funktion die Rechte ausdrücklich setzen (SPIEL.md §9).

## Review Focus

- **Tastatur am Handy über der Aktionsleiste:** Beim Tippen der Antwort (`#tans`) oder des Koffer-Codes (`#tfin`) muss das Feld sichtbar bleiben, nicht hinter der Tastatur; Seite nicht seitlich verschoben. Test in Task 3.
- **Neuzeichnen alle 10 s:** Gewählter Tab am Handy, aufgeklapptes Team und gewähltes Team in der Spielleitung, Scrollposition der Teamliste und Kartenausschnitt dürfen beim `render()` nicht zurückspringen. Tests in Task 2 und Task 7.
- **Mitlesende (`teamAnsicht(st, true)`):** bekommen dieselbe Hülle, aber nie Eingabefelder in der Aktionsleiste; dort steht, wer eingibt. Test in Task 3.
- **Phasen ohne Station** (`drawn`, Gruppenselfie offen, `allSolved` am Koffer, Platz, `finished`): dürfen nicht leer aussehen und keine tote Aktionsleiste zeigen. Test in Task 3.
- **Team ohne Standort und mit altem Standort:** steht in "Braucht dich", ist auf der Karte als Knopf "kein Standort" erreichbar, und Auswählen springt nicht ins Leere. Test in Task 7.

---

## Dateien

- Modify: `index.html` (CSS-Block oben, `teamAnsicht()` ab Zeile ~1217, `viewTeam()`, `viewAdmin()` ab ~1767, `zustandHTML()`, `drawMap()` ab ~2062, `renderTimeline()`, `ACT` ab ~2285, `render()` ab ~3349)
- Create: `supabase/migrations/20261006090000_admin_fehlversuche.sql` (erzeugt von `tools/migration_admin_fehlversuche.py`)
- Create: `tools/migration_admin_fehlversuche.py`
- Create: `tools/pruefstand/admin_fehlversuche_db.py` (Probelauf mit Rücknahme, Muster `namenssuche_db.py`)
- Create: `tools/pruefstand/umbau.py` (Prüfskript ohne Datenbank, Muster `teststation.py`)
- Modify: `tools/pruefstand/mock.js` (Feld `failedAttempts`, neue Szenarien)
- Modify: `tools/pruefstand/shoot.py` (neue Szenarien in den Listen)
- Modify: `tools/pruefstand/README.md`, `HANDOFF.md`, `SPIEL.md` (Doku)

---

### Task 1: `admin_state` liefert Fehlversuche je Team

**Files:**
- Create: `tools/migration_admin_fehlversuche.py`, `supabase/migrations/20261006090000_admin_fehlversuche.sql`, `tools/pruefstand/admin_fehlversuche_db.py`
- Modify: `tools/pruefstand/mock.js` (Teams in `adminState()` bzw. dort, wo `admin_state` beantwortet wird)

**Interfaces:**
- Produces: jedes Element von `admin_state().teams` hat zusätzlich `failedAttempts` (int, 0 wenn nichts) und `lockedUntil` (timestamptz oder null) der aktuellen, ungelösten Station. Task 7 liest `t.failedAttempts`.

- [ ] **Step 1: Generator schreiben.** Er liest die jüngste Fassung von `admin_state` (heute in `supabase/migrations/20261002160000_kompass_waechter.sql`), fügt die zwei Felder hinter `"lastActivity"` ein und schreibt die Migration. So bleibt der Rest der Funktion Wort für Wort gleich.

```python
#!/usr/bin/env python3
"""Erzeugt supabase/migrations/20261006090000_admin_fehlversuche.sql aus der jüngsten admin_state-Fassung."""
import pathlib, re, sys
REPO = pathlib.Path(__file__).resolve().parent.parent
MIG = REPO / "supabase" / "migrations"
quellen = sorted(p for p in MIG.glob("*.sql") if "function admin_state(" in p.read_text(encoding="utf-8") and p.name < "20261006")
text = quellen[-1].read_text(encoding="utf-8")
m = re.search(r"create or replace function admin_state\(.*?\nend \$\$;", text, re.S)
if not m: sys.exit("admin_state nicht gefunden in " + quellen[-1].name)
fn = m.group(0)
anker = '             from progress pr where pr.team_id = t.id) as "lastActivity",\n'
if fn.count(anker) != 1: sys.exit("Anker lastActivity nicht eindeutig")
neu = anker + (
  "          -- Umbau Weiterentwicklung: Fehlversuche und Pause an der aktuellen Station, für \"Braucht dich\"\n"
  "          (select coalesce(pr.failed_attempts, 0) from stations s\n"
  "             left join progress pr on pr.station_id = s.id and pr.team_id = t.id\n"
  "             where pr.solved_at is null order by s.position limit 1) as \"failedAttempts\",\n"
  "          (select pr.locked_until from stations s\n"
  "             left join progress pr on pr.station_id = s.id and pr.team_id = t.id\n"
  "             where pr.solved_at is null order by s.position limit 1) as \"lockedUntil\",\n")
kopf = ("-- Umbau Weiterentwicklung (06.10.2026): admin_state liefert je Team failedAttempts und lockedUntil der\n"
        f"-- aktuellen Station. Erzeugt von tools/migration_admin_fehlversuche.py aus {quellen[-1].name}, nicht von Hand ändern.\n"
        "-- Probelauf: tools/pruefstand/admin_fehlversuche_db.py. Mehrfach ausführbar, löscht keine Daten.\n\n")
rechte = "\n\ngrant execute on function admin_state(text) to anon, authenticated;\n"
(MIG / "20261006090000_admin_fehlversuche.sql").write_text(kopf + fn.replace(anker, neu) + rechte, encoding="utf-8")
print("geschrieben aus", quellen[-1].name)
```

Vorher prüfen, mit welcher Signatur `admin_state` heute gewährt wird: `grep -n "grant execute on function admin_state" supabase/migrations/*.sql`. Steht dort eine andere Signatur als `(text)`, die `rechte`-Zeile anpassen.

- [ ] **Step 2: Probelauf schreiben (soll fehlschlagen, solange die Migration fehlt).** Muster `tools/pruefstand/namenssuche_db.py`; Kern:

```sql
do $probe$
declare v_pin text; r json; t_id uuid; s_id uuid; v_n int := 0;
begin
  execute $mig$__MIGRATION__$mig$;
  select admin_pin into v_pin from game_state where id = 1;
  r := admin_state(v_pin);
  if json_array_length(r->'teams') = 0 then
    insert into teams(name, code) values ('Probe', 'PROBE-' || upper(substr(md5(random()::text), 1, 6))) returning id into t_id;
    r := admin_state(v_pin);
  end if;
  if (r->'teams'->0) ? 'failedAttempts' is false then raise exception 'PROBE FEHLT A1: kein failedAttempts'; end if;
  if (r->'teams'->0->>'failedAttempts') is null then raise exception 'PROBE FEHLT A2: failedAttempts null statt 0'; end if;
  v_n := v_n + 2;
  -- B: Fehlversuche an der ersten ungelösten Station kommen an
  t_id := coalesce(t_id, (r->'teams'->0->>'id')::uuid);
  select s.id into s_id from stations s left join progress pr on pr.station_id = s.id and pr.team_id = t_id
    where pr.solved_at is null order by s.position limit 1;
  insert into progress(team_id, station_id, failed_attempts) values (t_id, s_id, 2)
    on conflict (team_id, station_id) do update set failed_attempts = 2;
  r := admin_state(v_pin);
  if not exists (select 1 from json_array_elements(r->'teams') e where (e->>'id')::uuid = t_id and (e->>'failedAttempts')::int = 2)
    then raise exception 'PROBE FEHLT B1: Fehlversuche kommen nicht an'; end if;
  v_n := v_n + 1;
  if not has_function_privilege('anon', 'admin_state(text)', 'execute') then raise exception 'PROBE FEHLT C1: anon darf admin_state nicht'; end if;
  v_n := v_n + 1;
  raise exception 'PROBELAUF_OK: % Prüfungen bestanden, alles zurückgenommen', v_n;
end $probe$;
```

Vor dem Schreiben prüfen: `progress` hat einen eindeutigen Schlüssel auf `(team_id, station_id)` (`grep -n "unique\|primary key" supabase/migrations/20260918120000_init.sql`); sonst `on conflict` durch `update ... where` plus `insert ... where not exists` ersetzen.

- [ ] **Step 3: Probelauf ohne Migration.** `timeout 120 python tools/pruefstand/admin_fehlversuche_db.py` → erwartet: Abbruch, weil die Migrationsdatei fehlt (FileNotFoundError).
- [ ] **Step 4: Migration erzeugen.** `python tools/migration_admin_fehlversuche.py`, dann `timeout 120 python tools/pruefstand/admin_fehlversuche_db.py` → erwartet `PROBELAUF_OK: 4 Prüfungen bestanden`.
- [ ] **Step 5: Mock nachziehen.** In `tools/pruefstand/mock.js` dort, wo die Teams für `admin_state` gebaut werden, `failedAttempts` und `lockedUntil` setzen: Standard 0/null; in den Teams, die schon Fehlversuche zeigen sollen, Werte aus dem Szenario (Otter: 2). Prüfen mit `timeout 300 python tools/pruefstand/shoot.py admin-teams` → keine neuen Meldungen.
- [ ] **Step 6: Einspielen (live).** `timeout 120 python tools/sql.py supabase/migrations/20261006090000_admin_fehlversuche.sql`, danach `python tools/sql.py --read-only -c "select json_array_length(admin_state((select admin_pin from game_state where id=1))->'teams')"` → Zahl, kein Fehler.
- [ ] **Step 7: Commit.** `git add tools/migration_admin_fehlversuche.py supabase/migrations/20261006090000_admin_fehlversuche.sql tools/pruefstand/admin_fehlversuche_db.py tools/pruefstand/mock.js && git commit -m "admin_state: Fehlversuche und Pause je Team (für Braucht dich)"`

---

### Task 2: Handy-Hülle mit drei Tabs

**Files:**
- Modify: `index.html` (CSS-Block; `teamAnsicht()`; `S` um `team.tab`; `ACT`)
- Create: `tools/pruefstand/umbau.py`
- Modify: `tools/pruefstand/mock.js` (nichts Neues nötig, nutzt `leitung-unterwegs`, `leitung-raetsel`, `mitglied-unterwegs`)

**Interfaces:**
- Produces: `S.team.tab` ∈ `"weg" | "ziffern" | "team"` (Standard `"weg"`); `huelleHTML({ kopf, inhalt, leiste, tabs })` liefert das Gerüst `<div class="ph"><header class="kopf">…</header><main class="inhalt" id="inhalt">…</main><div class="leiste" id="leiste">…</div><nav class="ftabs" role="tablist">…</nav></div>`; `tabsHTML(st)`; ACT-Handler `"t-tab"` (liest `data-tab`). Task 3 füllt `leiste`, Task 4 füllt `kopf`, Task 5 füllt Tab "team".

- [ ] **Step 1: Prüfskript anlegen, Teil Handy-Hülle.** Gerüst wie `tools/pruefstand/teststation.py` (Server auf Port 8840, `pruef()`, am Ende `OK` oder Liste `FEHLT`), Profil 390×844:

```python
print("Handy, Teamleitung unterwegs")
pg.goto(f"{BASIS}/app.html?szenario=leitung-unterwegs"); pg.wait_for_selector(".ph")
pruef(pg.locator(".ph > .kopf").count() == 1 and pg.locator(".ph > .inhalt").count() == 1, "Hülle mit Kopf und Inhalt")
tabs = pg.locator(".ftabs [role=tab]")
pruef(tabs.count() == 3 and [tabs.nth(i).inner_text().split("\n")[0] for i in range(3)] == ["Weg", "Ziffern", "Team"], "drei Tabs Weg, Ziffern, Team")
pruef(pg.locator("#needle").count() == 1 and pg.locator("#dist").count() == 1, "Kompass und Entfernung im Tab Weg")
pg.click(".ftabs [data-tab=team]")
pruef(pg.locator("#needle").count() == 0, "Tab Team ohne Kompass")
pg.evaluate("render()")                      # die 10-s-Abfrage zeichnet neu
pruef(pg.get_attribute(".ftabs [data-tab=team]", "aria-selected") == "true", "Tab bleibt nach render() gewählt")
box = pg.locator(".ftabs").bounding_box()
pruef(abs(box["y"] + box["height"] - 844) < 2, "Tabs kleben unten")
pruef(pg.evaluate("document.documentElement.scrollWidth") <= 390, "kein seitliches Scrollen")
print("Handy, Teamleitung Rätsel")
pg.goto(f"{BASIS}/app.html?szenario=leitung-raetsel"); pg.wait_for_selector(".ph")
pruef(pg.inner_text(".ftabs [data-tab=weg]").startswith("Rätsel"), "erster Tab heißt im Rätsel 'Rätsel'")
```

- [ ] **Step 2: Laufen lassen, erwartet FEHLT.** `timeout 300 python tools/pruefstand/umbau.py` → "FEHLT Hülle mit Kopf und Inhalt" usw.
- [ ] **Step 3: CSS ergänzen** (nach dem `.tabs`-Block um Zeile 206; Werte aus `v-weiter.html` Zeilen 116 bis 228, Namen ohne Kollision mit den bestehenden `.tabs` der Spielleitung, daher `.ftabs`):

```css
/* Handy im Spiel: Kopf, Inhalt, Aktionsleiste, Tabs (Umbau Weiterentwicklung) */
body.spiel{height:100vh;height:100dvh;overflow:hidden}
body.spiel main{max-width:none;padding:0}
.ph{position:relative;z-index:1;height:100vh;height:100dvh;max-width:560px;margin:0 auto;display:grid;grid-template-columns:minmax(0,1fr);grid-template-rows:auto minmax(0,1fr) auto auto}
.ph > .kopf{background:var(--card);border-bottom:1px solid var(--line);padding:10px 16px 8px}
.ph > .inhalt{overflow-y:auto;overscroll-behavior:contain;padding:14px 16px 20px}
.ph > .inhalt > .panel:first-child{margin-top:0}
.ph > .leiste{background:var(--card);border-top:1px solid var(--line);padding:10px 16px 12px}
.ph > .leiste:empty{display:none}
.ph > .leiste .btn{margin-top:0}
.ftabs{display:grid;grid-template-columns:repeat(3,1fr);background:var(--card);border-top:1px solid var(--line);padding-bottom:env(safe-area-inset-bottom)}
.ftabs button{position:relative;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:1px;min-height:58px;border:0;background:none;color:var(--muted);font:600 var(--fs-xs)/1.2 var(--body);cursor:pointer}
.ftabs button svg{width:24px;height:24px}
.ftabs button[aria-selected="true"]{color:var(--ink)}
.ftabs button[aria-selected="true"]::before{content:"";position:absolute;top:-1px;left:30%;right:30%;height:3px;border-radius:99px;background:var(--flag)}
.ftabs .badge{position:absolute;top:6px;left:calc(50% + 10px);min-width:22px;padding:0 5px;border-radius:99px;background:var(--paper);border:1px solid var(--line);font:700 11px/16px var(--body);color:var(--ink);font-variant-numeric:tabular-nums;white-space:nowrap}
```

- [ ] **Step 4: Zustand und Tabs.** In `S.team` den Eintrag `tab: "weg"` ergänzen (Objekt um Zeile 561). Neue Funktionen direkt vor `teamAnsicht()`:

```js
// Umbau Weiterentwicklung: das Spiel am Handy als feste Hülle. Kopf und Tabs stehen, nur der Inhalt scrollt.
const TAB_ICON = {
  weg: '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" stroke-width="2"/><path d="M12 6l3 8-3-2-3 2z" fill="currentColor"/></svg>',
  raetsel: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 9a3 3 0 1 1 4 2.8c-.7.3-1 .9-1 1.6V15" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><circle cx="12" cy="18.5" r="1.2" fill="currentColor"/></svg>',
  ziffern: '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="5" y="10" width="14" height="10" rx="2" fill="none" stroke="currentColor" stroke-width="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3" fill="none" stroke="currentColor" stroke-width="2"/></svg>',
  team: '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="9" cy="9" r="3" fill="none" stroke="currentColor" stroke-width="2"/><circle cx="17" cy="10" r="2.5" fill="none" stroke="currentColor" stroke-width="2"/><path d="M3 19c.8-3 3.2-4.5 6-4.5s5.2 1.5 6 4.5M15 15c2.6 0 4.6 1.3 5.5 4" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>'
};
function tabsHTML(st) {
  const raetsel = !!(st.station && st.checkedIn);
  const g = (st.digits || []).filter(d => d != null).length;
  const tabs = [["weg", raetsel ? "Rätsel" : "Weg", raetsel ? TAB_ICON.raetsel : TAB_ICON.weg, ""],
    ["ziffern", "Ziffern", TAB_ICON.ziffern, `${g}/${st.totalStations}`],
    ["team", "Team", TAB_ICON.team, String((st.team.members || []).length)]];
  return `<nav class="ftabs" role="tablist" aria-label="Bereiche">${tabs.map(([id, txt, ic, b]) =>
    `<button role="tab" data-act="t-tab" data-tab="${id}" aria-selected="${(S.team.tab || "weg") === id}">${ic}<span>${txt}</span>${b ? `<span class="badge">${b}</span>` : ""}</button>`).join("")}</nav>`;
}
function huelleHTML(teile) {
  return `<div class="ph"><header class="kopf">${teile.kopf}</header><main class="inhalt" id="inhalt">${teile.inhalt}</main>
    <div class="leiste" id="leiste">${teile.leiste || ""}</div>${teile.tabs}</div>`;
}
```

In `ACT` (alphabetisch neben `"t-gps"`): `"t-tab"(d) { S.team.tab = d.tab; const i = $("#inhalt"); if (i) i.scrollTop = 0; },` (wie die anderen Handler liest er `d` = `dataset` des Knopfs; vor dem Einfügen an einem vorhandenen Handler prüfen, wie der Parameter heißt, und denselben Stil nehmen).

- [ ] **Step 5: `teamAnsicht()` aufteilen.** Nur für den laufenden Teil mit Station (die `if (!st.checkedIn) { … } else { … }`-Zweige, Zeilen ~1293 bis 1353) die Hülle nutzen. Die bisherige Zeichenkette `out` aus diesen Zweigen wird zu `weg`; Ziffern-Panel (`unterwegs`) und Mitgliederzeile wandern in die Tabs:

```js
  // Tab Ziffern: Schloss, Route und Erklärung der Schlussziffer
  const zifferTab = `<div class="panel ziffern"><div class="bar"><h3>Eure Ziffern</h3>
    <span class="small muted nw">${st.solvedCount} von ${st.totalStations}</span></div>${lockHTML(st)}${routeHTML(st)}
    <p class="small muted" style="margin-top:6px">Die abgesetzte letzte Ziffer ist die Schlussziffer: die Einerstelle der Summe ${summeText(st)}.</p></div>`;
  const tab = S.team.tab || "weg";
  const inhalt = tab === "ziffern" ? zifferTab : tab === "team" ? teamTabHTML(st, lesen) : weg;
  document.body.classList.add("spiel");
  return huelleHTML({ kopf: kopfHTML(st, lesen), inhalt, leiste: leisteHTML(st, s, lesen), tabs: tabsHTML(st) });
```

Für diesen Task gelten Zwischenfassungen, die Task 3 bis 5 ersetzen:
`function kopfHTML(st, lesen) { return `<h1>${teamEmoji(st.team.name)} Team ${esc(st.team.name)}</h1>`; }`,
`function leisteHTML() { return ""; }`,
`function teamTabHTML(st) { return `<div class="panel"><ul class="names">${(st.team.members || []).map(m => `<li>${esc(m)}</li>`).join("")}</ul></div>`; }`.
Knöpfe und Formulare bleiben in diesem Task noch im Inhalt von `weg`.

In `render()` vor `app.innerHTML = …` die Klasse zurücksetzen, damit andere Ansichten normal scrollen: `document.body.classList.remove("spiel");`.

- [ ] **Step 6: Prüfen.** `timeout 300 python tools/pruefstand/umbau.py` → alle Punkte aus Step 1 `ok`. Dann `timeout 300 python tools/pruefstand/kritik.py` und `timeout 300 python tools/pruefstand/waechter.py` → `OK`.
- [ ] **Step 7: Commit.** `git add index.html tools/pruefstand/umbau.py && git commit -m "Handy: Hülle mit Kopf, Inhalt und drei Tabs (Umbau Weiterentwicklung)"`

---

### Task 3: Aktionsleiste

**Files:**
- Modify: `index.html` (`leisteHTML()`, Zweige in `teamAnsicht()`, `<meta name="viewport">`)
- Modify: `tools/pruefstand/umbau.py`

**Interfaces:**
- Consumes: `huelleHTML`, `S.team.tab` aus Task 2.
- Produces: `leisteHTML(st, s, lesen)` → HTML der Leiste; Einchecken (`#tcheck`, `data-act="t-check"`), Antwort (`#tans` + `data-act="t-answer"`), Koffer (`#tfin` + `data-act="t-final"`) stehen nur noch dort.

- [ ] **Step 1: Prüfpunkte ergänzen.**

```python
print("Aktionsleiste")
pg.goto(f"{BASIS}/app.html?szenario=leitung-unterwegs"); pg.wait_for_selector(".ph")
pruef(pg.locator("#leiste #tcheck").count() == 1 and pg.locator("#inhalt #tcheck").count() == 0, "Einchecken steht in der Leiste")
pg.click(".ftabs [data-tab=team]")
pruef(pg.locator("#leiste #tcheck").count() == 1, "Leiste bleibt in jedem Tab")
pg.goto(f"{BASIS}/app.html?szenario=leitung-raetsel"); pg.wait_for_selector("#leiste #tans")
pg.click("#tans"); pg.keyboard.type("527")
r = pg.locator("#tans").bounding_box()
pruef(r["y"] + r["height"] <= 844 and pg.evaluate("document.documentElement.scrollWidth") <= 390, "Antwortfeld sichtbar, nichts seitlich verschoben")
pg.evaluate("render()")
pruef(pg.input_value("#tans") == "527", "Getipptes übersteht render()")
pg.goto(f"{BASIS}/app.html?szenario=mitglied-raetsel"); pg.wait_for_selector(".ph")
pruef(pg.locator("#leiste input").count() == 0 and "gibt" in pg.inner_text("#leiste"), "Mitlesende: keine Eingabe, Leiste sagt wer eingibt")
for sz in ["leitung-startklar", "leitung-koffer", "leitung-platz2", "leitung-beendet", "selfie-offen"]:
    pg.goto(f"{BASIS}/app.html?szenario={sz}"); pg.wait_for_selector("#app > *")
    leer = pg.evaluate("(() => { const l = document.querySelector('#leiste'); return !!l && l.innerText.trim() === '' && getComputedStyle(l).display !== 'none'; })()")
    pruef(not leer and not err, f"{sz}: keine leere Leiste, keine Fehler")
```

- [ ] **Step 2: Laufen lassen, erwartet FEHLT** bei "Einchecken steht in der Leiste" und folgenden.
- [ ] **Step 3: Viewport.** In `<head>` den Viewport auf `width=device-width, initial-scale=1, viewport-fit=cover, interactive-widget=resizes-content` setzen (so verkleinert Android/Chrome das Layout beim Öffnen der Tastatur; iOS verschiebt selbst, die Leiste bleibt im Grid unten).
- [ ] **Step 4: `leisteHTML()`** ersetzt die Zwischenfassung. Inhalte kommen 1:1 aus den heutigen Zweigen in `teamAnsicht()` (Zeilen ~1306 bis 1311 Einchecken, ~1342 bis 1346 Antwort, ~1278 bis 1282 Koffer):

```js
// Die eine Handlung, die gerade dran ist, steht immer unten. Mitlesende sehen dort, wer sie macht.
function leisteHTML(st, s, lesen) {
  const leitung = vorname(st.team.leaderName) || "eure Teamleitung";
  const ichSelbst = lesen && st.name && st.name === st.team.leaderName;
  if (lesen) return ichSelbst ? `<a class="btn" href="#/team">Zur Teamleitung</a>`
    : `<p class="small" style="margin:0">${st.allSolved ? "Den Koffer-Code" : s && st.checkedIn ? "Die Antwort" : "Einchecken"} gibt <b>${esc(leitung)}</b> ein.</p>`;
  if (st.allSolved) {
    const left = st.prizesLeft ?? 0;
    return `<label for="tfin">Koffer-Code, <span class="nw">${ANZ(st) + 1} Stellen</span></label>
      <div class="reihe"><input id="tfin" inputmode="numeric" pattern="[0-9]*" maxlength="${ANZ(st) + 1}" autocomplete="off" enterkeyhint="go">
      <button class="btn" data-act="t-final" data-wait="Standort wird bestimmt …" ${S.busy ? "disabled" : ""}>${left ? "Koffer öffnen" : "Code eingeben"}</button></div>${msgBox("leiste")}`;
  }
  if (!s) return "";
  if (st.checkedIn) {
    const pause = !st.testMode && st.lockedUntil && new Date(st.lockedUntil).getTime() > Date.now();
    return `<label for="tans">Eure Antwort</label>
      <div class="reihe"><input id="tans" ${s.numeric ? 'inputmode="numeric" pattern="[0-9]*"' : ""} autocomplete="off" autocorrect="off" autocapitalize="off" spellcheck="false" enterkeyhint="send" ${pause ? "disabled" : ""}>
      <button class="btn" data-act="t-answer" data-wait="Wird geprüft …" ${S.busy || pause ? "disabled" : ""}>Prüfen</button></div>
      ${pause ? "" : `<p class="small muted nw" style="margin:6px 0 0">${st.testMode ? "Testmodus: jede Antwort zählt" : `Fehlversuche: ${st.failedAttempts} von 3`}</p>`}${msgBox("leiste")}`;
  }
  const g = S.gps, hasTarget = s.lat != null && s.lng != null;
  if (!g.on && !st.testMode) return `<button class="btn" data-act="t-gps">Standort und Kompass freigeben</button>`;
  return `<button class="btn ${checkWeit(st, s) ? "weit" : ""}" id="tcheck" data-act="t-check" data-wait="Standort wird bestimmt …" ${S.busy || (!st.testMode && (!hasTarget || !g.pos)) ? "disabled" : ""}>${checkText(st, s)}</button>${msgBox("leiste")}`;
}
```

CSS dazu: `.ph > .leiste .reihe{display:flex;gap:8px;align-items:stretch}.ph > .leiste .reihe input{flex:1;min-width:0;min-height:52px}.ph > .leiste .reihe .btn{width:auto;flex:none;min-width:120px}`.

- [ ] **Step 5: Fehlermeldungen an die Leiste hängen.** Die Handler `t-check`, `t-answer`, `t-final` setzen heute `S.msg` ohne `ort`; damit die Meldung am Knopf steht, in diesen drei Handlern `ort: "leiste"` ergänzen (Suche: `grep -n '"t-check"\|"t-answer"\|"t-final"' index.html`, dann in jedem `S.msg = { … }` des Handlers). Im Inhalt bleiben Erfolgsmeldungen (`okOben`) wie heute.
- [ ] **Step 6: Aus dem Inhalt entfernen,** was jetzt in der Leiste steht: den Einchecken-Knopf samt Hinweis "Sobald der Standort da ist …" (bleibt als Satz unter der Entfernung), das Antwortfeld mit Knopf, das Koffer-Feld. Phasen ohne Station (`drawn`, `place`, `finished`, Selfie) bekommen die Hülle nicht; dort bleibt die Seite wie heute (lange Seite, `nav()`), damit keine leere Leiste entsteht. Die Hülle gilt für: laufend mit Station und `allSolved`.
- [ ] **Step 7: Prüfen.** `timeout 300 python tools/pruefstand/umbau.py`, `timeout 300 python tools/pruefstand/selfie.py`, `timeout 300 python tools/pruefstand/teststation.py`, `timeout 300 python tools/pruefstand/bugjagd2.py` → alle `OK`. Melden die alten Skripte, dass ein Knopf nicht gefunden wird, den Selektor im Skript auf `#leiste …` anpassen, nicht die App.
- [ ] **Step 8: Commit.** `git add index.html tools/pruefstand/*.py && git commit -m "Handy: Aktionsleiste unten (Einchecken, Antwort, Koffer), Mitlesende sehen wer eingibt"`

---

### Task 4: Kopf mit Ziffern und Hilfe

**Files:**
- Modify: `index.html` (`kopfHTML()`, ACT `"t-hilfe"`, `"t-hilfe-zu"`, CSS)
- Modify: `tools/pruefstand/umbau.py`

**Interfaces:**
- Consumes: `lockHTML(st, klein)` (heute Zeile ~1068), `helpBtn(text)` (~820), `uhrHTML(st)` (~1047).
- Produces: `kopfHTML(st, lesen)`; `S.team.hilfe` (bool) öffnet ein Blatt mit WhatsApp/Anrufen.

- [ ] **Step 1: Prüfpunkte.**

```python
print("Kopf")
pg.goto(f"{BASIS}/app.html?szenario=leitung-unterwegs"); pg.wait_for_selector(".kopf")
k = pg.inner_text(".kopf")
pruef("Team Fuchs" in k and "Noch" in k, "Kopf: Teamname und Restzeit")
pruef(pg.locator(".kopf .minilock").count() == 1, "Kopf: Ziffern klein")
pg.click(".kopf .minilock")
pruef(pg.get_attribute(".ftabs [data-tab=ziffern]", "aria-selected") == "true", "Ziffern im Kopf öffnen den Tab Ziffern")
pg.click(".kopf [data-act=t-hilfe]")
pruef(pg.locator(".blatt a[href^='https://wa.me'], .blatt a[href^='tel:']").count() >= 1, "Hilfe öffnet ein Blatt mit WhatsApp oder Anrufen")
pg.keyboard.press("Escape")
pruef(pg.locator(".blatt").count() == 0, "Escape schließt das Blatt")
```

- [ ] **Step 2: Laufen lassen, erwartet FEHLT.**
- [ ] **Step 3: `kopfHTML()`** (ersetzt die Zwischenfassung):

```js
function kopfHTML(st, lesen) {
  const leitung = st.team.leaderName === S.myName && !lesen ? "Du leitest das Team" : `Teamleitung: ${esc(st.team.leaderName || "offen")}`;
  return `<div class="k1">${logo()}<span class="tiertop" aria-hidden="true">${teamEmoji(st.team.name)}</span>
      <div class="tn"><h1>Team ${esc(st.team.name)}</h1><span class="sub">${leitung}</span></div>
      ${helpHref("") ? `<button class="hilfe-btn" data-act="t-hilfe">Hilfe</button>` : ""}${themaBtn()}</div>
    <div class="k2">${uhrHTML(st)}<span class="chip uhr knapp" id="stand" hidden></span>
      <button class="minilock" data-act="t-tab" data-tab="ziffern" aria-label="Eure Ziffern: ${st.solvedCount} von ${st.totalStations}. Antippen zeigt alle.">
        <span class="lbl">Ziffern</span>${lockHTML(st, true)}</button></div>
    ${st.testMode ? `<div class="msg warn" style="margin:8px 0 0">Testmodus: Entfernung und Antworten werden nicht geprüft.</div>` : ""}`;
}
```

Vorher `helpHref` (Zeile ~809) lesen: liefert es ohne hinterlegte Hilfe-Nummer etwas Leeres, entfällt der Knopf; sonst Bedingung an die dortige Logik anpassen. CSS aus `v-weiter.html` Zeilen 119 bis 130 übernehmen (`.k1`, `.tiertop`, `.tn`, `.hilfe-btn`, `.k2`, `.minilock`), Präfix `.ph > .kopf`; `.minilock .lock` auf 22 px Radhöhe begrenzen.

- [ ] **Step 4: Hilfe-Blatt.** `S.team.hilfe` = true zeigt am Ende von `huelleHTML` `<div class="ueber" data-act="t-hilfe-zu"><div class="blatt" role="dialog" aria-modal="true" aria-labelledby="hilfe-t"><h2 id="hilfe-t">Hilfe von der Spielleitung</h2>${helpBtn(text)}<button class="link" data-act="t-hilfe-zu">Schließen</button></div></div>` mit `text` wie heute je Phase (Zeilen ~1352 f.). ACT: `"t-hilfe"() { S.team.hilfe = true; }`, `"t-hilfe-zu"(d, e) { if (e && e.target.closest(".blatt") && !e.target.closest("[data-act=t-hilfe-zu]")) return; S.team.hilfe = false; }` (Signatur an den vorhandenen ACT-Aufruf anpassen; prüfen, ob der Event-Parameter übergeben wird). Escape: im vorhandenen `keydown`-Listener `if (e.key === "Escape" && S.team.hilfe) { S.team.hilfe = false; render(); }`. CSS: `.ueber{position:fixed;inset:0;z-index:50;background:rgba(15,27,24,.45);display:flex;align-items:flex-end;justify-content:center;animation:ein .16s cubic-bezier(.32,.72,.4,1)}.blatt{width:100%;max-width:560px;background:var(--card);border-radius:14px 14px 0 0;padding:20px 16px calc(16px + env(safe-area-inset-bottom))}`; `@keyframes ein` nur anlegen, wenn es ihn noch nicht gibt.
- [ ] **Step 5: Den alten Kopf** (`<div class="bar">…<h1>…` Zeile ~1223) und den Testmodus-Hinweis im Inhalt für die Hülle weglassen; den `helpBtn` am Seitenende (Zeile ~1352) im Hüllen-Fall weglassen.
- [ ] **Step 6: Prüfen.** `timeout 300 python tools/pruefstand/umbau.py`, `timeout 300 python tools/pruefstand/kritik.py` → `OK`.
- [ ] **Step 7: Commit.** `git commit -am "Handy: Kopf mit Ziffern, Restzeit und Hilfe-Blatt"`

---

### Task 5: Tab Team

**Files:**
- Modify: `index.html` (`teamTabHTML()`)
- Modify: `tools/pruefstand/umbau.py`

**Interfaces:**
- Consumes: `mitlesePanelHTML(st, text)`, `leitungHTML(st, ohneMit)`, `abmeldenHTML()`, `albumHTML(st)`, `themaBtn()`.
- Produces: `teamTabHTML(st, lesen)`.

- [ ] **Step 1: Prüfpunkte.**

```python
print("Tab Team")
pg.goto(f"{BASIS}/app.html?szenario=leitung-unterwegs"); pg.wait_for_selector(".ph"); pg.click(".ftabs [data-tab=team]")
t = pg.inner_text("#inhalt")
pruef("Mitlesen fürs Team" in t and "Anna Berger" in t and "Abmelden" in t, "Teamleitung: Mitlese-Link, Mitglieder, Abmelden")
pg.goto(f"{BASIS}/app.html?szenario=mitglied-unterwegs"); pg.wait_for_selector(".ph"); pg.click(".ftabs [data-tab=team]")
t = pg.inner_text("#inhalt")
pruef("Mitlesen fürs Team" not in t and "Abmelden" not in t and "Anna Berger" in t, "Mitlesende: nur Mitglieder")
```

- [ ] **Step 2: Laufen lassen, erwartet FEHLT.**
- [ ] **Step 3: Umsetzen.**

```js
function teamTabHTML(st, lesen) {
  const mitglieder = `<div class="panel"><h3>Mitglieder <span class="small muted nw">${(st.team.members || []).length}</span></h3>
    <ul class="names">${(st.team.members || []).map(m => `<li>${esc(m)}${m === st.team.leaderName ? ' <span class="chip">Teamleitung</span>' : ""}</li>`).join("")}</ul></div>`;
  return (lesen ? "" : mitlesePanelHTML(st, "Wer diesen Link öffnet, sieht auf dem eigenen Handy alles mit: Station, Rätsel, Ziffern. Eingeben kannst nur du."))
    + mitglieder + albumHTML(st) + (lesen ? "" : leitungHTML(st, true) + abmeldenHTML());
}
```

In `teamAnsicht()` im Hüllen-Fall `ende` (Album, Leitung, Abmelden, `nav()`) nicht mehr an den Weg-Tab hängen.
- [ ] **Step 4: Prüfen.** `timeout 300 python tools/pruefstand/umbau.py`, `timeout 300 python tools/pruefstand/selfie.py` → `OK`.
- [ ] **Step 5: Commit.** `git commit -am "Handy: Tab Team mit Mitlese-Link, Mitgliedern, Album, Leitung abgeben und Abmelden"`

---

### Task 6: Spielleitung in voller Breite, Reiter "Karte und Teams", Zeitachse eigener Reiter

**Files:**
- Modify: `index.html` (`viewAdmin()`, `render()`, `S.admin.tab`-Standard, CSS)
- Modify: `tools/pruefstand/umbau.py`, `tools/pruefstand/mock.js` (Szenarien, die `tab` setzen)

**Interfaces:**
- Produces: Reiter-Schlüssel `"live"` (Karte und Teams), `"zeit"`, `"teams"` bleibt für Auslosen/Start vor dem Spiel, `"people"`, `"stations"`, `"fotos"`, `"danger"`; Layout `<div class="lv"><section class="kartefeld"><div id="map"></div>…</section><section class="teamfeld" id="teamfeld">…</section></div>`. Task 7 füllt `#teamfeld`, Task 8 die Ereignisliste.

- [ ] **Step 1: Prüfpunkte** (Profil 1440×900 und 820×1180):

```python
print("Spielleitung, Karte und Teams")
pg.set_viewport_size({"width": 1440, "height": 900})
pg.goto(f"{BASIS}/app.html?szenario=admin-karte"); pg.wait_for_selector("#map .leaflet-marker-icon", timeout=25000)
reiter = [x.strip() for x in pg.locator(".tabs [role=tab]").all_inner_texts()]
pruef(reiter[:2] == ["Karte und Teams", "Zeitachse"], f"Reiter: {reiter}")
m, l = pg.locator("#map").bounding_box(), pg.locator("#teamfeld").bounding_box()
pruef(l["x"] > m["x"] + m["width"] - 2 and abs(l["y"] - m["y"]) < 40, "Teamliste rechts neben der Karte")
pruef(pg.locator("#app").bounding_box()["width"] > 1300, "volle Breite")
pruef(pg.locator("#tlrows").count() == 0, "Zeitachse nicht mehr unter der Karte")
pg.click("[data-act=a-tab][data-tab=zeit]"); pg.wait_for_selector("#tlrows")
pruef(pg.locator("#tlslider").count() == 1, "Zeitachse mit Schieber im eigenen Reiter")
pg.set_viewport_size({"width": 820, "height": 1180})
pg.goto(f"{BASIS}/app.html?szenario=admin-karte"); pg.wait_for_selector("#teamfeld")
m, l = pg.locator("#map").bounding_box(), pg.locator("#teamfeld").bounding_box()
pruef(l["y"] >= m["y"] + m["height"] - 2, "Tablet hoch: Liste unter der Karte")
```

- [ ] **Step 2: Laufen lassen, erwartet FEHLT.**
- [ ] **Step 3: Reiter und Standard.** In `S.admin` `tab: "map"` → `tab: "live"`. Reiterliste in `viewAdmin()`:

```js
  const laeuft = st.status === "running" || st.status === "finished";
  const tabs = [["live", "Karte und Teams"], ["zeit", "Zeitachse"], ...(laeuft ? [] : [["teams", "Auslosen"]]),
    ["people", "Teilnehmende"], ["stations", "Stationen"], ["fotos", "Fotos"], ["danger", "Daten löschen"]];
```

Vor dem Start bleibt "Auslosen" (der heutige Reiter Teams mit Auslosen und "Bereit zum Start"); im Spiel entfällt er, die Tabelle wird durch die Teamliste in "Karte und Teams" ersetzt. Ist `A.tab === "teams"` und das Spiel läuft (alter gemerkter Zustand), auf `"live"` setzen. `"danger"` bekommt `class="loesch"` und `margin-left:auto`.

- [ ] **Step 4: Inhalt "live".** Der heutige Block `if (A.tab === "map")` wird zu:

```js
  if (A.tab === "live") {
    const withPos = (st.teams || []).filter(t => t.position);
    out += `<div class="lv"><section class="kartefeld">
        <div id="map" class="${A.full ? "full" : ""}"></div>
        <button class="btn sm kartezu" data-act="a-full" ${A.full ? "" : "hidden"}>Vollbild beenden</button>
        <div class="bar kartefuss"><span class="small muted"><b class="nw">${withPos.length} von ${(st.teams || []).length}</b> Teams mit Standort, alle 10 s. Gestrichelt: Strecke ohne GPS-Signal.</span>
          <span><button class="btn sm alt" data-act="a-alle">Alle zeigen</button><button class="btn sm alt" data-act="a-full">Vollbild</button></span></div>
        <div class="legend" id="legend">${(st.teams || []).map((t, i) => `<button class="tchip ${A.hidden[t.id] ? "off" : ""}" style="--c:${teamColor(i)}" data-act="a-team" data-id="${t.id}"><i></i>${teamEmoji(t.name)} ${esc(t.name)}</button>`).join("")}</div>
        <div class="panel" id="zuletzt"></div>
      </section><section class="teamfeld panel" id="teamfeld">${teamlisteHTML(st)}</section></div>`;
  }
  if (A.tab === "zeit") out += `<div class="panel"><div class="bar"><h3>Zeitachse</h3><span class="small muted" id="tlspan"></span></div>…`;   // der bisherige Zeitachsen-Block unverändert
```

Zwischenfassung für diesen Task: `function teamlisteHTML(st) { return `<h3>Teams</h3>`; }` (Task 7 ersetzt sie). Der bisherige Zeitachsen-Block (`<div class="panel"><div class="bar"><h3>Zeitachse</h3>…</div>`, Zeilen ~1801 bis 1810) zieht wörtlich in den Reiter `"zeit"`; der letzte Satz "Ein Teamname antippen …" bleibt dort.

- [ ] **Step 5: `render()` anpassen.** `app.className = S.view === "admin" && S.admin.pin ? "voll" : "";` und:

```js
  if (S.view === "admin" && S.admin.pin && (S.admin.tab === "live" || S.admin.tab === "zeit")) {
    if (S.admin.tab === "live") drawMap(true); else renderTimeline();
    syncTracks().then(() => { if (S.admin.tab === "live") { drawMap(false); zuletztZeichnen(); } else renderTimeline(); }).catch(() => { });
  }
```

Zwischenfassung: `function zuletztZeichnen() {}` (Task 8). Alle anderen Stellen, die `tab === "map"` abfragen, finden und umstellen: `grep -n 'tab === "map"\|tab: "map"\|data-tab="map"' index.html tools/pruefstand/*.js tools/pruefstand/*.py`.

- [ ] **Step 6: CSS.**

```css
main.voll{max-width:1680px;padding:16px 24px 40px}
.lv{display:grid;grid-template-columns:minmax(0,1fr) minmax(360px,440px);gap:16px;align-items:start;margin-top:14px}
.lv .kartefeld #map{height:calc(100vh - 230px);min-height:420px}
.teamfeld{margin-top:0;position:sticky;top:12px;max-height:calc(100vh - 24px);overflow:auto;padding:0}
@media (max-width:1023px){.lv{grid-template-columns:minmax(0,1fr)}.lv .kartefeld #map{height:56vh}.teamfeld{position:static;max-height:none}}
.tabs .loesch{margin-left:auto;color:var(--err)}
```

Vorher prüfen, welche Höhe `#map` heute hat (`grep -n "#map{" index.html`) und die neue Regel nur für `.lv` setzen.

- [ ] **Step 7: Mock-Szenarien.** In `tools/pruefstand/mock.js` Szenarien mit `tab: "map"` auf `"live"` und mit `tab: "teams"` im laufenden Spiel auf `"live"` setzen (`grep -n 'tab' tools/pruefstand/mock.js`).
- [ ] **Step 8: Prüfen.** `timeout 300 python tools/pruefstand/umbau.py`, `timeout 300 python tools/pruefstand/teststation.py`, `timeout 300 python tools/pruefstand/bugjagd2.py` → `OK`.
- [ ] **Step 9: Commit.** `git commit -am "Spielleitung: volle Breite, Reiter Karte und Teams, Zeitachse als eigener Reiter"`

---

### Task 7: Teamliste mit "Braucht dich", Auswahl zwischen Liste und Karte

**Files:**
- Modify: `index.html` (`teamlisteHTML()`, `problemVon()`, `drawMap()`, ACT `"a-sel"`, Kopf-Knopf, CSS)
- Modify: `tools/pruefstand/umbau.py`, `tools/pruefstand/mock.js` (Szenario `admin-probleme`)

**Interfaces:**
- Consumes: `t.failedAttempts` (Task 1), `t.position.updatedAt`, `t.checkedInAt`, `t.currentPosition`, `t.place`, `zustandHTML`-Logik (Zeilen ~1981 bis 1998).
- Produces: `problemVon(t, st)` → `null | { stufe: "fehler" | "warn", kurz: string, text: string }`; `S.admin.sel` (Team-id oder null); ACT `"a-sel"` (liest `data-id`), `"a-probleme"`.

- [ ] **Step 1: Mock-Szenario `admin-probleme`.** Laufendes Spiel mit einem Team ohne `position`, einem mit `position.updatedAt` vor 7 min, einem mit `failedAttempts: 2` an der Station; in `shoot.py` in `ADMIN` aufnehmen.
- [ ] **Step 2: Prüfpunkte.**

```python
print("Teamliste")
pg.set_viewport_size({"width": 1440, "height": 900})
pg.goto(f"{BASIS}/app.html?szenario=admin-probleme"); pg.wait_for_selector("#teamfeld .row")
gruppen = pg.locator("#teamfeld .grp").all_inner_texts()
pruef(gruppen and gruppen[0].startswith("Braucht dich"), f"erster Block 'Braucht dich': {gruppen}")
erste = pg.locator("#teamfeld .row").first.inner_text()
pruef("kein GPS" in erste, f"kein Standort steht ganz oben: {erste[:60]!r}")
pruef("3 Teams brauchen dich" in pg.inner_text("[data-act=a-probleme]"), "Zähler im Kopf")
pg.click("#teamfeld .row:nth-child(3) .row-main")
sel = pg.evaluate("S.admin.sel")
pruef(sel and pg.locator(f"#teamfeld .row.sel").count() == 1, "Zeile aufgeklappt")
pruef(pg.locator(".mapbadge.team.sel").count() == 1, "Team auf der Karte markiert")
pg.locator("#teamfeld").evaluate("e => e.scrollTop = 200"); pg.evaluate("render()")
pruef(pg.evaluate("S.admin.sel") == sel and pg.locator("#teamfeld").evaluate("e => e.scrollTop") > 150, "Auswahl und Scrollen überstehen render()")
pg.click("[data-act=a-probleme]")
pruef(pg.locator("#teamfeld .row.sel").inner_text().find("kein GPS") >= 0, "Zähler springt zum ersten Problem")
```

- [ ] **Step 3: Laufen lassen, erwartet FEHLT.**
- [ ] **Step 4: Problem-Regel** (neben `zustandHTML`):

```js
// Wann braucht ein Team die Spielleitung? Nur im laufenden Spiel und nicht im Ziel.
const GPS_ALT_MS = 5 * 60000;
function problemVon(t, st) {
  if (st.status !== "running" || t.place) return null;
  const upd = t.position && t.position.updatedAt, alt = upd ? Date.now() - new Date(upd).getTime() : null;
  if (alt == null) return { stufe: "fehler", kurz: "kein GPS", text: `${t.name} sendet keinen Standort. Ruf die Teamleitung an; ist das Team an der Station, schalte sie frei.` };
  if (alt > GPS_ALT_MS) return { stufe: "fehler", kurz: `GPS ${ago(upd)}`, text: `Der letzte Standort ist ${ago(upd)} alt. Vielleicht ist das Handy gesperrt.` };
  if ((t.failedAttempts || 0) >= 2) return { stufe: "warn", kurz: `${t.failedAttempts} Fehlversuche`, text: `${t.failedAttempts} von 3 Fehlversuchen an Station ${t.currentPosition}. Klemmt das Rätsel, kannst du es als gelöst werten.` };
  return null;
}
```

Vorher `ago()` (Zeile ~517) lesen: liefert es "vor 7 min", heißt der Chip "GPS vor 7 min"; das ist gewollt.

- [ ] **Step 5: `teamlisteHTML(st)`** ersetzt die Zwischenfassung: Kopf `<div class="list-kopf"><h3>Teams</h3></div>`, dann `<ol class="tliste">` mit Gruppenzeilen `<li class="grp err">Braucht dich · n</li>` (nur wenn n > 0) und `<li class="grp">Alle anderen · m</li>`. Reihenfolge: Probleme (Stufe fehler vor warn, dann Name), danach wie heute `place`, `solved` absteigend, Name. Je Team:

```js
function teamZeile(t, i, st) {
  const p = problemVon(t, st), sel = S.admin.sel === t.id, gesamt = aktiv(st).length;
  const wo = t.place ? `im Ziel, Platz ${t.place}` : t.checkedInAt ? `an Station ${t.currentPosition}` : t.currentPosition ? `zu Station ${t.currentPosition}` : "";
  const knopf = st.status !== "running" || t.place || !t.currentPosition ? ""
    : !t.checkedInAt ? `<button class="btn sm alt" data-act="a-danger" data-key="unlock" data-id="${t.id}" data-pos="${t.currentPosition}" data-name="${esc(t.name)}">Freischalten</button>`
      : `<button class="btn sm alt" data-act="a-danger" data-key="solve" data-id="${t.id}" data-pos="${t.currentPosition}" data-name="${esc(t.name)}">Rätsel werten</button>`;
  const detail = !sel ? "" : `<div class="detail">${p ? `<p class="msg ${p.stufe === "fehler" ? "err" : "warn"}">${esc(p.text)}</p>` : ""}
      <label for="lt-${t.id}">Teamleitung</label>
      <select class="sm" id="lt-${t.id}" data-chg="a-leader" data-id="${t.id}" data-ort="t:${t.id}">${!t.leaderId ? `<option value="" selected>offen</option>` : ""}
        ${(st.participants || []).filter(x => x.teamId === t.id).map(x => `<option value="${esc(x.id)}" ${x.id === t.leaderId ? "selected" : ""}>${esc(x.name)}</option>`).join("")}</select>
      <p class="small">Code <b class="nw">${esc(t.code)}</b></p>
      ${t.readToken ? `<button class="btn sm alt" data-act="a-mit" data-id="${t.id}" data-ort="t:${t.id}" data-token="${esc(t.readToken)}" data-name="${esc(t.name)}">Mitlese-Link kopieren</button>` : ""}
      ${msgBox("t:" + t.id)}</div>`;
  return `<li class="row ${p ? "p-" + p.stufe : ""} ${sel ? "sel" : ""}" data-row="${t.id}">
    <div class="row-top"><button class="row-main" data-act="a-sel" data-id="${t.id}" aria-expanded="${sel}">
      <span class="tier" style="--tc:${teamColor(i)}" aria-hidden="true">${teamEmoji(t.name)}</span>
      <span class="row-txt"><b>${esc(t.name)}</b> <span class="small muted nw">${t.solved}/${gesamt}</span>
        <span class="l2"><span class="nw">${wo}</span>${p ? ` <span class="chip ${p.stufe === "fehler" ? "err" : "warn"} nw">${esc(p.kurz)}</span>` : ""}</span></span></button>${knopf}</div>${detail}</li>`;
}
```

`i` ist der Index in `st.teams` (damit die Farbe zur Karte passt), nicht der Platz in der sortierten Liste. CSS aus `v-weiter.html` (`.row`, `.row-top`, `.row-main`, `.tier`, `.grp`, `.detail`, Zeilen zu `.list-kopf` bis `.detail`) übernehmen, Präfix `#teamfeld`.

- [ ] **Step 6: Auswahl.** ACT: `"a-sel"(d) { S.admin.sel = S.admin.sel === d.id ? null : d.id; }`; `"a-probleme"() { const st = S.admin.state, erst = (st.teams || []).find(t => problemVon(t, st)); if (erst) { S.admin.tab = "live"; S.admin.sel = erst.id; S.admin.zuSel = true; } }`. Nach `render()` im Admin-Live-Fall: Scrollposition von `#teamfeld` vor dem Neuzeichnen merken und danach setzen (wie `getippt` in `render()`); ist `S.admin.zuSel` gesetzt, die gewählte Zeile mit `scrollIntoView({ block: "nearest" })` zeigen und das Flag löschen. In `drawMap()` beim Team-Icon die Klasse `sel` setzen, wenn `S.admin.sel === t.id`, und für gewählte Teams `zIndexOffset: 800`; Klick auf den Marker setzt `S.admin.sel` (Leaflet `marker.on("click", () => { S.admin.sel = t.id; S.admin.zuSel = true; render(); })`, nur beim Anlegen des Markers registrieren). Teams ohne Position: unter der Karte als Knöpfe `<button class="btn sm alt" data-act="a-sel" data-id="…">🐬 Delfin: kein Standort</button>` (ersetzt die heutige Zeile "Ohne Position: …").
- [ ] **Step 7: Zähler im Kopf.** In `viewAdmin()` neben dem Status: `const pn = (st.teams || []).filter(t => problemVon(t, st)).length;` und `${st.status === "running" ? `<button class="btn sm ${pn ? "warn" : "alt"}" data-act="a-probleme">${pn ? `${pn} ${pn === 1 ? "Team braucht" : "Teams brauchen"} dich` : "Alle Teams laufen"}</button>` : ""}`.
- [ ] **Step 8: Prüfen.** `timeout 300 python tools/pruefstand/umbau.py`, `timeout 300 python tools/pruefstand/bugjagd2.py` → `OK`.
- [ ] **Step 9: Commit.** `git commit -am "Spielleitung: Teamliste mit Braucht dich, Auswahl zwischen Liste und Karte"`

---

### Task 8: "Zuletzt" unter der Karte

**Files:**
- Modify: `index.html` (`zuletztZeichnen()`, CSS)
- Modify: `tools/pruefstand/umbau.py`

**Interfaces:**
- Consumes: `S.admin.tracks[teamId].stations[]` mit `position`, `checkedInAt`, `solvedAt` (aus `syncTracks`), `st.teams[].position.updatedAt`.
- Produces: `ereignisse(st)` → `[{ at: ms, teamId, text, art: "ok" | "err" | "" }]`, neueste zuerst, höchstens 8; `zuletztZeichnen()` füllt `#zuletzt`.

- [ ] **Step 1: Prüfpunkte.**

```python
print("Zuletzt")
pg.goto(f"{BASIS}/app.html?szenario=admin-probleme"); pg.wait_for_selector("#zuletzt li", timeout=20000)
li = pg.locator("#zuletzt li").all_inner_texts()
pruef(1 <= len(li) <= 8, f"zwischen 1 und 8 Ereignisse: {len(li)}")
pruef(any("eingecheckt" in x or "Ziffer" in x for x in li), "Check-in oder Ziffer als Ereignis")
pg.locator("#zuletzt li button").first.click()
pruef(pg.evaluate("S.admin.sel") is not None, "Antippen wählt das Team")
```

- [ ] **Step 2: Laufen lassen, erwartet FEHLT.**
- [ ] **Step 3: Umsetzen.**

```js
// Die letzten Ereignisse aller Teams, aus den Routen-Daten (Check-in, Ziffer) und dem Standort (seit 5 min weg)
function ereignisse(st) {
  const A = S.admin, liste = [];
  (st.teams || []).forEach(t => {
    const tr = A.tracks && A.tracks[t.id];
    ((tr && tr.stations) || []).forEach(s => {
      if (s.checkedInAt) liste.push({ at: new Date(s.checkedInAt).getTime(), teamId: t.id, text: `eingecheckt an Station ${s.position}`, art: "" });
      if (s.solvedAt) liste.push({ at: new Date(s.solvedAt).getTime(), teamId: t.id, text: `Ziffer von Station ${s.position}`, art: "ok" });
    });
    const p = problemVon(t, st), upd = t.position && t.position.updatedAt;
    if (p && p.stufe === "fehler" && upd) liste.push({ at: new Date(upd).getTime() + GPS_ALT_MS, teamId: t.id, text: "kein Standort mehr", art: "err" });
    if (t.place && t.finishedAt) liste.push({ at: new Date(t.finishedAt).getTime(), teamId: t.id, text: `im Ziel, Platz ${t.place}`, art: "ok" });
  });
  return liste.filter(e => e.at <= Date.now()).sort((a, b) => b.at - a.at).slice(0, 8);
}
function zuletztZeichnen() {
  const el = $("#zuletzt"), st = S.admin.state; if (!el || !st) return;
  const ev = ereignisse(st), idx = id => (st.teams || []).findIndex(t => t.id === id);
  el.innerHTML = `<h3>Zuletzt</h3>${ev.length ? `<ol class="ticker">${ev.map(e => { const t = st.teams[idx(e.teamId)];
    return `<li><button data-act="a-sel" data-id="${e.teamId}" class="${e.art}"><time class="nw">${fmtClock(e.at)}</time>
      <span><b>${teamEmoji(t.name)} ${esc(t.name)}</b> ${esc(e.text)}</span></button></li>`; }).join("")}</ol>`
    : `<p class="small muted">Noch nichts passiert.</p>`}`;
}
```

`zuletztZeichnen()` zusätzlich direkt nach `drawMap(true)` in `render()` aufrufen (zeigt den Stand, bevor die Routen nachgeladen sind). CSS: `.ticker{list-style:none;margin:8px 0 0;padding:0;display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:2px 16px}.ticker button{display:flex;gap:10px;align-items:baseline;width:100%;min-height:42px;border:0;background:none;text-align:left;font:inherit;color:inherit;cursor:pointer}.ticker time{color:var(--muted);font-variant-numeric:tabular-nums}.ticker .ok time{color:var(--ok)}.ticker .err time{color:var(--err)}`. Vorher prüfen, dass `fmtClock` (bei den Karten-Popups benutzt) "HH:MM" liefert.

- [ ] **Step 4: Prüfen.** `timeout 300 python tools/pruefstand/umbau.py` → `OK`.
- [ ] **Step 5: Commit.** `git commit -am "Spielleitung: Zuletzt mit den letzten Ereignissen aller Teams"`

---

### Task 9: Gesamtprüfung, Doku, Auslieferung

**Files:**
- Modify: `tools/pruefstand/shoot.py`, `tools/pruefstand/README.md`, `HANDOFF.md`, `SPIEL.md` (falls dort Reiter oder Handy-Aufbau beschrieben sind: `grep -n "Reiter\|Karte\|Teams" SPIEL.md`)

- [ ] **Step 1: Alle Prüfskripte**, jedes einzeln im Vordergrund: `for s in umbau kritik waechter selfie name teststation bugjagd2 geraetetest; do timeout 300 python tools/pruefstand/$s.py || echo "FEHLER $s"; done` → überall `OK`.
- [ ] **Step 2: Alle Bilder.** `cd tools/pruefstand && timeout 590 python shoot.py` → im Bericht nur die bekannte 404 beim ersten Bild; die Bilder `leitung-unterwegs-*`, `leitung-raetsel-*`, `mitglied-*`, `admin-karte-*`, `admin-probleme-*` ansehen (Hell und Dunkel, Tablet hoch und quer).
- [ ] **Step 3: Mockup-Abgleich.** Die Bilder neben `mockups/design-varianten/v-weiter.html#unterwegs`, `#raetsel` und `#admin` legen; Abweichungen, die nicht in "Was bleibt" stehen, beheben oder im HANDOFF begründen.
- [ ] **Step 4: Doku.** HANDOFF: neuer Abschnitt "Umbau Weiterentwicklung (Nachtrag 33)" mit Handy-Aufbau, Spielleitung, Migration, neuem Prüfskript, Szenario `admin-probleme`; im "Stand zum Fortsetzen" die Zeile zu den Design-Varianten auf "gebaut" setzen. README des Prüfstands: `umbau.py` in die Tabelle.
- [ ] **Step 5: Commit und Auslieferung.** `git add -A index.html tools supabase HANDOFF.md SPIEL.md && git commit -m "Umbau Weiterentwicklung: Doku und Prüfstand"`, dann nach Rücksprache mit Friedrich `git push origin master` und auf `https://7deeda.github.io/Stadtjagt/` prüfen, dass `class="ftabs"` ausgeliefert wird. (Erledigt 09.10.2026: gemerged, gepusht, live geprüft.)
