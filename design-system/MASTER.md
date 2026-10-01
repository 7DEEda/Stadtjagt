# Design System Stadtjagd

Stand 01.10.2026. Quelle der Wahrheit für das Aussehen von `index.html` und
`geraete-test.html`. Die Werte sind die, die im Spiel stehen; neue Seiten und
Änderungen halten sich daran. Ansicht mit allen Bausteinen:
`design-system/index.html` (im Browser öffnen, hell und dunkel umschaltbar).

Aufbau nach dem Muster der Skill **ui-ux-pro-max** (Master-Datei, Abweichungen
je Seite unter `design-system/pages/`). Herleitung am Ende.

---

## 1. Grundidee: Kartenpapier und Signalorange

Die Stadtjagd ist ein Orientierungslauf durch eine Stadt. Das Spiel sieht aus
wie eine Wanderkarte: mattes Papier mit Höhenlinien als Grund, darauf Karten
(Panels) wie eingeklebte Zettel, und **ein** Signalorange für alles, was man
tun soll. Draußen, in der Sonne, mit einer Hand, beim Gehen.

| Grundsatz | heißt konkret |
|---|---|
| **Lesbar in der Sonne** | jedes Textpaar mindestens 4,5:1, Bedienelemente 3:1, im hellen Design geprüft, nicht nur im dunklen |
| **Ein Orange pro Ansicht** | genau ein Hauptknopf je Zustand; Orange nie als Fläche für Schmuck |
| **Mit dem Daumen** | Trefferfläche mindestens 44 px (Handy) und 48 px (Tablet), 8 px Abstand |
| **Ruhig** | nichts springt: feste Breiten für Zahlen und verschlüsselte Zeichen, Bewegung nur mit Bedeutung |
| **Hochformat** | das Handy wird hochkant gehalten; quer erscheint ein Hinweis (Tablet und Spielleitung dürfen quer) |
| **Spiel, nicht Formular** | Teamtiere, Kompass, verschlüsselter Name, Ziffernschloss: das Spiel darf Spaß machen, die Bedienung bleibt nüchtern |

---

## 2. Farben

Alle Farben sind Token auf `:root`; Bausteine verwenden nur Token, keine
Hex-Werte. Dunkel ist kein umgedrehtes Hell, sondern eigene, entsättigte Werte.

### Grund und Schrift

| Token | Hell | Dunkel | Einsatz |
|---|---|---|---|
| `--paper` | `#F1F5EE` | `#0F1B18` | Seitengrund, Kartenpapier |
| `--card` | `#FFFFFF` | `#16261F` | Panels, Dialoge |
| `--ink` | `#17302A` | `#E4EEE8` | Text, Ziffernräder, Nadel-Schaft |
| `--muted` | `#5B6F68` | `#9BB1A9` | Nebentext, Beschriftungen |
| `--line` | `#D3DECF` | `#2A3F38` | Trennlinien, Panel-Rand (nur Schmuck, nicht für Bedienelemente) |
| `--feld` | `#7D9189` | `#5E786F` | Ränder von Eingabefeldern und Bedienelementen, mindestens 3:1 |
| `--contour` | `#CFDBC8` | `#1C312B` | Höhenlinien des Hintergrunds |

### Signal und Zustände

| Token | Hell | Dunkel | Einsatz |
|---|---|---|---|
| `--flag` | `#EE5F1B` | `#FF7A3A` | Signalorange: Hauptknopf, Route, Nadel, aktive Marken |
| `--flag-ink` | `#0F1B18` | `#0F1B18` | Schrift **auf** Orange (dunkel, nicht weiß) |
| `--flag-text` | `#C2410C` | `#FF7A3A` | Orange **als Schrift** auf hellem Grund |
| `--ok` / `--ok-bg` | `#25683F` / `#E3F1E7` | `#6CCB8E` / `#16332A` | Erfolg, „geht“, Ziffer erhalten |
| `--err` / `--err-bg` | `#B3261E` / `#FBE9E7` | `#FF8A80` / `#3A1F1C` | Fehler, abgelehnt, Löschen |
| `--warn` / `--warn-bg` | `#8A5A00` / `#FBF0D9` | `#E8B75A` / `#33290F` | Warnung, Testmodus, eingeschränkt |
| `--info-bg` | `#E6EEF4` | `#172A36` | Hinweise mit `--ink` |
| `--water` | `#2F6E9E` | `#6FA8D6` | Wasser auf der Karte, Probe-Team, Mitlesen |

