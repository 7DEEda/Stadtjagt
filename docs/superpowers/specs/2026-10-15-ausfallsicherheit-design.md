# Ausfallsicherheit für den Eventtag (Design)

Stand 15.10.2026. **Umgesetzt am 16.10.2026 (Nachtrag 35, SPIEL.md §15)**, mit
den Änderungen aus der Gegenprüfung, die dieser Fassung vorgehen: Aufräumen nur
unter `sj-*`; Serverfehler (5xx, kein JSON) wie Funkloch, `S.zuletzt` nur bei
guter Antwort; Koffer-Code der Notfallmappe aus den Stationen der echten Route,
keine Haken im Testmodus, "Daten vom" aus dem letzten `admin_state`; Eventstand
nicht per Push notieren; `offline.py` mit mock.js inline und RPC-Pfad am
Prüfserver; Text "Das Foto wird nachgereicht, sobald das Netz reicht."; Abgleich
nur mit zwei Fällen (Phase weiter oder "Wieder Netz. Tippt noch mal."); kein
Clientzweig "Check-in tolerant"; letzter Stand auch in `leitungNochDa()`
gelöscht; Link mit Schrägstrich; Service Worker spätestens 7 Tage vor dem
Event live, Notausgang auf iPhone und Android geprobt; index.html gezippt etwa
93 KB (vor dem Umbau, jetzt etwa 99 KB). Bezug: HANDOFF.md,
"Stand zum Fortsetzen", Absatz "Weitere Punkte für die Ausfallsicherheit".
Mockup der sichtbaren Teile: `mockups/ausfallsicherheit/index.html`
(Funkloch-Meldung, Versionszeile, Notfallmappe; Daten erfunden).

**Migration nötig: ja** (Abschnitt 3.3, nur für "doppelt zählt nichts" bei
falschen Antworten und für gleiche Antworten auf Wiederholungen).

## 0. Ziel und Abgrenzung

Am Eventtag (Prag, ~100 Leute, 12 Teams) soll das Spiel weiterlaufen, wenn
einzelne Teile ausfallen:

| Ausfall | heute | danach |
|---|---|---|
| Funkloch beim Öffnen oder Neuladen (iOS wirft Tabs oft raus) | Browser-Fehlerseite | App startet aus dem Cache, zeigt den letzten Stand mit "Stand 13:27", Kompass und Entfernung laufen weiter |
| GitHub Pages hakt | App lädt nicht | wie oben |
| unpkg oder Google Fonts nicht erreichbar | Karte der Spielleitung fehlt, Ersatzschrift | alles liegt im Repo |
| Eingabe im Funkloch, Antwort geht verloren | eine falsche Antwort kann doppelt zählen, eine richtige meldet bei Wiederholung "Erst am Ort einchecken" | gleiche Eingabe, gleiche Antwort; nichts zählt doppelt |
| Unklar, welcher Stand auf welchem Handy läuft | nicht sichtbar | "Version 15.10., 22:26" unten, Link bei neuerer Version |
| Datenbank oder App ganz weg | kein Plan | Notfallmappe auf Papier, Ablauf dafür |
| Änderungen kurz vor dem Event | kein Stopp | Änderungsstopp als Ablaufpunkt |

Nicht im Umfang: Spielen ganz ohne Datenbank (jede Eingabe braucht den
Server, das bleibt so), Warteschlange für Eingaben, Web-App zum Installieren,
Kartenkacheln offline, Umzug der Datenbank.

## 1. App startet auch ohne Netz (Service Worker)

### 1.1 Datei und Umfang

Neue Datei `sw.js` im Repo-Wurzelordner, Scope `/Stadtjagt/`. Sie kümmert
sich nur um die eigenen Dateien der App. Alles andere geht unberührt ans Netz
(kein `respondWith`):

- Supabase (`*.supabase.co`, alle RPCs `/rest/v1/rpc/...`): nie im Cache,
  auch nicht als Fallback. Spielstand aus einem Cache wäre falsch.
- Kartenkacheln (`tile.openstreetmap.org`): nie im Cache.
- Alles, was nicht GET ist (auch der HEAD der Versionsprüfung, 4.2).
- Andere Seiten im selben Scope: `geraete-test.html`, `kompass-test.html`,
  `design-system/`, `mockups/`, `tools/`. Sie laufen wie bisher.

| Datei | Strategie | im Vorab-Cache (install) |
|---|---|---|
| Navigation auf `./` oder `./index.html` (jede Query, Hash geht nie mit) | Netz zuerst, 4 s, sonst Cache | ja, Schlüssel `./` |
| `config.js`, `kompass-waechter.js` | Netz zuerst, 4 s, sonst Cache | ja |
| `vendor/fonts/*.woff2` (Abschnitt 2) | Cache zuerst, bei Fehlen aus dem Netz und ablegen | ja |
| `hintergrund/a.svg`, `b.svg`, `c.svg` | Cache zuerst, im Hintergrund nachladen (stale-while-revalidate) | ja |
| `vendor/leaflet-1.9.4/*`, `vendor/qrcode.js` | Cache zuerst, bei Fehlen aus dem Netz und ablegen | nein (nur Spielleitung bzw. bei Bedarf) |

Vorab-Cache beim Installieren: `index.html`, `config.js` und
`kompass-waechter.js` mit `cache.addAll` (scheitert eins, scheitert die
Installation, dann gibt es eben keinen Service Worker und alles läuft wie
heute). Schriften und Hintergründe einzeln mit `catch`, damit ein fehlendes
Bild die Installation nicht kippt. Alle Vorab-Abrufe mit `cache: "reload"`,
sonst landet die 10-Minuten-Kopie aus dem HTTP-Cache im Speicher. Umfang beim
ersten Besuch einmalig rund 450 KB über die Leitung (index.html gezippt etwa
70 KB, Schriften 270 KB, Hintergründe gezippt etwa 60 KB).

