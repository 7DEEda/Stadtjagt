# Seite: Rückblick-Show

Ergänzt `design-system/MASTER.md`. MASTER ist für Handys und Tablets geschrieben; die Rückblick-Show läuft
auf einem Beamer oder Fernseher (16:9, 1920x1080, skaliert auf jedes Fenster). Hier stehen nur die
Abweichungen, alles andere bleibt: Token, Schriften (Barlow, Barlow Semi Condensed, lokal aus `vendor/fonts`),
Radien, Schatten, ein Orange als Signal, keine weiße Schrift auf Orange. Code: `rueckblick.js`,
`rueckblick.css` (alle Regeln unter `#rueckblick`). Spezifikation: `docs/superpowers/specs/2026-10-15-rueckblick-show-design.md`.

| Regel | MASTER | Bühne | Warum |
|---|---|---|---|
| Schriftstufen | `--fs-xs` 13 bis `--fs-schild` 48 | `--bs-xs` 30, `--bs-s` 36, `--bs-m` 48, `--bs-l` 72, `--bs-xl` 120, `--bs-uhr` 168, `--bs-titel` 200 (auf der 1920er Bühne) | Lesen aus 5 bis 10 m. Bei 1280x720 ist die kleinste Schrift noch 20 px (`rueckblick.py` prüft es, auch für Emoji) |
| Bewegung | 160 ms | Einblenden 480 ms, Kamerafahrt 1,8 s, Walze rastet in 650 ms; Kurve `cubic-bezier(.32,.72,.4,1)` bzw. `smoothstep` | 160 ms sind auf der Bühne ein Ruck; jede Bewegung behält eine Bedeutung (Kamera = wohin es geht, Puls = Station gelöst, Walze = Uhrzeit wird gelesen, Foto gleitet = Reihenfolge der Ankunft) |
| Szenenwechsel | Seitenwechsel nicht animieren | Überblendung 480 ms | Bühne ohne Schnitt; nichts ändert Breite oder Höhe |
| Kartenfarben | nur Grund-Token | neu, nur unter `#rueckblick`: `--park`, `--strasse`, `--strasse-rand`, `--fluss`, `--flaeche`, `--haus`, `--haus-rand`, `--gruen`, hell und dunkel | Grundkarte aus OpenStreetMap ohne Kacheln; `index.html` kennt `--park` und `--strasse` mit anderen Werten für die Hintergründe |
| Hauptknopf | einer pro Ansicht | nur "Rückblick starten" in Vorbereiten; Orange sonst nur für Stationen, "Prag" im Vorspann und die Stationsleiste | Signal bleibt Signal |
| Schrift auf Orange | `--flag-text` im hellen Thema | wie MASTER | `--flag` als Schrift auf Hell ist nicht erlaubt (4,5:1) |
| Deckkraft | | keine `opacity` auf Schrift; Ortsnamen auf der Karte tragen einen Halo in Papierfarbe | Kontrast 4,5:1 auch über Park und Fluss |

Teamfarben wie auf der Karte der Spielleitung. `TEAM_COLORS[8]` (`#E65100`) ist orange und damit nah an den
Stationen; die Show unterscheidet Teams und Stationen über die Form (Kreis mit Tier gegen Kreis mit Ziffer).

Hell und dunkel: die Show folgt `sj.thema` der App, `T` schaltet um. Bewegung reduzieren
(`prefers-reduced-motion`): Schnitt statt Kamerafahrt, keine Pulse, Walzen und Gleiten, Ziffern erscheinen zur
Rastzeit; der Zeitraffer bleibt.

Steuerleiste: in Bildschirm-Pixeln (nicht mitskaliert), fest am Fensterrand, nur bei Mausbewegung, blendet nach
2,5 s aus. Vorbereiten-Panel, Fotos-durchsehen-Panel, Fotowand und großes Foto bleiben über ihr.