### Geprüfte Kontraste

| Paar | Hell | Dunkel |
|---|---|---|
| `--ink` auf `--card` / `--paper` | 14,1 / 12,8 | 13,3 / 14,9 |
| `--muted` auf `--card` / `--paper` | 5,4 / 4,9 | 7,0 / 7,8 |
| `--flag-ink` auf `--flag` (Hauptknopf) | 5,3 | 6,8 |
| `--flag-text` auf `--card` | 5,2 | 6,1 |
| `--ok` auf `--ok-bg` | 5,8 | 6,9 |
| `--err` auf `--err-bg` | 5,6 | 6,6 |
| `--warn` auf `--warn-bg` | 5,2 | 7,7 |
| `--feld` auf `--card` (Rand) | 3,3 | 3,3 |

**Nicht erlaubt:** Weiß auf `--flag` (3,3:1), `--flag` als Schrift auf Weiß
(3,3:1), `--line` als Rand eines Bedienelements (1,4:1).

### Teamfarben (Karte der Spielleitung)

16 Farben in `TEAM_COLORS`, auf hell und dunkel unterscheidbar, Schrift darauf
über `schriftAuf()` (dunkel auf hellen Tönen). Stationen sind orange; ein Team
in Orange ist zu vermeiden.

---

## 3. Schrift

| Rolle | Schrift | Einsatz |
|---|---|---|
| `--head` | Barlow Semi Condensed 500/600/700 | Überschriften, Knöpfe, Zahlen (Entfernung, Ziffern, Restzeit) |
| `--body` | Barlow 400/500/600 | Fließtext, Beschriftungen |
| `--mono` | JetBrains Mono 700 | nur der verschlüsselte Stationsname |

Die Skill empfiehlt genau dieses Paar (Barlow Condensed mit Barlow) für
„Sport, Wettkampf, Aktion“. Schmal für Wirkung in Überschriften, normal breit
für Lesetext.

### Größen (Stufen)

| Token | Größe | Einsatz |
|---|---|---|
| `--fs-xs` | 13 px | Kartenbeschriftungen (Lücken, Stationsschilder), Zeitachse am Tablet |
| `--fs-s` | 15 px | Nebentext (`.small`), Meldungen, kleine Knöpfe, Chips, Tabellenköpfe |
| `--fs-m` | 17 px | Fließtext, Eingabefelder (nie kleiner als 16 px, sonst zoomt iOS) |
| `--fs-l` | 19 px | Ortshinweis, Rätsel, Hauptknopf, h3 |
| `--fs-xl` | 24 px | h2, Stationsname, verschlüsselter Name, Zeiten am Tablet |
| `--fs-xxl` | 32 px | h1, Teamname |
| `--fs-zahl` | 38 px, ab 700 px Breite 56 px | Entfernung, Countdown, Teamkarte |
| `--fs-rad` | 32 px | Ziffernräder |
| `--fs-schild` | 48 px | Team-Zeichen zum Hochhalten, Platz-Zeichen am Ende |

Seit 01.10.2026 stehen im Spiel nur noch diese Stufen (`var(--fs-*)` auf
`:root` in `index.html`); vorher waren es 21 verschiedene Größen. Einzige
Ausnahme ist die Beschriftung der Hintergrundkarte (`.topo`, 6 bis 12 px): sie
skaliert mit dem SVG und ist Dekor, kein Text zum Lesen. Neue Stellen nehmen
eine Stufe, keine eigene Größe. Zeilenhöhe Fließtext 1,5. Zahlen, die sich
ändern, mit `font-variant-numeric: tabular-nums`.

Kennungen und Werte mit Einheit („60 m“, „1:47 h“, Codes) brechen nie in sich
um (`white-space: nowrap`), nur davor.

---

## 4. Raum, Form, Tiefe