### 1.2 Netz zuerst, mit Zeitgrenze

Für index.html, config.js und kompass-waechter.js:

1. `fetch(url, { cache: "no-cache" })`. GitHub Pages schickt
   `Cache-Control: max-age=600`; mit `no-cache` fragt der Browser immer nach
   (ETag, meist 304), ein Fix ist also gleich nach dem Deployment da und nicht
   erst nach 10 Minuten.
2. Antwortet das Netz mit 200 innerhalb von 4 s: ausliefern und den Cache
   damit überschreiben.
3. Scheitert der Abruf sofort (kein Netz) oder dauert er länger als 4 s:
   die Kopie aus dem Cache ausliefern. Der Abruf läuft weiter
   (`event.waitUntil`) und legt das Ergebnis für das nächste Laden ab.
4. Kein Cache und kein Netz (erster Besuch im Funkloch): Fehler wie heute.

4 s, weil index.html gezippt etwa 70 KB hat und das auch im schwachen
Mobilfunk in der Regel reicht; der Stresstest maß für die Datenbank
p95 unter 0,4 s, GitHub Pages ist ein CDN. Wer über 4 s braucht, bekommt den
vorigen Stand sofort statt einer weißen Seite, und die Versionsprüfung (4.2)
bietet den neuen an, sobald er da ist.

Nur Antworten mit Status 200 und `type: "basic"` kommen in den Cache.

### 1.3 Kein ewig alter Stand

Das Hauptrisiko eines Service Workers ist ein Handy, das tagelang eine alte
App zeigt. Dagegen:

- Die App-Hülle kommt immer zuerst aus dem Netz (1.2). Der Cache ist nur
  Ersatz. Ein Fix-Push ist also spätestens beim nächsten Laden mit Netz da.
- `navigator.serviceWorker.register("sw.js", { updateViaCache: "none" })`:
  der Browser prüft `sw.js` bei jeder Navigation am HTTP-Cache vorbei.
- `sw.js` ruft beim Installieren `skipWaiting()`, beim Aktivieren
  `clients.claim()` und löscht alle Caches, deren Name nicht zur aktuellen
  Fassung gehört. Cache-Namen tragen eine Nummer: `sj-huelle-1`,
  `sj-dauer-1`. Die Nummer steigt nur, wenn sich die Liste oder die
  Strategie ändert, nicht bei jedem Fix (dafür sorgt Netz zuerst).
- Dateien unter `vendor/` sind über den Namen versioniert
  (`leaflet-1.9.4/`, Schriftdateien mit Schnitt im Namen). Wer eine davon
  tauscht, gibt ihr einen neuen Namen; sonst bliebe die alte im Cache.
- **Notausgang:** Macht der Service Worker am Eventtag Ärger, ersetzt man
  `sw.js` durch eine Fassung, die alle Caches löscht und sich abmeldet
  (`self.registration.unregister()`), und pusht. Jedes Handy wirft ihn beim
  nächsten Laden mit Netz ab. Die Vorlage liegt als `tools/sw-aus.js` im Repo
  (wird nicht ausgeliefert, nur kopiert), der Ablauf steht in HANDOFF.

Alte Fassungen der App können trotzdem eine Weile auf Handys laufen (Tab
bleibt offen, Laden im Funkloch). Deshalb gilt weiter und jetzt verschärft:
**Jede Datenbank-Änderung bleibt mit der vorigen App-Fassung verträglich**
(neue Parameter nur mit `default`, keine Felder aus Antworten entfernen).
Die Migration in 3.3 hält das ein.

### 1.4 Kein Installieren-Popup

Kein Web-App-Manifest, kein `<link rel="manifest">`, keine
`apple-mobile-web-app-*`-Meta-Angaben. Ohne Manifest zeigt Chrome auf Android
weder Mini-Infoleiste noch Installieren-Dialog, Safari bietet nichts an. Der
Menüpunkt "Zum Startbildschirm" bleibt, wie bei jeder Seite.

### 1.5 Registrieren

Am Ende des App-Skripts, nach `refresh()`:

```js
if ("serviceWorker" in navigator && /\/(index\.html)?$/.test(location.pathname)
    && (location.protocol === "https:" || location.hostname === "127.0.0.1" || location.hostname === "localhost"))
  addEventListener("load", () => navigator.serviceWorker.register("sw.js", { updateViaCache: "none" }).catch(() => { }));
```

Nur für `index.html` bzw. `./`: der Prüfstand lädt `app.html` und bekommt
also keinen Service Worker (sonst lägen Szenarien verschiedener Läufe im
Cache). Fehler beim Registrieren (privater Modus, alte Browser) sind still,
die App läuft dann wie heute.

### 1.6 Letzter Stand ohne Netz

Die Hülle allein zeigt ohne Netz nur "Lade …". Damit ein Team nach einem
Neuladen im Funkloch weiter zur Station findet, merkt sich das Handy den
letzten Stand:

- **Teamleitung:** Nach jedem erfolgreichen `team_state` (in
  `teamStandSetzen`) schreibt die App
  `LS["sj.letzter.team"] = { code, at: Date.now(), state }` (einige KB).
  Startet die App, scheitert `team_state` mit `netz: true` und ist noch kein
  `S.team.state` da, nimmt sie den gemerkten Stand, wenn `code` gleich
  `S.team.code` ist, er höchstens 12 h alt ist und `status` `drawn` oder
  `running` lautet. `S.zuletzt = at`, damit oben "Stand 13:27" steht.
  Entfernung, Pfeil, Ziffern, Rätsel und Hochhalten gehen dann, weil GPS und
  Kompass kein Netz brauchen. Eingaben scheitern mit der Meldung aus 3.4.
- **Mitlesen:** dasselbe für `S.pub` und den Stand des Teams aus
  `member_state`/`member_state_by_team` unter `sj.letzter.mit`, Bedingungen
  wie oben (gleicher Geräte- oder Mitlese-Schlüssel).
