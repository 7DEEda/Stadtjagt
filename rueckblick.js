/* Rückblick-Show der Stadtjagd, Fassung v2. Spezifikation: docs/superpowers/specs/2026-10-15-rueckblick-show-design.md
   (Ablauf nach dem Nachtrag vom 17.10.2026), Vorlage für Aussehen und Verhalten: mockups/rueckblick-v2/index.html,
   Kritik und Muss-Befunde: docs/superpowers/specs/2026-10-17-rueckblick-kritik.md, SPIEL.md §16.
   Wird von index.html nur beim Öffnen von #/rueckblick nachgeladen (zusammen mit rueckblick.css und
   rueckblick-karte.js), damit die Handys im Spiel nichts davon tragen. Die Show liegt in einem eigenen Container
   außerhalb von #app: index.html zeichnet sie nie neu und fragt in dieser Ansicht nichts ab.
   Alles steht in einer Funktion, damit keine Namen aus index.html überschrieben werden; was die Show von dort braucht,
   kommt über das Objekt host (rpc, pin, farbe, emoji, url, api). Stimmt host.api nicht mit API überein, sind index.html
   und diese Datei aus verschiedenen Fassungen: die Show meldet das und startet nicht.
   Ablauf: Splash, Fun Facts, Die Gruppen (nur bei mehr als einer Startgruppe), ein Zeitraffer, Awards, Rangliste von
   unten, Drei Spalten, Platz 3, Platz 2, Platz 1, Siegerbild, Abspann (endlos). */
