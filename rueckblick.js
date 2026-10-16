/* Rückblick-Show der Stadtjagd. Spezifikation: docs/superpowers/specs/2026-10-15-rueckblick-show-design.md, SPIEL.md §16.
   Wird von index.html nur beim Öffnen von #/rueckblick nachgeladen (zusammen mit rueckblick.css und
   rueckblick-karte.js), damit die Handys im Spiel nichts davon tragen. Die Show liegt in einem eigenen Container
   außerhalb von #app: index.html zeichnet sie nie neu und fragt in dieser Ansicht nichts ab.
   Alles steht in einer Funktion, damit keine Namen aus index.html überschrieben werden; was die Show von dort braucht,
   kommt über das Objekt host (rpc, pin, farbe, emoji, api). Stimmt host.api nicht mit API überein, sind index.html und
   diese Datei aus verschiedenen Fassungen: die Show meldet das und startet nicht. */
(function () {
"use strict";
const API = 1;
let host = null, root = null, modus = "echt", rafId = 0, ladeNr = 0;
const $ = s => root.querySelector(s);
const MIN = 60000;
const MEDAILLE = ["🥇", "🥈", "🥉"];

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


const beispielDaten = () => {
  const R = zufall(20261017);
  const T0 = new Date(2026, 9, 17, 14, 0, 12).getTime(), TEND = new Date(2026, 9, 17, 16, 40, 0).getTime();
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
  const NAMEN = ["Adler", "Delfin", "Einhorn", "Eule", "Flamingo", "Fuchs", "Igel", "Otter", "Panda", "Pinguin", "Tiger", "Wolf"];
  const TEMPO = { Adler: .78, Eule: .84, Tiger: .88, Fuchs: .93, Wolf: .97, Panda: 1, Delfin: 1.04, Pinguin: 1.08, Einhorn: 1.2, Flamingo: 1.3, Otter: 1.12, Igel: 1.38 };
  const GEHEN = [8, 10, 9, 10, 11], RAETSEL = [6, 9, 7, 11, 8];
  const STECKT = { Otter: 5, Igel: 4 };              // rätselt beim Spielende noch an dieser Station
  const OHNE_GPS = new Set(["Igel"]);                 // Handy der Teamleitung hat nie gemeldet
  const LUECKE = { Otter: [T0 + 31 * MIN, T0 + 45 * MIN] };   // Handy in der Tasche
  const OHNE_FOTO = new Set(["Delfin:1", "Pinguin:3", "Wolf:4"]);
  const VOR = ["Anna", "Ben", "Clara", "David", "Emre", "Fatma", "Greta", "Hannes", "Ida", "Jonas", "Kira", "Lars", "Mia", "Nils", "Olga", "Paul",
    "Rosa", "Sven", "Tara", "Uwe", "Vera", "Wim", "Yara", "Zoe", "Aylin", "Bruno", "Carla", "Dennis", "Elif", "Finn", "Gül", "Henrik"];
  const NACH = ["Berger", "Demir", "Keller", "Krüger", "Hoffmann", "Schröder", "Wagner", "Neumann", "Schulz", "Hofmann", "Franke", "Martin",
    "Yılmaz", "Lehmann", "Peters", "Graf", "Vogel", "Kaya", "Brandt", "Busch", "Arnold", "Lorenz", "Sommer", "Winter"];
  const leute = new Set(); while (leute.size < 96) leute.add(VOR[Math.floor(R() * VOR.length)] + " " + NACH[Math.floor(R() * NACH.length)]);
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
    const f = TEMPO[name], seite = (R() - .5) * 16, pts = [], sts = [];
    const punkt = (x, y, t, s = 4) => pts.push([x + (R() - .5) * s * 2, y + (R() - .5) * s * 2, t]);
    let t = T0 + R() * 1.5 * MIN, cur = P(START.lat, START.lng), fertig = null;
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
      if (STECKT[name] === k + 1) { for (let tt = an; tt < TEND; tt += 60000) punkt(ziel[0] + 18, ziel[1] - 10, tt, 6); break; }
      const geloest = ein + RAETSEL[k] * f * (0.7 + R() * 0.6) * MIN;
      st.solvedAt = new Date(geloest).toISOString();
      if (!OHNE_FOTO.has(name + ":" + (k + 1))) fotos.push({ teamName: name, position: k + 1, stationName: s.name, route: "echt", takenAt: new Date(geloest + (0.6 + R() * 0.6) * MIN).toISOString() });
      const weg = geloest + (1.2 + R() * 0.8) * MIN;
      for (let tt = an; tt < weg; tt += 60000) punkt(ziel[0] + (R() - .5) * 20, ziel[1] + (R() - .5) * 20, tt, 3);
      t = weg; cur = ziel;
      if (k === 4) fertig = weg + (0.8 + R() * 1.6) * MIN;
    }
    if (fertig) for (let tt = t; tt < TEND; tt += 60000) punkt(cur[0] - 20 + R() * 40, cur[1] - 20 + R() * 40, tt, 4);
    const id = "t" + (ti + 1);
    const lu = LUECKE[name];
    const roh = OHNE_GPS.has(name) ? [] : pts.filter(p => !lu || p[2] < lu[0] || p[2] > lu[1]).map(p => { const l = LL(p[0], p[1]); return [+l[0].toFixed(6), +l[1].toFixed(6), Math.round(p[2])]; });
    const leute8 = alle.slice(ti * 8, ti * 8 + 8).sort((a, b) => a.localeCompare(b, "de"));
    teams.push({ id, name, members: leute8, leaderName: leute8[Math.floor(R() * 8)], solved: sts.filter(s => s.solvedAt).length,
      finishedAt: fertig ? new Date(fertig).toISOString() : null, place: null });
    tracks.push({ id, name, points: roh, pointCount: roh.length, stations: sts });
    fotos.forEach(x => { if (x.teamName === name) x.teamId = id; });
  });
  teams.filter(t => t.finishedAt).sort((a, b) => a.finishedAt.localeCompare(b.finishedAt)).forEach((t, i) => t.place = i + 1);
  return {
    state: { status: "finished", testMode: false, route: "echt", prizeCount: 3, selfieOn: true, photosDeleteOn: "2026-10-19",
      startedAt: new Date(T0).toISOString(), finishedAt: new Date(TEND).toISOString(), start: START, stations: STATIONEN, teams },
    tracks: { status: "finished", startedAt: new Date(T0).toISOString(), finishedAt: new Date(TEND).toISOString(), teams: tracks },
    photos: fotos
  };
};

// Platzhalter für ein Gruppenselfie (im echten Spiel: admin_photo mit p_full = true)
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
    '<path d="M250 360 L350 360 L330 300 L270 300 Z"/><path d="M300 305 L410 80" stroke="#fff" stroke-width="16" stroke-linecap="round"/>'][pos - 1];
  const n = 5 + Math.floor(R() * 4); let leute = "";
  for (let i = 0; i < n; i++) {
    const x = 70 + (460 / (n - 1)) * i + (R() - .5) * 30, y = 520 + (R() - .5) * 60 + (i % 2) * 34, r = 46 + R() * 10;
    leute += `<g opacity="${(0.62 + R() * 0.2).toFixed(2)}"><circle cx="${x.toFixed(0)}" cy="${y.toFixed(0)}" r="${r.toFixed(0)}"/><ellipse cx="${x.toFixed(0)}" cy="${(y + r + 120).toFixed(0)}" rx="${(r * 1.7).toFixed(0)}" ry="${(r * 1.9).toFixed(0)}"/></g>`;
  }
  // Querformat: dieselben Zutaten auf 800x600 verteilt (im echten Spiel kommt das Format aus dem Foto selbst)
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
   Aufbereiten: aus den RPC-Antworten werden Teams, Spuren, Ereignisse,
   Kapitel (Spezifikation 6.3). Reine Funktionen von roh, ohne Zugriff auf die Seite.
   ===================================================================== */
const LUECKE_M = 50, LUECKE_MS = 90000;   // wie LUECKE_M/LUECKE_MS in index.html (gestrichelte Strecken)
const MAX_MS = 15 / 3.6;                   // schneller als 15 km/h läuft hier niemand
const OPT = { fotos: true, anhalten: true, aus: new Set() };
let D = null;   // aufbereitete Daten
let K = [];     // Kapitel

const dist = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1]);
const ms = iso => iso ? Date.parse(iso) : null;
const uhr = t => new Date(t).toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" });
const uhrS = t => new Date(t).toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
function dauer(m) { m = Math.round(m / 60000); return m < 60 ? m + " min" : Math.floor(m / 60) + ":" + String(m % 60).padStart(2, "0") + " h"; }
const km = m => (m / 1000).toFixed(1).replace(".", ",") + " km";

// GPS-Sprünge (6.3): nur einzelne Ausreißer fallen weg, also ein Punkt, der zu beiden Nachbarn springt, während die
// Nachbarn zueinander passen. Ein Vergleich mit dem "letzten behaltenen Punkt" würde nach einer Tram- oder Taxifahrt
// jeden weiteren Punkt verwerfen, weil der Bezugspunkt stehen bleibt.
function ohneAusreisser(pts) {
  const v = (a, b) => dist([a.x, a.y], [b.x, b.y]) / Math.max(1, (b.t - a.t) / 1000);
  return pts.filter((p, k, a) => {
    if (!k || k === a.length - 1) return true;
    const vor = a[k - 1], nach = a[k + 1];
    return !(v(vor, p) > MAX_MS && v(p, nach) > MAX_MS && v(vor, nach) <= MAX_MS);
  });
}