- Gelöscht wird der gemerkte Stand bei Abmelden, Abgeben, `codeUngueltig()`
  und wenn `nameNochDa()` die Person nicht mehr findet.
- **Spielleitung:** nichts gemerkt. `admin_state` enthält alle Lösungen und
  Namen; das Tablet behält den Stand ohnehin, solange die Seite offen ist,
  und für den Totalausfall gibt es die Notfallmappe (Abschnitt 5).

Der gemerkte Stand enthält das Rätsel der aktuellen Station und den
Team-Code, beides liegt auf demselben Handy schon heute
(`sj.code`, Anzeige). Neu ist nichts davon für andere sichtbar.

### 1.7 Grenzen (in HANDOFF und Ablauf aufnehmen)

- Der erste Besuch braucht Netz. Erst danach liegt die App auf dem Handy.
- **iOS:** Safari löscht Cache und `localStorage` einer Seite nach etwa 7
  Tagen ohne Besuch (Tracking-Schutz, gilt für nicht installierte Seiten).
  Das trifft schon heute `sj.token` und `sj.name`. Folge für den Ablauf: Alle
  öffnen die App am Vorabend oder Morgen im Hotel-WLAN (6.2).
- Privates Surfen: Service Worker fehlt oder vergisst alles beim Schließen.
  Die App läuft dann wie heute.
- Die Karte der Spielleitung zeigt ohne Netz keine Kacheln, nur Marker auf
  grauem Grund.

## 2. Leaflet und Schriften lokal

- **Leaflet 1.9.4** nach `vendor/leaflet-1.9.4/`: `leaflet.js`,
  `leaflet.css`, `images/` (layers.png, layers-2x.png, marker-icon.png,
  marker-icon-2x.png, marker-shadow.png) und `LICENSE` (BSD-2). Quelle: das
  npm-Paket `leaflet@1.9.4` (registry.npmjs.org, Tarball), einmal beim
  Umsetzen geholt, Inhalt mit der unpkg-Fassung verglichen. `loadLeaflet()`
  nimmt die beiden lokalen Pfade, sonst bleibt alles gleich (lazy, nur
  Spielleitung). Der Prüfstand kopiert `vendor/` schon heute neben `app.html`
  (`shoot.bauen()`), läuft also danach auch ohne unpkg.
- **Schriften** nach `vendor/fonts/` statt Google Fonts: Barlow 400, 500, 600,
  Barlow Semi Condensed 500, 600, 700, JetBrains Mono 700, je `latin` und
  `latin-ext` (tschechische Namen wie "Křižík" brauchen `latin-ext`), 14
  Dateien, zusammen etwa 270 KB. Dateinamen nach dem Muster
  `barlow-semi-condensed-700-latin-ext.woff2`. Die `@font-face`-Regeln mit
  denselben `unicode-range`-Angaben wie bei Google Fonts und
  `font-display: swap` stehen im `<style>` von index.html; die beiden
  `preconnect`-Zeilen und der Google-Link fallen weg. Lizenz SIL OFL 1.1 als
  `vendor/fonts/OFL.txt`. Die Dateien liegen schon für das Mockup unter
  `mockups/ausfallsicherheit/fonts/` (8 der 14) und wurden am 15.10.2026 von
  fonts.gstatic.com geholt (Barlow v13, Barlow Semi Condensed v16,
  JetBrains Mono v24).
- `geraete-test.html` und die Mockups laden weiter von Google Fonts; nicht
  im Umfang, beim nächsten Anfassen umstellen.

## 3. Eingaben im Funkloch

### 3.1 Wie es heute ist

`rpc()` bricht nach 15 s ab (Fotos 60 s). Jeder Netzfehler und das
Zeitlimit werden zu `keineVerbindung()`: "Keine Verbindung. Wartet kurz und
tippt noch mal.", `netz: true`. Der Klick-Handler zeigt die Meldung am Knopf
(`ort: "leiste"`), ohne `kind: "netz"`; sie bleibt also stehen, bis die Phase
wechselt, auch wenn der 10-s-Abruf längst wieder durchkommt. Das Getippte
bleibt im Feld.

Zwei Fälle sind für das Handy gleich, für den Server nicht: die Anfrage kam
nie an, oder sie kam an und nur die Antwort ging verloren (auch: Supabase
hängt länger als 15 s, wie im ersten Stresstest-Lauf bis 40 s, und arbeitet
die Anfrage danach ab).

| Eingabe | Anfrage verloren | Antwort verloren, nochmal getippt |
|---|---|---|
| Einchecken (`check_in`) | nichts passiert | Server prüft die Entfernung erneut. Steht das Team noch dort: wieder "Angekommen". Hat das GPS gesprungen: "Noch 63 m bis zur Station", obwohl `state.checkedIn` schon wahr ist und das Rätsel darunter steht. |
| Richtige Antwort (`submit_answer`) | nichts passiert | Station ist gelöst, `current_station` ist die nächste, noch ohne Check-in: **"Erst am Ort einchecken, dann gibt es das Rätsel."** Die Ziffer erscheint ohne Meldung. |
| Falsche Antwort | nichts passiert | **zählt zweimal** als Fehlversuch; beim zweiten oder dritten Mal Denkpause, die das Team so nie verdient hat. |
| Koffer-Code (`submit_final`) | nichts passiert | idempotent: Wer einen Platz hat, bekommt ihn wieder, ohne Ortsprüfung (`v_place` wird zuerst gelesen). Falscher Code zählt nirgends. **Passt.** |
| Selfie (`team_selfie`) | Foto bleibt auf dem Handy (`fotoMerken`), `fotoNachreichen` schickt es beim nächsten Abruf | `on conflict do update` und `selfie_at = coalesce(...)`: idempotent. Die Ansicht hängt aber auf "Erneut senden", bis man tippt (`S.selfie` bleibt gesetzt). |
| Ohne Foto weiter (`team_selfie_skip`) | nichts passiert | idempotent. **Passt.** |
| Tipp aufdecken (`reveal_tip`) | nichts passiert | idempotent (`coalesce(tip_at, now())`). **Passt.** |
| Anmelden (`register_participant`) | seit Bugjagd 03.10. idempotent über den vorher abgelegten Schlüssel. **Passt.** | |

