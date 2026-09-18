"""Baut die Vergleichsseite mockups/hintergrund-varianten.html aus den drei SVG-Dateien."""
import gzip, os, sys

QUELLE = sys.argv[1]
ZIEL = sys.argv[2]

VARIANTEN = [
    ("a", "A", "Wanderkarte fein",
     "Der bisherige Stil, deutlich dichter: Höhenlinien aus einem Geländemodell mit Zählkurven, "
     "Bäche, die dem Gefälle folgen, Waldflächen, Kartengitter mit Randzahlen, Höhenpunkte, Nordpfeil und Maßstab."),
    ("b", "B", "Prag-Stadtplan",
     "Die echte Prager Innenstadt aus OpenStreetMap: Moldau mit Inseln, Straßen nach Rang, Parks, Bahn, "
     "Viertelnamen. Darauf eure Route mit den fünf Stationen, lagegetreu aus der Datenbank. "
     "Braucht den Hinweis „© OpenStreetMap-Mitwirkende“, er steht klein unten rechts."),
    ("c", "C", "Orientierungslauf-Karte",
     "Die Zeichensprache eines Orientierungslaufs: Freiflächen, Dickicht, Sumpf, braune Höhenlinien mit Formlinien, "
     "Felsen, drei Wegarten, Nordlinien. Darüber der Bahnaufdruck: Start, Posten 1 bis 5, Ziel ist der Koffer."),
]

