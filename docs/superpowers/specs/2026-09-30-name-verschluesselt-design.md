# Stationsname verschlüsselt: Spezifikation

Stand 30.09.2026, umgesetzt und live. Mockups: `mockups/name-verschluesselt.html`,
`mockups/station-karte.html`. Migration: `supabase/migrations/20260930200000_name_verschluesselt.sql`.

## Entscheidungen (Friedrich, 30.09.2026)

| Frage | Entscheidung |
|---|---|
| Echt unter Verschluss oder nur Anzeige | nur die Anzeige; der Name kommt im Klartext ans Handy |
| Wieder verschlüsseln beim Weggehen | nein, einmal entschlüsselte Buchstaben bleiben stehen |
| Ortshinweis | erscheint erst, wenn der Name ganz lesbar ist |
| Schwellen | Meter je Station, auf einer Karte einstellbar; leer heißt nicht verschlüsselt |
| Testmodus | die Annäherung wird vorgespielt, sobald die Station dran ist |

## Verhalten

- `stations.reveal_start_m` (hier beginnt es) und `reveal_clear_m` (ab hier lesbar).
- Anteil = (beginnt - Entfernung) / (beginnt - klar), begrenzt auf 0 bis 1; so viele
  Buchstaben stehen fest. Reihenfolge zufällig, je Name fest.
- Schloss je Station im `localStorage`. Ohne Standort bleibt der Name verschlüsselt.
- Eine Schrift (JetBrains Mono), Felder fester Breite und Höhe: die Zeile springt nicht.
- Testmodus: 3 s ganz verschlüsselt, dann 7 s Auflösen.

## Spielleitung

Beim Bearbeiten einer Station: Karte mit drei Kreisen (Einchecken, ganz lesbar,
Entschlüsseln beginnt), Griffe zum Ziehen, Felder für die Meter, Station davor mit
direktem Weg, Vorschlag aus der Etappe (60 % und 30 %), Probe-Team mit Vorschau.

## Prüfen

`python tools/pruefstand/name.py` (Prüfstand, 28 Prüfungen),
`python tools/pruefstand/name_db.py` (Probelauf gegen die Datenbank, 13 Prüfungen).
Draußen beim Hinlaufen noch nicht gesehen.