### 3.2 Entscheidung: nochmal tippen, nicht automatisch nachreichen

Einchecken, Antwort und Koffer-Code werden **nicht** automatisch
nachgereicht. Stattdessen sagt die App klar, dass nichts doppelt zählt, und
jede Wiederholung bekommt dieselbe Antwort wie die erste.

Begründung:

1. Einchecken und Koffer-Code hängen am Ort und am Moment. Eine Eingabe aus
   der Warteschlange trüge einen alten Standort; sie könnte ein Team
   einchecken, das schon weitergelaufen ist, oder mit einer überholten
   Position scheitern.
2. Das Team steht in dem Moment am Ort, schaut aufs Handy und will genau das
   Ergebnis wissen. Ein Tipp ist da natürlicher als ein unsichtbarer
   Hintergrundvorgang, der irgendwann später ein "Leider falsch" auslöst.
3. Eine aufgeschobene Antwort kann veraltet sein: das Team tippt inzwischen
   etwas anderes, die Spielleitung hat die Station gewertet, die Denkpause
   läuft.
4. Der eigentliche Schaden heute ist das doppelte Zählen und die falsche
   Meldung bei Wiederholung. Beides löst Idempotenz auf dem Server (3.3),
   egal ob von Hand oder automatisch wiederholt.
5. Weniger Zustand über Neuladen hinweg, weniger Code.

Ausnahme bleibt das Gruppenselfie: Es wird schon heute nachgereicht, und das
passt dort (groß, nicht zeitkritisch, kein Wettbewerb um den Moment,
idempotent).

Statt Nachreichen gibt es einen **Abgleich**: Kommt nach einer gescheiterten
Eingabe der nächste `team_state` durch, vergleicht die App ihn mit dem Stand
vor der Eingabe und sagt, was passiert ist (3.4). Damit sieht das Team auch
ohne zweiten Tipp, wenn die Eingabe doch ankam.

### 3.3 Server (Migration, nur vorbereiten)

Datei `supabase/migrations/20261016090000_eingaben_wiederholen.sql`,
mehrfach ausführbar. Vorlage für `submit_answer` ist die Fassung aus
`20261004100000_bugjagd2.sql`, für `check_in` die aus
`20260918210000_testmodus.sql` (beide über `tools/migration_bugjagd2.py`
`neueste()` gegenprüfen).

**a) Spalte:**

```sql
alter table progress add column if not exists last_wrong text;   -- norm() der letzten gezählten falschen Antwort
```

**b) `submit_answer` mit Station:** neuer Parameter, damit der Server eine
Wiederholung nach dem Wechsel zur nächsten Station erkennt. Weil sich die
Signatur ändert, `drop` und `create` (ein zweites `create or replace` legte
eine Überladung an; PostgREST fände mit zwei Argumenten beide Fassungen und
antwortete PGRST203):

```sql
drop function if exists submit_answer(text, text);
create or replace function submit_answer(p_code text, p_answer text, p_position int default null)
returns json language plpgsql security definer set search_path = public as $$
declare t teams; g game_state; cur stations; row_p progress; fr stations; fr_p progress;
        v_norm text := coalesce(norm(p_answer), ''); v_attempts int; v_locked boolean; v_rest int;
begin
  t := team_by_code(p_code);
  select * into g from game_state where id = 1;
  if g.status <> 'running' then ... wie bisher ... end if;
  cur := current_station(t.id);

  -- Wiederholung: die App nennt die Station, an der getippt wurde. Ist das Team inzwischen weiter
  -- (die erste Antwort kam an, ihre Antwort nicht; oder die Spielleitung hat gewertet), nie gegen
  -- das nächste Rätsel prüfen.
  if p_position is not null and (cur.id is null or cur.position <> p_position) then
    select * into fr from stations where position = p_position;
    select * into fr_p from progress where team_id = t.id and station_id = fr.id;
    if fr_p.solved_at is not null and (g.test_mode or answer_ok(p_answer, fr.answer)) then
      return json_build_object('ok', true, 'message', <Erfolgstext wie unten>, 'state', team_state(p_code));
    end if;
    return json_build_object('ok', false,
      'message', case when fr_p.solved_at is not null then 'Diese Station ist schon gelöst.'
                      else 'Das Rätsel hat gewechselt. Lest es noch mal.' end,
      'state', team_state(p_code));
  end if;

  if cur.id is null then ... 'Alle Stationen sind gelöst.' ... end if;
  select * into row_p from progress where team_id = t.id and station_id = cur.id for update;
  ... Check-in fehlt, Denkpause: wie bisher ...
  if g.test_mode or answer_ok(p_answer, cur.answer) then
    update progress set solved_at = now(), failed_attempts = 0, locked_until = null, last_wrong = null ...;
    return ... wie bisher ...;
  end if;
  if v_norm = '' then ... 'Bitte gebt eine Antwort ein.' ... end if;

  -- Dieselbe falsche Antwort wie zuletzt zählt nicht noch einmal: im Funkloch kam die erste an,
  -- nur ihre Antwort nicht. Antwortet genau wie beim ersten Mal.
  if v_norm = row_p.last_wrong then
    v_rest := case when row_p.locked_until is not null and row_p.locked_until <= now() then 3
                   else 3 - row_p.failed_attempts end;
    return json_build_object('ok', false,
      'message', 'Leider falsch. Noch ' || v_rest || case when v_rest = 1 then ' Versuch.' else ' Versuche.' end,
      'state', team_state(p_code));
  end if;

  ... Zählen wie bisher, dazu last_wrong = v_norm im selben update ...
end $$;
grant execute on function submit_answer(text, text, int) to anon, authenticated;
```

