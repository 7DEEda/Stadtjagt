# Handoff: Stadtjagd

Digital geführtes Geocaching für die TSE-Teamfahrt in **Prag**. Die Teilnehmenden
melden sich per Link an, werden per Knopfdruck in Teams ausgelost und laufen
dieselbe Route mit fünf Stationen ab. Jede Station gibt nach GPS-Check-in und
gelöstem Rätsel eine Ziffer frei. Die sechste Ziffer ist die Einerstelle der
Summe der fünf. Am Ziel stehen drei Koffer mit absteigendem Preisgeld: die
ersten drei Teams, die den vollständigen Code eingeben, bekommen Platz 1 bis 3
und je einen Koffer. Alle anderen laufen weiter und kommen mit Platz ins Ziel.

**Stand 01.10.2026, abends:** Live auf GitHub Pages, Nachträge 1 bis 27 in der
Datenbank. Seit dem 19.09. dazugekommen, jeweils mit eigenem Abschnitt am Ende
dieser Datei:

- Nachtrag 23: Geräte-Test (`geraete-test.html`, Suite 7) mit Läufen in der Datenbank
- Nachtrag 24: Kompass als Zeichen, Kompass nach dem Neuladen
- Nachtrag 25: Gruppenselfie an jeder Station (abschaltbar, Reiter „Fotos“)
- Nachtrag 26: Stationsname entschlüsselt sich mit der Annäherung, Station
  bearbeiten mit Karte, Einmessen als Fenster
- ohne Migration: Hinweis bei ungefährem Standort, Mitlese-Link als QR-Code,
  Kompass nach einer Pause, Lücken in der Route gestrichelt, Bedienung mit dem
  Finger am Tablet, Testmodus spielt das Entschlüsseln vor
- Nachtrag 27 (01.10.): Befunde der UI-Kritik, Zifferntastatur bei Zahlenlösungen,
  Hochformat-Hinweis
- ohne Migration (01.10.): Design System (`design-system/`), Schalter
  hell/dunkel, Schriftstufen `--fs-*`

**Die Datenbank ist gerade im Probebetrieb, nicht leer:** Status „running“,
Testmodus an, zwei Teams (Fuchs, Wolf) aus Friedrichs Durchgang am 30.09.,
Gruppenselfie eingeschaltet, alle fünf Stationen mit Kreisen fürs Entschlüsseln
(Vorschlag 60 % und 30 % der Etappe, von Claude am 30.09. eingetragen). Vor dem
Event: Fortschritt zurücksetzen, Testdaten entfernen, **Testmodus aus**,
Löschdatum für die Fotos setzen. In `device_test_runs` liegt außerdem der
Kontroll-Lauf ABK2 vom Laptop.

**Offen, weil nur am echten Gerät zu klären** (alles andere ist im Prüfstand
geprüft):

- Gruppenselfie: Frontkamera geht auf, Foto steht richtig herum, „Foto
  speichern“ landet in der Galerie (Android und iPhone)
- iPhone: „Wach halten“ wurde verweigert, ohne Stromsparmodus. Der Schritt
  „Wach halten, mit Tipp“ im Geräte-Test klärt, ob die Sperre einen Fingertipp
  braucht; das Spiel versucht sie vorsorglich bei jedem Tipp
- iPhone nach dem Neuladen: Hinweis „Kompass ist nach dem Neuladen aus“ nach
  etwa drei Sekunden, Tipp wirkt
- iPhone mit ungefährem Standort: Hinweis erscheint, nach dem Umstellen klappt es
- Android: Kompass nach einer Pause. Der Schritt „Kompass nach Pause“ misst,
  ob die Richtung bei ruhigem Handy nachwandert; davon hängt ab, ob fünf
  Sekunden Einmessen reichen
- Verschlüsselter Name draußen: löst er sich beim Hinlaufen auf, bleibt die
  Zeile ruhig
- Tablet: Tastatur verdeckt keine Knöpfe, Griffe auf der Stationskarte lassen
  sich ziehen, ohne dass die Seite scrollt
- QR-Code des Mitlese-Links mit einer Handykamera scannen
- **Offen (02.10., Friedrich): Stresstest mit 100 Geräten.** Prüfen, ob
  Supabase (Anmeldung, team_state-Abfragen alle paar Sekunden, report_position,
  Selfie-Uploads, Realtime) 100 gleichzeitige Handys trägt; Antwortzeiten und
  Fehlerquote messen, Grenzen des Supabase-Tarifs (Verbindungen, Anfragen)
  gegenprüfen. Vorschlag: Lastskript, das 100 gespielte Handys gegen eine
  Kopie der Datenbank oder im Testmodus laufen lässt.

**Befund vom 29.09., erledigt am 02.10.:** Ändert die Spielleitung im laufenden
Spiel die Ziffer einer Station, die Teams schon gelöst haben, ändert sich deren
Ziffer lautlos mit, und der Koffer verlangt die neue. Jetzt fragt `a-save` in
dem Fall nach (`DANGER.ziffer`): nennt alte und neue Ziffer und die betroffenen
Teams. Abbrechen lässt das Getippte im Formular stehen. Test:
`python tools/pruefstand/ziffer.py`.
- Hochformat-Hinweis am Handy: erscheint quer nach einer halben Sekunde, nicht
  beim Einmessen
- **Nächster Schritt (01.10.):** ein Kollege mit modernem iPhone macht den
  Geräte-Test (`https://7deeda.github.io/Stadtjagt/geraete-test.html`, in
  Safari öffnen, nicht aus der WhatsApp-Vorschau). Danach
  `python tools/testlaeufe.py` und auswerten: Wake Lock mit Tipp, genauer
  Standort, Kamera, Kompass nach Pause

Befunde aus vier Läufen des Geräte-Tests (`testlaeufe/UEBERSICHT.md`, nicht im
Repo): Standort, Kompass, Kamera und Wake Lock gehen auf drei Android-Handys
(Chrome und Edge). Vibration wurde auf keinem gespürt und fehlt auf iPhones
ganz: nichts darauf bauen. Mitteilungen brauchen auf Android einen Service
Worker und gibt es auf dem iPhone nur als installierte App. Das eine iPhone
lieferte nur den ungefähren Standort (Einstellung) und verweigerte Wake Lock.

**Betrieb, am 30.09. gelernt:**

- Commits in diesem OneDrive-Ordner scheitern mit „unable to append to
  .git/logs“. Abhilfe je Aufruf: `git -c windows.appendAtomically=false commit …`
  und ebenso `push`. Dauerhaft gesetzt ist es nicht.
- Der Pages-Lauf kann bei GitHub scheitern („Fetching artifact metadata
  failed“). Stand der Läufe ohne Anmeldung:
  `https://api.github.com/repos/7DEEda/Stadtjagt/actions/runs`. Neu anstoßen
  mit einem leeren Commit.
- Migrationen erst als Probelauf (`tools/pruefstand/selfie_db.py`,
  `name_db.py`): ein DO-Block, der die Migration einspielt, prüft und mit einem
  absichtlichen Fehler alles zurücknimmt. Danach `tools/sql.py <datei>`.
- Kartenkacheln von OpenStreetMap kommen nur bei Seiten mit Absender an. Ein
  Mockup direkt von der Platte zeigt „Access blocked“.
- `dist_m` und andere interne Funktionen sind auch für den Management-Zugang
  gesperrt; Entfernungen für Auswertungen lokal rechnen.
- Die App nimmt von `rpc()` nur JSON-Objekte an. Eine Funktion, die nackten
  Text liefert, gilt als Fehlantwort: immer `json_build_object(...)`.
- Die vier Dateien mit `-nb-f-reiss` im Namen sind OneDrive-Konfliktkopien vom
  Notebook und gehören nicht ins Repo. Bisher nicht angefasst.
- Python-Pakete fürs Prüfen, am 30.09. installiert: `playwright`, `segno`,
  `zxing-cpp`, `pillow`.

**Stand 19.09.2026, abends (überholt, zur Geschichte):** Live auf GitHub Pages, Datenbank eingerichtet,
Nachträge 1 bis 22 live (6: drei Koffer, 7: Testmodus, 11: Mitlesen, 12: Anmeldung
bis zum Auslosen, 13: Randfälle, 14: Teamleitung und Mitlese-Link, 17:
Spieldauer, Tipp, Koffer-Hinweis, 18: Teamleitung ohne Code, 19: Hintergrund
umschaltbar, 20: Funde der Bugjagd, 21: UI-Durchsicht mit Zustand der Teams,
22: ein Handy, eine Person, kein Code; 22 ist nur Frontend; Überblick in
[SPIEL.md](SPIEL.md)). Kein aktives Spiel, Datenbank leer, Status
Anmeldung, aktiver Hintergrund A. Die Fahrt ist Ende April 2027. **Neue Route am 18.09.2026:** Start am Hotel Mama Shelter in
Holešovice, dann Planetarium, Rudolfstollen, Wasserturm Letná, Bergstation der
Aussicht Letná (ehemalige Bergstation der Standseilbahn), Metronom (siehe „Route“). Die Orte stehen in
`supabase/seed-stationen-prag.sql` und seit 18.09.2026 auch in der Datenbank,
mit Platzhaltern statt Rätseln. Offen sind Rätsel und Ortshinweise, der
Praxistest draußen und die echte WhatsApp-Nummer für den Hilfe-Knopf (bis dahin
steht die Testnummer 0172 0000000 drin).

Spielregeln, Zustände, Abläufe und Code-Aufbau in geordneter Form: `SPIEL.md`.
Diese Datei ist das fortlaufende Protokoll mit Zugängen und Entscheidungen.

## Stack und Aufbau

| Teil | Technik | Datei |
|---|---|---|
| Frontend | eine HTML-Datei, kein Framework, kein Build | `index.html` |
| Verbindung | Supabase-URL, Publishable key, Support-Nummer | `config.js` |
| Backend | PostgreSQL-Funktionen (`security definer`) in Supabase | `supabase/migrations/*.sql` |
| Karte | Leaflet 1.9.4 mit OpenStreetMap, per CDN | in `index.html` |
| Hosting | GitHub Pages über Actions | `.github/workflows/pages.yml` |

Es gibt bewusst keine Edge Functions, kein React, kein npm. Die gesamte
Spiellogik liegt in der Datenbank, das Frontend ruft ausschließlich
RPC-Endpunkte auf.

### Alle Dateien

```
index.html                      die komplette App, kein Build nötig
config.js                       Supabase-Zugang und WhatsApp-Nummer
geraete-test.html               Geräte-Test: prüft auf einem Handy alles, was das Spiel braucht (Nachtrag 23)
geraete-tests.js                die Suite dazu, ein Baustein je Test
kompass-test.html               leitet auf geraete-test.html weiter
tools/testlaeufe.py             Läufe des Geräte-Tests nach testlaeufe/ holen
tools/sql.py                    SQL an die Datenbank schicken, ohne den SQL-Editor
supabase/migrations/            Schema und Spiellogik, in dieser Reihenfolge einspielen
  20260918120000_init.sql         Tabellen, Rechte, alle Funktionen
  20260918150000_where_clauses.sql  WHERE-Klauseln für pg-safeupdate
  20260918160000_routes.sql       Verlaufstabelle, admin_tracks, Beenden löscht nicht mehr
  20260918170000_draw_size.sql    Auslosen mit Teamgröße oder Teamzahl
  20260918180000_tiernamen.sql    Tiernamen mit Emoji, ohne Umlaute
  20260918190000_anmeldung_leeren.sql  alle Teilnehmenden auf einmal löschen
  20260918200000_drei_koffer.sql  Plätze 1 bis 3 statt eines Siegers
  20260918210000_testmodus.sql    Durchklicken ohne Entfernung und Rätsel
  20260918220000_durchsicht.sql   Code ohne Bindestrich, Namenssuche, Positionsprüfung
  20260918230000_viele_namen.sql  viele Namen auf einmal, Testdaten
  20260919000000_nachmelden.sql   Nachzügler melden sich selbst an
  20260919010000_mitlesen.sql     das ganze Team liest mit (Geräte-Schlüssel)
  20260919020000_anmeldung_bis_auslosen.sql  Selbstanmeldung wieder nur bis zum Auslosen
  20260919030000_wasserdicht.sql  Koffer-Code nur am Ziel, Fortsetzen, Rätsel werten, mehrere Lösungen, Testdaten entfernen
  20260919040000_leitung_und_mitlesen.sql  Teamleitung zuweisen und abgeben, Mitlese-Link je Team
  20260919050000_review.sql       name_key nachgezogen, Fehlversuche unter Zeilensperre (Code-Review)
  20260919060000_start_im_testmodus.sql  Starten im Testmodus wieder erlaubt, mit Warnung
  20260919070000_koffer_hinweis_spieldauer.sql  Koffer-Hinweis, Spieldauer mit Countdown, Tipp je Station
  20260919080000_leitung_ohne_code.sql  Teamleitung loggt sich über den Geräte-Schlüssel ein (leader_code)
  20260919090000_hintergrund.sql  Hintergrund umschaltbar (game_state.background, admin_set_background)
  20260919100000_bugjagd.sql      Funde der Bugjagd: norm mit Háček, Sperren beim Auslosen, Station beim Werten, lange PIN
  20260919110000_team_zustand.sql admin_state mit checkedInAt und lastSolvedAt (Zustandszeile im Reiter Teams)
hintergrund/a.svg, b.svg, c.svg  die drei Hintergrund-Varianten, werden nachgeladen
supabase/seed-stationen-prag.sql  die fünf Prager Stationen (Route Holešovice, Letná)
supabase/seed-personen.sql      100 erfundene Teilnehmende, nur zum Proben
mockups/kompass-einmessen.html  Entwurf für das Einmessen des Kompasses
mockups/karte-routen.html       Entwurf für Routen und Zeitachse, vor der Umsetzung,
                                zeigt noch Berlin. Historisches Dokument, keine Doku.
supabase/config.toml            Projektdatei der Supabase CLI, hier ungenutzt
.github/workflows/pages.yml     Deployment auf GitHub Pages
README.md                       Kurzfassung fuer den Einstieg
HANDOFF.md                      diese Datei
```

## Sicherheitsmodell

Das ist der Kern, hier bitte nichts aufweichen:

- Alle Tabellen haben RLS aktiviert und **keine** Policies. Clients können also
  keine Tabelle direkt lesen oder schreiben.
- Zugriff läuft nur über Funktionen mit `security definer`, für die `anon` das
  Ausführungsrecht hat.
- Lösungen, Ziffern und der Koffercode verlassen die Datenbank nie. Der
  Rätseltext wird erst nach erfolgreichem Check-in ausgeliefert, eine Ziffer
  erst nach richtiger Antwort.
- Plätze werden atomar vergeben: `submit_final` sperrt die Zeile in
  `game_state` (`for update`), gleichzeitige Eingaben warten also
  hintereinander, und `finishes.place` ist zusätzlich `unique`. Zwei Teams
  können nie denselben Platz bekommen. Geprüft mit zehn gleichzeitigen
  Eingaben, siehe „Drei Koffer“.
- Die Admin-PIN wird serverseitig in `require_admin()` geprüft, nicht im Browser.
- Mitlesen geht nur mit dem Geräte-Schlüssel aus der eigenen Anmeldung
  (`participants.token`), nie über den Namen: Namen sind öffentlich, und alle
  Teams lösen dieselben Rätsel mit denselben Ziffern. `member_state` liefert
  keinen Team-Code; eingeben (Check-in, Antwort, Koffer-Code) geht weiter nur
  mit dem Team-Code.
- Team-Codes bestehen aus Tiername und vier Ziffern (`FUCHS-4711`) und stehen
  **nicht** in der öffentlichen Antwort.

Bekannte, bewusst akzeptierte Schwächen:

- Positionen kommen vom Gerät und lassen sich mit Entwicklerwerkzeugen
  fälschen. Für ein Firmenevent akzeptabel.
- Wer einen Team-Code kennt, kann für dieses Team mitspielen. Die Codes gibst du
  nur an die Teamleitungen.
- Die Admin-PIN liegt im Klartext in `game_state.admin_pin`.
- Die Support-Nummer in `config.js` ist öffentlich, siehe „Hilfe für die
  Teilnehmenden“.

## Datenmodell

- `participants` – Name, `name_key` (normalisiert, unique), `team_id`
- `teams` – Name, Code, `leader_participant_id`
- `stations` – `position` 1–5, Name, `lat`, `lng`, `radius_m`, `location_hint`,
  `riddle`, `answer`, `digit`
