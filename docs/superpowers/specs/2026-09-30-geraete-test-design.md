# Geräte-Test: Spezifikation

Stand 30.09.2026. Freigegeben im Gespräch, Mockup: `mockups/geraete-test.html`.

## Zweck

Ein Prüfstand, mit dem Friedrich auf mehreren eigenen Handys und Geräten
herausfindet, welche Funktionen des Spiels dort tragen und welche angedachten
Funktionen machbar wären. Ziel ist Wissen vor dem Event, damit vor Ort nichts
überrascht. Kein Pflicht-Check für Teilnehmende, kein Bezug zur Anmeldung.

## Bausteine

| Datei | Aufgabe |
|---|---|
| `geraete-test.html` | Seite: Aussehen des Spiels, Hintergrund mit Parallax, Ablauf, Anzeige, Speichern |
| `geraete-tests.js` | die Suite: Liste der Test-Bausteine, `SUITE_VERSION` |
| `geraete-test-qr.html` | zeigt am Laptop den QR-Code, den das Handy scannt |
| `vendor/jsQR.js` | QR-Bibliothek, lokal (kein CDN) |
| `kompass-test.html` | leitet auf `geraete-test.html` weiter |
| `supabase/migrations/20260930120000_geraetetest.sql` | Nachtrag 23: Tabelle und zwei RPCs |
| `tools/testlaeufe.py` | holt Läufe nach `testlaeufe/`, baut `UEBERSICHT.md` |
| `tools/pruefstand/geraetetest.py` | Durchlauf am Laptop mit gespielten Sensoren |

`testlaeufe/` steht in `.gitignore`: der Workflow veröffentlicht das ganze Repo
auf GitHub Pages, die Läufe enthalten Koordinaten.

## Test-Baustein

```js
{ id: "standort", titel: "Standort", bezug: "Einchecken an der Station",
  block: "auto" | "hand" | "neu",
  hand: "Anweisung",            // nur bei Schritten, die eine Hand brauchen
  frage: "Hast du ...?",        // nur bei Ja/Nein-Rückfragen
  lauf: async (ctx) => ({ art: "ok" | "warn" | "err", wert: "±12 m", mess: { ... } }) }
```

- `art`: ok = geht, warn = eingeschränkt, err = geht nicht; dazu `skip`
  (übersprungen), das die Seite setzt. Stürzt ein Baustein ab oder läuft in die
  Zeitgrenze, wird daraus `err` mit der Meldung in `mess`.
- `wert`: kurze Anzeige rechts in der Zeile. `mess`: Messwerte, aufklappbar und gespeichert.
- `ctx` gibt den Bausteinen `rpc()`, die Konfiguration, einen gemeinsamen
  Sensor-Zugang (Ausrichtungs-Ereignisse) und `warte(ms)`.
- Jeder Baustein hat eine Zeitgrenze (Standard 25 s), danach `err` mit „keine Antwort“.
- Neuer Spielinhalt: einen Baustein anhängen, `SUITE_VERSION` hochzählen.

## Umfang Suite 1

**auto** (nach dem einen Tipp, der zuerst die iOS-Erlaubnis für Bewegung holt):
umgebung, speicher, server, uhr, standort, kompass, neigung, wachhalten, karte,
schrift, teilen.

**hand**: kompass-drehen (36 Zehn-Grad-Fächer, ab 30 ok), bildschirm-aus-an
(Zeit bis zum nächsten Standort, Wake Lock neu geholt), app-wechsel
(`visibilitychange`, Seite überlebt).

**neu**: kamera (Foto über `<input capture>`, verkleinern auf 1600 px,
Wegwerf-Upload derselben Größe an `device_test_echo`), qr (BarcodeDetector,
sonst jsQR über `getUserMedia`), ton (Web Audio, Rückfrage), vibration
(`navigator.vibrate`, Rückfrage), benachrichtigung (API vorhanden, Erlaubnis,
Hinweis auf iOS-Einschränkung), live (WebSocket zu Supabase Realtime,
Herzschlag), offline (Service Worker und Cache API vorhanden, Cache schreibt und
liest; es wird kein Service Worker registriert).