CSS = r"""
:root{
  --paper:#F1F5EE; --card:#FFFFFF; --ink:#17302A; --muted:#5B6F68; --line:#D3DECF;
  --contour:#CFDBC8; --flag:#EE5F1B; --flag-ink:#FFFFFF; --water:#2F6E9E;
  --head:"Barlow Semi Condensed","Arial Narrow",system-ui,sans-serif;
  --body:"Barlow",system-ui,-apple-system,"Segoe UI",sans-serif;
  /* neu für die Varianten */
  --park:#DFEAD6; --baum:#C3D5B8; --strasse:#CBD7C4; --strasse-haupt:#B5C5AE;
  --ol-braun:#E0CCB3; --ol-gelb:#F3EDD6; --ol-gruen:#DCEAD3; --ol-dicht:#C9DEBD; --ol-schwarz:#A3AFA9;
  --desk:#DDE3DA;
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --paper:#0F1B18; --card:#16261F; --ink:#E4EEE8; --muted:#9BB1A9; --line:#2A3F38;
  --contour:#1C312B; --flag:#FF7A3A; --water:#6FA8D6;
  --park:#142A20; --baum:#1D3A2B; --strasse:#1F352E; --strasse-haupt:#29443A;
  --ol-braun:#332A21; --ol-gelb:#1E2419; --ol-gruen:#142A1E; --ol-dicht:#1A3524; --ol-schwarz:#3B4C45;
  --desk:#08110F;}}
:root[data-theme="dark"]{
  --paper:#0F1B18; --card:#16261F; --ink:#E4EEE8; --muted:#9BB1A9; --line:#2A3F38;
  --contour:#1C312B; --flag:#FF7A3A; --water:#6FA8D6;
  --park:#142A20; --baum:#1D3A2B; --strasse:#1F352E; --strasse-haupt:#29443A;
  --ol-braun:#332A21; --ol-gelb:#1E2419; --ol-gruen:#142A1E; --ol-dicht:#1A3524; --ol-schwarz:#3B4C45;
  --desk:#08110F;}
*{box-sizing:border-box}
html,body{margin:0}
body{background:var(--desk);color:var(--ink);font:16px/1.5 var(--body)}
h1,h2,h3{font-family:var(--head);margin:0;line-height:1.1}
.kopf{max-width:1240px;margin:0 auto;padding:24px 16px 4px}
.kopf h1{font-size:30px}
.kopf p{margin:.4em 0 0;color:var(--muted);max-width:760px}
.schalter{display:flex;flex-wrap:wrap;gap:8px;margin-top:14px;align-items:center}
.schalter button{border:1.5px solid var(--line);background:var(--card);color:var(--ink);border-radius:8px;
  padding:8px 14px;font:600 15px var(--body);cursor:pointer;min-height:42px}
.schalter button[aria-pressed="true"]{border-color:var(--flag);color:var(--flag)}
.reihe{max-width:1240px;margin:0 auto;padding:16px;display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:24px}
.karte h2{font-size:24px;display:flex;gap:10px;align-items:baseline}
.karte h2 b{color:var(--flag)}
.karte p{margin:.35em 0 0;font-size:15px;color:var(--muted);min-height:96px}
.groesse{font-size:13px;color:var(--muted);margin-top:4px;white-space:nowrap}
.handy{position:relative;width:100%;max-width:370px;aspect-ratio:390/844;margin-top:12px;border:9px solid #1a1a1a;
  border-radius:32px;overflow:hidden;background:var(--paper)}
.breit{position:relative;width:100%;aspect-ratio:16/9;margin-top:12px;border:6px solid #1a1a1a;border-radius:10px;overflow:hidden;background:var(--paper)}
.handy .topo,.breit .topo{position:absolute;inset:0;width:100%;height:100%}
.ui{position:absolute;inset:0;padding:18px 14px;display:flex;flex-direction:column;gap:12px;transition:opacity .16s cubic-bezier(.32,.72,.4,1)}
body.leer .ui{opacity:0}
.marke{display:flex;gap:10px;align-items:center}
.marke svg{width:30px;height:30px}
.marke h3{font-size:28px;font-weight:700}
.marke small{display:block;color:var(--muted);font:500 13px var(--body)}
.panel{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px}
.panel .m{color:var(--muted);font-size:13px}
.panel h4{font:700 22px var(--head);margin:2px 0 0}
.panel .h{font-size:16px;font-weight:500;margin-top:6px}
.kompass{display:flex;gap:14px;align-items:center;margin-top:10px}
.kompass svg{width:64px;height:64px}
.kompass .d{font:700 32px var(--head);line-height:1;white-space:nowrap}
.knopf{margin-top:10px;border-radius:10px;background:var(--flag);color:#fff;text-align:center;padding:11px;font:700 17px var(--head)}
.nav{margin-top:auto;text-align:center;font-size:13px;color:var(--muted)}
.nav span{text-decoration:underline}
.zwischen{max-width:1240px;margin:8px auto 0;padding:0 16px}
.zwischen h2{font-size:22px}
.zwischen p{margin:.3em 0 0;color:var(--muted);font-size:15px}

/* ---- Hintergrund: alle Linien bleiben auf jedem Bildschirm gleich fein ---- */
.topo *{vector-effect:non-scaling-stroke}
.topo text{vector-effect:none}
/* A */
.topo .c,.topo .c5{fill:none;stroke:var(--contour);stroke-width:1}
.topo .c5{stroke-width:1.9}
.topo .w{fill:none;stroke:var(--water);stroke-width:2.6;opacity:.4;stroke-linecap:round}
.topo .wl{fill:none;stroke:var(--water);stroke-width:1;opacity:.3}
.topo .t{fill:none;stroke:var(--flag);stroke-width:1.7;stroke-dasharray:8 6;stroke-linecap:round;opacity:.4}
.topo .t2{stroke-dasharray:3 5;opacity:.3}
.topo .p{fill:none;stroke:var(--contour);stroke-width:1.7;stroke-linejoin:round;stroke-linecap:round}
.topo .pf{fill:var(--contour)}
.topo .wald{fill:url(#a-wald)}
.topo .baum{fill:var(--baum)}
.topo .gitter{fill:none;stroke:var(--contour);stroke-width:.6}
.topo .gl,.topo .hz{font:600 8px var(--body);fill:var(--muted);opacity:.5}
.topo .hz{font-weight:500;opacity:.6}
.topo .nord path{fill:var(--muted);opacity:.45}
.topo .nord text{font:700 10px var(--head);fill:var(--muted);opacity:.55;text-anchor:middle}
.topo .mass path{fill:none;stroke:var(--muted);opacity:.45}
.topo .mass text{font:500 8px var(--body);fill:var(--muted);opacity:.55}
/* B */
.topo .park{fill:var(--park)}
.topo .wasser{fill:var(--water);fill-opacity:.16;stroke:var(--water);stroke-opacity:.35;stroke-width:.7}
.topo .bach{fill:none;stroke:var(--water);stroke-width:.8;opacity:.35}
.topo .bahn-gl{fill:none;stroke:var(--muted);stroke-width:1;stroke-dasharray:4 3;opacity:.3}
.topo [class^="st"]{fill:none;stroke:var(--strasse);stroke-linecap:round;stroke-linejoin:round}
.topo .st-fuss{stroke-width:.6;stroke-dasharray:1.5 2}
.topo .st{stroke-width:1}
.topo .st-mittel{stroke-width:1.5}
.topo .st-haupt{stroke-width:2.1;stroke:var(--strasse-haupt)}
.topo .fl{font:italic 600 11px var(--head);letter-spacing:.3em;fill:var(--water);opacity:.55}
.topo .vl{font:600 8.5px var(--head);letter-spacing:.2em;text-transform:uppercase;fill:var(--muted);opacity:.55;text-anchor:middle}
.topo .route{fill:none;stroke:var(--flag);stroke-width:2;stroke-dasharray:6 5;stroke-linecap:round;opacity:.6}
.topo .stn{fill:var(--paper);stroke:var(--flag);stroke-width:1.8}
.topo .stn-n{font:700 9px var(--head);fill:var(--flag);text-anchor:middle}
.topo .osm{font:500 6px var(--body);fill:var(--muted);opacity:.7;text-anchor:end}
/* C */
.topo .ol-offen{fill:var(--ol-gelb)}
.topo .ol-gruen{fill:var(--ol-gruen)}
.topo .ol-gruen2{fill:url(#c-dicht)}
.topo .dicht{stroke:var(--ol-dicht);stroke-width:1.4}
.topo .ol-sumpf{fill:url(#c-sumpf)}
.topo .sumpf{stroke:var(--water);stroke-width:1;opacity:.45}
.topo .ol-c,.topo .ol-c5,.topo .ol-form{fill:none;stroke:var(--ol-braun);stroke-width:.9}
.topo .ol-c5{stroke-width:1.7}
.topo .ol-form{stroke-width:.7;stroke-dasharray:5 3}
.topo .ol-w{fill:none;stroke:var(--water);stroke-width:2.2;opacity:.45;stroke-linecap:round}
.topo .ol-wl{fill:none;stroke:var(--water);stroke-width:.9;opacity:.4}
.topo .ol-stein{stroke:var(--ol-schwarz);stroke-width:3.4;stroke-linecap:round}
.topo .ol-wand{fill:none;stroke:var(--ol-schwarz);stroke-width:1.1}
.topo .ol-weg,.topo .ol-pfad,.topo .ol-spur{fill:none;stroke:var(--ol-schwarz);stroke-width:1.3}
.topo .ol-pfad{stroke-width:1;stroke-dasharray:5 2.5}
.topo .ol-spur{stroke-width:.8;stroke-dasharray:2 2.5}
.topo .ol-nord{stroke:var(--water);stroke-width:.6;opacity:.3}
.topo .bahn{fill:none;stroke:var(--flag);stroke-width:1.6;opacity:.6}
.topo .bahn-n{font:700 12px var(--head);fill:var(--flag);opacity:.75}
/* Auf breiten Bildschirmen wären die Beschriftungen riesig: dort weglassen */
.breit .topo text{display:none}
"""

