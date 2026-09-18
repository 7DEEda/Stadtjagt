# Stadtjagd

Digital geführtes Geocaching für die TSE-Teamfahrt: Anmeldung per Link, zufällige Teamauslosung,
fünf Stationen mit GPS-Check-in und Rätsel, sechsstelliger Koffercode, Live-Karte für die Spielleitung.

Vollständiger Kontext, Architektur und offene Punkte: **[HANDOFF.md](HANDOFF.md)**

## Schnellstart

1. Supabase-Projekt anlegen (Region Frankfurt).
2. Migration einspielen:
   ```bash
   npx supabase@latest login
   npx supabase@latest link --project-ref <ref>
   npx supabase@latest db push
   ```
   Alternativ den Inhalt von `supabase/migrations/20260918120000_init.sql` im SQL-Editor ausführen.
3. In `config.js` die Project URL und den **anon public key** eintragen
   (Supabase → Project Settings → API). Der `service_role` key gehört dort nicht hinein.
4. Repo nach GitHub pushen, unter Settings → Pages als Quelle „GitHub Actions“ wählen.

## Ansichten

| Pfad | Für wen |
|---|---|
| `/#/public` | alle Teilnehmenden: anmelden, Team nachschlagen |
| `/#/team` | Handy der Teamleitung, Login per Team-Code |
| `/#/admin` | Spielleitung, PIN (Standard 2026) |

PIN ändern: `update game_state set admin_pin = 'neuePIN';`

## Aufbau

```
index.html                     komplette App, kein Build nötig
config.js                      Supabase-URL und anon key
supabase/migrations/*.sql      Schema, Rechte und die gesamte Spiellogik
.github/workflows/pages.yml    Deployment auf GitHub Pages
```

## Lokal testen

```bash
npx serve .
```

GPS und Kompass funktionieren nur über HTTPS oder localhost, nicht per Doppelklick auf die Datei.
