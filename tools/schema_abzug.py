#!/usr/bin/env python3
"""
Schema-Abzug: der heutige Stand der Datenbank (Schema public) als Dateien.

    python tools/schema_abzug.py             schreibt supabase/schema/
    python tools/schema_abzug.py --pruefen   vergleicht Live-Datenbank mit supabase/schema/

Gelesen wird ausschließlich über tools/sql.py im Modus read_only, und nur aus den
Systemkatalogen (pg_proc, pg_class, pg_attribute, pg_constraint, pg_index,
pg_policies, pg_trigger, pg_views). Tabelleninhalte werden nie gelesen.

Die Ausgabe ist deterministisch: sortiert, LF, UTF-8, ohne Zeitstempel. Ein
unveränderter Stand erzeugt keinen Git-Diff.

--pruefen beendet sich mit Exit 1, wenn supabase/schema/ vom Live-Stand abweicht.
Zusätzlich meldet es als Warnung (ohne Einfluss auf den Exit-Code), wo
supabase/migrations/ und Live-Datenbank nicht zusammenpassen: Funktionen, die nur
auf einer Seite vorkommen, und Funktionen, deren Körper in der letzten Migration
anders lautet als live.
"""
import argparse
import difflib
import pathlib
import re
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import sql as sqlmod  # noqa: E402

REPO = pathlib.Path(__file__).resolve().parent.parent
ZIEL = REPO / "supabase" / "schema"
MIGRATIONEN = REPO / "supabase" / "migrations"
UNTERORDNER = ("funktionen", "tabellen", "sichten")
KOPF = "-- Erzeugt von tools/schema_abzug.py aus der Live-Datenbank. Nicht von Hand ändern.\n"
ROLLEN = ("public", "anon", "authenticated")

NICHT_AUS_EXTENSION = (
    "not exists (select 1 from pg_depend d where d.objid = {oid} and d.deptype = 'e')"
)


def abfrage(q: str) -> list:
    antwort = sqlmod.ausfuehren(q, read_only=True)
    return antwort or []


# ---------------------------------------------------------------- Katalog lesen

def lese_funktionen() -> list:
    return abfrage(f"""
        select p.proname::text as name,
               pg_get_function_identity_arguments(p.oid) as args,
               pg_get_functiondef(p.oid) as def,
               p.prorettype::regtype::text as ret,
               p.prosrc as src,
               p.pronargs::int as nargs,
               has_function_privilege('anon', p.oid, 'execute') as anon,
               has_function_privilege('authenticated', p.oid, 'execute') as auth,
               coalesce((select array_agg(case when a.grantee = 0 then 'public' else a.grantee::regrole::text end)
                           from aclexplode(p.proacl) a where a.privilege_type = 'EXECUTE'),
                        case when p.proacl is null then array['public'] else array[]::text[] end) as grants
          from pg_proc p
         where p.pronamespace = 'public'::regnamespace
           and p.prokind in ('f', 'p', 'w')
           and {NICHT_AUS_EXTENSION.format(oid='p.oid')}
    """)


def lese_relationen(arten: str) -> list:
    return abfrage(f"""
        select c.oid::int as oid, c.relname::text as name, c.relkind::text as kind,
               c.relrowsecurity as rls, c.relforcerowsecurity as frls,
               coalesce(c.reloptions, array[]::text[]) as opts,
               coalesce((select array_agg(x.grantee::regrole::text || ':' || x.privilege_type)
                           from aclexplode(c.relacl) x
                          where x.grantee in ('anon'::regrole, 'authenticated'::regrole)),
                        array[]::text[]) as acl
          from pg_class c
         where c.relnamespace = 'public'::regnamespace
           and c.relkind in ({arten})
           and {NICHT_AUS_EXTENSION.format(oid='c.oid')}
    """)