FLAG = ('<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="1" y="1" width="22" height="22" fill="none" '
        'stroke="var(--ink)" stroke-width="2" rx="3"/><path d="M8 18V6l9 4-9 4" fill="var(--flag)"/></svg>')

UI = f"""<div class="ui"><div class="marke">{FLAG}<div><h3>Stadtjagd</h3><small>Team Fuchs, FUCHS-4711</small></div></div>
<div class="panel"><div class="m">Station 2 von 5</div><h4>Astronomische Uhr</h4>
<div class="h">Am Rathaus des großen Platzes zeigt eine Uhr nicht nur die Stunde.</div>
<div class="kompass"><svg viewBox="0 0 78 78"><circle cx="39" cy="39" r="35" fill="none" stroke="var(--line)" stroke-width="3"/>
<polygon points="39,8 47,42 39,36 31,42" fill="var(--flag)" transform="rotate(38 39 39)"/></svg>
<div><div class="d">240 m</div><div class="m">GPS ±8 m, Kompass aktiv</div></div></div>
<div class="knopf">Wir sind da</div></div>
<div class="nav"><span>Anmeldung</span> | <span>Team</span> | <span>Spielleitung</span></div></div>"""

def lies(k):
    p = os.path.join(QUELLE, f"hintergrund-{k}.svg")
    raw = open(p, encoding="utf-8").read()
    return raw, len(raw.encode()) / 1024, len(gzip.compress(raw.encode())) / 1024

