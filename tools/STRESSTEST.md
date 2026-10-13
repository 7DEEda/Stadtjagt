# Stresstest der Stadtjagd

Anleitung für Friedrich und für eine Claude-Sitzung, die den Stresstest
übernimmt (etwa auf dem privaten Rechner). Stand 13.10.2026.

**An Claude:** Arbeite diese Datei der Reihe nach ab, ohne nachzufragen, wo
es nicht nötig ist. Fragen musst du nur an den markierten Stellen
(**FRIEDRICH**). Halte den Stand unten unter "Protokoll" fest, damit jede
Sitzung weiß, wo es weitergeht. Diese Datei liegt im öffentlichen Repo:
schreib hier nie Passwörter, Tokens oder den Secret Key hinein.

## Worum es geht

Am Eventtag (Prag) spielen etwa 100 Handys gleichzeitig. Jedes fragt alle
10 Sekunden den Spielstand ab, die Teamleitungen melden zusätzlich ihre
Position; zusammen etwa 20 bis 30 Anfragen pro Sekunde an Supabase. Der Test
zeigt, ob das Live-Setup (Supabase, kostenloser Plan, Frankfurt) das
zuverlässig schafft, und wo die Grenze liegt. Davon hängt ab, ob die Datenbank
bei Supabase bleibt (dann Pro für den Event-Monat, damit nichts pausiert) oder
auf einen eigenen Server umzieht. Die App selbst bleibt auf GitHub Pages
(Entscheidung 13.10.2026).

## Testprojekt

- Supabase-Projekt `stadtjagd-stresstest`, Ref `brtngzltqgniihjaoskr`,
  Region Central EU (Frankfurt), Postgres (Standard), gleiche Einstellungen
  wie das Live-Projekt.
- URL, Publishable Key und Ref stehen als Vorgabe in `tools/stresstest.py`.
- Admin-PIN im Testprojekt: `stresstest-2026` (setzt `einrichten`).
- Das Live-Projekt (`lwdmwklyydhcvnhpjudk`) verweigert das Skript; dort wird
  nie getestet.

## Voraussetzungen

1. Repo aktuell: über OneDrive erst fertig synchronisieren lassen, oder
   `git clone https://github.com/7DEEda/Stadtjagt.git` außerhalb von OneDrive.
   Danach `git pull`.
2. Python ab 3.10 (`python --version`), keine Zusatzpakete.
3. **FRIEDRICH:** ein Personal Access Token von
   supabase.com/dashboard/account/tokens, nur für Schritt 1 ("einrichten").
   Auf Friedrichs privatem Rechner gibt es schon einen: "Acces White"
   (`sbp_fc2043…126b`, Konto mit der Org "7DEEda's Org", gültig bis
   30.04.2027); den nehmen, kein neuer nötig. Der Token auf dem Arbeitsrechner
   (`sbp_fce8b2…`) sieht das Testprojekt nicht (HTTP 403) und taugt hierfür nicht.
   Er liegt in `tools/stresstest.token` (nur der Token, eine Zeile). Die Datei
   steht in `.gitignore`, kommt also nie ins öffentliche Repo, wird aber über
   OneDrive mitsynchronisiert; das Skript liest sie von selbst. Fehlt sie,
   Friedrich nach dem Token fragen und ihn dort ablegen (Erlaubnis vom
   13.10.2026). Alternativ `$env:SUPABASE_ACCESS_TOKEN="<Token>"`.
4. status.supabase.com prüfen: Bei einer Störung (am 13.10. war eine) sagen
   die Messwerte nichts über die App. Dann nur einrichten, nicht messen.

## Ablauf

Alle Befehle im Repo-Ordner, im Vordergrund. `lauf` dauert etwa 17 Minuten
(1 min Anmeldung, 15 min Spiel, Bericht).

1. **Einrichten** (einmal):
   `python tools/stresstest.py einrichten`
   Spielt alle Migrationen, die Prager Stationen, Testlösungen und die PIN
   ein. Bricht es an einer Migration ab, Datei und Fehlermeldung notieren und
   der Ursache nachgehen (frisches Projekt: fehlende Rolle, Erweiterung oder
   eine Migration, die Daten voraussetzt). Danach kann der Token im
   Dashboard zurückgezogen werden.
2. **Lauf 1, Eventlast:** `python tools/stresstest.py lauf`
   (100 Handys, 12 Teams, Takt 10 s, 2 Tablets der Spielleitung).