- **Abstände** in Schritten von 4 px: 4, 8, 12, 16, 24, 32. Panels 16 px innen,
  14 px Abstand zwischen Panels.
- **Spalte:** Handy volle Breite mit 16 px Rand; Teamleitung höchstens 460 px,
  ab 700 px Breite 600 px; Spielleitung `main.wide` bis 900 px.
- **Radien:** 14 px Panels, 10 px Knöpfe und Eingabefelder, 8 px Ziffernräder
  und Bilder, 99 px Chips. Andere Werte nicht neu einführen.
- **Schatten:** nur für Dinge, die über der Seite liegen.
  - Dialog: `0 12px 32px rgba(17,17,17,.28), 0 2px 6px rgba(17,17,17,.12)`
  - Marker und Griffe auf der Karte: `0 1px 4px rgba(0,0,0,.4)`
  - Panels haben keinen Schatten, nur den 1-px-Rand `--line`.
- **Hintergrund:** Höhenlinien-Karte (klassisch, A, B, C), fest am Fenster,
  mit Neigungs- und Scroll-Parallax. Freier Text auf der Karte bekommt einen
  Lichthof in `--paper`.

---

## 5. Bewegung

| Regel | Wert |
|---|---|
| Dauer | 160 ms für Einblenden, Zustandswechsel, Nadel |
| Kurve | `cubic-bezier(.32,.72,.4,1)` |
| Bedeutung | jede Bewegung sagt etwas: Nadel = Richtung, Einrasten = Buchstabe gefunden, Puls = neue Ziffer |
| Dauerbewegung | nur Nadeln, Parallax, das Flimmern verschlüsselter Zeichen, die Acht beim Einmessen und der Drehhinweis |
| Bewegung reduzieren | alles davon schaltet ab (`prefers-reduced-motion`), die Information bleibt |

Nicht animieren: Breite und Höhe (Layout springt), Seitenwechsel.

---

## 6. Bausteine

| Baustein | Klasse | Regeln |
|---|---|---|
| **Hauptknopf** | `.btn` | Orange, Schrift `--flag-ink`, 19 px `--head` 700, volle Breite, mindestens 48 px hoch; einer pro Ansicht |
| **Nebenknopf** | `.btn.alt` | transparent, Rand 1,5 px, Schrift `--ink` |
| **Kleiner Knopf** | `.btn.sm` | 15 px, 44 px hoch (Tablet 48 px), 8 px Abstand |
| **Gefahr** | `.btn.warn` | `--err-btn`, Schrift weiß; nur im Bestätigungsdialog oder Lösch-Bereich |
| **Weit weg** | `.btn.weit` | Nebenknopf-Optik mit Restentfernung, wird im Radius zum Hauptknopf |
| **Beschäftigt** | `[aria-busy=true]` | Text aus `data-wait` („Wird geprüft …“), bleibt farbig, nicht grau |
| **Link** | `.link` | unterstrichen, `--muted`, 44 px Trefferfläche |
| **Panel** | `.panel` | `--card`, Rand `--line`, Radius 14 px, Innenabstand 16 px |
| **Meldung** | `.msg.ok/.err/.info/.warn` | steht direkt am Auslöser (Fehler unter dem Knopf, Erfolg oben im Panel) |
| **Chip** | `.chip` | Status kurz („Läuft“, „Noch 1:47 h“); live in Orange |
| **Ziffernschloss** | `.lock .wheel` | 6 Räder in `--ink`, sechstes abgesetzt und gestrichelt (Schlussziffer), neue Ziffer pulsiert |
| **Route** | `.route` | Punkte 1 bis 5, erledigt orange, jetzt mit orangem Ring, offen mit `--feld`-Ring |
| **Kompass** | `.compass` | Ring, orange Nadel, Entfernung daneben groß; Fragezeichen, solange keine Richtung |
| **Verschlüsselter Name** | `.geheim` | `--mono`, feste Zellen (0,64 em breit, 1,2 em hoch); offen in Orange, eingerastet in `--ink`, Fortschrittsbalken |
| **Dialog** | `.overlay .dialog` | oben ausgerichtet, scrollbar, Radius 14 px, Innenabstand 24 px, immer mit sichtbarem Abbrechen |
| **Hochformat-Hinweis** | `.quer` | Handy mit Notch dreht sich im Uhrzeigersinn, Pfeil gleiche Richtung |
| **Album** | `.album` | 5 quadratische Kacheln, leere gestrichelt mit Nummer |
| **Kartenmarker** | `.mapbadge` | 28 px sichtbar, 44 px Trefferfläche, Stationen orange mit Nummer, Teams in Teamfarbe mit Tier |