karten, breit = [], []
for k, buch, titel, text in VARIANTEN:
    s, kb, gz = lies(k)
    karten.append(f'<section class="karte"><h2><b>{buch}</b> {titel}</h2><p>{text}</p>'
                  f'<div class="groesse">{kb:.0f} KB, ausgeliefert etwa {gz:.0f} KB</div>'
                  f'<div class="handy">{s}{UI}</div></section>')
    # Breitbild: IDs doppelt, deshalb Muster und Textpfad-IDs umbenennen
    b = s.replace('id="a-wald"', 'id="a-wald-b"').replace("url(#a-wald)", "url(#a-wald-b)")
    breit.append(f'<section class="karte"><h2><b>{buch}</b> {titel}</h2><div class="breit">{b}</div></section>')

html = f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Hintergrund Varianten</title>
<link href="https://fonts.googleapis.com/css2?family=Barlow+Semi+Condensed:wght@500;600;700&family=Barlow:wght@400;500;600&display=swap" rel="stylesheet">
<style>{CSS}</style>
</head>
<body>
<div class="kopf"><h1>Stadtjagd: drei Hintergründe</h1>
<p>Jede Variante liegt hinter derselben Team-Ansicht. Die Linien bleiben auf jedem Bildschirm gleich fein,
auch am Laptop der Spielleitung; bisher wurden sie dort fast fünfmal so dick.</p>
<div class="schalter">
<button data-thema="light">Hell</button><button data-thema="dark">Dunkel</button><button data-thema="" aria-pressed="true">wie System</button>
<button id="leer" aria-pressed="false">Nur Hintergrund</button></div></div>
<div class="reihe">{''.join(karten)}</div>
<div class="zwischen"><h2>Am Laptop</h2><p>Dort zeigt der Hintergrund nur den mittleren Streifen, Beschriftungen fallen weg.</p></div>
<div class="reihe">{''.join(breit)}</div>
<script>
document.querySelectorAll("[data-thema]").forEach(b => b.onclick = () => {{
  const t = b.dataset.thema;
  if (t) document.documentElement.dataset.theme = t; else delete document.documentElement.dataset.theme;
  document.querySelectorAll("[data-thema]").forEach(x => x.setAttribute("aria-pressed", x === b));
}});
document.getElementById("leer").onclick = e => {{
  const an = document.body.classList.toggle("leer");
  e.currentTarget.setAttribute("aria-pressed", an);
}};
</script>
</body>
</html>"""
open(ZIEL, "w", encoding="utf-8").write(html)
print("geschrieben", ZIEL, f"{len(html.encode()) / 1024:.0f} KB")
