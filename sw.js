/* Service Worker der Stadtjagd (Ausfallsicherheit, Spezifikation 2026-10-15, Abschnitt 1).
   Damit die App auch im Funkloch oder bei einem Aussetzer von GitHub Pages startet. Er kümmert sich nur um die
   eigenen Dateien der App; alles andere geht unberührt ans Netz (kein respondWith):
   - Supabase und alle RPCs: nie aus dem Cache, ein Spielstand aus dem Cache wäre falsch;
   - Kartenkacheln und alles von fremden Rechnern;
   - alles, was nicht GET ist (auch der HEAD der Versionsprüfung);
   - andere Seiten im selben Ordner: geraete-test.html, kompass-test.html, design-system/, mockups/, tools/, und die
     Fernbedienung der Rückblick-Show fürs Handy (Nachtrag 37): ihre Navigation geht unberührt ans Netz, sie braucht
     ohnehin Netz; Schriften und config.js teilt sie mit der App (dafür gelten die Regeln unten).
   Hülle (index.html, config.js, kompass-waechter.js): Netz zuerst mit 4 s Grenze, sonst der Cache. Ein Fix ist
   also beim nächsten Laden mit Netz da. Schriften, Leaflet, QR: Cache zuerst (Dateinamen tragen die Fassung).
   Hintergründe: aus dem Cache, im Hintergrund nachgeladen.
   Aufräumen nur unter dem eigenen Präfix "sj-": CacheStorage gilt für den ganzen Origin (7deeda.github.io), also
   auch für den Geräte-Test und andere Pages-Projekte.
   Notausgang: tools/sw-aus.js nach sw.js kopieren und pushen (HANDOFF, Ablauf am Eventtag). */
"use strict";
// Die Nummer steigt nur, wenn sich die Liste oder die Strategie ändert, nicht bei jedem Fix (dafür sorgt Netz zuerst)
const HUELLE = "sj-huelle-1", DAUER = "sj-dauer-1";
const BASIS = new URL("./", self.location).href;   // Scope, etwa https://7deeda.github.io/Stadtjagt/
const HUELLE_DATEIEN = ["config.js", "kompass-waechter.js"];
const SCHRIFTEN = ["barlow-400-latin", "barlow-400-latin-ext", "barlow-500-latin", "barlow-500-latin-ext", "barlow-600-latin",
  "barlow-600-latin-ext", "barlow-semi-condensed-500-latin", "barlow-semi-condensed-500-latin-ext", "barlow-semi-condensed-600-latin",
  "barlow-semi-condensed-600-latin-ext", "barlow-semi-condensed-700-latin", "barlow-semi-condensed-700-latin-ext",
  "jetbrains-mono-700-latin", "jetbrains-mono-700-latin-ext"].map(n => `vendor/fonts/${n}.woff2`);
const HINTERGRUENDE = ["hintergrund/a.svg", "hintergrund/b.svg", "hintergrund/c.svg"];
// Karte der Spielleitung (Leaflet) und Mitlese-QR: gleich beim ersten Besuch, nicht erst nach der ersten Benutzung
const BIBLIOTHEKEN = ["vendor/qrcode.js", "vendor/leaflet-1.9.4/leaflet.js", "vendor/leaflet-1.9.4/leaflet.css",
  "vendor/leaflet-1.9.4/images/layers.png", "vendor/leaflet-1.9.4/images/layers-2x.png", "vendor/leaflet-1.9.4/images/marker-icon.png",
  "vendor/leaflet-1.9.4/images/marker-icon-2x.png", "vendor/leaflet-1.9.4/images/marker-shadow.png"];
const NETZ_GRENZE_MS = 4000;

const abs = p => new URL(p, BASIS).href;
const ablegbar = r => r && r.status === 200 && r.type === "basic";

