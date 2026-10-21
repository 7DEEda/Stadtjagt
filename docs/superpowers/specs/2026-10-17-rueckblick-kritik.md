# Rückblick-Show: Kritik zusammengeführt

Sechs Linsen (Dramaturgie, Bühne, Steuerung, Publikum, Daten, Technik). Muss-Befunde selbst im Code nachgeprüft (rueckblick.js, index.html) und an Bildern aus den Kritikordnern (fotos5-14000, platz3-12400, abspann-30000, 1920x1080-dark-20-abspann-37100, 1920x1080-light-04-weg3-17000, abbruch-weg4).

Kurzurteil: Das Gerüst trägt (Zeitraffer, Fotos, 3, 2, 1 mit Halt und drehenden Walzen, Leiste ohne Spoiler, Show läuft nach dem Laden ohne Netz). Gefährdet ist der Abend an drei Stellen: das Finale verrät sich selbst (Fotowand Station 5) und schneidet den Jubel ab, die Steuerung verzeiht keinen nervösen Klick, und echte GPS-Daten zeigen Dinge, die die Probe nicht zeigt (Abbrüche, Wege nach dem Koffer).

## Muss (sonst leidet der Abend sichtbar)

| # | Befund | Linsen | Beleg (geprüft) | Änderung | Aufwand |
|---|---|---|---|---|---|
| M1 | Nach dem Aufdecken läuft die Show nach 6,8 s (Platz 1: 7,3 s) von selbst weiter, mitten in Jubel und Kofferübergabe. | Dramaturgie, Steuerung, Publikum | rueckblick.js:303-304, 536, 757: Team erst bei halt+3100, Kapitelende bei 12500/14000, dann geheZu(i+1) | Zweiter Haltepunkt je Platz-Kapitel bei `dur - 300` (Logik wie `k.halt` in takt(), eigener Merker `Z.frei2`). Bild steht fertig (Name, Foto, Route), Weiter geht zum nächsten Platz. Schalter: "Vor und nach jedem Koffer-Platz anhalten". Leiste: "Platz 3, aufgedeckt, wartet auf Weiter". | klein |
| M2 | Weiter verzeiht keinen Fehlgriff im Finale: (a) Weiter in den ersten 2,6 s (Platz 1: 3,6 s) überspringt den Platz ganz, (b) zweiter Klick während der 3,1 s Walzenrasten springt zum nächsten Platz, bevor der Name je zu sehen war, (c) gehaltene Taste rast durch alle Kapitel. | Steuerung, Dramaturgie | rueckblick.js:507-511 (nach `Z.frei` geht jedes Weiter per geheZu weiter, vor dem Halt ebenso), 534, 1102-1124 (kein `e.repeat`) | In weiter(): Platz-Kapitel mit `Z.lokal < k.halt` springt auf den Halt (`Z.lokal = k.halt; Z.haelt = true`). Zwischen Aufdecken und `enthuellt + 1500` Weiter und Zurück ignorieren. Allgemein Weiter in den ersten 600 ms nach einem Kapitelwechsel verwerfen. In taste(): `if (e.repeat) { e.preventDefault(); return; }` außer für H. | klein |
| M3 | Weiter in der Pause ändert den Zustand, nicht das Bild: die alte Szene bleibt stehen, die neue hat Deckkraft 0. Nach Schwarzbild (B) ist die Show immer pausiert, also trifft das genau den Klicker-Fall; die Spielleitung drückt mehrfach und springt blind. | Steuerung | rueckblick.js:501-505 und 679-680 (Überblendung hängt an `Z.lokal`, das in der Pause 0 bleibt), 811 (schwarz setzt `spielt = false`) | Weiter und Zurück setzen `Z.spielt = true` (wie PowerPoint). schwarz() merkt sich, ob die Show lief, und setzt beim Zurückholen fort; Klick aufs Schwarzbild holt das Bild zurück, Leiste liegt darüber (z-index 10). | klein |
| M4 | Fotowand Station 5 zeigt etwa 25 s vor Platz 3 die komplette Rangfolge, mit "zuerst da: Adler 15:15" darüber. Platz 1 zeigt danach dasselbe Foto noch einmal. | Dramaturgie, Publikum | rueckblick.js:291-292 (Sortierung nach Check-in), 594-598, 604 (bestesFoto nimmt die höchste Station); Bild fotos5-14000 liest sich Adler, Eule, Tiger, Fuchs ... = Platz 1 bis 10 | Für die letzte Station: Fotos mit `zufallsReihe()` mischen, Block "zuerst da" weglassen. bestesFoto() für die Platz-Kapitel: frühestes Foto des Teams (aufsteigend nach position), damit es keine Wiederholung ist. | klein |
| M5 | Show lässt sich ohne Rückfrage verlassen: Maus-Seitentaste, Alt+Pfeil links, Touchpad-Wischen oder der Link "Zur Spielleitung" beenden sie und zeigen die Spielleitung mit der Rangliste auf dem Beamer; Strg+R und Neuladen-Knopf verwerfen alle Fotos, ohne Netz ist die Show dann tot. | Steuerung, Technik | index.html:4051-4054 (hashchange ruft beenden()), rueckblick.js:1152-1165 (fotoCache.clear), kein beforeunload, kein popstate | Beim Öffnen `history.pushState` setzen, popstate abfangen und auf der Leiste fragen: "Rückblick verlassen? Die Fotos werden danach neu geladen." mit "Verlassen" und "Bleiben". beforeunload mit `e.preventDefault()` in Phase vorbereiten und show (über `hoere()`, beenden() räumt ab). Beim Verlassen zuerst Schwarzbild, nie direkt die Rangliste. Kapitel-id in sessionStorage merken und nach Neuladen im Vorbereiten "Weiter bei Platz 2" anbieten. | mittel |
| M6 | Wege nach dem Zieleinlauf landen auf dem Beamer und in den km: Handys melden weiter, solange das Spiel läuft. Café, Hotel, Heimweg erscheinen in "Bis zum Spielende" und im Abspann vor 100 Kollegen; km rund 27 % zu hoch. Die Probe zeigt das nicht. | Publikum, Daten | rueckblick.js:187 (schneidet bei tEnd, nicht bei t.fertig), 202; index.html:3524 (sendet bei `status === "running"`); nur das Platz-Kapitel schneidet richtig (758) | In aufbereiten() je Team bei `Math.min(tEnd, ms(t.finishedAt) + 2 * MIN)` abschneiden; der Kopf bleibt im Ziel stehen. In maybeReport() nichts senden, wenn das Team fertig ist (finishedAt gesetzt). beispielDaten() (Zeile 100) ohne Zittern nach dem Koffer. | klein |
| M7 | GPS bricht ab oder startet spät: Kopf steht eine Stunde an der falschen Stelle (Tiger um 15:12 noch an Station 1) oder ist beim Start schon an Station 3, im Widerspruch zur Seitenleiste. Vorbereiten meldet "12 von 12 mit GPS-Route". | Daten | rueckblick.js:192-197 (Check-ins nur, wenn `pts.length < 2`), 255-261; Bild abbruch-weg4 | Check-ins immer einmischen: für jedes `s.ein` und `s.ok` ohne GPS-Punkt im Umkreis von 3 min einen Punkt an der Station einfügen, bei erstem GPS-Punkt später als t0 + 5 min den Startpunkt bei t0 davor; sortieren, `g` neu rechnen (gestrichelt). Vorbereiten: "Tiger: GPS nur bis 14:25, danach aus den Check-ins". Prüfstand Gruppe 5: Fall mit Abbruch und Spätstart. | mittel |
| M8 | Fotos durchsehen, dann Bild ab oder Pfeil: Show startet mit der alten Kapitelliste, ein bewusst aussortiertes Foto läuft vor allen. | Steuerung | rueckblick.js:1059-1066 (kapitelBauen nur bei Fertig), 509, 524, 813 (Phase bleibt "vorbereiten") | starten() ruft immer zuerst `kapitelBauen()`. Zusätzlich im Durchsehen `Z.phase = "durchsehen"`, damit startbar() falsch ist. | klein |
| M9 | Platz-Bild: die Teamroute läuft quer durch "Platz 3", Walzen, Teamname und Mitgliedernamen; im Dunkeln ist sie dagegen kaum zu sehen. | Bühne | Bild platz3-12400; rueckblick.js:304 (Kamera volle Bühne), 758, 610; rueckblick.css:40-41 | Route in die Fläche, die frei ist: für Platz-Kapitel einen `<div class="schleier">` (72 %) als erstes Kind in platzHTML und die Spur mit voller Deckkraft darüber, Textspalte darüber (z-index). Wenn S5 umgesetzt wird, mit der dort beschriebenen Route über die Übersicht verbinden. Mit rueckblick.py Gruppe 10 hell und dunkel prüfen. | klein |