- `progress` – je Team und Station: `checked_in_at`, `solved_at`,
  `failed_attempts`, `locked_until`
- `team_positions` – letzte bekannte Position je Team
- `position_log` – jeder gemeldete Punkt, daraus entstehen die Routen
- `finishes` – je Team `place` (unique) und `finished_at`, entsteht beim
  richtigen Koffer-Code, verschwindet mit dem Team (`on delete cascade`)
- `game_state` – Einzelzeile mit `status` (`registration` → `drawn` → `running`
  → `finished`), `winner_team_id` (Platz 1), `prize_count` (Zahl der Koffer,
  Vorgabe 3), `admin_pin`

## RPC-Endpunkte

Öffentlich: `public_state`, `register_participant`, `lookup_participant`,
`member_state` (mit Geräte-Schlüssel)

Team: `team_state`, `check_in`, `submit_answer`, `submit_final`,
`report_position`

Admin (alle mit PIN): `admin_state`, `admin_tracks`, `admin_draw`,
`admin_start`, `admin_finish`, `admin_reset`, `admin_clear_positions`,
`admin_clear_participants`, `admin_add_participant`,
`admin_rename_participant`, `admin_delete_participant`, `admin_save_station`,
`admin_unlock_station`, `admin_set_pin`, `admin_set_test_mode`,
`admin_add_participants`

`admin_draw` hat seit Nachtrag 3 drei Parameter: `(p_pin, p_teams, p_size)`.
Die alte Fassung mit nur einem Parameter wurde entfernt, sonst wüsste PostgREST
bei einem Aufruf mit nur der PIN nicht, welche gemeint ist.

Hilfsfunktionen ohne Ausführungsrecht für `anon`: `norm`, `dist_m`,
`team_by_code`, `current_station`, `require_admin`.

## Ansichten

- `#/public` – Anmeldung mit Namensfeld, nach der Auslosung Namenssuche, nach
  Spielende Rangliste
- `#/team` – Login per Team-Code, Zahlenschloss, Ortshinweis, Kompass mit
  Entfernung, Check-in, Rätsel, Endcode
- `#/admin` – Karte, Teams, Teilnehmende, Stationen, Daten löschen; oben
  Auslosen, Starten, Beenden. **Seit 18.09.2026 nicht mehr in der Fußzeile der
  Teilnehmenden verlinkt:** die Spielleitung öffnet
  https://7deeda.github.io/Stadtjagt/#/admin direkt, am besten als Lesezeichen
  auf dem Tablet.

Jedes Team hat ein Tier-Emoji, passend zum Namen. Die Namen kommen aus
`admin_draw`, die Emoji aus `TEAM_EMOJI` in `index.html`. Beide Listen müssen
zusammenpassen, sonst erscheint eine Pfote als Platzhalter. Aktuell: Fuchs,
Wolf, Eule, Tiger, Panda, Einhorn, Flamingo, Pinguin, Delfin, Adler, Igel,
Otter, Krake, Biber, Koala, Drache. Alle ohne Umlaute, damit die Team-Codes auf
jeder Handytastatur leicht zu tippen sind.

Der Hintergrund ist eine gezeichnete Wanderkarte mit Höhenlinien, Fluss,
gestrichelten Wegen und Wegpunkten. Das SVG ist erzeugt, nicht von Hand
gesetzt; das Skript dazu liegt nicht im Repo, die Formen sind fest eingebaut.
Farben kommen aus den vorhandenen Token, die Klassen heißen `c` und `c5` für
Höhenlinien, `w` und `wl` für Wasser, `t` für Wege, `p` für Wegpunkte.

## Route

Start ist der Treffpunkt, kein Datensatz: Hotel Mama Shelter Praha,
Veletržní 1502/20, Praha 7-Holešovice, 50.102458, 14.431681.

| Nr. | Station | Tschechisch | Koordinaten | Luftlinie davor |
|---|---|---|---|---|
| 1 | Planetarium Prag | Planetárium Praha | 50.105286, 14.427406 | 440 m ab Start |
| 2 | Rudolfstollen | Rudolfova štola | 50.104441, 14.419553 | 570 m |
| 3 | Wasserturm Letná | Vodárenská věž Letná | 50.100195, 14.420089 | 470 m |
| 4 | Aussicht Letná, ehemalige Bergstation | Horní stanice lanové dráhy Františka Křižíka (Standseilbahn 1891 bis 1916, heute Aussichtspunkt an der Treppe) | 50.095789, 14.425346 | 620 m |
| 5 | Metronom | Pražský metronom | 50.094775, 14.415938 | 680 m |

Zusammen rund 2,8 km Luftlinie, zu Fuß eher 3,5 km, dazu der Anstieg aus der
Stromovka auf die Letná. Die Stationsnamen sieht das Team vor dem Check-in, die
Ortshinweise sind das eigentliche Rätsel für den Weg; der Hinweis der Station 5
erscheint am Ende als Hinweis auf den Koffer.

Noch offen: Rätsel mit Lösungen, Ortshinweise, wo der Koffer steht. Bis dahin
stehen in der Seed-Datei Platzhalter mit leerer Lösung; eine leere Lösung zählt
nie als richtig. Eingespielt am 18.09.2026 mit `tools/sql.py`; ein erneutes
Einspielen überschreibt die fünf Stationen, also auch später im Reiter Stationen
eingetragene Rätsel.

Hintergrund-Variante B zeigt noch die alte Altstadt-Route. Für die neue muss der
Ausschnitt nach Norden wandern (Mitte etwa 50.100, 14.4235), dafür die OSM-Daten
mit einem Rahmen bis etwa 50.132 neu laden und die Stationen in
`tools/hintergrund/hintergrund.py` tauschen.

## Drei Koffer

Seit Nachtrag 6 gibt es statt eines Siegers Plätze. `game_state.prize_count`
sagt, wie viele Koffer es gibt (Vorgabe 3, ändern per SQL). Alle Koffer haben
denselben Code aus den Ziffern; wer welchen bekommt, entscheidet der Platz in
der App. Deshalb steht jemand von der Spielleitung bei den Koffern und gibt den
passenden erst frei, wenn das Team den Platz-Bildschirm zeigt.

- **Code richtig:** `submit_final` vergibt den nächsten freien Platz. Wer ihn
  noch einmal eingibt, behält seinen Platz. Platz 1 steht zusätzlich in
  `winner_team_id`, damit Bestehendes nicht bricht.
- **Das Spiel läuft weiter**, auch nach dem dritten Koffer. Die übrigen Teams
  kommen mit Platz ins Ziel. Früher sprang das Spiel beim ersten richtigen
  Code auf `finished`, und alle anderen sahen „Ein anderes Team war schneller“.
- **Spiel beenden** bleibt bei der Spielleitung. Danach nimmt `submit_final`
  keine Codes mehr an; wer bis dahin nicht im Ziel war, steht in der
  Rangliste nach gelösten Stationen.
- **Anzeige:** Die Team-Ansicht zeigt vor der Eingabe, wie viele Koffer noch
  übrig sind, danach Platz und Medaille (🥇🥈🥉) oder 🏁 ab Platz 4. Die
  öffentliche Seite zeigt während des Spiels live den „Zieleinlauf“, nach dem
  Ende die Rangliste. Im Admin-Bereich stehen Platz und Uhrzeit bei den Teams
  und in der Zeitachse.
- **Zurücksetzen:** „Spiel starten“ und „Fortschritt zurücksetzen“ leeren die
  Plätze. Auslosen und „Alle löschen“ löschen die Teams, die Plätze gehen mit.

Getestet am 18.09.2026 gegen ein lokales PostgreSQL 15 mit allen Migrationen:
26 Prüfungen, darunter falscher Code, doppelte Eingabe, Platz 4 ohne Koffer,
Eingabe nach dem Beenden, Zurücksetzen, ein erzwungener Wettlauf (Team B
wartet nachweislich, bis A fertig ist, und bekommt Platz 2) und zehn Teams
gleichzeitig (Plätze 1 bis 10 je genau einmal). Dazu die Oberfläche im Browser
über eine lokale Nachbildung der Supabase-Schnittstelle. Nach dem Einspielen
live geprüft: `public_state` liefert `prizeCount` und Plätze, `finishes` ist
für `anon` gesperrt. Die Testskripte liegen nicht im Repo.

## Team finden nach dem Auslosen

Wer sich auf seinem Handy angemeldet hat, sieht nach dem Auslosen innerhalb von
etwa zehn Sekunden „Dein Team“: das Tier-Emoji groß auf einem Kreis in der
Teamfarbe, Teamname, Teamleitung und Mitglieder. Die Farbe ist dieselbe wie auf
der Karte der Spielleitung (beide sortieren die Teams nach Namen).
„Zum Hochhalten“ füllt den ganzen Bildschirm mit Teamfarbe, riesigem Emoji und
Namen, damit sich die Gruppen auf dem Platz finden; Antippen schließt. Solange
das offen ist, bleibt der Bildschirm an, wo der Browser die Wake-Lock-API kann.
Angesprochen wird nur mit Vornamen („Du bist dabei, Anna.“, „Dein Team, Anna“), Listen zeigen den vollen Namen.
Wer auf einem fremden Handy angemeldet wurde, sucht seinen Namen unter „In
welchem Team bin ich?“ und bekommt dieselbe Karte.

Neu auslosen und Löschen ziehen die Handys selbst nach (behoben 18.09.2026):

- Die angezeigte Karte liest das Team bei jeder Abfrage neu aus den
  Teamlisten in `public_state`. Nach einem Neu-Auslosen steht nach spätestens
  zehn Sekunden das neue Team da, auch in der Vollbild-Ansicht.
- Die Team-Ansicht meldet sich ab, wenn der Code nicht mehr gilt, und sagt
  „Dieser Team-Code gilt nicht mehr, vermutlich wurde neu ausgelost“. Vorher
  zeigte sie still das alte Team weiter.
- Nach „Alle löschen“ prüft die Anmeldeseite, ob der im Handy gespeicherte
  Name noch angemeldet ist (beim Laden und wenn die Zahl der Angemeldeten
  sinkt). Wenn nicht, erscheint wieder das Anmeldeformular statt „Du bist
  dabei“.

## Das ganze Team liest mit (Nachtrag 11)

Alle im Team sehen ab dem Start auf der Anmeldeseite, was die Teamleitung sieht:
Station, Ortshinweis, Kompass und Entfernung (mit dem eigenen GPS), das Rätsel
nach dem Check-in, Fehlversuche und Denkpause, die Ziffern, beim Koffer das volle
Zahlenschloss, am Ende Platz und Medaille. Eingeben kann nur die Teamleitung;
an den Stellen steht dann etwa „Einchecken macht Silke“ oder „Die Antwort gibt
Silke ein“. Vor dem Start zeigt die Team-Karte auch Mitgliedern den
Übungskompass zur TSE AG.

Wie das Handy sein Team kennt: `register_participant` gibt einen zufälligen
Geräte-Schlüssel zurück (64 Hex-Zeichen), die App speichert ihn als `sj.token`.
`member_state(p_token)` liefert damit `team_state` ohne Team-Code, alle zehn
Sekunden neu. Mitglieder teilen ihren Standort nicht, nur die Teamleitung.

Wer von der Spielleitung eingetragen wurde (Nachzügler im Admin-Bereich,
Sammeleingabe, Testdaten) oder sich vor Nachtrag 11 angemeldet hat, hat
keinen Schlüssel und sieht nur die Team-Karte. Abhilfe wäre ein Mitlese-Link
auf dem Handy der Teamleitung; gebaut ist das noch nicht.

`teamAnsicht(st, lesen)` in `index.html` baut beide Ansichten; `lesen` blendet
die Eingaben aus. Die Ansicht der Teamleitung (`#/team`) ist unverändert.

## Teamsuche nur, wo das Handy sein Team nicht kennt (18.09.2026)

„In welchem Team bin ich?“ steht groß nur noch auf Handys, die ihr eigenes Team
nicht kennen: von jemand anderem angemeldet, von der Spielleitung nachgetragen,
oder ein anderer Browser als bei der Anmeldung (häufig: Link in WhatsApp
geöffnet, später in Safari). Handys mit „Dein Team“ zeigen nur einen kleinen
Link „Anderes Team nachschauen“; das Ergebnis steht dann darunter, die eigene
Karte bleibt. Wer sein Team über die Suche gefunden hat, kann mit „Das bin
ich, merken“ den Namen auf dem Handy speichern (nur Anzeige, kein Mitlesen:
dafür fehlt der Geräte-Schlüssel). Nach der Anmeldung steht der Hinweis, die
Seite später im selben Browser zu öffnen, am besten per Lesezeichen.

## Anmeldung nur bis zum Auslosen (Nachtrag 12, ersetzt Nachtrag 10)

Nachtrag 10 hatte die Selbstanmeldung bis zum Spielende geöffnet. Zusammen mit
dem Mitlesen (Nachtrag 11) war das eine Lücke: Wer mitten im Spiel einen
erfundenen Namen anmeldete, bekam einen Geräte-Schlüssel und las bei dem Team
mit, in das er kam. Alle Teams haben dieselben Ziffern, also genügte ein
schnelles Team für den Koffer-Code.

Seit 18.09.2026 schließt die Selbstanmeldung wieder mit dem Auslosen. Danach
zeigt die Anmeldeseite unter „Noch nicht angemeldet?“ nur die Hilfe-Knöpfe
(WhatsApp mit „Ich bin noch nicht angemeldet. Mein Name:“), die Spielleitung
trägt Nachzügler im Reiter Teilnehmende ein (ins kleinste Team). Solche
Nachzügler lesen nicht mit, sie sehen ihr Team über die Namenssuche.

Übrig bleibt: Vor dem Auslosen könnte jemand zusätzlich einen erfundenen Namen
anmelden. Das Los entscheidet das Team, ein Handy behält nur den Schlüssel der
letzten Anmeldung, und der Name steht sichtbar in der Liste. Deshalb steht
beim Auslosen die Zahl der Angemeldeten groß mit dem Hinweis, sie mit der
Gästeliste abzugleichen.

Auf der Team-Karte öffnet auch ein Tipp aufs große Emoji die Vollbild-Ansicht
zum Hochhalten.

## Nachzügler melden sich selbst an (Nachtrag 10, abgelöst durch Nachtrag 12)

Die Anmeldung bleibt bis zum Spielende offen. Vor dem Auslosen wie bisher ohne
Team; danach kommt die Person ins gerade kleinste Team, und `register_participant`
gibt das Team gleich mit zurück (Name, Leitung, Mitglieder, kein Team-Code).
Die Anmeldeseite zeigt nach dem Auslosen unter der Teamsuche „Noch nicht
angemeldet?“, nur auf Handys, auf denen noch niemand angemeldet ist; nach dem
Nachmelden erscheint sofort die große Team-Karte. Nach „Spiel beenden“ lehnt die
Datenbank ab: „Das Spiel ist vorbei, die Anmeldung ist geschlossen.“

## Viele Namen und Testdaten (Nachtrag 9)

Reiter Teilnehmende, Bereich „Mehrere auf einmal“: ein Name pro Zeile, dann
„Alle eintragen“. `admin_add_participants` überspringt leere Zeilen, Doppelte
(auch innerhalb der Liste) und Namen außerhalb von 2 bis 60 Zeichen und meldet,
wie viele es waren. Sind schon Teams ausgelost, kommt jede neue Person ins
gerade kleinste Team.

„Testdaten einfügen“ trägt 90 erfundene Namen mit dem Zusatz „(Test)“ ein,
etwa „Anna Brand (Test)“. Die Suche findet sie mit „Test“, einzeln löschen geht
über das ×, alle zusammen über „Alle löschen“. **Vor dem Event wegräumen.**

## Durchsicht der Bedienung (18.09.2026)

Alle Ansichten durchgeklickt: Teilnehmende auf iPhone SE, 360 und 320 px,
Spielleitung auf dem Tablet hoch und quer, hell und dunkel. Behoben:

- **„Spiel beenden“ fragt nach** (Dialog wie beim Löschen, ohne getipptes Wort).
  Vorher beendete ein Tipp das Spiel für alle, danach nahm die App keine
  Koffer-Codes mehr an.
- **Abmelden** ist ein kleiner Link mit Rückfrage und steht jetzt in jeder
  Team-Ansicht, auch vor dem Start, am Koffer und nach dem Ende.
- **Denkpause** nach drei Fehlversuchen: Feld und Knopf gesperrt, Countdown in
  Sekunden, danach wieder frei. Vorher stand dort „Fehlversuche 0/3“.