Schwellen: Standort ok bis ±25 m, warn bis ±100 m. Kompass ok bis ±25°
(`KOMPASS_GRENZE` des Spiels). Uhr ok bis 5 s, warn bis 60 s. Server ok bis
800 ms Median, warn bis 3 s.

## Speichern

Tabelle `device_test_runs`: `run_key text primary key`, `created_at`,
`updated_at`, `suite_version int`, `label text`, `payload jsonb`. RLS an, keine
Rechte für anon; Zugriff nur über:

- `device_test_save(p_key text, p_payload jsonb)`: legt an oder ersetzt den Lauf
  mit diesem Schlüssel. Lehnt ab über 64 KB, bei Schlüsseln außerhalb
  `[A-Z0-9]{12}` und wenn die Tabelle schon 2000 Läufe hat. Gibt `{ ok, serverTime }`.
- `device_test_echo(p_data text)`: nimmt bis 1 MB, wirft es weg, gibt die Länge
  zurück. Für die Upload-Messung.

Der Schlüssel entsteht auf dem Handy (12 Zeichen Zufall), angezeigt werden die
ersten vier. Wer den Schlüssel nicht kennt, kann einen Lauf nicht überschreiben;
lesen kann über die Seite niemand. Gespeichert wird nach dem auto-Block und
nach jedem weiteren Schritt. Scheitert es, liegt der Lauf in `localStorage`
(`sj.geraetetest`), die Seite zeigt „Erneut senden“.

Das `label` setzt die Seite selbst aus Betriebssystem, Browser und Bildschirmgröße; ein Namensfeld gibt es nicht (Entscheidung 30.09.2026).

Payload: `{ suite, label, begonnen, beendet, ua, bilanz: {ok,warn,err,skip}, tests: { <id>: {art, wert, mess, dauerMs} } }`.

## Abholen

`python tools/testlaeufe.py` liest über die Management-API (Token wie
`tools/sql.py`, read-only) alle Läufe, schreibt
`testlaeufe/<JJJJ-MM-TT_HHMM>_<label>_<key4>.json` und `testlaeufe/UEBERSICHT.md`
(Matrix Test gegen Lauf, darunter je Test die Messwerte der auffälligen Läufe).

## Aussehen

Wie im Mockup. Farben, Schrift, Karten, Knöpfe aus `index.html`. Hintergrund
folgt `public_state().background`, ohne Verbindung „klassisch“. Neigungs-Parallax
wie `neigungStart()` im Spiel. Keine em- oder en-dashes in Oberflächentexten.

## Prüfen

`tools/pruefstand/geraetetest.py` öffnet die Seite mit Playwright, spielt
Standort und Ausrichtung ein, fängt die RPCs ab und prüft: alle auto-Bausteine
liefern ein Ergebnis, der gespeicherte Payload hat die erwartete Form. Im
Vordergrund mit Timeout. Echte Geräte: erster Lauf durch Friedrich.

## Nicht enthalten

Anzeige der Läufe im Admin-Bereich, Bezug zur Anmeldung, Foto-Speicher,
registrierter Service Worker.

## Nachtrag 30.09.2026, Suite 4

QR-Code und Ton sind entfallen (Entscheidung Friedrich), damit auch
`geraete-test-qr.html`, `geraete-test-qr.svg` und `vendor/jsQR.js`. Die Suite hat
19 Bausteine. Seit Suite 3 nennt der Umgebungs-Test die Geräteart.

## Nachtrag 30.09.2026, Suite 5 bis 7

Suite 5: ungefährer Standort (über 1000 m) wird als „nur ungefähr“ gemeldet, mit Anleitung.
Suite 6: Schritt „Wach halten, mit Tipp“ (braucht die Bildschirmsperre einen Fingertipp?).
Suite 7: Schritt „Kompass nach Pause“ (wandert die Richtung nach einem App-Wechsel bei ruhigem Handy nach?).
Die Seite hat seit der UI-Durchsicht einen geführten Ablauf: immer nur ein Schritt offen. Damit 21 Bausteine.
