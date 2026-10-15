# Rückblick-Show: Design

Stand 15.10.2026. Entwurf, nicht gebaut. Mockup zum Anklicken:
`mockups/rueckblick/index.html` (eigenständig, offline, Beispieldaten Prag mit
12 Teams und 5 Stationen; Tasten wie unten, `H` zeigt sie).

## 1. Worum es geht

Nach dem Spiel, beim Abendessen, zeigt ein Beamer oder Fernseher (16:9,
1920x1080 oder 1280x720) einen Rückblick von etwa 3 bis 5 Minuten: die Wege
aller Teams als Zeitraffer über Prag, dazwischen die Gruppenselfies der
Stationen, am Ende die Plätze mit den Koffern und alle Teams. Die Spielleitung
startet ihn mit ihrer PIN. Alles kommt aus den echten Spieldaten; die Show
erfindet nichts dazu.

Rahmen:

- **Nur nach dem Spiel** (`status = finished`). Vorher ist die Ansicht gesperrt.
- **Keine Eingaben am Spiel.** Die Show liest nur; sie ändert nichts in der
  Datenbank (Ausnahme, die schon heute gilt: `admin_state` löscht die Fotos,
  wenn das Löschdatum erreicht ist, siehe 7.).
- **Ohne Maus bedienbar**, mit Tastatur oder Präsentations-Klicker.
- **Läuft nach dem Laden ohne Netz.** Alle Daten und Fotos liegen dann im
  Speicher des Browsers; ein WLAN-Aussetzer im Restaurant stört nicht.
- **Formsprache der Stadtjagd** (`design-system/MASTER.md`: Kartenpapier,
  Signalorange, Barlow), nicht das TSE-Firmendesign.

## 2. Was es schon gibt und wiederverwendet wird

Die Show braucht **keine neue RPC und keine Migration** (Begründung in 6.4).

| Baustein | Wo | Was die Show davon nimmt |
|---|---|---|
| `admin_tracks(p_pin)` ohne `p_since` | Migration `20260918160000_routes.sql` | alle Punkte je Team als `[Breite, Länge, Zeit in ms]`, `pointCount`, je Station `checkedInAt` und `solvedAt`, dazu `status`, `startedAt`, `finishedAt` |
| `admin_state(p_pin)` | zuletzt `20261006090000_admin_fehlversuche.sql` | `status`, `testMode`, `route`, `prizeCount`, `selfieOn`, `photosDeleteOn`, `photoCount`, `start` (Name, Koordinaten), `stations` (immer die echte Route, mit `radiusM`), je Team `name`, `members`, `leaderName`, `solved`, `place`, `finishedAt` |
| `admin_photos(p_pin)` | `20261002120000_teststation.sql` | Liste `teamId`, `teamName`, `position`, `stationName`, `route`, `takenAt` |
| `admin_photo(p_pin, p_team, p_position, p_full, p_route)` | dieselbe | ein Foto als Base64 (`p_full = true`: 1280 px, bis 700 KB; sonst Vorschau 320 px) |
| Zeitachse der Spielleitung | `index.html`: `drawMap`, `syncTracks`, `timelineRows`, `playStep` | Lückenregel `LUECKE_M` (50 m) und `LUECKE_MS` (90 s) für gestrichelte Strecken; Abspielen als Zeitraffer (dort 45 s für das ganze Spiel); Grenze 30 km um die erste Station |
| Teamfarben und Tiere | `TEAM_COLORS`, `teamColor(i)`, `TEAM_EMOJI`, `teamEmoji()` | dieselbe Farbe je Team wie auf der Karte der Spielleitung (Reihenfolge von `admin_state.teams`, nach Namen) |
| Plätze | `platzZeichen()`, `MEDAILLE`, `prizeCount` | Medaille 1 bis 3, weitere Koffer-Plätze mit Koffer |
| Rangliste | `public_state.ranking` (SQL) | dieselbe Reihenfolge: Platz, dann gelöste Stationen absteigend, dann letzte Lösung aufsteigend |
| Formate | `fmtDur()`, `fmtClock()`, `uhrzeit()` | „1:26 h“, „14:32“ |
| Logo | `logo()` | Kompass im Kreis |
| Hell/dunkel | `sj.thema`, Token doppelt (Media-Query und `data-theme`) | die Show folgt der Wahl der App, `T` schaltet um |