Regeln dazu:

- `last_wrong` gilt je Team und Station (Zeile in `progress`). Eine andere
  falsche Antwort zählt normal und ersetzt `last_wrong`.
- Auch absichtlich wiederholt zählt dieselbe falsche Antwort nicht noch
  einmal. Das ist gewollt: Sie bringt dem Team nichts, und so braucht es
  keine Kennung je Anfrage (die das Handy über Neuladen hinweg halten müsste
  und die vom Tablet der Spielleitung aus fehlte).
- Läuft die Denkpause, greift wie bisher zuerst die Sperre ("Denkpause:
  noch 87 Sekunden."); eine Wiederholung der dritten falschen Antwort
  verlängert also nichts.
- Alte App-Fassungen rufen ohne `p_position` auf und bekommen das Verhalten
  von heute plus "doppelt zählt nichts" (Default `null`).
- Die neue App ruft mit `p_position`, bei PGRST202 (Datenbank ohne
  Migration) einmal ohne, nach dem Muster von `pub-reg` (`ohneFunktion`).

**c) `check_in` gleich bei Wiederholung:** Signatur bleibt, also
`create or replace` (Rechte bleiben). Nach `cur := current_station(...)` und
vor der Entfernungsprüfung:

```sql
  -- schon eingecheckt (Wiederholung nach verlorener Antwort): gleiche Antwort, ohne die Entfernung
  -- neu zu prüfen; das GPS darf inzwischen gesprungen sein
  if exists (select 1 from progress where team_id = t.id and station_id = cur.id and checked_in_at is not null) then
    return json_build_object('ok', true, 'message', <Text wie beim ersten Check-in>, 'state', team_state(p_code));
  end if;
```

**d) `submit_final`, `team_selfie`, `team_selfie_skip`, `reveal_tip`:**
bleiben, sind schon idempotent (3.1).

**e)** Am Ende `notify pgrst, 'reload schema';`.

**Probelauf** `tools/pruefstand/eingaben_db.py` nach dem Muster
`namenssuche_grenze_db.py`: ein DO-Block, spielt die Migration ein, legt ein
erfundenes Team mit zwei Stationen-Fortschritten an, setzt das Spiel im Block
auf `running`, prüft und endet **immer** mit einer Ausnahme (PROBELAUF_OK).
Mit `--ohne` rot. Prüfungen:

1. Check-in im Radius: ok. Derselbe Check-in 500 m entfernt: ok, gleicher
   Text, kein `distance`.
2. Falsche Antwort "12": `failed_attempts` 1. Nochmal "12" und " 12!"
   (gleich nach `norm`): weiter 1, Text "Noch 2 Versuche.". "13": 2.
3. Richtige Antwort mit `p_position` 1: gelöst. Dieselbe nochmal mit
   `p_position` 1: ok, gleicher Text, Station 2 unberührt
   (`failed_attempts` 0, kein Check-in). Falsche Antwort mit `p_position` 1:
   "Diese Station ist schon gelöst.", Station 2 unberührt.
4. Aufruf mit zwei benannten Argumenten (alte App) geht und zählt wie oben.
5. Denkpause: dritte falsche Antwort sperrt; dieselbe nochmal: Sperrtext,
   `pauses` unverändert.
6. `submit_final` zweimal: gleicher Platz.
7. Rechte: `submit_answer(text,text,int)` für `anon` und `authenticated`
   ausführbar, `submit_answer(text,text)` gibt es nicht mehr; dazu die
   Prüfung der internen Hilfsfunktionen wie in `rechte_db.py`.
   `rechte_db.py` selbst bleibt danach grün.

Das Spiel kurz auf `running` zu setzen geschieht nur im zurückgerollten
Block; die Sperre auf `game_state` hält Millisekunden.

### 3.4 App

- **Meldung bei einer Eingabe ohne Netz** (`t-check`, `t-answer`, `t-final`):
  "Keine Verbindung. Tippt noch mal, sobald ihr Netz habt. Doppelt zählt
  nichts." in der Leiste (`ort: "leiste"`), Getipptes bleibt. Die drei
  Aktionen fangen `e.netz` selbst, merken sich
  `S.offen = { act, phase: phaseKey(st), pos, failed: st.failedAttempts, locked: st.lockedUntil }`
  und werfen die Meldung weiter. Andere Aktionen behalten die bisherige
  Meldung.
- **Abgleich** in `teamStandSetzen(s)`, solange `S.offen` gesetzt ist, vor
  dem bisherigen "Phase gewechselt, Meldung weg":
  - Phase weiter (`phaseKey` anders): die Erfolgsmeldung, als wäre die
    Antwort durchgekommen. Einchecken: "Angekommen. Das Rätsel ist frei."
    Antwort: "Richtig. Station 3 gelöst, eure Ziffer: 7." mit
    `S.neueZiffer` (bei offenem Selfie keine Meldung, wie heute). Koffer:
    die Platz-Meldung wie vom Server.
  - Phase gleich, aber `failedAttempts` gestiegen oder `lockedUntil` neu:
    "Leider falsch. Noch 2 Versuche." bzw. "Dreimal falsch. Zwei Minuten
    Denkpause für euer Team."
  - sonst: "Wieder Netz. Tippt noch mal." (Hinweis, nicht Fehler).
  - Danach `S.offen = null`. Neuladen vergisst `S.offen`, dann gilt der Stand
    aus dem Abruf ohne Meldung.
- **Antwort mit Station:** `t-answer` schickt `p_position` (die Station, die
  beim Tippen zu sehen war), Rückfall ohne bei PGRST202.