def lese_spalten() -> list:
    return abfrage("""
        select a.attrelid::int as oid, a.attnum::int as nr, a.attname::text as name,
               format_type(a.atttypid, a.atttypmod) as typ, a.attnotnull as nn,
               pg_get_expr(d.adbin, d.adrelid) as dflt,
               a.attgenerated::text as gen, a.attidentity::text as ident
          from pg_attribute a
          join pg_class c on c.oid = a.attrelid
          left join pg_attrdef d on d.adrelid = a.attrelid and d.adnum = a.attnum
         where c.relnamespace = 'public'::regnamespace and c.relkind in ('r', 'p')
           and a.attnum > 0 and not a.attisdropped
    """)


def lese_constraints() -> list:
    return abfrage("""
        select conrelid::int as oid, conname::text as name, pg_get_constraintdef(oid) as def
          from pg_constraint
         where connamespace = 'public'::regnamespace and conrelid <> 0
    """)


def lese_indizes() -> list:
    return abfrage("""
        select i.indrelid::int as oid, ic.relname::text as name, pg_get_indexdef(i.indexrelid) as def
          from pg_index i join pg_class ic on ic.oid = i.indexrelid
         where ic.relnamespace = 'public'::regnamespace
           and not exists (select 1 from pg_constraint k where k.conindid = i.indexrelid)
    """)


def lese_policies() -> list:
    return abfrage("""
        select tablename::text as tabelle, policyname::text as name, permissive::text as permissive,
               roles::text[] as roles, cmd::text as cmd, qual, with_check
          from pg_policies where schemaname = 'public'
    """)


def lese_trigger() -> list:
    return abfrage("""
        select tgrelid::int as oid, tgname::text as name, pg_get_triggerdef(oid) as def
          from pg_trigger
         where not tgisinternal and tgrelid in (select oid from pg_class where relnamespace = 'public'::regnamespace)
    """)


def lese_sichten() -> dict:
    zeilen = abfrage("select viewname::text as name, definition from pg_views where schemaname = 'public'")
    return {z["name"]: z["definition"] for z in zeilen}


# ------------------------------------------------------------------- Rendern