## 3. Ablauf der Show

Die Show besteht aus Kapiteln. Jedes Kapitel hat eine feste Dauer und ist eine
reine Funktion der Zeit im Kapitel: Pause, Zurück und Springen ergeben immer
dasselbe Bild.

| Kapitel | Dauer | Inhalt |
|---|---|---|
| Vorspann | 7,5 s | Logo (Nadel pendelt sich nach Norden ein), „Stadtjagd“, „Prag“, darunter Datum, Teams, Leute, Stationen |
| Start | 5,5 s | Karte am Startpunkt, alle Teams im Ring um das Haus; rechts Uhr 14:00 und die Teams als Legende (Farbe, Tier, Name) |
| Weg zu Station k (k = 1 bis 5) | 18 s, ohne Fotos 24 s | Zeitraffer vom Ende des vorigen Kapitels bis zur Grenze k (siehe 6.3); Kamera auf vorige und nächste Station plus alle Teams; rechts Kapitel, Stationsname, Uhr, „seit Start“, die letzten drei Ereignisse („an Station 2“, „Station 2 gelöst“), Stationsleiste 1 bis 5 |
| Fotos Station k | 1,2 s + 1 s je Foto + 2,6 s | nur wenn es Fotos gibt: Kopf mit Nummer, Name, „zuerst da“; die Fotos erscheinen in der Reihenfolge der Ankunft einzeln groß in der Mitte (mit Team und Uhrzeit) und gleiten dann an ihren Platz in der Wand |
| Bis zum Spielende | 10 s | nur wenn nach der letzten Grenze noch mehr als 3 min Spiel lagen: Zeitraffer bis `finishedAt`, Kamera auf Station 5 und alle Teams, Uhr endet mit „Spielende“ |
| Platz 3, 2, 1 | je 12,5 s, Platz 1 14 s | Finale, rückwärts. Titel mit Medaille, sechs Ziffernwalzen drehen und rasten links nach rechts auf die Uhrzeit ein, zu der das Team den Koffer-Code eingegeben hat (`finishedAt`, HH:MM:SS); danach Tier, Name, alle Mitglieder, rechts ein Gruppenfoto des Teams (letzte Station mit Foto), dahinter zeichnet sich seine Route über die Karte |
| Alle Teams | 15 s | Karten in Ranglisten-Reihenfolge: Platz (Medaille oder „Platz 7“, ohne Platz „unterwegs“), Strecke in km oder „ohne GPS“, Tier und Name, „im Ziel 15:26, nach 1:26 h“ oder „4 von 5 Stationen“ |
| Alle Routen | 9 s, bleibt stehen | alle Wege auf der Karte, Teams am Endpunkt; Karte unten links: „Stadtjagd Prag“, „12 Teams, zusammen 53,5 km gelaufen“ |

Länge mit 12 Teams und allen Fotos etwa 4:10 min, ohne Fotos etwa 3:25 min
(Mockup: 249 s und 206 s). Bei 16 Teams und allen Fotos etwa 4:30 min. Kürzer
als 3 min wird es nicht, weil die Wege ohne Fotos auf 24 s wachsen.

**Spannung im Finale.** Jeder ahnt das Ergebnis, die Rangliste stand am
Nachmittag auf allen Handys. Das Finale ist darum eine Ehrung, die Spannung
kommt aus der Inszenierung: rückwärts von Platz 3 nach 1, die Walzen drehen,
bevor sie die Uhrzeit zeigen, und (Schalter, Vorgabe an) die Show **hält vor
jedem Aufdecken an**, während die Walzen weiterdrehen, bis die Spielleitung
`Weiter` drückt. So kann sie ansagen („Den dritten Koffer bekommt …“). Damit
der Zeitraffer nichts vorwegnimmt, zeigt er keine Zieleinläufe, nur Check-ins
und gelöste Stationen.

## 4. Bühne und Gestaltung

### 4.1 Bühne

- Feste Bühne 1920x1080, per `transform: scale()` auf das Fenster eingepasst,
  mittig; der Rand außen hat die Papierfarbe. 1280x720 ist dieselbe Bühne mal
  2/3, nichts ordnet sich um.