- **Eingaben bleiben stehen**, wenn etwas schiefgeht (Anmeldung, Teamsuche,
  Team-Code, Antwort, Koffer-Code). Vorher leerte das Neuzeichnen das Feld.
- **Team-Code** geht auch ohne Bindestrich und klein (Nachtrag 8), das Feld hat
  keine Autokorrektur mehr.
- **Teamsuche** findet Namensteile; bei mehreren Treffern kommen bis zu acht
  Namen zum Antippen. Nach dem Auslosen zeigt die Anmeldeseite das eigene Team
  von selbst („Dein Team“), der Name ist von der Anmeldung bekannt.
- **Wartebildschirm** vor dem Start: „Standort und Kompass freigeben“, das
  Einmessen läuft dort schon, beim Startsignal ist alles bereit. Dazu ein
  Kompass mit Übungsziel **TSE AG, Bergiusstraße 52, 12057 Berlin**
  (52.46175, 13.46070, Adresse laut Impressum, Koordinaten aus
  OpenStreetMap). So lassen sich Pfeil und Entfernung vor dem Start
  ausprobieren; aus Prag zeigt er rund 271 km nach Nordnordwest. Das Ziel
  steht als `PROBEZIEL` in `index.html`, ab dem Start zeigt der Pfeil auf die
  Station. Entfernungen ab 10 km zeigt die App in ganzen Kilometern.
- **Kompass** zeigt ein Fragezeichen statt eines grauen Pfeils, solange keine
  Richtung bekannt ist.
- **Positionen:** App und Datenbank verwerfen 0/0, Genauigkeit 0 und schlechter
  als 1 km; die Karte der Spielleitung ignoriert Punkte über 30 km von der
  Route. Vorher zog ein einziger 0/0-Punkt die Karte auf den halben Globus.
- **Karte:** Stationsmarken liegen über den Team-Symbolen.
- **Zeitachse:** kurze Platzmarke (Medaille), am rechten Rand nach innen
  gezogen, statt in die Zeitspalte zu laufen.
- **Reiter Teams:** im Spiel nach Platz und Fortschritt sortiert; der große
  rote „Fortschritt zurücksetzen“ steht nicht mehr oben, nur noch im Reiter
  Daten löschen.
- **Reiter Stationen:** fehlender Ortshinweis, Rätsel, Lösung oder Standort ist
  rot markiert, oben steht, welche Stationen noch nicht fertig sind. Die
  Platzhalter „Ortshinweis folgt“ und „Rätsel folgt“ zählen als fehlend.
- **Reiter Teilnehmende:** Suche nach Name oder Team, × in Fingergröße,
  beim Nachzügler die Rückmeldung, in welches Team er gekommen ist.
- **Tippziele** mindestens 42 px (kleine Knöpfe, Links, Fußzeile).
- **Texte:** „Noch 1 Versuch.“, freundlicher Hinweis bei doppeltem Namen,
  Erfolgsmeldungen verschwinden nach etwa zehn Sekunden, bei ignorierter
  GPS-Erlaubnis ein passender Hinweis statt „Signal schwach“.

- **Reihenfolge der Team-Ansicht unterwegs** (entschieden 18.09.2026,
  Variante B aus `mockups/team-reihenfolge.html`): Station, Entfernung, Pfeil
  und „Wir sind da“ stehen oben, darunter „Eure Ziffern“ mit kleinen Rädern und
  Fortschritt. Groß erscheint das Zahlenschloss nur noch beim Koffer, auf dem
  Platz-Bildschirm und nach dem Ende. Vorher schnitt auf einem iPhone SE in
  Safari (rund 548 px sichtbar) die Kante mitten durch die Entfernung.

Getestet lokal gegen PostgreSQL 15 (21 Prüfungen zu Nachtrag 8, dazu wieder
Koffer und Testmodus) und in der Oberfläche; Nachtrag 8 live eingespielt und
über die öffentliche Schnittstelle geprüft.

## Testmodus

Zum Durchklicken am Schreibtisch, seit Nachtrag 7. Schalter im Admin-Bereich,
Reiter Stationen, ganz oben; gespeichert in `game_state.test_mode`.

- **An:** Check-in ohne Entfernungsprüfung, auch ganz ohne GPS; jede Antwort
  zählt, auch ein leeres Feld; die Denkpause nach drei Fehlversuchen entfällt.
  Der Koffer-Code wird weiter geprüft, er steht ja im Zahlenschloss.
- **Sichtbar:** rotes „Testmodus an“ im Kopf der Spielleitung, roter Hinweis
  oben in der Team-Ansicht.
- **Vor dem Event ausschalten.** Sonst kommt jedes Team ohne Laufen und ohne
  Rätsel an alle Ziffern.
- **Nebenbei behoben:** `check_in` ohne Koordinaten ging vorher durch, weil die
  Entfernung dann `null` ist und `null > Toleranz` nie wahr wird. Außerhalb des
  Testmodus braucht der Check-in jetzt einen Standort.

Getestet am 18.09.2026 lokal: 25 Prüfungen zum Testmodus, dazu erneut die 26
Koffer-Prüfungen, und ein Durchlauf aller fünf Stationen in der Oberfläche ohne
GPS und mit leeren Antworten.

## Hintergrund: Varianten umschaltbar (Nachtrag 19, 19.09.2026)

Die drei Entwürfe vom 18.09.2026 sind eingebaut: `hintergrund/a.svg`, `b.svg`,
`c.svg` im Repo, „klassisch“ ist die bisherige Wanderkarte im HTML. Die
Spielleitung wählt im Reiter Stationen („Hintergrund“, `admin_set_background`,
`game_state.background`); `public_state`, `team_state` und `admin_state` tragen
das Feld, `render()` lädt die Datei nach (`hintergrundSetzen`) und merkt sich
die Wahl als `sj.bg`, damit der nächste Aufruf gleich richtig startet. Alle
Linien sind `vector-effect: non-scaling-stroke`, Beschriftungen fallen ab 700 px
Breite weg. Freier Text ohne Karte darunter (Kopfzeile, Reiter, „Mitglieder“,
„Hilfe von der Spielleitung“, Links) hat einen Lichthof in Papierfarbe
(`text-shadow`), damit er auf jeder Variante lesbar bleibt; Knöpfe, Felder und
Karten setzen ihn zurück. Geprüft hell und dunkel auf allen vier.

**Parallax (19.09.2026):** Die Karte ist um `--px-hub` (40lvh) höher als das
Fenster und wandert beim Scrollen nach oben, über die ganze Seitenlänge genau
um diesen Überstand. Ohne Skript: eine scroll-gebundene CSS-Animation
(`animation-timeline: scroll(root)`), die der Browser im Compositor rechnet.
Die erste Fassung per JavaScript ruckelte und sprang auf Android, sobald
Chrome die Adressleiste ein- oder ausblendete (`innerHeight` änderte sich);
darum jetzt `lvh`-Einheiten, die davon unabhängig sind. Am Seitenende schließt
die Karte exakt mit dem Fensterrand ab. Browser ohne `animation-timeline`
(ältere Firefox, Safari vor 26) und „Bewegung reduzieren“ zeigen die Karte
still.

**Neigungs-Parallax (19.09.2026):** Bewegt man das Handy, rutscht die Karte
bis 18 px in die Neigungsrichtung (`neigungStart()`, `deviceorientation`,
ein Transform pro Bild auf dem Rahmen `.topo`, der dafür 18 px über das
Fenster hinausragt). Bezug ist die Haltung, in der das Handy gerade ruht: ein
Tiefpass (2 % je Ereignis) zieht den Bezug nach, bei ruhiger Hand steht die
Karte, 25° Ausschlag sind der volle Weg. Querformat vertauscht die Achsen.
Android liefert die Ereignisse ohne Nachfrage; iOS erst nach der
Bewegungsfreigabe, die `startGps()` für den Kompass einholt, danach hängt
sich `neigungStart()` erneut ein. „Bewegung reduzieren“ schaltet es ab.

Variante B zeigt noch den Altstadt-Ausschnitt; Route und Stationsmarken wurden
beim Kopieren entfernt, weil sie die alte Route zeigten. Für die Holešovice-
Route müsste `tools/hintergrund/hintergrund.py` mit neuem Ausschnitt laufen
(siehe unten). Vergleich zum Anklicken weiterhin:
`mockups/hintergrund-varianten.html`.

| | Variante | Größe, ausgeliefert |
|---|---|---|
| A | Wanderkarte fein: heutiger Stil, Höhenlinien aus einem Geländemodell, Bäche, Wald, Gitter, Höhenpunkte, Nordpfeil, Maßstab | 42 KB, gezippt 11 KB |
| B | Prag-Stadtplan aus OpenStreetMap: Moldau, Straßen nach Rang, Parks, Viertel, Route mit den fünf Stationen lagegetreu | 152 KB, gezippt 60 KB |
| C | Orientierungslauf-Karte mit Bahnaufdruck: Start, Posten 1 bis 5, Ziel ist der Koffer | 59 KB, gezippt 19 KB |

- Erzeugt von `tools/hintergrund/hintergrund.py`, die fertigen SVGs liegen in
  `mockups/hintergrund/`. Aufruf und Datenabruf stehen oben im Skript.
- Alle Varianten nutzen `vector-effect: non-scaling-stroke`: die Linien bleiben
  auf jedem Bildschirm gleich fein. Beim heutigen Hintergrund werden sie am
  Laptop fast fünfmal so dick. Beschriftungen fallen auf breiten Bildschirmen
  weg, sonst wären sie riesig.
- Die Varianten brauchen neue Farb-Token (`--park`, `--strasse`, `--ol-*` usw.),
  hell und dunkel; die Werte stehen in `tools/hintergrund/vergleich.py`.
- B braucht den Hinweis „© OpenStreetMap-Mitwirkende“ (ODbL), er steht klein
  unten rechts im SVG. Vor dem Einbau B auf etwa 100 KB verkleinern.
- Beim Einbau ersetzt das gewählte SVG das `<svg class="topo">` in
  `index.html`, dazu die CSS-Klassen aus `vergleich.py`.

## Auslosen

Im Reiter Teams steht ein Formular: entweder Personen pro Team oder Anzahl
Teams. Darunter steht sofort, was dabei herauskommt, etwa „Ergibt 4 Teams, 1 mit
4 und 3 mit 3 Personen“. Mehr als 16 Teams gehen nicht, so viele Tiernamen gibt
es.

Vorher rechnete `admin_draw` die Teamzahl fest als `round(Personen / 10)`. Bei
13 Angemeldeten ergibt das 1, also blieb es beim Auslosen immer bei einem Team.
Das sah wie ein Fehler aus, war aber die Regel.

Ist schon ausgelost, fragt das erneute Auslosen über denselben Dialog nach wie
die Löschaktionen, denn es wirft die bestehenden Teams und ihre Codes weg.

Läuft das Spiel schon oder ist es beendet, lehnt die Datenbank ein Auslosen ab,
sonst wäre der Fortschritt der Teams nichts mehr wert. Der Reiter Teams zeigt
dann keinen leeren Bereich, sondern erklärt das und bietet direkt „Fortschritt
zurücksetzen“ an. Danach steht das Spiel wieder auf `drawn` und das Formular ist
zurück.

## Löschen

Alles, was Daten entfernt, fragt zweimal: erst der Dialog, dann muss das Wort
`LÖSCHEN` getippt werden, bevor der Knopf überhaupt anklickbar wird. Escape und
„Abbrechen“ brechen ab.

Im Reiter **Daten löschen** stehen die großen Aktionen: Standortdaten löschen,
Fortschritt zurücksetzen und alle Teilnehmenden löschen. Der Reiter zeigt
vorher, wie viele Teams, Personen, Positionen und gelöste Stationen betroffen
sind. Oben im Kopf stehen nur noch Auslosen, Starten und Beenden.

Im Reiter **Teilnehmende** sitzt „Alle löschen“ direkt neben der Zahl. Das ruft
`admin_clear_participants` auf: alle Personen, alle Teams, Fortschritt und
Standortdaten weg, Status zurück auf `registration`, damit sich wieder jemand
anmelden kann. Stationen, Rätsel, Ziffern und die PIN bleiben. Praktisch nach
einem Probelauf mit Testeinträgen.

Das × bei einer einzelnen Person fragt ebenfalls nach, verlangt aber kein
getipptes Wort: eine Person zu streichen ist Routine, und der gesperrte Knopf
sah dort wie ein Fehler aus. Wer eine Aktion ohne Wort anlegen will, setzt
`wort: false` im Eintrag.

Neues Auslosen sitzt nicht hier, sondern im Reiter Teams, weil dort auch die
Teamgröße eingestellt wird. Es fragt trotzdem nach.

Neue Löschaktionen gehören in die Liste `DANGER` in `index.html`, dann bekommen
sie den Dialog automatisch. Titel, Beschreibung und Zusatz dürfen Funktionen des
Zustands sein, damit im Dialog echte Zahlen stehen.

## Routen und Zeitachse

Auf der Karte hat jedes Team eine Farbe und seine gelaufene Route. Darunter
steht für jedes Team eine Zeitleiste: ausgefüllt heißt unterwegs, schraffiert
heißt an der Station am Rätsel, der Kreis mit der Ziffer markiert den Moment, in
dem die Antwort saß. Rechts die Gesamtzeit vom Start bis zur letzten Ziffer,
sortiert nach Schnelligkeit. Ein Klick auf ein Team blendet seine Route aus.

Der Schieber zieht die Karte auf einen früheren Zeitpunkt zurück, „Abspielen“
lässt den ganzen Ablauf in 45 Sekunden laufen, „Jetzt“ springt zurück auf den
aktuellen Stand. Weil alle Teams dieselbe Route laufen, liegen die Linien
größtenteils übereinander; zum Vergleichen einzelne Teams ausblenden.

Wie oft ein Punkt entsteht: Ein Team meldet seine Position, wenn es sich mehr
als 20 m bewegt hat oder die letzte Meldung älter als 60 Sekunden ist. Beim
Gehen ist das etwa alle 15 Sekunden, an einer Station einmal pro Minute. Für 90
Minuten sind das rund 250 Punkte je Team. `admin_tracks` liefert beim Nachladen
nur die Punkte seit dem letzten Abruf, damit nicht alle zehn Sekunden der ganze
Verlauf über die Leitung geht.

## Hilfe für die Teilnehmenden

In der öffentlichen Ansicht und in der Team-Ansicht steht ein Knopf, der
WhatsApp mit einer vorbereiteten Nachricht öffnet. Die Nachricht nennt je nach
Ansicht Team, Code und aktuelle Station, damit die Spielleitung sofort weiß, wer
schreibt.

Seit 18.09.2026 sind es zwei Knöpfe unter „Hilfe von der Spielleitung“: **WhatsApp** (grünes Symbol, öffnet `wa.me` mit vorbereitetem Text) und **Anrufen** (`tel:`-Link, öffnet die Telefon-App). Die Nummer steht in `config.js` unter `support.phone`, international ohne
Pluszeichen, aus 0151 2345678 wird also `491512345678`. Ohne Nummer erscheint
kein Knopf. **Die Nummer wird öffentlich**: sie steht im Quelltext der Seite und
im öffentlichen Repo, dessen Historie sie dauerhaft behält. Nimm eine, bei der
das in Ordnung ist, am besten ein Diensthandy.

## Randfälle abgedichtet (Nachtrag 13, 18.09.2026)

Ergebnis eines Durchgangs durch alle Randfälle des Konzepts (Anmeldung,
Auslosen, Spiel, Ziel, Ende, Spielleitung). Eingebaut:

- **Koffer-Code nur am Koffer:** `submit_final` bekommt wie `check_in` eine
  Position und prüft sie gegen die letzte Station (Radius plus GPS-Toleranz,
  im Testmodus nicht). Vorher konnte ein Team, das die Ziffern per Nachricht
  bekam, von überall einen Platz holen. Die App holt dafür eine frische
  Position; die Meldung nennt die Restentfernung.
- **Versehentlich beendet:** „Spiel fortsetzen“ (`admin_resume`) bringt
  `finished` zurück auf `running`, ohne etwas zu löschen. Vorher gab es nur
  „Fortschritt zurücksetzen“, das alles wegwarf.
- **Starten nur aus `drawn`:** `admin_start` prüft das jetzt selbst, nicht
  nur der Knopf. Mit Testmodus an brach es zunächst ab; seit Nachtrag 16
  (19.09.2026) warnt es nur noch, damit der Testmodus beim Testen dauerhaft
  an bleiben kann.