function aufbereiten(roh) {
  const st = roh.state, t0 = ms(st.startedAt), tEnd = ms(st.finishedAt) || ms(roh.tracks.finishedAt);
  const alle = (st.stations || []).slice().sort((a, b) => a.position - b.position)
    .map(s => ({ ...s, xy: s.lat != null && s.lng != null ? P(s.lat, s.lng) : null }));   // ohne Koordinaten: fehlt auf der Karte
  const start = st.start && st.start.lat != null ? { ...st.start, xy: P(st.start.lat, st.start.lng) }
    : { name: "Start", xy: (alle.find(s => s.xy) || { xy: [0, 0] }).xy };
  const anker = [start.xy, ...alle.filter(s => s.xy).map(s => s.xy)];
  const teams = (st.teams || []).map((t, i) => {
    const tr = (roh.tracks.teams || []).find(x => x.id === t.id) || { points: [], stations: [] };
    // Punkte nur aus dem Spiel, nur nahe der Route (1 km), ohne einzelne Sprünge
    let pts = (tr.points || []).filter(p => p[2] >= t0 - MIN && p[2] <= tEnd)
      .map(p => { const xy = P(p[0], p[1]); return { x: xy[0], y: xy[1], t: p[2] }; })
      .filter(p => Math.min(...anker.map(a => dist(a, [p.x, p.y]))) < 1000);
    pts = ohneAusreisser(pts);
    const sts = (tr.stations || []).map(s => ({ position: s.position, ein: ms(s.checkedInAt), ok: ms(s.solvedAt) })).sort((a, b) => a.position - b.position);
    const ohneGps = pts.length < 2;
    if (ohneGps) {   // Weg aus den Check-ins, ganz gestrichelt; ganz ohne Check-in bleibt das Team am Start
      pts = [{ x: start.xy[0], y: start.xy[1], t: t0 }];
      sts.forEach(s => { const sx = alle.find(x => x.position === s.position); if (!sx || !sx.xy || !s.ein) return;
        pts.push({ x: sx.xy[0], y: sx.xy[1], t: s.ein }); if (s.ok) pts.push({ x: sx.xy[0], y: sx.xy[1], t: s.ok }); });
      pts.forEach((p, k) => p.g = k > 0 && dist([p.x, p.y], [pts[k - 1].x, pts[k - 1].y]) > 1);
    } else {
      pts.forEach((p, k) => { if (!k) return; const q = pts[k - 1], m = dist([p.x, p.y], [q.x, q.y]), dt = p.t - q.t;
        p.g = m > LUECKE_M || (dt > LUECKE_MS && m > 15); });
    }
    let weg = 0; if (!ohneGps) { let a = pts[0]; for (const q of pts) { const dd = dist([a.x, a.y], [q.x, q.y]); if (dd > 15) { weg += dd; a = q; } } }
    return { id: t.id, name: t.name, emoji: host.emoji(t.name), farbe: host.farbe(i), members: t.members || [], place: t.place,
      fertig: ms(t.finishedAt), pts, sts, ohneGps, weg, solved: sts.filter(s => s.ok).length,
      luecken: !ohneGps && pts.some(p => p.g) };
  });
  // Reihenfolge wie die öffentliche Rangliste: Platz, dann gelöste Stationen, dann letzte Lösung
  const letzte = t => Math.max(0, ...t.sts.filter(s => s.ok).map(s => s.ok)) || Infinity;
  const rang = [...teams].sort((a, b) => (a.place || 999) - (b.place || 999) || b.solved - a.solved || letzte(a) - letzte(b));
  const ereignisse = [];
  teams.forEach(t => t.sts.forEach(s => { if (s.ein) ereignisse.push({ t: s.ein, team: t, art: "ein", pos: s.position });
    if (s.ok) ereignisse.push({ t: s.ok, team: t, art: "ok", pos: s.position }); }));
  ereignisse.sort((a, b) => a.t - b.t);
  const fotos = (roh.photos || []).filter(f => (f.route || "echt") === "echt" && teams.some(t => t.id === f.teamId))
    .map(f => ({ ...f, team: teams.find(t => t.id === f.teamId), takenAt: ms(f.takenAt), ratio: f.ratio || 3 / 4 }));
  // Grenzen der Kapitel: Zeitpunkt, an dem die Hälfte der Teams mit Fortschritt die Station gelöst hat. Teams ohne jeden
  // Check-in zählen nicht mit (sie stehen im Ring am Start). Mindestens 2 min nach der vorigen Grenze, nie hinter dem
  // Spielende; liegt die Grenze dort, endet das Kapitel bei finishedAt.
  const mitSpiel = teams.filter(t => t.sts.length).length, haelfte = Math.max(1, Math.ceil(mitSpiel / 2));
  const grenzen = [t0];
  for (const s of alle) {
    const ok = teams.map(t => (t.sts.find(x => x.position === s.position) || {}).ok).filter(Boolean).sort((a, b) => a - b);
    const vorige = grenzen[grenzen.length - 1];
    if (!ok.length || vorige >= tEnd) break;
    const wunsch = ok.length >= haelfte ? ok[haelfte - 1] : ok[ok.length - 1];
    grenzen.push(Math.min(tEnd, Math.max(wunsch, vorige + 2 * MIN)));
  }
  return { st, t0, tEnd, start, stationen: alle, teams, rang, ereignisse, fotos, grenzen, prizeCount: st.prizeCount ?? 3 };
}



/* ---------- Kamera: Inhalt (Meter) in einen Bühnenbereich einpassen ---------- */
const KARTE_B = { x: 0, w: 1320 }, VOLL_B = { x: 0, w: 1920 };
function rahmen(punkte, pad, minW) {
  punkte = punkte.filter(Boolean);   // eine Station ohne Koordinaten fehlt auf der Karte, Kapitel und Fotos bleiben
  if (!punkte.length) punkte = [[0, 0]];
  let x0 = Math.min(...punkte.map(p => p[0])) - pad, x1 = Math.max(...punkte.map(p => p[0])) + pad;
  let y0 = Math.min(...punkte.map(p => p[1])) - pad, y1 = Math.max(...punkte.map(p => p[1])) + pad;
  if (x1 - x0 < minW) { const c = (x0 + x1) / 2; x0 = c - minW / 2; x1 = c + minW / 2; }
  if (y1 - y0 < minW * .6) { const c = (y0 + y1) / 2; y0 = c - minW * .3; y1 = c + minW * .3; }
  return { x0, x1, y0, y1 };
}
function einpassen(b, bereich, rand = 70) {
  const s = Math.min((bereich.w - 2 * rand) / (b.x1 - b.x0), (1080 - 2 * rand) / (b.y1 - b.y0));
  const bx = (b.x0 + b.x1) / 2, by = (b.y0 + b.y1) / 2;
  return { cx: bx + (960 - (bereich.x + bereich.w / 2)) / s, cy: by, s };
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

/* ---------- Kapitel (Spezifikation 3): reine Funktion von Daten und Auswahl ---------- */
// Zufällige Reihenfolge, bei jedem Vorbereiten neu (Fisher-Yates)
function zufallsReihe(a) { const r = a.slice(); for (let i = r.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [r[i], r[j]] = [r[j], r[i]]; } return r; }
// Sechs Spalten, jedes Foto in seinem Format in die kürzeste Spalte; Dauer nach Zahl der Fotos, am Ende 2,5 s nur die Karte
function abspannRolle(fotos) {
  const SP = 6, X0 = 80, B = 1760, LUECKE = 28, UNTER = 44, cw = (B - (SP - 1) * LUECKE) / SP, hoehe = Array(SP).fill(0), slots = [];
  fotos.forEach((f, i) => { const c = hoehe.indexOf(Math.min(...hoehe)), h = cw / f.ratio;
    slots[i] = { x: X0 + c * (cw + LUECKE), y: hoehe[c], w: cw, h }; hoehe[c] += h + UNTER + LUECKE; });
  const lauf = Math.min(42000, Math.max(16000, fotos.length * 650)), gesamt = Math.max(...hoehe);
  return { slots, gesamt, lauf, dur: lauf + 2500, tempo: (gesamt + 1080) / lauf };
}
function kapitelFuer(d, opt) {
  const k = [], sXY = pos => (d.stationen.find(s => s.position === pos) || {}).xy || null;
  const uebersicht = rahmen([d.start.xy, ...d.stationen.map(s => s.xy), P(50.0925, 14.4170)], 110, 900);
  d.uebersicht = uebersicht;
  const aus = f => opt.aus.has(f.teamId + ":" + f.position);
  const mitFotos = opt.fotos && d.fotos.some(f => !aus(f));
  const wegDauer = mitFotos ? 18000 : 24000;
  k.push({ id: "vorspann", art: "titel", dur: 7500, kam: einpassen(uebersicht, VOLL_B), name: "Vorspann" });
  k.push({ id: "start", art: "karte", dur: 5500, von: d.t0, bis: d.t0, name: "Start",
    kam: einpassen(rahmen([d.start.xy, d.stationen.length ? d.stationen[0].xy : null], 220, 800), KARTE_B) });
  for (let i = 1; i < d.grenzen.length; i++) {
    const s = d.stationen[i - 1], pos = s.position, vor = i === 1 ? d.start.xy : d.stationen[i - 2].xy, bis = d.grenzen[i];
    const koepfe = d.teams.map(t => kopf(t, bis)).filter(Boolean);
    k.push({ id: "weg" + pos, art: "karte", dur: wegDauer, von: d.grenzen[i - 1], bis, station: pos, name: "Weg zu Station " + pos,
      kam: einpassen(rahmen([vor, s.xy, ...koepfe], 140, 760), KARTE_B) });
    const fotos = mitFotos ? d.fotos.filter(f => f.position === pos && !aus(f)) : [];
    if (fotos.length) {   // nur wenn es Fotos gibt: nie ein leeres Fotokapitel
      const ein = t => ((t.sts.find(x => x.position === pos) || {}).ein) || Infinity;
      fotos.sort((a, b) => ein(a.team) - ein(b.team) || a.takenAt - b.takenAt);
      k.push({ id: "fotos" + pos, art: "fotos", dur: 1200 + fotos.length * 1000 + 2600, station: pos, fotos, name: "Fotos Station " + pos });
    }
  }
  const letzte = d.grenzen.length - 1;
  if (letzte >= 1 && d.tEnd - d.grenzen[letzte] > 3 * MIN) {
    const koepfe = d.teams.map(t => kopf(t, d.tEnd)).filter(Boolean), lpos = d.stationen[letzte - 1].position;
    k.push({ id: "ziel", art: "karte", dur: 10000, von: d.grenzen[letzte], bis: d.tEnd, station: lpos, ziel: true, name: "Bis zum Spielende",
      kam: einpassen(rahmen([sXY(lpos), ...koepfe], 160, 760), KARTE_B) });
  }
  const koffer = d.rang.filter(t => t.place && t.place <= d.prizeCount).sort((a, b) => b.place - a.place);
  koffer.forEach(t => k.push({ id: "platz" + t.place, art: "platz", team: t, dur: t.place === 1 ? 14000 : 12500,
    halt: t.place === 1 ? 3600 : 2600, name: "Platz " + t.place, kam: einpassen(uebersicht, VOLL_B) }));
  k.push({ id: "alle", art: "alle", dur: 15000, name: "Alle Teams", kam: einpassen(uebersicht, VOLL_B) });
  const abFotos = mitFotos ? zufallsReihe(d.fotos.filter(f => !aus(f))) : [];
  if (abFotos.length) {
    const roll = abspannRolle(abFotos);
    k.push({ id: "abspann", art: "abspann", dur: roll.dur, name: "Abspann", fotos: abFotos, roll, kam: einpassen(uebersicht, VOLL_B) });
  } else {
    k.push({ id: "abspann", art: "abspann", dur: 9000, name: "Alle Routen", kam: einpassen(rahmen([d.start.xy, ...d.stationen.map(s => s.xy)], 150, 900), { x: 560, w: 1360 }) });
  }
  k.forEach((x, i) => { x.i = i; if (!x.kam) x.kam = einpassen(uebersicht, VOLL_B); });
  return k;
}
function kapitelBauen() { K = kapitelFuer(D, OPT); }


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
   und die Kamera verschiebt nur noch dieses Bild. Routen, Stationen und Namen bleiben Vektor darüber. */
let rasterNr = 0;
function karteRastern() {
  const KA = window.PRAG_KARTE; if (!KA || !D.hatKarte) return Promise.resolve(false);
  return new Promise(fertig => {
  const nr = ++rasterNr, css = getComputedStyle(root), f = n => css.getPropertyValue(n).trim();
  // Ausschnitt: alles, was irgendeine Kamera der Show zeigt (Vereinigung der Sichtfenster), plus 250 m Rand
  const fenster = (typeof K !== "undefined" ? K : []).map(k => k.kam).filter(Boolean)
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
    if (nr !== rasterNr) { fertig(false); return; }
    const c = document.createElement("canvas"); c.width = W; c.height = H;
    c.getContext("2d").drawImage(img, 0, 0, W, H);
    c.toBlob(b => {
      if (nr !== rasterNr || !b) { fertig(false); return; }
      const g = $("#rb-grund"), alt = g.querySelector("image.karte");
      [...g.children].forEach(e => { if (e.tagName !== "rect") e.remove(); });   // Vektor-Ersatz weg, nur noch das Bild
      if (alt && alt.dataset.url) URL.revokeObjectURL(alt.dataset.url);
      const bu = URL.createObjectURL(b);
      const im = el("image", { class: "karte", href: bu, x: x0, y: y0, width: w, height: h, preserveAspectRatio: "none" }, g);
      im.dataset.url = bu; D.karteFertig = true; fertig(true);
    }, "image/png");
  };
  img.onerror = () => fertig(false);
  img.src = url;
  setTimeout(() => fertig(false), 10000);
  });
}