- Kartenkapitel: Karte links (1320 px), Seitenleiste rechts (600 px, `--card`,
  Rand `--line`). Alle anderen Kapitel nutzen die ganze Bühne.
- Die Karte läuft in zwei SVG-Ebenen: Welt (Meter, Grundkarte und Spuren,
  Linien `vector-effect: non-scaling-stroke`) und Schirm (Bildschirm-Pixel:
  Stationen, Teams, Pulse, Ortsnamen), damit Marken und Schrift bei jedem
  Ausschnitt gleich groß bleiben.

### 4.2 Abweichungen von MASTER.md (eigene Seite `design-system/pages/rueckblick.md`)

MASTER.md ist für Handys und Tablets geschrieben. Für die Bühne gelten diese
Abweichungen, alles andere bleibt (Token, Schriften, Radien, Schatten, ein
Orange als Signal, keine weiße Schrift auf Orange):

| Regel | MASTER | Bühne | Warum |
|---|---|---|---|
| Schriftstufen | `--fs-xs` 13 bis `--fs-schild` 48 | `--bs-xs` 30, `--bs-s` 36, `--bs-m` 48, `--bs-l` 72, `--bs-xl` 120, `--bs-uhr` 168, `--bs-titel` 200 (auf der 1920er Bühne) | Lesen aus 5 bis 10 m. Bei 1280x720 ist die kleinste Schrift noch 20 px (geprüft) |
| Bewegung | 160 ms | Einblenden 480 ms, Kamerafahrt 1,8 s, Walze rastet in 650 ms, Kurve bleibt `cubic-bezier(.32,.72,.4,1)` bzw. `smoothstep` | 160 ms sind auf der Bühne ein Ruck; jede Bewegung behält eine Bedeutung (Kamera = wohin es geht, Puls = Station gelöst, Walze = Uhrzeit wird gelesen, Foto gleitet = Reihenfolge der Ankunft) |
| Szenenwechsel | Seitenwechsel nicht animieren | Überblendung 480 ms | Bühne ohne Schnitt; nichts ändert Breite oder Höhe |
| Kartenfarben | nur Grund-Token | neu `--park`, `--strasse`, `--strasse-rand`, `--fluss`, `--flaeche`, hell und dunkel (Werte im Mockup; dieselben Rollen wie bei Hintergrund-Variante B) | Grundkarte ohne Kacheln |
| Hauptknopf | einer pro Ansicht | auf der Bühne gibt es nur „Rückblick starten“ im Vorbereiten; Orange sonst nur für Stationen, „Prag“ im Vorspann und die Stationsleiste | Signal bleibt Signal |

Teamfarben wie auf der Karte der Spielleitung. Hinweis: `TEAM_COLORS[8]`
(`#E65100`, bei 12 Teams Panda) ist orange und damit nah an den Stationen;
MASTER sagt „ein Team in Orange ist zu vermeiden“. Die Show unterscheidet
Teams und Stationen über die Form (Kreis mit Tier gegen Kreis mit Ziffer).
Empfehlung unabhängig von der Show: den Wert in `TEAM_COLORS` tauschen,
bevor ausgelost wird (Entscheidung Friedrich).

### 4.3 Hell und dunkel

Die Show folgt `sj.thema` der App; `T` schaltet um und merkt es. Empfehlung
fürs Restaurant: hell bei Fernseher oder hellem Raum (Beamer machen dunkle
Flächen im Licht grau), dunkel bei Beamer im abgedunkelten Raum. Beides ist im
Mockup geprüft.

### 4.4 Bewegung reduzieren

Bei `prefers-reduced-motion` entfallen Kamerafahrten (Schnitt auf den neuen
Ausschnitt), Pulse, Walzendrehen (Ziffern erscheinen zur Rastzeit), das Gleiten
der Fotos und das Pendeln der Nadel. Der Zeitraffer selbst bleibt: er ist der
Inhalt, wird bewusst gestartet und lässt sich anhalten.

## 5. Steuerung

### 5.1 Tasten

