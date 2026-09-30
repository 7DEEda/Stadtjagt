# Geräte-Test Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eine Testseite, die auf einem Handy mit einem Tipp alle fürs Spiel nötigen und angedachten Gerätefunktionen prüft, den Lauf in Supabase speichert und sich per Skript auf den PC holen lässt.

**Architecture:** Statische Seite `geraete-test.html` (Ablauf, Anzeige, Speichern) plus `geraete-tests.js` (Liste der Test-Bausteine). Schreiben über zwei `security definer`-RPCs in eine Tabelle ohne Rechte für anon. Abholen über die Management-API wie `tools/sql.py`.

**Tech Stack:** HTML/CSS/JS ohne Build, Supabase (Postgres, PostgREST, Realtime), Python 3 (Standardbibliothek, Playwright nur für den Prüfstand), jsQR lokal.

Spezifikation: `docs/superpowers/specs/2026-09-30-geraete-test-design.md`. Der Plan nennt Reihenfolge, Dateien und Prüfung; der Code steht in den Dateien selbst, nicht doppelt hier.

---

### Task 1: Datenbank (Nachtrag 23)
**Files:** Create `supabase/migrations/20260930120000_geraetetest.sql`
- [ ] Tabelle `device_test_runs`, RLS an, `revoke all` für anon und authenticated
- [ ] `device_test_save(p_key, p_payload)`: Schlüssel `^[A-Z0-9]{12}$`, höchstens 64 KB, höchstens 2000 Läufe, upsert
- [ ] `device_test_echo(p_data)`: höchstens 1 MB, gibt `bytes` und `serverTime`
- [ ] Einspielen erst nach Freigabe: `python tools/sql.py supabase/migrations/20260930120000_geraetetest.sql`
- [ ] Prüfen: `python tools/sql.py --read-only -c "select count(*) from device_test_runs"` liefert 0

### Task 2: Suite
**Files:** Create `geraete-tests.js`, `vendor/jsQR.js`
- [ ] `window.SJ_TESTS = { version: 1, tests: [...] }`, Bausteine laut Spezifikation (11 auto, 3 hand, 7 neu)
- [ ] Jeder Baustein liefert `{ art, wert, mess }`; Schwellen aus der Spezifikation

### Task 3: Seite
**Files:** Create `geraete-test.html`, `geraete-test-qr.html`, `geraete-test-qr.svg`; Modify `kompass-test.html` (Weiterleitung)
- [ ] Aussehen aus dem Mockup, Hintergrund nach `public_state().background`, Neigungs-Parallax
- [ ] Ein Tipp: Bewegungs-Erlaubnis, dann alle selbstlaufenden Bausteine nacheinander, je mit Zeitgrenze
- [ ] Hand-Schritte mit „Los“ und „Überspringen“, Rückfragen mit Ja und Nein
- [ ] Speichern nach dem auto-Block und nach jedem Schritt; bei Fehler Sicherung in `localStorage` und „Erneut senden“
- [ ] Keine em- oder en-dashes in Oberflächentexten

### Task 4: Abholen
**Files:** Create `tools/testlaeufe.py`; Modify `.gitignore` (`testlaeufe/`)
- [ ] Läufe read-only lesen, je Lauf eine JSON-Datei, `UEBERSICHT.md` als Matrix

### Task 5: Prüfstand
**Files:** Create `tools/pruefstand/geraetetest.py`
- [ ] Server auf Port 8792, Playwright mit gespieltem Standort und gespielten Ausrichtungs-Ereignissen, `device_test_save` und `device_test_echo` abgefangen
- [ ] Prüft: jeder selbstlaufende Baustein hat ein Ergebnis, Payload hat `suite`, `bilanz`, `tests`
- [ ] Aufruf im Vordergrund mit Timeout: `python tools/pruefstand/geraetetest.py`, erwartet „OK“ am Ende

### Task 6: Veröffentlichen (nach Freigabe)
- [ ] Migration einspielen, committen, pushen; Live-Seite abrufen und einen Lauf mit `tools/testlaeufe.py` abholen
- [ ] `HANDOFF.md` und `README.md` um den Geräte-Test ergänzen
