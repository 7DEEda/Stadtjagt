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