| Taste | Wirkung |
|---|---|
| `Leertaste`, `K`, `F5` | Start, Pause; hält die Show vor einem Aufdecken, deckt sie auf |
| `→`, `Bild ↓`, `Enter`, `N` | Weiter: nächstes Kapitel, bzw. aufdecken |
| `←`, `Bild ↑`, `Rücktaste`, `P` | Zurück: Kapitel von vorn; innerhalb der ersten 1,5 s ins Kapitel davor |
| `Pos1`, `Ende` | zum Anfang, zum Finale (Platz 3) |
| `F` | Vollbild an und aus (Fullscreen API; `Esc` beendet es im Browser) |
| `B`, `.` | Bild schwarz und Pause; jede Taste holt es zurück |
| `T` | hell oder dunkel |
| `H`, `?` | Tastenhilfe; `Esc` schließt sie |

Präsentations-Klicker senden `Bild ↓/↑`, oft `B` oder `.` für Schwarz und `F5`
oder `Shift+F5` für „Präsentation starten“. `F5` wird abgefangen, sonst lädt
die Seite neu und die geladenen Fotos sind weg.

### 5.2 Steuerleiste

Unten, in Bildschirm-Pixeln (nicht mitskaliert, Knöpfe 48 px): Zurück,
Start/Pause/Abspielen, Weiter, ein Fortschrittsband mit einem Abschnitt je
Kapitel (anklickbar), Kapitelname („Platz 2, wartet auf Weiter“), „1:12 /
4:09“, Hell/Dunkel, Vollbild, Tasten. Sie erscheint **nur bei Mausbewegung**
und blendet nach 2,5 s aus; der Mauszeiger verschwindet mit ihr. Tasten zeigen
sie nicht, damit auf dem Beamer nichts aufblitzt.

### 5.3 Bildschirm wach

Während die Ansicht offen ist, hält ein Wake Lock den Bildschirm an
(`navigator.wakeLock`, wie `wachHaltenPruefen()`), nach `visibilitychange` neu.
Geht er nicht, steht in Vorbereiten: „Bildschirmschoner am Laptop ausschalten.“

## 6. Daten

### 6.1 Einstieg und PIN

- Neue Ansicht `#/rueckblick`. In `#/admin` steht nach dem Spielende im Kopf
  neben „Spiel fortsetzen“ der Knopf „Rückblick“ (`btn sm alt`), dazu im Reiter
  Zeitachse unter der Zeitachse. Der Link öffnet die Ansicht im selben Tab; die
  PIN liegt dort schon im `sessionStorage` (`sj.pin`).
- Ohne PIN (anderer Rechner, neuer Tab) zeigt die Ansicht ein PIN-Feld wie
  `#/admin` und prüft mit `admin_state`.
- Vor dem Spielende: „Der Rückblick startet nach dem Spielende.“ und nichts
  weiter.
- `#/rueckblick/probe` spielt die Show mit eingebauten Beispieldaten (wie im
  Mockup), ohne PIN und ohne Datenbank. Dafür: Beamer, Ton aus, Lesbarkeit im
  Raum am Nachmittag prüfen, ohne echte Daten zu zeigen.
- Der 10-s-Abruf der App läuft in `#/rueckblick` nicht (Zweig in der
  Abruf-Schleife wie bei `admin`, nur ohne Aufruf).

### 6.2 Laden (Vorbereiten)

Die Ansicht beginnt mit „Vorbereiten“, das auch der Beamer schon zeigt:

1. `admin_state(p_pin)`. Prüfen: `status = finished`, `testMode = false` (sonst
   Sperre, siehe 7.), `startedAt` gesetzt.
2. `admin_tracks(p_pin)` ohne `p_since` (ganzer Verlauf, etwa 12 x 400 Punkte,
   unter 300 KB).
3. `admin_photos(p_pin)`, nur Einträge mit `route = 'echt'` und einem Team aus
   `admin_state`.
4. Je Foto `admin_photo(p_pin, teamId, position, true, 'echt')`, drei
   gleichzeitig, in Ankunftsreihenfolge der Kapitel. Base64 wird zu einem Blob
   und `URL.createObjectURL`; vor dem Start `img.decode()`, damit nichts
   ruckelt. Schlägt ein Foto zweimal fehl, kommt die Vorschau (`p_full =
   false`); fehlt auch sie, bleibt das Foto weg. 60 Fotos zu 300 KB sind etwa
   18 MB, über Restaurant-WLAN unter einer Minute.

Vorbereiten zeigt nur Fakten und Folgen (wie im Mockup):

- „Spiel beendet um 16:40 Uhr, 10 von 12 Teams im Ziel“, darunter „Beim
  Spielende unterwegs: Igel, Otter“
