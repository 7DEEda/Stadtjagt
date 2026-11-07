"""Sauberes Ende für Prüfskripte, die eine Seite mit Leaflet-Karte geöffnet haben.

Chrome 155 hängt auf dem Arbeitsrechner beim browser.close() nach einer Leaflet-Seite. Statt bis zum Timeout zu
warten: Ergebnis drucken, die eigenen Chrome-Prozesse beenden und das Skript enden.

    import abschluss
    vorher = abschluss.merken()          # vor pw.chromium.launch(...)
    ...
    abschluss.ende(fehler, vorher)       # druckt nichts, beendet mit 0 oder 1

Eigen heißt: chrome.exe, der seit merken() dazugekommen ist UND von diesem Python-Prozess abstammt (Python startet den
Playwright-Treiber, der startet Chrome). Bis zur Bugjagd 07.11.2026 (Fund 11) reichte "neu und 'playwright' in der
Kommandozeile"; das traf auch den Chrome eines anderen Prüfskripts, das parallel lief (anderer Worktree, anderer Port).
"""
import json
import os
import subprocess
import sys


def _prozesse():
    """{pid: (eltern_pid, name)} aller Prozesse; leer außerhalb von Windows (im Container endet Chrome mit ihm)."""
    if os.name != "nt":
        return {}
    try:
        aus = subprocess.run(["powershell", "-NoProfile", "-Command",
                              "Get-CimInstance Win32_Process | Select-Object ProcessId, ParentProcessId, Name | "
                              "ConvertTo-Json -Compress"],
                             capture_output=True, text=True, timeout=30).stdout
        return {int(p["ProcessId"]): (int(p["ParentProcessId"] or 0), str(p["Name"] or "").lower())
                for p in json.loads(aus or "[]")}
    except Exception:
        return {}


def _eigene_chrome():
    """PIDs aller chrome.exe, die von diesem Prozess abstammen (über beliebig viele Ebenen)."""
    alle = _prozesse()
    kinder = {}
    for pid, (eltern, _) in alle.items():
        kinder.setdefault(eltern, []).append(pid)
    eigene, offen = set(), [os.getpid()]
    while offen:
        for k in kinder.get(offen.pop(), []):
            if k not in eigene and k != os.getpid():
                eigene.add(k)
                offen.append(k)
    return {pid for pid in eigene if alle[pid][1] == "chrome.exe"}


def merken():
    return _eigene_chrome()


def ende(fehler, vorher):
    sys.stdout.flush()
    for pid in _eigene_chrome() - set(vorher):
        subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True)
    os._exit(1 if fehler else 0)