let teamEl = {}, kopfEl = {}, stEl = [], namenEl = [];
function kartenElemente() {
  letzteKarte = null;
  const sp = $("#rb-spuren"); sp.innerHTML = ""; teamEl = {};
  D.stationen.filter(s => s.xy).forEach(s => el("circle", { class: "radius", cx: s.xy[0], cy: s.xy[1], r: s.radiusM || 50 }, sp));
  D.teams.forEach(t => {
    const g = el("g", {}, sp);
    teamEl[t.id] = { g, rand: el("path", { class: "rand" }, g), luecke: el("path", { class: "luecke", stroke: t.farbe }, g), spur: el("path", { class: "spur", stroke: t.farbe }, g) };
  });
  const sg = $("#rb-stationen"); sg.innerHTML = ""; stEl = [];
  const startG = el("g", {}, sg); el("circle", { class: "startbadge", r: 28 }, startG); el("path", { class: "haus", d: HAUS }, startG);
  stEl.push({ g: startG, xy: D.start.xy });
  D.stationen.filter(s => s.xy).forEach(s => { const g = el("g", {}, sg); el("circle", { class: "stbadge", r: 28 }, g);
    const tx = el("text", { class: "stnr", "text-anchor": "middle", y: 11 }, g); tx.textContent = s.position; stEl.push({ g, xy: s.xy }); });
  const kg = $("#rb-koepfe"); kg.innerHTML = ""; kopfEl = {};
  D.teams.forEach(t => { const g = el("g", { class: "kopf" }, kg);
    if (t.ohneGps) el("circle", { class: "ohne", r: 38 }, g);
    el("circle", { class: "k", r: 30, fill: t.farbe }, g);
    const tx = el("text", { "text-anchor": "middle", y: 12 }, g); tx.textContent = t.emoji; kopfEl[t.id] = g; });
  const ng = $("#rb-namen"); ng.innerHTML = ""; namenEl = D.namen.map(n => { const tx = el("text", { class: n[3], "text-anchor": "middle" }, ng); tx.textContent = n[0]; return { tx, xy: P(n[1], n[2]) }; });
}

// Ankunftsreihenfolge je Ort für die Ringplätze (Start: Teamreihenfolge)
function ringPlatz(team, ortIdx) {
  if (ortIdx === 0) return D.teams.indexOf(team);
  const pos = D.stationen[ortIdx - 1].position;
  const rf = D.teams.map(t => ({ t, e: (t.sts.find(x => x.position === pos) || {}).ein || Infinity })).sort((a, b) => a.e - b.e);
  return rf.findIndex(x => x.t === team);
}
let ringCache = {};
let letzteKarte = null;
function zeichneKarte(T, kam, modus) {
  // modus: { spuren: "alle" | "keine" | Team, koepfe: bool, bis: Zeit für eine einzelne Spur }
  // Steht alles still (Abspann, Alle Teams), nichts neu zeichnen: das kostete die Hälfte der Bildrate (gemessen 16.10.)
  const sp = modus.spuren && modus.spuren.id ? modus.spuren.id : modus.spuren;
  const schluessel = [Math.round(T), kam.cx.toFixed(2), kam.cy.toFixed(2), kam.s.toFixed(5), sp, modus.koepfe, modus.bis == null ? "" : Math.round(modus.bis), Z.szene && Z.szene.dataset.k].join("|");
  if (schluessel === letzteKarte) return;
  letzteKarte = schluessel;
  const s = kam.s, vw = 1920 / s, vh = 1080 / s, vx = kam.cx - vw / 2, vy = kam.cy - vh / 2;
  $("#rb-welt").setAttribute("viewBox", `${vx.toFixed(2)} ${vy.toFixed(2)} ${vw.toFixed(2)} ${vh.toFixed(2)}`);
  // Quellenhinweis (ODbL) nur im Abspann, klein unten rechts (Entscheidung Friedrich 16.10.: sonst zu präsent)
  const osm = $("#rb-osm"); if (osm) osm.hidden = !(D.osmQuelle && K[Z.i] && K[Z.i].id === "abspann");
  const sx = p => [(p[0] - vx) * s, (p[1] - vy) * s];
  // Marken nur, solange sie ganz im Bild stehen (die Kamera zeigt nicht immer alle Stationen)
  stEl.forEach(e => { const q = sx(e.xy); e.g.setAttribute("transform", `translate(${q[0].toFixed(1)} ${q[1].toFixed(1)})`);
    e.g.style.display = q[0] < 32 || q[0] > 1888 || q[1] < 32 || q[1] > 1048 ? "none" : ""; });
  // Ortsnamen nur, solange sie ganz im Bild stehen: kein halber Name am Rand, keiner außerhalb der Bühne
  namenEl.forEach(n => { const q = sx(n.xy); n.tx.setAttribute("x", q[0].toFixed(0)); n.tx.setAttribute("y", q[1].toFixed(0));
    n.tx.style.display = q[0] < 90 || q[0] > 1830 || q[1] < 60 || q[1] > 1020 ? "none" : ""; });
  D.teams.forEach(t => {
    const e = teamEl[t.id], zeigen = modus.spuren === "alle" || modus.spuren === t;
    e.g.style.display = zeigen ? "" : "none";
    if (!zeigen) return;
    const bis = modus.spuren === t && modus.bis != null ? modus.bis : T;
    const p = t.pts, j = kopfIdx(p, bis);
    let fest = "", luecke = "";
    for (let i = 0; i <= j; i++) {
      const c = p[i].x.toFixed(1) + " " + p[i].y.toFixed(1);
      if (!i) { fest += "M" + c; continue; }
      if (p[i].g) { luecke += "M" + p[i - 1].x.toFixed(1) + " " + p[i - 1].y.toFixed(1) + "L" + c; fest += "M" + c; } else fest += "L" + c;
    }
    if (j >= 0 && j < p.length - 1) { const h = kopf(t, bis), c = h[0].toFixed(1) + " " + h[1].toFixed(1);
      if (p[j + 1].g) luecke += "M" + p[j].x.toFixed(1) + " " + p[j].y.toFixed(1) + "L" + c; else fest += "L" + c; }
    e.spur.setAttribute("d", fest); e.rand.setAttribute("d", fest); e.luecke.setAttribute("d", luecke);
  });
  // Köpfe: an einem Ort stehen die Teams im Ring, in der Reihenfolge ihrer Ankunft
  const orte = [D.start.xy, ...D.stationen.map(x => x.xy)];
  D.teams.forEach(t => {
    const g = kopfEl[t.id], h = modus.koepfe ? kopf(t, T) : null;
    if (!h) { g.style.display = "none"; return; }
    g.style.display = "";
    let best = 0, bd = Infinity; orte.forEach((o, i) => { const dd = o ? dist(o, h) : Infinity; if (dd < bd) { bd = dd; best = i; } });
    let q = sx(h);
    const w = glatt((70 - bd) / 45);
    if (w > 0) {
      const key = t.id + ":" + best, platz = ringCache[key] ?? (ringCache[key] = ringPlatz(t, best));
      const a = -Math.PI / 2 + platz * (Math.PI * 2 / 12), o = sx(orte[best]);
      const z = [o[0] + Math.cos(a) * 116, o[1] + Math.sin(a) * 116];
      q = [q[0] + (z[0] - q[0]) * w, q[1] + (z[1] - q[1]) * w];
    }
    g.setAttribute("transform", `translate(${q[0].toFixed(1)} ${q[1].toFixed(1)})`);
  });
}