- **Rätsel werten:** im Reiter Teams neben „Freischalten“. Zählt die aktuelle
  Station eines Teams als gelöst (`admin_solve_station`), wenn ein Rätsel
  klemmt. Fragt nach, löscht nichts.
- **Mehrere Lösungen je Rätsel:** im Feld Lösung mit `|` trennen
  („5|fünf“). Leere Teile zählen nie. `norm` faltet Großbuchstaben mit Umlaut
  jetzt selbst, unabhängig von der Locale der Datenbank.
- **Testdaten entfernen:** löscht nur Namen mit „(Test)“, echte Anmeldungen
  bleiben. Im Reiter Teilnehmende und unter Daten löschen. Vorher hätte
  „Alle löschen“ auch die echten Anmeldungen samt Geräte-Schlüssel entfernt.
- **Umbenennen** durch die Spielleitung: gleiche Regeln wie die Anmeldung
  (2 bis 60 Zeichen, keine Doppelten). Das Handy der umbenannten Person
  übernimmt den neuen Namen über den Geräte-Schlüssel, statt sich abzumelden
  (`nameNochDa` prüft mit Schlüssel über `member_state`, ohne Schlüssel wie
  bisher über den Namen).
- Ziffer im Stationsformular ist Pflicht (vorher wurde leer still zur 0).

Bewusst nicht geändert: Team-Codes bleiben Tier plus vier Ziffern; wer den
Code hat, spielt für das Team. Die drei Koffer haben weiter einen Code, die
Aufsicht am Koffer entscheidet nach dem Platz-Bildschirm. Offen bleibt der
Mitlese-Link für Leute, die sich auf einem anderen Gerät angemeldet haben
(siehe Offene Punkte).

Getestet gegen das lokale PostgreSQL (Skript `test_wasserdicht.py`, 40
Prüfungen) und im Browser: Rätsel werten, Testdaten entfernen, Pflicht-Ziffer,
Beenden und Fortsetzen, Koffer-Code aus 31 km Entfernung abgelehnt und am Ziel
Platz 1, umbenannte Person bleibt angemeldet.

## Teamleitung und Mitlese-Link (Nachtrag 14, 19.09.2026)

**Teamleitung wechseln.** Die Spielleitung wählt im Reiter Teams je Team die
Leitung über ein Auswahlfeld (`admin_set_leader`). Die Teamleitung kann ihre
Leitung in ihrer Ansicht abgeben („Leitung abgeben“ unten, `team_set_leader`
nach Namen aus dem eigenen Team). Der Team-Code bleibt in beiden Fällen
derselbe: Wer übernimmt, bekommt den Code und loggt sich damit ein; das alte
Handy kann sich abmelden. Wer den Code hat, spielt, das ist unverändert.

**Mitlese-Link.** Jedes Team hat einen Mitlese-Schlüssel (`teams.read_token`,
32 Hex, Vorgabe beim Anlegen, neu bei jedem Auslosen). Die Teamleitung sieht
unten „Mitlesen fürs Team“ mit „Link teilen“ (Share-Sheet, sonst WhatsApp) und
„Link kopieren“; die Spielleitung hat je Team „Mitlese-Link“ im Reiter Teams
für Nachzügler. Der Link ist `index.html#/mit/<schlüssel>`: die App merkt sich
den Schlüssel als `sj.mit`, springt auf `#/public` und liest ab dann über
`member_state_by_team` mit (wie `member_state`, aber ohne Namen). Ein
Geräte-Schlüssel aus der Anmeldung hat Vorrang. Damit lesen auch die mit, die
sich am Rechner angemeldet haben, einen anderen Browser nutzen oder von der
Spielleitung nachgetragen wurden. Team-Code und Mitlese-Schlüssel kommen nur in
`team_state` (Teamleitung) und `admin_state` vor; `member_state`,
`member_state_by_team` und `public_state` lassen beide weg.

**Start auf der Karte.** Das Hotel Mama Shelter steht als Haus auf der Karte
der Spielleitung (Konstante `START` in `index.html`, nicht in der Datenbank).

Getestet lokal (`test_leitung.py`, 18 Prüfungen) und im Browser: Link öffnen
auf einem fremden Handy zeigt das Team, Leitung abgeben, Leitung im Admin
wählen, Mitlese-Link kopieren, Haus auf der Karte.

## Teamleitung ohne Code (Nachtrag 18, 19.09.2026)

Wer sich auf dem eigenen Handy angemeldet hat, ist über den Geräte-Schlüssel
bekannt. Öffnet diese Person `#/team` und leitet gerade ein Team, holt die App
den Team-Code selbst (`leader_code(p_token)`, `leitungOhneCode()` in
`refresh()`) und loggt ein; das Feld zum Tippen erscheint gar nicht. Der Knopf
auf der Team-Karte heißt „Du bist Teamleitung: loslegen“. Bei einem Wechsel
der Leitung bekommt die neue Leitung den Code auf demselben Weg, niemand muss
ihn weitersagen; das alte Handy bleibt eingeloggt, bis es sich abmeldet (wer
den Code hat, spielt, unverändert). Tippen bleibt für Handys ohne Anmeldung
(Code von der Spielleitung) und für die Spielleitung am Tablet.

## Durchgang aus Sicht der Teams (Nachtrag 17, 19.09.2026)

Ablauf und Oberfläche aus Sicht von Teilnehmenden und Teamleitung durchgegangen
(SPIEL.md 5.1 bis 5.6). Sieben Punkte, alle umgesetzt:

1. **Einstieg für die Teamleitung:** Erkennt das Handy, dass es der Teamleitung
   gehört (Name aus Anmeldung oder Mitlesen = Leitung), zeigt die Team-Karte
   oben „Du bist Teamleitung: Code eingeben“ (Link zu `#/team`). Liest die
   Leitung nur mit, steht derselbe Hinweis über der Team-Ansicht.
2. **Mitlese-Link vor dem Start ganz oben:** direkt unter „Ihr seid startklar“,
   mit „Schick den Link jetzt in eure Team-Gruppe“. Im Spiel bleibt er unten.
3. **Eigener Koffer-Hinweis:** `game_state.case_hint` statt Ortshinweis von
   Station 5; im Reiter Stationen pflegbar (`admin_set_settings`).
4. **Feste Spieldauer:** `game_state.duration_min` (Vorgabe 180), im Reiter
   Stationen einstellbar, auch während des Spiels. Ab „Spiel starten“ zeigen
   Teamleitung, Mitlesende und Spielleitung im Kopf „Noch 1:45 h“, in den
   letzten 15 Minuten rot, danach „Zeit ist um, zurück zum Ziel“. Reine
   Information: Eingaben bleiben möglich, das Spiel endet erst mit „Spiel
   beenden“ (`endsAt` = `started_at` + Dauer, Countdown im 1-s-Takt).
5. **Tipp je Station:** `stations.tip` (optional, Feld im Stationsformular).
   Nach der ersten Denkpause (`progress.pauses`) kann die Teamleitung ihn
   aufdecken (`reveal_tip`, `progress.tip_at`); danach sehen ihn alle im Team.
   Die Meldung beim dritten Fehlversuch sagt das an. `admin_save_station` hat
   dafür `p_tip` (mit Vorgabe, die alte Signatur ist entfernt).
6. **Rangliste nach dem Ende** auch in der Team-Ansicht, eigenes Team fett
   (`ranglisteHTML`, `public_state` wird im Zustand `finished` mitgeholt).
7. **Hinweis für Mitlesende** unter „Standort und Kompass aktivieren“:
   freiwillig, den Weg findet die Teamleitung.

Getestet lokal (`test_einstellungen.py`, 26 Prüfungen) und im Browser: Knopf
auf der Team-Karte der Leitung, Mitlese-Panel vor dem Start, Countdown im
Kopf, Tipp nach drei Fehlversuchen, Koffer-Hinweis aus den Einstellungen,
Rangliste nach dem Ende, Einstellungen im Admin.

## Code-Review (19.09.2026)

Drei Prüfer (JavaScript, Datenbank, Sicherheit) über die Nachträge 13 und 14
und die UI-Runde. Sicherheit: nichts über die in SPIEL.md dokumentierten
Lücken hinaus. Behoben (Nachtrag 15 und `index.html`):

- Rückmeldung nach „Leitung abgeben“ war vor dem Start, im Ziel und nach dem
  Ende unsichtbar (die Phase hatte keinen `msgBox()`); jetzt eigener Ort
  `abgeben` direkt unter dem Feld, auch für Fehler.
- `mitLinkPruefen()` lief beim Start ungeschützt: ein gesperrter
  `localStorage` (privates Fenster) hätte die Seite leer gelassen. Jetzt
  `try/catch`.
- Auswahlfelder: die 10-s-Abfrage zeichnete auch bei offenem `<select>` neu
  (`SELECT` zählt jetzt als „tippt gerade“), und das Feld ist gesperrt,
  solange der Wechsel unterwegs ist.
- `norm()`-Änderung aus Nachtrag 13 ohne Nachzug von `participants.name_key`
  (live wich keine Zeile ab, die Supabase-Locale faltet `lower()` korrekt).
- `submit_answer` zählt Fehlversuche jetzt unter Zeilensperre (`for update`),
  zwei gleichzeitige Falschantworten konnten sonst denselben Stand lesen.

## Bugjagd (Nachtrag 20, 19.09.2026)

Multi-Agent-Bugjagd über das ganze Repo (4 Winkel, Jury aus drei Prüfern je
Fund, Kritiker): 10 Funde bestätigt, alle 3 von 3, 2 verworfen (beide in
`tools/hintergrund/hintergrund.py`, Entwicklerwerkzeug ohne Folge für das
Spiel). Stand: live seit 19.09.2026 (gepusht, Nachtrag 20 eingespielt und über
`pg_proc`/`pg_trigger` geprüft). Behoben:

- **Weiße Seite bei blockierten Website-Daten** (major). `index.html` las
  `localStorage` ungeschützt beim Laden. Jetzt `LS`/`SS` über
  `speicherOderMap`: wirft der Speicher, merkt sich die App die Werte bis zum
  Neuladen in einer Map. Geprüft in headless Chrome mit gesperrten Cookies:
  alter Stand leer, neuer Stand rendert alle drei Ansichten.
- **`tools/sql.py` ließ `delete from x;` durch**, sobald später im Text
  irgendein `where` stand (major). Beide Regeln (delete und update) schauen
  jetzt nur bis zum nächsten `;`. Die Update-Regel meldete umgekehrt
  `create trigger ... before update of ...` fälschlich, weil sie bis zum
  nächsten `set search_path` weiterlief.
- **„Rätsel werten“ und „Freischalten“** werteten die Station, die beim
  Eintreffen gerade aktuell war: ein zweiter Klick nach einem Netzfehler oder
  eine veraltete Ansicht schenkte die nächste Station. Jetzt mit `p_position`,
  der Server lehnt ab, wenn das Team schon weiter ist. Der Dialog nennt die
  Station. `p_position` ist optional, eine alte Seite läuft weiter.
- **Tschechische Antworten:** `norm()` löschte ř č š ž ě í, „Křižík“ wurde zu
  „kik“. Jetzt fallen alle gängigen lateinischen Diakritika auf den
  Grundbuchstaben, ä ö ü ß wie bisher auf ae oe ue ss. `name_key` nachgezogen.
- **Leerer Namensschlüssel:** ein Name nur aus Kyrillisch oder Emoji ergab
  `''`, die zweite solche Person hörte „Dann bist du dabei“. Jetzt abgelehnt
  in allen vier Wegen, dazu ein Trigger auf `participants`.
- **Auslosen gegen Anmelden:** zwei gleichzeitige Auslosungen legten doppelt
  so viele Teams an, eine Anmeldung während des Auslosens blieb ohne Team.
  `admin_draw` sperrt `game_state` jetzt gleich zu Beginn (`for update`),
  Anmeldung und Nachtragen warten mit `for share`.
- **Live-Karte verlor Punkte**, deren Meldung erst nach dem Abruf committete
  (Zeitfilter `recorded_at > p_since`). Das Frontend lädt jetzt voll neu,
  sobald seine Punktzahl von `pointCount` abweicht, nicht nur bei zu vielen.
- **Admin-PIN:** Änderungen verlangen mindestens 12 Zeichen, auch per
  direktem UPDATE. Live hatte die PIN am 19.09.2026 nur 4 Zeichen (siehe
  Offene Punkte).
- **Löschdialog:** ein Name mit `$&` oder `$$` verfälschte den Dialogtext
  (`String.replace`-Muster). Jetzt mit Replacer-Funktion.

Getestet: alle 21 Migrationen in PGlite (PostgreSQL 17 im Prozess)
eingespielt, 34 Prüfungen zu norm, Anmeldung, Werten, PIN und erneutem
Einspielen grün. Die Sperren gegen Gleichzeitigkeit lassen sich dort nicht
nachstellen (eine Verbindung).

Wer neu aufsetzt: erst die Migration, dann die Seite. Andersherum schickt
die neue Seite `p_position` an eine Funktion, die es noch nicht kennt.

Deckung: Der Scout ließ nur Doku (README, HANDOFF, SPIEL.md) und
`.gitignore` aus; die OSM-Rohdaten unter `tools/hintergrund/` hat kein
Finder vollständig gelesen.

## UI-Runde (19.09.2026)

Durchgang mit Bildschirmfotos (Handy 390 px für Teilnehmende und Teamleitung,
Tablet 1024 px für die Spielleitung). Behoben: Fehlermeldungen blieben über
einen Phasenwechsel stehen („Leider falsch“ noch auf dem Koffer-Bildschirm;
jetzt `phaseKey`/`teamStandSetzen`), Hilfe-Knöpfe fehlten am Koffer, Kompass
und Entfernung waren unbeschriftet, der GPS-Status war ein Bandwurmsatz,
gesperrte Knöpfe sahen wie blasses Orange aus (jetzt grau), kein Hinweis
während des Standortholens (Knopf sagt „Standort wird bestimmt …“ über
`data-wait`), „Wir sind da“ ohne Erklärung, Admin-Teamzeile „0 / 5, nie“ (jetzt
„0 / 5 gelöst, bei Station 1, noch keine Aktivität“).

Nicht geändert, aber notiert: Schriften kommen von Google Fonts und Leaflet
von unpkg (CDN); für das Event mit Mobilfunk in Prag geht das, die
TSE-Regel „lokal vendoren“ wäre für einen späteren Stand einzuhalten.

## GPS und Kompass

- Entfernung per Haversine, Richtung per Kurswinkel, beides in `index.html`.
- Blickrichtung: iOS über `webkitCompassHeading`, Android über
  `deviceorientationabsolute`. Auf iOS muss
  `DeviceOrientationEvent.requestPermission()` in einem Klick-Handler laufen,
  deshalb der Knopf „Standort und Kompass aktivieren“.
- Ohne Magnetometer wird die Laufrichtung aus zwei GPS-Punkten genutzt. Bis sie
  bekannt ist, bleibt der Pfeil grau (`.needle.unsicher`), statt eine
  erfundene Richtung zu zeigen.
- Beim Check-in wird eine frische Position geholt. Serverseitig gilt `radius_m`
  plus bis zu 25 m GPS-Toleranz.
- **Alles braucht HTTPS.** Eine lokal per Doppelklick geöffnete Datei (`file://`
  oder `content://`) bekommt keinen Standortzugriff.
- **Der Kompass sagt, warum er nicht geht.** `S.gps.kompass` hält den Zustand,
  unter der Nadel steht er im Klartext: `wartet` (erlaubt, noch nichts
  gekommen), `an`, `kalibrieren` (ungenau oder ohne Nordbezug), `relativ`
  (Drehung ohne Nordbezug, andere Geräte), `abgelehnt`, `fehlt`. Vorher landete
  jeder Fehlschlag in einem leeren `catch` und sah gleich aus. Wechselt der
  Zustand, zeichnet die Team-Ansicht neu, damit Hinweis und Knöpfe sofort
  stimmen; aber nur, solange Kompass oder Einmessen zu sehen sind, sonst ginge
  eine halb getippte Rätselantwort verloren.
- **Erlaubnis auf dem iPhone:** Den Schalter „Bewegung und Ausrichtung“ in den
  Safari-Einstellungen gibt es seit iOS 13 nicht mehr, die Erlaubnis gilt je
  Seite und wird per `requestPermission()` erfragt. Nach einer Ablehnung
  antwortet sie oft sofort mit `denied`. Die App rät deshalb: Seite schließen,
  neu öffnen, „Erlauben“ tippen, notfalls den Browser ganz beenden. Der Knopf
  „Kompass erneut versuchen“ steht nur noch in diesem Hinweis.