self.addEventListener("install", e => {
  e.waitUntil((async () => {
    // Hülle mit addAll: scheitert eine Datei, scheitert die Installation, und alles läuft wie ohne Service Worker.
    // cache: "reload", sonst landete die 10-Minuten-Kopie aus dem HTTP-Cache im Speicher.
    const h = await caches.open(HUELLE);
    const index = await fetch(BASIS, { cache: "reload" });
    if (!ablegbar(index)) throw new Error("index.html nicht geladen");
    await h.put(BASIS, index);
    await h.addAll(HUELLE_DATEIEN.map(p => new Request(abs(p), { cache: "reload" })));
    // Schriften, Hintergründe und Bibliotheken einzeln: ein fehlendes Bild kippt die Installation nicht
    const d = await caches.open(DAUER);
    await Promise.all(SCHRIFTEN.concat(HINTERGRUENDE, BIBLIOTHEKEN).map(p => fetch(abs(p), { cache: "reload" })
      .then(r => ablegbar(r) ? d.put(abs(p), r) : null).catch(() => null)));
    await self.skipWaiting();
  })());
});

self.addEventListener("activate", e => {
  e.waitUntil((async () => {
    // nur eigene, alte Fassungen: fremde Caches desselben Origins bleiben unberührt
    const namen = await caches.keys();
    await Promise.all(namen.filter(n => n.startsWith("sj-") && n !== HUELLE && n !== DAUER).map(n => caches.delete(n)));
    await self.clients.claim();
  })());
});

// Netz zuerst: no-cache fragt am HTTP-Cache vorbei nach (ETag, meist 304). Kommt binnen 4 s eine gute Antwort, gilt
// sie und ersetzt die Kopie. Sonst die Kopie; der Abruf läuft weiter und legt sein Ergebnis fürs nächste Laden ab.
function netzZuerst(e, url, schluessel) {
  const netz = fetch(url, { cache: "no-cache" });
  e.waitUntil(netz.then(r => {
    if (!ablegbar(r)) return null;
    const kopie = r.clone();
    return caches.open(HUELLE).then(c => c.put(schluessel, kopie));
  }).catch(() => null));
  const kopie = () => caches.open(HUELLE).then(c => c.match(schluessel));
  return new Promise(fertig => {
    let erledigt = false;
    const geben = r => { if (!erledigt && r) { erledigt = true; clearTimeout(uhr); fertig(r); } };
    const uhr = setTimeout(() => kopie().then(geben), NETZ_GRENZE_MS);
    netz.then(async r => { if (r.ok) return geben(r); geben((await kopie()) || r); })
      .catch(async () => { const k = await kopie(); if (k) geben(k); else if (!erledigt) { erledigt = true; clearTimeout(uhr); fertig(Response.error()); } });
  });
}

async function cacheZuerst(schluessel) {
  const c = await caches.open(DAUER);
  const da = await c.match(schluessel);
  if (da) return da;
  const r = await fetch(schluessel);
  if (ablegbar(r)) await c.put(schluessel, r.clone());
  return r;
}

async function ausCacheNachladen(e, schluessel) {
  const c = await caches.open(DAUER);
  const da = await c.match(schluessel);
  const netz = fetch(schluessel, { cache: "no-cache" }).then(async r => { if (ablegbar(r)) await c.put(schluessel, r.clone()); return r; });
  if (da) { e.waitUntil(netz.catch(() => null)); return da; }
  return netz;
}

self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (!url.href.startsWith(BASIS)) return;   // fremde Rechner (Supabase, Kacheln) und andere Pfade desselben Origins
  const pfad = url.pathname.slice(new URL(BASIS).pathname.length);
  const ohneQuery = url.origin + url.pathname;
  if (req.mode === "navigate") {
    // Navigation auf ./ oder ./index.html, jede Query; immer unter dem Schlüssel ./ abgelegt. Die URL statt des
    // Request-Objekts: ein Request im Modus navigate lässt sich nicht mit eigenen Optionen neu abschicken.
    if (pfad === "" || pfad === "index.html") e.respondWith(netzZuerst(e, req.url, BASIS));
    return;
  }
  if (HUELLE_DATEIEN.includes(pfad)) { e.respondWith(netzZuerst(e, ohneQuery, ohneQuery)); return; }
  if (/^vendor\/fonts\/[a-z0-9-]+\.woff2$/.test(pfad) || /^vendor\/leaflet-1\.9\.4\//.test(pfad) || pfad === "vendor/qrcode.js") {
    e.respondWith(cacheZuerst(ohneQuery)); return;
  }
  if (HINTERGRUENDE.includes(pfad)) { e.respondWith(ausCacheNachladen(e, ohneQuery)); return; }
  // alles andere: kein respondWith, der Browser fragt wie ohne Service Worker
});