def lf(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def bez(name: str) -> str:
    """Bezeichner, bei Bedarf in Anführungszeichen."""
    return name if re.fullmatch(r"[a-z_][a-z0-9_]*", name) else '"' + name.replace('"', '""') + '"'


def rechte_funktion(f: dict) -> list:
    sig = f"public.{bez(f['name'])}({f['args']})"
    grants = [r for r in ROLLEN if r in f["grants"]]
    zeilen = [f"revoke all on function {sig} from public, anon, authenticated;"]
    if grants:
        zeilen.append(f"grant execute on function {sig} to {', '.join(grants)};")
    return zeilen


def rechte_text(f: dict) -> str:
    ja = lambda b: "ja" if b else "nein"  # noqa: E731
    return f"-- Ausführen: public={ja('public' in f['grants'])}, anon={ja(f['anon'])}, authenticated={ja(f['auth'])}"


def funktion_sql(fs: list) -> str:
    teile = [KOPF]
    for f in sorted(fs, key=lambda x: x["args"]):
        teile.append(rechte_text(f) + "\n" + lf(f["def"]).rstrip().rstrip(";") + ";\n" + "\n".join(rechte_funktion(f)) + "\n")
    return "\n".join(teile)


def rechte_relation(r: dict, art: str) -> list:
    privs = {"anon": [], "authenticated": []}
    for eintrag in r["acl"]:
        rolle, recht = eintrag.split(":", 1)
        privs[rolle].append(recht)
    zeilen = [f"revoke all on table public.{bez(r['name'])} from anon, authenticated;"]
    for rolle in ("anon", "authenticated"):
        if privs[rolle]:
            liste = ", ".join(sorted(p.lower() for p in privs[rolle]))
            zeilen.append(f"grant {liste} on table public.{bez(r['name'])} to {rolle};")
    return zeilen


def tabelle_sql(r: dict, spalten, constraints, indizes, policies, triggers) -> str:
    n = f"public.{bez(r['name'])}"
    zeilen = []
    for s in sorted(spalten, key=lambda x: x["nr"]):
        z = f"  {bez(s['name'])} {s['typ']}"
        if s["ident"] == "a":
            z += " generated always as identity"
        elif s["ident"] == "d":
            z += " generated by default as identity"
        if s["gen"] == "s":
            z += f" generated always as ({s['dflt']}) stored"
        elif s["dflt"] is not None:
            z += f" default {s['dflt']}"
        if s["nn"]:
            z += " not null"
        zeilen.append(z)
    for c in sorted(constraints, key=lambda x: x["name"]):
        zeilen.append(f"  constraint {bez(c['name'])} {c['def']}")
    teile = [KOPF, f"create table {n} (\n" + ",\n".join(zeilen) + "\n);\n"]
    for i in sorted(indizes, key=lambda x: x["name"]):
        teile.append(i["def"] + ";\n")
    teile.append(f"alter table {n} {'enable' if r['rls'] else 'disable'} row level security;\n")
    if r["frls"]:
        teile.append(f"alter table {n} force row level security;\n")
    for p in sorted(policies, key=lambda x: x["name"]):
        rollen = ", ".join(p["roles"])
        s = f"create policy {bez(p['name'])} on {n} as {p['permissive'].lower()} for {p['cmd'].lower()} to {rollen}"
        if p["qual"]:
            s += f" using ({p['qual']})"
        if p["with_check"]:
            s += f" with check ({p['with_check']})"
        teile.append(s + ";\n")
    for t in sorted(triggers, key=lambda x: x["name"]):
        teile.append(t["def"] + ";\n")
    teile.append("\n".join(rechte_relation(r, "table")) + "\n")
    return lf("\n".join(teile))


def sicht_sql(r: dict, definition: str) -> str:
    n = f"public.{bez(r['name'])}"
    opts = f" with ({', '.join(sorted(r['opts']))})" if r["opts"] else ""
    koerper = lf(definition).strip().rstrip(";").rstrip()
    return lf(KOPF + f"\ncreate or replace view {n}{opts} as\n{koerper};\n" + "\n".join(rechte_relation(r, "view")) + "\n")


# ------------------------------------------------------------------ Rechte-Tabelle

def zugang(f: dict) -> str:
    if f["ret"] == "trigger":
        return "Trigger"
    if not (f["anon"] or f["auth"] or "public" in f["grants"]):
        return "intern"
    if not f["anon"]:
        return "nur authenticated"
    if re.search(r"\brequire_admin\s*\(", f["src"]):
        return "nur PIN"
    return "offen"


def readme_text(funktionen: list, tabellen: list, sichten: list) -> str:
    zeilen = []
    for f in sorted(funktionen, key=lambda x: (x["name"], x["args"])):
        a = lambda b: "ja" if b else "nein"  # noqa: E731
        zeilen.append(
            f"| `{f['name']}({f['args']})` | {zugang(f)} | {a('public' in f['grants'])} | {a(f['anon'])} | {a(f['auth'])} |"
        )
    zaehl = {}
    for f in funktionen:
        zaehl[zugang(f)] = zaehl.get(zugang(f), 0) + 1
    summe = ", ".join(f"{k} {v}" for k, v in sorted(zaehl.items()))
    return lf(f"""# Schema-Abzug

Der heutige Stand der Datenbank (Schema `public`), erzeugt aus der Live-Datenbank.
**Wird erzeugt, nicht von Hand geändert.** Die Quelle der Wahrheit für die Spiellogik
sind weiter die Migrationen in `../migrations/`; dieser Ordner zeigt, was davon heute
tatsächlich gilt: je Funktion eine Datei mit der letzten Fassung und ihren Rechten.

- `funktionen/<name>.sql`: Funktionsdefinition (Überladungen hintereinander) und
  `revoke`/`grant` für `public`, `anon`, `authenticated`
- `tabellen/<name>.sql`: Spalten, Constraints, Indizes, RLS, Policies, Trigger, Tabellenrechte
- `sichten/<name>.sql`: Views

Nicht enthalten: Supabase-eigene Schemas, Funktionen und Tabellen aus Extensions,
Rechte für `postgres` und `service_role`, Sequenzen (stehen als `nextval(...)` im Default),
Tabelleninhalte.

## Neu erzeugen und prüfen

```
python tools/schema_abzug.py             # schreibt diesen Ordner neu
python tools/schema_abzug.py --pruefen   # Live gegen diesen Ordner, Exit 1 bei Abweichung
```

Beides liest nur (`tools/sql.py` im Modus read-only, nur Systemkataloge). Nach jeder
eingespielten Migration neu erzeugen und mitcommitten; `--pruefen` vor jedem Einspielen.
`--pruefen` meldet außerdem als Warnung, wo Migrationen und Live-Datenbank nicht
zusammenpassen.

## Rechte

Stand: {len(funktionen)} Funktionen ({summe}), {len(tabellen)} Tabellen, {len(sichten)} Sichten.

- **offen**: `anon` darf aufrufen, die Funktion ruft `require_admin` nicht selbst auf
  (öffentlicher Zustand, Team-Funktionen mit Team-Code oder Token)
- **nur PIN**: `anon` darf aufrufen, der Körper ruft `require_admin` direkt auf
- **intern**: weder `public`, `anon` noch `authenticated` dürfen aufrufen
- **Trigger**: Trigger-Funktion

"nur PIN" ist aus dem Funktionstext abgeleitet (direkter Aufruf von `require_admin`),
nicht aus einer Zusicherung der Datenbank. Eine Funktion, die die PIN über eine andere
Hilfsfunktion prüft, steht als "offen".

| Funktion | Zugang | public | anon | authenticated |
|---|---|---|---|---|
""" + "\n".join(zeilen) + "\n")


# ------------------------------------------------------------------- Erzeugen

def erzeuge(ziel: pathlib.Path) -> dict:
    funktionen = lese_funktionen()
    tab = lese_relationen("'r', 'p'")
    sichten = lese_relationen("'v', 'm'")
    sichten_def = lese_sichten()
    spalten = lese_spalten()
    constraints = lese_constraints()
    indizes = lese_indizes()
    policies = lese_policies()
    trigger = lese_trigger()

    dateien = {}
    nach_name = {}
    for f in funktionen:
        nach_name.setdefault(f["name"], []).append(f)
    for name, fs in nach_name.items():
        dateien[f"funktionen/{name}.sql"] = funktion_sql(fs)

    def je(liste, oid):
        return [x for x in liste if x["oid"] == oid]

    for r in tab:
        dateien[f"tabellen/{r['name']}.sql"] = tabelle_sql(
            r, je(spalten, r["oid"]), je(constraints, r["oid"]), je(indizes, r["oid"]),
            [p for p in policies if p["tabelle"] == r["name"]], je(trigger, r["oid"]),
        )
    for r in sichten:
        dateien[f"sichten/{r['name']}.sql"] = sicht_sql(r, sichten_def[r["name"]])
    dateien["README.md"] = readme_text(funktionen, tab, sichten)

    for unter in UNTERORDNER:
        (ziel / unter).mkdir(parents=True, exist_ok=True)
    for pfad, inhalt in dateien.items():
        (ziel / pfad).write_bytes(inhalt.encode("utf-8"))
    return {"funktionen": funktionen, "n_funktionen": len(funktionen), "n_dateien_f": len(nach_name),
            "n_tabellen": len(tab), "n_sichten": len(sichten), "dateien": dateien}


def schreibe_abzug() -> None:
    # Veraltete Dateien (Funktion, Tabelle oder Sicht gibt es live nicht mehr) entfernen
    with tempfile.TemporaryDirectory() as tmp:
        info = erzeuge(pathlib.Path(tmp))
    for unter in UNTERORDNER:
        ordner = ZIEL / unter
        ordner.mkdir(parents=True, exist_ok=True)
        for alt in ordner.glob("*.sql"):
            if f"{unter}/{alt.name}" not in info["dateien"]:
                alt.unlink()
    for pfad, inhalt in info["dateien"].items():
        (ZIEL / pfad).write_bytes(inhalt.encode("utf-8"))
    print(f"{info['n_funktionen']} Funktionen ({info['n_dateien_f']} Dateien), "
          f"{info['n_tabellen']} Tabellen, {info['n_sichten']} Sichten nach {ZIEL.relative_to(REPO)}")


# --------------------------------------------------------------------- Prüfen

def lies_baum(wurzel: pathlib.Path) -> dict:
    out = {}
    if wurzel.exists():
        for p in sorted(wurzel.rglob("*")):
            if p.is_file():
                out[p.relative_to(wurzel).as_posix()] = lf(p.read_bytes().decode("utf-8"))
    return out


def vergleiche_baeume(soll: dict, ist: dict) -> list:
    """soll = Live-Stand, ist = Ordner im Repo."""
    meldungen = []
    for pfad in sorted(set(soll) | set(ist)):
        if pfad not in ist:
            meldungen.append(f"fehlt im Repo (live vorhanden): {pfad}")
        elif pfad not in soll:
            meldungen.append(f"nur im Repo (live nicht mehr vorhanden): {pfad}")
        elif soll[pfad] != ist[pfad]:
            diff = list(difflib.unified_diff(ist[pfad].splitlines(), soll[pfad].splitlines(),
                                             "Repo", "live", lineterm="", n=0))
            kurz = "\n".join("    " + z for z in diff[:12])
            mehr = f"\n    ... ({len(diff) - 12} weitere Zeilen)" if len(diff) > 12 else ""
            meldungen.append(f"weicht ab: {pfad}\n{kurz}{mehr}")
    return meldungen


# --- Migrationen lesen

RE_FUNC = re.compile(r"create\s+(?:or\s+replace\s+)?function\s+(?:public\.)?\"?([a-z_][a-z0-9_]*)\"?\s*\(", re.I)
RE_DROP = re.compile(r"drop\s+function\s+(?:if\s+exists\s+)?([^;]*);", re.I)
RE_RENAME = re.compile(r"alter\s+table\s+(?:public\.)?\"?([a-z_][a-z0-9_]*)\"?\s+rename\s+to\s+\"?([a-z_][a-z0-9_]*)\"?", re.I)
RE_TAB = re.compile(r"create\s+table\s+(?:if\s+not\s+exists\s+)?(?:public\.)?\"?([a-z_][a-z0-9_]*)\"?", re.I)


def ohne_kommentar_zeilen(text: str) -> str:
    return re.sub(r"--[^\n]*", "", text)


def argzahl(args: str) -> int:
    if not args.strip():
        return 0
    tiefe, n = 0, 1
    for ch in args:
        if ch == "(":
            tiefe += 1
        elif ch == ")":
            tiefe -= 1
        elif ch == "," and tiefe == 0:
            n += 1
    return n


def migrations_funktionen() -> tuple:
    """-> (definitionen {(name, nargs): (datei, kopf, koerper)}, namen {name: erste_datei}, drops {name: letzte_datei})"""
    defs, namen, drops, tabellen = {}, {}, {}, {}
    for datei in sorted(MIGRATIONEN.glob("*.sql")):
        text = datei.read_text(encoding="utf-8")
        for m in RE_TAB.finditer(ohne_kommentar_zeilen(text)):
            tabellen.setdefault(m.group(1).lower(), datei.name)
        for m in RE_RENAME.finditer(ohne_kommentar_zeilen(text)):
            alt, neu = m.group(1).lower(), m.group(2).lower()
            if alt in tabellen:
                tabellen[neu] = tabellen.pop(alt)
        for m in RE_DROP.finditer(ohne_kommentar_zeilen(text)):
            for teil in re.finditer(r"(?:public\.)?\"?([a-z_][a-z0-9_]*)\"?\s*\(", m.group(1), re.I):
                drops[teil.group(1).lower()] = datei.name
        for m in RE_FUNC.finditer(text):
            name = m.group(1).lower()
            # Argumentliste per Klammerzählung
            tiefe, i = 1, m.end()
            while i < len(text) and tiefe:
                tiefe += (text[i] == "(") - (text[i] == ")")
                i += 1
            args = text[m.end():i - 1]
            rest = text[i:]
            b = re.search(r"\bas\s+(\$[a-z_]*\$)(.*?)\1", rest, re.I | re.S)
            if not b:
                continue
            kopf = rest[:b.start()].lower()
            defs[(name, argzahl(ohne_kommentar_zeilen(args)))] = (datei.name, kopf, b.group(2))
            namen.setdefault(name, datei.name)
    return defs, namen, drops, tabellen


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", lf(s)).strip()


def warnungen_migrationen(funktionen: list, live_tabellen: list) -> list:
    defs, namen, drops, mig_tab = migrations_funktionen()
    live = {f["name"] for f in funktionen}
    w = []
    for n in sorted(set(namen) - live):
        spaet = f" (spätestens in {drops[n]} per drop function entfernt)" if n in drops else ""
        w.append(f"in Migration {namen[n]} definiert, live nicht vorhanden: {n}{spaet}")
    for n in sorted(live - set(namen)):
        w.append(f"live vorhanden, in keiner Migration definiert: {n}")
    for t in sorted(set(mig_tab) - set(live_tabellen)):
        w.append(f"Tabelle in Migration {mig_tab[t]} angelegt, live nicht vorhanden: {t}")
    for t in sorted(set(live_tabellen) - set(mig_tab)):
        w.append(f"Tabelle live vorhanden, in keiner Migration angelegt: {t}")
    for f in sorted(funktionen, key=lambda x: (x["name"], x["args"])):
        d = defs.get((f["name"], f["nargs"]))
        if not d:
            continue
        datei, kopf, koerper = d
        if norm(koerper) != norm(f["src"]):
            w.append(f"Körper weicht ab: {f['name']}({f['args']}) live gegen letzte Migration {datei}")
        sd_mig = "security definer" in kopf
        sd_live = "SECURITY DEFINER" in lf(f["def"]).split("AS $")[0]
        if sd_mig != sd_live:
            w.append(f"security definer weicht ab: {f['name']} (Migration {datei}: {sd_mig}, live: {sd_live})")
    return w


def pruefen() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_pfad = pathlib.Path(tmp)
        info = erzeuge(tmp_pfad)
        soll = lies_baum(tmp_pfad)
    ist = lies_baum(ZIEL)
    abw = vergleiche_baeume(soll, ist)
    tabellen = [p.split("/")[1][:-4] for p in soll if p.startswith("tabellen/")]
    warn = warnungen_migrationen(info["funktionen"], tabellen)
    for z in warn:
        print("WARNUNG " + z)
    if abw:
        print(f"\n{len(abw)} Abweichung(en) zwischen Live-Datenbank und supabase/schema/:")
        for z in abw:
            print("  " + z)
        print("\nNeu erzeugen mit: python tools/schema_abzug.py")
        return 1
    print(f"Sauber: supabase/schema/ stimmt mit der Live-Datenbank überein "
          f"({info['n_funktionen']} Funktionen, {info['n_tabellen']} Tabellen, {info['n_sichten']} Sichten).")
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description="Schema-Abzug der Live-Datenbank nach supabase/schema/.")
    ap.add_argument("--pruefen", action="store_true", help="nur vergleichen, nichts schreiben (Exit 1 bei Abweichung)")
    a = ap.parse_args()
    if a.pruefen:
        sys.exit(pruefen())
    schreibe_abzug()


if __name__ == "__main__":
    main()