- **Ohne Kompass:** Kommt 3 s nach dem Freigeben kein brauchbares Ereignis,
  gilt der Kompass als `fehlt`. Handys ohne Magnetsensor schweigen einfach oder
  schicken leere Ereignisse; vorher stand dort für immer „Kompass meldet sich
  noch nicht“. Ein ruhiger Hinweis erklärt, dass der Pfeil der Laufrichtung
  folgt und die Entfernung immer stimmt. Meldet sich der Kompass später doch,
  springt der Zustand zurück auf `an`.
- **Unkalibrierter Magnetsensor:** iOS liefert dann `webkitCompassAccuracy < 0`
  oder `webkitCompassHeading === null`. Abhilfe ist eine liegende Acht mit dem
  Handy. Das steht als Hinweis in der App.
- **Eine große positive Genauigkeit ist genauso unbrauchbar.** Gemessen auf
  einem iPhone 17 Pro (iOS 27, Chrome für iOS) am 18.09.2026: Erlaubnis
  erteilt, 1143 Ereignisse empfangen, `webkitCompassHeading` vorhanden, aber
  `webkitCompassAccuracy` bei **±74°**, und der Wert bewegte sich über zwölf
  aufeinanderfolgende Ereignisse um keine einzige Nachkommastelle. Der Sensor
  antwortet also, führt aber nicht nach. Die erste Fassung prüfte nur auf
  negative Werte und meldete deshalb fröhlich „Kompass aktiv“, während der
  Pfeil um einen Viertelkreis danebenlag.
- **Grenze:** `KOMPASS_GRENZE` in `index.html`, aktuell 25 Grad; zurück auf
  „aktiv“ erst unter 20 Grad, damit Hinweis und Knopf nicht flackern. Darüber gilt
  die Richtung als unbrauchbar, die App sagt das mit dem gemessenen Wert und
  schaltet auf die Laufrichtung aus zwei GPS-Punkten um, sobald das Team ein
  paar Schritte gegangen ist. Dafür wird die Laufrichtung jetzt auch dann
  mitgerechnet, wenn der Kompass etwas liefert; vorher unterblieb das, sobald
  irgendeine Richtung ankam, und es gab keinen Ersatz.
- **Was gegen einen schlechten Sensor hilft:** liegende Acht mit dem Gerät,
  weg von Magneten (MagSafe-Hüllen, Autohalterungen, Magnetbörsen, Kopfhörer),
  und in den Einstellungen unter Datenschutz, Ortungsdienste, Systemdienste den
  Dienst Kompasskalibrierung einschalten.
- **Einmessen (liegende Acht):** Meldet sich zum ersten Mal am Tag ein echter
  Kompass (`an` oder `kalibrieren`), zeigt die Team-Ansicht statt des Kompasses
  eine Anleitung mit Animation und Fortschrittsbalken. Eine Webseite kann das
  Kalibrieren weder auslösen noch prüfen, nur das Schwenken messen
  (Winkelgeschwindigkeit aus `beta`/`gamma` über 80°/s, Zittern zählt nicht).
  Fertig nach 5 s Schwenken, auf dem iPhone schon nach 2 s, sobald
  `webkitCompassAccuracy` ±15° oder besser meldet; Android verrät keine
  Genauigkeit. „Überspringen“ geht immer. Beides merkt sich das Handy in
  `localStorage` unter `sj.kal` mit dem Datum, danach bleibt der Link „Kompass
  neu einmessen“. Wird der Kompass später ungenau, trägt der Hinweis den Knopf
  „Jetzt einmessen“. Bleibt er nach dem Einmessen über der Grenze, nennt die App
  Magnete und die iOS-Kompasskalibrierung. Die Werte stehen als `KAL_*` im
  Abschnitt „GPS und Kompass“ in `index.html`. Entwurf:
  `mockups/kompass-einmessen.html`.
- **Testseite (bis 30.09.2026, seitdem Teil des Geräte-Tests, siehe Nachtrag 23):** `kompass-test.html`, live unter
  https://7deeda.github.io/Stadtjagt/kompass-test.html. Zeigt Erlaubnis,
  Ereigniszahl, `webkitCompassHeading`, Genauigkeit und Rohwerte und fällt nach
  fünf Sekunden ein Urteil. Sie zählt, wie viele der 36 Richtungen beim Drehen
  ankommen (ab 30: funktioniert), und schreibt nur Änderungen ins Protokoll;
  ein still liegendes Handy liefert sonst zwölf gleiche Zeilen, was wie ein
  eingefrorener Sensor aussieht. Ein Knopf legt den Bericht in die
  Zwischenablage.

## Standortdaten und Datenschutz

Die Team-Handys senden ihre Position nur, solange `status = 'running'`, und nur
bei mehr als 20 m Bewegung oder älter als 60 Sekunden. In der Team-Ansicht steht
sichtbar, dass der Standort geteilt wird. Betroffen sind nur die Handys der
Teamleitungen, also so viele wie es Teams gibt. Je nach Haus vorher mit dem
Betriebsrat klären.

**Geändert am 18.09.2026:** „Spiel beenden“ löscht die Standortdaten nicht mehr,
sonst wären die Routen genau dann weg, wenn man sie auswerten will. Gelöscht
wird nur noch auf Knopfdruck über „Standortdaten löschen“, beim Zurücksetzen und
beim Leeren der Anmeldung. Das ist bewusst mehr als vorher: Aus kurzen
Positionsmeldungen wird ein vollständiger Bewegungsverlauf der Teamleitungen
über die ganze Spielzeit. Den Teams vorher sagen, dass der Weg aufgezeichnet
wird, und nach der Auswertung löschen.

## Umgebung (Stand 19.09.2026, live)

| Was | Wert |
|---|---|
| GitHub-Repo | `7DEEda/Stadtjagt`, Branch **master** (nicht `main`) |
| Live-Seite | https://7deeda.github.io/Stadtjagt/ |
| Supabase URL | `https://lwdmwklyydhcvnhpjudk.supabase.co` |
| Publishable key | `sb_publishable_7uEQEkFwi27XJdGLSoso5w_TMxHJYUq` (steht in `config.js`, darf öffentlich sein) |
| Admin-PIN | in `game_state.admin_pin`, am 18.09.2026 geändert (Standard war 2026). Der aktuelle Wert steht bewusst nicht im Repo, das ist öffentlich. |

Init-Migration und Nachträge 1 bis 21 sind eingespielt (22 braucht keine Migration), geprüft über `pg_proc`
und Aufrufe der Endpunkte. Wer die Datenbank neu aufsetzt, spielt sie in der
Reihenfolge ein, in der sie unter „Alle Dateien“ stehen: ohne Nachtrag 1
schlägt „Teams auslosen“ mit „UPDATE requires a WHERE clause“ fehl, ohne
Nachtrag 2 fehlen Routen und Zeitachse, ohne Nachtrag 3 bleibt die Teamgröße
fest.

Wichtig für die Weiterarbeit:

- **Init-Migration nicht erneut ausführen.** Sie beginnt mit `drop table …
  cascade`. Änderungen kommen als neue Datei unter `supabase/migrations/`.
- **Neue Supabase-Schlüssel:** Das Projekt nutzt den Publishable key
  (`sb_publishable_…`), nicht den alten anon key. Der `sb_secret_…` gehört
  nirgends in Repo oder App.
- **Workflow horcht auf `[main, master]`**, weil der lokale Branch `master`
  heißt.
- **Auf dem Arbeitsrechner sind weder Node.js noch die GitHub CLI installiert**,
  und Adminrechte fehlen. Also keine Lösungen vorschlagen, die `npx`, `npm` oder
  `gh` für den Betrieb voraussetzen. Auf dem Privatrechner (Adminrechte) ist
  Node 24 installiert; dort lässt es sich für Prüfungen nutzen, etwa zur
  Syntaxprüfung von `index.html`, das Projekt selbst braucht es aber nicht. Python ist vorhanden, Git läuft über VS Code, SQL über
  `tools/sql.py` oder den SQL-Editor.
- **Das Projekt lag zunächst unter OneDrive.** Wenn es dort noch liegt: nach
  außerhalb verschieben, OneDrive synchronisiert den `.git`-Ordner mit und
  erzeugt Konflikte.
- **Kartenkacheln brauchen einen Referer.** `openstreetmap.org` antwortet auf
  Anfragen ohne Referer mit einem Sperrbild („Access blocked“) statt mit der
  Karte. Eine per Doppelklick geöffnete Datei (`file://`) sendet keinen, dort
  bleibt die Karte leer. Auf der Live-Seite und über `http://localhost`
  funktioniert sie. Zum lokalen Testen `python -m http.server` im Projektordner
  starten. Localhost gilt dem Browser außerdem als sicherer Kontext,
  Standortzugriff geht dort ohne HTTPS.
- **Jedes UPDATE und DELETE braucht ein WHERE.** Supabase lädt für
  API-Verbindungen die Erweiterung pg-safeupdate. Ohne WHERE bricht die Funktion
  mit „UPDATE requires a WHERE clause“ ab, auch innerhalb von
  security-definer-Funktionen. Für „alle Zeilen“ `where true` schreiben. Tests
  über eine direkte Datenbankverbindung zeigen das nicht, nur Aufrufe über die
  API.
- **Beispieldaten:** `supabase/seed-stationen-prag.sql` setzt die fünf Prager
  Stationen der neuen Route mit Koordinaten, Koffer-Code 371955. Rätsel und
  Ortshinweise sind noch Platzhalter, siehe „Route“.
  `supabase/seed-personen.sql` legt 100 erfundene Teilnehmende an, nur zum
  Proben und nur vor dem Auslosen einspielen.

## SQL ausführen ohne den Browser

`tools/sql.py` schickt SQL über die Supabase Management-API an die Datenbank,
damit Migrationen nicht mehr von Hand in den SQL-Editor kopiert werden müssen.

```
python tools/sql.py supabase/migrations/20260918160000_routes.sql
python tools/sql.py --read-only -c "select status from game_state"
```

Der Zugang braucht einen Personal Access Token von
https://supabase.com/dashboard/account/tokens. Er steht **nicht** im Repo,
sondern in `%USERPROFILE%\.supabase\stadtjagt.token`, also außerhalb von
OneDrive, oder in der Umgebungsvariable `SUPABASE_ACCESS_TOKEN`. Ein solcher
Token gilt fürs ganze Supabase-Konto, nicht nur für dieses Projekt; nach dem
Event auf derselben Seite zurückziehen. Der Publishable key aus `config.js` ist
hier der falsche Schlüssel, das Skript sagt das auch.

Eingebaute Bremse: Anweisungen, die Daten vernichten, lehnt das Skript ab,
solange nicht `--force` dabeisteht. Das schützt vor allem vor der
Init-Migration, die mit `drop table ... cascade` anfängt. Eine Funktion oder
einen Index zu ersetzen geht ohne `--force` durch, wird aber gemeldet. UPDATE
und DELETE innerhalb von Funktionskörpern (`$$ ... $$`) zählen nicht mit, sonst
käme kein Nachtrag durch. Die Projektkennung liest das Skript aus `config.js`,
sie steht also nur an einer Stelle.

## Einrichtung

### Supabase
1. Projekt auf supabase.com anlegen, Region Frankfurt.
2. Init-Migration und danach die Nachträge einspielen, per `tools/sql.py` oder
   im SQL-Editor.
3. Project Settings → API: Project URL und Publishable key (`sb_publishable_…`)
   nach `config.js` kopieren. Der Secret key (`sb_secret_…`) gehört nicht
   dorthin.
4. Support-Nummer in `config.js` eintragen, sonst fehlt der Hilfe-Knopf.

### GitHub Pages
Repo anlegen, Ordner pushen, unter Settings → Pages als Quelle „GitHub Actions“
wählen. Der Workflow im Ordner `.github/workflows` veröffentlicht bei jedem Push
auf `main` oder `master`.

### Lokal in VS Code
`index.html` braucht keinen Build. Zum Testen reicht die Erweiterung „Live
Server“, ohne Node.js, oder `python -m http.server` im Projektordner. Für
GPS-Tests am Handy brauchst du HTTPS, also entweder die veröffentlichte Seite
oder einen Tunnel.

## Ablauf am Eventtag

1. **Vorher: Testmodus aus!** Reiter Stationen, oben. Im Kopf der Spielleitung
   darf kein rotes „Testmodus an“ mehr stehen („Spiel starten“ warnt sonst
   rot). Testdaten wegräumen: „Testdaten entfernen“ im Reiter Teilnehmende.
2. **Vorher:** Route ablaufen, jede Station im Reiter Stationen prüfen, Rätsel
   und Antworten vor Ort bestätigen, notfalls „Meinen Standort übernehmen“
   drücken. Alle drei Koffer auf den Code aus dem Reiter Stationen stellen und
   an die letzte Station bringen.
3. **Vorher:** Support-Nummer in `config.js` eintragen und pushen. Im Reiter
   Stationen Spieldauer, Koffer-Hinweis, Tipps je Station und den Hintergrund
   festlegen.
4. Anmeldelink verteilen, Teilnehmende tragen sich ein.
5. Vor dem Auslosen: Zahl der Angemeldeten mit der Gästeliste abgleichen,
   Testeinträge über „Testdaten entfernen“ wegräumen.
6. Am Treffpunkt: Reiter Teams, Teamgröße wählen, auslosen. Codes muss
   niemand verteilen: jede Teamleitung ist auf ihrem eigenen Handy unter
   „Teamleitung“ gleich drin. Den Teams sagen, dass der Weg aufgezeichnet wird und
   dass die Teamleitung den Mitlese-Link in die Team-Gruppe schickt. Passt
   eine Leitung nicht (nicht da, kein Handy), im Auswahlfeld eine andere
   wählen. Nachzügler: eintragen, dann „Mitlese-Link“ des Teams schicken.
7. „Spiel starten“, danach die Karte offen lassen.
8. Wenn ein Team hängt: „Freischalten“ im Reiter Teams ersetzt den Check-in, das
   Rätsel bleibt. Klemmt das Rätsel selbst: „Rätsel werten“ daneben.
9. An den Koffern: Den Code gibt die Teamleitung erst am Koffer ein, die App
   prüft den Standort. Jedes Team zeigt seinen Platz-Bildschirm, die Aufsicht
   gibt Koffer 1, 2 oder 3 frei. Der Zieleinlauf steht live auf der
   Anmeldeseite. Fällt das Handy eines Teams aus, kann die Spielleitung am
   Tablet unter `#/team` über „Spielleitung: mit Team-Code eingeben“ für das
   Team eingeben (Code im Reiter Teams).
10. Wenn alle da sind oder die Zeit um ist: „Spiel beenden“. Die Rangliste
   erscheint öffentlich, die Routen bleiben zum Auswerten erhalten. Zu früh
   gedrückt: „Spiel fortsetzen“, nichts geht verloren.
11. **Danach:** Zeitachse und Routen ansehen, dann „Standortdaten löschen“.

## Ein Handy, eine Person, kein Code (Nachtrag 22, 19.09.2026)

Entscheidung: Jede Person meldet sich nur selbst an, auf dem eigenen Handy.
Die Teamleitung braucht deshalb keinen Code. Nur Frontend, keine Migration.

- „Jemanden ohne eigenes Handy anmelden“ entfällt; nach der Anmeldung steht
  „Dieses Handy gehört jetzt zu dir.“
- `#/team` ohne Code-Feld. Die Leitung ist über `leader_code` sofort drin,
  andere Handys sehen den Grund und den Weg zur Anmeldeseite. Das Code-Feld
  bleibt hinter dem Link „Spielleitung: mit Team-Code eingeben“ als Ausweg,
  wenn das Handy einer Leitung ausfällt.
- Ein per Teamsuche gemerkter Name („Das bin ich, merken“) gibt keine
  Eingabe frei, nur der eigene Geräte-Schlüssel.
- Wechselt die Spielleitung die Leitung oder gibt die Leitung ab, meldet sich
  das alte Handy ab (`leitungNochDa` prüft nach jedem Abruf, ein Funkloch
  meldet nicht ab). Bisher blieb der gemerkte Code gültig, und ein Team
  konnte zwei eingebende Handys haben.
- Nach einem Neu-Auslosen loggt das Handy der neuen Leitung von selbst ein.
- Texte ohne Codes: Auslosen, „Bereit zum Start“, Leitungswechsel, Abgeben,
  Abmelden.