- **Check-in tolerant:** Kommt `ok: false`, aber `r.state.checkedIn` und
  dieselbe Station (Datenbank ohne Migration), zeigt die App die
  Erfolgsmeldung statt "Noch 63 m".
- **Selfie:** Zeigt ein Abruf das Foto der Station, während `S.selfie` mit
  `status: "fehler"` daran hängt, räumt die App `S.selfie` ab und meldet
  "Foto ist drin." Die Erkennung in `t-selfie-ok` prüft `e.netz` statt des
  Meldungstexts (der Text ändert sich hier für Eingaben). Der Satz "Das Foto
  reichen wir nach, sobald das Netz reicht." wird zu "Das Foto geht nach,
  sobald das Netz reicht." (Tool spricht ohne "wir").
- Zeitlimit bleibt 15 s; der Knopf sagt währenddessen "Wird geprüft …" bzw.
  "Standort wird bestimmt …" wie heute.

### 3.5 Texte

| Wo | Text |
|---|---|
| Leiste, Eingabe ohne Netz | Keine Verbindung. Tippt noch mal, sobald ihr Netz habt. Doppelt zählt nichts. |
| Leiste, Netz zurück, nichts angekommen | Wieder Netz. Tippt noch mal. |
| Server, Wiederholung an gelöster Station, andere Antwort | Diese Station ist schon gelöst. |
| Server, Station passt nicht und ist nicht gelöst (Fortschritt zurückgesetzt) | Das Rätsel hat gewechselt. Lest es noch mal. |
| Selfie nachgereicht | Foto ist drin. |
| Ohne Foto weiter, Foto wartet | Station 3 gelöst, eure Ziffer: 7. Das Foto geht nach, sobald das Netz reicht. |

Erfolgs- und Fehlertexte im Abgleich sind wortgleich mit den heutigen.

## 4. Sichtbare Version

### 4.1 Was steht da

Unter der Navigation (`nav()`, also unten auf Anmeldeseite, im Tab Team der
Teamleitung und bei der Spielleitung) eine Zeile in `--fs-s`, `--muted`,
zentriert: **"Version 15.10., 22:26"**, `white-space: nowrap`. Dieselbe
Angabe steht im Kopf der Notfallmappe.

Quelle ist `document.lastModified`, also der `Last-Modified`-Kopf der
geladenen index.html. GitHub Pages setzt ihn beim Deployment für alle Dateien
auf die Zeit der Veröffentlichung (geprüft 15.10.2026: index.html, config.js
und a.svg tragen alle `Thu, 15 Oct 2026 20:26:44 GMT`). Kommt die Seite aus
dem Cache des Service Workers, trägt die gespeicherte Antwort ihren Kopf
mit, die Version stimmt also auch ohne Netz. Vorteile: kein Build, nichts von
Hand zu pflegen, nichts zu vergessen, und sie zeigt genau den Stand, der
läuft. Ein Commit-Hash wäre genauer, braucht aber einen Build-Schritt oder
eine GitHub Action; nicht nötig, weil pro Push genau ein Deployment entsteht
und die Zeit eindeutig ist.

Lesen: `document.lastModified` hat die Form `MM/DD/YYYY hh:mm:ss` (lokal);
per Regex zerlegen, nicht `new Date(string)`. Fehlt der Kopf, liefert der
Browser die aktuelle Zeit; liegt der Wert weniger als 5 s vor dem Laden,
bleibt die Zeile leer.

### 4.2 Neuere Version da

Beim Zurückkehren in die App (`visibilitychange`) und höchstens alle 10
Minuten aus dem 10-s-Takt (nicht bei verdeckter Seite) fragt die App
`fetch(location.pathname, { method: "HEAD", cache: "no-store" })` und liest
`Last-Modified`. Liegt er mehr als 1 s nach der geladenen Version, kommt
hinter die Versionszeile der Link **"Neue Version laden"**
(`.link`, `data-act="neu-laden"`, `location.reload()`). Kein Banner, kein
Neuladen von selbst: Ein Neuladen kostet auf iOS die Kompass-Freigabe
("Kompass wieder einschalten" fängt das auf) und brächte mitten in einer
Eingabe Getipptes durcheinander. Fehlschläge der Prüfung sind still.

Mockup: `mockups/ausfallsicherheit/index.html`, Zustand "Neue Version".

## 5. Notfallmappe

### 5.1 Zweck

Fällt die Datenbank oder die App ganz aus, läuft das Spiel über die
Spielleitung weiter: Teams melden sich per Anruf oder WhatsApp, die
Spielleitung gibt Ortshinweise und Koordinaten durch, prüft Antworten auf
Papier und hakt ab. Dafür braucht sie alles auf einem Blatt.

### 5.2 Bedienung

- Reiter **Stationen**, im letzten Panel neben dem Koffer-Code: Knopf
  "Notfallmappe" (`.btn.sm.alt`, kein zweites Orange).
- Öffnet eine eigene Ansicht der Spielleitung (`S.admin.mappe = true`) statt
  der Reiter: oben eine Leiste mit "Zurück" (`.btn.sm.alt`) und "Drucken"
  (`.btn.sm`, orange, `window.print()`), darunter das Blatt.
- Das Blatt entsteht nur aus `S.admin.state` im Browser. Kein neuer RPC,
  keine Datei im Repo (das Repo ist öffentlich, die Mappe enthält alle
  Lösungen). Weil es nur den Stand im Speicher braucht, geht es auch, wenn
  die Datenbank gerade weg ist und das Tablet noch offen war; dann steht
  oben "Daten vom" mit der Zeit des letzten Abrufs (`S.zuletzt`).
- Auf dem iPad: "Drucken" öffnet den Druckdialog, dort AirPrint oder als PDF
  sichern.

### 5.3 Inhalt (alles aus `admin_state`)