- „11 von 12 Teams mit GPS-Route“, darunter „Igel ohne GPS: Weg aus den
  Check-ins, gestrichelt“ (Warnzeichen statt Haken)
- „54 Gruppenfotos geladen“ mit Fortschritt „Fotos 23 von 54“ während des
  Ladens, darunter „Gelöscht am 19.10.2026“; bei Fehlern „3 Fotos nicht
  geladen“ und „Erneut versuchen“
- „Alles geladen, die Show läuft jetzt auch ohne Netz“
- Schalter „Gruppenfotos zeigen“, Link „Fotos durchsehen (2 aus)“, Schalter
  „Vor jedem Koffer-Platz anhalten, Weiter deckt auf“
- Hauptknopf „Rückblick starten“, daneben „Dauer etwa 4:09 min“, darunter die
  wichtigsten Tasten

„Fotos durchsehen“ zeigt alle Fotos je Station; Antippen nimmt eines aus dem
Rückblick („Gelöscht wird nichts.“). Die Auswahl gilt nur für diese Sitzung.

### 6.3 Aufbereiten

Alles im Browser, einmal beim Laden:

- **Projektion:** Meter um einen Bezugspunkt (`x = (lng - lng0) * 111320 *
  cos(lat0)`, `y = (lat0 - lat) * 111200`); für 2 km genau genug.
- **Punkte filtern:** nur zwischen `startedAt - 1 min` und `finishedAt`; nur
  innerhalb 1 km um Start oder eine Station (die Spielleitung nimmt 30 km, die
  Bühne braucht einen festen Ausschnitt); GPS-Sprünge mit mehr als 15 km/h zum
  vorigen behaltenen Punkt fallen weg.
- **Lücken:** wie `drawMap`: ein Stück mit mehr als `LUECKE_M` oder mehr als
  `LUECKE_MS` bei mehr als 15 m ist gestrichelt. Steht irgendwo eine Lücke,
  steht unten links „gestrichelt: ohne GPS-Signal“.
- **Team ohne GPS** (weniger als 2 Punkte): Weg aus Start (`startedAt`) und je
  Station Check-in und Lösung; ganz gestrichelt, die Marke trägt einen
  gestrichelten Ring.
- **Strecke:** Ankermethode wie `laufrichtung()`: ein Stück zählt erst, wenn
  der Punkt mehr als 15 m vom letzten Anker entfernt ist. So zählt das Zittern
  im Stand nicht mit. Ohne GPS keine Zahl, sondern „ohne GPS“.
- **Ereignisse:** aus `admin_tracks.teams[].stations`: Check-in und gelöst je
  Station, zeitlich sortiert. Keine Zieleinläufe (3.).
- **Grenzen der Kapitel:** `g0 = startedAt`; `gk` = Zeitpunkt, zu dem die Hälfte
  der Teams mit Fortschritt Station k gelöst hat (bei weniger als der Hälfte die
  letzte Lösung von k), mindestens 2 min nach `g(k-1)`. Hat niemand k gelöst,
  enden die Wege bei k-1. Zwischen den Grenzen läuft die Zeit mit `smoothstep`,
  am Anfang und Ende eines Kapitels langsam.
- **Kamera:** je Kapitel ein Rahmen um vorige Station, Station k und alle
  Teamköpfe zur Grenze, mindestens 760 m breit, in den Kartenbereich
  eingepasst; Übergang 1,8 s (Mittelpunkt linear, Maßstab logarithmisch).
- **Ringplätze:** Kommt ein Team einem Ort (Start, Station) näher als 70 m,
  gleitet seine Marke auf einen festen Platz im Ring um den Ort (12 Plätze,
  116 px), in der Reihenfolge der Ankunft an diesem Ort. Plätze verschieben
  sich nicht, wenn andere dazukommen; nichts springt.
- **Rangliste:** wie `public_state.ranking` (2.).

### 6.4 Warum keine neue RPC

Alles, was die Show zeigt, liefern die vier Admin-Funktionen schon, mit
derselben PIN-Prüfung. Eine eigene `admin_rueckblick`-Funktion würde nur
dieselben Daten in einem Aufruf bündeln; der Gewinn (ein statt drei Abrufe,
einmal am Abend) rechtfertigt keine Migration mit Probelauf und Rechten.
Zwei Eigenheiten der bestehenden Funktionen sind bewusst hingenommen und in der
Show abgefangen:

- `admin_tracks` liest die Stationen über die Sicht `stations`, also die aktive
  Route. Ist der Testmodus an, kämen nur Check-ins der Teststation. Darum
  sperrt die Show bei `testMode = true` (7.).
- `admin_state` löscht beim Abruf die Fotos, wenn `photos_delete_on` erreicht
  ist (`<= current_date`). Das gilt heute schon für jede Spielleitungsansicht;
  die Show liest es nur ab (7.).

## 7. Randfälle

| Fall | Verhalten |
|---|---|
| Gruppenselfie war aus, keine Fotos | Keine Fotokapitel, Wege 24 s; Vorbereiten zeigt die Fotozeile nicht. Ob Fotos kommen, entscheidet ihr Vorhandensein, nicht `selfieOn` (der Schalter kann nach dem Spiel umgestellt sein) |
| Einzelne Fotos fehlen (übersprungen, Funkloch) | Das Team fehlt in dieser Wand, ohne Platzhalter; die Wand ordnet sich nach der Zahl. Kein „kein Foto“ auf der Bühne |
| Station ohne ein Foto | kein Fotokapitel für diese Station |
| Foto lädt nicht | zweimal versuchen, dann Vorschau, dann weglassen; Vorbereiten nennt die Zahl |
| Löschdatum erreicht | `admin_state` hat die Fotos schon gelöscht: Vorbereiten zeigt „Fotos am 17.10.2026 gelöscht (Löschdatum)“, Show ohne Fotos. Vorbeugen: im Reiter Fotos ein Datum **nach** dem Abendessen setzen (das Datum selbst löscht schon); dort steht nach dem Spielende unter dem Datum: „Der Rückblick braucht die Fotos: ein Datum nach dem Abendessen wählen.“ |
| Löschdatum steht bevor | Vorbereiten nennt es („Gelöscht am 19.10.2026“) |
| Team ohne GPS | Weg aus Check-ins, gestrichelt, Ring gestrichelt, in „Alle Teams“ „ohne GPS“ statt km |
| GPS-Lücken, Sprünge | gestrichelt bzw. verworfen (6.3) |
| Standortdaten schon gelöscht (`admin_clear_positions`) | alle Teams wie „ohne GPS“; Vorbereiten: „Standortdaten gelöscht: Wege aus den Check-ins“. Die Show läuft trotzdem |
| Team nicht im Ziel | Marke bleibt beim Spielende stehen, wo sie war; in „Alle Teams“ „unterwegs“ und „4 von 5 Stationen“, nach der Ranglistenregel einsortiert |
| Weniger Teams im Ziel als Koffer | nur so viele Platz-Kapitel, wie es Plätze bis `prizeCount` gibt |
| Kein Team im Ziel | kein Finale; nach dem letzten Weg direkt „Alle Teams“ |
| `prizeCount` größer als 3 | Platz 4 und weiter mit Koffer-Zeichen statt Medaille, Reihenfolge rückwärts wie oben |
| Testmodus an | Sperre in Vorbereiten: „Der Testmodus ist an. Der Rückblick zeigt nur das echte Spiel: im Reiter Stationen ausschalten.“ Fotos der Teststation (`route = 'test'`) fallen ohnehin weg |
| Spiel läuft noch oder ist fortgesetzt (`admin_resume`) | Sperre wie oben („startet nach dem Spielende“); nach erneutem Beenden gilt das neue `finishedAt` |
| Spielleitung hat Stationen per „Freischalten“ oder „Rätsel werten“ gesetzt | zählt wie Check-in und Lösung (dieselben Spalten) |
| Teamleitung wechselte im Spiel | egal: Punkte hängen am Team, nicht an der Person |
| Station ohne Koordinaten | fehlt auf der Karte; Kapitel und Fotos bleiben |
| 16 Teams | Ring hat 12 Plätze: ab dem 13. Team rücken die Plätze auf 16 (Winkel 22,5°, Radius 150 px); „Alle Teams“ 4x4 |
| Lange Namen | Stationsname bis drei Zeilen; Teamnamen sind Tiere (kurz); Mitglieder umbrechen nur zwischen Namen |
| Netz fällt während der Show aus | egal, alles ist geladen |
| Seite neu geladen | Daten sind weg (nur im Speicher), Vorbereiten lädt neu; `F5` ist deshalb abgefangen |
| Zwei Fenster mit der Show | unabhängig, beide nur lesend |