Bekannte Grenze: Nachzügler, die die Spielleitung einträgt, haben keinen
Geräte-Schlüssel. Sie lesen über den Mitlese-Link mit, können aber nicht
Teamleitung sein (der Wechsel-Dialog sagt das).

Danach, ebenfalls live: Das Hauszeichen im Hintergrund (klassisch und A,
Mitte links) ist entfernt, auch im Generator `tools/hintergrund/hintergrund.py`.
Die Leiste unten markiert die aktuelle Seite (`aria-current`); ein Tipp darauf
springt nach oben und lädt neu. Vorher tat er auf der eigenen Seite nichts,
weil sich die Adresse nicht ändert und kein `hashchange` kommt.

## UI-Durchsicht des bestehenden Designs (Nachtrag 21, 19.09.2026)

Workflow mit neun Agenten über die echte App: ein Prüfstand mit gespielter
Datenbank (Scratchpad, `mock.js` beantwortet alle RPCs, `shoot.py` fotografiert
mit Playwright) lieferte 78 Bilder: iPhone 390 px hell und dunkel, Android
360 px, Querformat, Tablet 820 hoch und quer, 768 px. Sechs Linsen
(Teilnehmende, Teamleitung, Spielleitung, Lesbarkeit, Handy und Tablet als
Gerät, Texte), Gegenprüfung, Kritiker: 64 Roh-Funde, 45 bestätigt plus 6 vom
Kritiker, 10 muss. Alle eingebaut, im bestehenden Design (Schriften, Farben,
Topo, Aufbau unverändert). Vorher und nachher mit allen Funden:
`mockups/ui-durchsicht/index.html`.

Die wichtigsten:

- **Meldungen an genau einer Stelle.** Eine Ablehnung stand bei der Teamleitung
  dreimal, Suchfehler standen unter dem Rätsel der Mitlesenden (Regel siehe
  SPIEL.md, Meldungen).
- **Getipptes bleibt.** Die 10-s-Abfrage zeichnete Antwort- und Koffer-Feld leer,
  sobald die iPhone-Tastatur zu war.
- **Funkloch:** Mitlesende fliegen nicht mehr aus der Team-Ansicht, Netz- und
  Standortfehler kommen auf Deutsch mit Handlungshinweis, „Stand 13:27“ im
  Kopf nach 30 s ohne Server, sofortiges Nachladen nach der Rückkehr in die App.
- **Unterwegs:** Ohne Standort ist „Standort und Kompass freigeben“ der
  Hauptknopf; „Wir sind da“ steht direkt unter dem Kompass, der Kompass ist
  größer, darunter „Einchecken ab etwa 60 m“ bzw. „Ihr seid im Umkreis“;
  Einmessen blendet den Weg nicht mehr aus; abgelehnter Standort ist keine
  Sackgasse mehr; nach Neuladen startet der Standort von selbst, wenn er
  schon erlaubt war; der Bildschirm bleibt an.
- **Spielleitung am Tablet:** PIN-Feld mit Buchstaben-Tastatur (Passphrase),
  „Vollbild“ der Karte sperrte das Tablet, Zustandszeile je Team mit
  GPS-Alter, nur der passende Knopf, Rückmeldung in der Zeile, „Bereit zum
  Start“ mit Rückfrage, Leitungswechsel mit Rückfrage, Testdaten nur vor dem
  Auslosen, Tippziele mindestens 42 px.
- **Lesbarkeit:** Feldränder 3:1, Schrift auf Orange im Dunkelmodus dunkel,
  Hochhalten mit dunkler Schrift auf hellen Teamfarben.

Offen und nur auf dem Gerät prüfbar: die iOS-Freigabe des Kompasses nach
Neuladen (Knopf „Kompass wieder einschalten“), Wake Lock auf iOS, Teilen über
das Share-Sheet.

## UI-Varianten als Mockup (19.09.2026, gespeichert, nicht gebaut)

Drei klickbare Entwürfe unter `mockups/ui-varianten/`, Einstieg `index.html`
(drei Handys nebeneinander, eine Steuerung für Bildschirm und Rolle, dazu die
Befunde der Durchsicht). Gemeinsame Spiellogik in `gemeinsam.js`, Schriften
und Bildmarke lokal daneben.

- **A Postenkarte:** heutiger OL-Look, feste Aktionsleiste unten, Postenkarte
  statt Schloss und Routenleiste, Nebensachen in einem Blatt.
- **B Wegweiser:** ein Modus pro Bildschirm (Weg, Rätsel, Code), Schwarz auf
  Signalgelb, Check-in erst im Umkreis.
- **C Logbuch:** TSE-Design, Stationen als Zeitleiste, zeigt den
  Mitlesenden, was die Leitung tut.

Entscheidung 19.09.2026: vorerst keine der drei; erst das bestehende Design
in sich verbessern (UI-Workflow).

## Ideen für ein kniffligeres Spiel (19.09.2026, gespeichert, nicht gebaut)

Befund: Das Spiel ist heute ein Geocache, „von A nach B“: Ortshinweis,
hinlaufen, einchecken, Zählaufgabe, Ziffer ablesen. Die App zeigt die
Entfernung zum Ziel, das nimmt dem Suchen die Spannung. Rahmen: ~100 Leute in
einem Raum, Anmeldung, Gruppen finden, gemeinsamer Start vom Hotel. Drei
Änderungen, die das drehen, ohne die Kernlogik anzufassen; Entscheidung offen:

- **A. Der Ort ist selbst das Rätsel.** Ortshinweis als Rätsel (Bildausschnitt,
  verschlüsselte Beschreibung, Rechenaufgabe mit Koordinaten). Dafür je Station
  ein Schalter „Entfernung erst unter 150 m zeigen“, sonst verrät die App den
  Ort. Check-in bleibt.
- **B. Hinweise sammeln statt Ziffern ablesen.** Jede Station gibt einen
  *Hinweis* (Wort, Zahl, Symbol) statt der sichtbaren Ziffer; am Ende ein
  **Schlussrätsel** (`game_state`), das die fünf Hinweise zum Koffer-Code
  verbindet. Koffer-Ansicht zeigt gesammelte Hinweise plus Schlussrätsel statt
  der Ziffernräder; die Code-Prüfung bleibt. Technisch: `stations.clue`,
  `game_state.final_riddle`.
- **C. Versetzte Reihenfolge.** Heute laufen alle Teams dieselbe Route in
  derselben Reihenfolge: 100 Leute gleichzeitig vor dem Planetarium, Abschreiben
  beim Nachbarteam. Jedes Team startet bei einer anderen Station und geht im
  Kreis weiter. Technisch: Versatz je Team beim Auslosen (`teams.start_offset`),
  `current_station` läuft rotiert; Ziffern bleiben nach Stationsnummer sortiert,
  der Code ist für alle gleich.
- Dazu: **Kompass entschärfen** (Einmess-Aufforderung weg, Knopf „In Karten-App
  öffnen“), Zeitachse nicht weiter ausbauen.

Inhalte, die kein Code ersetzt: Rätsel, die nur vor Ort lösbar sind und mehr
als Zählen verlangen (Jahreszahl auf einer Inschrift minus etwas; Chiffre mit
Schlüssel am Ort; Frage, die das Herumgehen ums Objekt verlangt).

## Offene Punkte

- **Probelauf draußen** mit echten Handys steht aus, am besten ein iPhone und
  ein Android. Ablauf: jede Person meldet sich auf dem eigenen Handy an,
  auslosen, starten, die Leitung tippt auf „Teamleitung“ (ohne Code),
  Standort und Kompass freigeben,
  Entfernung und Pfeil beim Gehen prüfen, einchecken, Rätsel lösen, danach die
  Karte und die Zeitachse im Admin-Bereich ansehen. Anschließend „Fortschritt
  zurücksetzen“. Dabei auch prüfen, was der Prüfstand nicht kann: iOS-Freigabe
  des Kompasses nach Neuladen („Kompass wieder einschalten“), Bildschirm
  bleibt an (Wake Lock, iOS), „Link teilen“ über das Share-Sheet, Leitung
  abgeben (altes Handy meldet sich ab).
- **Rätsel und Ortshinweise** für die neue Route ausdenken, dann vor Ort
  prüfen: nur dort lösbar, etwa über Jahreszahlen, Inschriften oder Zählaufgaben.
- **Kompass auf dem iPhone 17 Pro:** Ursache gefunden, siehe GPS und Kompass.
  Der Sensor meldet ±74° Unsicherheit und einen eingefrorenen Wert. Die App
  erkennt das jetzt und weicht auf die Laufrichtung aus. Ob das Gerät nach
  Kalibrierung brauchbare Werte liefert, ist noch nicht bestätigt: Testseite
  erneut aufrufen, dabei auf die Zeile „Kompassgenauigkeit“ achten. Bleibt sie
  über 25°, nimmt das Team als Ersatz die Laufrichtung, und die Entfernung in
  Metern stimmt ohnehin unabhängig vom Kompass. Zum Vergleich ein iPhone 17
  (kein Pro, iOS 27, Chrome) am selben Tag: Erlaubnis erteilt,
  `webkitCompassHeading` mit ±10°, also brauchbar. Die zwölf gleichen Werte im
  Bericht kamen dort vom still liegenden Handy. Beim Pro deshalb erneut testen
  und sich dabei einmal im Kreis drehen.
- **WhatsApp-Nummer:** In `config.js` steht seit 18.09.2026 die Testnummer
  `491720000000` (0172 0000000), damit der Hilfe-Knopf sichtbar ist. Vor dem
  Event durch die echte Nummer der Spielleitung ersetzen und pushen.
- An den Koffern muss jemand von der Spielleitung stehen: alle drei haben
  denselben Code, erst der Platz-Bildschirm entscheidet, welcher Koffer dran ist.
- **Admin-PIN:** Die Vorgabe `2026` steht in der Init-Migration im
  öffentlichen Repo, und es gibt keine Bremse gegen Durchprobieren. **Live hat
  die PIN am 19.09.2026 nur 4 Zeichen** (geprüft über `length(admin_pin)`,
  nicht `2026` selbst). Vor dem Event eine lange PIN setzen (Passphrase, 12
  und mehr Zeichen, per `admin_set_pin` oder SQL, siehe README). Seit
  Nachtrag 20 lehnt die Datenbank kürzere ab.
- **Mitlese-Link als QR:** Der Link ist da (Nachtrag 14), ein QR-Code auf dem
  Handy der Teamleitung wäre noch bequemer als Teilen per Nachricht. Braucht
  einen kleinen QR-Generator, lokal eingebettet.
- **Prüfstand:** Der UI-Prüfstand liegt unter `tools/pruefstand/` (gespielte
  Datenbank `mock.js`, Fotos `shoot.py` mit Playwright, siehe README dort).
  Die PGlite-Tests der Migrationen liegen nicht im Repo; sie ließen sich bei
  Bedarf aus SPIEL.md und den Nachträgen 20 und 21 neu schreiben.
- **Hintergrund festlegen:** aktiv ist A; B zeigt noch den Altstadt-Ausschnitt.
- Optional: Startreihenfolge versetzen, Team-Chat, Fotoaufgaben.

## Historie und Entscheidungen

- Zuerst als Klick-Prototyp ohne Backend gebaut, um den Ablauf zu klären.
- Danach eine Version in Lovable (React, TanStack Start, Supabase). Projekt-ID
  `c04743bb-e316-45db-b53c-0808ce46ae52`. Aufgegeben, weil das Guthaben mitten
  in der Live-Karte ausging. Der Stand dort funktioniert, hat aber keine Karte
  und liefert Team-Codes öffentlich aus.
- Aktuelle Version bewusst ohne Framework: eine HTML-Datei plus SQL, damit sie
  ohne Build, ohne Abo und ohne fremde Plattform läuft.
- Geprüft wurde der komplette Ablauf gegen eine echte PostgreSQL-Instanz
  inklusive Sperre nach drei Fehlversuchen und der Frage, ob zwei Teams
  gleichzeitig gewinnen können. Können sie nicht.
- **18.09.2026, Routen behalten statt löschen.** Gegen das ursprüngliche
  Versprechen im Datenschutzabschnitt entschieden, weil die Auswertung sonst
  unmöglich wäre. Dafür löscht jetzt nur noch ein ausdrücklicher Knopf.
- **18.09.2026, Löschen in einen eigenen Bereich.** Vorher lagen „Zurücksetzen“
  und „Standortdaten löschen“ zwischen den Alltagsknöpfen. Jetzt ein eigener
  Reiter plus getipptes Wort. Ausnahme ist das × bei einer einzelnen Person: die
  volle Zeremonie sah dort wie ein Fehler aus.
- **18.09.2026, Teamgröße einstellbar.** Die feste Regel `round(Personen / 10)`
  ergab bei kleinen Gruppen immer ein Team und wirkte wie ein Fehler.
- **18.09.2026, Tiernamen nach Emoji ausgewählt.** Tiere ohne eigenes Emoji
  (Reiher, Marder, Iltis, Specht, Kranich, Luchs, Steinbock, Dachs, Hirsch,
  Falke) sind raus, dafür bekanntere mit Emoji und ohne Umlaute.
- **18.09.2026, Management-API statt SQL-Editor.** Weil auf dem Arbeitsrechner
  kein Node.js liegt, war die Supabase CLI keine Option. `tools/sql.py` spricht
  direkt die HTTP-API an.

## Geräte-Test (Nachtrag 23, 30.09.2026)

Zweck: vor dem Event auf möglichst vielen eigenen Geräten klären, was trägt und
was von den angedachten Funktionen machbar wäre. Kein Pflicht-Check für
Teilnehmende, kein Bezug zur Anmeldung.

- **Seite:** https://7deeda.github.io/Stadtjagt/geraete-test.html. Ein Tipp
  holt die iOS-Erlaubnis für Bewegung und lässt dann alle selbstlaufenden Tests
  durch. Danach kommen die Schritte mit der Hand (Kompass drehen, Bildschirm
  sperren, App wechseln) und die neuen Funktionen (Kamera, Vibration,
  Mitteilungen, Live-Verbindung, Offline). Aussehen und Hintergrund wie das
  Spiel, der Hintergrund folgt der Wahl der Spielleitung.
- **Suite erweitern:** einen Baustein in `geraete-tests.js` anhängen und
  `version` hochzählen. Der Kopf der Datei beschreibt die Felder. Seite und
  Datenbank bleiben unverändert. `id` nie umbenennen, sonst passen alte Läufe
  nicht mehr zur Übersicht.
- **Speichern:** Tabelle `device_test_runs`, ohne Rechte für anon. Hinein geht
  es nur über `device_test_save` (Schlüssel vom Handy, höchstens 64 KB,
  höchstens 2000 Läufe). `device_test_echo` wirft Daten weg und dient der
  Upload-Messung des Kamera-Tests. Scheitert das Speichern, liegt der Lauf in
  `localStorage` und die Seite bietet „Erneut senden“ an.
- **Abholen:** `python tools/testlaeufe.py` schreibt je Lauf eine JSON-Datei
  nach `testlaeufe/` und baut `testlaeufe/UEBERSICHT.md` (Matrix Test gegen
  Lauf). Der Ordner steht in `.gitignore`: das Repo wird komplett
  veröffentlicht, die Läufe enthalten Koordinaten.
- QR-Code und Ton waren bis Suite 3 dabei und sind am 30.09.2026 entfallen
  (Entscheidung Friedrich); `vendor/jsQR.js` und `geraete-test-qr.html` sind gelöscht.
- **Prüfstand:** `python tools/pruefstand/geraetetest.py` lässt die Seite mit
  gespieltem Standort und Kompass durchlaufen, ohne in die Datenbank zu
  schreiben. Braucht `pip install playwright`. „Wach halten“ meldet dort
  „verweigert“, das liegt am unsichtbaren Browser.
- Spezifikation und Plan: `docs/superpowers/`. Mockup: `mockups/geraete-test.html`.

## Kompass als Zeichen, Kompass nach dem Neuladen (Nachtrag 24, 30.09.2026)

Nur Frontend, keine Migration.

- **Zeichen im Kopf:** Die weiß-orange Postenflagge ist durch einen Kompass
  ersetzt (`logo()` in `index.html`, vorher die Konstante `FLAG`; Varianten in
  `mockups/icon-varianten.html`). Kennt die App die Blickrichtung, zeigt die
  orange Spitze nach Norden (`logoNadel()`); sonst steht sie nach oben. Der
  Geräte-Test nutzt dasselbe Zeichen.