(function () {
"use strict";
const API = 1;
let host = null, root = null, modus = "echt", rafId = 0, ladeNr = 0;
const $ = s => root.querySelector(s);
const MIN = 60000;
const MEDAILLE = ["🥇", "🥈", "🥉"];
const TZ = "Europe/Prague";   // K14: Uhrzeiten wie in Prag, egal wie der Laptop eingestellt ist

function zufall(seed) { return () => { seed |= 0; seed = seed + 0x6D2B79F5 | 0; let t = Math.imul(seed ^ seed >>> 15, 1 | seed);
  t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }

// Projektion: Meter um einen Bezugspunkt in Holešovice/Letná (für 2 km genau genug); dieselben Werte wie die Grundkarte
// (rueckblick-karte.js, erzeugt von tools/rueckblick/karte.py)
const LAT0 = 50.1000, LNG0 = 14.4235, KX = 71520, KY = 111200;
const P = (lat, lng) => [(lng - LNG0) * KX, (LAT0 - lat) * KY];
const LL = (x, y) => [LAT0 - y / KY, LNG0 + x / KX];

// Schriftschnitte der Bühne. unicode-range lädt Glyphen erst beim ersten Gebrauch: ohne Netz käme mitten in der Show die
// Ersatzschrift. Darum holt Vorbereiten jeden Schnitt einmal mit einem Mustertext, der die latin-ext-Teilmenge braucht.
const SCHNITTE = ['500 1em "Barlow Semi Condensed"', '600 1em "Barlow Semi Condensed"', '700 1em "Barlow Semi Condensed"',
  '500 1em "Barlow"', '600 1em "Barlow"'];
const SCHRIFT_MUSTER = "Holešovice Výstaviště Letná Křižík";

/* =====================================================================
   Beispieldaten für #/rueckblick/probe, in der Form der echten RPCs (admin_state, admin_tracks, admin_photos).
   Drei Startgruppen je 15 min versetzt, mit startedAt und startGroup je Team: so liefern es die echten Daten, sobald
   es Startgruppen gibt. Die Show selbst liest nur, was aufbereiten() daraus macht.
   ===================================================================== */
const GRUPPE_MS = 15 * MIN;
const beispielDaten = (anzahl = 12) => {
  const R = zufall(20261017);
  const T0 = Date.UTC(2026, 9, 17, 12, 0, 12), TEND = Date.UTC(2026, 9, 17, 14, 40, 0);
  const STATIONEN = [
    { position: 1, name: "Planetarium Prag", lat: 50.105286, lng: 14.427406, radiusM: 50 },
    { position: 2, name: "Rudolfstollen", lat: 50.104441, lng: 14.419553, radiusM: 60 },
    { position: 3, name: "Wasserturm Letná", lat: 50.100195, lng: 14.420089, radiusM: 50 },
    { position: 4, name: "Aussicht Letná", lat: 50.095789, lng: 14.425346, radiusM: 50 },
    { position: 5, name: "Metronom", lat: 50.094775, lng: 14.415938, radiusM: 50 }];
  const START = { name: "Hotel Mama Shelter", lat: 50.102458, lng: 14.431681 };
  const WEGE = [
    [[50.1036, 14.4317], [50.1047, 14.4311], [50.1053, 14.4291]],
    [[50.1059, 14.4252], [50.1057, 14.4222], [50.1049, 14.4203]],
    [[50.1034, 14.4191], [50.1021, 14.4207], [50.1010, 14.4198]],
    [[50.0992, 14.4213], [50.0981, 14.4233], [50.0968, 14.4249]],
    [[50.0957, 14.4229], [50.0955, 14.4201], [50.0951, 14.4176]]];
  const UMWEG = { Pinguin: { 1: [[50.1063, 14.4262], [50.1076, 14.4240], [50.1070, 14.4208], [50.1052, 14.4200]] },
    Flamingo: { 3: [[50.0995, 14.4247], [50.0986, 14.4282], [50.0972, 14.4268]] },
    Wolf: { 4: [[50.0962, 14.4232], [50.0966, 14.4196], [50.0955, 14.4178]] } };
  const NAMEN = ["Adler", "Delfin", "Einhorn", "Eule", "Flamingo", "Fuchs", "Igel", "Otter", "Panda", "Pinguin", "Tiger", "Wolf",
    "Biber", "Drache", "Koala", "Krake"].slice(0, anzahl).sort((a, b) => a.localeCompare(b, "de"));
  const TEMPO = { Adler: .78, Eule: .84, Tiger: .88, Fuchs: .93, Wolf: .97, Panda: 1, Delfin: 1.04, Pinguin: 1.08, Einhorn: 1.2, Flamingo: 1.3, Otter: 1.12, Igel: 1.38,
    Biber: 1.06, Drache: .9, Koala: 1.16, Krake: 1.01 };
  const GEHEN = [8, 10, 9, 10, 11], RAETSEL = [6, 9, 7, 11, 8];
  const STECKT = { Otter: 5, Igel: 4 };              // rätselt beim Spielende noch an dieser Station
  const LUECKE = { Otter: [31 * MIN, 45 * MIN] };    // Handy in der Tasche (ab dem Start der Gruppe)
  const OHNE_FOTO = new Set(["Delfin:1", "Pinguin:3", "Wolf:4"]);
  const VOR = ["Anna", "Ben", "Clara", "David", "Emre", "Fatma", "Greta", "Hannes", "Ida", "Jonas", "Kira", "Lars", "Mia", "Nils", "Olga", "Paul",
    "Rosa", "Sven", "Tara", "Uwe", "Vera", "Wim", "Yara", "Zoe", "Aylin", "Bruno", "Carla", "Dennis", "Elif", "Finn", "Gül", "Henrik"];
  const NACH = ["Berger", "Demir", "Keller", "Krüger", "Hoffmann", "Schröder", "Wagner", "Neumann", "Schulz", "Hofmann", "Franke", "Martin",
    "Yılmaz", "Lehmann", "Peters", "Graf", "Vogel", "Kaya", "Brandt", "Busch", "Arnold", "Lorenz", "Sommer", "Winter"];
  const leute = new Set(); while (leute.size < anzahl * 8) leute.add(VOR[Math.floor(R() * VOR.length)] + " " + NACH[Math.floor(R() * NACH.length)]);
  const alle = [...leute];
  const along = (wp, f) => {   // Punkt bei Anteil f der Länge eines Linienzugs
    const seg = []; let L = 0;
    for (let i = 1; i < wp.length; i++) { const d = Math.hypot(wp[i][0] - wp[i - 1][0], wp[i][1] - wp[i - 1][1]); seg.push(d); L += d; }
    let s = f * L;
    for (let i = 0; i < seg.length; i++) {
      if (s <= seg[i] || i === seg.length - 1) { const u = seg[i] ? Math.min(1, s / seg[i]) : 0;
        const a = wp[i], b = wp[i + 1], nx = -(b[1] - a[1]) / (seg[i] || 1), ny = (b[0] - a[0]) / (seg[i] || 1);
        return [a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u, nx, ny]; }
      s -= seg[i];
    }
  };
  const teams = [], tracks = [], fotos = [];
  NAMEN.forEach((name, ti) => {
    const f = TEMPO[name] || 1.1, seite = (R() - .5) * 16, pts = [], sts = [];
    const gruppe = ti % 3, T0g = T0 + gruppe * GRUPPE_MS, TENDg = TEND + gruppe * GRUPPE_MS;
    const punkt = (x, y, t, s = 4) => pts.push([x + (R() - .5) * s * 2, y + (R() - .5) * s * 2, t]);
    let t = T0g + R() * 1.5 * MIN, cur = P(START.lat, START.lng), fertig = null;
    for (let k = 0; k < 5; k++) {
      const s = STATIONEN[k], ziel = P(s.lat, s.lng);
      const wp = [cur, ...((UMWEG[name] && UMWEG[name][k]) || WEGE[k]).map(p => P(p[0], p[1])), ziel];
      const gehen = GEHEN[k] * f * (0.85 + R() * 0.3) * MIN;
      for (let tt = t; tt < t + gehen; tt += 15000 + (R() - .5) * 6000) {
        const a = along(wp, (tt - t) / gehen); punkt(a[0] + a[2] * seite, a[1] + a[3] * seite, tt);
      }
      const an = t + gehen, ein = an + (0.3 + R() * 0.6) * MIN;
      const st = { position: k + 1, checkedInAt: new Date(ein).toISOString(), solvedAt: null };
      sts.push(st);
      if (STECKT[name] === k + 1) { for (let tt = an; tt < TENDg; tt += 60000) punkt(ziel[0] + 18, ziel[1] - 10, tt, 6); break; }
      const geloest = ein + RAETSEL[k] * f * (0.7 + R() * 0.6) * MIN;
      st.solvedAt = new Date(geloest).toISOString();
      if (!OHNE_FOTO.has(name + ":" + (k + 1))) fotos.push({ teamName: name, position: k + 1, stationName: s.name, route: "echt", takenAt: new Date(geloest + (0.6 + R() * 0.6) * MIN).toISOString() });
      const weg = geloest + (1.2 + R() * 0.8) * MIN;
      for (let tt = an; tt < weg; tt += 60000) punkt(ziel[0] + (R() - .5) * 20, ziel[1] + (R() - .5) * 20, tt, 3);
      t = weg; cur = ziel;
      if (k === 4) fertig = weg + (0.8 + R() * 1.6) * MIN;
    }
    // nach dem Koffer meldet kein Handy mehr (M6: aufbereiten() schneidet bei finishedAt ab)
    const id = "t" + (ti + 1), lu = LUECKE[name];
    const roh = pts.filter(p => !lu || p[2] < T0g + lu[0] || p[2] > T0g + lu[1]).map(p => { const l = LL(p[0], p[1]); return [+l[0].toFixed(6), +l[1].toFixed(6), Math.round(p[2])]; });
    const leute8 = alle.slice(ti * 8, ti * 8 + 8).sort((a, b) => a.localeCompare(b, "de"));
    teams.push({ id, name, members: leute8, leaderName: leute8[Math.floor(R() * 8)], solved: sts.filter(s => s.solvedAt).length,
      finishedAt: fertig ? new Date(fertig).toISOString() : null, place: null, startedAt: new Date(T0g).toISOString(), startGroup: gruppe });
    tracks.push({ id, name, points: roh, pointCount: roh.length, stations: sts });
    fotos.forEach(x => { if (x.teamName === name) x.teamId = id; });
  });
  // Platz wie in der Datenbank nach der Uhrzeit des Koffer-Codes; die Show wertet nach Gesamtzeit (aufbereiten)
  teams.filter(t => t.finishedAt).sort((a, b) => a.finishedAt.localeCompare(b.finishedAt)).forEach((t, i) => t.place = i + 1);
  const ende = new Date(TEND + 2 * GRUPPE_MS).toISOString();
  return {
    state: { status: "finished", testMode: false, route: "echt", prizeCount: 3, selfieOn: true, photosDeleteOn: "2026-10-19",
      startedAt: new Date(T0).toISOString(), finishedAt: ende, start: START, stations: STATIONEN, teams },
    tracks: { status: "finished", startedAt: new Date(T0).toISOString(), finishedAt: ende, teams: tracks },
    photos: fotos
  };
};

// Platzhalter für ein Gruppenselfie in der Probe (im echten Spiel: admin_photo mit p_full = true)
function mischen(a, b, w) { const p = h => [1, 3, 5].map(i => parseInt(h.substr(i, 2), 16)), x = p(a), y = p(b);
  return "#" + x.map((v, i) => Math.round(v * (1 - w) + y[i] * w).toString(16).padStart(2, "0")).join(""); }
function fotoBild(team, pos, quer) {
  const R = zufall(team.name.length * 97 + pos * 13 + team.name.charCodeAt(0));
  const oben = mischen(team.farbe, "#FFFFFF", .58), unten = mischen(team.farbe, "#17302A", .2);
  const marken = [
    '<path d="M150 330 A150 150 0 0 1 450 330 Z M120 330 H480 V352 H120 Z"/>',
    '<path d="M110 360 C150 200 450 200 490 360 Z" opacity=".5"/><path d="M220 360 V270 A80 80 0 0 1 380 270 V360 Z" fill="#17302A" opacity=".55"/>',
    '<path d="M265 360 V150 H335 V360 Z M250 150 L300 80 L350 150 Z"/>',
    '<path d="M120 360 H200 V320 H260 V280 H320 V240 H380 V200 H480 V360 Z"/>',
    '<path d="M250 360 L350 360 L330 300 L270 300 Z"/><path d="M300 305 L410 80" stroke="#fff" stroke-width="16" stroke-linecap="round"/>'][(pos - 1) % 5];
  const n = 5 + Math.floor(R() * 4); let leute = "";
  for (let i = 0; i < n; i++) {
    const x = 70 + (460 / (n - 1)) * i + (R() - .5) * 30, y = 520 + (R() - .5) * 60 + (i % 2) * 34, r = 46 + R() * 10;
    leute += `<g opacity="${(0.62 + R() * 0.2).toFixed(2)}"><circle cx="${x.toFixed(0)}" cy="${y.toFixed(0)}" r="${r.toFixed(0)}"/><ellipse cx="${x.toFixed(0)}" cy="${(y + r + 120).toFixed(0)}" rx="${(r * 1.7).toFixed(0)}" ry="${(r * 1.9).toFixed(0)}"/></g>`;
  }
  const svg = quer
    ? `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 600"><defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${oben}"/><stop offset="1" stop-color="${unten}"/></linearGradient></defs>
    <rect width="800" height="600" fill="url(#g)"/><g fill="#fff" opacity=".5" transform="translate(100,-120)">${marken}</g><g fill="#17302A" transform="translate(-30,-230) scale(1.42,1)">${leute}</g>
    <circle cx="730" cy="545" r="50" fill="#17302A" opacity=".85"/></svg>`
    : `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 800"><defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${oben}"/><stop offset="1" stop-color="${unten}"/></linearGradient></defs>
    <rect width="600" height="800" fill="url(#g)"/><g fill="#fff" opacity=".5">${marken}</g><g fill="#17302A">${leute}</g>
    <circle cx="520" cy="740" r="60" fill="#17302A" opacity=".85"/></svg>`;
  return "data:image/svg+xml;charset=utf-8," + encodeURIComponent(svg);
}

/* =====================================================================
   Aufbereiten: aus den RPC-Antworten werden Teams, Spuren, Plätze, Awards (Spezifikation 6.3 mit den Nachträgen).
   Reine Funktion von roh, ohne Zugriff auf die Seite (außer Teamfarbe und Tier aus host).
   ===================================================================== */
const LUECKE_M = 50, LUECKE_MS = 90000;   // wie LUECKE_M/LUECKE_MS in index.html (gestrichelte Strecken)
const MAX_MS = 15 / 3.6;                   // schneller als 15 km/h läuft hier niemand
const DUENN_M = 8;                         // S14: Punkte näher als 8 m am letzten behaltenen fallen weg
const CHECKIN_FENSTER = 3 * MIN, SPAETSTART = 5 * MIN;   // M7
const ACC_MAX = 25, TEMPO_MIN_MS = 60000, TEMPO_MIN_M = 100;   // Awards: was fürs Tempo zählt
const OPT = { fotos: true, anhalten: true, rand: false, aus: new Set() };
let D = null;   // aufbereitete Daten
let K = [];     // Kapitel

const dist = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1]);
const ms = iso => iso ? Date.parse(iso) : null;
const uhr = t => new Date(t).toLocaleTimeString("de-DE", { timeZone: TZ, hour: "2-digit", minute: "2-digit" });
// Laufzeit seit dem gemeinsamen Start 0:00, etwa 0:10 oder 1:23
const lauf = t => { const m = Math.max(0, Math.floor((t - D.t0) / 60000)); return Math.floor(m / 60) + ":" + String(m % 60).padStart(2, "0"); };
function dauerGenau(m) { const s = Math.round(m / 1000); return Math.floor(s / 3600) + ":" + String(Math.floor(s / 60) % 60).padStart(2, "0") + ":" + String(s % 60).padStart(2, "0") + " h"; }
const km = m => (m / 1000).toFixed(1).replace(".", ",") + " km";
const datumKurz = t => new Date(t + "T12:00").toLocaleDateString("de-DE");

// GPS-Sprünge (S15): verworfen wird ein Lauf aus einem bis drei Punkten, der vom letzten guten Punkt wegspringt und
// zurück, während der Punkt danach wieder zum letzten guten passt (15 km/h). Ein Vergleich nur mit dem "letzten
// behaltenen Punkt" würde nach einer Tram- oder Taxifahrt jeden weiteren Punkt verwerfen (kaskadiert); vier Punkte
// woanders sind kein Ausreißer mehr, sondern ein Ort.
function ohneAusreisser(pts) {
  const v = (a, b) => dist([a.x, a.y], [b.x, b.y]) / Math.max(1, (b.t - a.t) / 1000), aus = [];
  for (let k = 0; k < pts.length;) {
    let weg = 0;
    if (aus.length) {
      const vor = aus[aus.length - 1];
      if (v(vor, pts[k]) > MAX_MS)
        for (let n = 1; n <= 3 && k + n < pts.length; n++)
          if (v(pts[k + n - 1], pts[k + n]) > MAX_MS && v(vor, pts[k + n]) <= MAX_MS) { weg = n; break; }
    }
    if (weg) { k += weg; continue; }
    aus.push(pts[k]); k++;
  }
  return aus;
}
// S14: echte Handys melden 4.000 bis 8.000 Punkte je Team; die Bühne braucht davon nur die, die etwas zeigen. Ein Punkt
// bleibt, wenn er mehr als 8 m vom letzten behaltenen liegt, eine Lücke beginnt oder endet, oder der letzte ist. Stand
// das Team (der letzte behaltene liegt über 20 s zurück), bleibt auch der Punkt davor: sonst wanderte der Kopf über die
// ganze Wartezeit langsam zur nächsten Stelle.
function ausduennen(p) {
  if (p.length < 3) return p;
  const aus = [p[0]];
  for (let i = 1; i < p.length; i++) {
    const q = p[i], a = aus[aus.length - 1], vor = p[i - 1], letzter = i === p.length - 1;
    if (q.g || letzter || p[i + 1].g || dist([a.x, a.y], [q.x, q.y]) > DUENN_M) {
      if (vor !== a && vor.t - a.t > 20000) aus.push(vor);
      aus.push(q);
    }
  }
  return aus;
}
// M7: GPS bricht ab, startet spät oder fehlt um einen Check-in: Check-in und Lösung kommen immer dazu, als Punkt an der
// Station, wenn kein GPS-Punkt innerhalb von 3 min liegt; liegt der erste GPS-Punkt mehr als 5 min nach dem Start, steht
// der Startpunkt bei 0:00 davor. Die Stücke zu und von solchen Punkten sind gestrichelt.
function einmischen(gps, sts, startXY, ort, tStart, schluss) {
  const nahe = t => { const i = kopfIdx(gps, t); return [gps[i], gps[i + 1]].some(p => p && Math.abs(p.t - t) <= CHECKIN_FENSTER); };
  const neu = [], spaet = gps[0].t > tStart + SPAETSTART;
  if (spaet) neu.push({ x: startXY[0], y: startXY[1], t: tStart, syn: true });
  sts.forEach(s => { const xy = ort(s.position); if (!xy) return;
    [s.ein, s.ok].forEach(t => { if (t && t <= schluss && !nahe(t)) neu.push({ x: xy[0], y: xy[1], t, syn: true }); }); });
  if (!neu.length) return { pts: gps, spaet: false, ende: false };
  const pts = gps.concat(neu).sort((a, b) => a.t - b.t);
  pts.forEach((p, k) => { if (k && (p.syn || pts[k - 1].syn)) p.g = true; });
  pts[0].g = false;
  return { pts, spaet, ende: neu.some(p => p.t > gps[gps.length - 1].t) };
}

function aufbereiten(roh) {
  const st = roh.state, tr0 = roh.tracks || {}, t0 = ms(st.startedAt);
  const tEndUhr = ms(st.finishedAt) || ms(tr0.finishedAt) || t0;
  const stationen = (st.stations || []).slice().sort((a, b) => a.position - b.position)
    .map(s => ({ ...s, xy: s.lat != null && s.lng != null ? P(s.lat, s.lng) : null }));   // ohne Koordinaten: fehlt auf der Karte
  const start = st.start && st.start.lat != null ? { ...st.start, xy: P(st.start.lat, st.start.lng) }
    : { name: "Start", xy: (stationen.find(s => s.xy) || { xy: [0, 0] }).xy };
  const anker = [start.xy, ...stationen.filter(s => s.xy).map(s => s.xy)];
  const ort = pos => (stationen.find(x => x.position === pos) || {}).xy || null;
  // Startgruppen: heute starten alle mit dem Spiel; liefern die Daten je Team startedAt (oder startGroup), zählt dessen Start
  const tStartVon = t => t.startedAt ? ms(t.startedAt) : t0;
  const starts = [...new Set((st.teams || []).map(tStartVon))].sort((a, b) => a - b);
  let rohPunkte = 0;
  const teams = (st.teams || []).map((t, i) => {
    const tr = (tr0.teams || []).find(x => x.id === t.id) || { points: [], stations: [] };
    rohPunkte += (tr.points || []).length;
    const tStart = tStartVon(t), fertigUhr = ms(t.finishedAt);
    // M6: nach dem Koffer-Code (plus 2 min) zählt nichts mehr, weder auf der Karte noch in den Kilometern
    const schluss = Math.min(tEndUhr, fertigUhr != null ? fertigUhr + 2 * MIN : Infinity);
    // Punkte nur aus dem Spiel, nur nahe der Route (1 km), ohne Ausreißer; Genauigkeit, falls die Daten sie tragen
    let gps = (tr.points || []).filter(p => p[2] >= tStart - MIN && p[2] <= schluss)
      .map(p => { const xy = P(p[0], p[1]); return { x: xy[0], y: xy[1], t: p[2], acc: p[3] == null ? null : +p[3], g: false }; })
      .filter(p => Math.min(...anker.map(a => dist(a, [p.x, p.y]))) < 1000);
    gps = ohneAusreisser(gps);
    gps.forEach((p, k) => { p.g = false; if (!k) return; const q = gps[k - 1], m = dist([p.x, p.y], [q.x, q.y]), dt = p.t - q.t;
      p.g = m > LUECKE_M || (dt > LUECKE_MS && m > 15); });
    // Strecke: Ankermethode wie laufrichtung(): ein Stück zählt erst ab 15 m vom letzten Anker (Zittern im Stand zählt nicht)
    let weg = 0; if (gps.length >= 2) { let a = gps[0]; for (const q of gps) { const dd = dist([a.x, a.y], [q.x, q.y]); if (dd > 15) { weg += dd; a = q; } } }
    gps = ausduennen(gps);
    const sts = (tr.stations || []).map(s => ({ position: s.position, ein: ms(s.checkedInAt), ok: ms(s.solvedAt) })).sort((a, b) => a.position - b.position);
    const ohneGps = gps.length < 2;
    let pts, gpsHinweis = null;
    if (ohneGps) {   // Weg aus den Check-ins, ganz gestrichelt; ganz ohne Check-in bleibt das Team am Start
      pts = [{ x: start.xy[0], y: start.xy[1], t: tStart }];
      sts.forEach(s => { const xy = ort(s.position); if (!xy || !s.ein) return;
        pts.push({ x: xy[0], y: xy[1], t: s.ein }); if (s.ok) pts.push({ x: xy[0], y: xy[1], t: s.ok }); });
      pts.sort((a, b) => a.t - b.t);
      pts.forEach((p, k) => p.g = k > 0 && dist([p.x, p.y], [pts[k - 1].x, pts[k - 1].y]) > 1);
      weg = 0;
    } else {
      const r = einmischen(gps, sts, start.xy, ort, tStart, schluss);
      pts = r.pts;
      const von = uhr(gps[0].t), bis = uhr(gps[gps.length - 1].t);
      if (r.spaet && r.ende) gpsHinweis = `${t.name}: GPS nur von ${von} bis ${bis}, sonst aus den Check-ins`;
      else if (r.spaet) gpsHinweis = `${t.name}: GPS erst ab ${von}, davor aus den Check-ins`;
      else if (r.ende) gpsHinweis = `${t.name}: GPS nur bis ${bis}, danach aus den Check-ins`;
    }
    // alle Zeiten auf den gemeinsamen Start 0:00 schieben (virtuelles Rennen der Startgruppen)
    const versatz = tStart - t0;
    if (versatz) { pts.forEach(p => p.t -= versatz); sts.forEach(x => { if (x.ein) x.ein -= versatz; if (x.ok) x.ok -= versatz; }); }
    const fertig = fertigUhr != null ? fertigUhr - versatz : null;
    return { id: t.id, name: t.name, emoji: host.emoji(t.name), farbe: host.farbe(i), members: t.members || [], leitung: t.leaderName || null, dbPlace: t.place ?? null, place: null,
      gruppe: t.startGroup ?? starts.indexOf(tStart), startAt: tStart, versatz, fertig, netto: fertig != null ? fertig - t0 : null,
      pts, sts, ohneGps, weg, gpsHinweis, gleich: [], solved: sts.filter(s => s.ok).length, luecken: !ohneGps && pts.some(p => p.g) };
  });
  // Ende des Zeitraffers in Laufzeit: alle Gruppen haben dieselbe Spieldauer, das Spiel endet mit der Zeit der letzten
  // Gruppe; in Laufzeit also Spielende minus Versatz der letzten Gruppe
  const tEnd = Math.max(tEndUhr - Math.max(0, ...teams.map(t => t.versatz)), ...teams.map(t => t.fertig || 0));
  // Plätze nach Gesamtzeit (vom eigenen Start bis zum Koffer-Code); bei gleicher Zeit gilt der Platz aus der Datenbank
  const fertige = teams.filter(t => t.netto != null)
    .sort((a, b) => a.netto - b.netto || (a.dbPlace || 999) - (b.dbPlace || 999) || a.name.localeCompare(b.name, "de"));
  fertige.forEach((t, n) => t.place = n + 1);
  // K12: dieselbe Sekunde auf den Walzen, also benennen, wer knapp vorn lag (ohne Teamnamen, damit nichts verrät)
  fertige.forEach((t, n) => { const nb = fertige[n + 1]; if (!nb || Math.round(nb.netto / 1000) !== Math.round(t.netto / 1000)) return;
    const s = ((nb.netto - t.netto) / 1000).toFixed(1).replace(".", ",");
    if (s === "0,0") { t.gleich.push(`gleichauf mit Platz ${nb.place}`); nb.gleich.push(`gleichauf mit Platz ${t.place}`); }
    else { t.gleich.push(`${s} s vor Platz ${nb.place}`); nb.gleich.push(`${s} s hinter Platz ${t.place}`); } });
  // Reihenfolge wie die öffentliche Rangliste: Platz, dann gelöste Stationen, dann letzte Lösung
  const letzte = t => Math.max(0, ...t.sts.filter(s => s.ok).map(s => s.ok)) || Infinity;
  const rang = [...teams].sort((a, b) => (a.place || 999) - (b.place || 999) || b.solved - a.solved || letzte(a) - letzte(b));
  const fotos = (roh.photos || []).filter(f => (f.route || "echt") === "echt" && teams.some(t => t.id === f.teamId))
    .map(f => { const team = teams.find(t => t.id === f.teamId); return { ...f, team, takenAt: ms(f.takenAt) - team.versatz, ratio: f.ratio || 3 / 4 }; });
  const d = { st, t0, tEnd, tEndUhr, start, stationen, teams, rang, fotos, rohPunkte, prizeCount: st.prizeCount ?? 3 };
  d.awards = awardsVergeben(d);
  return d;
}

/* ---------- Awards: lustige Preise aus Spuren und Check-ins, vor den Koffern ---------- */
// Kennzahlen je Team. Was fehlt (kein GPS, Lücke oder zu wenig Punkte auf einem Weg, keine gelöste Station), bleibt leer;
// das Team fällt dann nur aus dieser Wertung. Weg und Gehzeit je Abschnitt: vom letzten Punkt am alten Ort (60 m) bis
// zum ersten am neuen, für Umweg an beiden Enden mit dem Ort verbunden; Rätselzeit und Warten an der Station zählen
// nicht. Nur bis zur letzten Station, die das Team der Reihe nach gelöst hat. Tempo nur aus Stücken von mindestens 60 s
// und 100 m, deren Punkte (falls die Daten die Genauigkeit tragen) höchstens 25 m ungenau sind; Weg und Zeit sind dabei
// dasselbe Stück (ohne die Verbindungen zu den Orten).
function kennzahlen(t, d) {
  const z = {};
  const raetsel = t.sts.filter(x => x.ein && x.ok && x.ok > x.ein).map(x => x.ok - x.ein);
  if (raetsel.length) z.raetsel = raetsel.reduce((a, b) => a + b, 0) / raetsel.length;
  const reihe = [];
  for (const s of d.stationen) { if (!s.xy) break; const x = t.sts.find(y => y.position === s.position); if (!x || !x.ein || !x.ok) break; reihe.push({ s, x }); }
  if (!reihe.length || t.ohneGps) return z;
  let kurz = 0, gelaufen = 0, tm = 0, tz = 0, vorXY = d.start.xy, vorT = d.t0;
  for (const { s, x } of reihe) {
    // Weg vollständig: genug Punkte, keine Lücke (auch nicht zum ersten Punkt danach), Anfang und Ende an den Orten
    const i0 = t.pts.findIndex(p => p.t >= vorT), i1 = kopfIdx(t.pts, x.ein), ps = i0 < 0 ? [] : t.pts.slice(i0, i1 + 1);
    const nach = t.pts[i1 + 1], eng = (p, xy) => dist([p.x, p.y], xy) < 100;
    if (ps.length < 3 || ps.slice(1).some(p => p.g) || (nach && nach.g) || !eng(ps[0], vorXY) || !eng(ps[ps.length - 1], s.xy)) return z;
    const da = p => dist([p.x, p.y], s.xy) < 60, j1 = ps.findIndex(da), j0 = j1 < 0 ? -1 : ps.slice(0, j1 + 1).findLastIndex(p => dist([p.x, p.y], vorXY) < 60);
    if (j0 < 0 || j1 - j0 < 2) return z;
    const geh = ps.slice(j0, j1 + 1);
    let a = geh[0], innen = 0;
    for (const q of geh) { const dd = dist([a.x, a.y], [q.x, q.y]); if (dd > 15) { innen += dd; a = q; } }
    const e = geh[geh.length - 1]; innen += dist([a.x, a.y], [e.x, e.y]);
    const m = dist(vorXY, [geh[0].x, geh[0].y]) + innen + dist([e.x, e.y], s.xy), dauer = e.t - geh[0].t;
    gelaufen += m; kurz += dist(vorXY, s.xy);
    if (dauer >= TEMPO_MIN_MS && innen >= TEMPO_MIN_M && geh.every(p => p.acc == null || p.acc <= ACC_MAX)) { tm += innen; tz += dauer; }
    vorXY = s.xy; vorT = x.ok;
  }
  Object.assign(z, { kurz, gelaufen, umweg: gelaufen - kurz, faktor: gelaufen / kurz });
  if (tz > 0) z.tempo = tm / 1000 / (tz / 3600000);
  return z;
}
const kmh = v => v.toFixed(1).replace(".", ",") + " km/h";
const minuten = m => Math.max(1, Math.round(m / 60000)) + " min";
const meter = m => m >= 1000 ? km(m) : Math.round(m / 10) * 10 + " m";
// Reihenfolge der Show: abwechselnd gut und lustig. richtung 1: kleinster Wert gewinnt, -1: größter
const AWARDS = [
  { id: "navi", titel: "Navi auf zwei Beinen", emo: "🧭", richtung: 1, wert: z => z.faktor,
    zeile: z => { const p = Math.round((z.faktor - 1) * 100); return p >= 1 ? `nur <b>${p} %</b> Umweg vom idealen Weg` : "<b>kaum</b> Umweg vom idealen Weg"; } },
  { id: "sightseeing", titel: "Sightseeing-Tour", emo: "📸", richtung: -1, wert: z => z.umweg, gilt: z => z.umweg > 0,
    zeile: z => `<b>${meter(z.umweg)}</b> mehr Prag gesehen` },
  { id: "raetselfuechse", titel: "Rätselfüchse", emo: "🧩", richtung: 1, wert: z => z.raetsel,
    zeile: z => `im Schnitt <b>${minuten(z.raetsel)}</b> je Rätsel` },
  { id: "philosophen", titel: "Die Philosophen", emo: "🤔", richtung: -1, wert: z => z.raetsel,
    zeile: z => `im Schnitt <b>${minuten(z.raetsel)}</b> nachgedacht` },
  { id: "sprinter", titel: "Sprinter", emo: "⚡", richtung: -1, wert: z => z.tempo,
    zeile: z => `<b>${kmh(z.tempo)}</b> im Schnitt` },
  { id: "flaneure", titel: "Flaneure", emo: "☕", richtung: 1, wert: z => z.tempo,
    zeile: z => `<b>${kmh(z.tempo)}</b>, Zeit für Prag` }];
// Jedes Team höchstens einen Award: hat der Beste schon einen, geht er an das nächstbeste Team. Haben weniger als drei
// Teams die Kennzahl, entfällt der Award still. Die Koffer-Teams gehen leer aus: ein "Sprinter" kurz vor der
// Siegerehrung verriete, wer vorn liegt (sie bekommen gleich ihren eigenen Auftritt)
function awardsVergeben(d) {
  const alle = d.teams.map(t => ({ t, z: kennzahlen(t, d) })), vergeben = new Set(), liste = [];
  d.kennzahlen = alle;
  const frei = alle.filter(x => !(x.t.place && x.t.place <= d.prizeCount));
  for (const a of AWARDS) {
    const mit = frei.filter(x => Number.isFinite(a.wert(x.z)) && (!a.gilt || a.gilt(x.z)));
    if (mit.length < 3) continue;
    mit.sort((p, q) => (a.wert(p.z) - a.wert(q.z)) * a.richtung);
    const sieger = mit.find(x => !vergeben.has(x.t.id)); if (!sieger) continue;
    vergeben.add(sieger.t.id);
    liste.push({ id: a.id, titel: a.titel, emo: a.emo, team: sieger.t, wert: a.wert(sieger.z), zeile: a.zeile(sieger.z) });
  }
  return liste;
}

/* ---------- Kamera: Inhalt (Meter) in einen Bühnenbereich einpassen ---------- */
const VOLL_B = { x: 0, w: 1920 };
function rahmen(punkte, pad, minW) {
  punkte = punkte.filter(Boolean);   // eine Station ohne Koordinaten fehlt auf der Karte
  if (!punkte.length) punkte = [[0, 0]];
  let x0 = Math.min(...punkte.map(p => p[0])) - pad, x1 = Math.max(...punkte.map(p => p[0])) + pad;
  let y0 = Math.min(...punkte.map(p => p[1])) - pad, y1 = Math.max(...punkte.map(p => p[1])) + pad;
  if (x1 - x0 < minW) { const c = (x0 + x1) / 2; x0 = c - minW / 2; x1 = c + minW / 2; }
  if (y1 - y0 < minW * .6) { const c = (y0 + y1) / 2; y0 = c - minW * .3; y1 = c + minW * .3; }
  return { x0, x1, y0, y1 };
}
function einpassen(b, bereich, rand = 70) {
  const Y = bereich.y || 0, H = bereich.h || 1080;   // ohne y/h: volle Höhe
  const s = Math.min((bereich.w - 2 * rand) / (b.x1 - b.x0), (H - 2 * rand) / (b.y1 - b.y0));
  const bx = (b.x0 + b.x1) / 2, by = (b.y0 + b.y1) / 2;
  return { cx: bx + (960 - (bereich.x + bereich.w / 2)) / s, cy: by + (540 - (Y + H / 2)) / s, s };
}
function kamMisch(a, b, u) { return { cx: a.cx + (b.cx - a.cx) * u, cy: a.cy + (b.cy - a.cy) * u, s: Math.exp(Math.log(a.s) + (Math.log(b.s) - Math.log(a.s)) * u) }; }
const glatt = u => u <= 0 ? 0 : u >= 1 ? 1 : u * u * (3 - 2 * u);

/* ---------- Kopf (Teamposition) zu einer Zeit ---------- */
function kopfIdx(p, T) { let lo = 0, hi = p.length - 1; if (!p.length || T < p[0].t) return -1;
  while (lo < hi) { const m = (lo + hi + 1) >> 1; if (p[m].t <= T) lo = m; else hi = m - 1; } return lo; }
function kopf(team, T) {
  const p = team.pts; if (!p.length) return null;
  const i = kopfIdx(p, T); if (i < 0) return [p[0].x, p[0].y];
  if (i >= p.length - 1) return [p[i].x, p[i].y];
  const a = p[i], b = p[i + 1], u = (T - a.t) / Math.max(1, b.t - a.t);
  return [a.x + (b.x - a.x) * u, a.y + (b.y - a.y) * u];
}
// K11: der Ring um einen Ort hat zwölf Plätze; ab dem 13. Team sechzehn (22,5°) auf größerem Radius
const ringMass = n => n > 12 ? { plaetze: Math.max(16, n), radius: 150 } : { plaetze: 12, radius: 116 };

/* =====================================================================
   Kapitel (Nachtrag 17.10.): reine Funktion von Daten und Auswahl
   ===================================================================== */
// Zeitraffer: 70 s für das ganze Spiel; die Kamera hat alle 0,5 s einen Stützpunkt, dazwischen linear
const ZR_MS = 70000, ZR_SCHRITT = 500, ZR_B = { x: 0, w: 1920, y: 180, h: 790 };
// Awards: 6 s je Award; das Team springt 1,2 s nach dem Titel auf, die Route zeichnet sich in 2,8 s
const AWARD_MS = 6000, AW_TITEL = 260, AW_TEAM = 1460, AW_ROUTE = 2800, AWARD_B = { x: 1000, w: 920, y: 0, h: 970 };
// Zeitraffer: gleichmäßig, nur am Anfang und am Ende weich (je 5 % der Dauer)
const sanft = (u, a = .05) => u <= 0 ? 0 : u >= 1 ? 1 : (u < a ? u * u / (2 * a) : u > 1 - a ? 1 - a - (1 - u) * (1 - u) / (2 * a) : u - a / 2) / (1 - a);
const kapitelZeit = (k, lokal) => k.von + (k.bis - k.von) * sanft(Math.min(1, lokal / k.dur));
function kapitelFuer(d, opt) {
  const k = [];
  const uebersicht = rahmen([d.start.xy, ...d.stationen.map(s => s.xy), P(50.0925, 14.4170)], 110, 900);
  d.uebersicht = uebersicht;
  const aus = f => opt.aus.has(f.teamId + ":" + f.position);
  const mitFotos = opt.fotos && d.fotos.some(f => !aus(f));
  const halt = opt.anhalten, voll = einpassen(uebersicht, VOLL_B);
  // 1. Splash: der Vorspann steht als Startbild, bis die Spielleitung Weiter drückt (S6)
  k.push(halt ? { id: "vorspann", art: "titel", dur: 3600, halte: [{ t: 3000 }], kam: voll, name: "Vorspann" }
    : { id: "vorspann", art: "titel", dur: 7500, kam: voll, name: "Vorspann" });
  // 2. Fun Facts, 3. die Startgruppen (nur, wenn es mehr als eine gibt)
  // Halt bei 3,6 s: die Brathähnchen stehen, Weiter schaltet von Hand auf Bier um (Friedrich 17.10.), danach Endhalt
  k.push({ id: "fakten", art: "fakten", dur: 7500, halte: [{ t: 3600, springe: true }], name: "Fun Facts", kam: voll });
  // 6,5 s Auftritt, dann der Ausgang: die Teams drehen sich zu "?" und fliegen zum Start (Friedrich 17.10.), zusammen 10 s
  if (new Set(d.teams.map(t => t.gruppe)).size > 1) k.push({ id: "gruppen", art: "gruppen", dur: 10000, name: "Die Gruppen", kam: voll,
    ...(halt ? { halte: [{ t: GR_AUS, springe: true }] } : {}) });   // Halt vor dem Drehen: das Mischen beginnt auf Weiter (Friedrich 17.10.)
  // 4. ein Zeitraffer über das ganze Spiel; die Kamera folgt allen Köpfen und dem Start
  const fertig = d.teams.map(t => t.fertig), alleDa = fertig.length && fertig.every(Boolean);
  const bis = alleDa ? Math.min(d.tEnd, Math.max(...fertig) + 2 * MIN) : d.tEnd;
  const zr = { id: "zeitraffer", art: "karte", dur: ZR_MS, von: d.t0, bis: Math.max(d.t0 + MIN, bis), name: "Zeitraffer" };
  zr.bahn = kameraBahn(zr, d); zr.kam = zr.bahn[0]; zr.kamEnde = zr.bahn[zr.bahn.length - 1];
  zr.schnitt = true;   // harter Schnitt auf die Bahn: der Schleier davor deckt ihn, sonst fährt die Kamera aus der Übersicht
  k.push(zr);
  // 5. Rangliste, Teil 1: die Plätze ab 4 decken sich auf; 6. die Bonusrunde Awards (Friedrich 17.10.: vor der
  // Siegerehrung); 7. Rangliste, Teil 2: die Zeiten der ersten drei rasten ein. S17: ohne ein Team im Ziel gibt es
  // weder Rangliste noch Finale
  const top = [1, 2, 3].slice(0, Math.max(0, Math.min(3, d.prizeCount))).map(p => d.rang.find(t => t.place === p)).filter(Boolean);
  const [rang1, rang2] = top.length ? rangKapitel(d, top.length) : [];
  if (rang1) k.push(rang1);
  // Awards: kurzer Auftakt, dann je Award ein Kapitel, das (wie jedes Kapitel) am Ende auf Weiter wartet
  if (d.awards.length) {
    const kams = d.awards.map(a => einpassen(rahmen([d.start.xy, ...d.stationen.map(s => s.xy), ...a.team.pts.map(p => [p.x, p.y])], 60, 700), AWARD_B, 50));
    k.push({ id: "awards", art: "award", intro: true, dur: 2500, name: "Awards", symbole: d.awards.map(a => a.emo), kam: kams[0] });
    d.awards.forEach((a, n) => k.push({ id: "award" + (n + 1), art: "award", dur: AWARD_MS, name: "Award " + (n + 1), award: a, team: a.team, kam: kams[n] }));
  }
  if (top.length) {
    k.push(rang2);
    // 8. Drei Spalten, 9. Platz 3 aufdecken, 10. Duell: erst Platz 2, dann Platz 1 als eigener, eskalierter Moment;
    // Halt vor und nach jedem Aufdecken
    const sp = spaltenBasis(d, top);
    k.push({ id: "spalten", art: "spalten", dur: 6000, name: top.length === 3 ? "Drei Spalten" : "Die Spalten", sp, offen: [], auf: [] });
    if (top.length >= 3) k.push(aufdeckKapitel("platz3", "Platz 3", sp, [], [{ platz: 3 }]));
    if (top.length >= 2) k.push(aufdeckKapitel("platz2", "Platz 2", sp, top.length >= 3 ? [3] : [], [{ platz: 2 }]));
    k.push(aufdeckKapitel("platz1", "Platz 1", sp, top.filter(t => t.place > 1).map(t => t.place), [{ platz: 1, gross: true }]));
    k.push(halt ? { id: "sieger", art: "sieger", dur: 2600, halte: [{ t: 2300 }], name: "Siegerbild", kam: voll }
      : { id: "sieger", art: "sieger", dur: 9000, name: "Siegerbild", kam: voll });
  }
  // 11. Abspann: läuft ohne Ende, bis die Spielleitung etwas drückt (kein eigenes Schlussbild)
  const schluss = einpassen(rahmen([d.start.xy, ...d.stationen.map(s => s.xy)], 200, 900), { x: 800, w: 1120, y: 0, h: 970 });
  const abFotos = mitFotos ? d.fotos.filter(f => !aus(f)) : [];
  k.push({ id: "abspann", art: "abspann", dur: 20000, endlos: true, name: abFotos.length ? "Abspann" : "Alle Routen", kam: schluss,
    roll: abFotos.length ? { fotos: abFotos, seed: Math.floor(Math.random() * 1e9), bloecke: [], ab: 0 } : null });
  k.forEach((x, i) => { x.i = i; if (!x.kam) x.kam = voll; });
  // Rangliste und Spalten liegen auf dichtem Schleier: die Kamera bleibt stehen, wo das Kapitel davor endete. Das
  // Siegerbild schneidet hart auf die Kamera des Abspanns (unter dem Schleier unsichtbar)
  k.forEach((x, i) => { if (i && ["rangliste", "spalten"].includes(x.art)) x.kam = k[i - 1].art === "award" ? k[i - 1].kam : k[i - 1].kamEnde || k[i - 1].kam;
    if (x.art === "sieger") { x.kam = schluss; x.schnitt = true; } });
  return k;
}
function kapitelBauen() { K = kapitelFuer(D, OPT); }
// Kamera des Zeitraffers: alle Köpfe und der Start im Bild. Nie hektisch: erst die Hülle über ±4 s (die Kamera öffnet
// sich, bevor ein Team an den Rand kommt), dann über ±3 s gemittelt
function kameraBahn(k, d) {
  const n = Math.ceil(k.dur / ZR_SCHRITT), roh = [];
  for (let i = 0; i <= n; i++) { const T = kapitelZeit(k, i * ZR_SCHRITT);
    roh.push(rahmen([d.start.xy, ...d.teams.map(t => kopf(t, T))], 170, 650)); }
  const fenster = (a, w, f) => a.map((_, i) => f(a.slice(Math.max(0, i - w), i + w + 1)));
  const huelle = fenster(roh, 8, w => ({ x0: Math.min(...w.map(r => r.x0)), x1: Math.max(...w.map(r => r.x1)), y0: Math.min(...w.map(r => r.y0)), y1: Math.max(...w.map(r => r.y1)) }));
  const mittel = fenster(huelle, 6, w => { const m = f => w.reduce((a, r) => a + r[f], 0) / w.length; return { x0: m("x0"), x1: m("x1"), y0: m("y0"), y1: m("y1") }; });
  return mittel.map(r => einpassen(r, ZR_B, 30));
}
function bahnBei(k, L) { const f = Math.max(0, Math.min(k.bahn.length - 1, L / ZR_SCHRITT)), i = Math.floor(f), j = Math.min(k.bahn.length - 1, i + 1);
  return kamMisch(k.bahn[i], k.bahn[j], f - i); }
// Gesamtzeit H:MM:SS als fünf Ziffern für die Walzen
const ziffern = t => { const sek = Math.round(t.netto / 1000); return `${Math.min(9, Math.floor(sek / 3600))}${String(Math.floor(sek / 60) % 60).padStart(2, "0")}${String(sek % 60).padStart(2, "0")}`; };
// Rangliste in drei Klicks (Friedrich 17.10.): 1) alle Zeiten rattern, nichts ist aufgedeckt (Halt); 2) Weiter deckt die
// Plätze ab 4 von unten nach oben auf, Zeit einrasten und "?" wird zum Team, unten schneller (0,6 s), oben langsamer
// (1,3 s) (Halt); 3) Weiter lässt die Zeiten von Platz 3, 2, 1 einrasten (Platz 1 mit langsamer letzter Walze), die Teams
// bleiben verdeckt; am Ende geht Weiter zu den Spalten
function rangKapitel(d, top) {
  const zeilen = d.rang, plan = {};
  const rast = (ab, art) => [0, 1, 2, 3, 4].map(j => ({ ab: ab + j * (art ? 200 : 90) + (art === 2 && j === 4 ? 300 : 0), dauer: art === 2 && j === 4 ? 1100 : art ? 600 : 380 }));
  const unten = zeilen.filter(t => !t.place || t.place > top).reverse();
  const halt1 = 1900;
  let t = halt1 + 1100;   // die erste Walze rastet 760 ms vor dem Aufdecken ein: erst nach dem Halt, sonst stünde sie schon davor
  unten.forEach((tm, i) => { const u = unten.length > 1 ? i / (unten.length - 1) : 1;
    plan[tm.id] = { rast: tm.place ? rast(t - 760) : null, auf: t }; t += 600 + 700 * u; });
  const halt2 = t + 1500;   // der letzte Aufdeck-Schritt ist bis zum Ende von Teil 1 ganz fertig (Teil 2 setzt 500 ms früher an)
  t = halt2 + 400;
  for (let pl = top; pl >= 1; pl--) { const tm = zeilen.find(x => x.place === pl); plan[tm.id] = { rast: rast(t, pl === 1 ? 2 : 1), auf: null }; t += 1100; }
  const erster = zeilen.find(x => x.place === 1), ende = t + 900;
  // Teil 1 endet nach dem Aufdecken bis Platz 4 (Endhalt, danach die Awards); Teil 2 beginnt mit allen Plätzen ab 4
  // schon aufgedeckt (versatz = Zeit am Ende von Teil 1), die Zeiten der ersten drei rattern und warten auf Weiter
  return [{ id: "rangliste", art: "rangliste", name: "Rangliste", zeilen, plan, top, erster, dur: halt2, halte: [{ t: halt1, springe: true }] },
    // Regel: kein Halt vor dem Ende des Einblendens (Liste bis 650 ms); Halt bei 800, erstes Einrasten bei 900, die Walzen
    // drehen im Halt weiter
    { id: "rangliste2", art: "rangliste", name: "Rangliste, die ersten drei", zeilen, plan, top, erster, versatz: halt2 - 500, dur: ende - halt2 + 500,
      halte: [{ t: 800, springe: true }] }];
}
// Drei Spalten: Reihenfolge wie das Podest (2, 1, 3), ein gemeinsamer Kartenausschnitt für alle drei Wege (540 x 290)
function spaltenBasis(d, top) {
  const folge = [2, 1, 3].map(p => top.find(t => t.place === p)).filter(Boolean), W = 540, H = 290;
  const r = rahmen([d.start.xy, ...d.stationen.map(s => s.xy), ...top.flatMap(t => t.pts.map(q => [q.x, q.y]))], 70, 600);
  let w = r.x1 - r.x0, h = r.y1 - r.y0;
  if (w / h > W / H) { const nh = w * H / W; r.y0 -= (nh - h) / 2; h = nh; } else { const nw = h * W / H; r.x0 -= (nw - w) / 2; w = nw; }
  const sc = W / w;
  return { folge, r, sc, px: q => [(q[0] - r.x0) * sc, (q[1] - r.y0) * sc] };
}
// Ein Aufdeck-Kapitel: Vorlauf, Halt (vor), Weiter, Spannung, das Team fliegt in seine Spalte, Aufdecken, Halt (nach,
// Kofferübergabe, M1). sperren: dort wirken Weiter und Zurück nicht (M2)
function aufdeckKapitel(id, name, sp, offen, auf) {
  const halte = [{ t: 1000, art: "vor", springe: true }], sperren = [];
  let t = 1000;
  auf.forEach((a, i) => {
    a.ab = t; a.enth = t + (a.gross ? 2600 : i ? 1000 : 1300);
    sperren.push([a.ab, a.enth + 1500]);
    t = a.enth + (a.gross ? 4200 : 2600);
    halte.push({ t, art: "nach", springe: true });
  });
  return { id, art: "spalten", name, sp, offen, auf, halte, sperren, dur: t + 300 };
}

/* =====================================================================
   Zeichnen
   ===================================================================== */
const NS = "http://www.w3.org/2000/svg";
const el = (tag, attr = {}, kind) => { const e = document.createElementNS(NS, tag); for (const a in attr) e.setAttribute(a, attr[a]); if (kind) kind.appendChild(e); return e; };
const pfad = pts => pts.map((p, i) => (i ? "L" : "M") + p[0].toFixed(1) + " " + p[1].toFixed(1)).join("");
const LOGO = `<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" stroke-width="1.8"/><g class="nadel" style="transform-origin:12px 12px"><polygon points="12,4.5 15.2,12 12,10.6 8.8,12" fill="var(--flag)"/><polygon points="12,19.5 8.8,12 12,13.4 15.2,12" fill="currentColor" opacity=".55"/></g></svg>`;
const HAUS = "M-9 2 0-6l9 8M-7 1v9h14V1M-2 10V5h4v5";

/* ---------- Grundkarte ---------- */
// Die echte Karte von Prag aus OpenStreetMap (rueckblick-karte.js, erzeugt von tools/rueckblick/karte.py) in den Farben
// der Stadtjagd. Fehlt die Datei, bleibt die Ausweichlösung: Papier mit Höhenlinien, darauf Stationen, Start und Spuren.
function grundkarte() {
  const g = $("#rb-grund"), alt = g.querySelector("image.karte");
  if (alt && alt.dataset.url) URL.revokeObjectURL(alt.dataset.url);
  g.innerHTML = "";
  el("rect", { x: -6000, y: -6000, width: 12000, height: 12000, fill: "var(--paper)" }, g);
  D.namen = [["Letná", 50.0972, 14.4140, "ortsname"], ["Stromovka", 50.1083, 14.4135, "ortsname"], ["Holešovice", 50.1006, 14.4400, "ortsname"],
    ["Výstaviště", 50.1072, 14.4325, "ortsname"], ["Vltava", 50.0921, 14.4215, "flussname"]];
  const KA = window.PRAG_KARTE;
  D.hatKarte = !!(KA && KA.lat0 === LAT0 && KA.lng0 === LNG0);
  D.osmQuelle = D.hatKarte ? KA.quelle : null;
  D.karteFertig = false;
  if (D.hatKarte) {
    for (const lage of ["gruen", "park", "wasser", "flusslinie", "gebaeude", "weg", "bahn"]) if (KA.lagen[lage]) el("path", { class: lage, d: KA.lagen[lage] }, g);
    if (KA.lagen.neben) { el("path", { class: "strasse-r", d: KA.lagen.neben, style: "stroke-width:6" }, g); el("path", { class: "neben", d: KA.lagen.neben }, g); }
    if (KA.lagen.haupt) { el("path", { class: "strasse-r", d: KA.lagen.haupt }, g); el("path", { class: "strasse", d: KA.lagen.haupt }, g); }
    return;
  }
  const ring = (lat, lng, rx, ry, wob) => { const c = P(lat, lng), pts = [];
    for (let a = 0; a < 64; a++) { const w = a / 64 * Math.PI * 2, f = 1 + Math.sin(w * 3 + wob) * .08 + Math.sin(w * 5 + wob * 2) * .05;
      pts.push([c[0] + Math.cos(w) * rx * f, c[1] + Math.sin(w) * ry * f]); } return pfad(pts) + "Z"; };
  for (let i = 0; i < 6; i++) el("path", { class: "hoehe", d: ring(50.0972, 14.4195, 1050 - i * 150, 330 - i * 48, i * .7) }, g);
  for (let i = 0; i < 3; i++) el("path", { class: "hoehe", d: ring(50.1112, 14.4060, 700 - i * 170, 300 - i * 70, 2 + i) }, g);
}

/* Die echte Karte hat tausende Formen; neu gezeichnet bei jeder Kamerabewegung ruckelt sie (gemessen 16.10.: 3 bis 5
   statt 55 Bilder pro Sekunde). Darum wird sie beim Vorbereiten einmal als Bild gerendert, in den aktuellen Farben,
   und die Kamera verschiebt nur noch dieses Bild. Routen, Stationen und Namen bleiben Vektor darüber. Beim Wechsel
   hell/dunkel bleibt das alte Bild stehen, bis das neue fertig ist (S13). */
let rasterNr = 0;
function karteRastern() {
  const KA = window.PRAG_KARTE; if (!KA || !D || !D.hatKarte) return Promise.resolve(false);
  return new Promise(fertig => {
    const nr = ++rasterNr, css = getComputedStyle(root), f = n => css.getPropertyValue(n).trim();
    const aktuell = () => nr === rasterNr && !!root && !!D;   // K3: nach beenden() nichts mehr anfassen
    // Ausschnitt: alles, was irgendeine Kamera der Show zeigt (Vereinigung der Sichtfenster), plus 250 m Rand
    const fenster = K.flatMap(k => [k.kam, ...(k.bahn || [])]).filter(Boolean)
      .map(c => ({ x0: c.cx - 960 / c.s, x1: c.cx + 960 / c.s, y0: c.cy - 540 / c.s, y1: c.cy + 540 / c.s }));
    const pkt = [D.start.xy, ...D.stationen.map(x => x.xy)].filter(Boolean);
    fenster.push({ x0: Math.min(...pkt.map(q => q[0])) - 900, x1: Math.max(...pkt.map(q => q[0])) + 900,
                   y0: Math.min(...pkt.map(q => q[1])) - 900, y1: Math.max(...pkt.map(q => q[1])) + 900 });
    const x0 = Math.min(...fenster.map(r => r.x0)) - 250, x1 = Math.max(...fenster.map(r => r.x1)) + 250;
    const y0 = Math.min(...fenster.map(r => r.y0)) - 250, y1 = Math.max(...fenster.map(r => r.y1)) + 250;
    const w = x1 - x0, h = y1 - y0, res = Math.min(1.6, 5000 / Math.max(w, h)), W = Math.round(w * res), H = Math.round(h * res);
    const px = n => (n / res).toFixed(3);   // Linienbreiten in Bildschirm-Pixeln des Bildes, umgerechnet in Meter
    const lage = (name, attr) => KA.lagen[name] ? `<path d="${KA.lagen[name]}" ${attr}/>` : "";
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${x0} ${y0} ${w} ${h}" width="${W}" height="${H}">
      <rect x="${x0}" y="${y0}" width="${w}" height="${h}" fill="${f("--paper")}"/>
      ${lage("gruen", `fill="${f("--gruen")}"`)}${lage("park", `fill="${f("--park")}"`)}${lage("wasser", `fill="${f("--fluss")}"`)}
      ${lage("flusslinie", `fill="none" stroke="${f("--fluss")}" stroke-width="${px(4)}"`)}
      ${lage("gebaeude", `fill="${f("--haus")}" stroke="${f("--haus-rand")}" stroke-width="${px(.8)}"`)}
      ${lage("weg", `fill="none" stroke="${f("--feld")}" stroke-opacity=".55" stroke-width="${px(1.4)}" stroke-dasharray="${px(6)} ${px(7)}"`)}
      ${lage("bahn", `fill="none" stroke="${f("--feld")}" stroke-opacity=".6" stroke-width="${px(2)}" stroke-dasharray="${px(10)} ${px(6)}"`)}
      ${lage("neben", `fill="none" stroke="${f("--strasse-rand")}" stroke-width="${px(6)}" stroke-linecap="round" stroke-linejoin="round"`)}
      ${lage("neben", `fill="none" stroke="${f("--strasse")}" stroke-width="${px(3)}" stroke-linecap="round" stroke-linejoin="round"`)}
      ${lage("haupt", `fill="none" stroke="${f("--strasse-rand")}" stroke-width="${px(9)}" stroke-linecap="round" stroke-linejoin="round"`)}
      ${lage("haupt", `fill="none" stroke="${f("--strasse")}" stroke-width="${px(6)}" stroke-linecap="round" stroke-linejoin="round"`)}</svg>`;
    const url = URL.createObjectURL(new Blob([svg], { type: "image/svg+xml" })), img = new Image();
    img.onload = () => {
      URL.revokeObjectURL(url);
      if (!aktuell()) { fertig(false); return; }
      const c = document.createElement("canvas"); c.width = W; c.height = H;
      c.getContext("2d").drawImage(img, 0, 0, W, H);
      c.toBlob(b => {
        if (!aktuell() || !b) { fertig(false); return; }
        const g = $("#rb-grund"), alt = g.querySelector("image.karte");
        [...g.children].forEach(e => { if (e.tagName !== "rect") e.remove(); });   // Vektor-Ersatz weg, nur noch das Bild
        if (alt && alt.dataset.url) URL.revokeObjectURL(alt.dataset.url);
        const bu = URL.createObjectURL(b);
        const im = el("image", { class: "karte", href: bu, x: x0, y: y0, width: w, height: h, preserveAspectRatio: "none" }, g);
        im.dataset.url = bu; D.karteFertig = true;
        root.querySelectorAll("image.mkarte").forEach(m => m.setAttribute("href", bu));   // kleine Karten der Spalten
        letzteKarte = null;
        fertig(true);
      }, "image/png");
    };
    img.onerror = () => { URL.revokeObjectURL(url); fertig(false); };
    img.src = url;
    setTimeout(() => fertig(false), 15000);
  });
}

let radEl = [], teamEl = {}, kopfEl = {}, ankerEl = {}, stEl = [], namenEl = [];
function kartenElemente() {
  letzteKarte = null;
  const sp = $("#rb-spuren"); sp.innerHTML = ""; teamEl = {};
  radEl = D.stationen.filter(s => s.xy).map(s => ({ s, e: el("circle", { class: "radius", cx: s.xy[0], cy: s.xy[1], r: s.radiusM || 50, style: "opacity:0" }, sp) }));
  D.teams.forEach(t => {
    const g = el("g", {}, sp);
    // Spur in Stücken zu je STUECK Punkten: fertige Stücke bleiben stehen, je Bild wird nur das letzte neu gesetzt
    teamEl[t.id] = { g, rand: el("g", {}, g), luecke: el("g", { stroke: t.farbe }, g), spur: el("g", { stroke: t.farbe }, g), stuecke: [] };
  });
  linienFarben();
  const sg = $("#rb-stationen"); sg.innerHTML = ""; stEl = [];
  const startG = el("g", {}, sg); el("circle", { class: "startbadge", r: 28 }, startG); el("path", { class: "haus", d: HAUS }, startG);
  stEl.push({ g: startG, xy: D.start.xy });
  D.stationen.filter(s => s.xy).forEach(s => { const g = el("g", {}, sg); el("circle", { class: "stbadge", r: 28 }, g);
    const tx = el("text", { class: "stnr", "text-anchor": "middle", y: 11 }, g); tx.textContent = s.position; stEl.push({ g, xy: s.xy }); });
  const kg = $("#rb-koepfe"); kg.innerHTML = ""; kopfEl = {};
  // Ankerlinien (17.10.): im Ring verbindet eine gepunktete Linie jeden Kopf mit dem Ort; sie liegen unter den Abzeichen
  const ag = $("#rb-anker"); ag.innerHTML = ""; ankerEl = {};
  D.teams.forEach(t => { ankerEl[t.id] = el("line", { class: "anker" }, ag); });
  D.teams.forEach(t => { const g = el("g", { class: "kopf" }, kg);
    el("circle", { class: "k", r: 30, fill: t.farbe }, g);
    const tx = el("text", { class: "tier", "text-anchor": "middle", y: 12 }, g); tx.textContent = t.emoji;
    const fr = el("text", { class: "frage", "text-anchor": "middle", y: 13 }, g); fr.textContent = "?"; kopfEl[t.id] = g; });
  const ng = $("#rb-namen"); ng.innerHTML = ""; namenEl = D.namen.map(n => { const tx = el("text", { class: n[3], "text-anchor": "middle" }, ng); tx.textContent = n[0]; return { tx, xy: P(n[1], n[2]) }; });
}

// S18: im dunklen Thema die Linien heller, sonst versinken Indigo, Petrol, Oliv und Magenta in der Karte
const istDunkel = () => { const t = document.documentElement.dataset.theme; return t ? t === "dark" : matchMedia("(prefers-color-scheme: dark)").matches; };
const linie = t => istDunkel() ? mischen(t.farbe, "#FFFFFF", .35) : t.farbe;
function linienFarben() {
  D.teams.forEach(t => { const e = teamEl[t.id]; if (!e) return; e.spur.setAttribute("stroke", linie(t)); e.luecke.setAttribute("stroke", linie(t)); });
}
// Ankunftsreihenfolge je Ort für die Ringplätze (Start: Teamreihenfolge). S3: an der letzten Station ebenfalls
// Teamreihenfolge, sonst liest man dort die Zielreihenfolge ab.
function ringPlatz(team, ortIdx) {
  if (ortIdx === 0 || ortIdx === D.stationen.length) return D.teams.indexOf(team);
  const pos = D.stationen[ortIdx - 1].position;
  const rf = D.teams.map(t => ({ t, e: (t.sts.find(x => x.position === pos) || {}).ein || Infinity })).sort((a, b) => a.e - b.e);
  return rf.findIndex(x => x.t === team);
}
let ringCache = {}, letzteKarte = null, kartenZaehler = 0, kopfPos = {};
function zeichneKarte(T, kam, modus) {
  // modus: { spuren: "alle" | "keine" | Team, koepfe: bool oder Team, bis: Zeit für eine einzelne Spur }
  // Steht alles still (Abspann, Siegerbild), nichts neu zeichnen: das kostete die Hälfte der Bildrate (gemessen 16.10.)
  const sp = modus.spuren && modus.spuren.id ? modus.spuren.id : modus.spuren;
  const einzeln = modus.koepfe && modus.koepfe.id ? modus.koepfe : null;
  const schluessel = [Math.round(T), kam.cx.toFixed(2), kam.cy.toFixed(2), kam.s.toFixed(5), sp, einzeln ? "k" + einzeln.id : modus.koepfe, modus.bis == null ? "" : Math.round(modus.bis), Z.szene && Z.szene.dataset.k].join("|");
  if (schluessel === letzteKarte) return;
  letzteKarte = schluessel; kartenZaehler++;
  const s = kam.s, vw = 1920 / s, vh = 1080 / s, vx = kam.cx - vw / 2, vy = kam.cy - vh / 2;
  $("#rb-welt").setAttribute("viewBox", `${vx.toFixed(2)} ${vy.toFixed(2)} ${vw.toFixed(2)} ${vh.toFixed(2)}`);
  // Quellenhinweis (ODbL) nur im Abspann, klein unten rechts (Entscheidung Friedrich 16.10.: sonst zu präsent)
  const osm = $("#rb-osm"); if (osm) osm.hidden = !(D.osmQuelle && K[Z.i] && K[Z.i].id === "abspann" && Z.phase === "show");
  const sx = p => [(p[0] - vx) * s, (p[1] - vy) * s];
  // Marken und Ortsnamen nur, solange sie ganz im Bild stehen: kein halber Name am Rand, keiner außerhalb der Bühne
  stEl.forEach(e => { const q = sx(e.xy); e.g.setAttribute("transform", `translate(${q[0].toFixed(1)} ${q[1].toFixed(1)})`);
    const weg = q[0] < 32 || q[0] > 1888 || q[1] < 32 || q[1] > 1048 ? "none" : ""; if (e.g.style.display !== weg) e.g.style.display = weg; });
  namenEl.forEach(n => { const q = sx(n.xy); n.tx.setAttribute("x", q[0].toFixed(0)); n.tx.setAttribute("y", q[1].toFixed(0));
    const weg = q[0] < 90 || q[0] > 1830 || q[1] < 60 || q[1] > 1020 ? "none" : ""; if (n.tx.style.display !== weg) n.tx.style.display = weg; });
  D.teams.forEach(t => {
    const e = teamEl[t.id], zeigen = modus.spuren === "alle" || modus.spuren === t;
    const anz = zeigen ? "" : "none"; if (e.g.style.display !== anz) e.g.style.display = anz;
    if (!zeigen) return;
    const bis = modus.spuren === t && modus.bis != null ? modus.bis : T;
    // Bewegt sich nur die Kamera, bleibt die Spur gleich (Meter-Koordinaten): nicht neu bauen, das kostete Bilder
    if (e.bis === Math.round(bis)) return;
    e.bis = Math.round(bis);
    spurSetzen(t, e, bis);
  });
  // Köpfe: an einem Ort stehen die Teams im Ring, in der Reihenfolge ihrer Ankunft
  const orte = [D.start.xy, ...D.stationen.map(x => x.xy)], ring = ringMass(D.teams.length);
  // Der Check-in-Umkreis einer Station erscheint nur, solange ein Team in der Nähe ist (Friedrich 17.10.: kein Überbleibsel)
  radEl.forEach(({ s: st, e: r }) => {
    const da = (modus.koepfe || einzeln) && D.teams.some(t => { if (einzeln && t !== einzeln) return false;
      const h = kopf(t, einzeln ? modus.bis ?? T : T); return h && dist(h, st.xy) < (st.radiusM || 50) * 2.4; });
    const o = da ? "1" : "0"; if (r.style.opacity !== o) r.style.opacity = o; });
  const kk = K[Z.i], zr = kk && kk.art === "karte", tempo = zr ? Math.max(1, (kk.bis - kk.von) / kk.dur) : 1;
  D.teams.forEach(t => {
    const g = kopfEl[t.id], h = einzeln ? (einzeln === t ? kopf(t, modus.bis ?? T) : null) : modus.koepfe ? kopf(t, T) : null;
    const an = ankerEl[t.id];
    if (!h) { if (g.style.display !== "none") g.style.display = "none"; kopfPos[t.id] = null; if (an.style.opacity !== "0") an.style.opacity = "0"; return; }
    if (g.style.display) g.style.display = "";
    if (g.style.opacity) g.style.opacity = "";   // die Awards blenden das Teamsymbol aus
    let best = 0, bd = Infinity; orte.forEach((o, i) => { const dd = o ? dist(o, h) : Infinity; if (dd < bd) { bd = dd; best = i; } });
    let q = sx(h);
    const w = einzeln ? 0 : glatt((70 - bd) / 45);
    if (w > 0) {
      const key = t.id + ":" + best, platz = ringCache[key] ?? (ringCache[key] = ringPlatz(t, best));
      const a = -Math.PI / 2 + platz * (Math.PI * 2 / ring.plaetze), o = sx(orte[best]);
      const z = [o[0] + Math.cos(a) * ring.radius, o[1] + Math.sin(a) * ring.radius];
      q = [q[0] + (z[0] - q[0]) * w, q[1] + (z[1] - q[1]) * w];
      // die Linie beginnt am Rand des Abzeichens (38 px) und endet am Rand des Kopfes (32 px)
      const dl = Math.hypot(q[0] - o[0], q[1] - o[1]) || 1, ux = (q[0] - o[0]) / dl, uy = (q[1] - o[1]) / dl;
      an.setAttribute("x1", (o[0] + ux * 38).toFixed(1)); an.setAttribute("y1", (o[1] + uy * 38).toFixed(1));
      an.setAttribute("x2", (q[0] - ux * 32).toFixed(1)); an.setAttribute("y2", (q[1] - uy * 32).toFixed(1));
      an.style.opacity = dl > 75 ? w.toFixed(2) : "0";
    } else if (an.style.opacity !== "0") an.style.opacity = "0";
    // Station gelöst: der Kopf springt kurz auf (1,4 s Kapitelzeit nach dem Lösen), der Ring dazu kommt aus pulse()
    const geloest = !ruhig && zr ? t.sts.map(x => x.ok).filter(o => o && o <= T).pop() : null;
    const u = geloest ? (T - geloest) / tempo / 1400 : 1, hoch = u < 1 ? 1 + .45 * Math.sin(Math.PI * Math.min(1, u * 1.6)) * (1 - u) : 1;
    kopfPos[t.id] = u < 1 ? { q, u } : null;
    g.setAttribute("transform", `translate(${q[0].toFixed(1)} ${q[1].toFixed(1)})${hoch !== 1 ? ` scale(${hoch.toFixed(3)})` : ""}`);
  });
}
// Gemessen 17.10.: die ganze Spur je Bild neu zu bauen kostete im langen Zeitraffer Bilder; in Stücken bleibt die Arbeit
// je Bild klein (höchstens STUECK Punkte je Team). Kurze Stücke auch, weil lange, breite Linien mit vielen Ecken (der
// weiße Rand) bei jeder Kamerafahrt teuer neu zu zeichnen sind: mit 48 Punkten je Stück und spärlichen Punkten (einer je
// Minute) 31 bis 41 Bilder pro Sekunde, mit 16 wieder 60 (gemessen 17.10., rueckblick.py Gruppe 13)
const STUECK = 16;
function spurSetzen(t, e, bis) {
  const p = t.pts, j = kopfIdx(p, bis), n = j < 0 ? 0 : Math.max(1, Math.ceil(j / STUECK)), xy = i => p[i].x.toFixed(1) + " " + p[i].y.toFixed(1);
  while (e.stuecke.length < n) e.stuecke.push({ rand: el("path", { class: "rand" }, e.rand), luecke: el("path", { class: "luecke" }, e.luecke), spur: el("path", { class: "spur" }, e.spur), key: "" });
  e.stuecke.forEach((st, c) => {
    if (c >= n) { if (st.key) { st.key = ""; st.spur.setAttribute("d", ""); st.rand.setAttribute("d", ""); st.luecke.setAttribute("d", ""); } return; }
    const a = c * STUECK, b = c === n - 1 ? j : (c + 1) * STUECK, h = c === n - 1 && j < p.length - 1 ? kopf(t, bis) : null;
    const key = b + (h ? ":" + h[0].toFixed(1) + "," + h[1].toFixed(1) : "");
    if (st.key === key) return;
    st.key = key;
    let fest = "M" + xy(a), luecke = "";
    for (let i = a + 1; i <= b; i++) { if (p[i].g) { luecke += "M" + xy(i - 1) + "L" + xy(i); fest += "M" + xy(i); } else fest += "L" + xy(i); }
    if (h) { const cc = h[0].toFixed(1) + " " + h[1].toFixed(1); if (p[j + 1].g) luecke += "M" + xy(j) + "L" + cc; else fest += "L" + cc; }
    st.spur.setAttribute("d", fest); st.rand.setAttribute("d", fest); st.luecke.setAttribute("d", luecke);
  });
}

/* =====================================================================
   Ablauf: Kapitel, Zeit, Pause, Halt vor und nach dem Aufdecken
   ===================================================================== */
// hNr: Index des nächsten Haltepunkts im Kapitel (k.halte); extra: Zeit im ersten Halt (die Walzen drehen weiter)
const Z = { endHalt: false, phase: "laden", i: 0, lokal: 0, spielt: false, haelt: false, hNr: 0, extra: 0, letzt: 0, wechsel: 0, vorSchwarz: false, vorFrage: false, szene: null, alt: null };
// Die Show läuft für das Publikum, nicht für den Laptop: Bewegung ist an, auch wenn der Rechner "reduzierte Bewegung"
// meldet (16.10.: Friedrichs Chrome meldete es, die Show stand still). Abschalten nur bewusst im Vorbereiten.
const systemRuhig = matchMedia("(prefers-reduced-motion: reduce)").matches;
let ruhig = false;
function kamFuer(i, lokal) {
  const k = K[i], ziel = k.bahn ? bahnBei(k, lokal) : k.kam, vorher = i > 0 ? (K[i - 1].kamEnde || K[i - 1].kam) : ziel;
  return ruhig || k.schnitt ? ziel : kamMisch(vorher, ziel, glatt(lokal / 1800));
}
const KAP_KEY = "sj.rb.kapitel";   // M5: Kapitel merken, nach dem Neuladen "Weiter bei …"
function geheZu(i, lokal = 0) {
  i = Math.max(0, Math.min(K.length - 1, i));
  const h = K[i].halte || [];
  Z.phase = "show"; Z.i = i; Z.lokal = lokal; Z.extra = 0; Z.wechsel = performance.now(); Z.endHalt = false;
  Z.hNr = h.filter(x => x.t < lokal).length;
  Z.haelt = OPT.anhalten && h.some(x => x.t === lokal);   // Sprung genau auf einen Halt (Prüfungen, Weiter bei)
  try { sessionStorage.setItem(KAP_KEY, JSON.stringify({ id: K[i].id, modus })); } catch { /* dann ohne "Weiter bei" */ }
  szeneBauen();
  zeichnen();
}
const startbar = () => !!D && (Z.phase === "vorbereiten" || Z.phase === "show");
// der endlose Abspann hat kein Ende: dort schaltet die Leertaste Pause und weiter
const amEnde = () => Z.phase === "show" && Z.i === K.length - 1 && !K[Z.i].endlos && Z.lokal >= K[Z.i].dur;
// M2: zwischen Weiter am Halt und Aufdecken + 1,5 s wirken Weiter und Zurück nicht (prellender Klicker, Doppelklick)
function gesperrt() { const k = K[Z.i]; return Z.phase === "show" && !!k.sperren && !Z.haelt && k.sperren.some(([a, b]) => Z.lokal >= a && Z.lokal < b); }
function weiter() {
  if (!startbar() || frageOffen()) return;   // M8: aus dem Durchsehen startet nichts
  if (Z.phase !== "show") return starten();
  // M2: Weiter in den ersten 600 ms nach einem Kapitelwechsel verwerfen; S11: nach dem Abspann tut Weiter nichts
  if (performance.now() - Z.wechsel < 600 || gesperrt() || amEnde()) return;
  const k = K[Z.i], h = OPT.anhalten && k.halte && k.halte[Z.hNr];
  Z.spielt = true; knopf();   // M3: Weiter setzt fort, auch aus der Pause und nach dem Schwarzbild
  if (Z.haelt) {
    Z.haelt = false; Z.hNr++;
    // der letzte Halt kurz vor dem Ende (Splash, nach dem Aufdecken, Rangliste, Siegerbild): gleich ins nächste Kapitel,
    // sonst bräuchte es nach dem Endhalt ein zweites Weiter
    if (Z.hNr >= k.halte.length && k.dur - Z.lokal <= 700 && Z.i < K.length - 1) return geheZu(Z.i + 1);
    leisteFortschritt(); return;
  }
  if (Z.endHalt) { if (Z.i < K.length - 1) geheZu(Z.i + 1); return; }   // Kapitel zu Ende gespielt: Weiter geht ins nächste
  // M2: zu frühes Weiter springt auf den nächsten Halt, statt den Platz zu überspringen (ein prellender zweiter Druck
  // deckt dann nicht gleich auf: dieselbe 600-ms-Sperre wie nach einem Kapitelwechsel)
  if (h && h.springe && Z.lokal < h.t) { Z.lokal = h.t; Z.haelt = true; Z.wechsel = performance.now(); leisteFortschritt(); return; }
  if (Z.i < K.length - 1) geheZu(Z.i + 1);
}
function zurueck() {
  if (Z.phase !== "show" || gesperrt() || frageOffen()) return;
  Z.spielt = true; knopf();   // M3
  if (Z.lokal > 1500) geheZu(Z.i); else geheZu(Z.i - 1);
}
function spielPause(perTaste) {
  if (!startbar() || frageOffen()) return;
  if (Z.phase !== "show") return starten();
  if (Z.haelt || Z.endHalt) return weiter();
  if (amEnde()) return;
  Z.spielt = !Z.spielt; knopf();
  // S9: pausiert bleibt die Leiste stehen; per Taste fortgesetzt ist sie sofort weg
  if (!Z.spielt) leisteZeigen(); else if (perTaste === true) leisteWeg(); else leisteZeigen();
  leisteFortschritt();
}
// M8: Starten baut die Kapitel immer neu (Fotoauswahl, Haltepunkte, Mischung des Abspanns)
function starten(id, lokal = 0) {
  if (!D) return;
  kapitelBauen(); $("#rb-ueber").innerHTML = ""; Z.spielt = true;
  let i = id ? K.findIndex(x => x.id === id) : 0; if (i < 0) i = 0;
  const k = K[i], l = lokal === "nach" ? (k.halte ? k.halte[k.halte.length - 1].t : k.dur) : lokal === "ende" ? k.dur : lokal;
  geheZu(i, l); knopf();
}
function knopf() { const b = $("#rb-bSpiel"); b.querySelector("span").textContent = Z.phase !== "show" ? "Start" : Z.spielt ? "Pause" : "Abspielen";
  b.querySelector("svg").innerHTML = Z.spielt && Z.phase === "show" ? '<path d="M6 4h4v16H6zM14 4h4v16h-4z"/>' : '<path d="M7 4v16l13-8z"/>'; }

function takt(jetzt) {
  if (!root) return;
  const dt = Math.min(100, jetzt - (Z.letzt || jetzt)); Z.letzt = jetzt;
  if (Z.phase === "show") {
    const k = K[Z.i];
    if (Z.spielt) {
      const h = OPT.anhalten && k.halte && k.halte[Z.hNr];
      if (!Z.haelt && h && Z.lokal < h.t && Z.lokal + dt >= h.t) { Z.lokal = h.t; Z.haelt = true; }
      // die Walzen drehen im Halt weiter: im ersten Halt jedes Kapitels, in der Rangliste in jedem
      if (Z.haelt) { if (Z.hNr === 0 || k.art === "rangliste") Z.extra += dt; } else Z.lokal += dt;
      // nichts läuft von selbst durch (Friedrich 17.10.): das Kapitel hält am Ende, bis Weiter kommt
      if (Z.lokal >= k.dur && !k.endlos) { Z.lokal = k.dur; if (!Z.endHalt) { Z.endHalt = true; leisteFortschritt(); } }
    }
    zeichnen();
  }
  rafId = requestAnimationFrame(takt);
}

/* ---------- Szenen ---------- */
const BREITE = 1920;
function szeneBauen() {
  const k = K[Z.i], box = $("#rb-szenen");
  if (Z.alt) Z.alt.remove();
  Z.alt = Z.szene; if (Z.alt) Z.alt.style.zIndex = 1;
  const s = document.createElement("div"); s.className = "szene"; s.style.zIndex = 2; s.dataset.k = k.id;
  const html = { titel: vorspannHTML, fakten: faktenHTML, gruppen: gruppenHTML, karte: zrHTML, award: awardHTML,
    rangliste: rangHTML, spalten: spaltenHTML, sieger: siegerHTML, abspann: abspannHTML }[k.art];
  if (html) s.innerHTML = html(k);
  box.appendChild(s); Z.szene = s; Z.altBis = 520; Z.szeneAb = performance.now(); $("#rb-buehne").dataset.art = k.art;
  k.el = elemente(k, s);
  ringCache = {}; letzteKarte = null;
  leisteSpur();
}
// Mittelpunkt eines Elements in Bühnen-Pixeln (die Bühne ist skaliert)
function mitteAufBuehne(x) { const B = $("#rb-buehne").getBoundingClientRect(), r = x.getBoundingClientRect(), sk = B.width / 1920;
  return [(r.left + r.width / 2 - B.left) / sk, (r.top + r.height / 2 - B.top) / sk]; }
// Einmal je Szene die Teile suchen, die zeichnen() je Bild setzt
function elemente(k, s) {
  const q = x => s.querySelector(x), qa = x => [...s.querySelectorAll(x)];
  if (k.art === "award") return k.intro ? { klein: q("small"), titel: q("h2"), symbole: qa(".aw-reihe span") }
    : { emo: q(".aw-emo"), titel: q(".aw-titel"), wert: q(".aw-wert"), team: q(".aw-team"), kreis: q(".aw-team .b") };
  if (k.art === "karte") return { kopf: q(".zr-kopf"), uhr: q(".zr-uhr"), ziel: q(".zr-ziel") };
  if (k.art === "fakten") return { kopf: q(".ff-kopf"), kacheln: qa(".ff-netz > div"), lagen: qa(".ff-lagen").map(x => [...x.children].map(e => ({ el: e, b: e.querySelector("b") }))) };
  if (k.art === "gruppen") return { kopf: q(".ff-kopf"), spalten: qa(".gr-spalte"), teams: qa(".gr-spalte").map(x => [...x.querySelectorAll(".gr-team")]) };
  if (k.art === "rangliste") return { kopf: q(".rl-kopf"), netz: q(".rl-netz"), zeilen: qa(".rl-zeile").map((row, i) => {
    const t = k.zeilen[i]; return { row, i, t, fr: row.querySelector(".fr"), ti: row.querySelector(".ti"), n: row.querySelector(".n"),
      baender: [...row.querySelectorAll(".band")], z: t.place ? ziffern(t) : "", st: null, dif: row.querySelector(".dif") }; }) };
  if (k.art === "spalten") return { toen: q(".sp-toen"), spalten: qa(".sp-spalte").map(c => {
    const t = k.sp.folge.find(x => x.place === +c.dataset.p), grau = c.querySelector(".grau");
    return { el: c, t, grau, len: grau.getTotalLength() || 1, farbe: c.querySelector(".farbe"), kopf: c.querySelector(".mk"), mkt: c.querySelector(".mkt"),
      fr: c.querySelector(".sp-kreis .fr"), ti: c.querySelector(".sp-kreis .ti"), n: c.querySelector(".sp-team .n"), m: c.querySelector(".sp-m"),
      blitz: c.querySelector(".sp-blitz"), ringe: [...c.querySelectorAll(".sp-ring")], ziel: mitteAufBuehne(c.querySelector(".sp-kreis")) }; }),
    rest: qa(".sp-rest").map(e => ({ el: e, t: k.rest.find(t => t.place === +e.dataset.p), name: e.querySelector("span") })) };
  if (k.art === "abspann") return { rolle: q(".rolle"), bloecke: qa(".rblock").map(b => ({ b, n: -1 })), karte: q(".ab-karte") };
  return {};
}
const fakten = () => {
  const d = D, leute = d.teams.reduce((n, t) => n + t.members.length, 0);
  return { datum: new Date(d.t0).toLocaleDateString("de-DE", { timeZone: TZ, weekday: "long", day: "numeric", month: "long", year: "numeric" }), leute,
    km: d.teams.reduce((n, t) => n + t.weg, 0) };
};
function vorspannHTML() {
  const f = fakten();
  return `<div class="schleier mittel"></div><div class="titel"><div class="logo">${LOGO}</div><h1>Stadtjagd</h1><div class="ort">Prag</div>
    <div class="fakten"><span>${modus === "probe" ? "Probe" : f.datum}</span><span>${D.teams.length} Teams</span><span>${f.leute} Leute</span><span>${D.stationen.length} Stationen</span></div></div>`;
}
// Fun Facts (Friedrich 17.10.: drei Kacheln): alle zusammen gelaufen (je Person gezählt), Schritte (ca. 1.350 je km) und
// Kalorien (ca. 55 kcal je km und Person; erst als halbe Brathähnchen à ca. 750 kcal, dann als Liter Bier à ca. 430 kcal)
const zahl = n => Math.round(n).toLocaleString("de-DE");
function faktenWerte() {
  const pkm = D.teams.reduce((n, t) => n + t.weg / 1000 * t.members.length, 0), leute = D.teams.reduce((n, t) => n + t.members.length, 0);
  return [
    { emo: "👣", wert: Math.round(pkm), lbl: "Personenkilometer", klein: `${leute} Leute zusammen` },
    { emo: "👟", wert: Math.round(pkm * 1350 / 1000) * 1000, lbl: "Schritte", klein: "geschätzt" },
    { emo: "🍗", wert: Math.round(pkm * 55 / 750), lbl: "halbe Brathähnchen verbrannt", klein: `ca. ${zahl(Math.round(pkm * 55 / 100) * 100)} kcal, geschätzt`,
      wechsel: { emo: "🍺", wert: Math.round(pkm * 55 / 430), lbl: "Liter Bier verbrannt" } }];
}
function faktenHTML(k) {
  k.werte = faktenWerte();
  const oben = Math.max(40, (1080 - untenFrei()) / 2 - 290);
  return `<div class="schleier dicht"></div><div class="ff-kopf" style="top:${oben}px">Fun Facts</div>
    <div class="ff-netz" style="top:${oben + 150}px">${k.werte.map(w => `<div><div class="ff-lagen">${[w, w.wechsel].filter(Boolean).map(l =>
      `<div class="ff-lage"><span class="emo">${l.emo}</span><b>0</b><span class="ff-lbl">${l.lbl}</span></div>`).join("")}</div>${w.klein ? `<small>${esc(w.klein)}</small>` : ""}</div>`).join("")}</div>`;
}
// Die Gruppen (Friedrich 17.10.): Startzeit, Zahl der Leute und die Teams der Gruppe mit Tier und Namen, als
// Zusammenfassung, wer in welcher Gruppe war. Der Zeitraffer danach bleibt anonym.
function gruppenHTML() {
  const gr = [...new Set(D.teams.map(t => t.gruppe))].sort((a, b) => a - b);
  const groesste = Math.max(...gr.map(g => D.teams.filter(t => t.gruppe === g).length));
  // Zeilenhöhe der Teams nach der größten Gruppe, damit alles über der Leiste bleibt
  const frei = 1080 - untenFrei() - 48, zh = Math.max(46, Math.min(78, Math.floor((frei - 140 - 290) / Math.max(1, groesste))));
  const hoch = 140 + 290 + groesste * zh, oben = Math.max(24, (1080 - untenFrei() - hoch) / 2);
  return `<div class="schleier dicht"></div><div class="ff-kopf" style="top:${oben}px">Die Gruppen</div>
    <div class="gr-netz" style="top:${oben + 140}px;--zh:${zh}px">${gr.map(g => { const ts = D.teams.filter(t => t.gruppe === g);
      return `<div class="gr-spalte"><h3>Gruppe ${g + 1}</h3><div class="zeit">Start ${uhr(ts[0].startAt)} Uhr</div>
        <div class="leute">${ts.reduce((n, t) => n + t.members.length, 0)} Leute</div>
        <div class="gr-koepfe">${ts.map(t => `<div class="gr-team" data-id="${t.id}"><i style="background:${t.farbe}">${t.emoji}</i><span class="gr-name">${esc(t.name)}</span></div>`).join("")}</div></div>`; }).join("")}</div>${zrHTML().replace('class="zr-kopf"', 'class="zr-kopf gr-zr"')}`;
}
// Ausgang der Gruppen-Folie (17.10.): die Teams drehen sich zu "?" und landen genau an den Stellen, an denen der
// Zeitraffer die anonymen Köpfe am Start zeigt (Ring um den Start, Plätze in Teamreihenfolge, aus der Kamera des
// Zeitraffers). Der Schleier blendet auf, dann der Schnitt auf die Karte.
const GR_AUS = 6500;
function gruppenAusgang(L, e, kam) {
  const FLIP = 520, VERSATZ = 70, FLUG = 1500, abFlug = GR_AUS + FLIP + (D.teams.length - 1) * VERSATZ + 300;
  const zr = K.find(x => x.id === "zeitraffer"), s = Z.szene, kz = zr ? zr.kam : kam, sch = s.querySelector(".schleier");
  const zk = s.querySelector(".gr-zr"); if (zk) zk.style.opacity = (ein(L, abFlug, FLUG - 200)).toFixed(3);   // Laufzeit-Kasten wie im Zeitraffer
  if (L > abFlug - 300) {   // Karte hinter dem Schleier schon in der Kamera des Zeitraffers, der Schleier blendet auf
    zeichneKarte(D.t0, kz, { spuren: "keine", koepfe: false });
    if (sch) sch.style.opacity = (1 - ein(L, abFlug, FLUG - 200)).toFixed(3);
  } else if (sch && sch.style.opacity) sch.style.opacity = "";
  if (L <= GR_AUS) {   // vor dem Drehen und im Halt (zurückgesprungen): Flieger weg, Kreise wieder da
    if (e.flug) { e.flug.forEach(z => { z.f.remove(); z.i.style.visibility = ""; z.kreis.style.removeProperty("--namen"); }); e.flug = null; }
    return;
  }
  if (!e.flug) {   // Flieger einmal anlegen, an der Stelle des Teamkreises (Bühnen-Pixel)
    const bu = $("#rb-buehne").getBoundingClientRect(), sk = bu.width / 1920, ring = ringMass(D.teams.length); e.flug = [];
    D.teams.forEach((t, n) => {
      const kreis = s.querySelector(`.gr-team[data-id="${t.id}"]`); if (!kreis) return;
      const i = kreis.querySelector("i"), r = i.getBoundingClientRect();
      const f = document.createElement("div"); f.className = "gr-flieger";
      f.style.cssText = `left:${((r.left - bu.left) / sk).toFixed(1)}px;top:${((r.top - bu.top) / sk).toFixed(1)}px;width:${(r.width / sk).toFixed(1)}px;height:${(r.height / sk).toFixed(1)}px`;
      f.style.setProperty("--c", t.farbe); f.textContent = t.emoji; s.appendChild(f); i.style.visibility = "hidden";
      const o = [(D.start.xy[0] - kz.cx) * kz.s + 960, (D.start.xy[1] - kz.cy) * kz.s + 540], a = -Math.PI / 2 + n * (Math.PI * 2 / ring.plaetze);
      e.flug.push({ t, f, i, kreis, von: [(r.left - bu.left + r.width / 2) / sk, (r.top - bu.top + r.height / 2) / sk],
        nach: [o[0] + Math.cos(a) * ring.radius, o[1] + Math.sin(a) * ring.radius], d: r.width / sk });
    });
  }
  e.flug.forEach((z, n) => {
    const t0 = GR_AUS + n * VERSATZ, fl = Math.min(1, Math.max(0, (L - t0) / FLIP));
    z.kreis.style.setProperty("--namen", (1 - ein(L, t0 + FLIP * .5, 300)).toFixed(3));
    const q = ruhig ? (L >= t0 + FLIP ? 1 : 0) : fl, frage = q >= .5;
    if (z.f.dataset.f !== (frage ? "1" : "0")) { z.f.dataset.f = frage ? "1" : "0"; z.f.textContent = frage ? "?" : z.t.emoji; z.f.classList.toggle("frage", frage); }
    const sx = ruhig ? 1 : Math.max(.02, Math.abs(Math.cos(Math.PI * fl)));
    const u = ruhig ? +(L >= abFlug + FLUG) : glatt((L - abFlug) / FLUG), x = z.von[0] + (z.nach[0] - z.von[0]) * u, y = z.von[1] + (z.nach[1] - z.von[1]) * u;
    const gr = (60 / z.d) * u + (1 - u);   // vom Kreis der Gruppenkarte auf Kopfgröße (60)
    z.f.style.transform = `translate(${(x - z.von[0]).toFixed(1)}px,${(y - z.von[1]).toFixed(1)}px) scale(${(sx * gr).toFixed(3)},${gr.toFixed(3)})`;
  });
}
// Zeitraffer: oben Laufzeit und wie viele schon im Ziel sind
function zrHTML() {
  return `<div class="zr-kopf"><div><small>Laufzeit</small><b><em class="zr-uhr">0:00</em><span>h</span></b></div><i></i>
    <div><small>im Ziel</small><b><em class="zr-ziel">0</em><span>von ${D.teams.length}</span></b></div></div>`;
}
const walzenHTML = () => `<div class="mw">${[0, 1, 2, 3, 4].map(j => `${j === 1 || j === 3 ? '<span class="dp">:</span>' : ""}<div class="walze"><div class="band">${"0123456789012".split("").map(c => `<div>${c}</div>`).join("")}</div></div>`).join("")}</div>`;
// Abstand zum Ersten: m:ss, ab einer Stunde h:mm:ss
const diffText = m => { const s = Math.max(0, Math.round(m / 1000)), h = Math.floor(s / 3600), mi = Math.floor(s / 60) % 60, x = String(s % 60).padStart(2, "0");
  return h ? h + ":" + String(mi).padStart(2, "0") + ":" + x : mi + ":" + x; };
// Rangliste: alle Plätze untereinander, rechts der Abstand zum Ersten; K11: ab 14 Teams in zwei Spalten (vordere links)
function rangHTML(k) {
  const n = k.zeilen.length, spalten = n >= 14 ? 2 : 1, je = Math.ceil(n / spalten), oben = 140, frei = 1080 - untenFrei() - oben - 24;
  const zh = Math.min(spalten > 1 ? 64 : 92, Math.floor(frei / je));
  k.zh = zh;
  return `<div class="schleier dicht"></div><div class="rl-kopf${spalten > 1 ? " breit" : ""}">Rangliste</div>
    <div class="rl-netz${spalten > 1 ? " zwei" : ""}" style="top:${oben + Math.max(0, (frei - zh * je) / 2)}px;--zh:${zh}px;--je:${je}">${k.zeilen.map(t => `<div class="rl-zeile">
      <span class="r">${t.place && t.place <= k.top ? `<span class="emo">${MEDAILLE[t.place - 1]}</span>` : t.place ? t.place + "." : ""}</span>
      <span class="rl-kreis"><span class="fr">?</span><span class="ti" style="background:${t.farbe}">${t.emoji}</span></span>
      <span class="n">${esc(t.name)}${t.place ? (t.gleich.length && t.place > k.top ? `<small>${esc(t.gleich.join(", "))}</small>` : "") : `<small>${t.solved} von ${D.stationen.length} Stationen</small>`}</span>
      ${t.place ? walzenHTML() : '<span class="weg">nicht im Ziel</span>'}
      <span class="dif">${t.place > 1 && k.erster ? "+" + diffText(t.netto - k.erster.netto) : ""}</span></div>`).join("")}</div>`;
}
function spaltenHTML(k) {
  const { folge, r, sc, px } = k.sp, bild = $("#rb-grund image.karte"), erst = k.id === "spalten";
  const karte = bild ? `<image class="mkarte" href="${bild.getAttribute("href")}" x="${((+bild.getAttribute("x") - r.x0) * sc).toFixed(1)}" y="${((+bild.getAttribute("y") - r.y0) * sc).toFixed(1)}"
    width="${(+bild.getAttribute("width") * sc).toFixed(1)}" height="${(+bild.getAttribute("height") * sc).toFixed(1)}" preserveAspectRatio="none" opacity=".6"/>` : "";
  const sx = px(D.start.xy), orte = `<circle class="start" cx="${sx[0].toFixed(1)}" cy="${sx[1].toFixed(1)}" r="9"/>` + D.stationen.filter(st => st.xy).map(st => { const q = px(st.xy);
    return `<circle class="st" cx="${q[0].toFixed(1)}" cy="${q[1].toFixed(1)}" r="12"/><text x="${q[0].toFixed(1)}" y="${(q[1] + 5).toFixed(1)}">${st.position}</text>`; }).join("");
  // Spalten und darunter die Reihe der noch verdeckten Teams (ohne Überschrift), zusammen mittig über der Leiste
  const p1 = folge.find(t => t.place === 1), mitte = (1080 - untenFrei()) / 2, hoehe = 72 + 14 + 72 + 22 + 292 + 24 + 128 + 14 + 117, oben = Math.max(16, mitte - (hoehe + 112) / 2);
  k.rest = folge.filter(t => !k.offen.includes(t.place)).sort((a, b) => a.name.localeCompare(b.name, "de"));
  k.restY = oben + hoehe + 32 + 40;
  return `<div class="schleier dicht"></div>${k.auf.some(a => a.gross) && p1 ? `<div class="sp-toen" style="background:${p1.farbe}"></div>` : ""}
    ${k.rest.map(t => `<div class="sp-rest" data-p="${t.place}"><div class="b" style="background:${t.farbe}">${t.emoji}</div><span>${esc(t.name)}</span></div>`).join("")}
    <div class="sp-netz" style="top:${oben.toFixed(0)}px">${folge.map(t => { const pf = t.pts.length ? t.pts.map(q => px([q.x, q.y])) : [sx], d = pfad(pf), e = pf[pf.length - 1];
      return `<div class="sp-spalte" data-p="${t.place}"><div class="sp-blitz" style="background:${t.farbe}"></div>
        <div class="sp-platz"><span class="emo">${MEDAILLE[t.place - 1]}</span>Platz ${t.place}</div>
        <div class="sp-zeit">${dauerGenau(t.netto)}${t.gleich.length ? `<small>${esc(t.gleich.join(", "))}</small>` : ""}</div>
        <div class="sp-karte"><svg viewBox="0 0 540 290" aria-hidden="true">${karte}<path class="grau" d="${d}" pathLength="1" stroke-dasharray="1 1" stroke-dashoffset="${erst ? 1 : 0}"/>
          <path class="farbe" d="${d}" pathLength="1" stroke="${linie(t)}" stroke-dasharray="1 1" stroke-dashoffset="1"/>${orte}
          <g class="mk" transform="translate(${(erst ? sx : e)[0].toFixed(1)} ${(erst ? sx : e)[1].toFixed(1)})"><circle class="kf" r="17"/><text class="kfr" y="8">?</text>
            <g class="mkt" opacity="0"><circle r="17" fill="${t.farbe}" stroke="var(--ring)" stroke-width="3"/><text class="kti" y="7">${t.emoji}</text></g></g></svg></div>
        <div class="sp-team"><div class="sp-kreis"><i class="sp-ring" style="--c:${t.farbe}"></i><i class="sp-ring" style="--c:${t.farbe}"></i><div class="fr">?</div><div class="ti" style="background:${t.farbe}">${t.emoji}</div></div>
          <div class="n">${esc(t.name)}</div></div>
        <div class="sp-m">${t.members.map(n => `<span class="nw">${esc(n)}</span>`).join(", ")}</div></div>`; }).join("")}</div>`;
}
// Bühnen-Pixel, die unten für die feste Leiste frei bleiben müssen (skalieren() setzt --unten)
const untenFrei = () => parseFloat(getComputedStyle($("#rb-buehne")).getPropertyValue("--unten")) || 0;
function siegerHTML() {
  const top = [2, 1, 3].map(p => D.rang.find(t => t.place === p)).filter(Boolean), H = { 1: 300, 2: 210, 3: 150 };
  const mitte = (1080 - untenFrei()) / 2, block = 168 + 20 + 72 + 24 + 300, ganz = block + 40 + 58, oben = mitte - ganz / 2;
  return `<div class="schleier dicht"></div>
    <div class="sg-podest" style="top:${oben}px;height:${block}px">${top.map(t => `<div class="sg-platz" data-p="${t.place}"><div class="b" style="background:${t.farbe}">${t.emoji}</div>
      <div class="n">${esc(t.name)}</div><div class="stufe" style="--c:${t.farbe};height:${H[t.place]}px"><span class="emo">${MEDAILLE[t.place - 1]}</span></div></div>`).join("")}</div>
    <div class="sg-summe" style="top:${oben + block + 40}px">${D.teams.length} Teams, zusammen ${km(fakten().km)} gelaufen</div>`;
}
// Award: Symbol, Titel und Wert links, darunter das Team; im Auftakt die Symbole aller Awards in einer Reihe
function awardHTML(k) {
  if (k.intro) return `<div class="aw-auftakt"><small>Bonusrunde</small><h2>Die Awards</h2>
    <div class="aw-reihe">${k.symbole.map(e => `<span class="emo">${e}</span>`).join("")}</div></div>`;
  const a = k.award, t = k.team;
  return `<div class="aw-spalte"><div class="aw-emo emo">${a.emo}</div><div class="aw-titel">${esc(a.titel)}</div><div class="aw-wert">${a.zeile}</div>
    <div class="aw-team"><div class="b" style="background:${t.farbe}">${t.emoji}</div><div class="n">${esc(t.name)}</div></div></div>`;
}
// Abspann (Nachtrag 17.10.): ein endloser Strom aus Blöcken; jeder Block ist ein Durchgang durch alle Fotos, neu gemischt,
// und setzt die Spalten dort fort, wo der Block davor endete (keine Lücke). Ein Block ist mindestens 1300 px hoch (bei
// wenigen Fotos mehrere Durchgänge), so reichen drei wiederverwendete Blöcke im DOM für jedes Fenster
const ROLLE = { SP: 4, CW: 360, LUECKE: 72, UNTER: 52, ABSTAND: 32, START: 200, TEMPO: 40 / 1000 };
function rolleBlock(r, n) {
  const SP = Math.min(ROLLE.SP, r.fotos.length), X0 = (1920 - (SP * ROLLE.CW + (SP - 1) * ROLLE.LUECKE)) / 2;
  while (r.bloecke.length <= n) {
    const m = r.bloecke.length, hoehe = m ? r.bloecke[m - 1].hoehe.slice() : Array(SP).fill(0), anfang = Math.min(...hoehe), kacheln = [];
    const rnd = zufall(r.seed + m * 7919);
    do {
      const reihe = r.fotos.slice();
      for (let i = reihe.length - 1; i > 0; i--) { const j = Math.floor(rnd() * (i + 1)); [reihe[i], reihe[j]] = [reihe[j], reihe[i]]; }
      reihe.forEach(f => { const c = hoehe.indexOf(Math.min(...hoehe)), h = ROLLE.CW / f.ratio;
        kacheln.push({ f, x: X0 + c * (ROLLE.CW + ROLLE.LUECKE), y: hoehe[c], w: ROLLE.CW, h }); hoehe[c] += h + ROLLE.UNTER + ROLLE.ABSTAND; });
    } while (Math.min(...hoehe) - anfang < 1300);
    r.bloecke.push({ kacheln, hoehe, oben: Math.min(...kacheln.map(x => x.y)), unten: Math.max(...hoehe) });
  }
  return r.bloecke[n];
}
function rolleZeichnen(k, e, L) {
  const r = k.roll, s = ruhig ? Math.floor(L / 6000) * 240 : ROLLE.TEMPO * L, oben = s - ROLLE.START, unten = oben + 1080;
  e.rolle.style.transform = `translate3d(0,${(-oben).toFixed(1)}px,0)`;
  // sichtbare Blöcke: der erste, dessen Unterkante unter dem Fensteranfang liegt, und die danach, solange sie oben ins Fenster reichen
  while (r.ab > 0 && rolleBlock(r, r.ab).oben > oben) r.ab--;
  while (rolleBlock(r, r.ab).unten < oben) r.ab++;
  const zeigen = [];
  for (let n = r.ab; rolleBlock(r, n).oben < unten && zeigen.length < e.bloecke.length; n++) zeigen.push(n);
  e.bloecke.forEach(b => { if (b.n >= 0 && !zeigen.includes(b.n)) { b.n = -1; b.b.innerHTML = ""; } });
  zeigen.forEach(n => { if (e.bloecke.some(b => b.n === n)) return; const b = e.bloecke.find(x => x.n < 0); b.n = n;
    b.b.innerHTML = rolleBlock(r, n).kacheln.map(x => `<div class="rk" style="left:${x.x}px;top:${x.y.toFixed(1)}px;width:${x.w}px;height:${x.h.toFixed(1)}px"><img src="${x.f.src}" alt="Gruppenfoto ${esc(x.f.team.name)}"></div>
      <div class="ru" style="left:${x.x}px;top:${(x.y + x.h + 8).toFixed(1)}px;width:${x.w}px"><span class="emo">${x.f.team.emoji}</span>${esc(x.f.team.name)}<small>Station ${x.f.position}</small></div>`).join(""); });
}
function abspannHTML(k) {
  const f = fakten(), karte = `<div class="ab-karte"><h2>Stadtjagd Prag</h2><p>${D.teams.length} Teams, zusammen ${km(f.km)} gelaufen</p></div>`;
  return k.roll ? `<div class="schleier mittel"></div><div class="rollfenster"><div class="rolle">${'<div class="rblock"></div>'.repeat(3)}</div></div>${karte}` : karte;
}
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

/* ---------- Zeitraffer-Kopf ---------- */
function zrKopf(k, T) {
  const e = k.el, u = lauf(T), z = D.teams.filter(t => t.fertig && t.fertig <= T).length;
  if (e.u !== u) { e.uhr.textContent = u; e.u = u; }
  if (e.z !== z) { e.ziel.textContent = z; e.z = z; }
}

/* ---------- Ein Bild ---------- */
const ein = (lokal, ab, dauerMs = 480) => ruhig ? (lokal >= ab ? 1 : 0) : glatt((lokal - ab) / dauerMs);
// Überschwinger beim Aufspringen (0,85, 1,05, 1); b = Anteil von 520 ms
const spring = b => ruhig || b >= 1 ? 1 : b <= 0 ? .85 : b < .6 ? .85 + .2 * (1 - Math.pow(1 - b / .6, 2)) : 1.05 - .05 * glatt((b - .6) / .4);
const gleitet = (x, v, weg = 16) => { x.style.opacity = v.toFixed(3); x.style.transform = `translateY(${((1 - v) * weg).toFixed(1)}px)`; };
function zeichnen() {
  if (Z.phase !== "show") return;
  const k = K[Z.i], L = Z.lokal, kam = kamFuer(Z.i, L), s = Z.szene, e = k.el;
  leisteFortschritt();
  // Übergang: neue Szene blendet über die alte; Karte und Award lassen die alte zugleich weichen
  if (s) s.style.opacity = ein(L, 0);
  // Die alte Szene blendet nach echter Zeit aus, nicht nach der Kapitelzeit: ein früher Halt friert die Kapitelzeit ein und
  // ließ die Überblendung sonst auf halber Strecke stehen (Fehler 17.10., Award zu Rangliste Teil 2)
  if (Z.alt) { const dtS = performance.now() - (Z.szeneAb || 0);
    if (dtS > Z.altBis) { Z.alt.remove(); Z.alt = null; }
    else if (k.art === "karte" || k.art === "award") Z.alt.style.opacity = (1 - (ruhig ? 1 : glatt(dtS / (k.art === "award" ? 240 : 480)))).toFixed(3); }
  // Awards: die Karte tritt zurück, danach blendet sie wieder auf
  const gr = $("#rb-grund"), vorAw = Z.i > 0 && K[Z.i - 1].art === "award", grO = k.art === "award" ? (vorAw ? ".28" : (1 - .72 * ein(L, 0, 700)).toFixed(3))
    : vorAw ? (.28 + .72 * ein(L, 0, 700)).toFixed(3) : "";
  if (gr.style.opacity !== grO) gr.style.opacity = grO;
  const sg = $("#rb-stationen"); if (k.art !== "award" && sg.style.opacity) sg.style.opacity = "";
  if (k.art === "karte") {
    const T = kapitelZeit(k, L);
    zeichneKarte(T, kam, { spuren: "alle", koepfe: true });
    zrKopf(k, T);
    pulse();
    return;
  }
  if ($("#rb-pulse").firstChild) $("#rb-pulse").innerHTML = "";
  if (k.art === "titel") {
    zeichneKarte(D.t0, kam, { spuren: "keine", koepfe: false });
    s.querySelector(".logo").style.opacity = ein(L, 100, 600);
    const nadel = s.querySelector(".nadel"); if (nadel) nadel.style.transform = `rotate(${ruhig ? 0 : (1 - glatt(L / 2200)) * 140 * Math.cos(L / 260)}deg)`;
    const h = s.querySelector("h1"), o = s.querySelector(".ort"), f = s.querySelector(".fakten");
    [[h, 500], [o, 900], [f, 1500]].forEach(([x, ab]) => { const v = ein(L, ab); x.style.opacity = v; x.style.transform = `translateY(${(1 - v) * 16}px)`; });
  }
  if (k.art === "fakten") {
    zeichneKarte(D.t0, kam, { spuren: "keine", koepfe: false });
    gleitet(e.kopf, ein(L, 0));
    // Zahlen zählen hoch (1,6 s, zum Ende langsamer), die Kacheln kommen nacheinander. Kalorien: die Brathähnchen stehen
    // bis zum Halt bei 3,6 s; Weiter schaltet die Kachel weich auf Liter Bier um, sie zählt neu (ruhig: ohne Zählen, harter Wechsel)
    const zaehle = (b, wert, von) => { const u = ruhig ? +(L >= von) : Math.min(1, Math.max(0, (L - von) / 1600)), w = zahl(wert * (1 - Math.pow(1 - u, 3)));
      if (b.textContent !== w) b.textContent = w; };
    e.kacheln.forEach((x, i) => { const ab = 300 + i * 250, w = k.werte[i], lg = e.lagen[i]; gleitet(x, ein(L, ab, 520), 30);
      zaehle(lg[0].b, w.wert, ab + 150);
      if (!lg[1]) return;
      // erst weicht das Huhn (260 ms), dann kommt das Bier (320 ms), nie beide zugleich
      const um = 3900, raus = ein(L, um, 260), rein = ein(L, um + 260, 320);
      lg[0].el.style.opacity = (1 - raus).toFixed(3); lg[0].el.style.transform = `translateY(${(-raus * 24).toFixed(1)}px)`;
      lg[1].el.style.opacity = rein.toFixed(3); lg[1].el.style.transform = `translateY(${((1 - rein) * 24).toFixed(1)}px)`;
      zaehle(lg[1].b, w.wechsel.wert, um + 260); });
  }
  if (k.art === "gruppen") {
    zeichneKarte(D.t0, kam, { spuren: "keine", koepfe: false });
    gleitet(e.kopf, Math.min(ein(L, 0), 1 - ein(L, GR_AUS + 1000, 700)));
    e.spalten.forEach((x, i) => gleitet(x, Math.min(ein(L, 300 + i * 250, 520), 1 - ein(L, GR_AUS + 1400, 900)), 30));
    // die Teams steigen nacheinander in ihre Karte ein: Kreis springt auf, Name gleitet nach
    e.teams.forEach((ts, i) => ts.forEach((a, j) => { const ab = 800 + i * 250 + j * 120, v = ein(L, ab, 260);
      a.style.opacity = v.toFixed(3); a.style.transform = `translateX(${((1 - v) * -18).toFixed(1)}px)`;
      a.firstChild.style.transform = `scale(${spring((L - ab) / 520).toFixed(4)})`; }));
    gruppenAusgang(L, e, kam);
  }
  if (k.art === "award") awardZeichnen(k, L, kam);
  if (k.art === "rangliste") { zeichneKarte(D.tEnd, kam, { spuren: "keine", koepfe: false }); rangZeichnen(k, L); }
  if (k.art === "spalten") { zeichneKarte(D.tEnd, kam, { spuren: "keine", koepfe: false }); spaltenZeichnen(k, L); }
  if (k.art === "sieger") {
    zeichneKarte(D.tEnd, kam, { spuren: "alle", koepfe: false });
    const ab = { 3: 200, 2: 450, 1: 750 };
    s.querySelectorAll(".sg-platz").forEach(d => { const v = ein(L, ab[d.dataset.p] || 0, 560); d.style.opacity = v; d.style.transform = `translateY(${(1 - v) * 40}px)`; });
    s.querySelector(".sg-summe").style.opacity = ein(L, 1300, 600);
  }
  if (k.art === "abspann") {
    // die Rolle läuft ohne Ende; ohne Fotos steht die Karte mit allen Routen
    zeichneKarte(D.tEnd, kam, { spuren: "alle", koepfe: !k.roll });
    if (k.roll) rolleZeichnen(k, e, L);
    gleitet(e.karte, ein(L, k.roll ? 600 : 1600, 800));
  }
}
// Station gelöst: Ring um den Kopf des Teams (anonym, darum an jeder Station)
function pulse() {
  const g = $("#rb-pulse");
  let html = "";
  if (!ruhig) D.teams.forEach(t => { const kp = kopfPos[t.id]; if (!kp) return;
    html += `<circle class="kpuls" cx="${kp.q[0].toFixed(1)}" cy="${kp.q[1].toFixed(1)}" r="${(34 + kp.u * 46).toFixed(1)}" opacity="${(1 - kp.u).toFixed(2)}"/>`; });
  if (html || g.firstChild) g.innerHTML = html;
}
// Ein Award läuft durch: Symbol springt auf, Titel und Wert gleiten ein, 1,2 s später springt das Team auf und seine
// Route zeichnet sich in Teamfarbe über die Karte, sein Kopf läuft an der Spitze mit
function awardZeichnen(k, L, kam) {
  const e = k.el, vor = K[Z.i - 1] || {};
  // Stationen: im Auftakt blenden sie aus, mit dem ersten Award wieder ein
  const st = k.intro ? (vor.art === "karte" ? 1 - ein(L, 0) : 0) : vor.art === "award" && !vor.intro ? 1 : ein(L, 0);
  $("#rb-stationen").style.opacity = st.toFixed(3);
  if (k.intro) {
    zeichneKarte(D.tEnd, kam, { spuren: "keine", koepfe: false });
    gleitet(e.klein, ein(L, 100)); gleitet(e.titel, ein(L, 300));
    e.symbole.forEach((x, i) => { const v = ein(L, 900 + i * 140, 420); x.style.opacity = v.toFixed(3); x.style.transform = `translateY(${((1 - v) * 24).toFixed(1)}px) scale(${(.9 + .1 * v).toFixed(3)})`; });
    return;
  }
  const t = k.team, da = L >= AW_TEAM, rU = ruhig ? +da : glatt((L - AW_TEAM) / AW_ROUTE);
  const bis = D.t0 + ((t.fertig || D.tEnd) - D.t0) * rU;
  zeichneKarte(D.tEnd, kam, { spuren: da ? t : "keine", koepfe: da ? t : false, bis });
  // Ist die Route fertig gezeichnet, blendet das Teamsymbol am Ende der Route aus (Friedrich 17.10.)
  if (da && kopfEl[t.id]) kopfEl[t.id].style.opacity = (ruhig ? 0 : 1 - glatt((L - AW_TEAM - AW_ROUTE - 100) / 450)).toFixed(3);
  e.emo.style.opacity = ein(L, 80, 240).toFixed(3); e.emo.style.transform = `scale(${spring((L - 80) / 520).toFixed(4)})`;
  gleitet(e.titel, ein(L, AW_TITEL)); gleitet(e.wert, ein(L, AW_TITEL + 380));
  gleitet(e.team, ruhig ? +da : glatt((L - AW_TEAM) / 200), 24);
  e.kreis.style.transform = `scale(${spring((L - AW_TEAM) / 520).toFixed(4)})`;
}
// Walzen: drehen, bis ihre Ziffer an der Reihe ist, dann rastet sie mit Auslauf ein
function walzeSetzen(bd, L, r, ziel, off, dh, ex = 0) {
  let pos;
  if (ruhig) pos = L >= r.ab ? ziel : 0;
  else if (L < r.ab) pos = (L + ex) * .014 + off;
  else { const p0 = (r.ab + ex) * .014 + off, zp = Math.ceil((p0 - ziel) / 10) * 10 + ziel + 10, u = Math.min(1, (L - r.ab) / r.dauer);
    pos = p0 + (zp - p0) * (1 - Math.pow(1 - u, 3)); }
  const ty = (-(((pos % 10) + 10) % 10) * dh).toFixed(1);
  if (bd._ty !== ty) { bd.style.transform = `translateY(${ty}px)`; bd._ty = ty; }
}
function rangZeichnen(k, L0) {
  const e = k.el, dh = k.zh * .8, L = L0 + (k.versatz || 0);   // Teil 2 zeichnet den Stand nach dem Aufdecken; Einblenden läuft mit L0
  gleitet(e.kopf, ein(L0, 0)); e.netz.style.opacity = ein(L0, 150, 500).toFixed(3);
  e.zeilen.forEach(z => {
    const p = k.plan[z.t.id] || {};
    if (z.dif && p.rast) { const r4 = p.rast[4]; z.dif.style.opacity = (ruhig ? +(L >= r4.ab + r4.dauer) : glatt((L - r4.ab - r4.dauer) / 420)).toFixed(3); }
    if (p.rast) z.baender.forEach((bd, j) => walzeSetzen(bd, L, p.rast[j], +z.z[j], z.i * 1.7 + j * 3.3, dh, Z.extra));
    if (p.auf == null) return;
    // "?" wird zum Team: Kreis springt mit Überschwinger, Name gleitet ein, die Zeile leuchtet kurz in Teamfarbe
    const d0 = L - p.auf, st = d0 < 0 ? -1 : d0 > 950 ? 2 : Math.round(d0);
    if (z.st === st) return;
    z.st = st;
    const a = ruhig ? +(d0 >= 0) : glatt(d0 / 220);
    z.fr.style.opacity = (1 - a).toFixed(3); z.ti.style.opacity = a.toFixed(3); z.ti.style.transform = `scale(${spring(d0 / 520).toFixed(4)})`;
    z.n.style.opacity = a.toFixed(3); z.n.style.transform = `translateX(${((1 - a) * -16).toFixed(1)}px)`;
    const g = ruhig || d0 < 0 ? 0 : 16 * (1 - glatt(d0 / 900));
    z.row.style.background = g > .2 ? `color-mix(in srgb, ${z.t.farbe} ${g.toFixed(1)}%, transparent)` : "";
  });
}
// Spalten: im ersten Kapitel kommen sie nacheinander und die drei Wege zeichnen sich grau, jeder so schnell wie das Team
// war (der schnellste ist zuerst fertig); in den Aufdeck-Kapiteln treten die anderen Spalten zurück, der "?"-Kreis
// atmet im Halt und zittert nach Weiter, dann Blitz, Tier, Name, Route in Farbe, Mitglieder. Platz 1: Bühne tönt sich,
// Name skaliert, Puls um den Kreis
function spaltenZeichnen(k, L) {
  const e = k.el, maxN = Math.max(...k.sp.folge.map(t => t.netto)), jetzt = performance.now();
  e.spalten.forEach((c, i) => {
    const t = c.t, a = k.auf.find(x => x.platz === t.place), offen = k.offen.includes(t.place);
    let v = 1, f = 1;
    if (k.id === "spalten") { v = ein(L, 200 + i * 220, 520); f = ruhig ? +(L >= 1400) : Math.min(1, Math.max(0, (L - 1400) / (3400 * t.netto / maxN))); }
    const dim = k.auf.length && !a ? 1 - .55 * ein(L, 0, 600) : 1;
    c.el.style.opacity = (v * dim).toFixed(3); c.el.style.transform = `translateY(${((1 - v) * 30).toFixed(1)}px)`;
    if (c.f !== f) { c.grau.setAttribute("stroke-dashoffset", (1 - f).toFixed(4)); const q = c.grau.getPointAtLength(f * c.len);
      c.kopf.setAttribute("transform", `translate(${q.x.toFixed(1)} ${q.y.toFixed(1)})`); c.f = f; }
    const enth = offen ? -Infinity : a ? a.enth : Infinity, d0 = L - enth, auf = d0 >= 0;
    let sk = 1;
    if (a && !auf && !ruhig) {
      if (L >= a.ab && !Z.haelt) sk = 1 + (a.gross ? .1 : .06) * glatt((L - a.ab) / (a.enth - a.ab)) * Math.sin((L - a.ab) / 38);
      else sk = 1 + .035 * Math.sin((L + Z.extra) / 320);
    }
    const ta = ruhig ? +auf : glatt(d0 / 220);
    c.fr.style.opacity = (1 - ta).toFixed(3); c.fr.style.transform = `scale(${sk.toFixed(4)})`;
    c.ti.style.opacity = ta.toFixed(3); c.ti.style.transform = `scale(${(auf ? spring(d0 / 520) : .85).toFixed(4)})`;
    c.n.style.opacity = (ruhig ? +auf : glatt((d0 - 150) / 250)).toFixed(3);
    if (a && a.gross) c.n.style.transform = `scale(${(ruhig || !auf ? 1 : 1.15 - .15 * glatt((d0 - 150) / 700)).toFixed(4)})`;
    c.m.style.opacity = (ruhig ? +auf : glatt((d0 - 500) / 400)).toFixed(3);
    c.blitz.style.opacity = ruhig || !auf ? 0 : (.35 * (1 - glatt(d0 / 600))).toFixed(3);
    const rf = ruhig ? +auf : glatt((d0 - 200) / 1400);
    if (c.rf !== rf) { c.farbe.setAttribute("stroke-dashoffset", (1 - rf).toFixed(4)); c.mkt.setAttribute("opacity", ta.toFixed(3)); c.rf = rf; }
    if (a && a.gross && auf && !ruhig) { if (!k.pulsAb) k.pulsAb = jetzt;
      c.ringe.forEach((r, j) => { const u = ((jetzt - k.pulsAb + j * 650) % 1300) / 1300; r.style.opacity = (.8 * (1 - u)).toFixed(3); r.style.transform = `scale(${(1 + u * .45).toFixed(3)})`; }); }
    else if (c.ringe[0].style.opacity !== "0") c.ringe.forEach(r => { r.style.opacity = "0"; });
  });
  // Reihe der noch verdeckten Teams: mittig; wer aufgedeckt wird, fliegt in seine Spalte, die anderen rücken zusammen
  const slot = (liste, t) => 960 - 90 + (liste.indexOf(t) - (liste.length - 1) / 2) * 340;
  const weg = k.auf.filter(a => k.rest.some(t => t.place === a.platz)).sort((a, b) => a.enth - b.enth);
  const vR = k.id === "spalten" ? ein(L, 900, 520) : 1;
  e.rest.forEach(r => {
    let x = slot(k.rest, r.t), liste = k.rest;
    weg.forEach(a => { const neu = liste.filter(t => t.place !== a.platz);
      if (neu.includes(r.t)) x += (slot(neu, r.t) - slot(liste, r.t)) * (ruhig ? +(L >= a.enth) : glatt((L - a.enth - 100) / 500));
      liste = neu; });
    let tx = x, ty = k.restY, sk = 1, op = vR, nm = 1;
    const a = k.auf.find(z => z.platz === r.t.place), c = e.spalten.find(z => z.t === r.t);
    if (a && L >= a.enth) op = 0;
    else if (a && !ruhig && L >= a.enth - 600) { const u = glatt((L - a.enth + 600) / 600);
      tx = x + (c.ziel[0] - x) * u; ty = k.restY + (c.ziel[1] - k.restY) * u - Math.sin(Math.PI * u) * 80; sk = 1 + .6 * u; nm = Math.max(0, 1 - u * 2.5); }
    r.el.style.opacity = op.toFixed(3); r.name.style.opacity = nm.toFixed(3);
    r.el.style.transform = `translate(${(tx - 40).toFixed(1)}px,${(ty - 40).toFixed(1)}px) scale(${sk.toFixed(3)})`;
  });
  if (e.toen) { const p1 = k.auf.find(x => x.gross), danach = k.auf[1];
    e.toen.style.opacity = p1 ? (.14 * ein(L, p1.enth, 900) * (danach ? 1 - ein(L, danach.ab, 600) : 1)).toFixed(3) : 0; }
}

const HAKEN = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10" stroke-width="1.8"/><path d="m7.5 12.5 3 3 6-6.5"/></svg>';
const ACHTUNG = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3 2 20h20Z"/><path d="M12 10v4M12 17h.01"/></svg>';
// Dauer bis zum Abspann (der läuft ohne Ende)
function gesamt() { return K.reduce((n, k) => n + (k.endlos ? 0 : k.dur), 0); }
function mmss(t) { t = Math.round(t / 1000); return Math.floor(t / 60) + ":" + String(t % 60).padStart(2, "0"); }

/* ---------- Steuerleiste ---------- */
// S9: läuft die Show, verschwindet die Leiste 2,5 s nach der letzten Mausbewegung; pausiert bleibt sie stehen
let leisteUhr = null;
function leisteZeigen() {
  if (!root) return;
  $("#rb-leiste").classList.remove("weg"); root.classList.remove("still");
  clearTimeout(leisteUhr);
  leisteUhr = setTimeout(() => { if (root && Z.phase === "show" && Z.spielt) leisteWeg(); }, 2500);
}
function leisteWeg() { clearTimeout(leisteUhr); $("#rb-leiste").classList.add("weg"); root.classList.add("still"); }
function leisteSpur() {
  $("#rb-lSpur").innerHTML = K.map((k, i) => `<span style="--d:${k.dur}" data-i="${i}"><i></i></span>`).join("");
  leisteFortschritt();
}
// Wie bei einem Video (Friedrich 17.10.): an jede Stelle der Leiste klicken oder ziehen. Das Kapitel unter dem Zeiger und
// die Stelle darin ergeben sich aus der Lage; im selben Kapitel wird nur die Zeit gesetzt, ohne die Szene neu zu bauen.
// Halte vor der Stelle gelten als erledigt.
function leistePos(e) {
  const segs = [...$("#rb-lSpur").querySelectorAll("span")]; if (!segs.length) return null;
  let best = segs[0], bd = Infinity;
  segs.forEach(sg => { const r = sg.getBoundingClientRect(), d = e.clientX < r.left ? r.left - e.clientX : e.clientX > r.right ? e.clientX - r.right : 0; if (d < bd) { bd = d; best = sg; } });
  const r = best.getBoundingClientRect(), i = +best.dataset.i, k = K[i];
  return { i, lok: Math.round(Math.max(0, Math.min(1, (e.clientX - r.left) / Math.max(1, r.width))) * k.dur * (k.endlos ? 1 : .999)) };
}
function leisteSuche(e) {
  if (!startbar() || frageOffen()) return;
  const q = leistePos(e); if (!q) return;
  if (Z.phase !== "show") return starten(K[q.i].id, q.lok);   // M8: Starten baut die Kapitel neu
  Z.spielt = true;
  if (q.i === Z.i) {
    const h = K[q.i].halte || [];
    Z.lokal = q.lok; Z.haelt = false; Z.endHalt = false; Z.hNr = h.filter(x => x.t < q.lok).length; Z.extra = 0; Z.wechsel = performance.now();
    zeichnen(); leisteFortschritt();
  } else geheZu(q.i, q.lok);
  knopf();
}
function leisteBedienen() {
  const sp = $("#rb-lSpur"), tipp = $("#rb-lTipp"); let zieht = false;
  sp.addEventListener("pointerdown", e => { zieht = true; try { sp.setPointerCapture(e.pointerId); } catch (x) { /* ohne Fangen */ } leisteSuche(e); });
  sp.addEventListener("pointermove", e => {
    if (zieht) leisteSuche(e);
    const q = leistePos(e); if (!q) return;
    const k = K[q.i]; tipp.textContent = k.name + (k.endlos ? "" : " " + mmss(q.lok)); tipp.style.left = Math.max(8, Math.min(innerWidth - 200, e.clientX - 60)) + "px"; tipp.style.opacity = 1; });
  sp.addEventListener("pointerleave", () => { if (!zieht) tipp.style.opacity = 0; });
  const ende = () => { zieht = false; tipp.style.opacity = 0; };
  sp.addEventListener("pointerup", ende); sp.addEventListener("pointercancel", ende);
}
let fortStand = "";
// Kapitel und Zustand in Worten, nie ein Team: für die Leiste und den Stand der Fernbedienung
function zustandWorte() {
  const show = Z.phase === "show", k = K[Z.i], endlos = show && k && k.endlos, h = show && k.halte && k.halte[Z.hNr];
  const zustand = !show ? "" : Z.endHalt && !Z.haelt && !k.endlos ? "wartet auf Weiter" : Z.haelt ? (h && h.art === "nach" ? "aufgedeckt, wartet auf Weiter" : "wartet auf Weiter")
    : !Z.spielt && !amEnde() ? "Pause" : endlos ? "läuft endlos" : "";
  return { name: show ? k.name : Z.phase === "durchsehen" ? "Fotos durchsehen" : "Vorbereiten", zustand, endlos: !!endlos };
}
// Gespielte Zeit bis zur Stelle im aktuellen Kapitel (der endlose Abspann zählt nicht zur Gesamtdauer)
function vorbeiMs() {
  const show = Z.phase === "show", k = K[Z.i], endlos = show && k && k.endlos;
  return K.slice(0, Z.i).reduce((n, x) => n + (x.endlos ? 0 : x.dur), 0) + (show ? (endlos ? Z.lokal : Math.min(Z.lokal, k.dur)) : 0);
}
// Leiste nennt nur Kapitel und Zustand, nie ein Team
function leisteFortschritt() {
  const show = Z.phase === "show", w = zustandWorte(), endlos = w.endlos, vorbei = vorbeiMs();
  const vorn = modus === "probe" ? "Probe: " : "";
  const txt = vorn + w.name + (w.zustand ? ", " + w.zustand : "") + "|" + (endlos ? mmss(vorbei) : mmss(vorbei) + " / " + mmss(gesamt()));
  $("#rb-lSpur").querySelectorAll("span").forEach((x, i) => x.style.setProperty("--p", (i < Z.i ? 100 : i > Z.i || !show ? 0 : K[i].endlos ? 100 : Math.min(100, Z.lokal / K[i].dur * 100)) + "%"));
  if (txt !== fortStand) { const [a, b] = txt.split("|"); $("#rb-lKap").textContent = a; $("#rb-lZeit").textContent = b; fortStand = txt; }
}
function vollbild() {
  if (document.fullscreenElement) document.exitFullscreen().catch(() => {});
  else document.documentElement.requestFullscreen().catch(() => {});
}
function thema() {
  const jetzt = document.documentElement.dataset.theme || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
  const neu = jetzt === "dark" ? "light" : "dark"; document.documentElement.dataset.theme = neu;
  try { localStorage.setItem("sj.thema", neu); } catch (e) { /* gilt dann nur bis zum Neuladen */ }
  themaNeu();
}
// S13: nur neu rastern, das alte Bild steht bis zum Tausch; S18: Linienfarben fürs Thema
function themaNeu() { if (!D) return; karteRastern(); linienFarben(); letzteKarte = null; }
// S8: Rand für Fernseher mit Overscan, die Bühne auf 94 %
function rand(an = !OPT.rand) { OPT.rand = an; const c = root.querySelector("#rb-oRand"); if (c) c.checked = an; skalieren(); }
// M3: das Schwarzbild merkt sich, ob die Show lief, und setzt beim Zurückholen dort fort
function schwarz() {
  const s = $("#rb-schwarz"), an = !s.classList.contains("an");
  s.classList.toggle("an", an);
  if (an) { Z.vorSchwarz = Z.spielt; Z.spielt = false; } else Z.spielt = Z.vorSchwarz;
  knopf(); leisteFortschritt();
}

/* ---------- M5: Verlassen nur nach Rückfrage ---------- */
// Zurück im Browser, Maus-Seitentaste, Wischen auf dem Touchpad und der Link zur Spielleitung fragen erst; Neuladen fragt
// der Browser (beforeunload). Die Fotos liegen nur im Speicher: wer die Show verlässt, lädt sie danach neu.
const frageOffen = () => !!root && !root.querySelector("#rb-frage").hidden;
function frage() {
  if (!root || frageOffen()) return;
  Z.vorFrage = Z.spielt; Z.spielt = false; knopf();
  const f = $("#rb-frage");
  $("#rb-frageText").textContent = modus === "probe" ? "Probe verlassen?" : "Rückblick verlassen? Die Fotos werden danach neu geladen.";
  f.hidden = false; leisteZeigen();
  $("#rb-bleiben").focus();
}
function bleiben() { if (!frageOffen()) return; $("#rb-frage").hidden = true; Z.spielt = Z.vorFrage; knopf(); $("#rb-bleiben").blur(); }
function verlassen() {
  $("#rb-frage").hidden = true;
  $("#rb-schwarz").classList.add("an");   // erst schwarz, nie direkt die Rangliste der Spielleitung auf dem Beamer
  Z.spielt = false;
  const ziel = modus === "probe" ? "#/" : "#/admin";
  setTimeout(() => { location.hash = ziel; }, 60);
}
function zurueckImBrowser() {
  if (!root) return;
  history.pushState({ rueckblick: 1 }, "", location.href);   // die Sperre steht wieder
  frage();
}
function vorUnload(e) {
  if (D && ["vorbereiten", "show", "durchsehen"].includes(Z.phase)) { e.preventDefault(); e.returnValue = ""; }
}

/* ---------- Gerüst ---------- */
const GERUEST = `
<div id="rb-buehne" aria-live="off">
  <div class="osm" id="rb-osm" hidden>© OpenStreetMap-Mitwirkende</div>
  <svg id="rb-welt" aria-hidden="true"><g id="rb-grund"></g><g id="rb-spuren"></g></svg>
  <svg id="rb-schirm" viewBox="0 0 1920 1080" aria-hidden="true"><g id="rb-namen"></g><g id="rb-anker"></g><g id="rb-stationen"></g><g id="rb-pulse"></g><g id="rb-koepfe"></g></svg>
  <div id="rb-szenen"></div>
  <div id="rb-ueber"></div>
</div>
<div id="rb-leiste" class="weg" role="toolbar" aria-label="Steuerung">
  <button data-k="zurueck" title="Zurück (Pfeil links)"><svg viewBox="0 0 24 24"><path d="M6 5h2v14H6zM20 5v14L9 12z"/></svg>Zurück</button>
  <button data-k="spiel" class="haupt" id="rb-bSpiel"><svg viewBox="0 0 24 24"><path d="M7 4v16l13-8z"/></svg><span>Start</span></button>
  <button data-k="weiter" title="Weiter (Pfeil rechts)">Weiter<svg viewBox="0 0 24 24"><path d="M16 5h2v14h-2zM4 5v14l11-7z"/></svg></button>
  <div class="spur" id="rb-lSpur"></div>
  <span class="kap" id="rb-lKap"></span>
  <span class="zeit" id="rb-lZeit"></span>
  <div id="rb-lTipp" aria-hidden="true"></div>
  <button data-k="thema" title="Hell oder dunkel (T)">Hell/Dunkel</button>
  <button data-k="voll" title="Vollbild (F)">Vollbild</button>
  <button data-k="hilfe" title="Tasten (H)">Tasten</button>
</div>
<div id="rb-frage" role="alertdialog" aria-labelledby="rb-frageText" hidden><span id="rb-frageText"></span>
  <button id="rb-bleiben" class="haupt">Bleiben</button><button id="rb-verlassen">Verlassen</button></div>
<div id="rb-schwarz"></div>
`;

/* =====================================================================
   Laden: PIN, Prüfung, Daten, Fotos, Karte, Schriften (Spezifikation 6.1 und 6.2)
   ===================================================================== */
const AUS_KEY = "sj.rb.aus";   // nur "teamId:position", nie Bilddaten
function ausLesen() { try { const a = JSON.parse(sessionStorage.getItem(AUS_KEY) || "[]"); return new Set(Array.isArray(a) ? a : []); } catch { return new Set(); } }
function ausSchreiben() { try { sessionStorage.setItem(AUS_KEY, JSON.stringify([...OPT.aus])); } catch { /* dann gilt die Auswahl nur bis zum Neuladen nicht */ } }

const fotoCache = new Map();   // "teamId:position" -> { src: Blob-URL, ratio }; nur im Speicher, nie auf der Festplatte
const schluesselVon = f => f.teamId + ":" + f.position;
// S23: so lange wartet die Show auf den ersten Versuch eines Fotos, und danach erscheint der Ausweg
const geduld = () => window.__rbGeduld || 20000;
async function bildAus(b64) {
  const bin = atob(String(b64).replace(/\s/g, "")), u8 = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) u8[i] = bin.charCodeAt(i);
  const url = URL.createObjectURL(new Blob([u8], { type: "image/jpeg" })), img = new Image();
  img.src = url;
  try { await img.decode(); } catch (e) { URL.revokeObjectURL(url); throw e; }   // vor dem Start decodieren, damit nichts ruckelt
  return { src: url, ratio: img.naturalWidth / Math.max(1, img.naturalHeight) };
}
const mitFrist = (p, frist) => Promise.race([p, new Promise((_, nein) => setTimeout(() => nein(new Error("Zeitlimit")), frist))]);
// Zweimal in voller Größe (der erste Versuch mit Zeitlimit), dann die Vorschau; fehlt auch sie, bleibt das Foto weg
async function einFoto(pin, f) {
  for (const [voll, frist] of [[true, geduld()], [true, 0], [false, 0]]) {
    try {
      const anfrage = host.rpc("admin_photo", { p_pin: pin, p_team: f.teamId, p_position: f.position, p_full: voll, p_route: "echt" });
      const r = await (frist ? mitFrist(anfrage, frist) : anfrage);
      if (r && r.data) return await bildAus(r.data);
    } catch (e) { /* nächster Versuch */ }
  }
  return null;
}
let fotoStopp = null;   // beendet das Warten auf die restlichen Fotos ("Ohne die restlichen Fotos weiter")
async function fotosLaden(pin, liste, aktuell, fort) {
  const todo = liste.filter(f => !fotoCache.has(schluesselVon(f)));
  let fertig = liste.length - todo.length, stopp = false;
  const arbeiter = async () => {
    while (todo.length && aktuell() && !stopp) {
      const f = todo.shift(), r = await einFoto(pin, f);
      if (r && root) fotoCache.set(schluesselVon(f), r); else if (r) URL.revokeObjectURL(r.src);
      if (!stopp) fort(++fertig, liste.length);
    }
  };
  await Promise.race([Promise.all([arbeiter(), arbeiter(), arbeiter()]), new Promise(res => { fotoStopp = () => { stopp = true; res(); }; })]);
  fotoStopp = null;
  return liste.filter(f => !fotoCache.has(schluesselVon(f)));
}

function schriftenLaden() {
  const limit = new Promise(res => setTimeout(() => res(false), 8000));
  const laden = Promise.all(SCHNITTE.map(s => document.fonts.load(s, SCHRIFT_MUSTER)))
    .then(() => SCHNITTE.every(s => document.fonts.check(s, SCHRIFT_MUSTER))).catch(() => false);
  return Promise.race([laden, limit]);
}
function karteLaden() {
  if (window.PRAG_KARTE) return Promise.resolve(true);
  return new Promise(res => {
    const s = document.createElement("script");
    s.src = host.url("rueckblick-karte.js");
    s.onload = () => res(!!window.PRAG_KARTE); s.onerror = () => res(false);
    document.head.appendChild(s);
    setTimeout(() => res(!!window.PRAG_KARTE), 15000);
  });
}

// Bildschirm wach halten (wie wachHaltenPruefen() in index.html); nach visibilitychange neu
let wakeSperre = null, wachOk = null;
async function wach() {
  if (!root || document.hidden) return;
  try {
    if (!navigator.wakeLock) throw new Error("kein Wake Lock");
    if (!wakeSperre || wakeSperre.released) wakeSperre = await navigator.wakeLock.request("screen");
    wachOk = true;
  } catch (e) { wachOk = false; }
  const li = root && root.querySelector("#rb-wach");
  if (li) li.hidden = wachOk !== false;
}

/* ---------- Flächen vor der Show ---------- */
function panel(html) {
  $("#rb-buehne").dataset.art = "vorbereiten";
  $("#rb-ueber").innerHTML = `<div class="szene" style="opacity:1"><div class="schleier dicht"></div>${html}</div>`;
  skalieren();
}
const kopfHTML = titel => `<h1>${LOGO}${esc(titel)}</h1>`;
function sperreZeigen(text) {
  Z.phase = "sperre";
  panel(`<div class="v-panel" role="dialog" aria-label="Rückblick">${kopfHTML("Rückblick")}<div class="rb-fehler" role="alert">${esc(text)}</div>
    <a class="v-zurueck" href="#/admin">Zur Spielleitung</a></div>`);
}
function pinFrage(meldung) {
  Z.phase = "pin";
  panel(`<div class="v-panel" role="dialog" aria-label="PIN">${kopfHTML("Rückblick")}
    <div class="v-pin"><input id="rb-pin" type="password" placeholder="PIN" aria-label="PIN" autocomplete="current-password" autocapitalize="off" autocorrect="off" spellcheck="false" enterkeyhint="go"><button class="start" id="rb-pinok">Einloggen</button></div>
    ${meldung ? `<div class="rb-fehler" role="alert">${esc(meldung)}</div>` : ""}</div>`);
  const f = $("#rb-pin"), los = () => { const p = f.value.trim(); if (p) { host.pinSetzen(p); laden(); } };
  $("#rb-pinok").onclick = los; f.onkeydown = e => { if (e.key === "Enter") los(); };
  f.focus();
}
function ladeFehler(e) {
  if (/Falsche PIN/i.test(e.message || "")) { host.pinVergessen(); return pinFrage("Falsche PIN."); }
  Z.phase = "sperre";
  // K5: die Meldung der App spricht die Teams an ("Wartet kurz und tippt"); hier liest die Spielleitung
  const text = e.netz ? "Keine Verbindung zum Server. Prüfe das WLAN und versuche es erneut." : (e.message || "Die Daten kamen nicht an.");
  panel(`<div class="v-panel" role="dialog" aria-label="Rückblick">${kopfHTML("Rückblick")}<div class="rb-fehler" role="alert">${esc(text)}</div>
    <div class="v-fuss"><button class="start" id="rb-nochmal">Erneut versuchen</button></div>
    <a class="v-zurueck" href="#/admin">Zur Spielleitung</a></div>`);
  $("#rb-nochmal").onclick = () => laden();
}
// S21: die Ladezeile steht für sich (nicht im Listenraster, dort brach jedes Wort um); der Balken bleibt bei Karte und
// Schriften voll stehen
function ladePanel(zeile, n, von, mitAusweg) {
  Z.phase = "laden";
  panel(`<div class="v-panel" role="dialog" aria-label="Rückblick wird vorbereitet">${kopfHTML(modus === "probe" ? "Rückblick, Probe" : "Rückblick")}
    <p class="v-lade" id="rb-ladezeile">${esc(zeile)}</p>
    <div class="v-balken"><i id="rb-balken" style="width:${von ? Math.round(n / von * 100) : n ? 100 : 0}%"></i></div>
    ${mitAusweg ? `<div class="v-fuss"><button class="nochmal" id="rb-ohne" hidden>Ohne die restlichen Fotos weiter</button></div>` : ""}</div>`);
  const o = root.querySelector("#rb-ohne");
  if (o) { o.onclick = () => { if (fotoStopp) fotoStopp(); }; setTimeout(() => { if (o.isConnected) o.hidden = false; }, geduld()); }
}
function ladeFortschritt(n, von) {
  const z = root && root.querySelector("#rb-ladezeile"), b = root && root.querySelector("#rb-balken");
  if (z) z.textContent = `Fotos ${n} von ${von}`;
  if (b) b.style.width = Math.round(n / von * 100) + "%";
}

async function laden() {
  const nr = ++ladeNr, aktuell = () => nr === ladeNr && !!root;
  if (host.api !== API) return;
  ladePanel("Daten werden geholt");
  try {
    let roh;
    if (modus === "probe") roh = beispielDaten();
    else {
      const pin = host.pin();
      if (!pin) return pinFrage();
      const st = await host.rpc("admin_state", { p_pin: pin });
      if (!aktuell()) return;
      if (st.status !== "finished" || !st.startedAt) return sperreZeigen("Der Rückblick startet nach dem Spielende.");
      if (st.testMode) return sperreZeigen("Der Testmodus ist an. Der Rückblick zeigt nur das echte Spiel: im Reiter Stationen ausschalten.");
      const tracks = await host.rpc("admin_tracks", { p_pin: pin });
      if (!aktuell()) return;
      // Fotos der Teststation (route "test") und Teams, die es nicht mehr gibt, fallen weg
      const liste = ((await host.rpc("admin_photos", { p_pin: pin })) || []).filter(f => (f.route || "echt") === "echt" && (st.teams || []).some(t => t.id === f.teamId))
        .sort((a, b) => a.position - b.position || String(a.takenAt).localeCompare(String(b.takenAt)));
      if (!aktuell()) return;
      let fehlt = [];
      if (liste.length) { ladePanel(`Fotos 0 von ${liste.length}`, 0, liste.length, true); fehlt = await fotosLaden(pin, liste, aktuell, ladeFortschritt); }
      if (!aktuell()) return;
      roh = { state: st, tracks, photos: liste.filter(f => fotoCache.has(schluesselVon(f))).map(f => ({ ...f, ...fotoCache.get(schluesselVon(f)) })),
        fehlt: fehlt.map(f => `${f.teamName || ((st.teams || []).find(t => t.id === f.teamId) || {}).name || "Team"} Station ${f.position}`) };
    }
    D = aufbereiten(roh);
    D.fehlt = roh.fehlt || [];
    if (modus === "probe") D.fotos.forEach((f, i) => { f.ratio = i % 3 === 1 ? 4 / 3 : 3 / 4; f.src = fotoBild(f.team, f.position, f.ratio > 1); });
    const loeschDatum = D.st.photosDeleteOn || null;
    D.geloescht = !D.fotos.length && !D.fehlt.length && !!loeschDatum && loeschDatum <= new Date().toISOString().slice(0, 10) ? loeschDatum : null;
    // ausgenommene Fotos überleben ein Neuladen, aber nur die, die es noch gibt
    const da = new Set(D.fotos.map(f => f.teamId + ":" + f.position));
    OPT.aus = new Set([...ausLesen()].filter(k => da.has(k)));
    ladePanel("Karte und Schriften werden geholt", 1);
    kapitelBauen();
    const [schriftOk] = await Promise.all([schriftenLaden(), karteLaden()]);
    if (!aktuell()) return;
    D.schriftOk = schriftOk;
    grundkarte(); kartenElemente();
    await karteRastern();
    if (!aktuell()) return;
    vorbereiten();
  } catch (e) { if (aktuell()) ladeFehler(e); }
}
// Prüfstand: andere Rohdaten übernehmen, als wären sie geladen (16 Teams, Gruppe 10)
function uebernehmen(roh) {
  D = aufbereiten(roh); D.fehlt = []; D.schriftOk = true;
  D.fotos.forEach((f, i) => { f.ratio = i % 3 === 1 ? 4 / 3 : 3 / 4; f.src = fotoBild(f.team, f.position, f.ratio > 1); });
  OPT.aus = new Set();
  kapitelBauen(); grundkarte(); kartenElemente(); karteRastern(); vorbereiten();
}

/* =====================================================================
   Vorbereiten, Fotos durchsehen, Tastenhilfe
   ===================================================================== */
// M5: das zuletzt gezeigte Kapitel dieser Sitzung (nach einem Neuladen)
function gemerktesKapitel() {
  try { const g = JSON.parse(sessionStorage.getItem(KAP_KEY) || "null");
    return g && g.modus === modus && g.id !== "vorspann" ? K.find(k => k.id === g.id) || null : null; } catch { return null; }
}
function vorbereitenHTML() {
  const d = D, ohne = d.teams.filter(t => t.ohneGps && t.sts.length), idle = d.teams.filter(t => !t.sts.length);
  const nichtIm = d.teams.filter(t => !t.place), imZiel = d.teams.length - nichtIm.length;
  const keineStandorte = d.teams.length > 1 && d.teams.every(t => t.ohneGps);
  const nFotos = d.fotos.length, plural = (n, a, b) => `${n} ${n === 1 ? a : b}`;
  const fehltNamen = d.fehlt.length > 6 ? d.fehlt.slice(0, 6).join(", ") + ` und ${d.fehlt.length - 6} weitere` : d.fehlt.join(", ");
  const fotoZeile = d.fehlt.length ? `<li class="warn">${ACHTUNG}<span>${plural(d.fehlt.length, "Foto", "Fotos")} nicht geladen<button class="nochmal" id="rb-nochmal">Erneut versuchen</button></span>
        <small>${esc(fehltNamen)}${nFotos ? `. ${plural(nFotos, "Gruppenfoto", "Gruppenfotos")} geladen` : ""}</small></li>`
    : d.geloescht ? `<li class="warn">${ACHTUNG}<span>Fotos am ${datumKurz(d.geloescht)} gelöscht (Löschdatum)</span></li>`
    : nFotos ? `<li class="ok">${HAKEN}<span>${plural(nFotos, "Gruppenfoto", "Gruppenfotos")} geladen</span>${d.st.photosDeleteOn ? `<small>Gelöscht am ${datumKurz(d.st.photosDeleteOn)}</small>` : ""}</li>` : "";
  const abbrueche = d.teams.filter(t => t.gpsHinweis);
  const gpsKlein = keineStandorte ? "Standortdaten gelöscht: Wege aus den Check-ins"
    : [ohne.length ? `${ohne.map(t => esc(t.name)).join(", ")} ohne GPS: Weg aus den Check-ins, gestrichelt` : "",
       ...abbrueche.map(t => esc(t.gpsHinweis)),
       idle.length ? `${idle.map(t => esc(t.name)).join(", ")} ohne Check-in: bleibt am Start` : ""].filter(Boolean).join(". ");
  const gpsWarn = ohne.length || abbrueche.length || keineStandorte;
  const finale = K.some(k => k.art === "spalten");
  const gemerkt = gemerktesKapitel();
  const spruenge = K.filter(k => k.id !== "vorspann" && !/^award\d/.test(k.id));
  return `<div class="szene" style="opacity:1"><div class="schleier dicht"></div>
    <div class="v-spruenge">Direkt zu ${spruenge.map(k => `<button data-sprung="${k.id}">${esc(k.name)}</button>`).join("")}</div>
    <div class="v-panel" role="dialog" aria-label="Rückblick vorbereiten">
    ${kopfHTML(modus === "probe" ? "Rückblick, Probe" : "Rückblick")}
    <ul class="v-liste">
      ${modus === "probe" ? `<li class="warn">${ACHTUNG}<span>Beispieldaten, nichts davon aus einem echten Spiel</span></li>` : ""}
      <li class="${imZiel ? "ok" : "warn"}">${imZiel ? HAKEN : ACHTUNG}<span>Spiel beendet um <span class="nw">${uhr(d.tEndUhr)} Uhr</span>, ${imZiel} von ${d.teams.length} Teams im Ziel</span>
        ${!imZiel ? `<small>Kein Team im Ziel: die Show endet ohne Rangliste und Siegerehrung</small>`
          : nichtIm.length ? `<small>Beim Spielende unterwegs: ${nichtIm.map(t => esc(t.name)).join(", ")}</small>` : ""}</li>
      <li class="${gpsWarn ? "warn" : "ok"}">${gpsWarn ? ACHTUNG : HAKEN}<span>${d.teams.length - d.teams.filter(t => t.ohneGps).length} von ${d.teams.length} Teams mit GPS-Route</span>
        ${gpsKlein ? `<small>${gpsKlein}</small>` : ""}</li>
      ${fotoZeile}
      ${d.hatKarte ? (d.karteFertig ? "" : `<li class="warn">${ACHTUNG}<span>Karte nicht vorbereitet, die Kartenkapitel ruckeln<button class="nochmal" id="rb-raster">Erneut versuchen</button></span></li>`)
        : `<li class="warn">${ACHTUNG}<span>Grundkarte nicht geladen, die Bühne zeigt Papier mit Höhenlinien</span></li>`}
      ${d.schriftOk ? `<li class="ok">${HAKEN}<span>Alles geladen, die Show läuft jetzt auch ohne Netz</span></li>`
        : `<li class="warn">${ACHTUNG}<span>Schrift nicht geladen, die Bühne zeigt eine Ersatzschrift<button class="nochmal" id="rb-nochmal2">Erneut versuchen</button></span></li>`}
      <li class="warn" id="rb-wach" hidden>${ACHTUNG}<span>Bildschirmschoner am Laptop ausschalten.</span></li>
    </ul>
    <div class="v-opt">
      ${nFotos ? `<label><input type="checkbox" id="rb-oFotos" ${OPT.fotos ? "checked" : ""}><span>Gruppenfotos zeigen</span></label>
      <button class="rb-link" id="rb-oDurch">Fotos durchsehen${OPT.aus.size ? ` (${OPT.aus.size} aus)` : ""}</button>` : ""}
      ${finale ? `<label><input type="checkbox" id="rb-oHalt" ${OPT.anhalten ? "checked" : ""}><span>Vor und nach jedem Koffer-Platz anhalten</span></label>` : ""}
      <label><input type="checkbox" id="rb-oRand" ${OPT.rand ? "checked" : ""}><span>Rand für Fernseher</span></label>
      <label><input type="checkbox" id="rb-oRuhig" ${ruhig ? "checked" : ""}><span>Bewegung reduzieren${systemRuhig && !ruhig ? '<small class="v-hinweis">Dieser Rechner meldet reduzierte Bewegung. Die Show läuft trotzdem mit Bewegung.</small>' : ""}</span></label>
    </div>
    <div class="v-fuss"><button class="start" id="rb-oStart">Rückblick starten</button>
      ${gemerkt ? `<button class="weiter-bei" id="rb-oWeiter">Weiter bei ${esc(gemerkt.name)}</button>` : ""}
      <span class="dauer">bis zum Abspann etwa <b class="tab">${mmss(gesamt())} min</b></span></div>
    <div class="v-tasten"><span><kbd>Leertaste</kbd> Start und Pause</span><span><kbd>→</kbd> <kbd>←</kbd> Kapitel</span><span><kbd>F</kbd> Vollbild</span><span><kbd>H</kbd> alle Tasten</span></div>
    ${modus === "probe" ? "" : `<button class="v-zurueck" id="rb-oZurueck">Zur Spielleitung</button>`}
  </div>${fernHTML()}</div>`;
}
function vorbereiten() {
  fernStarten();   // ab Vorbereiten: Befehle vom Handy, Stand fürs Handy (Nachtrag 37); vor dem Block, damit er weiß, ob sie läuft
  Z.phase = "vorbereiten"; Z.spielt = false; Z.haelt = false; knopf(); $("#rb-buehne").dataset.art = "vorbereiten";
  if (Z.szene) { Z.szene.remove(); Z.szene = null; } if (Z.alt) { Z.alt.remove(); Z.alt = null; }
  $("#rb-pulse").innerHTML = ""; $("#rb-koepfe").style.opacity = ""; $("#rb-stationen").style.opacity = ""; $("#rb-grund").style.opacity = "";
  zeichneKarte(D.t0, einpassen(D.uebersicht, VOLL_B), { spuren: "keine", koepfe: false });
  $("#rb-ueber").innerHTML = vorbereitenHTML();
  skalieren();   // das Panel ist erst jetzt da: Größe über der Leiste neu berechnen
  const an = (id, fn) => { const x = root.querySelector(id); if (x) fn(x); };
  // S10: nach dem Umschalten den Fokus abgeben, sonst schaltet die nächste Leertaste den Haken statt zu starten
  an("#rb-oFotos", x => x.onchange = e => { e.target.blur(); OPT.fotos = e.target.checked; kapitelBauen(); vorbereiten(); });
  an("#rb-oHalt", x => x.onchange = e => { e.target.blur(); OPT.anhalten = e.target.checked; kapitelBauen(); vorbereiten(); });
  an("#rb-oRand", x => x.onchange = e => { e.target.blur(); rand(e.target.checked); });
  an("#rb-oRuhig", x => x.onchange = e => { e.target.blur(); ruhig = e.target.checked; vorbereiten(); });
  an("#rb-oDurch", x => x.onclick = durchsehen);
  an("#rb-oStart", x => x.onclick = () => starten());
  an("#rb-oWeiter", x => x.onclick = () => { const g = gemerktesKapitel(); starten(g ? g.id : undefined); });
  an("#rb-oZurueck", x => x.onclick = e => { e.currentTarget.blur(); frage(); });
  an("#rb-nochmal", x => x.onclick = () => laden());
  an("#rb-nochmal2", x => x.onclick = () => laden());
  an("#rb-raster", x => x.onclick = () => karteRastern().then(() => { if (root && Z.phase === "vorbereiten") vorbereiten(); }));
  root.querySelectorAll("#rb-ueber [data-sprung]").forEach(b => b.onclick = () => { b.blur(); starten(b.dataset.sprung); });
  const li = root.querySelector("#rb-wach"); if (li) li.hidden = wachOk !== false;
  leisteSpur();
  fernBinden();
}
function durchsehen() {
  Z.phase = "durchsehen";   // M8: solange hier gewählt wird, startet weder Leertaste noch Pfeil die Show
  const reihen = D.stationen.map(s => { const f = D.fotos.filter(x => x.position === s.position);
    return f.length ? `<div class="d-reihe"><span class="nr">${s.position}</span>${f.map(x => `<button class="d-bild ${OPT.aus.has(x.teamId + ":" + x.position) ? "aus" : ""}" data-id="${x.teamId}:${x.position}" title="${esc(x.team.name)}"><img src="${x.src}" alt=""><span>${x.team.emoji}</span></button>`).join("")}</div>` : ""; }).join("");
  $("#rb-ueber").innerHTML = `<div class="szene" style="opacity:1"><div class="schleier dicht"></div><div class="d-panel" role="dialog" aria-label="Fotos durchsehen">
    <h2>Fotos durchsehen</h2><p>Antippen nimmt ein Foto aus dem Rückblick. Gelöscht wird nichts.</p>
    <div class="d-reihen">${reihen}</div><button class="fertig" id="rb-dFertig">Fertig</button></div></div>`;
  root.querySelectorAll("#rb-ueber .d-bild").forEach(b => b.onclick = () => { const id = b.dataset.id; OPT.aus.has(id) ? OPT.aus.delete(id) : OPT.aus.add(id); b.classList.toggle("aus"); b.blur(); ausSchreiben(); });
  $("#rb-dFertig").onclick = () => { kapitelBauen(); vorbereiten(); };
  leisteFortschritt();
}
function hilfe() {
  const h = root.querySelector("#rb-hilfeBox");
  if (h) { h.remove(); return; }
  const d = document.createElement("div"); d.id = "rb-hilfeBox"; d.className = "szene"; d.style.cssText = "opacity:1;z-index:20";
  d.innerHTML = `<div class="rb-hilfe" role="dialog" aria-label="Tasten"><h2>Tasten</h2><table>
    <tr><td><kbd>Leertaste</kbd> <kbd>K</kbd> <kbd>F5</kbd></td><td>Start, Pause, am Halt weiter</td></tr>
    <tr><td><kbd>→</kbd> <kbd>Bild ↓</kbd> <kbd>Enter</kbd></td><td>Weiter: am Halt aufdecken oder weiter, sonst nächstes Kapitel</td></tr>
    <tr><td><kbd>←</kbd> <kbd>Bild ↑</kbd></td><td>Zurück: Kapitel von vorn, zweimal: Kapitel davor</td></tr>
    <tr><td><kbd>Pos1</kbd> <kbd>Ende</kbd></td><td>Zum Anfang, zur Rangliste</td></tr>
    <tr><td><kbd>F</kbd></td><td>Vollbild an und aus</td></tr>
    <tr><td><kbd>B</kbd> <kbd>.</kbd></td><td>Bild schwarz; noch einmal: weiter, wo die Show war</td></tr>
    <tr><td><kbd>T</kbd></td><td>Hell oder dunkel</td></tr>
    <tr><td><kbd>R</kbd></td><td>Rand für Fernseher an und aus</td></tr>
    <tr><td><kbd>H</kbd> <kbd>Esc</kbd></td><td>Diese Hilfe zu</td></tr></table></div>`;
  $("#rb-buehne").appendChild(d);
}

/* =====================================================================
   Fernbedienung (Nachtrag 37, SPIEL.md §17). Das Handy der Spielleitung (rueckblick-fernbedienung.html) schreibt
   Befehle in die Datenbank (rb_befehl); die Show holt sie im 1-s-Takt ab (rb_poll) und führt sie aus wie die Tasten,
   durch dieselben Sperren (M1, M2, M3, M8). Ihren Stand meldet sie bei jeder Änderung und sonst alle 4 s
   (rb_status_setzen), mit der Moderationshilfe, die nur das Handy zeigt (Spoiler, nie am Beamer). Kein Realtime,
   eine Anfrage zugleich, nichts davon im Bild-Takt. Fehler bleiben still, der nächste Takt versucht es wieder; kennt
   die Datenbank die Funktionen nicht (Migration fehlt), hört die Show auf zu fragen. Auch in der Probe (Friedrich
   17.10.: den Demo-Rückblick vom Handy steuern): Befehle und Stand laufen dort ebenso über die Datenbank, nur die
   Daten der Show sind Beispieldaten. Die PIN fragt der Block im Vorbereiten beim Aktivieren ab (nur sessionStorage,
   sj.pin); ist sie aus der Spielleitung schon da, startet die Fernbedienung gleich. Ohne Handy bleibt alles wie
   vorher: Tastatur und Presenter.
   ===================================================================== */
const FERN_TAKT = 1000, FERN_HERZ = 4000, FERN_HANDY = 10000, FERN_DATEI = "rueckblick-fernbedienung.html";
// nr: letzte Befehlsnummer, die die Show kennt (null: noch nicht übernommen); handy: letztes Lebenszeichen des Handys;
// meldung: Fehler beim Aktivieren (falsche PIN, kein Netz)
const F = { an: false, gen: 0, uhr: 0, nr: null, kern: "", modFuer: "", mod: [], gesendet: 0, handy: 0, fehlt: false, qr: "", meldung: "" };
const fernLink = () => new URL(FERN_DATEI, location.href).href;   // ohne Hash und Query, nie mit PIN
const ohneFunktion = e => !!e && (e.code === "PGRST202" || /Could not find the function/i.test(e.message || ""));
function fernStarten() {
  if (F.an || F.fehlt || !root || !host || !host.pin()) return;
  Object.assign(F, { an: true, nr: null, kern: "", gesendet: 0 });
  fernTakt(++F.gen);
}
function fernStoppen() {
  if (!F.an) return;
  F.an = false; F.gen++; clearTimeout(F.uhr);
  // Stand mit der Moderation (Teamnamen) löschen; das Handy zeigt dann "Keine Show gefunden"
  const pin = host && host.pin();
  if (pin) host.rpc("rb_ende", { p_pin: pin }).catch(() => { /* still: verfällt nach 6 s am Handy */ });
}
async function fernTakt(gen) {
  const aktuell = () => F.an && gen === F.gen && !!root && !!D;
  if (!aktuell()) return;
  const pin = host.pin();
  try {
    const r = await host.rpc("rb_poll", { p_pin: pin, p_seit: F.nr });
    if (!aktuell()) return;
    if (r && r.nr != null) {
      // erster Abruf: nur die Nummer übernehmen, ein Befehl von vorher wirkt nicht
      const tun = F.nr != null && r.befehl;
      F.nr = r.nr;
      if (tun) { F.handy = Date.now(); fernBefehl(r.befehl); }
    }
    const st = fernStatus();
    if (st.kern !== F.kern || Date.now() - F.gesendet >= FERN_HERZ) {
      const a = await host.rpc("rb_status_setzen", { p_pin: pin, p_status: st.daten });
      if (!aktuell()) return;
      F.kern = st.kern; F.gesendet = Date.now();
      if (a && a.handy_alter_s != null) F.handy = Math.max(F.handy, Date.now() - a.handy_alter_s * 1000);
      fernAnzeige();
    }
  } catch (e) {
    if (ohneFunktion(e) && gen === F.gen) { F.fehlt = true; F.an = false; fernAnzeige(); return; }
    // PIN falsch (in der Probe aus einer alten Sitzung, oder inzwischen geändert): aus, der Block fragt neu
    if (/Falsche PIN/i.test(e.message || "") && gen === F.gen) {
      F.an = false; F.meldung = "Falsche PIN."; if (modus === "probe") host.pinVergessen(); fernAnzeige(); return;
    }
    // Netz weg, Server 5xx, Zeitlimit: still; die Show läuft, der nächste Takt fragt wieder
  }
  if (aktuell()) F.uhr = setTimeout(() => fernTakt(gen), FERN_TAKT);
}
// Ein Befehl vom Handy wirkt wie die Taste: dieselben Funktionen, dieselben Sperren
function fernBefehl(b) {
  if (!root || !D || frageOffen()) return;   // Rückfrage "verlassen?" offen: das entscheidet der Laptop
  // wie jede Taste außer B: im Schwarzbild holt sie erst das Bild zurück (M3)
  if (b !== "schwarz" && $("#rb-schwarz").classList.contains("an")) { schwarz(); return; }
  const tat = { weiter, zurueck, pause: () => spielPause(true), schwarz, ende: zumEnde,
    start: () => { if (Z.phase === "vorbereiten") starten(); } }[b];
  if (tat) tat();
}
// Stand für das Handy. kern ändert sich nur mit Kapitel, Zustand oder Befehl (nicht mit jedem Bild): dann gleich senden
function fernStatus() {
  const show = Z.phase === "show", k = show ? K[Z.i] : null, w = zustandWorte();
  const kapitel = ["laden", "pin", "sperre"].includes(Z.phase) ? "Rückblick wird geladen" : w.name;
  const kern = { phase: Z.phase, id: k ? k.id : null, kapitel, zustand: w.zustand, schwarz: !!root.querySelector("#rb-schwarz.an"),
    spielt: show && Z.spielt, haelt: Z.haelt, hNr: Z.hNr, endHalt: Z.endHalt, nr: F.nr, i: show ? Z.i : -1, n: K.length, fotos: OPT.fotos };
  const schluessel = JSON.stringify(kern);
  if (schluessel !== F.modFuer) { F.mod = moderation().filter(Boolean); F.modFuer = schluessel; }
  return { kern: schluessel, daten: { v: 1, ...kern, probe: modus === "probe", text: kapitel + (w.zustand ? ", " + w.zustand : ""), vorbei: vorbeiMs(), gesamt: gesamt(),
    endlos: w.endlos, mod: F.mod } };
}

/* ---------- Moderation: kurze Bausteine je Kapitelart, du-Form, nur fürs Handy ---------- */
const ohneTags = s => String(s).replace(/<[^>]+>/g, "");
const hms = m => { const s = Math.round(m / 1000); return Math.floor(s / 3600) + ":" + String(Math.floor(s / 60) % 60).padStart(2, "0") + ":" + String(s % 60).padStart(2, "0"); };
const abstand = m => Math.round(m / 1000) >= 3600 ? hms(m) : mmss(m);
const leuteText = t => { const m = t.members, n = m.length;
  return `${n} ${n === 1 ? "Person" : "Leute"}${n ? ` (${m.slice(0, 2).join(", ")}${n > 2 ? ", …" : ""})` : ""}`; };
const platzTeam = p => D.rang.find(t => t.place === p);
function platzText(t) {
  const erster = platzTeam(1), zweiter = platzTeam(2);
  const ab = t.place === 1 ? (zweiter ? `, ${abstand(zweiter.netto - t.netto)} vor Platz 2` : "") : erster ? `, ${abstand(t.netto - erster.netto)} hinter dem Ersten` : "";
  return `${t.name}, ${leuteText(t)}, Zeit ${hms(t.netto)}${ab}${t.gleich.length ? ` (${t.gleich.join(", ")})` : ""}`;
}
const awardText = a => `${a.titel}: ${a.team.name}, ${ohneTags(a.zeile)}.`;
function kapitelKurz(k) {
  if (!k) return null;
  if (k.art === "award" && !k.intro) return k.award.titel;
  return k.name;
}
// was nach diesem Kapitel kommt; beim nächsten Award gleich mit Team und Wert
function danach(i) {
  const n = K[i + 1]; if (!n) return null;
  return n.art === "award" && !n.intro ? `Danach: ${awardText(n.award)}` : `Danach: ${kapitelKurz(n)}.`;
}
function moderation() {
  if (!D) return [];
  const leute = D.teams.reduce((n, t) => n + t.members.length, 0);
  if (Z.phase === "vorbereiten" || Z.phase === "durchsehen")
    return [`${D.teams.length} Teams, ${leute} Leute, ${D.stationen.length} Stationen.`, `Gleich: ${kapitelKurz(K[0])}.`];
  if (Z.phase !== "show") return ["Der Rückblick wird am Laptop geladen."];
  const k = K[Z.i], nach = danach(Z.i);
  if (k.art === "titel") return [`Begrüßen: Stadtjagd Prag, ${D.teams.length} Teams, ${leute} Leute, ${D.stationen.length} Stationen.`, nach];
  if (k.art === "fakten") {
    const w = faktenWerte(), bier = w[2].wechsel;
    return Z.hNr >= 1 ? [`${zahl(bier.wert)} Liter Bier verbrannt.`, nach]
      : [`${zahl(w[0].wert)} Personenkilometer, etwa ${zahl(w[1].wert)} Schritte, ${zahl(w[2].wert)} halbe Brathähnchen verbrannt.`, `Weiter schaltet auf ${zahl(bier.wert)} Liter Bier.`];
  }
  if (k.art === "gruppen") {
    const gr = [...new Set(D.teams.map(t => t.gruppe))].sort((a, b) => a - b).map(g => uhr(D.teams.find(t => t.gruppe === g).startAt));
    return [`${gr.length} Startgruppen, Start ${gr.join(", ")} Uhr. Gewertet wird die Zeit ab dem eigenen Start.`, nach];
  }
  if (k.art === "karte") {
    const im = D.teams.filter(t => t.place).length;
    return Z.endHalt ? [`Zeitraffer zu Ende: ${im} von ${D.teams.length} Teams im Ziel.`, nach] : [`Läuft. Gleich: ${kapitelKurz(K[Z.i + 1]) || "Abspann"}.`];
  }
  if (k.art === "rangliste") {
    const oben = [...Array(k.top)].map((_, j) => platzTeam(j + 1)).filter(Boolean);
    if (k.id === "rangliste") {
      const unten = k.zeilen.filter(t => !t.place || t.place > k.top), vierter = platzTeam(k.top + 1);
      if (!unten.length) return [`Weiter zeigt die Rangliste ohne die ersten ${k.top}.`, nach];
      if (Z.hNr === 0) return ["Alle Zeiten rattern, aufgedeckt ist noch nichts.",
        `Weiter deckt ${unten.length} Teams von unten auf${vierter ? `, zuletzt Platz ${vierter.place}: ${vierter.name}, ${hms(vierter.netto)}` : ""}.`];
      return [Z.endHalt ? `Die Plätze ab ${k.top + 1} stehen.` : `Die Plätze ab ${k.top + 1} decken sich auf.`, nach];
    }
    if (Z.hNr === 0) return [`Weiter lässt die Zeiten der ersten ${oben.length} einrasten, die Teams bleiben verdeckt: ${oben.slice().reverse().map(t => `Platz ${t.place} ${hms(t.netto)}`).join(", ")}.`];
    return [`Die Zeiten der ersten ${oben.length} stehen, die Teams sind noch verdeckt.`, nach];
  }
  if (k.art === "award") {
    if (k.intro) return [`${D.awards.length} ${D.awards.length === 1 ? "Award" : "Awards"}, die Koffer-Teams gehen dabei leer aus.`, nach];
    return [awardText(k.award), nach];
  }
  if (k.art === "spalten") {
    if (!k.auf.length) return [`${kapitelKurz(k)}: Platz ${k.sp.folge.map(t => t.place).join(", ")} mit Zeit und Weg, die Teams verdeckt.`, nach];
    const p = k.auf[0].platz, t = platzTeam(p), weiterNach = p > 1 ? `Danach: Platz ${p - 1}.` : nach;
    if (Z.hNr === 0) return [`Als Nächstes wird Platz ${p} aufgedeckt: ${platzText(t)}.`, weiterNach];
    const koffer = `Kofferübergabe an ${t.name}${t.leitung ? `, Teamleitung ${t.leitung}` : ""}.`;
    if (!Z.haelt && !Z.endHalt) return [`Platz ${p}: ${t.name} wird aufgedeckt.`, koffer];
    return [`Platz ${p}: ${t.name}, Zeit ${hms(t.netto)}.`, koffer, `Alle: ${t.members.join(", ")}.`, weiterNach];
  }
  if (k.art === "sieger") return [`Siegerbild: ${[1, 2, 3].map(platzTeam).filter(Boolean).map(t => `Platz ${t.place} ${t.name}`).join(", ")}.`, nach];
  if (k.art === "abspann") return ["Läuft endlos."];
  return [k.name];
}

/* ---------- Block im Vorbereiten: Link als QR-Code, ob ein Handy da ist ---------- */
let qrLaedt = null;
function fernQr() {
  if (F.qr) return F.qr;
  if (window.qrcode) { const q = window.qrcode(0, "M"); q.addData(fernLink()); q.make(); return F.qr = q.createSvgTag({ cellSize: 4, margin: 2, scalable: true }); }
  // vendor/qrcode.js (MIT) lädt erst beim ersten Gebrauch, wie beim Mitlese-Link in index.html
  if (!qrLaedt) qrLaedt = new Promise((ok, nein) => { const s = document.createElement("script"); s.src = "vendor/qrcode.js"; s.onload = ok; s.onerror = nein; document.head.appendChild(s); })
    .then(() => fernAnzeige(), () => { qrLaedt = null; });
  return "";
}
function fernInnen() {
  if (F.fehlt) return `<h2>Handy als Fernbedienung</h2><p>Die Datenbank kennt die Fernbedienung noch nicht.</p>`;
  const kopf = `<h2>Handy als Fernbedienung</h2><div class="v-qr" role="img" aria-label="QR-Code der Fernbedienung">${fernQr()}</div>`;
  // noch nicht aktiv (Probe ohne PIN, oder die PIN stimmt nicht mehr): PIN der Spielleitung hier eingeben
  if (!F.an) return kopf + `<form class="v-fernpin" id="rb-fernForm"><input id="rb-fernPin" type="password" placeholder="PIN" aria-label="PIN der Spielleitung"
      autocomplete="current-password" autocapitalize="off" autocorrect="off" spellcheck="false" enterkeyhint="go"><button class="start" type="submit">Aktivieren</button></form>
    ${F.meldung ? `<p class="warn" role="alert">${esc(F.meldung)}</p>` : ""}`;
  const da = F.handy && Date.now() - F.handy < FERN_HANDY;
  return kopf + `<p>PIN am Handy eingeben</p>${da ? `<p class="da">${HAKEN}<span>Handy verbunden</span></p>` : ""}`;
}
const fernHTML = () => `<div class="v-fern" id="rb-fern" role="group" aria-label="Handy als Fernbedienung">${fernInnen()}</div>`;
function fernAnzeige() {
  const box = root && root.querySelector("#rb-fern"); if (!box) return;
  const neu = fernInnen(); if (box.dataset.innen !== neu) { box.innerHTML = neu; box.dataset.innen = neu; fernBinden(); }
}
// Aktivieren: PIN mit rb_poll prüfen, dann nur in sessionStorage merken (host.pinSetzen, sj.pin) und starten
function fernBinden() {
  const f = root && root.querySelector("#rb-fernForm"); if (!f) return;
  f.onsubmit = async ev => {
    ev.preventDefault();
    const inp = f.querySelector("input"), knopf = f.querySelector("button"), p = inp.value.trim(); if (!p) return;
    knopf.disabled = true;
    try {
      await host.rpc("rb_poll", { p_pin: p, p_seit: null });
      if (!root) return;
      host.pinSetzen(p); F.meldung = ""; inp.blur(); fernStarten();
    } catch (e) {
      if (ohneFunktion(e)) F.fehlt = true;
      else F.meldung = /Falsche PIN/i.test(e.message || "") ? "Falsche PIN." : "Keine Verbindung zum Server.";
    } finally { if (knopf.isConnected) knopf.disabled = false; }
    fernAnzeige();
  };
}

/* ---------- Bühne skalieren ---------- */
function skalieren() {
  if (!root) return;
  const s = Math.min(innerWidth / 1920, innerHeight / 1080) * (OPT.rand ? .94 : 1), b = $("#rb-buehne");
  b.style.transform = `scale(${s}) translate(-50%,-50%)`;
  // Die Leiste liegt fest am Fensterrand, nicht auf der Bühne: ihre Höhe in Bühnen-Pixel, damit Panels darüber bleiben
  const l = $("#rb-leiste"), unten = l ? l.offsetHeight / s - Math.max(0, (innerHeight - 1080 * s) / 2) / s : 0;
  b.style.setProperty("--unten", Math.max(0, unten) + "px");
  // Passt das Vorbereiten-Panel nicht über die Leiste, wird es kleiner statt abgeschnitten (kein Scrollen auf dem Beamer);
  // wird es dabei klein, fällt die Tastenzeile weg (K10)
  const v = root.querySelector(".v-panel");
  if (v) {
    const oben = root.querySelector(".v-spruenge") ? 168 : 0, frei = 1080 - Math.max(0, unten) - 48 - oben, tz = v.querySelector(".v-tasten");
    if (tz) { tz.hidden = false; if (frei / v.offsetHeight < .9) tz.hidden = true; }
    v.style.setProperty("--vs", Math.min(1, frei / v.offsetHeight));
    v.style.setProperty("--oben", oben + "px");
  }
}

/* =====================================================================
   Öffnen und Schließen. Alles, was die Show an document hängt, kommt hier hinein und beim Schließen wieder heraus.
   ===================================================================== */
let abhoerer = [], mqDunkel = null, mqFn = null;
function hoere(ziel, typ, fn) { ziel.addEventListener(typ, fn); abhoerer.push([ziel, typ, fn]); }
// Notbremse (Taste Ende, "Zum Ende" am Handy): springt zur Rangliste
function zumEnde() {
  if (!startbar()) return;
  const ziel = K.find(x => x.id === "rangliste") || K[Math.max(0, K.length - 2)];
  if (Z.phase !== "show") return starten(ziel.id);
  Z.spielt = true; geheZu(K.indexOf(ziel)); knopf();
}
function taste(e) {
  if (!root) return;
  const k = e.key;
  // F5 lädt sonst die Seite neu, und die geladenen Fotos sind weg (Präsentations-Klicker senden F5 für "Präsentation starten")
  if (k === "F5" && !e.altKey && !e.ctrlKey && !e.metaKey) { e.preventDefault(); if (!e.repeat && !frageOffen()) spielPause(true); return; }
  if (e.altKey || e.ctrlKey || e.metaKey) return;
  if (e.target && e.target.matches && e.target.matches("input[type=password],input[type=text],textarea")) return;   // PIN tippen
  // Rückfrage offen: nur Esc (bleiben); Enter und Leertaste lösen den Knopf mit dem Fokus aus
  if (frageOffen()) { if (k === "Escape") { e.preventDefault(); bleiben(); } return; }
  if ((k === " " || k === "Enter") && document.activeElement && document.activeElement.matches("input,button,a") && Z.phase !== "show") return;
  const nur = fn => () => { if (startbar()) fn(); };
  const tat = {
    " ": () => spielPause(true), k: () => spielPause(true), K: () => spielPause(true),
    ArrowRight: weiter, PageDown: weiter, Enter: weiter, n: weiter, N: weiter,
    ArrowLeft: zurueck, PageUp: zurueck, Backspace: zurueck, p: zurueck, P: zurueck,
    Home: nur(() => { if (Z.phase !== "show") return starten(); Z.spielt = true; geheZu(0); knopf(); }),
    End: zumEnde,
    f: vollbild, F: vollbild, t: thema, T: thema, b: schwarz, B: schwarz, ".": schwarz, r: () => rand(), R: () => rand(),
    h: hilfe, H: hilfe, "?": hilfe, Escape: () => { const h = root.querySelector("#rb-hilfeBox"); if (h) h.remove(); }
  }[k];
  // M2: gehaltene Taste rast nicht durch die Kapitel (außer H)
  if (e.repeat && !["h", "H", "?"].includes(k)) { if (tat) e.preventDefault(); return; }
  if ($("#rb-schwarz").classList.contains("an") && !["b", "B", "."].includes(k)) { if (D) schwarz(); else $("#rb-schwarz").classList.remove("an"); e.preventDefault(); return; }
  if (!tat) return;
  e.preventDefault(); tat();
}
function oeffnen(h, art) {
  if (root) beenden();
  host = h; modus = art === "probe" ? "probe" : "echt";
  Object.assign(Z, { phase: "laden", i: 0, lokal: 0, spielt: false, haelt: false, hNr: 0, extra: 0, letzt: 0, wechsel: 0, vorSchwarz: false, vorFrage: false, szene: null, alt: null });
  D = null; K = []; OPT.aus = new Set(); fortStand = "";
  Object.assign(F, { fehlt: false, handy: 0, modFuer: "", meldung: "" });
  root = document.createElement("div");
  root.id = "rueckblick"; root.className = "still"; root.setAttribute("role", "region"); root.setAttribute("aria-label", "Rückblick");
  root.innerHTML = GERUEST;
  document.body.appendChild(root);
  const app = document.getElementById("app"); if (app) app.inert = true;
  document.body.classList.add("fest");
  $("#rb-leiste").addEventListener("click", e => { const b = e.target.closest("button"); if (!b) return;
    ({ zurueck, weiter, spiel: spielPause, thema, voll: vollbild, hilfe })[b.dataset.k](); b.blur(); });
  $("#rb-schwarz").addEventListener("click", () => { if (D) schwarz(); });
  leisteBedienen();
  $("#rb-bleiben").addEventListener("click", bleiben);
  $("#rb-verlassen").addEventListener("click", verlassen);
  hoere(document, "mousemove", leisteZeigen);
  hoere(document, "keydown", taste);
  hoere(window, "resize", skalieren);
  hoere(document, "visibilitychange", wach);
  hoere(window, "popstate", zurueckImBrowser);
  hoere(window, "beforeunload", vorUnload);
  history.pushState({ rueckblick: 1 }, "", location.href);   // M5: Zurück im Browser landet erst bei der Rückfrage
  mqDunkel = matchMedia("(prefers-color-scheme: dark)");
  mqFn = () => { if (D && !document.documentElement.dataset.theme && Z.phase !== "show") themaNeu(); };
  mqDunkel.addEventListener("change", mqFn);
  skalieren();
  wach();
  rafId = requestAnimationFrame(takt);
  if (h.api !== API) { Z.phase = "sperre"; panel(`<div class="v-panel" role="dialog" aria-label="Rückblick">${kopfHTML("Rückblick")}<div class="rb-fehler" role="alert">Seite und Rückblick sind aus verschiedenen Fassungen: die Seite neu laden.</div></div>`); return; }
  laden();
}
function beenden() {
  if (!root) return;
  fernStoppen();   // Fernbedienung aus, Stand mit der Moderation in der Datenbank löschen (rb_ende)
  ladeNr++; rasterNr++;   // laufende Ladevorgänge und Rasterungen verlaufen im Sand (K3)
  if (fotoStopp) fotoStopp();
  cancelAnimationFrame(rafId);
  abhoerer.forEach(([z, t, f]) => z.removeEventListener(t, f)); abhoerer = [];
  if (mqDunkel && mqFn) mqDunkel.removeEventListener("change", mqFn); mqDunkel = mqFn = null;
  const alt = root.querySelector("#rb-grund image.karte"); if (alt && alt.dataset.url) URL.revokeObjectURL(alt.dataset.url);
  fotoCache.forEach(f => URL.revokeObjectURL(f.src)); fotoCache.clear();   // Fotos nur im Speicher: beim Verlassen weg
  if (wakeSperre) { try { wakeSperre.release(); } catch (e) { /* schon frei */ } wakeSperre = null; }
  clearTimeout(leisteUhr);
  root.remove(); root = null; D = null; K = [];
  const app = document.getElementById("app"); if (app) app.inert = false;
  document.body.classList.remove("fest");
}

window.RueckblickShow = { api: API, oeffnen, beenden, offen: () => !!root };
// Für Prüfungen und Bildschirmfotos (tools/pruefstand/rueckblick.py): RB.zeige("platz1", 4000) steht, spielt nicht
window.RB = {
  zeige: (id, lokal = 0) => { $("#rb-ueber").innerHTML = ""; const i = K.findIndex(x => x.id === id); geheZu(i < 0 ? 0 : i, lokal); Z.spielt = false; knopf(); zeichnen(); },
  starten,
  kapitel: () => K.map(k => ({ id: k.id, art: k.art, name: k.name, dur: k.dur, endlos: !!k.endlos, halte: (k.halte || []).map(h => h.t), sperren: k.sperren || [],
    fotos: k.roll ? k.roll.fotos.length : 0 })),
  zustand: () => ({ phase: Z.phase, i: Z.i, id: K[Z.i] && K[Z.i].id, lokal: Z.lokal, spielt: Z.spielt, haelt: Z.haelt, hNr: Z.hNr, leiste: root ? $("#rb-lKap").textContent : "" }),
  gesamt, D: () => D, vorbereiten, opt: () => ({ fotos: OPT.fotos, anhalten: OPT.anhalten, rand: OPT.rand, ruhig }),
  // Fernbedienung (fernbedienung.py)
  fern: () => ({ an: F.an, nr: F.nr, fehlt: F.fehlt, handy: F.handy, link: fernLink() }), fernStatus: () => D ? fernStatus().daten : null,
  kartenZaehler: () => kartenZaehler, rohPunkte: () => D ? D.rohPunkte : 0,
  awards: () => ({ liste: D.awards.map(a => ({ id: a.id, team: a.team.name, wert: a.wert, zeile: a.zeile })),
    kennzahlen: D.kennzahlen.map(x => ({ team: x.t.name, place: x.t.place, ...x.z })) }),
  test: { aufbereiten, kapitel: kapitelFuer, ohneAusreisser, kopf, kennzahlen, ring: ringMass,
    sechzehn: () => uebernehmen(beispielDaten(16)),
    // für die unabhängige Rechnung der Awards in Python
    export: () => ({ t0: D.t0, start: D.start.xy, prizeCount: D.prizeCount, stationen: D.stationen.map(s => ({ position: s.position, xy: s.xy })),
      teams: D.teams.map(t => ({ id: t.id, name: t.name, place: t.place, ohneGps: t.ohneGps, sts: t.sts.map(s => ({ position: s.position, ein: s.ein, ok: s.ok })),
        pts: t.pts.map(p => ({ x: p.x, y: p.y, t: p.t, g: !!p.g, acc: p.acc ?? null })) })) }) }
};
})();