### Logo

Kompass im Kreis (`logo()`): Ring in `--ink`, Nordspitze in `--flag`,
Südspitze `--ink` 55 %. Die Nadel zeigt live nach Norden, wo das Handy es
weiß. Keine weiß-orange Postenflagge mehr.

---

## 7. Bedienung und Barrierefreiheit

- Trefferflächen 44 px am Handy, 48 px am Tablet; kleine Marker bekommen eine
  unsichtbar größere Fläche.
- Kein Neuzeichnen, solange ein Finger aufliegt; Getipptes überlebt das
  Neuzeichnen.
- Jede Aktion, die den Server fragt, sagt das am Knopf (`data-wait`).
- Alles, was das Spiel für alle verändert (Spiel starten, Testmodus im
  laufenden Spiel, Freischalten, Rätsel werten, Löschen), fragt nach; Löschen
  zusätzlich mit getipptem Wort.
- Farbe nie allein: Status trägt immer auch Text oder Form.
- Labels sichtbar über jedem Feld; Zahlenfelder mit `inputmode="numeric"`.
- Zoom nie sperren.

---

## 8. Sprache in der Oberfläche

- Du/ihr, kurz, freundlich, ohne Marketing. „Wir sind da“, nicht „Check-in
  durchführen“.
- Keine Gedankenstriche (– und —) in sichtbarem Text, echte Umlaute.
- Fehler sagen, was zu tun ist („Noch 177 m bis zum Einchecken“).
- Kennungen wie Team-Code, Lauf-Kennung, Koordinaten brechen nicht um.

---

## 9. Nicht tun

- Weiße Schrift auf Orange; Orange als Schmuckfläche.
- Zweiter oranger Knopf in derselben Ansicht.
- Neue Schriftgrößen, Radien oder Schatten außerhalb der Stufen.
- Bewegung ohne Bedeutung, Animation von Breite oder Höhe.
- Emoji als Bedien-Symbol (die Teamtiere sind Spielfiguren, keine Symbole).
- Inhalte, die nur mit Hover, nur mit Maus oder nur im Querformat gehen.

---

## Herleitung mit ui-ux-pro-max (01.10.2026)

Abfragen der Skill mit „outdoor adventure scavenger hunt map game mobile team“,
„orienteering topographic map navigation compass outdoor“ und „location based
game GPS city exploration“ (Bewegung 3 von 10, Dichte 6 von 10):

- **Übernommen:** Primärfarbe „Adventure orange“ (#EA580C, das Spiel nutzt das
  verwandte #EE5F1B) mit einer kühlen Kartenfarbe daneben (bei uns `--water`);
  Schriftpaar Barlow Condensed und Barlow („Sports/Fitness: energetic,
  condensed, action“); Stil „Paper“ für hohen Kontrast draußen (mattes Papier,
  Tintenschrift); Bewegung „subtle“, 150 bis 300 ms; die Regeln der Quick
  Reference zu Kontrast, Trefferflächen, Rückmeldung und reduzierter Bewegung.
- **Nicht übernommen:** die vorgeschlagenen Seitenmuster (App-Store-Landingpage,
  Konferenz-Landingpage, horizontale Scroll-Reise), weil die Stadtjagd keine
  Landingpage ist; Calistoga/Inter und reines Dunkel-Design, weil Barlow und
  Hell-Dunkel schon tragen und draußen das helle Design zählt.

Zwei unabhängige Kritiken vom selben Tag (`.ui-design/reviews/stadtjagd_20261001.md`)
haben die Kontrast- und Bedienregeln in Abschnitt 2 und 7 geprägt.