- **Kompass nach dem Neuladen:** `startGps(true)` setzte den Kompass auf
  „tippen“, sobald der Browser `DeviceOrientationEvent.requestPermission`
  kennt. Das war als Erkennung für iOS gedacht, Chrome kennt die Funktion
  inzwischen aber auch (gemessen: Chrome 155 auf Android und am Laptop). Android
  verlangte dadurch nach jedem Neuladen einen Tipp. Jetzt hört die App nach dem
  Neuladen einfach zu: kommen Ereignisse, läuft der Kompass; kommt drei
  Sekunden nichts, bittet sie um den Tipp. Nach der Freigabe hängt
  `addOrient(true)` den Zuhörer frisch ein.
  Geprüft im Prüfstand in beiden Fällen (Ereignisse kommen, Ereignisse kommen
  nicht, danach Tipp). Auf echten Geräten noch nicht gesehen: vor allem auf
  einem iPhone nach dem Neuladen einmal prüfen, dass der Hinweis „Kompass ist
  nach dem Neuladen aus“ nach etwa drei Sekunden erscheint und der Tipp wirkt.
- **Geräte-Test, geführter Ablauf:** Umsetzung der UI-Kritik
  (`mockups/geraete-test-v2.html`). Nach dem automatischen Teil ist immer nur
  ein Schritt offen, der große Knopf führt dorthin. Statuszeichen mit eigener
  Form, gelbe und rote Zeilen klappen mit dem Grund auf, „Noch mal“ und
  „Abbrechen“ sind sichtbar. Im hellen Schema steht dunkle Schrift auf den
  orangen Knöpfen (Kontrast 5,3 statt 3,3); das Spiel selbst bleibt bei Weiß.

## Gruppenselfie an jeder Station (Nachtrag 25, 30.09.2026)

Spezifikation: `docs/superpowers/specs/2026-09-30-gruppenselfie-design.md`,
Mockup: `mockups/gruppenselfie.html`. Migration:
`supabase/migrations/20260930180000_gruppenselfie.sql`.

- **Abschaltbar, Standard aus.** Die Spielleitung schaltet im neuen Reiter
  „Fotos“ ein und setzt dort das Löschdatum. Solange der Schalter aus ist,
  verhält sich das Spiel wie vorher. Wird mitten im Spiel eingeschaltet,
  brauchen schon gelöste Stationen kein Foto mehr.
- **Ablauf:** Nach der richtigen Antwort zeigt das Handy der Teamleitung statt
  der nächsten Station den Selfie-Schritt (Frontkamera, Vorschau, „Das nehmen
  wir“). Erst mit dem Foto erscheint die Ziffer. `submit_answer` ist
  unverändert: Zeitmessung und Rangliste hängen weiter an `solved_at`. Neu ist
  `progress.selfie_at`; `team_state` hält die Ziffer zurück, solange es fehlt,
  und meldet die offene Station als `selfie.pending`.
- **Die Ziffer hängt nie am Netz:** Scheitert das Hochladen, gibt es „Ohne
  Hochladen weiter“ (`team_selfie_skip`). Das Foto bleibt im `localStorage`
  (`sj.foto.<team>.<position>`) und wird beim nächsten Abruf nachgereicht.
  Streikt die Kamera, erscheint nach dem ersten Versuch „Ohne Foto weiter“.
- **Wer was sieht:** Teamleitung, Mitglieder und Mitlesende sehen „Euer Album“
  (Zugang über Team-Code, Geräte-Schlüssel oder Mitlese-Link, `team_photo`).
  Die Spielleitung sieht alle im Reiter „Fotos“, lädt sie als ZIP herunter
  (im Browser gebaut, ohne Bibliothek) und kann sie löschen.
- **Speicher:** `station_photos` (Foto bis 700 KB, Vorschau bis 60 KB, nur
  JPEG), ohne Rechte für anon. Der Fremdschlüssel auf `progress` sorgt dafür,
  dass Zurücksetzen, neu Auslosen und Leeren der Anmeldung die Fotos
  mitnehmen. Das Handy verkleinert vorher auf 1280 px.
- **Löschen:** Ist `game_state.photos_delete_on` erreicht, entfernen
  `team_state` und `admin_state` die Fotos beim nächsten Abruf.
- **Ersetzen:** das Foto der zuletzt gelösten Station, bis an der nächsten
  eingecheckt ist („Neu aufnehmen“ im großen Foto).
- **Prüfen:** `python tools/pruefstand/selfie.py` spielt den Ablauf im
  Prüfstand durch (ohne Datenbank, ohne Kamera). `python
  tools/pruefstand/selfie_db.py` ist der Probelauf gegen die echte Datenbank:
  ein einziger DO-Block, der die Migration einspielt, 34 Prüfungen macht und
  am Ende alles zurücknimmt. Auf echten Handys prüfen: Frontkamera öffnet
  sich, Foto steht richtig herum, „Foto speichern“ landet in der Galerie.

## Ungefährer Standort (30.09.2026)

Befund aus dem Geräte-Test (iPhone, iOS 18.7): ±4650 m, weil „Genauer Standort“
für Safari aus war. Das Spiel verwirft Meldungen über ±1000 m (`brauchbar()`)
und sagte dazu bisher nichts, das Handy hing ohne Erklärung. Jetzt merkt sich
`startGps()` so eine Meldung in `S.gps.grob`, und `grobHTML()` zeigt, wo man die
Einstellung auf iPhone und Android ändert. Der Geräte-Test (Suite 5) meldet
denselben Fall als „nur ungefähr“. Geprüft im Prüfstand (Szenario
`leitung-standort-grob`), auf einem echten iPhone noch nicht.

## Mitlese-Link als QR-Code (30.09.2026)

„Link teilen“ zeigt den Mitlese-Link zusätzlich als QR-Code im Kasten „Mitlesen
fürs Team“ und öffnet danach wie bisher das Teilen-Fenster. Der Code bleibt
stehen: wer neben der Teamleitung steht, scannt ihn mit der Handykamera.
Generator: `vendor/qrcode.js` (qrcode-generator 1.4.4, MIT), lokal, wird erst
beim ersten Gebrauch geladen (`qrSvg()`). Der Code steht immer dunkel auf Weiß,
auch im dunklen Design.

## Kompass nach einer Pause (30.09.2026)

Befund von Friedrich (Android): Kompass eingemessen, in eine andere App
gewechselt, sich bewegt, zurück auf die Seite, der Pfeil zeigt mit festem
Versatz daneben, „als wäre er pausiert worden“. Im Spiel gibt es keinen
gespeicherten Versatz; die Richtung kommt bei jedem Ereignis frisch aus
`deviceorientationabsolute`. Vermutung: die Sensor-Fusion des Handys hält im
Hintergrund an und findet Norden erst durch Bewegung wieder. Belegt ist das
noch nicht, der Geräte-Test misst es ab Suite 7 (Schritt „Kompass nach Pause“).

Was das Spiel jetzt tut: War die Seite mindestens 3 Sekunden im Hintergrund,
gilt der Kompass als unsicher (`kompassNachPause()`, Zustand „kalibrieren“):
der Pfeil folgt der Laufrichtung, soweit eine da ist, und das Einmessen
(liegende Acht) wird von selbst angeboten, mit dem Satz, warum. Nach dem
Einmessen oder „Überspringen“ gilt der Kompass wieder. Nur Android; iOS meldet
die Genauigkeit selbst. Geprüft im Prüfstand, auf einem echten Handy noch nicht.

## Stationsname verschlüsselt, Einmessen als Fenster (Nachtrag 26, 30.09.2026)

Migration: `supabase/migrations/20260930200000_name_verschluesselt.sql`.
Mockups: `mockups/name-verschluesselt.html`, `mockups/station-karte.html`.

- **Auf dem Handy:** Hat eine Station die beiden Entfernungen
  `reveal_start_m` und `reveal_clear_m`, steht ihr Name zuerst als flimmernde
  Zeichen da (`stationsNameHTML()`, `geheimStand()`). Zwischen den beiden
  Entfernungen rasten die Buchstaben ein, in zufälliger, je Name fester
  Reihenfolge. Der Ortshinweis erscheint erst, wenn der Name ganz lesbar ist.
- **Schloss:** Es zählt der weiteste Stand je Station, gemerkt im
  `localStorage` (`sj.geheim.<team>.<position>`). Wer wieder wegläuft,
  verliert nichts.
- **Nur die Anzeige** (Entscheidung Friedrich): Der Name kommt im Klartext vom
  Server. Jedes Handy entschlüsselt nach seinem eigenen Standort; ohne
  freigegebenen Standort bleibt der Name verschlüsselt.
- **Ruhige Zeile:** flimmernde und eingerastete Zeichen stehen in derselben
  Schrift (JetBrains Mono) in Feldern fester Breite und Höhe, damit weder die
  Zeile noch der Inhalt darunter springt.
- **Spielleitung:** „Bearbeiten“ einer Station zeigt eine Karte mit drei
  Kreisen (Einchecken, ganz lesbar, Entschlüsseln beginnt), jeder mit einem
  Griff zum Ziehen und einem Feld für die Meter; dazu die Station davor mit
  dem direkten Weg, ein Vorschlag aus der Etappenlänge (60 % und 30 %) und ein
  Probe-Team, das zeigt, wie der Name an einer Stelle aussähe
  (`stationsKarte()`, `ekZeichnen()`). „Nicht verschlüsseln“ lässt beide
  Entfernungen leer. Beide Knöpfe zeichnen die Seite nicht neu, damit
  ungespeicherte Eingaben stehen bleiben.
- **Kompass einmessen** liegt jetzt als Fenster über der Seite
  (`kalFensterHTML()`), statt den Inhalt darunter wegzuschieben.
- **Prüfen:** `python tools/pruefstand/name.py` (Prüfstand),
  `python tools/pruefstand/name_db.py` (Probelauf gegen die Datenbank, nimmt
  alles zurück). Kartenkacheln lädt OpenStreetMap nur für Seiten mit Absender:
  ein Mockup direkt von der Platte zeigt „Access blocked“, über die
  veröffentlichte Adresse geht es.

## Bedienung mit dem Finger am Tablet (30.09.2026)

Durchsicht von Teamleitung und Spielleitung am Tablet durch einen unabhängigen
Kritiker, am Code und an Fotos aus dem Prüfstand, nicht an einem Gerät.
Umgesetzt:

- Ziehgriffe und Marker auf den Karten: sichtbar klein, Trefferfläche 44 px.
  Zoom-Knöpfe und das Schließkreuz der Sprechblase 44 px.
- Karte im Formular „Station bearbeiten“: mit dem Finger scrollt ein Wisch die
  Seite, zwei Finger zoomen die Karte (vorher fing die Karte jeden Wisch ab).
  Mit der Maus bleibt das Verschieben.
- „Vollbild“ zeichnet die Karte nicht mehr neu: Zoom und Ausschnitt bleiben.
- Schieber der Zeitachse 44 px hoch.
- „Freischalten“ im Reiter Teams fragt nach, wie „Rätsel werten“. Die Zeilen
  ordnen sich alle 10 s neu, ein Tipp landete leicht beim falschen Team.
- Solange ein Finger aufliegt, zeichnet die Seite nicht neu (`fingerSeit`).
- Löschkreuz bei den Teilnehmenden am rechten Rand statt hinter dem Namen.
- Dialoge stehen oben und scrollen, damit die Bildschirmtastatur die Knöpfe
  nicht verdeckt.
- Teamleitung ab 700 px Breite: Spalte 600 px, Kompass 180 px, Entfernung 56 px.
- Am Tablet mit Finger: kleine Knöpfe, Links und Reiter mindestens 48 px hoch.
- Koordinaten: „50,0875“ im Feld Breite wurde als Paar zerlegt (Breite 50,
  Länge 875). Jetzt gilt nur ein Paar mit Dezimalpunkten oder vier Teilen als Paar.
- Lücken-Schilder auf der Karte erst ab zwei Minuten.

Nicht umgesetzt: Rückfrage beim Wechsel der Teamleitung per Auswahlfeld prüfen,
Reihenfolge der Teams fest lassen. Offen, weil nur am Gerät zu klären: ob die
Bildschirmtastatur im Querformat Knöpfe verdeckt, ob das Ziehen der Griffe
sauber vom Scrollen getrennt ist.

## UI-Kritik und Hochformat (Nachtrag 27, 01.10.2026)

Zwei Kritik-Läufe (design-critique und ui-ux-pro-max mit Kritikern) über
Teamleitung, Mitlesen, Selfie, verschlüsselten Namen und Spielleitung; Bericht
in `.ui-design/reviews/stadtjagd_20261001.md` (nicht im Repo). Umgesetzt:

- Knopfschrift dunkel auf Orange (`--flag-ink:#0F1B18`, 5,3:1 statt 3,3:1),
  `--ok` dunkler, Ränder der Bedienelemente in `--feld`, Orange als Schrift nur
  als `--flag-text`, neue Meldungsart `.msg.warn` (Testmodus-Banner)
- „Wir sind da“ (`#tcheck`) ist außerhalb des Radius ein Nebenknopf
  „Noch X m bis zum Einchecken“
- Zahlenlösungen öffnen die Zifferntastatur: `team_state` liefert
  `station.numeric` (Migration `20261001120000_zahlenantwort.sql`)
- sechste Ziffer abgesetzt und erklärt (Schlussziffer), Route zählt gesetzte
  Ziffern, Knöpfe sagen beim Warten, was passiert (`data-wait`)
- Testmodus im laufenden Spiel fragt nach
- Touch-Ziele 44 px am Handy, 48 px am Tablet; Zahlen mit `tabular-nums`
- **Hochformat-Hinweis** (`#quer`, `querPruefen()`): Handy quer (Höhe unter
  500 px, Finger als Zeiger) zeigt nach 0,5 s ein Fenster mit drehendem Handy
  samt Notch und Pfeil im Uhrzeigersinn. Nicht bei der Spielleitung, nicht beim
  Einmessen, nicht beim Hochhalten und im großen Foto. Sperren kann eine
  Webseite das Querformat nicht. Test: `python tools/pruefstand/kritik.py`

## Design System, Hell/Dunkel-Schalter, Schriftstufen (01.10.2026)

- `design-system/MASTER.md` ist das Regelwerk (Token, Kontraste, Schriftstufen,
  Abstände, Bausteine, Sprache, Nicht tun), `design-system/index.html` die
  Ansicht dazu, online unter `/design-system/`. Hergeleitet mit der Skill
  ui-ux-pro-max.
- Schalter hell/dunkel oben rechts in jedem Kopf (`themaBtn()`, Aktion `thema`).
  Die Wahl steht pro Gerät in `localStorage` `sj.thema`, ein kleines Skript im
  `<head>` setzt sie vor dem ersten Zeichnen. Ohne Wahl folgt die App dem Gerät.
  Dunkle Token gelten doppelt: per Media Query und für `[data-theme="dark"]`.
  Der Prüfstand löscht `sj.thema` beim Laden nicht.
- Schriftgrößen nur noch als `var(--fs-*)` (9 Stufen, siehe MASTER.md);
  Ausnahme ist die Beschriftung der Hintergrundkarte `.topo`.

## Geräte-Test einfach, Suite 8 (02.10.2026)

- Die Testseite verrät nichts mehr vom Spiel: keine Begriffe wie Spiel,
  Station, Prag, Stadtjagd; immer die klassische Hintergrundkarte (B trägt
  Prager Ortsnamen, C nummerierte Posten). Die Adresse enthält weiter
  `/Stadtjagt/`; ein eigenes, neutral benanntes Repo nur für die Testseite
  wäre der Ausweg (noch nicht entschieden).
- Aufbau nach Material 3 (Mockup `mockups/geraete-test-einfach.html`):
  Start, automatische Prüfung als Häkchen-Liste, dann je ein Bildschirm pro
  Hand-Schritt (Fortschritt oben, „Los“ unten, „Überspringen“ leise), am Ende
  „Fertig, danke“ mit Laufkennung. Messwerte unter „Ergebnis ansehen“.
  „Bericht kopieren“ und „Erneut senden“ nur, wenn das Speichern scheitert;
  ein liegengebliebener Lauf geht beim nächsten Öffnen von selbst raus.
- Suite 8: „Wach halten“ ohne Tipp fragt beim Laden der Seite
  (`basis.wach.vorab`), „Wach halten, mit Tipp“ im Tipp auf „Test starten“
  (`basis.wach.tippAnfrage`) und läuft damit von selbst; 7 statt 8
  Hand-Schritte. Schritte haben `kopf` (Überschrift) und `hand` als Text oder
  Liste.