## Sollte

| # | Befund | Linsen | Änderung | Aufwand |
|---|---|---|---|---|
| S1 | Selfies stehen nur rund 0,3 s groß und ruhig (rueckblick.js:735-743), dafür 5 x 18 s Zeitraffer im gleichen Takt; ab Weg 3 kennt der Saal das Muster. | Publikum, Dramaturgie | Je Foto 1,6 s (`a = 900 + i * 1600`, Flug ab `a + 1100`), also gut 0,8 s groß und ruhig. Wege nach Dramaturgie: weg1 18 s, weg2 bis weg4 je 12 s, weg5 20 s. Abspann höchstens 24 s und 4 Spalten (breitere Unterschriften, kein "Flamingo Station" ohne Ziffer). Bilanz bei 54 Fotos etwa +7 s. | klein |
| S2 | Fotowände 1 bis 4 nach Ankunft: der Langsamste kommt fünfmal allein und zuletzt; Uhrzeiten springen (Wand zeigt Fotozeit, Sortierung nach Check-in, Eule 14:23 oben und 14:33 am Foto). | Publikum, Bühne | Wand in fester Teamreihenfolge (wie die Legende am Start). "zuerst da" im Kopf bleibt an Station 1 bis 4. Uhrzeit aus den Kachel-Unterschriften streichen, nur im großen Spot zeigen. | klein |
| S3 | Endspurt verrät die Zielreihenfolge: Ring an Station 5 in Ankunftsfolge, Ereignisband "Station 5 gelöst" mit Uhrzeit (weg5, Bis zum Spielende). | Dramaturgie | An der letzten Station im Band nur "an Station 5", kein "gelöst"; Ring an der letzten Station in Teamreihenfolge belegen (ringPlatz, rueckblick.js:428-433, 476-484). | klein |
| S4 | Finale-Aufbau: kein Aktwechsel vor Platz 3 (nur 480 ms Überblendung), und "Alle Teams" nach dem Sieger ist 15 s Lesestoff, der den Höhepunkt zurücknimmt; Plätze 4 bis 12 kommen, wenn niemand mehr hinschaut. Rang 48 px und Zeile 30 px reichen nur bis zu den mittleren Tischen. | Dramaturgie, Bühne | Reihenfolge umbauen (siehe Choreografie): "Plätze ab 4" als Tafel vor dem Finale (ohne Top 3), Zwischenbild "Die Koffer", 3, 2, 1, Siegerbild, Abspann. Tafel: Teamname 64 px, Rang 48 px, eine Angabe in 36 px ("nach 1:26 h" oder "4 von 5 Stationen"). | mittel |
| S5 | Platz-Bild: Halt hängt links oben mit 700 px leerer Karte (mitte = 740 auch vor dem Foto, Zeile 610); Name kommt ohne Schlag mit derselben 480-ms-Blende wie jede Unterzeile; Mitgliedernamen 30 px grau (20 px bei 1280x720); Walzen bleiben nach dem Aufdecken die schwerste Fläche; Querformat-Foto auf 420x560 beschnitten (nur Mitte bleibt); Platz 1 sieht aus wie Platz 3. | Dramaturgie, Bühne, Publikum, Daten | Halt: Spalte mittig (left 400), Walzen eine Stufe größer. Ab enthuellt Spalte in 480 ms auf left 180. Schlag: 150 ms nach letzter Walze Bühne kurz in Teamfarbe (Schleier 25 % auf 0 in 600 ms), Teamkreis scale 0,85 auf 1,05 auf 1. Danach Walzen auf scale(.6) opacity .7. Namen `var(--ink)` 48 px. Foto mit `foto.ratio >= 1`: Klasse `quer` 600x450. Platz 1: letzte Walze 1,2 s, 400 ms Stille, Name scale 1,15 auf 1, Bühne in Teamfarbe getönt, Route über die Übersicht mit .puls an allen fünf Stationen, Fotos aller Stationen als Fächer. | mittel |
| S6 | Kein Startbild: vor dem Start steht Vorbereiten mit "Beim Spielende unterwegs: Igel, Otter" auf dem Beamer, der Vorspann läuft nach 7,5 s ohne Halt in die Karte. | Dramaturgie, Steuerung, Publikum | Vorspann bekommt `halt: 3000` (bei Halt-Option): Logo, Titel, Fakten stehen, bis Weiter. HANDOFF, Ablauf am Eventtag: Fotos durchsehen und starten, bevor der Beamer gespiegelt wird. | klein |
| S7 | Schlussbild trägt nicht: Karte "Stadtjagd Prag" verdeckt Station 5, Schleier 82 % macht alles fast schwarz oder fast weiß, keine Köpfe; ohne Fotos verdeckt dieselbe Karte den Zielring. Das Bild steht den Rest des Abends. | Bühne, Dramaturgie, Publikum, Daten | Kamera für beide Abspann-Varianten `{ x: 800, w: 1120 }` mit Ringradius im Rand. In den letzten 2,5 s (`L > k.roll.lauf`) Schleier auf .25 abblenden und `koepfe: true`. Mit S4 umgesetzt alternativ das Siegerbild als Schluss. | klein |
| S8 | Kein sicherer Rand für Fernseher mit Overscan; der Hinweis "gestrichelt: ohne GPS-Signal" steht ohne Halo bei x 48, y 1040 und überdruckt Station 5 (Bild 1920x1080-light-04-weg3-17000). | Bühne | Hinweis in die Seitenleiste über die Stationsleiste. Taste R und Haken "Rand für Fernseher" multiplizieren in skalieren() mit 0,94. Seitenleiste padding 64px 96px 72px 64px, Marken-Grenze in zeichneKarte 96/54 px. Rand-Scan 5 % in rueckblick.py. | klein |
| S9 | Pause ist nach 2,5 s nicht mehr zu erkennen, und jede Leertaste lässt die Leiste auf dem Beamer aufblitzen (gegen Spezifikation 5.2). | Steuerung | Pausiert bleibt die Leiste stehen; beim Fortsetzen per Taste sofort weg. | klein |
| S10 | Leertaste auf der Halt-Checkbox schaltet den Halt still aus, statt zu starten (Zeile 1111 lässt Leertaste an Inputs durch). | Steuerung | In den onchange-Handlern der Optionen `e.target.blur()`. | klein |
| S11 | Leertaste nach dem Abspann startet den Vorspann neu (Zeile 521). | Steuerung | Am Ende tun Leertaste und Weiter nichts; Neustart nur mit Pos1 oder über die Leiste. | klein |
| S12 | Probe ist nach dem Start nicht mehr als Probe erkennbar; der Vorspann zeigt ein echtes Datum mit erfundenen Siegern. | Steuerung | In der Probe dauerhaft "Probe" oben links auf der Bühne und in der Leiste ("Probe: Platz 3, wartet auf Weiter"), im Vorspann "Probe" statt Datum. | klein |
| S13 | Hell/Dunkel während der Show: 8,6 s mit 3,7 fps, weil grundkarte() das Raster löscht und die Vektorkarte zeichnet. | Technik, Steuerung | In thema() und mqFn nur karteRastern() aufrufen und das alte Bild bis zum Tausch stehen lassen; mqFn in Phase show übergehen. | klein |
| S14 | Bei echter GPS-Dichte (4.000 bis 8.000 Punkte) fallen weg5 und "Bis zum Spielende" auf 19 bis 25 fps; die Probe hat nur 3.500 Punkte und zeigt das nicht. | Technik | In aufbereiten() ausdünnen (Punkt nur bei mehr als 8 m Abstand oder Lückenbeginn). Probe-Daten auf 600 Punkte je Team. | klein |
| S15 | Ausreißer aus zwei oder drei Punkten bleiben (Fuchs 6,7 statt 4,8 km, Linien quer über die Karte). | Daten | ohneAusreisser() verwirft Läufe bis 3 Punkte; in rueckblick.py Gruppe 5 `zwei == 4` prüfen. | klein |
| S16 | Spielende vor der letzten Station: Schlusskapitel heißt "Zum Koffer" und nennt die schon verlassene Station. | Daten | In kapitelFuer: ist `letzte < d.stationen.length`, Schlusskapitel mit `station = d.stationen[letzte].position`, `ziel = false`, "Weg zu Station n". | klein |
| S17 | Niemand im Ziel: kein Finale, keine Vorwarnung, zwölfmal "unterwegs". Teams mit Technikpech tragen bis zu vier Marken (gestrichelter Ring, "ohne GPS", allein am Start, Kamera zoomt für sie heraus). | Daten, Publikum | Vorbereiten ohne Platz-Kapitel: "Kein Team im Ziel: nach den Wegen kommt Alle Teams", Halt-Haken ausblenden. Ohne Platz "nicht im Ziel", ohne Check-in "nicht gestartet". In "Alle Teams" km-Feld leer statt "ohne GPS"; gestrichelten Ring am Kopf weglassen; Teams ohne Check-in nach dem Start nicht im Kamerarahmen. | klein |
| S18 | Dunkles Thema: Ring um Köpfe und Marken ist fast so dunkel wie die Karte; Indigo, Petrol, Oliv, Magenta versinken (1,7 bis 2,4:1). | Bühne | Im dunklen Thema Ring `var(--ink)`, Linien `mischen(t.farbe, "#FFFFFF", .35)`. | klein |
| S19 | Seitenleiste zieht den Blick: Ereignisliste wechselt 22 Mal in 18 s, 168-px-Uhr springt zweimal je Sekunde. | Bühne | Liste durch ruhigen Zähler ersetzen ("Station 3 gelöst", groß "7 von 12", feste Zeile "zuerst: Eule 14:23"), Uhr auf 120 px, Kopfzeile "Stadtjagd Prag" weg. | mittel |
| S20 | Panda (#E65100) hat fast das Stationsorange (ΔE 6), drei Blaugrün-Teams kaum zu trennen. | Bühne | Vor dem Auslosen TEAM_COLORS[8] gegen #455A64 tauschen, [10] prüfen. Entscheidung Friedrich, die App nutzt dieselbe Liste. | klein |
| S21 | Ladeanzeige bricht jedes Wort in eine Zeile ("Fotos / 3 / von / 48"), Balken springt nach den Fotos auf 0. | Technik | Ladezeile ohne li-Raster (`grid-column: 1 / -1`), Balken für Karte und Schriften voll stehen lassen. | klein |
| S22 | Scheitert die Rasterung, steht trotzdem "Alles geladen", und alle Kartenkapitel laufen mit 3,7 fps. | Technik | Warnzeile bei `D.hatKarte && !D.karteFertig`: "Karte nicht vorbereitet, die Kartenkapitel ruckeln" mit "Erneut versuchen". | klein |
| S23 | Laden der Fotos bei zähem Server ohne Ausweg (3 Versuche je 60 s). | Technik | Nach 20 s Knopf "Ohne die restlichen Fotos weiter"; erster Versuch mit 20 s Zeitlimit. | mittel |

## Kann

| # | Befund | Linsen | Änderung | Aufwand |
|---|---|---|---|---|
| K1 | Mittelfeld hat keinen eigenen Moment, alle Ehrungen gehen an die Spitze. | Publikum | Im Kopf der Fotokapitel 1 bis 4 neben "zuerst da" "schnellstes Rätsel" mit Tier, Name, Dauer (min(ok minus ein)). Nur Positives. | klein |
| K2 | H zeigt die Tastentabelle über der laufenden Show. | Steuerung | H pausiert, Schließen setzt fort, wenn sie lief. | klein |
| K3 | Verspätete Rasterung nach beenden() wirft "Cannot set properties of null". | Technik | In beenden() `rasterNr++`, in den Rückrufen auf `root && D` prüfen, Blob-URL freigeben. | klein |
| K4 | "1 Foto nicht geladen" sagt nicht, welches. | Technik | Schlüssel sammeln, "Eule Station 2" ausgeben. | klein |
| K5 | Verbindungsfehler spricht die Teams an ("Wartet kurz und tippt"). | Technik | Eigener Text: "Keine Verbindung zum Server. Prüfe das WLAN und versuche es erneut." | klein |
| K6 | Takt zeichnet in der Pause weiter (13 % Hauptthread). | Technik | zeichnen() nur bei spielt, Halt oder Merker `Z.neu`. | klein |
| K7 | Kartenraster auf 4K mit 200 % weich. | Technik | Grenze an devicePixelRatio koppeln, höchstens 8192 px. | klein |
| K8 | Großes Foto wird für die ausgeblendete Leiste kleiner gerechnet (bis 15 % bei 1280x720). | Bühne | `--unten` in Phase show 0. | klein |
| K9 | Stationsradien schimmern im Vorspann als Kreise durch. | Bühne | `#rb-buehne[data-art=titel] .radius{display:none}`. | klein |
| K10 | Vorbereiten bei 1280x720: 16 px Schrift, Prüfstand merkt es nicht. | Bühne | SCAN misst getBoundingClientRect; Tastenzeile weg bei `--vs < 0,9`. | klein |
| K11 | Mehr als 12 Teams: Ring hat 12 feste Plätze, Legende schneidet ab. | Daten | Ringplätze = max(12, Teamzahl), Radius mitwachsen, Legende ab 13 dreispaltig. | klein |
| K12 | Gleichstand in derselben Sekunde zeigt denselben Code. | Daten | Unter den Walzen "0,4 Sekunden vor Delfin". | klein |
| K13 | Wenige Fotos im Abspann laufen links hinter der Karte. | Daten | Spalten = min(4, Fotozahl), mittig; unter 3 Fotos Abspann ohne Rolle. | klein |
| K14 | Uhrzeiten hängen an der Zeitzone des Laptops. | Daten | `timeZone: "Europe/Prague"` in uhr, uhrS, fakten().datum. | klein |

## Verworfen oder umentschieden

- **Countdown 12 bis 4 mit je eigenem Auftritt** (Dramaturgie): verworfen zugunsten einer Tafel "Plätze ab 4", die auf einmal einblendet. Publikum begründet zu Recht, dass sonst der letzte Platz einen eigenen Auftritt bekommt. Die Spannung bleibt: man weiß, welche drei Teams fehlen, nicht in welcher Reihenfolge.
- **Tier-Walze statt Uhrzeit** (Publikum): verworfen. Die Uhrzeit-Walzen sind der Trommelwirbel, und das Siegerteam erkennt seine eigene Code-Zeit, bevor der Name kommt; das ist ein guter Moment für den Raum. Der fehlende Schlag beim Namen wird über S5 gelöst.
- **Rückblick-Dateien in den Service Worker** (Steuerung): verworfen. Technik hält zu Recht dagegen, dass die Handys sonst 1,9 MB mittragen; Fotos und Spuren kämen ohnehin aus der Datenbank. Stattdessen M5 (Rückfrage, Kapitel merken) und im HANDOFF: Rückblick vor dem Essen mit Netz laden, Tab offen lassen.
- **T in der Show nur über die Leiste** (Steuerung): nicht nötig, wenn S13 umgesetzt ist.
- **Themenwechsel als muss** (Technik): auf sollte gesenkt. Ausgelöst wird er nur durch T; Windows wechselt das Thema ohne Zusatzwerkzeug nicht von selbst.
- **Schlussbild und Lückenhinweis als muss** (Bühne): auf sollte gesenkt (S7, S8); sichtbar unschön, aber kein Inhalt oder Moment geht verloren.
- **Fotos 0,3 s als muss** (Publikum): auf sollte gesenkt (S1), weil die Fotos im Abspann und als Wand trotzdem kommen. Dort steht es als erster Sollte-Befund, weil es den größten Gewinn fürs Mittelfeld bringt.
- **Check-in-Zeit statt Fotozeit unter den Kacheln** (Bühne): durch S2 überholt (feste Teamreihenfolge, Zeit nur im Spot).
- **"Doppelklick springt auf den enthüllten Zustand"** (Dramaturgie) gegen "Klick ignorieren" (Steuerung): Ignorieren gewinnt. Ein prellender Klicker würde sonst die Walzen sofort einrasten lassen und den Trommelwirbel kosten.

## Finale: Gesamtchoreografie

Voraussetzung: M1 bis M4, S3 bis S5. Option "Vor und nach jedem Koffer-Platz anhalten" ist an.

| Schritt | Spielleitung tut | Publikum sieht |
|---|---|---|
| 1. Bis zum Spielende | nichts | Zeitraffer bis Spielende, Ring an Station 5 in Teamreihenfolge, Band nur "an Station 5". Keine Reihenfolge ablesbar. |
| 2. Plätze ab 4 (etwa 15 s, läuft durch) | nichts | Tafel mit allen Teams außer den drei Koffer-Teams, Rang groß, je eine Angabe ("nach 1:26 h" oder "4 von 5 Stationen"), Teams ohne Ziel als "nicht im Ziel" nach Fortschritt. Jeder findet sich; man sieht, welche drei fehlen. |
| 3. Die Koffer (hält) | spricht frei ("Drei Teams fehlen noch"), dann Weiter | Drei Medaillen 3, 2, 1 groß nebeneinander auf dichtem Schleier. Stilles Bild als Zäsur. |
| 4. Platz 3, Vorlauf und Halt | wartet; Weiter zu früh springt nur auf den Halt | "Platz 3" mit Medaille, darunter die Walzen, mittig. Walzen drehen endlos. Leiste: "Platz 3, wartet auf Weiter". |
| 5. Platz 3, Aufdecken | Weiter, danach 3 s lang wirkungslos | Ziffern rasten eine nach der anderen ein (2,4 s); das Team erkennt seine Code-Zeit. 700 ms Stille. |
| 6. Platz 3, Schlag | nichts | Blitz in Teamfarbe, Teamkreis springt mit Überschwinger auf, Name 128 px und Mitglieder 48 px in Textfarbe; Walzen treten zurück. Spalte gleitet nach links, Foto (frühestes, Hoch- oder Querformat) fährt rechts ein, Route zeichnet sich unter einem Schleier. |
| 7. Platz 3, Nach-Halt | ruft das Team nach vorn, Kofferübergabe, Foto; dann Weiter | Fertiges Bild steht, so lange es dauert. Leiste: "Platz 3, aufgedeckt, wartet auf Weiter". |
| 8. Platz 2 | wie 4 bis 7 | wie 4 bis 7, Silber |
| 9. Platz 1 | wie 4 bis 7, Halt etwas länger moderieren | Wie Platz 3, aber eskaliert: letzte Ziffer rastet langsam (1,2 s), 400 ms Stille, Bühne tönt sich in Teamfarbe, Name tritt mit Skalierung 1,15 auf 1 auf, Route über die Übersicht mit Puls an allen fünf Stationen, Fotos aller Stationen als Fächer. Nach-Halt. |
| 10. Siegerbild (hält) | Schlussworte, dann Weiter | Podest 2, 1, 3 mit Tier, Name, Medaille; darunter "12 Teams, zusammen 46,9 km gelaufen". |
| 11. Abspann (etwa 24 s) | nichts, Applaus | Fotorolle in Zufallsreihenfolge, 4 Spalten. |
| 12. Schlussbild (bleibt) | Leertaste tut nichts mehr | Alle Routen in Teamfarbe mit Köpfen im Ziel, Schleier abgeblendet, Station 5 frei neben der Karte "Stadtjagd Prag", OSM-Nennung. |

Notbremse bleibt: Ende springt zu "Die Koffer", B schaltet schwarz und setzt beim Zurückholen dort fort, wo die Show war.

## Bleibt so

- Reihenfolge 3, 2, 1 mit Halt vor jedem Platz; die Walzen drehen im Halt weiter (sichtbarer Trommelwirbel ohne Ton).
- Auflösung in Stufen: Uhrzeit, dann Team und Mitglieder namentlich, dann Foto, dann Route; die Route des Teams erst nach dem Aufdecken (kein Spoiler über die Teamfarbe).
- Leiste und Kapitelnamen verraten nichts ("Platz 3", keine Teamnamen in Titeln oder Fortschrittsband).
- "zuerst da" an den Stationen 1 bis 4, Ring nach Ankunft und Puls beim Lösen an den Stationen 1 bis 4, "Bis zum Spielende" für die Nachzügler.
- Feste Bühne 1920x1080 als Ganzes skaliert; Station und Team über die Form getrennt; Ortsnamen mit Halo; Bühnenstufen als Token.
- Großes Einzelfoto mit Namensschild, dann in die Wand; fehlende Fotos ohne Platzhalter; Abspann in Zufallsreihenfolge, OSM-Nennung nur dort.
- Gemeinsame Zahlen statt Vergleich ("96 Leute", "zusammen 46,9 km").
- Steuerung: F5 abgefangen, B schwarz, Ende zum Finale, Zurück wie im Mediaplayer, Klick auf die Bühne tut nichts, PIN-Feld schluckt die Tasten, Takt mit dt-Grenze 100 ms, Wake Lock.
- Technik: Karte einmal rastern (55 bis 60 fps), nach dem Laden keine einzige Anfrage mehr, Blob-URLs ohne Leck, Schriften über Mustertext vorgeladen, Rückblick-Dateien nicht im Service Worker, Probe ohne Datenbank.
- Daten: Kapitelgrenzen nach der Hälfte der Teams mit Mindestabstand und Klemme am Spielende; kein leeres Fotokapitel; Sprungfilter über die Nachbarn; Teams ohne GPS gestrichelt über die Check-ins (dieses Prinzip auf Abbrüche ausweiten, M7); Platz-Kapitel schneidet die Spur am Koffer ab (auf alle Kapitel ausweiten, M6).
- Gesamtlänge um 4:40 ohne Halte.

## Reihenfolge der Umsetzung

1. Steuerung absichern: M2, M3, M8, S10, S11 (alles in weiter(), taste(), starten(), schwarz(); ein Nachmittag).
2. Finale: M1, M4, M9, S3, dann S4 und S5 als ein Paket.
3. Daten: M6, M7, S15, S14 mit Prüfstand-Fällen.
4. Verlassen und Neuladen: M5.
5. Rest nach Zeit; S20 vor dem Auslosen entscheiden.

Bildschirmfotos der Linsen:
- C:/Users/fried/AppData/Local/Temp/claude/c--Users-fried-OneDrive---TSE-AG-Berlin-Claude-TSE-Marketing-Stadtjagt/f0498f04-9151-4a20-bce5-7ecd947855f3/scratchpad/kritik-dramaturgie/
- C:/Users/fried/AppData/Local/Temp/claude/c--Users-fried-OneDrive---TSE-AG-Berlin-Claude-TSE-Marketing-Stadtjagt/f0498f04-9151-4a20-bce5-7ecd947855f3/scratchpad/kritik-buehne/shots/
- C:/Users/fried/AppData/Local/Temp/claude/c--Users-fried-OneDrive---TSE-AG-Berlin-Claude-TSE-Marketing-Stadtjagt/f0498f04-9151-4a20-bce5-7ecd947855f3/scratchpad/kritik-steuerung/
- C:/Users/fried/AppData/Local/Temp/claude/c--Users-fried-OneDrive---TSE-AG-Berlin-Claude-TSE-Marketing-Stadtjagt/f0498f04-9151-4a20-bce5-7ecd947855f3/scratchpad/kritik-publikum/
- C:/Users/fried/AppData/Local/Temp/claude/c--Users-fried-OneDrive---TSE-AG-Berlin-Claude-TSE-Marketing-Stadtjagt/f0498f04-9151-4a20-bce5-7ecd947855f3/scratchpad/kritik-daten/
- C:/Users/fried/AppData/Local/Temp/claude/c--Users-fried-OneDrive---TSE-AG-Berlin-Claude-TSE-Marketing-Stadtjagt/f0498f04-9151-4a20-bce5-7ecd947855f3/scratchpad/kritik-technik/