1. **Kopf:** "Stadtjagd Notfallmappe"; "Daten vom 18.10.2026, 09:12"
   (`S.zuletzt`), "Version 17.10., 21:40" (4.1), Zahl der Teams und
   Personen, "Testmodus an" als Warnung (sonst "Testmodus aus").
2. **Koffer-Code** groß (`caseCode`, nowrap), "gilt für alle 3 Koffer"
   (`prizeCount`), Start (`start.name`, Koordinaten), Koffer-Hinweis
   (`caseHint`).
3. **Wenn die App ausfällt:** die fünf Schritte aus 6.4, kurz.
4. **Stationen** (`stations`, echte Route, auch wenn der Testmodus an ist),
   je Station ein Block, der nicht über eine Seite bricht: Nummer und Name,
   "Ziffer 4" rechts, dann Ort (Breite, Länge mit 5 Nachkommastellen,
   Radius), Ortshinweis, Rätsel, Lösung (Teile von `|` als "12 oder
   zwölf"), Tipp (sonst "keiner"). Fehlt etwas (Platzhalter, keine
   Koordinaten), steht dort "fehlt" in `--err`.
5. **Teams und Laufzettel** (auf neuer Seite): Tabelle Team, Leitung, Code
   (nowrap), Mitglieder (Vornamen), fünf Kästchen für die Stationen (beim
   Drucken schon gelöste mit Haken, aus `solved`), "Platz ____" bzw. der
   Platz, wenn vergeben. Vor dem Auslosen statt der Tabelle "Noch nicht
   ausgelost."
6. **Fuß:** "Enthält alle Lösungen. Nach dem Spiel vernichten."

### 5.4 Aussehen und Druck

- Das Blatt trägt eine Klasse `.papier`, die die hellen Token fest setzt
  (wie `tse-papier` im TSE-Kanon): Es ist auf dem Bildschirm auch im dunklen
  Design hell, und der Druck sowieso.
- `@media print`: nur das Blatt (Kopfleiste, Hintergrund `.topo`,
  Navigation, Versionszeile, Meldungen ausgeblendet), Seitengrund weiß,
  `@page { size: A4; margin: 12mm }`, Überschriften nicht am Seitenende,
  Stationsblöcke `break-inside: avoid`, Teams ab neuer Seite. Zusätzlich
  setzt `@media print` für die ganze App die hellen Token, falls jemand eine
  andere Ansicht druckt.
- Schriftstufen und Radien aus MASTER.md; Kennungen (Code, Koordinaten,
  Radius, Zeiten) nowrap.
- Erwartet: 3 bis 4 A4-Seiten bei 5 Stationen und 12 Teams (Mockup mit 3
  Stationen und 3 Teams: 3 Seiten).

## 6. Ablauf (in HANDOFF "Ablauf am Eventtag" übernehmen)

### 6.1 Änderungsstopp

- **Stopp 3 Tage vor dem Event** (Datum eintragen, sobald das Eventdatum
  feststeht). Bis dahin: alle Migrationen eingespielt, Support-Nummer in
  `config.js`, lange Admin-PIN, Supabase Pro für den Event-Monat (falls so
  entschieden), Testmodus-Fragen geklärt.
- Nach dem Stopp kein Push und keine Migration, außer einem **Notfall-Fix**:
  nur für einen Fehler, der das Spiel verhindert; Prüfstand grün
  (`umbau.py`, `review1510.py`, die Skripte aus Abschnitt 7); kurzer Test auf
  einem Handy; danach die neue Version notieren.
- **Eventstand notieren:** Nach dem letzten Push die Zeile "Version …" auf
  dem Tablet ablesen und in HANDOFF eintragen.

### 6.2 Vorher

- Notfallmappe drucken, sobald Stationen, Rätsel und Lösungen fest sind
  (spätestens am Vorabend), und nach dem Auslosen noch einmal als PDF auf
  das Handy der Spielleitung sichern (dann mit Teams und Codes).
- Am Vorabend oder Morgen im Hotel-WLAN: Alle öffnen den Link einmal. Damit
  liegt die App auf jedem Handy, und iOS hält Speicher und Anmeldung 7 Tage.
- Am Treffpunkt auf zwei, drei Handys und dem Tablet die Zeile "Version …"
  mit dem notierten Eventstand vergleichen.

### 6.3 Während des Spiels

- Ein Team meldet "Keine Verbindung": weitergehen bis Netz, dann nochmal
  tippen; nichts zählt doppelt.
- Notfall-Fix gepusht: In den Team-Gruppen sagen "Seite neu laden oder im
  Tab Team unten auf „Neue Version laden“ tippen". Danach Version prüfen.
- Service Worker macht Ärger: `tools/sw-aus.js` nach `sw.js` kopieren,
  pushen, alle laden neu (1.3).

### 6.4 Totalausfall (Datenbank oder App nicht erreichbar, länger als 10 Minuten)

1. Teams melden sich per Anruf oder WhatsApp mit Teamname und Station.
2. Ortshinweis und Koordinaten der nächsten Station durchgeben, das Team
   läuft mit einer Karten-App.
3. Am Ort schickt das Team ein Gruppenfoto, dann das Rätsel vorlesen.
4. Antwort mit der Lösung vergleichen, Ziffer nennen, im Laufzettel
   abhaken.
5. An den Koffern zählt die Ankunft: Reihenfolge im Laufzettel eintragen.

Kommt die Datenbank zurück, mit "Freischalten" bzw. "Rätsel werten" im
Reiter Teams den Papierstand nachtragen; Plätze an den Koffern vergibt die
Aufsicht nach dem Laufzettel.

## 7. Prüfungen

Alle im Vordergrund mit Timeout (`timeout 300 python ...`), Ergebnis
(OK / FEHLT) vor `browser.close()` drucken.

