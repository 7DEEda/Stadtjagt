/* Prüfstand für die Stadtjagd: ersetzt Supabase durch Beispieldaten.
   Aufruf: app.html?szenario=<name>  (Liste: app.html?szenario=liste oder window.__SZENARIEN)
   Läuft vor config.js und dem App-Skript. Nichts hiervon geht an eine echte Datenbank. */
(function () {
  "use strict";
  const P = new URLSearchParams(location.search);
  const SZ_NAME = P.get("szenario") || "anmeldung-leer";
  const NOW = Date.now();
  const MIN = 60000;
  const iso = ms => ms == null ? null : new Date(ms).toISOString();

  /* ---------- Konfiguration festnageln (config.js darf sie nicht überschreiben) ---------- */
  const MOCK_CFG = { url: "https://mock.invalid", key: "mock",
    support: { name: "der Spielleitung", phone: "491720000000" } };
  Object.defineProperty(window, "SJ_CONFIG", { configurable: false, get: () => MOCK_CFG, set: () => { } });

  /* ---------- Zufall mit festem Startwert, damit jedes Foto gleich aussieht ---------- */
  let seed = 20260919;
  const rnd = () => { seed |= 0; seed = seed + 0x6D2B79F5 | 0; let t = Math.imul(seed ^ seed >>> 15, 1 | seed);
    t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; };
  const hex = n => Array.from({ length: n }, () => "0123456789abcdef"[Math.floor(rnd() * 16)]).join("");

  const R_E = 6371000, rad = x => x * Math.PI / 180;
  const dist = (a, b) => { const dLat = rad(b.lat - a.lat), dLng = rad(b.lng - a.lng);
    const h = Math.sin(dLat / 2) ** 2 + Math.cos(rad(a.lat)) * Math.cos(rad(b.lat)) * Math.sin(dLng / 2) ** 2;
    return 2 * R_E * Math.asin(Math.min(1, Math.sqrt(h))); };

  /* ---------- Stationen (Orte und Ziffern aus seed-stationen-prag.sql, Texte ausgedacht) ---------- */
  const START = { lat: 50.102458, lng: 14.431681 };
  const STATIONEN = [
    { id: "s1", position: 1, name: "Planetarium Prag", lat: 50.105286, lng: 14.427406, radiusM: 50, digit: 3,
      locationHint: "Am Rand der Stromovka steht ein runder Bau mit weißer Kuppel. Geht zum Haupteingang.",
      riddle: "Über dem Eingang steht in Metallziffern das Jahr der Eröffnung. Welches Jahr ist es?",
      answer: "1960", tip: "Tretet ein paar Schritte zurück, die Ziffern hängen über der Glastür." },
    { id: "s2", position: 2, name: "Rudolfstollen", lat: 50.104441, lng: 14.419553, radiusM: 60, digit: 7,
      locationHint: "Geht in den Park hinein Richtung Westen. Der Eingang zum alten Wasserstollen liegt unter Bäumen am Hang.",
      riddle: "Kaiser Rudolf II. ließ diesen Stollen graben, um Wasser in seinen Park zu leiten. Wie viele Meter ist er lang? Die Zahl steht auf der Tafel neben dem Tor.",
      answer: "1098", tip: "Die Tafel hängt links vom Gittertor, die Länge steht in der zweiten Zeile." },
    { id: "s3", position: 3, name: "Wasserturm Letná", lat: 50.100195, lng: 14.420089, radiusM: 50, digit: 1,
      locationHint: "Oben auf der Letná, ein schlanker Turm aus Backstein mit grünem Dach.",
      riddle: "Zählt die Fenster auf der Seite mit dem Tor, vom Boden bis unters Dach. Wie viele sind es?",
      answer: "7|sieben", tip: "Das runde Fenster ganz oben zählt mit." },
    { id: "s4", position: 4, name: "Aussicht Letná, ehemalige Bergstation", lat: 50.095789, lng: 14.425346, radiusM: 50, digit: 9,
      locationHint: "Oben an der großen Treppe, die vom Park zur Čech-Brücke hinunterführt. Hier begann 1891 eine Standseilbahn, heute ist es ein Aussichtspunkt.",
      riddle: "Von der Brüstung aus seht ihr über die Moldau. Wie viele Brücken könnt ihr zählen?",
      answer: "5|fünf", tip: "Zählt von links nach rechts, auch die Eisenbahnbrücke ganz hinten." },
    { id: "s5", position: 5, name: "Metronom", lat: 50.094775, lng: 14.415938, radiusM: 50, digit: 5,
      locationHint: "Das große Pendel über der Stadt. Früher stand hier das größte Stalin-Denkmal Europas.",
      riddle: "In welchem Jahr wurde das Metronom aufgestellt? Die Jahreszahl steht auf der Infotafel am Sockel.",
      answer: "1991", tip: "Die Tafel steht an der Treppe auf der Seite zur Stadt." }
  ];
  const CASE_HINT = "Die Koffer stehen im Hotel Mama Shelter, im Innenhof hinter der Bar. Dort wartet die Spielleitung.";
  const CASE_CODE = "371955";

  /* ---------- Teams und Personen ---------- */
  const TEAMNAMEN = ["Adler", "Delfin", "Einhorn", "Eule", "Flamingo", "Fuchs", "Igel", "Otter", "Panda", "Pinguin", "Tiger", "Wolf"];
  const FUCHS_MITGLIEDER = ["Anna Berger", "Emre Demir", "Jonas Keller", "Julia Krüger", "Lea Hoffmann", "Maximilian Schröder", "Sophie Wagner", "Tobias Neumann"];
  const VOR = ["Ben", "Clara", "David", "Elif", "Felix", "Greta", "Hannes", "Ida", "Jan", "Katrin", "Lukas", "Mia", "Nils", "Olga",
    "Paul", "Rosa", "Sami", "Tilda", "Uwe", "Vera", "Wiebke", "Yusuf", "Zoe", "Moritz", "Laura", "Tim", "Nina", "Finn", "Lena",
    "Jakob", "Marie", "Leon", "Sarah", "Noah", "Emily", "Elias", "Amelie", "Philipp", "Charlotte", "Niklas", "Frieda", "Oskar",
    "Mila", "Henrik", "Carla", "Theo", "Pia", "Matteo", "Lotta", "Jonathan", "Ronja", "Samuel", "Helena", "Kai", "Merle", "Lars",
    "Svenja", "Till", "Frederike", "Konstantin", "Ella", "Aylin", "Dennis", "Nora", "Robert", "Isabel", "Marco", "Leonie",
    "Stefan", "Birgit", "Jens", "Heike", "Sven", "Petra", "Dirk", "Anke", "Ralf", "Ute", "Holger", "Silke", "Bernd", "Kerstin",
    "Markus", "Tanja"];
  const NACH = ["Müller", "Schmidt", "Schneider", "Fischer", "Weber", "Meyer", "Becker", "Schulz", "Koch", "Richter", "Klein",
    "Schwarz", "Zimmermann", "Braun", "Hofmann", "Hartmann", "Lange", "Schmitt", "Werner", "Krause", "Meier", "Lehmann", "Köhler",
    "Herrmann", "König", "Walter", "Huber", "Kaiser", "Peters", "Vogel", "Frank", "Roth", "Beck", "Lorenz", "Baumann", "Franke",
    "Albrecht", "Simon", "Ludwig", "Böhm", "Winter", "Kraus", "Martin", "Schumacher", "Vogt", "Stein", "Jäger", "Otto", "Sommer"];
  // Für die Teamsuche nach "Anna": mehrere passende Namen in verschiedenen Teams
  const ANNA_NAMEN = ["Anna Lehmann", "Hanna Schulz", "Johanna Richter", "Susanna Frank"];
  const andere = [];
  for (let i = 0; i < 84; i++) andere.push(VOR[i] + " " + NACH[(i * 7) % NACH.length]);
  andere.splice(5, 0, ANNA_NAMEN[0]); andere.splice(23, 0, ANNA_NAMEN[1]); andere.splice(47, 0, ANNA_NAMEN[2]); andere.splice(70, 0, ANNA_NAMEN[3]);

  const TEAMS = [];
  let k = 0, pid = 1;
  const PERSONEN = [];
  TEAMNAMEN.forEach(name => {
    const mitglieder = name === "Fuchs" ? FUCHS_MITGLIEDER.slice() : andere.slice(k, k += 8);
    const leader = mitglieder[name === "Fuchs" ? 0 : 1];
    const t = { id: "t-" + name.toLowerCase(), name,
      code: name === "Fuchs" ? "FUCHS-4821" : name.toUpperCase() + "-" + (1000 + Math.floor(rnd() * 9000)),
      readToken: hex(32) };
    t.members = mitglieder.slice().sort((a, b) => a.localeCompare(b, "de"));
    mitglieder.forEach(n => PERSONEN.push({ id: "p-" + (pid++), name: n, teamId: t.id, token: "tok-" + hex(24) }));
    t.leaderName = leader;
    t.leaderId = PERSONEN.find(p => p.name === leader).id;
    TEAMS.push(t);
  });
  PERSONEN.sort((a, b) => a.name.localeCompare(b.name, "de"));
  const person = name => PERSONEN.find(p => p.name === name);
  const FUCHS = TEAMS.find(t => t.name === "Fuchs");

  /* ---------- Szenarien ---------- */
  // welt: registration | drawn | running | finished
  // fuchs: Fortschritt von Team Fuchs; fertig: Reihenfolge der Teams im Ziel (Platz 1, 2, ...)
  // gps: Standort, den der Stub liefert; kompass: gut | ungenau | einmessen
  const TOK = n => person(n).token;
  const IM_TEAM = { "sj.code": "FUCHS-4821" };
  const GPS_UNTERWEGS = { lat: 50.10495, lng: 14.42290, acc: 8 };
  const GPS_ZU_WEIT = { lat: 50.10478, lng: 14.42185, acc: 46 };
  const GPS_VOR_START = { lat: 50.10231, lng: 14.43102, acc: 11 };   // vor dem Hotel, Übungsziel ist Berlin
  const kompassAn = [{ click: "[data-act=t-gps]" }, { wait: 400 }, { orient: "gut" }, { wait: 900 }];
  const SZ = {
    "anmeldung-leer": { welt: "registration", view: "public" },
    "anmeldung-angemeldet": { welt: "registration", view: "public", ls: { "sj.name": "Jonas Keller", "sj.token": TOK("Jonas Keller") } },
    "teamkarte-mitglied": { welt: "drawn", view: "public", ls: { "sj.name": "Jonas Keller", "sj.token": TOK("Jonas Keller") } },
    "teamkarte-leitung": { welt: "drawn", view: "public", ls: { "sj.name": "Anna Berger", "sj.token": TOK("Anna Berger") } },
    "hochhalten": { welt: "drawn", view: "public", ls: { "sj.name": "Jonas Keller", "sj.token": TOK("Jonas Keller") },
      steps: [{ until: ".teamkarte" }, { click: ".teamkarte .btn[data-act=pub-hoch]" }, { wait: 400 }] },
    "teamsuche": { welt: "drawn", view: "public",
      steps: [{ until: "#plook" }, { fill: ["#plook", "Anna"] }, { click: ".btn[data-act=pub-look]" }, { wait: 400 }] },
    "leitung-login": { welt: "drawn", view: "team" },
    "leitung-ohne-code": { welt: "running", view: "team", fuchs: { solved: 1 }, ls: { "sj.name": "Anna Berger", "sj.token": TOK("Anna Berger") } },
    "mitglied-auf-teamleitung": { welt: "running", view: "team", fuchs: { solved: 1 }, ls: { "sj.name": "Jonas Keller", "sj.token": TOK("Jonas Keller") } },
    "leitung-startklar": { welt: "drawn", view: "team", ls: IM_TEAM },
    "leitung-startklar-kompass": { welt: "drawn", view: "team", ls: IM_TEAM, gps: GPS_VOR_START, steps: kompassAn },
    "leitung-unterwegs": { welt: "running", view: "team", ls: IM_TEAM, fuchs: { solved: 1 } },
    "leitung-unterwegs-standort": { welt: "running", view: "team", ls: IM_TEAM, fuchs: { solved: 1 }, gps: GPS_UNTERWEGS, steps: kompassAn },
    "leitung-kompass-ungenau": { welt: "running", view: "team", ls: IM_TEAM, fuchs: { solved: 1 }, gps: GPS_UNTERWEGS,
      steps: [{ click: "[data-act=t-gps]" }, { wait: 400 }, { orient: "ungenau" }, { wait: 900 }] },
    "leitung-kompass-einmessen": { welt: "running", view: "team", ls: IM_TEAM, kalHeute: false, fuchs: { solved: 1 }, gps: GPS_UNTERWEGS,
      steps: [{ click: "[data-act=t-gps]" }, { wait: 400 }, { orient: "gut" }, { wait: 300 }, { schwenken: 2100 }, { wait: 300 }] },
    "leitung-checkin-abgelehnt": { welt: "running", view: "team", ls: IM_TEAM, fuchs: { solved: 1 }, gps: GPS_ZU_WEIT,
      steps: [...kompassAn, { until: "[data-act=t-check]:not([disabled])" }, { click: "[data-act=t-check]" }, { wait: 900 }] },
    "leitung-raetsel": { welt: "running", view: "team", ls: IM_TEAM, fuchs: { solved: 1, checkedIn: true } },
    "leitung-raetsel-fehlversuch": { welt: "running", view: "team", ls: IM_TEAM, fuchs: { solved: 1, checkedIn: true },
      steps: [{ until: "#tans" }, { fill: ["#tans", "1089"] }, { click: "[data-act=t-answer]" }, { wait: 700 }] },
    "leitung-denkpause": { welt: "running", view: "team", ls: IM_TEAM,
      fuchs: { solved: 1, checkedIn: true, pauses: 1, lockedUntil: NOW + 97000 } },
    "leitung-tipp": { welt: "running", view: "team", ls: IM_TEAM, fuchs: { solved: 1, checkedIn: true, pauses: 1, failedAttempts: 1, tipShown: true } },
    "leitung-koffer": { welt: "running", view: "team", ls: IM_TEAM, fuchs: { solved: 5 } },
    "leitung-platz2": { welt: "running", view: "team", ls: IM_TEAM, fuchs: { solved: 5 }, fertig: ["Adler", "Fuchs"] },
    "leitung-platz5": { welt: "running", view: "team", ls: IM_TEAM, fuchs: { solved: 5 }, fertig: ["Adler", "Eule", "Tiger", "Panda", "Fuchs"] },
    "leitung-beendet": { welt: "finished", view: "team", ls: IM_TEAM, fuchs: { solved: 4 } },
    "leitung-testmodus": { welt: "running", view: "team", ls: IM_TEAM, testMode: true, fuchs: { solved: 2 } },
    "mitglied-unterwegs": { welt: "running", view: "public", ls: { "sj.name": "Jonas Keller", "sj.token": TOK("Jonas Keller") }, fuchs: { solved: 1 } },
    "mitglied-raetsel": { welt: "running", view: "public", ls: { "sj.name": "Jonas Keller", "sj.token": TOK("Jonas Keller") }, fuchs: { solved: 1, checkedIn: true, failedAttempts: 1 } },
    "mitglied-beendet": { welt: "finished", view: "public", ls: { "sj.name": "Jonas Keller", "sj.token": TOK("Jonas Keller") }, fuchs: { solved: 4 } },
    "admin-login": { welt: "running", view: "admin" },
    "admin-karte": { welt: "running", view: "admin", ss: { "sj.pin": "4711" }, fuchs: { solved: 1 }, fertig: ["Adler"], settle: 3500 },
    "admin-teams": { welt: "running", view: "admin", ss: { "sj.pin": "4711" }, fuchs: { solved: 1 },
      steps: [{ until: ".tabs" }, { click: "[data-act=a-tab][data-tab=teams]" }, { wait: 300 }] },
    "admin-stationen": { welt: "running", view: "admin", ss: { "sj.pin": "4711" }, fuchs: { solved: 1 },
      steps: [{ until: ".tabs" }, { click: "[data-act=a-tab][data-tab=stations]" }, { wait: 300 }] },
    "admin-teilnehmende": { welt: "running", view: "admin", ss: { "sj.pin": "4711" }, fuchs: { solved: 1 },
      steps: [{ until: ".tabs" }, { click: "[data-act=a-tab][data-tab=people]" }, { wait: 300 }] },
    "admin-loeschen": { welt: "running", view: "admin", ss: { "sj.pin": "4711" }, fuchs: { solved: 1 },
      steps: [{ until: ".tabs" }, { click: "[data-act=a-tab][data-tab=danger]" }, { wait: 300 },
        { click: ".btn[data-act=a-danger][data-key=people]" }, { wait: 400 }] },
    "admin-bereit": { welt: "drawn", view: "admin", ss: { "sj.pin": "4711" },
      steps: [{ until: ".tabs" }, { click: "[data-act=a-tab][data-tab=teams]" }, { wait: 300 }] },
    "admin-start-dialog": { welt: "drawn", view: "admin", ss: { "sj.pin": "4711" },
      steps: [{ until: ".tabs" }, { click: "[data-act=a-tab][data-tab=teams]" }, { wait: 300 }, { click: ".panel .btn[data-act=a-start]" }, { wait: 400 }] },
    "admin-vollbild": { welt: "running", view: "admin", ss: { "sj.pin": "4711" }, fuchs: { solved: 1 }, settle: 3500,
      steps: [{ until: ".tabs" }, { wait: 2500 }, { click: "[data-act=a-full]" }, { wait: 800 }] },
    "admin-auslosen": { welt: "registration", view: "admin", ss: { "sj.pin": "4711" },
      steps: [{ until: ".tabs" }, { click: "[data-act=a-tab][data-tab=teams]" }, { wait: 300 }] }
  };
  window.__SZENARIEN = Object.keys(SZ);
  const C = SZ[SZ_NAME] || SZ["anmeldung-leer"];
  window.__SZENARIO = SZ[SZ_NAME] ? SZ_NAME : "anmeldung-leer (unbekannt: " + SZ_NAME + ")";

  /* ---------- Welt aufbauen ---------- */
  const WELT = { status: C.welt, background: "klassisch", testMode: !!C.testMode, prizeCount: 3, durationMin: 180 };
  const elapsed = C.welt === "finished" ? 185 : 72;   // Minuten seit dem Start
  WELT.startedAt = (C.welt === "running" || C.welt === "finished") ? NOW - elapsed * MIN : null;
  WELT.finishedAt = C.welt === "finished" ? WELT.startedAt + 182 * MIN : null;
  // Fortschritt der anderen Teams: [gelöst, gerade an der Station eingecheckt, Minuten ohne Meldung]
  const STAND_LAUF = { Adler: [5, false, 0], Eule: [4, false, 1], Tiger: [3, true, 0], Panda: [3, false, 1], Otter: [2, true, 0],
    Wolf: [2, false, 1], Pinguin: [2, false, 0], Einhorn: [2, false, 2], Flamingo: [1, true, 0], Igel: [1, false, 7], Delfin: [0, false, null], Fuchs: [1, false, 0] };
  const STAND_ENDE = { Adler: [5], Eule: [5], Tiger: [5], Otter: [5], Panda: [5], Wolf: [5], Pinguin: [5], Einhorn: [4, false, 3],
    Fuchs: [4, false, 2], Flamingo: [3, false, 5], Igel: [3, true, 4], Delfin: [2, false, null] };
  const fertig = C.fertig || (C.welt === "finished" ? ["Adler", "Eule", "Tiger", "Otter", "Panda", "Wolf", "Pinguin"] : ["Adler"]);
  const FU = Object.assign({ solved: 0, checkedIn: false, failedAttempts: 0, lockedUntil: null, pauses: 0, tipShown: false }, C.fuchs || {});
  const tEnde = WELT.finishedAt || NOW;
  const PKT = [START].concat(STATIONEN);

  TEAMS.forEach(t => {
    t.solved = 0; t.checkedIn = false; t.place = null; t.finishedAt = null; t.events = []; t.points = []; t.position = null; t.lastActivity = null;
    if (!WELT.startedAt) return;
    const tab = C.welt === "finished" ? STAND_ENDE : STAND_LAUF;
    let [solved, anStation, lag] = tab[t.name] || [0, false, 0];
    if (t.name === "Fuchs") { solved = FU.solved; anStation = FU.checkedIn; }
    const platz = fertig.indexOf(t.name) + 1;
    if (platz) { solved = 5; t.place = platz; t.finishedAt = WELT.startedAt + (C.welt === "finished" ? 95 + platz * 11 : 50 + platz * 3) * MIN;
      if (t.finishedAt > tEnde - 2 * MIN) t.finishedAt = tEnde - 2 * MIN; }
    t.solved = solved; t.checkedIn = anStation && solved < 5;
    // Abschnitte: gehen (Gewicht = Weg) und rätseln (feste Zeit), auf die verfügbare Zeit gestreckt
    const abschnitte = [];
    for (let i = 1; i <= solved; i++) { abschnitte.push({ typ: "gehen", von: PKT[i - 1], nach: PKT[i], w: dist(PKT[i - 1], PKT[i]) / 55 });
      abschnitte.push({ typ: "raten", bei: i, w: 5 + rnd() * 5 }); }
    if (platz) abschnitte.push({ typ: "gehen", von: PKT[5], nach: START, w: dist(PKT[5], START) / 55, ziel: true });
    else if (solved < 5) {
      if (anStation) { abschnitte.push({ typ: "gehen", von: PKT[solved], nach: PKT[solved + 1], w: dist(PKT[solved], PKT[solved + 1]) / 55 });
        abschnitte.push({ typ: "raten", bei: solved + 1, w: 3, offen: true }); }
      else abschnitte.push({ typ: "gehen", von: PKT[solved], nach: PKT[solved + 1], w: dist(PKT[solved], PKT[solved + 1]) / 55 * 0.6, teil: 0.6 });
    }
    const bis = platz ? t.finishedAt : tEnde - (lag || 0) * MIN - 20000;
    const von = WELT.startedAt + 2 * MIN;
    const summe = abschnitte.reduce((s, a) => s + a.w, 0) || 1;
    let zeit = von, letzter = START;
    const pts = t.points;
    const pushPt = (p, ms) => pts.push([+(p.lat + (rnd() - .5) * 0.00012).toFixed(6), +(p.lng + (rnd() - .5) * 0.00018).toFixed(6), Math.round(ms)]);
    abschnitte.forEach(a => {
      const dauer = a.w / summe * (bis - von);
      if (a.typ === "gehen") {
        const n = Math.max(3, Math.round(dauer / MIN));
        const teil = a.teil || 1;
        for (let j = 1; j <= n; j++) {
          const f = j / n * teil;
          letzter = { lat: a.von.lat + (a.nach.lat - a.von.lat) * f, lng: a.von.lng + (a.nach.lng - a.von.lng) * f };
          pushPt(letzter, zeit + dauer * j / n);
        }
      } else {
        t.events.push({ position: a.bei, checkedInAt: zeit, solvedAt: a.offen ? null : zeit + dauer });
        pushPt(letzter, zeit + dauer * .5);
        if (!a.offen) pushPt(letzter, zeit + dauer);
      }
      zeit += dauer;
    });
    const letztesEreignis = t.events.reduce((m, e) => Math.max(m, e.solvedAt || 0, e.checkedInAt || 0), 0);
    t.lastActivity = letztesEreignis || null;
    if (lag === null) pts.length = 0;   // hat nie einen Standort gemeldet (GPS nie freigegeben)
    if (pts.length) { const p = pts[pts.length - 1]; t.position = { lat: p[0], lng: p[1], accuracy: 9 + Math.round(rnd() * 14), updatedAt: p[2] }; }
  });
  // Delfin im laufenden Spiel: nie Standort gemeldet, aber schon an Station 1? Nein: noch unterwegs, ohne Aktivität.

  const doneCount = () => TEAMS.filter(t => t.place).length;
  const members = t => t.members.slice();

  /* ---------- Antworten ---------- */
  function teamState(t) {
    const istFuchs = t === FUCHS;
    const f = istFuchs ? FU : { solved: t.solved, checkedIn: t.checkedIn, failedAttempts: 0, lockedUntil: null, pauses: 0, tipShown: false };
    const all = f.solved >= 5;
    const cur = all ? null : STATIONEN[f.solved];
    const sum = STATIONEN.slice(0, f.solved).reduce((s, x) => s + x.digit, 0);
    const running = WELT.status === "running";
    const place = t.place;
    return {
      team: { id: t.id, name: t.name, code: t.code, readToken: t.readToken, leaderName: t.leaderName, members: members(t) },
      background: WELT.background, status: WELT.status, startedAt: iso(WELT.startedAt), durationMin: WELT.durationMin,
      endsAt: WELT.startedAt ? iso(WELT.startedAt + WELT.durationMin * MIN) : null,
      totalStations: 5, solvedCount: f.solved,
      digits: STATIONEN.map((s, i) => i < f.solved ? s.digit : null),
      finalDigit: all ? sum % 10 : null,
      station: cur && running ? { position: cur.position, name: cur.name, locationHint: cur.locationHint, lat: cur.lat, lng: cur.lng,
        radiusM: cur.radiusM, riddle: f.checkedIn ? cur.riddle : null,
        tipAvailable: !!cur.tip && !!f.checkedIn && (WELT.testMode || f.pauses >= 1), tip: f.tipShown ? cur.tip : null } : null,
      checkedIn: !!f.checkedIn && !all, failedAttempts: f.failedAttempts, lockedUntil: iso(f.lockedUntil), pauses: f.pauses,
      allSolved: all, caseHint: CASE_HINT, place, prizeCount: WELT.prizeCount, prizesLeft: Math.max(WELT.prizeCount - doneCount(), 0),
      winnerTeamId: (TEAMS.find(x => x.place === 1) || {}).id || null, isWinner: !!place && place <= WELT.prizeCount, testMode: WELT.testMode
    };
  }
  function memberState(t, name) {
    const s = teamState(t); delete s.team.code; delete s.team.readToken; s.name = name; return s;
  }
  const teamOf = p => TEAMS.find(t => t.id === p.teamId);
  const mitTeams = () => WELT.status !== "registration";
  function publicState() {
    const teams = mitTeams() ? TEAMS : [];
    const ranking = teams.map(t => ({ teamId: t.id, teamName: t.name, place: t.place, finishedAt: iso(t.finishedAt), solved: t.solved,
      lastSolvedAt: iso(t.events.reduce((m, e) => Math.max(m, e.solvedAt || 0), 0) || null), isWinner: !!t.place && t.place <= WELT.prizeCount }))
      .sort((a, b) => (a.place || 99) - (b.place || 99) || b.solved - a.solved || String(a.lastSolvedAt).localeCompare(String(b.lastSolvedAt)));
    return { background: WELT.background, status: WELT.status, startedAt: iso(WELT.startedAt), finishedAt: iso(WELT.finishedAt),
      winnerTeamId: (TEAMS.find(x => x.place === 1) || {}).id || null, prizeCount: WELT.prizeCount,
      participantCount: PERSONEN.length, stationCount: 5,
      teams: teams.map(t => ({ id: t.id, name: t.name, leaderName: t.leaderName, members: members(t) })), ranking };
  }
  function adminState() {
    const teams = mitTeams() ? TEAMS : [];
    return { background: WELT.background, status: WELT.status, startedAt: iso(WELT.startedAt), finishedAt: iso(WELT.finishedAt),
      durationMin: WELT.durationMin, endsAt: WELT.startedAt ? iso(WELT.startedAt + WELT.durationMin * MIN) : null,
      caseHint: CASE_HINT, winnerTeamId: (TEAMS.find(x => x.place === 1) || {}).id || null, prizeCount: WELT.prizeCount, testMode: WELT.testMode,
      participants: PERSONEN.map(p => ({ id: p.id, name: p.name, teamId: mitTeams() ? p.teamId : null, teamName: mitTeams() ? teamOf(p).name : null })),
      stations: STATIONEN.map(s => ({ id: s.id, position: s.position, name: s.name, lat: s.lat, lng: s.lng, radiusM: s.radiusM,
        locationHint: s.locationHint, riddle: s.riddle, answer: s.answer, digit: s.digit, tip: s.tip })),
      caseCode: CASE_CODE,
      teams: teams.map(t => ({ id: t.id, name: t.name, code: t.code, readToken: t.readToken, leaderId: t.leaderId, leaderName: t.leaderName,
        memberCount: t.members.length, members: members(t), solved: t.solved,
        currentPosition: t.solved < 5 ? t.solved + 1 : null,
        lastActivity: iso(t.lastActivity),
        // Nachtrag 21: Check-in an der aktuellen Station und letzte Lösung
        checkedInAt: iso((t.events.find(e => e.solvedAt == null && e.checkedInAt) || {}).checkedInAt || null),
        lastSolvedAt: iso(t.events.reduce((m, e) => Math.max(m, e.solvedAt || 0), 0) || null),
        position: t.position ? Object.assign({}, t.position, { updatedAt: iso(t.position.updatedAt) }) : null,
        place: t.place, finishedAt: iso(t.finishedAt) }))
    };
  }
  function adminTracks() {
    return { now: iso(Date.now()), status: WELT.status, startedAt: iso(WELT.startedAt), finishedAt: iso(WELT.finishedAt),
      winnerTeamId: (TEAMS.find(x => x.place === 1) || {}).id || null,
      teams: (mitTeams() ? TEAMS : []).map(t => ({ id: t.id, name: t.name, points: t.points, pointCount: t.points.length,
        stations: t.events.map(e => ({ position: e.position, checkedInAt: iso(e.checkedInAt), solvedAt: iso(e.solvedAt) })) })) };
  }
  const norm = s => String(s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().replace(/[^a-z0-9ß]/g, "");
  const fehler = msg => { const e = new Error(msg); e.rpc = true; throw e; };
  const pin = a => { if (a.p_pin !== "4711") fehler("Falsche PIN."); };
  const fuchsByCode = code => { const t = TEAMS.find(x => x.code === String(code || "").trim().toUpperCase()); if (!t || !mitTeams()) fehler("Unbekannter Team-Code."); return t; };

  const RPC = {
    public_state: () => publicState(),
    team_state: a => teamState(fuchsByCode(a.p_code)),
    member_state: a => { const p = PERSONEN.find(x => x.token === a.p_token); if (!p) fehler("Unbekanntes Gerät.");
      return mitTeams() ? memberState(teamOf(p), p.name) : { name: p.name, team: null }; },
    member_state_by_team: a => { const t = TEAMS.find(x => x.readToken === a.p_read_token); if (!t) fehler("Unbekannter Mitlese-Link."); return memberState(t, null); },
    lookup_participant: a => {
      const q = norm(a.p_name); if (!q) return { found: false };
      const exakt = PERSONEN.find(p => norm(p.name) === q);
      const treffer = exakt ? [exakt] : PERSONEN.filter(p => norm(p.name).includes(q));
      if (treffer.length > 1) return { found: false, candidates: treffer.slice(0, 8).map(p => p.name), more: treffer.length > 8 };
      if (!treffer.length) return { found: false };
      const p = treffer[0], t = mitTeams() ? teamOf(p) : null;
      return { found: true, name: p.name, team: t ? { name: t.name, leaderName: t.leaderName, members: members(t) } : null };
    },
    leader_code: a => { const p = PERSONEN.find(x => x.token === a.p_token); if (!p || !mitTeams()) fehler("Unbekanntes Gerät.");
      const t = teamOf(p); if (t.leaderId !== p.id) fehler("Du leitest gerade kein Team."); return { code: t.code }; },
    register_participant: a => { const name = String(a.p_name || "").trim(); if (name.length < 2) fehler("Bitte den vollen Namen eintragen.");
      return { name, token: "tok-neu", count: PERSONEN.length + 1 }; },
    check_in: a => {
      const t = fuchsByCode(a.p_code), s = STATIONEN[FU.solved];
      if (!s) return { ok: false, message: "Alle Stationen sind gelöst.", state: teamState(t) };
      const d = a.p_lat == null ? null : dist({ lat: a.p_lat, lng: a.p_lng }, s);
      if (!WELT.testMode && d > s.radiusM) return { ok: false, distance: Math.round(d), message: "Noch nicht am Ziel: " + Math.round(d) + " m entfernt.", state: teamState(t) };
      FU.checkedIn = true;
      return { ok: true, distance: d == null ? null : Math.round(d), message: WELT.testMode ? "Testmodus: eingecheckt ohne Entfernungsprüfung." : "Angekommen. Das Rätsel ist frei.", state: teamState(t) };
    },
    submit_answer: a => {
      const t = fuchsByCode(a.p_code), s = STATIONEN[FU.solved];
      if (WELT.testMode || s.answer.split("|").some(x => norm(x) === norm(a.p_answer))) {
        FU.solved++; FU.checkedIn = false; FU.failedAttempts = 0; FU.lockedUntil = null; FU.pauses = 0; FU.tipShown = false;
        return { ok: true, message: WELT.testMode ? "Testmodus: jede Antwort zählt. Eine Ziffer ist frei." : "Richtig. Eine Ziffer ist frei.", state: teamState(t) };
      }
      const n = FU.failedAttempts + 1;
      if (n >= 3) { FU.failedAttempts = 0; FU.lockedUntil = Date.now() + 120000; FU.pauses++;
        return { ok: false, message: "Dreimal falsch. Zwei Minuten Denkpause für euer Team.", state: teamState(t) }; }
      FU.failedAttempts = n;
      return { ok: false, message: "Leider falsch. Noch " + (3 - n) + " Versuch(e).", state: teamState(t) };
    },
    reveal_tip: a => { const t = fuchsByCode(a.p_code); FU.tipShown = true; return { ok: true, state: teamState(t) }; },
    submit_final: a => { const t = fuchsByCode(a.p_code);
      if (String(a.p_value).trim() !== CASE_CODE) return { ok: false, won: false, message: "Der Koffer bleibt zu. Prüft die letzte Ziffer.", state: teamState(t) };
      t.place = doneCount() + 1; t.finishedAt = Date.now();
      return { ok: true, won: t.place <= 3, message: "Koffer offen.", state: teamState(t) }; },
    report_position: () => ({ ok: true }),
    team_set_leader: a => teamState(fuchsByCode(a.p_code)),
    admin_state: a => { pin(a); return adminState(); },
    admin_tracks: a => { pin(a); return adminTracks(); },
    admin_delete_test_participants: a => { pin(a); return { deleted: 0, state: adminState() }; },
    admin_add_participants: a => { pin(a); return { added: 0, duplicates: 0, invalid: 0, state: adminState() }; },
    admin_start: a => { pin(a); return { state: adminState() }; }
  };

  /* ---------- fetch abfangen ---------- */
  const echtFetch = window.fetch.bind(window);
  const LOG = window.__RPC_LOG = [];
  window.fetch = async function (input, init) {
    const url = typeof input === "string" ? input : (input && input.url) || String(input);
    if (/supabase\.co/i.test(url)) throw new TypeError("Prüfstand: Anfragen an die Live-Datenbank sind gesperrt.");
    const m = url.match(/\/rest\/v1\/rpc\/([A-Za-z0-9_]+)/);
    if (!m) return echtFetch(input, init);
    let args = {};
    try { args = init && init.body ? JSON.parse(init.body) : {}; } catch { }
    await new Promise(r => setTimeout(r, 40));
    const fn = m[1];
    LOG.push(fn);
    const antwort = (status, data) => new Response(JSON.stringify(data), { status, headers: { "Content-Type": "application/json" } });
    try {
      // unbekannte Admin-Aufrufe: nichts tun, Stand zurückgeben
      const h = RPC[fn] || (fn.startsWith("admin_") ? (a => { pin(a); return adminState(); }) : null);
      if (!h) return antwort(404, { message: "Prüfstand kennt " + fn + " nicht." });
      return antwort(200, h(args));
    } catch (e) {
      return antwort(400, { message: e.message });
    }
  };

  /* ---------- Speicher und Ansicht vorbelegen ---------- */
  try {
    Object.keys(localStorage).filter(k => k.startsWith("sj.")).forEach(k => localStorage.removeItem(k));
    Object.keys(sessionStorage).filter(k => k.startsWith("sj.")).forEach(k => sessionStorage.removeItem(k));
    const ls = Object.assign({}, C.ls || {});
    if (C.kalHeute !== false) ls["sj.kal"] = new Date().toDateString();   // Einmessen heute schon erledigt
    Object.entries(ls).forEach(([k, v]) => localStorage.setItem(k, v));
    Object.entries(C.ss || {}).forEach(([k, v]) => sessionStorage.setItem(k, v));
  } catch (e) { console.warn("Prüfstand: Speicher gesperrt", e); }
  history.replaceState(null, "", location.pathname + location.search + "#/" + (C.view || "public"));

  /* ---------- Standort ---------- */
  const GPS = C.gps || null;
  const posObj = () => ({ coords: { latitude: GPS.lat, longitude: GPS.lng, accuracy: GPS.acc, altitude: null, altitudeAccuracy: null,
    heading: null, speed: null }, timestamp: Date.now() });
  const geo = {
    getCurrentPosition(ok, err) { setTimeout(() => GPS ? ok(posObj()) : err && err({ code: 3, message: "Zeitüberschreitung" }), 250); },
    watchPosition(ok) { const id = Math.floor(rnd() * 1e6) + 1; if (GPS) setTimeout(() => ok(posObj()), 150); return id; },
    clearWatch() { }
  };
  try { Object.defineProperty(navigator, "geolocation", { configurable: true, get: () => geo }); } catch (e) { console.warn(e); }

  /* ---------- Kompass: echte Ereignisse abfangen, eigene zustellen ---------- */
  const orientHandler = [];
  const addOrig = window.addEventListener;
  window.addEventListener = function (type, fn, opt) {
    if (/^deviceorientation/.test(type)) { orientHandler.push({ type, fn }); return; }
    return addOrig.call(this, type, fn, opt);
  };
  const zustellen = props => {
    const e = Object.assign({ timeStamp: performance.now(), alpha: null, beta: null, gamma: null, absolute: false }, props);
    const typ = orientHandler.some(h => h.type === "deviceorientationabsolute") ? "deviceorientationabsolute" : "deviceorientation";
    orientHandler.filter(h => h.type === typ).forEach(h => { try { h.fn(e); } catch (x) { console.error(x); } });
  };
  // alpha 63: Blickrichtung 297°, der Pfeil zeigt dann schräg nach links oben zur Station 2
  const ORIENT = {
    gut: () => ({ alpha: 63, beta: 35, gamma: 0, absolute: true }),
    // iOS-Art: Richtung mit schlechter Genauigkeit
    ungenau: () => ({ alpha: 63, beta: 35, gamma: 0, absolute: false, webkitCompassHeading: 297, webkitCompassAccuracy: 42 })
  };

  /* ---------- Schritte nach dem Laden ---------- */
  const warte = ms => new Promise(r => setTimeout(r, ms));
  async function bis(pruef, max = 8000) { const t0 = Date.now(); while (!pruef()) { if (Date.now() - t0 > max) return false; await warte(50); } return true; }
  async function lauf() {
    const app = () => document.getElementById("app");
    await bis(() => app() && app().children.length && !/Lade …/.test(app().textContent));
    await warte(250);
    for (const s of C.steps || []) {
      try {
        if (s.wait) await warte(s.wait);
        else if (s.until) { if (!await bis(() => document.querySelector(s.until))) console.warn("Prüfstand: nicht gefunden", s.until); }
        else if (s.fill) { const el = document.querySelector(s.fill[0]); if (el) { el.value = s.fill[1]; el.dispatchEvent(new Event("input", { bubbles: true })); } }
        else if (s.click) { const el = document.querySelector(s.click); if (el) el.click(); else console.warn("Prüfstand: kein Knopf", s.click); }
        else if (s.orient) { for (let i = 0; i < 4; i++) { zustellen(ORIENT[s.orient]()); await warte(60); } }
        else if (s.schwenken) {
          const t0 = performance.now(); let i = 0;
          while (performance.now() - t0 < s.schwenken) { i++; zustellen({ alpha: 63 + (i % 2 ? 6 : -6), beta: 35 + (i % 2 ? 22 : -22), gamma: i % 2 ? 15 : -15, absolute: true }); await warte(50); }
        }
      } catch (e) { console.error("Prüfstand-Schritt", s, e); }
    }
    await warte(C.settle || 600);
    window.__fertig = true;
  }
  window.addEventListener("DOMContentLoaded", () => { lauf(); });
})();
