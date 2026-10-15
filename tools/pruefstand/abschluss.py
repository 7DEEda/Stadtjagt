"""Sauberes Ende für Prüfskripte, die eine Seite mit Leaflet-Karte geöffnet haben.

Chrome 155 hängt auf dem Arbeitsrechner beim browser.close() nach einer Leaflet-Seite. Statt bis zum Timeout zu
warten: Ergebnis drucken, die Chrome-Prozesse beenden, die seit merken() dazugekommen sind, und das Skript enden.

    import abschluss
    vorher = abschluss.merken()          # vor pw.chromium.launch(...)
    ...
    abschluss.ende(fehler, vorher)       # druckt nichts, beendet mit 0 oder 1
"""
import os
import subprocess
import sys


def _pids():
    if os.name != "nt":
        return set()
    try:
        aus = subprocess.run(["powershell", "-NoProfile", "-Command",
                              "Get-CimInstance Win32_Process -Filter \"Name='chrome.exe'\" | "
                              "Where-Object { $_.CommandLine -match 'playwright' } | ForEach-Object { $_.ProcessId }"],
                             capture_output=True, text=True, timeout=30).stdout
        return {int(x) for x in aus.split() if x.strip().isdigit()}
    except Exception:
        return set()


def merken():
    return _pids()


def ende(fehler, vorher):
    sys.stdout.flush()
    neu = _pids() - set(vorher)
    for pid in neu:
        subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True)
    os._exit(1 if fehler else 0)