## 8. Karte ohne Kacheln

**Entscheidung: die Show nutzt keine Leaflet-Kacheln, sondern einen eigenen
Stadtplan als SVG.** Gründe:

- Netz: OSM-Kacheln kommen nur online, Leaflet selbst kommt heute noch von
  unpkg. Die Show soll nach dem Laden ohne Netz laufen.
- Bewegung: Kacheln laden bei jedem Zoomschritt nach; bei Kamerafahrten
  stünden graue Kacheln auf dem Beamer.
- Lesbarkeit und Formsprache: Kacheln tragen kleine Beschriftungen und viele
  Farben; die Stadtjagd sieht aus wie Kartenpapier, nur die Spuren sollen
  leuchten.
- Ein Rendering statt zwei: Kein Zweig „mit Kacheln“ und „ohne Kacheln“, der
  getrennt geprüft werden müsste.

Umsetzung:

- `hintergrund/rueckblick.svg`, erzeugt von `tools/hintergrund/hintergrund.py`
  (neuer Aufruf `--rueckblick`) aus den OSM-Daten, die dort schon liegen
  (`prag.json`, Rahmen 50.054 bis 50.118 / 14.386 bis 14.437). Für etwas Luft
  im Osten den Rahmen bis 14.445 neu laden (`osm-abfrage.txt`). Inhalt: Moldau,
  Parks (Letná, Stromovka), Výstaviště, Straßen in zwei Rängen, Wege
  gestrichelt, Höhenlinien der Letná; Koordinaten in Metern derselben
  Projektion wie 6.3 (Bezugspunkt als `data-lat0`, `data-lng0`), Klassen wie
  Hintergrund-Variante B, Farben über die Token aus 4.2. Ziel unter 150 KB.
- Ortsnamen (Letná, Stromovka, Holešovice, Výstaviště, Vltava) nicht im SVG,
  sondern in der Schirm-Ebene, damit sie bei jedem Ausschnitt 30 px groß sind.
- Pflichthinweis „© OpenStreetMap-Mitwirkende“ klein unten rechts in der
  Kartenfläche (ODbL).
- **Ausweichlösung, falls die Datei fehlt oder nicht lädt:** Papier mit den
  Höhenlinien der klassischen Wanderkarte (liegt in `index.html`) als
  Grundkarte, darauf Stationen, Startpunkt und Spuren wie gewohnt. Die Show
  bleibt vollständig, nur ohne Straßen und Fluss.
- Das Mockup zeigt eine stilisierte Fassung dieses Plans (von Hand
  angenähert, nicht lagegenau).

## 9. Datenschutz

- **Zusage an die Teams ändern, vor dem Event.** Heute steht in der App „Sehen
  können es nur euer Team und die Spielleitung.“ (`index.html`, Hinweis beim
  Gruppenfoto, Zeile um 959) und „Das Foto sehen nur euer Team und die
  Spielleitung.“ (Selfie-Schritt, um Zeile 1656). Zeigt der Rückblick Fotos,
  stimmt das nicht mehr. Neu: „Sehen können es euer Team, die Spielleitung und
  beim Abendessen alle im Rückblick.“ bzw. „Das Foto sehen euer Team, die
  Spielleitung und beim Abendessen alle im Rückblick.“ Wird das nicht vor dem
  Event live, zeigt die Show keine Fotos (Schalter in Vorbereiten aus).
- Fotos nur im Speicher (Blob-URLs), nie in `localStorage` oder auf der
  Festplatte; beim Verlassen der Ansicht `URL.revokeObjectURL`.
- Einzelne Fotos lassen sich vor dem Start ausnehmen („Fotos durchsehen“).
- Namen der Mitglieder sind schon öffentlich (Teamkarte, Rangliste); die Show
  zeigt keine Codes, keine Lösungen, keine Positionen einzelner Personen.

## 10. Code-Aufbau