/* =====================================================================
   Ablauf: Kapitel, Zeit, Pause, Halt vor dem Aufdecken
   ===================================================================== */
const Z = { phase: "laden", i: 0, lokal: 0, spielt: false, haelt: false, frei: false, extra: 0, letzt: 0, szene: null, alt: null };
const ruhig = matchMedia("(prefers-reduced-motion: reduce)").matches;
const kapitelZeit = (k, lokal) => k.von + (k.bis - k.von) * glatt(Math.min(1, lokal / k.dur));
function kamFuer(i, lokal) {
  const k = K[i], vorher = i > 0 ? K[i - 1].kam : k.kam;
  return ruhig ? k.kam : kamMisch(vorher, k.kam, glatt(lokal / 1800));
}
function letzteKarteVor(i) { for (let j = i; j >= 0; j--) if (K[j].art === "karte") return K[j]; return null; }

function geheZu(i, lokal = 0) {
  i = Math.max(0, Math.min(K.length - 1, i));
  Z.phase = "show"; Z.i = i; Z.lokal = lokal; Z.haelt = false; Z.frei = false; Z.extra = 0;
  szeneBauen();
  zeichnen();
}
function weiter() {
  if (!startbar()) return;
  if (Z.phase !== "show") return starten();
  if (Z.haelt) { Z.haelt = false; Z.frei = true; if (!Z.spielt) Z.spielt = true; return; }
  if (Z.i < K.length - 1) geheZu(Z.i + 1);
}
function zurueck() {
  if (Z.phase !== "show") return;
  if (Z.lokal > 1500) geheZu(Z.i); else geheZu(Z.i - 1);
}
function spielPause() {
  if (!startbar()) return;
  if (Z.phase !== "show") return starten();
  if (Z.haelt) return weiter();
  if (Z.i === K.length - 1 && Z.lokal >= K[Z.i].dur) { geheZu(0); Z.spielt = true; return; }
  Z.spielt = !Z.spielt; leisteZeigen(); knopf();
}
function starten() { $("#rb-ueber").innerHTML = ""; Z.spielt = true; geheZu(0); knopf(); }
function knopf() { const b = $("#rb-bSpiel"); b.querySelector("span").textContent = Z.phase !== "show" ? "Start" : Z.spielt ? "Pause" : "Abspielen";
  b.querySelector("svg").innerHTML = Z.spielt && Z.phase === "show" ? '<path d="M6 4h4v16H6zM14 4h4v16h-4z"/>' : '<path d="M7 4v16l13-8z"/>'; }