- „Handy einmal drehen“: Handy flach hinlegen und drehen; ein Kreis aus 36
  Strichen, die Kugel läuft mit der Himmelsrichtung, überfahrene Striche
  werden orange (`KREIS`, `kreisMalen()`), in der Mitte der Fortschritt.
- Die Position im Standort-Schritt bleibt genau gespeichert (Entscheidung
  02.10.: kein Abschneiden). Fotos werden nur zur Probe hochgeladen
  (`device_test_echo`), nicht behalten.
- Hintergrund scrollt nicht mehr mit (Spiel und Testseite, 02.10.): die
  scroll-gebundene Animation (`animation-timeline`, `--px-hub`) ist raus, die
  Karte bewegt sich nur noch mit der Neigung (`--nx`/`--ny`).
- „Handy einmal drehen“: die Prozentzahl in der Kreismitte dreht sich gegen
  das Handy (Bezug: Richtung beim Tipp auf „Los“, `S.kreisNull`) und bleibt so
  zur Person am Tisch ausgerichtet.
- Suite 9 (02.10.): „Kompass nach Pause“ entfällt, sechs Hand-Schritte.
  Ältere Läufe enthalten ihn noch.
- „Handy einmal drehen“ läuft bis zum vollen Kreis (36 von 36, höchstens
  30 s) und bleibt kurz auf 100 % stehen; die Anzeige rechnet auf 36. „ok“
  gilt weiter ab 30 Fächern, falls die Zeit abläuft.
- Suite 10 (02.10.): „Kompass“ im automatischen Teil gilt nicht mehr als
  Fehler, wenn das Handy still liegt (Chrome meldet nur Änderungen; die
  Richtung war da). Befund aus vier Läufen am 02.10. (Xiaomi 23113RKC6G,
  Chrome): drei Mal „keine Daten“ bei vorhandener Richtung.
- Läufe 02.10. (Xiaomi, Android 16, Chrome): Standort ±7 m nach 2,9 s, Handy
  drehen 36 von 36 in 13 s, Wach halten schon ohne Tipp erteilt, Standort
  nach dem Entsperren in 1,9 s zurück, Kamera ok, Lauf etwa 70 s. Vibration
  zweimal nicht gespürt (wie am 30.09.), Mitteilungen nur mit Service Worker.
  Lauf Z95K (Handy drehen 1 von 36): das Handy wurde nicht gedreht, kein
  Befund.
- Kompass-Genauigkeit: nur Safari auf dem iPhone meldet sie
  (`webkitCompassAccuracy`, am 30.09. ±18°); Chrome und Edge auf Android
  geben sie nicht an Webseiten weiter. Messbar wäre sie nur über einen
  Geh-Schritt (GPS-Laufrichtung gegen Kompass). Entscheidung 02.10.: die
  Tests laufen vorerst drinnen, ohne Gehen; kein solcher Schritt.
- Suite 11 (02.10.): „Handy einmal drehen“ schreibt jede Kompassmeldung mit
  (so schnell der Browser liefert, Android-Chrome etwa 60 pro Sekunde; eine
  Webseite kann nicht schneller abfragen). Im Lauf unter
  `tests["kompass-drehen"].roh`, kompakt `dt_ms,grad_x10[,genauigkeit];…`,
  dazu in `mess` Meldungen pro Sekunde, größter Sprung zwischen zwei
  Meldungen und Sprünge über 30°. Grenze des Servers 64 KB je Lauf: wird es
  eng, lässt `payload()` die Rohdaten weg, nie den Lauf.
- Die Zahl und die Kugel im Drehkreis folgen der Richtung geglättet
  (`GLATT` 0,12 je Bild, Ausreißer über 40° nur mit 0,04); die Zählung der
  Striche bleibt roh. Anlass: auf dem Xiaomi 22021211RG sprang die Zahl
  sichtbar, am selben Platz wie beim Lauf davor.
- Drehen höchstens 30 s (02.10.): bei 60 Meldungen pro Sekunde etwa 15 KB Rohdaten.
- Lauf RY4K (02.10., Xiaomi 22021211RG): beim Drehen gegen den
  Uhrzeigersinn fiel die Richtung zuerst in 1,5 s von 40° auf 210°, danach
  pendelte sie bei gleichmäßigem Weiterdrehen nur zwischen etwa 115° und 155°,
  gut einmal je Umdrehung. Bild eines Magnetsensors unter einem starken festen
  Störfeld (Magnet in Hülle oder Halterung, oder stark verstellt).
- Suite 12 (02.10.): Gyroskop und Beschleunigung beim Drehen
  (`devicemotion`, `sensor.bewegt`). Gemessen werden die Drehung laut
  Gyroskop, der Weg des Kompasses, „Kompass folgt zu x %“ und die Neigung
  (liegt das Handy flach). Hat sich das Handy laut Gyroskop um mehr als
  400° gedreht, endet der Schritt; sind dann weniger als 30 Fächer
  gesehen: „Kompass folgt nicht“ mit Hinweis. Die Zahl in der Kreismitte
  dreht sich nach dem Gyroskop zurück. Rohdaten jetzt
  `dt_ms,grad_x10,gyro_grad[,genauigkeit]`.
- Lauf VRB5 (02.10., Xiaomi 22021211RG, noch Suite 11 aus dem Browser-Cache):
  eine volle Drehung, der Kompass ging nur etwa 80° mit (210° bis 291°) und
  stand ab 13 s starr auf 291,4°, obwohl weiter Meldungen kamen. Der
  Magnetsensor dieses Geräts liefert keine brauchbare Richtung; das andere
  Xiaomi lief am selben Platz sauber. Pages lässt Browser bis zu 10 min
  zwischenspeichern: die Startseite zeigt jetzt „Version x“ (= Suite).
- Lauf 9S87 (02.10., Xiaomi 22021211RG, Suite 12): Kompass 36 von 36, aber
  485° für eine echte Drehung von 360° (Aussage Friedrich), ungleichmäßig
  (15°/s bis über 50°/s bei gleichmäßigem Drehen): verzerrter Magnetsensor.
  Das Gyroskop meldete nur −2°: Chrome legt die Hochachse nicht in
  `rotationRate.alpha` ab.
- Suite 13/14 (02.10.): `sensor.gyroDreh()` nimmt die Gyro-Achse mit dem
  meisten Weg seit „Los“ (im Lauf: „Gyro je Achse“, „Gyro-Achse der
  Drehung“). Neu bewertet: „Kompass folgt zu x %“ und „Größte Abweichung
  Kompass gegen Gyroskop“ an jeder Stelle der Drehung. Ab einer halben
  Umdrehung laut Gyroskop: mehr als 20 % Unterschied oder mehr als 30°
  daneben = Warnung, mehr als 40 % oder 60° = Fehler („bis x° daneben“).
  „36 von 36“ allein heißt also nicht mehr „geht“.
- Läufe 02.10. mittags: iPhone 2Z8H (iOS 18.7) schnell gedreht und 38° schräg
  gehalten; die Gyro-Drehung verteilte sich auf beta (388°) und gamma (364°),
  zusammen etwa 530°, der Kompass 529°: Kompass in Ordnung (meldet selbst
  ±10°), die Achsenwahl war falsch. Xiaomi 22021211RG zweimal schlecht
  (124 % mit 116° Abweichung, 48 % mit 228°). Xiaomi 23113RKC6G (DD2H) als
  Vergleich: Gyroskop −360°, Kompass −356°, höchstens 5° daneben.
- Suite 15 (02.10.): Drehung um die Senkrechte statt um eine Gerätachse:
  Drehrate (alpha um x, beta um y, gamma um z, so auf Android-Chrome und
  iOS-Safari gemessen) auf „oben“ projiziert, „oben“ aus
  accelerationIncludingGravity, auf z > 0 gewendet (iOS meldet die
  Schwerkraft umgekehrt). Ohne Schwerkraftdaten: Achse mit dem meisten Weg.
- „Handy einmal drehen“ ist gesperrt, bis das Handy flach liegt (Fenster mit
  Animation `#flach`, `flachPruefen()`): unter 8° Neigung für 0,7 s gibt
  „Los“ frei, über 15° sperrt wieder. Ohne Beschleunigungsdaten nach 1,5 s
  keine Sperre.
- Flach-Sperre blieb am 02.10. auf einem Xiaomi bei 49° stehen, obwohl das
  Handy flach lag: die Neigung kam aus der geglätteten Schwerkraft, und beim
  Stillliegen kamen keine Meldungen mehr. Jetzt aus dem Lagesensor (beta,
  gamma, ungeglättet, `neigung()`); die Schwerkraft für die Gyro-Rechnung
  nur noch leicht geglättet (0,6).
- Suite 16 (02.10.): neuer Hand-Schritt „Kompass einmessen“ direkt vor
  „Handy einmal drehen“: liegende Acht wie im Spiel (gleiche Animation),
  gezählt wird Schwenken über 80°/s, 5 s zusammen, höchstens 30 s; iOS
  meldet die Genauigkeit vorher und nachher. Sieben Hand-Schritte. Der
  Prüfstand legt sein gespieltes Handy jetzt flach (sonst sperrt der
  Drehschritt) und überspringt das Einmessen.
- Hintergrund-Neigung ruhiger (Spiel und Testseite, 02.10.): steht das Handy
  steiler als 75° (beta), hält die Karte still, weil gamma dort schlagartig um
  180° kippt (beim Einmessen ständig); die Karte gleitet zur neuen Lage
  (0,18 je Bild, `neigungIst` bzw. `sensor.gleiten()`), höchstens etwa 3 px
  je Bild statt Sprüngen bis 36 px. Hinweis: der Prüfstand stellt
  Lageereignisse nur dem Kompass zu, nicht dem Neigungs-Effekt.
- Lauf ASC3 (Xiaomi 23113RKC6G, Suite 16): eingemessen 5,1 s, danach
  Gyroskop −354°, Kompass −369° (104 %), höchstens 16° daneben.
- Lauf UW6V (Xiaomi 22021211RG, Suite 16, nach dem Einmessen): still liegend
  lief der Kompass von selbst 80° im Uhrzeigersinn (färbte 25 % des Kreises),
  danach folgte er dem Drehen einige Sekunden (202° gegen 216°), sprang dann
  zweimal um etwa +100° zurück; netto 13° bei 400° laut Gyroskop. Android
  führt kurz mit dem Gyroskop und zieht ruckartig zum falschen Magnetwert
  zurück. Einmessen half nicht: Kompass dieses Geräts unbrauchbar.
- Suite 17 (02.10.): Striche im Drehkreis zählen nur, wenn das Handy laut
  Gyroskop dreht (über 8°/s um die Senkrechte, `drehRate`). Neu „Kompass
  wandert ohne Drehung“ (in `sensor.bei` gezählt); über 30° gehört zur
  Bewertung „bis x° daneben“.
- Suite 18 (02.10.): der Geräte-Test speichert keine Position und keine Höhe
  mehr, nur die Genauigkeit (und ob Höhe und Bewegungsrichtung gemeldet
  werden). Ältere Läufe in der Datenbank enthalten die Position noch.
- Startseite mit Hinweistafel (Piktogramme wie am Parkeingang, Variante A
  dunkel, `TAFEL`): Anonym, Ort privat, Kamera, Sensoren, Gerät. „Weiter“
  führt auf die neue Seite „Gleich fragt dein Handy“ (`S.seite =
  "freigaben"`) mit nachgebauten Systemfragen für Android oder iPhone (aus der
  Browserkennung, `IOS`), orange umrandet, was man tippen soll; erst dort
  „Test starten“. Mockups: `mockups/geraete-test-tafel.html`,
  `mockups/geraete-test-freigaben.html`; QR-Code zum Verschicken:
  `mockups/qr-geraete-test.png`.
- Neuer Ordner `sicherungen/` (nicht im Repo): Stationen und Spielstand vom
  02.10. vor dem Umbau auf eine Teststation.
- Freigaben-Seite, Android: nach Foto vom 02.10. (Chrome, Android 16) ein Fenster mit Karten Genau/Ungefähr und drei Knöpfen untereinander; zwei Schritte (Standort, Kamera). Das Mockup `geraete-test-freigaben.html` zeigt noch die alte Android-Form.
- Geräte-Test unter neutraler Adresse (02.10.): eigenes öffentliches Repo
  `7DEEda/geraetetest`, https://7deeda.github.io/geraetetest/. Quelle bleibt
  hier; `python tools/geraetetest_veroeffentlichen.py` kopiert
  geraete-test.html als index.html, entfernt den Block WEITERLEITUNG, schreibt
  eine eigene config.js (`GT_CONFIG`, nur Server und öffentlicher Schlüssel),
  bricht bei verräterischen Wörtern ab (stadtj, Spiel, Prag, Station …) und
  pusht aus `.geraetetest-repo/` (nicht im Repo). Nach jeder Änderung am
  Geräte-Test dieses Skript laufen lassen. Die alte Adresse
  /Stadtjagt/geraete-test.html leitet auf die neue um. QR-Code
  `mockups/qr-geraete-test.png` zeigt die neue Adresse.
- Suite 19: neutrale Abfragen (Server-Prüfung und App-Wechsel nutzen
  `device_test_echo` statt `public_state`) und Kennungen (`GT_TESTS`,
  `GT_CONFIG`, Präfix `gt.` im Speicher, alte `sj.gt.offen.`-Läufe werden noch
  gelesen).
- Einmessen (Spiel und Test): die Acht-Animation rollt das Handy jetzt auch um
  die Längsachse, Text „Dreht und kippt es dabei in alle Richtungen“ (für den
  Magnetsensor zählen möglichst viele Lagen, Schwenken allein reicht nicht).

## Teststation (Nachtrag 28, 02.10.2026)

- Ist der Testmodus an, spielen alle Teams nur die Teststation (anfangs EDEKA
  Grenzallee, Berlin, Start der Etappe TSE Grenzallee 4); die fünf Prager
  Stationen bleiben unverändert und gelten, sobald der Testmodus aus ist.
- Bearbeiten: Spielleitung, Reiter Stationen, Abschnitt „Teststation“ (Karte
  mit ziehbaren Kreisen wie bei den echten Stationen).
- Im Testmodus reicht eine Person zum Auslosen (ein Team zum Ausprobieren).
  Schloss, Koffer-Feld und Texte rechnen mit der Stationszahl (Teststation:
  zwei Ziffern).
- Fortschritt je Route getrennt (progress hängt an der Station). Test-Fotos
  zeigt die Galerie der Spielleitung als eigene Kachel „Teststation“, auch im
  ZIP.
- Datenbank: Tabelle `stations_alle` (Spalte `route` echt/test), Sicht
  `stations` = aktive Route (`aktive_route()`), `current_station` liefert den
  Typ der Sicht. **Wer eine Spalte an `stations_alle` anfügt, muss danach
  `create or replace view stations as select * from stations_alle where route
  = aktive_route();` ausführen**, sonst steht das Spiel; wird die Sicht neu
  angelegt, danach `revoke all on stations from anon, authenticated`.
- 02.10.: Teams und Fortschritt des Probebetriebs gelöscht (Friedrich), die
  zwei Personen bleiben angemeldet, Status Anmeldung, Testmodus an.
  Sicherung vorher: `sicherungen/` (nicht im Repo).
- Plan: `docs/superpowers/plans/2026-10-02-teststation.md`; Prüfen:
  `tools/pruefstand/teststation.py`, Probelauf `teststation_db.py`.
- Vor dem Event: Testmodus aus, Fortschritt zurücksetzen. Die Teststation
  darf liegen bleiben.
- Startpunkt eintragbar (Nachtrag 29, 02.10.): je Route in game_state
  (`start_*`, `test_start_*`), `admin_set_start`, `admin_state.start`/`testStart`.
  Spielleitung, Reiter Stationen: Zeile „Start“ über der Stationsliste und im
  Abschnitt Teststation (Name, Koordinaten, Paar einfügbar, „Meinen Standort
  übernehmen“). Wirkt auf das Haus auf der Karte und die erste Etappe. Ohne
  Wert gelten die alten Konstanten `START`/`TEST_START`. Probelauf
  `tools/pruefstand/startpunkt_db.py`.
- Kopf der Spielleitung mit mehr Abstand zwischen Titel, Chips und Meldung.
- Geräte-Test Suite 20 (02.10.): eigener Schritt „Akku“ mit Stand und „lädt“; ohne `navigator.getBattery` (Safari, Firefox) Warnung „nicht lesbar“.