- **Neue Datei `rueckblick.js`**, nachgeladen beim ersten Aufruf von
  `#/rueckblick` (wie `hintergrund/*.svg`), damit die Handys im Spiel sie nie
  laden. Etwa 700 Zeilen, ohne Bibliothek. Aufbau wie im Mockup:
  `aufbereiten(roh)`, `kapitelBauen()`, `zeichneKarte(T, kam, modus)`,
  `szeneBauen()`, `zeichnen()` (reine Funktion von Kapitel und Zeit),
  `takt()` (requestAnimationFrame), `vorbereiten()`, `durchsehen()`,
  Tastatur, Leiste, `skalieren()`. Beispieldaten für `#/rueckblick/probe` als
  `rueckblickProbe()` in derselben Datei.
- **`index.html`:** Route `rueckblick` in `render()` (eigene Hülle ohne Kopf),
  Abruf-Schleife überspringt sie, Knopf „Rückblick“ im Admin-Kopf und im
  Reiter Zeitachse bei `finished`, die beiden Fototexte aus 9., der Satz zum
  Löschdatum aus 7., neue Token `--park` usw. und `--bs-*` (beide dunklen
  Blöcke ändern).
- **`hintergrund/rueckblick.svg`** und Generator (8.).
- **`design-system/pages/rueckblick.md`** mit den Abweichungen aus 4.2.
- **Service Worker:** für die Show nicht nötig (sie lädt online und läuft
  dann offline).

## 11. Prüfen

- **Prüfstand `tools/pruefstand/rueckblick.py`** gegen `mock.js`: Szenario
  „admin-beendet“ mit Spuren (vorhanden über `adminTracks()`), Fotos
  (`fotoListe()`, `admin_photo`), einem Team ohne GPS, einem nicht im Ziel,
  einem fehlenden Foto, einem Foto der Teststation. Prüft: Sperre vor
  Spielende und bei Testmodus; Kapitelliste (keine Teststation, keine leeren
  Fotokapitel); Tasten (Start, Pause, Weiter, Zurück, Ende, Halt vor dem
  Aufdecken, Schwarz, Hilfe, `F5` lädt nicht neu); keine Gedankenstriche im
  sichtbaren Text; kleinste Schrift bei 1280x720 mindestens 20 px; nichts ragt
  aus der Bühne; Bildschirmfotos 1920x1080 und 1280x720, hell und dunkel.
  Ergebnis vor `browser.close()` drucken (Chrome 155 hängt sonst, siehe
  HANDOFF). Im Vordergrund mit Timeout.
- Keine Datenbankänderung, also kein Probelauf `*_db.py`; `rechte_db.py`
  bleibt unberührt grün.
- Am Gerät: einmal mit `#/rueckblick/probe` auf dem Beamer des Restaurants
  oder einem vergleichbaren, Lesbarkeit aus der letzten Reihe, Klicker.

Abnahme: Show läuft mit echten Daten eines Probespiels von Start bis Abspann
ohne Eingriff in 3 bis 5 Minuten; jede Taste aus 5.1 tut, was dort steht; nach
dem Laden Netz aus, die Show läuft weiter.

## 12. Offen für Friedrich

- Fotos im Rückblick zeigen und dafür die Zusage in der App vor dem Event
  ändern (9.)? Vorgabe im Entwurf: ja.
- Halt vor jedem Platz als Vorgabe an (zum Ansagen) oder durchlaufen lassen?
- Teamfarbe Orange (`#E65100`) tauschen (4.2)?
- Eventdatum steht noch nicht im HANDOFF; der Vorspann nimmt das Datum aus
  `startedAt`.

## 13. Mockup

`mockups/rueckblick/index.html` mit `fonts.css` und `fonts/` (Barlow und
Barlow Semi Condensed, Kopie aus `mockups/design-varianten/`). Öffnen per
Doppelklick oder über einen lokalen Server. Zum Springen: `?k=platz1&t=9000`
(Kapitel und Millisekunden), `?thema=dark`, `?fotos=0`; in der Konsole
`RB.zeige("fotos2", 4500)`. Beispieldaten: 12 Teams, 96 Leute, die fünf
Prager Stationen, Start 14:00, Ende 16:40, 10 Teams im Ziel, Igel ohne GPS,
Otter mit 14 min GPS-Lücke, Pinguin, Flamingo und Wolf mit Umwegen, drei
fehlende Fotos. Die Fotos sind gezeichnete Platzhalter.