function takt(jetzt) {
  if (!root) return;
  const dt = Math.min(100, jetzt - (Z.letzt || jetzt)); Z.letzt = jetzt;
  if (Z.phase === "show") {
    const k = K[Z.i];
    if (Z.spielt) {
      if (k.halt && OPT.anhalten && !Z.frei && Z.lokal < k.halt && Z.lokal + dt >= k.halt) { Z.lokal = k.halt; Z.haelt = true; }
      if (Z.haelt) Z.extra += dt; else Z.lokal += dt;
      if (Z.lokal >= k.dur) { if (Z.i < K.length - 1) geheZu(Z.i + 1); else { Z.lokal = k.dur; Z.spielt = false; knopf(); } }
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
  if (k.art === "titel") s.innerHTML = vorspannHTML();
  if (k.art === "fotos") s.innerHTML = fotosHTML(k);
  if (k.art === "platz") s.innerHTML = platzHTML(k);
  if (k.art === "alle") s.innerHTML = alleHTML();
  if (k.art === "abspann") s.innerHTML = abspannHTML(k);
  box.appendChild(s); Z.szene = s; Z.altBis = 520; $("#rb-buehne").dataset.art = k.art;
  if (k.art === "karte") seiteFuellen(k);
  ringCache = {}; letzteKarte = null;
  leisteSpur();
}
const fakten = () => {
  const d = D, leute = d.teams.reduce((n, t) => n + t.members.length, 0);
  return { datum: new Date(d.t0).toLocaleDateString("de-DE", { weekday: "long", day: "numeric", month: "long", year: "numeric" }), leute,
    km: d.teams.reduce((n, t) => n + t.weg, 0) };
};
function vorspannHTML() {
  const f = fakten();
  return `<div class="schleier mittel"></div><div class="titel"><div class="logo">${LOGO}</div><h1>Stadtjagd</h1><div class="ort">Prag</div>
    <div class="fakten"><span>${f.datum}</span><span>${D.teams.length} Teams</span><span>${f.leute} Leute</span><span>${D.stationen.length} Stationen</span></div></div>`;
}
// Bühnen-Pixel, die unten für die feste Leiste frei bleiben müssen (skalieren() setzt --unten)
const untenFrei = () => parseFloat(getComputedStyle($("#rb-buehne")).getPropertyValue("--unten")) || 0;
// Fotowand: Reihen gleicher Höhe, jedes Foto in seinem eigenen Format (hoch oder quer), mittig, über der Leiste
function fotoRaster(fotos) {
  const B = 1760, OBEN = 236, UNTER = 86, ZEILE = 40, SPALTE = 32, MINU = 250, verf = 1080 - untenFrei() - 24 - OBEN;
  // Zelle = Foto, aber mindestens so breit, dass die Unterschrift ganz passt; das Foto steht mittig darin
  const zelle = (H, f) => Math.max(H * f.ratio, MINU);
  const reihenBei = H => { const rs = [[]]; let w = 0;
    fotos.forEach((f, i) => { const fw = zelle(H, f); if (rs[rs.length - 1].length && w + SPALTE + fw > B) { rs.push([]); w = 0; }
      w += (rs[rs.length - 1].length ? SPALTE : 0) + fw; rs[rs.length - 1].push(i); });
    return rs; };
  let H = 520, rs = reihenBei(H);
  while (H > 60 && rs.length * (H + UNTER) + (rs.length - 1) * ZEILE > verf) { H -= 4; rs = reihenBei(H); }
  const gh = rs.length * (H + UNTER) + (rs.length - 1) * ZEILE, y0 = OBEN + Math.max(0, (verf - gh) / 2), slots = [];
  rs.forEach((r, ri) => { const rw = r.reduce((a, i) => a + zelle(H, fotos[i]), 0) + (r.length - 1) * SPALTE;
    let x = (BREITE - rw) / 2;
    r.forEach(i => { const w = H * fotos[i].ratio, cw = zelle(H, fotos[i]);
      slots[i] = { x: x + (cw - w) / 2, y: y0 + ri * (H + UNTER + ZEILE), w, h: H, cx: x, cw }; x += cw + SPALTE; }); });
  return slots;
}
// Grundmaß einer Kachel: Hochformat 540x720, Querformat 720x540 (skaliert wird per transform)
const kachelB = f => f.ratio >= 1 ? 720 : 540, kachelH = f => f.ratio >= 1 ? 540 : 720;
function fotosHTML(k) {
  const s = D.stationen.find(x => x.position === k.station), f = k.fotos, zuerst = f[0] && f[0].team;
  const erst = D.teams.map(t => ({ t, e: (t.sts.find(x => x.position === k.station) || {}).ein })).filter(x => x.e).sort((a, b) => a.e - b.e)[0];
  k.slots = fotoRaster(f);
  return `<div class="schleier dicht"></div>
    <div class="f-kopf"><div class="nr">${k.station}</div><div><h2>${esc(s.name)}</h2></div>
      ${erst ? `<div class="zuerst"><small>zuerst da</small><b><span class="emo">${erst.t.emoji}</span> ${esc(erst.t.name)} <span class="tab">${uhr(erst.e)}</span></b></div>` : ""}</div>
    ${f.map((x, i) => `<div class="kachel" data-i="${i}" style="width:${kachelB(x)}px;height:${kachelH(x)}px"><img src="${x.src}" alt="Gruppenfoto ${esc(x.team.name)}"></div>
      <div class="unterschrift" data-u="${i}" style="left:${k.slots[i].cx}px;top:${k.slots[i].y + k.slots[i].h + 12}px;width:${k.slots[i].cw}px"><i style="background:${x.team.farbe}"></i><span class="emo">${x.team.emoji}</span><b class="nm">${esc(x.team.name)}</b><span class="zt">${uhr(x.takenAt)}</span></div>`).join("")}
    <div class="spot" id="rb-spot"></div>`;
}
function bestesFoto(t) {
  const f = D.fotos.filter(x => x.teamId === t.id && !OPT.aus.has(x.teamId + ":" + x.position)).sort((a, b) => b.position - a.position);
  return OPT.fotos ? f[0] : null;
}
function platzHTML(k) {
  const t = k.team, foto = bestesFoto(t), ziffern = uhrS(t.fertig).replace(/:/g, "");
  k.ziffern = ziffern; k.foto = !!foto;
  const mitte = foto ? 740 : 960, links = mitte - 560;
  const walzen = [0, 1, 2, 3, 4, 5].map(j => `${j === 2 || j === 4 ? '<span class="dp">:</span>' : ""}<div class="walze"><div class="band" data-w="${j}">${"0123456789012".split("").map(c => `<div>${c}</div>`).join("")}</div></div>`).join("");
  return `<div class="p-spalte" style="left:${links}px;width:1120px">
      <div class="p-titel" data-a="titel"><span class="emo">${MEDAILLE[t.place - 1] || "🧳"}</span>Platz ${t.place}</div>
      <div class="p-lbl" data-a="walzen">Koffer-Code eingegeben um</div>
      <div class="walzen" data-a="walzen">${walzen}</div>
      <div class="p-team" data-a="team"><div class="b" style="background:${t.farbe}">${t.emoji}</div>
        <div><div class="n">${esc(t.name)}</div><div class="m">${t.members.map(n => `<span class="nw">${esc(n)}</span>`).join(", ")}</div></div></div>
    </div>
    ${foto ? `<div class="p-foto" data-a="foto" style="transform:rotate(1.6deg)"><img src="${foto.src}" alt=""><small>Station ${foto.position}, ${uhr(foto.takenAt)}</small></div>` : ""}`;
}
function alleHTML() {
  const n = D.rang.length, spalten = n > 12 ? 4 : 4, reihen = Math.ceil(n / spalten);
  return `<div class="schleier dicht"></div><div class="a-kopf">Alle Teams</div>
    <div class="a-netz" style="grid-template-rows:repeat(${reihen},1fr)">${D.rang.map((t, i) => {
      const pl = t.place ? (t.place <= D.prizeCount ? `<span class="emo">${MEDAILLE[t.place - 1] || "🧳"}</span>Platz ${t.place}` : `Platz ${t.place}`)
        : "unterwegs";
      const z3 = t.place ? `im Ziel <span class="tab">${uhr(t.fertig)}</span>, nach ${dauer(t.fertig - D.t0)}` : `${t.solved} von ${D.stationen.length} Stationen`;
      return `<div class="a-karte" data-i="${i}" style="--c:${t.farbe}"><div class="z1"><span class="pl">${pl}</span><span class="nw">${t.ohneGps ? "ohne GPS" : km(t.weg)}</span></div>
        <div class="z2"><i style="background:${t.farbe}">${t.emoji}</i><b>${esc(t.name)}</b></div><div class="z3">${z3}</div></div>`; }).join("")}</div>`;
}

function abspannHTML(k) {
  if (k && k.roll) {
    const f = fakten();
    return `<div class="schleier mittel"></div><div class="rollfenster"><div class="rolle">${k.fotos.map((x, i) => { const sl = k.roll.slots[i];
      return `<div class="rk" style="left:${sl.x}px;top:${sl.y}px;width:${sl.w}px;height:${sl.h}px"><img src="${x.src}" alt="Gruppenfoto ${esc(x.team.name)}"></div>
        <div class="ru" style="left:${sl.x}px;top:${sl.y + sl.h + 8}px;width:${sl.w}px"><span class="emo">${x.team.emoji}</span>${esc(x.team.name)}<small>Station ${x.position}</small></div>`; }).join("")}</div></div>
      <div class="ab-karte"><h2>Stadtjagd Prag</h2><p>${D.teams.length} Teams, zusammen ${km(f.km)} gelaufen</p></div>`;
  }
  const f = fakten();
  return `<div class="ab-karte"><h2>Stadtjagd Prag</h2><p>${D.teams.length} Teams, zusammen ${km(f.km)} gelaufen</p></div>`;
}
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

/* ---------- Seitenleiste ---------- */
let seiteStand = {};
function seiteFuellen(k) {
  $("#rb-sKap").textContent = k.id === "start" ? "Start" : k.ziel ? "Zum Koffer" : "Weg zu";
  $("#rb-sName").textContent = k.id === "start" ? D.start.name : D.stationen.find(s => s.position === k.station).name;
  seiteStand = {};
}
function seiteZeichnen(k, T) {
  const uhrText = uhr(T), seit = T <= D.t0 ? `${D.teams.reduce((n, t) => n + t.members.length, 0)} Leute in ${D.teams.length} Teams` : `seit Start ${dauer(T - D.t0)}`;
  if (seiteStand.uhr !== uhrText) { $("#rb-sUhr").textContent = uhrText; seiteStand.uhr = uhrText; }
  const ende = k.ziel && T >= D.tEnd - 1000;
  const seitText = ende ? "Spielende" : seit;
  if (seiteStand.seit !== seitText) { $("#rb-sSeit").textContent = seitText; seiteStand.seit = seitText; }
  // Liste: am Start die Teams, unterwegs die letzten drei Ereignisse
  let html;
  if (k.id === "start") html = `<div class="legende">${D.teams.map(t => `<div><i style="background:${t.farbe}">${t.emoji}</i>${esc(t.name)}</div>`).join("")}</div>`;
  else {
    const ev = D.ereignisse.filter(e => e.t >= k.von && e.t <= T).slice(-3).reverse();
    html = ev.map(e => `<div class="ev"><span class="b" style="background:${e.team.farbe}">${e.team.emoji}</span><span class="n">${esc(e.team.name)}</span>
      <span class="z">${uhr(e.t)}</span><span class="w">${e.art === "ein" ? "an Station " + e.pos : "Station " + e.pos + " gelöst"}</span></div>`).join("");
  }
  if (seiteStand.liste !== html) { $("#rb-sListe").innerHTML = html; seiteStand.liste = html; }
  const jetzt = k.station || 0;
  const route = D.stationen.map((s, i) => `${i ? `<i class="${s.position <= jetzt - (k.ziel ? 0 : 1) ? "da" : ""}"></i>` : ""}<b class="${s.position < jetzt || (k.ziel && s.position === jetzt) ? "da" : s.position === jetzt ? "jetzt" : ""}">${s.position}</b>`).join("");
  if (seiteStand.route !== route) { $("#rb-sRoute").innerHTML = route; seiteStand.route = route; }
}

/* ---------- Ein Bild ---------- */
const ein = (lokal, ab, dauerMs = 480) => ruhig ? (lokal >= ab ? 1 : 0) : glatt((lokal - ab) / dauerMs);
function zeichnen() {
  if (Z.phase !== "show") return;
  const k = K[Z.i], L = Z.lokal, kam = kamFuer(Z.i, L);
  leisteFortschritt();
  // Übergang: neue Szene blendet über die alte
  if (Z.szene) Z.szene.style.opacity = k.art === "karte" ? 0 : ein(L, 0);
  if (Z.alt) { if (L > Z.altBis || k.art !== "karte" && ein(L, 0) >= 1) { Z.alt.remove(); Z.alt = null; } else if (k.art === "karte") Z.alt.style.opacity = 1 - ein(L, 0); }
  const seite = $("#rb-seite"), vorKarte = Z.i > 0 && K[Z.i - 1].art === "karte";
  seite.style.opacity = k.art === "karte" ? (vorKarte ? 1 : ein(L, 0)) : (Z.alt && vorKarte ? 1 - ein(L, 0) : 0);
  $("#rb-lhinweis").textContent = "";
  if (k.art === "karte") {
    const T = kapitelZeit(k, L);
    zeichneKarte(T, kam, { spuren: "alle", koepfe: true });
    seiteZeichnen(k, T);
    pulse(k, T);
    if (D.teams.some(t => t.luecken || t.ohneGps) && T > D.t0) $("#rb-lhinweis").textContent = "gestrichelt: ohne GPS-Signal";
    return;
  }
  $("#rb-pulse").innerHTML = "";
  const vorher = letzteKarteVor(Z.i), Tfest = vorher ? vorher.bis : D.t0;
  if (k.art === "titel") {
    zeichneKarte(D.t0, kam, { spuren: "keine", koepfe: false });
    const s = Z.szene; s.querySelector(".logo").style.opacity = ein(L, 100, 600);
    const nadel = s.querySelector(".nadel"); if (nadel) nadel.style.transform = `rotate(${ruhig ? 0 : (1 - glatt(L / 2200)) * 140 * Math.cos(L / 260)}deg)`;
    const h = s.querySelector("h1"), o = s.querySelector(".ort"), f = s.querySelector(".fakten");
    [[h, 500], [o, 900], [f, 1500]].forEach(([e, ab]) => { const v = ein(L, ab); e.style.opacity = v; e.style.transform = `translateY(${(1 - v) * 16}px)`; });
  }
  if (k.art === "fotos") { zeichneKarte(Tfest, kam, { spuren: "alle", koepfe: true }); fotosZeichnen(k, L); }
  if (k.art === "platz") platzZeichnen(k, L, kam);
  if (k.art === "alle") {
    zeichneKarte(D.tEnd, kam, { spuren: "alle", koepfe: false });
    Z.szene.querySelectorAll(".a-karte").forEach(c => { const v = ein(L, 300 + c.dataset.i * 110); c.style.opacity = v; c.style.transform = `translateY(${(1 - v) * 16}px)`; });
  }
  if (k.art === "abspann") {
    zeichneKarte(D.tEnd, kam, { spuren: "alle", koepfe: !k.roll });
    if (k.roll) {
      const r = Z.szene.querySelector(".rolle"), lauf = Math.min(L, k.roll.lauf);
      const weg = ruhig ? Math.floor(lauf / 5000) * 860 : k.roll.tempo * lauf;   // ruhig: alle 5 s eine Seite weiter
      r.style.transform = `translate3d(0,${(1080 - weg).toFixed(1)}px,0)`;
    }
    const c = Z.szene.querySelector(".ab-karte"), v = ein(L, 1600); c.style.opacity = v; c.style.transform = `translateY(${(1 - v) * 16}px)`;
  }
}
function pulse(k, T) {
  const g = $("#rb-pulse"), tempo = Math.max(1, (k.bis - k.von) / k.dur);
  let html = "";
  if (!ruhig) D.ereignisse.forEach(e => {
    if (e.art !== "ok" || e.t > T) return;
    const alter = (T - e.t) / tempo; if (alter > 1400) return;
    const s = D.stationen.find(x => x.position === e.pos), u = alter / 1400;
    if (!s || !s.xy) return;
    const kam = kamFuer(Z.i, Z.lokal), q = [(s.xy[0] - kam.cx) * kam.s + 960, (s.xy[1] - kam.cy) * kam.s + 540];
    html += `<circle class="puls" cx="${q[0].toFixed(1)}" cy="${q[1].toFixed(1)}" r="${(30 + u * 110).toFixed(1)}" stroke="${e.team.farbe}" opacity="${(1 - u).toFixed(2)}"/>`;
  });
  g.innerHTML = html;
}
function fotosZeichnen(k, L) {
  const s = Z.szene, n = k.fotos.length, GY = 196;
  // großes Foto: so hoch wie möglich, unter ihm bleibt Platz für die Unterschrift, alles über der Leiste
  const grossH = Math.min(720, 1080 - untenFrei() - 24 - GY - 100);
  let spot = null, spotH = grossH;
  const aktiv = k.fotos.some((f, i) => { const a = 900 + i * 1000; return L >= a && (ruhig ? L < a + 700 : (L - a - 600) / 420 < 1); });
  k.fotos.forEach((f, i) => {
    const kachel = s.querySelector(`.kachel[data-i="${i}"]`), u = s.querySelector(`.unterschrift[data-u="${i}"]`), slot = k.slots[i];
    const a = 900 + i * 1000;           // erscheint groß in der Mitte, dann an seinen Platz in der Wand
    const auf = ein(L, a, 320), weg = ruhig ? (L >= a + 700 ? 1 : 0) : glatt((L - a - 600) / 420);
    if (L < a) { kachel.style.opacity = 0; u.style.opacity = 0; return; }
    const gw = Math.min(1400, grossH * f.ratio), gh = gw / f.ratio, gx = 960 - gw / 2;
    const sGross = gw / kachelB(f), sKlein = slot.w / kachelB(f);
    const x = gx + (slot.x - gx) * weg, y = GY + (slot.y - GY) * weg, sc = sGross + (sKlein - sGross) * weg;
    kachel.style.opacity = auf; kachel.style.zIndex = weg < 1 ? 5 : 1;
    kachel.classList.toggle("gross", weg < 1);
    kachel.style.transform = `translate(${x.toFixed(1)}px,${(y + (1 - auf) * 14).toFixed(1)}px) scale(${sc.toFixed(4)})`;
    u.style.opacity = ein(L, a + 1000, 300) * (aktiv ? .25 : 1);
    if (weg < 1) { spot = f; spotH = gh; }
  });
  const sp = s.querySelector("#rb-spot"), txt = spot ? `<span class="emo">${spot.team.emoji}</span> ${esc(spot.team.name)}<span class="zt">${uhr(spot.takenAt)}</span>` : "";
  if (sp.dataset.t !== txt) { sp.innerHTML = txt; sp.dataset.t = txt; }
  sp.style.opacity = spot ? 1 : 0;
  sp.style.top = (GY + spotH + 20) + "px";
}
function platzZeichnen(k, L, kam) {
  const s = Z.szene, t = k.team, halt = k.halt, schloss = halt + 300;
  const enthuellt = schloss + 6 * 350 + 700;
  zeichneKarte(D.tEnd, kam, { spuren: t, koepfe: false, bis: D.t0 + (t.fertig - D.t0) * glatt((L - enthuellt) / 2600) });
  const sicht = (sel, v, dy = 16) => s.querySelectorAll(`[data-a="${sel}"]`).forEach(e => { e.style.opacity = v; e.style.transform = (e.dataset.a === "foto" ? "rotate(1.6deg) " : "") + `translateY(${(1 - v) * dy}px)`; });
  sicht("titel", ein(L, 0)); sicht("walzen", ein(L, 500)); sicht("team", ein(L, enthuellt)); sicht("foto", ein(L, enthuellt + 500));
  const spin = L + Z.extra;
  s.querySelectorAll(".band").forEach(b => {
    const j = +b.dataset.w, ziel = +k.ziffern[j], ab = schloss + j * 350;
    let pos;
    if (ruhig) pos = L >= ab ? ziel : 0;
    else {
      const p0 = (Math.min(spin, ab + Z.extra) * 0.014 + j * 3.3);
      if (L < ab) pos = spin * 0.014 + j * 3.3;
      else { const zielPos = Math.ceil((p0 - ziel) / 10) * 10 + ziel + 10, u = Math.min(1, (L - ab) / 650);
        pos = p0 + (zielPos - p0) * (1 - Math.pow(1 - u, 3)); }
    }
    const m = ((pos % 10) + 10) % 10;
    b.style.transform = `translateY(${(-m * 176).toFixed(1)}px)`;
  });
}

const HAKEN = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10" stroke-width="1.8"/><path d="m7.5 12.5 3 3 6-6.5"/></svg>';
const ACHTUNG = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3 2 20h20Z"/><path d="M12 10v4M12 17h.01"/></svg>';
function gesamt() { return K.reduce((n, k) => n + k.dur, 0); }
function mmss(t) { t = Math.round(t / 1000); return Math.floor(t / 60) + ":" + String(t % 60).padStart(2, "0"); }

/* ---------- Steuerleiste ---------- */
let leisteUhr = null;
function leisteZeigen() {
  $("#rb-leiste").classList.remove("weg"); root.classList.remove("still");
  clearTimeout(leisteUhr);
  leisteUhr = setTimeout(() => { if (Z.phase === "show") { $("#rb-leiste").classList.add("weg"); root.classList.add("still"); } }, 2500);
}
function leisteSpur() {
  $("#rb-lSpur").innerHTML = K.map((k, i) => `<span style="--d:${k.dur}" data-i="${i}" title="${esc(k.name)}"><i></i></span>`).join("");
  $("#rb-lSpur").querySelectorAll("span").forEach(s => s.onclick = () => { if (Z.phase !== "show") { $("#rb-ueber").innerHTML = ""; } geheZu(+s.dataset.i); });
  leisteFortschritt();
}
let fortStand = "";
function leisteFortschritt() {
  const vorbei = K.slice(0, Z.i).reduce((n, k) => n + k.dur, 0) + (Z.phase === "show" ? Math.min(Z.lokal, K[Z.i].dur) : 0);
  const txt = (Z.phase === "show" ? K[Z.i].name + (Z.haelt ? ", wartet auf Weiter" : "") : "Vorbereiten") + "|" + mmss(vorbei) + " / " + mmss(gesamt());
  $("#rb-lSpur").querySelectorAll("span").forEach((s, i) => s.style.setProperty("--p", (i < Z.i ? 100 : i > Z.i || Z.phase !== "show" ? 0 : Math.min(100, Z.lokal / K[i].dur * 100)) + "%"));
  if (txt !== fortStand) { const [a, b] = txt.split("|"); $("#rb-lKap").textContent = a; $("#rb-lZeit").textContent = b; fortStand = txt; }
}
function vollbild() {
  if (document.fullscreenElement) document.exitFullscreen().catch(() => {});
  else document.documentElement.requestFullscreen().catch(() => {});
}
function thema() {
  const jetzt = document.documentElement.dataset.theme || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
  const neu = jetzt === "dark" ? "light" : "dark"; document.documentElement.dataset.theme = neu;
  try { localStorage.setItem("sj.thema", neu); } catch (e) {}
  if (D) { grundkarte(); karteRastern(); }
}
function schwarz() { const s = $("#rb-schwarz"); s.classList.toggle("an"); if (s.classList.contains("an")) { Z.spielt = false; knopf(); } }

const startbar = () => !!D && (Z.phase === "vorbereiten" || Z.phase === "show");
const GERUEST = `
<div id="rb-buehne" aria-live="off">
  <div class="osm" id="rb-osm" hidden>© OpenStreetMap-Mitwirkende</div>
  <svg id="rb-welt" aria-hidden="true"><g id="rb-grund"></g><g id="rb-spuren"></g></svg>
  <svg id="rb-schirm" viewBox="0 0 1920 1080" aria-hidden="true"><g id="rb-namen"></g><g id="rb-stationen"></g><g id="rb-pulse"></g><g id="rb-koepfe"></g><text id="rb-lhinweis" class="lueckenhinweis" x="48" y="1040"></text></svg>
  <aside id="rb-seite">
    <div class="s-kopf"><span id="rb-sLogo"></span><span>Stadtjagd Prag</span></div>
    <div class="s-kapitel" id="rb-sKap"></div>
    <div class="s-name" id="rb-sName"></div>
    <div class="s-uhr" id="rb-sUhr">14:00</div>
    <div class="s-seit" id="rb-sSeit"></div>
    <div class="s-liste" id="rb-sListe"></div>
    <div class="s-route" id="rb-sRoute"></div>
  </aside>
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
  <button data-k="thema" title="Hell oder dunkel (T)">Hell/Dunkel</button>
  <button data-k="voll" title="Vollbild (F)">Vollbild</button>
  <button data-k="hilfe" title="Tasten (H)">Tasten</button>
</div>
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
async function bildAus(b64) {
  const bin = atob(String(b64).replace(/\s/g, "")), u8 = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) u8[i] = bin.charCodeAt(i);
  const url = URL.createObjectURL(new Blob([u8], { type: "image/jpeg" })), img = new Image();
  img.src = url;
  try { await img.decode(); } catch (e) { URL.revokeObjectURL(url); throw e; }   // vor dem Start decodieren, damit nichts ruckelt
  return { src: url, ratio: img.naturalWidth / Math.max(1, img.naturalHeight) };
}
// Zweimal in voller Größe, dann die Vorschau; fehlt auch sie, bleibt das Foto weg
async function einFoto(pin, f) {
  for (const voll of [true, true, false]) {
    try {
      const r = await host.rpc("admin_photo", { p_pin: pin, p_team: f.teamId, p_position: f.position, p_full: voll, p_route: "echt" });
      if (r && r.data) return await bildAus(r.data);
    } catch (e) { /* nächster Versuch */ }
  }
  return null;
}
async function fotosLaden(pin, liste, aktuell, fort) {
  const todo = liste.filter(f => !fotoCache.has(schluesselVon(f)));
  let fertig = liste.length - todo.length, fehl = 0;
  const arbeiter = async () => {
    while (todo.length && aktuell()) {
      const f = todo.shift(), r = await einFoto(pin, f);
      if (r) fotoCache.set(schluesselVon(f), r); else fehl++;
      fort(++fertig, liste.length);
    }
  };
  await Promise.all([arbeiter(), arbeiter(), arbeiter()]);
  return fehl;
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
  panel(`<div class="v-panel" role="dialog" aria-label="Rückblick">${kopfHTML("Rückblick")}<div class="rb-fehler" role="alert">${esc(e.message || "Die Daten kamen nicht an.")}</div>
    <div class="v-fuss"><button class="start" id="rb-nochmal">Erneut versuchen</button></div>
    <a class="v-zurueck" href="#/admin">Zur Spielleitung</a></div>`);
  $("#rb-nochmal").onclick = () => laden();
}
function ladePanel(zeile, n, von) {
  Z.phase = "laden";
  panel(`<div class="v-panel" role="dialog" aria-label="Rückblick wird vorbereitet">${kopfHTML("Rückblick")}
    <ul class="v-liste"><li class="ok"><span id="rb-ladezeile">${esc(zeile)}</span></li></ul>
    <div class="v-balken"><i id="rb-balken" style="width:${von ? Math.round(n / von * 100) : 0}%"></i></div></div>`);
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
    if (modus === "probe") roh = probeDaten();
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
      let fehl = 0;
      if (liste.length) { ladePanel("Fotos 0 von " + liste.length); fehl = await fotosLaden(pin, liste, aktuell, ladeFortschritt); }
      if (!aktuell()) return;
      roh = { state: st, tracks, photos: liste.filter(f => fotoCache.has(schluesselVon(f))).map(f => ({ ...f, ...fotoCache.get(schluesselVon(f)) })), fehlt: fehl };
    }
    D = aufbereiten(roh);
    D.fehlt = roh.fehlt || 0;
    if (modus === "probe") D.fotos.forEach((f, i) => { f.ratio = i % 3 === 1 ? 4 / 3 : 3 / 4; f.src = fotoBild(f.team, f.position, f.ratio > 1); });
    const loeschDatum = D.st.photosDeleteOn || null;
    D.geloescht = !D.fotos.length && !D.fehlt && !!loeschDatum && loeschDatum <= new Date().toISOString().slice(0, 10) ? loeschDatum : null;
    // ausgenommene Fotos überleben ein Neuladen, aber nur die, die es noch gibt
    const da = new Set(D.fotos.map(f => f.teamId + ":" + f.position));
    OPT.aus = new Set([...ausLesen()].filter(k => da.has(k)));
    ladePanel("Karte und Schriften werden geholt");
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
function probeDaten() { return beispielDaten(); }

/* =====================================================================
   Vorbereiten, Fotos durchsehen, Tastenhilfe
   ===================================================================== */
function vorbereitenHTML() {
  const d = D, ohne = d.teams.filter(t => t.ohneGps), idle = d.teams.filter(t => !t.sts.length);
  const nichtIm = d.teams.filter(t => !t.place), imZiel = d.teams.length - nichtIm.length;
  const datum = t => new Date(t + "T12:00").toLocaleDateString("de-DE");
  const keineStandorte = d.teams.length > 1 && ohne.length === d.teams.length;
  const nFotos = d.fotos.length;
  const fotoZeile = d.fehlt ? `<li class="warn">${ACHTUNG}<span>${d.fehlt} ${d.fehlt === 1 ? "Foto" : "Fotos"} nicht geladen<button class="nochmal" id="rb-nochmal">Erneut versuchen</button></span>
        ${nFotos ? `<small>${nFotos} ${nFotos === 1 ? "Gruppenfoto" : "Gruppenfotos"} geladen</small>` : ""}</li>`
    : d.geloescht ? `<li class="warn">${ACHTUNG}<span>Fotos am ${datum(d.geloescht)} gelöscht (Löschdatum)</span></li>`
    : nFotos ? `<li class="ok">${HAKEN}<span>${nFotos} ${nFotos === 1 ? "Gruppenfoto" : "Gruppenfotos"} geladen</span>${d.st.photosDeleteOn ? `<small>Gelöscht am ${datum(d.st.photosDeleteOn)}</small>` : ""}</li>` : "";
  const gpsKlein = keineStandorte ? "Standortdaten gelöscht: Wege aus den Check-ins"
    : [ohne.length ? `${ohne.map(t => esc(t.name)).join(", ")} ohne GPS: Weg aus den Check-ins, gestrichelt` : "",
       idle.length ? `${idle.map(t => esc(t.name)).join(", ")} ohne Check-in: bleibt am Start` : ""].filter(Boolean).join(". ");
  return `<div class="szene" style="opacity:1"><div class="schleier dicht"></div><div class="v-panel" role="dialog" aria-label="Rückblick vorbereiten">
    ${kopfHTML(modus === "probe" ? "Rückblick, Probe" : "Rückblick")}
    <ul class="v-liste">
      ${modus === "probe" ? `<li class="warn">${ACHTUNG}<span>Beispieldaten, nichts davon aus einem echten Spiel</span></li>` : ""}
      <li class="ok">${HAKEN}<span>Spiel beendet um <span class="nw">${uhr(d.tEnd)} Uhr</span>, ${imZiel} von ${d.teams.length} Teams im Ziel</span>
        ${nichtIm.length ? `<small>Beim Spielende unterwegs: ${nichtIm.map(t => esc(t.name)).join(", ")}</small>` : ""}</li>
      <li class="${ohne.length ? "warn" : "ok"}">${ohne.length ? ACHTUNG : HAKEN}<span>${d.teams.length - ohne.length} von ${d.teams.length} Teams mit GPS-Route</span>
        ${gpsKlein ? `<small>${gpsKlein}</small>` : ""}</li>
      ${fotoZeile}
      ${d.hatKarte ? "" : `<li class="warn">${ACHTUNG}<span>Grundkarte nicht geladen, die Bühne zeigt Papier mit Höhenlinien</span></li>`}
      ${d.schriftOk ? `<li class="ok">${HAKEN}<span>Alles geladen, die Show läuft jetzt auch ohne Netz</span></li>`
        : `<li class="warn">${ACHTUNG}<span>Schrift nicht geladen, die Bühne zeigt eine Ersatzschrift<button class="nochmal" id="rb-nochmal">Erneut versuchen</button></span></li>`}
      <li class="warn" id="rb-wach" hidden>${ACHTUNG}<span>Bildschirmschoner am Laptop ausschalten.</span></li>
    </ul>
    <div class="v-opt">
      ${nFotos ? `<label><input type="checkbox" id="rb-oFotos" ${OPT.fotos ? "checked" : ""}> Gruppenfotos zeigen</label>
      <button class="rb-link" id="rb-oDurch">Fotos durchsehen${OPT.aus.size ? ` (${OPT.aus.size} aus)` : ""}</button>` : ""}
      <label><input type="checkbox" id="rb-oHalt" ${OPT.anhalten ? "checked" : ""}> Vor jedem Koffer-Platz anhalten, Weiter deckt auf</label>
    </div>
    <div class="v-fuss"><button class="start" id="rb-oStart">Rückblick starten</button><span class="dauer">Dauer etwa <b class="tab">${mmss(gesamt())} min</b></span></div>
    <div class="v-tasten"><span><kbd>Leertaste</kbd> Start und Pause</span><span><kbd>→</kbd> <kbd>←</kbd> Kapitel</span><span><kbd>F</kbd> Vollbild</span><span><kbd>H</kbd> alle Tasten</span></div>
    ${modus === "probe" ? "" : `<a class="v-zurueck" href="#/admin">Zur Spielleitung</a>`}
  </div></div>`;
}
function vorbereiten() {
  Z.phase = "vorbereiten"; Z.spielt = false; knopf(); $("#rb-buehne").dataset.art = "vorbereiten";
  if (Z.szene) { Z.szene.remove(); Z.szene = null; } if (Z.alt) { Z.alt.remove(); Z.alt = null; }
  $("#rb-seite").style.opacity = 0; $("#rb-pulse").innerHTML = ""; $("#rb-lhinweis").textContent = "";
  zeichneKarte(D.t0, einpassen(D.uebersicht, VOLL_B), { spuren: "keine", koepfe: false });
  $("#rb-ueber").innerHTML = vorbereitenHTML();
  skalieren();   // das Panel ist erst jetzt da: Größe über der Leiste neu berechnen
  const f = $("#rb-oFotos"), dd = $("#rb-oDurch");
  if (f) f.onchange = e => { OPT.fotos = e.target.checked; kapitelBauen(); vorbereiten(); };
  if (dd) dd.onclick = durchsehen;
  $("#rb-oHalt").onchange = e => { OPT.anhalten = e.target.checked; };
  $("#rb-oStart").onclick = starten;
  const nochmal = $("#rb-nochmal"); if (nochmal) nochmal.onclick = () => laden();
  const li = $("#rb-wach"); if (li) li.hidden = wachOk !== false;
  leisteSpur();
}
function durchsehen() {
  const reihen = D.stationen.map(s => { const f = D.fotos.filter(x => x.position === s.position);
    return `<div class="d-reihe"><span class="nr">${s.position}</span>${f.map(x => `<button class="d-bild ${OPT.aus.has(x.teamId + ":" + x.position) ? "aus" : ""}" data-id="${x.teamId}:${x.position}" title="${esc(x.team.name)}"><img src="${x.src}" alt=""><span>${x.team.emoji}</span></button>`).join("")}</div>`; }).join("");
  $("#rb-ueber").innerHTML = `<div class="szene" style="opacity:1"><div class="schleier dicht"></div><div class="d-panel" role="dialog" aria-label="Fotos durchsehen">
    <h2>Fotos durchsehen</h2><p>Antippen nimmt ein Foto aus dem Rückblick. Gelöscht wird nichts.</p>
    <div class="d-reihen">${reihen}</div><button class="fertig" id="rb-dFertig">Fertig</button></div></div>`;
  $("#rb-ueber").querySelectorAll(".d-bild").forEach(b => b.onclick = () => { const id = b.dataset.id; OPT.aus.has(id) ? OPT.aus.delete(id) : OPT.aus.add(id); b.classList.toggle("aus"); ausSchreiben(); });
  $("#rb-dFertig").onclick = () => { kapitelBauen(); vorbereiten(); };
}
function hilfe() {
  const h = $("#rb-hilfeBox");
  if (h) { h.remove(); return; }
  const d = document.createElement("div"); d.id = "rb-hilfeBox"; d.className = "szene"; d.style.cssText = "opacity:1;z-index:20";
  d.innerHTML = `<div class="rb-hilfe" role="dialog" aria-label="Tasten"><h2>Tasten</h2><table>
    <tr><td><kbd>Leertaste</kbd> <kbd>K</kbd> <kbd>F5</kbd></td><td>Start, Pause, am Finale aufdecken</td></tr>
    <tr><td><kbd>→</kbd> <kbd>Bild ↓</kbd> <kbd>Enter</kbd></td><td>Weiter: nächstes Kapitel oder aufdecken</td></tr>
    <tr><td><kbd>←</kbd> <kbd>Bild ↑</kbd></td><td>Zurück: Kapitel von vorn, zweimal: Kapitel davor</td></tr>
    <tr><td><kbd>Pos1</kbd> <kbd>Ende</kbd></td><td>Zum Anfang, zum Finale</td></tr>
    <tr><td><kbd>F</kbd></td><td>Vollbild an und aus</td></tr>
    <tr><td><kbd>B</kbd> <kbd>.</kbd></td><td>Bild schwarz, Show hält an</td></tr>
    <tr><td><kbd>T</kbd></td><td>Hell oder dunkel</td></tr>
    <tr><td><kbd>H</kbd> <kbd>Esc</kbd></td><td>Diese Hilfe zu</td></tr></table></div>`;
  $("#rb-buehne").appendChild(d);
}

/* ---------- Bühne skalieren ---------- */
function skalieren() {
  if (!root) return;
  const s = Math.min(innerWidth / 1920, innerHeight / 1080), b = $("#rb-buehne");
  b.style.transform = `scale(${s}) translate(-50%,-50%)`;
  // Die Leiste liegt fest am Fensterrand, nicht auf der Bühne: ihre Höhe in Bühnen-Pixel, damit Panels darüber bleiben
  const l = $("#rb-leiste"), unten = l ? l.offsetHeight / s - Math.max(0, (innerHeight - 1080 * s) / 2) / s : 0;
  b.style.setProperty("--unten", Math.max(0, unten) + "px");
  // Passt das Vorbereiten-Panel nicht über die Leiste, wird es kleiner statt abgeschnitten (kein Scrollen auf dem Beamer)
  const v = root.querySelector(".v-panel");
  if (v) v.style.setProperty("--vs", Math.min(1, (1080 - Math.max(0, unten) - 48) / v.offsetHeight));
}

/* =====================================================================
   Öffnen und Schließen. Alles, was die Show an document hängt, kommt hier hinein und beim Schließen wieder heraus.
   ===================================================================== */
let abhoerer = [], mqDunkel = null, mqFn = null;
function hoere(ziel, typ, fn) { ziel.addEventListener(typ, fn); abhoerer.push([ziel, typ, fn]); }
function taste(e) {
  if (!root) return;
  const k = e.key;
  // F5 lädt sonst die Seite neu, und die geladenen Fotos sind weg (Präsentations-Klicker senden F5 für "Präsentation starten")
  if (k === "F5" && !e.altKey && !e.ctrlKey && !e.metaKey) { e.preventDefault(); spielPause(); return; }
  if (e.altKey || e.ctrlKey || e.metaKey) return;
  if (e.target && e.target.matches && e.target.matches("input[type=password],input[type=text],textarea")) return;   // PIN tippen
  const schwarzAn = $("#rb-schwarz").classList.contains("an");
  if (schwarzAn && !["b", "B", "."].includes(k)) { schwarz(); e.preventDefault(); return; }
  if ((k === " " || k === "Enter") && document.activeElement && document.activeElement.matches("input,button,a") && Z.phase !== "show") return;
  const nur = fn => () => { if (startbar()) fn(); };
  const tat = {
    " ": spielPause, k: spielPause, K: spielPause,
    ArrowRight: weiter, PageDown: weiter, Enter: weiter, n: weiter,
    ArrowLeft: zurueck, PageUp: zurueck, Backspace: zurueck, p: zurueck,
    Home: nur(() => { $("#rb-ueber").innerHTML = ""; geheZu(0); }),
    End: nur(() => { $("#rb-ueber").innerHTML = ""; const i = K.findIndex(x => x.art === "platz"); geheZu(i >= 0 ? i : K.length - 2); }),
    f: vollbild, F: vollbild, t: thema, T: thema, b: schwarz, B: schwarz, ".": schwarz,
    h: hilfe, H: hilfe, "?": hilfe, Escape: () => { const h = $("#rb-hilfeBox"); if (h) h.remove(); }
  }[k];
  if (!tat) return;
  e.preventDefault(); tat();
}
function oeffnen(h, art) {
  if (root) beenden();
  host = h; modus = art === "probe" ? "probe" : "echt";
  Object.assign(Z, { phase: "laden", i: 0, lokal: 0, spielt: false, haelt: false, frei: false, extra: 0, letzt: 0, szene: null, alt: null });
  D = null; K = []; OPT.aus = new Set();
  root = document.createElement("div");
  root.id = "rueckblick"; root.className = "still"; root.setAttribute("role", "region"); root.setAttribute("aria-label", "Rückblick");
  root.innerHTML = GERUEST;
  document.body.appendChild(root);
  const app = document.getElementById("app"); if (app) app.inert = true;
  document.body.classList.add("fest");
  $("#rb-sLogo").innerHTML = LOGO;
  $("#rb-leiste").addEventListener("click", e => { const b = e.target.closest("button"); if (!b) return;
    ({ zurueck, weiter, spiel: spielPause, thema, voll: vollbild, hilfe })[b.dataset.k](); b.blur(); });
  hoere(document, "mousemove", leisteZeigen);
  hoere(document, "keydown", taste);
  hoere(window, "resize", skalieren);
  hoere(document, "visibilitychange", wach);
  mqDunkel = matchMedia("(prefers-color-scheme: dark)");
  mqFn = () => { if (D && !document.documentElement.dataset.theme) { grundkarte(); karteRastern(); } };
  mqDunkel.addEventListener("change", mqFn);
  skalieren();
  wach();
  rafId = requestAnimationFrame(takt);
  if (h.api !== API) { Z.phase = "sperre"; panel(`<div class="v-panel" role="dialog" aria-label="Rückblick">${kopfHTML("Rückblick")}<div class="rb-fehler" role="alert">Seite und Rückblick sind aus verschiedenen Fassungen: die Seite neu laden.</div></div>`); return; }
  laden();
}
function beenden() {
  if (!root) return;
  ladeNr++;   // laufende Ladevorgänge verlaufen im Sand
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
// Für Prüfungen und Bildschirmfotos (tools/pruefstand/rueckblick.py): RB.zeige("platz1", 9000)
window.RB = {
  zeige: (id, lokal = 0) => { $("#rb-ueber").innerHTML = ""; const i = K.findIndex(x => x.id === id); geheZu(i < 0 ? 0 : i, lokal); Z.spielt = false; knopf(); zeichnen(); },
  kapitel: () => K.map(k => ({ id: k.id, dur: k.dur, art: k.art, fotos: k.fotos ? k.fotos.length : 0 })),
  zustand: () => ({ phase: Z.phase, i: Z.i, id: K[Z.i] && K[Z.i].id, lokal: Z.lokal, spielt: Z.spielt, haelt: Z.haelt }),
  gesamt, D: () => D, vorbereiten,
  test: { aufbereiten, kapitel: kapitelFuer, ohneAusreisser }
};
})();