3. **Bewerten** (siehe unten). Ist Lauf 1 gut:
4. **Lauf 2, doppelte Last:** `python tools/stresstest.py lauf --handys 200 --teams 24`
5. **Lauf 3, schneller Takt:** `python tools/stresstest.py lauf --takt 5`
   (entspricht ungefähr 200 Handys im normalen Takt).
6. Ergebnisse unten ins Protokoll, Berichte liegen als
   `tools/stresstest-bericht-*.json` (nicht im Repo, `.gitignore`).
7. **FRIEDRICH:** Ergebnis gemeinsam ansehen. Erst danach Schritt
   "Aufräumen".

Zwischen zwei Läufen räumt `lauf` das Testprojekt selbst auf (Teilnehmende,
Teams, Positionen). Von Hand: `python tools/stresstest.py aufraeumen`.

## Bewerten

Gut, wenn in Lauf 1 alles davon gilt:

- Fehler: 0 bei allen Funktionen. Jeder Fehler wird mit Meldung angezeigt;
  "Verbindung: ..." deutet auf das eigene Netz, "HTTP 5xx" oder Zeitüberschreitungen
  auf Supabase.
- p95 der häufigen Abfragen (`public_state`, `member_state`, `team_state`,
  `admin_state`) unter 1000 ms, p99 unter 2000 ms. Darüber merkt man es am
  Handy (Kompass und Entfernung kommen trotzdem lokal, aber Check-in und
  Antworten fühlen sich zäh an).
- `register_participant` während der Anmeldespitze ohne Fehler, p95 unter
  2000 ms.
- Ergebnis: alle 12 Teams im Ziel, 60 Stationen gelöst.
- Die 10-Sekunden-Zeilen bleiben über die ganze Zeit ungefähr gleich (kein
  Anstieg der Antwortzeit gegen Ende: das wäre ein Zeichen für wachsende
  Datenmengen, etwa Routen in `admin_tracks` oder Positionen).
- Antwortgröße von `public_state` und `admin_state` notieren: sie wächst mit
  der Teilnehmerzahl und geht über Mobilfunk.

Zeigen Lauf 2 oder 3 Fehler oder p95 über 1000 ms, ist das keine Katastrophe,
sondern die Grenze: festhalten, ab welcher Last. Fällt schon Lauf 1 durch:
die langsamste Funktion zuerst ansehen (Abfrage im SQL, fehlender Index,
Antwort zu groß) und **FRIEDRICH** fragen, bevor etwas an der Live-App oder
der Live-Datenbank geändert wird.

Wird gemessen über den eigenen Internetanschluss: sind alle Zeiten
gleichmäßig hoch, zuerst die eigene Leitung verdächtigen (zweiter Lauf zu
anderer Zeit oder von einem anderen Netz).

## Aufräumen (erst nach FRIEDRICHs Okay)

Nur, wenn beim Stresstest nichts aufgefallen ist bzw. Friedrich und Claude
gemeinsam sagen, dass es jetzt gut ist. Bis dahin bleibt alles stehen, auch
über mehrere Läufe und Korrekturen hinweg.

1. In `tools/stresstest.py` die Vorgaben `TEST_URL`, `TEST_KEY`, `TEST_REF`
   leeren (auf `None` setzen), committen und pushen.
2. `tools/stresstest.token` löschen. **FRIEDRICH:** im Supabase-Dashboard das
   Projekt `stadtjagd-stresstest` löschen und den Personal Access Token
   zurückziehen. Wurde der Secret Key
   des Testprojekts irgendwo geteilt, ist er mit dem Projekt weg.
3. Auf dem Arbeitsrechner liegen in Claudes Projektgedächtnis Zugangsdaten
   des Testprojekts (Datei `stadtjagd-stresstest-db-passwort.md`); die
   Sitzung dort löscht sie samt Eintrag in `MEMORY.md`.
4. HANDOFF, Abschnitt "Stresstest": Ergebnis in zwei, drei Sätzen, die
   Entscheidung Supabase Pro oder eigener Server, und dass das Testprojekt
   gelöscht ist.

## Protokoll

- 13.10.2026: Skript fertig, Trockenlauf gegen lokalen Fake-Server ok
  (100 Handys, 12 Teams im Ziel, etwa 20 bis 25 Anfragen/s). Testprojekt
  angelegt, Schema noch nicht eingespielt. Supabase meldete an dem Tag
  Störungen.
