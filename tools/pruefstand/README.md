# UI-Prüfstand

Fotografiert die echte `index.html` in jedem Spielzustand, ohne Datenbank.
`shoot.py` baut `app.html` (index.html plus `<script src="mock.js">` davor),
startet einen Server auf Port 8791, fotografiert mit Playwright und beendet ihn.
`mock.js` beantwortet alle RPCs aus Beispieldaten und blockiert supabase.co.

    python shoot.py                     alle Szenarien, 5 bis 8 Minuten
    python shoot.py teamsuche admin-teams   nur diese
    python shoot.py --build             nur app.html bauen

Braucht Python mit Playwright (`pip install playwright`, Kanal chrome).
Ergebnis in `shots/`, Übersicht in `bericht.json`. Im Vordergrund mit
Timeout aufrufen, etwa `timeout 580 python shoot.py`.

Ein Szenario ansehen: `python -m http.server 8791` in diesem Ordner, dann
`http://127.0.0.1:8791/app.html?szenario=<name>`. Die Namen stehen in
`mock.js` im Objekt `SZ`. Entstanden bei der UI-Durchsicht am 19.09.2026.

## Prüfskripte (ohne Datenbank, gegen `mock.js`)

Jedes endet mit `OK` oder listet `FEHLT`. Immer im Vordergrund mit Timeout,
etwa `timeout 300 python tools/pruefstand/waechter.py`.

| Skript | prüft |
|---|---|
| `selfie.py` | Gruppenselfie (Nachtrag 25) |
| `name.py` | verschlüsselter Stationsname (Nachtrag 26) |
| `geraetetest.py` | Geräte-Test |
| `kritik.py` | Befunde der UI-Kritik (Nachtrag 27) |
| `ziffer.py` | Ziffer im laufenden Spiel ändern |
| `teststation.py` | Teststation und Startpunkt (Nachtrag 28 und 29) |
| `waechter.py` | Kompass-Wächter: Logik, Anzeige, Spielleitung, Freigaben (Nachtrag 30) |
| `bugjagd2.py` | Funde der Bugjagd vom 03.10.2026 |

## Probeläufe gegen die echte Datenbank

`*_db.py` spielt eine Migration in EINEM DO-Block ein, prüft und wirft am Ende
absichtlich einen Fehler: der Server nimmt alles zurück (`PROBELAUF_OK`). Erst
danach die Migration mit `python tools/sql.py <datei>` einspielen. Braucht den
Zugang aus `tools/sql.py`.

`name_db.py`, `selfie_db.py`, `teststation_db.py`, `startpunkt_db.py`,
`waechter_db.py`, `rechte_db.py` (Rechte aller internen Hilfsfunktionen),
`bugjagd2_db.py`. Mit `--ohne` zeigen `rechte_db.py` und `bugjagd2_db.py` den
Stand ohne Migration.