- **`tools/pruefstand/offline.py`** (neu, ohne Leaflet-Seite): baut in einem
  eigenen Ordner index.html mit `mock.js` (wie `shoot.bauen()`, aber unter
  dem Namen `index.html`, damit der Service Worker registriert), dazu
  `sw.js`, `config.js`, `kompass-waechter.js`, `vendor/`, `hintergrund/`.
  Server auf eigenem Port. Prüft:
  1. Nach dem ersten Laden ist ein Service Worker aktiv und steuert die
     Seite; der Cache enthält `./`, `config.js`, `kompass-waechter.js`, alle
     Schriften.
  2. Keine Anfrage an fonts.googleapis.com, fonts.gstatic.com oder unpkg.com
     (Anfragen mitschneiden).
  3. Server stoppen, neu laden: App zeigt die Anmeldeseite, Schriften
     geladen (`document.fonts.check`), keine Fehler in der Konsole.
  4. Szenario Teamleitung unterwegs: einmal mit Netz laden, Server stoppen,
     neu laden: Station, Entfernung und "Stand hh:mm" stehen da (1.6).
  5. Server wieder starten, index.html anfassen (neue Änderungszeit), neu
     laden: die Versionszeile zeigt die neue Zeit (Netz zuerst).
  6. Seite offen, index.html anfassen, `visibilitychange` auslösen: Link
     "Neue Version laden" erscheint.
  7. Anfragen an `mock.invalid`/RPCs laufen nicht durch den Cache (nach
     Server-Stopp antworten sie weiter aus `mock.js`, nicht aus dem
     Service Worker).
- **`tools/pruefstand/funkloch.py`** (neu): `mock.js` bekommt einen Schalter
  `window.__netz = "weg" | "antwort-weg" | null` ("antwort-weg" führt die
  Eingabe im Beispiel-Server aus und wirft danach den Netzfehler) und bildet
  die Regeln aus 3.3 nach (`last_wrong`, `p_position`, Check-in ohne
  erneute Entfernung). Prüft je Eingabe: Meldungstext, Feld bleibt gefüllt,
  Abgleich nach dem nächsten Abruf (Erfolg mit Ziffer, "Leider falsch. Noch
  2 Versuche.", "Wieder Netz. Tippt noch mal."), dieselbe falsche Antwort
  zweimal zählt einmal, richtige Antwort wiederholt meldet Erfolg und nicht
  "Erst am Ort einchecken", Selfie hängt nicht auf "Erneut senden".
- **`tools/pruefstand/mappe.py`** (neu): Szenario Spielleitung, Reiter
  Stationen, "Notfallmappe": alle Stationen mit Lösung und Ziffer,
  Koffer-Code, Teams mit Code; im dunklen Farbschema ist das Blatt hell
  (berechnete Hintergrundfarbe); `emulate_media(media="print")`: nur das
  Blatt sichtbar; `page.pdf()` ergibt höchstens 5 Seiten; kein seitliches
  Scrollen bei 390 px; Codes und Koordinaten brechen nicht um. Öffnet keine
  Leaflet-Karte (Reiter Stationen ohne Bearbeiten).
- **`tools/pruefstand/eingaben_db.py`** (neu, Probelauf, 3.3): grün mit,
  rot `--ohne`. **`rechte_db.py`** grün.
- Bestehende Skripte bleiben grün, besonders `umbau.py` und `review1510.py`
  (Leaflet jetzt lokal) und `selfie.py`.
- **Handytest** (iPhone Safari, Android Chrome): erst mit Netz laden,
  Flugmodus, neu laden (App mit letztem Stand), Eingabe im Flugmodus
  (Meldung), Flugmodus aus (Abgleich), Push und Neuladen (Version wechselt),
  kein Installieren-Hinweis; Notfallmappe am iPad als PDF sichern.

## 8. Reihenfolge der Umsetzung

1. Leaflet und Schriften lokal (Abschnitt 2), Prüfstand grün. Unabhängig,
   sofort lieferbar.
2. Versionszeile und Versionsprüfung (4).
3. Notfallmappe (5).
4. Migration mit Probelauf (3.3), dann App-Teil (3.4) mit `funkloch.py`.
5. Service Worker und letzter Stand (1) mit `offline.py`, zuletzt, weil er
   alles Vorige mit ausliefert und die Versionszeile zum Prüfen braucht.

Ausliefern wie immer: erst die Migration einspielen
(`python tools/sql.py supabase/migrations/20261016090000_eingaben_wiederholen.sql`),
dann pushen. Alles vor dem Änderungsstopp.

## 9. Entscheidungen in dieser Spezifikation

- Nochmal tippen statt automatisch nachreichen (3.2), Abgleich zeigt, was
  ankam.
- "Doppelt zählt nichts" über die letzte falsche Antwort je Station
  (`progress.last_wrong`), nicht über eine Anfrage-Kennung: einfacher, wirkt
  auch vom Tablet und nach Neuladen, und eine absichtlich wiederholte gleiche
  Antwort nicht zu zählen schadet niemandem.
- `submit_answer` bekommt `p_position` (drop + create, Rechte ausdrücklich),
  `check_in` antwortet bei schon erfolgtem Check-in ohne neue
  Entfernungsprüfung.
- Version aus `Last-Modified` von GitHub Pages statt eines gepflegten Werts
  oder Build-Schritts.
- Netz zuerst mit 4 s für die Hülle, Cache zuerst für versionierte
  Bibliotheken, Schriften und Hintergründe.
- Letzter Stand wird nur für Teamleitung und Mitlesen gemerkt, nicht für die
  Spielleitung (Lösungen).
- Notfallmappe nur zur Laufzeit aus `admin_state`, nie als Datei im
  öffentlichen Repo; Platz im Reiter Stationen.
- Kein Update-Banner, nur der Link an der Versionszeile; kein Neuladen von
  selbst.
- Änderungsstopp 3 Tage vorher mit Notfall-Fix-Regel.