- 13.10.2026, 16:55: Token nur für das Testprojekt angelegt (24 h gültig, bis
  etwa 14.10. 16:45), liegt in `tools/stresstest.token`. `einrichten` lief vom
  Arbeitsrechner: alle 33 Migrationen ok, Stationen, Lösungen `loesung1` bis
  `loesung5`, PIN `stresstest-2026`. Korrekturen am Skript: PIN mindestens
  12 Zeichen (Datenbankregel), `einrichten` wiederholbar (überspringt das
  Schema, wenn es steht), Spieldauer als ganze Minuten. Funktionstest mit
  10 Handys, 2 Teams, 1,5 min: keine Fehler, p95 unter 125 ms (Supabase meldete
  Störungen, daher keine Messung). **Nächster Schritt: Lauf 1 (Schritt 2),
  sobald status.supabase.com grün ist.** Der Token wird für die Läufe nicht
  mehr gebraucht.
- 13.10.2026, 17:16 (Lauf 1, erster Versuch, 15 min): 0 Fehler, p95 aller
  Funktionen unter 170 ms, ein Ausreißer bei 790 s (p95 2,9 s, max 7,4 s).
  "Teams im Ziel 0": Fehler im Skript, nicht in der App. Der Koffer liegt an der
  letzten Station, das Skript schickte die Teams zum Start; `submit_final`
  lehnte mit `ok: false` ab, und das Skript zählte jeden HTTP-200 als ok.
- 13.10.2026, 17:48 (Lauf 1 wiederholt, 20 min, Skript korrigiert): Skript
  prüft jetzt `ok: false` als Logikfehler, Koffer an der letzten Station,
  alle Teams geben ihn ungefähr gleichzeitig ein, dazu 18 Randfälle (doppelter
  Name, Nachmelden, Check-in zu weit weg, Doppeltipp, Denkpause, falscher oder
  doppelter Koffer-Code, Koffer ohne GPS ...). **Ergebnis:** 0 Fehler, 0
  Logikfehler, alle 18 Randfälle wie erwartet, 12 von 12 Teams im Ziel, 60 von
  60 Stationen, Plätze lückenlos und eindeutig, `submit_final` p95 90 ms.
  p95 gesamt: public_state 190, member_state 129, team_state 108, admin_state
  378 ms; **p99 public_state 2346 ms (Kriterium 2000 verfehlt)**. Ursache: drei
  kurze Aussetzer (340 s, 700 bis 740 s, kleiner 830 s), in denen alle
  Funktionen gleichzeitig langsam waren (p95 bis 4,1 s), ohne Fehler und ohne
  Trend; p50 blieb bei 44 ms. Das erste Lauf-1 hatte einen ähnlichen Aussetzer.
  Spricht für Netz oder Supabase (Störung an dem Tag), nicht für eine einzelne
  Abfrage. Antwortgrößen: public_state 5,7 KB, admin_state 26 KB. 
- 13.10.2026, 18:11 (Lauf 2, 200 Handys, `--teams 24`, 20 min): 0 Fehler, 0
  Logikfehler, alle Randfälle ok. Gebildet wurden nur 16 Teams (`admin_draw`
  hat eine Mindestgröße, 24 Teams bei 200 Personen gehen nicht); alle 16 im
  Ziel, 80 von 80 Stationen, Plätze lückenlos. p95: public_state 64,
  member_state 54, team_state 57, admin_state 229 ms; p99 überall unter
  400 ms; kein Aussetzer. Antwortgröße admin_state 44 KB, public_state 8,9 KB.
- 13.10.2026, 18:32 (Lauf 3, Takt 5 s, 100 Handys, 20 min, etwa 38
  Anfragen/s, also das Doppelte der Eventlast): 0 Fehler, 12 von 12 Teams im
  Ziel, 60 von 60 Stationen, alle Randfälle ok. p95: public_state 60,
  member_state 54, team_state 55, admin_state 170 ms; p99 unter 260 ms;
  register_participant p95 501 ms (Anmeldespitze, Kriterium 2000 ms);
  submit_final p95 129 ms. Nur zwei Fenster über 200 ms (Start 222, 840 s
  379 ms).
- **Bewertung (Stand 13.10.2026, 18:35):** Die Last am Eventtag (etwa 20
  Anfragen/s) und bis zum Doppelten davon laufen fehlerfrei mit p95 unter
  400 ms. Verfehlt wurde nur der p99 von public_state im ersten Lauf 1 (2346 ms)
  durch drei kurze, alle Funktionen betreffende Aussetzer, die in Lauf 2 und 3
  nicht wiederkehrten (Netz oder Supabase-Störung). Nicht geprüft: Mobilfunk
  mit wechselnden IPs, eine Last von mehreren Rechnern, Pausieren des
  Free-Tier-Projekts bei Inaktivität. Offen für Friedrich: Supabase Pro für
  den Event-Monat (gegen Pausieren und mehr Rechenleistung) und, ob Aufräumen
  jetzt folgen soll.

