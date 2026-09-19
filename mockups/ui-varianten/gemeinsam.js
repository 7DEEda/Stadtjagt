/* Gemeinsame Spiellogik der drei UI-Varianten. Jede Variante liefert nur
   window.ZEICHNE(S) und liest den Zustand S; Klicks laufen über data-act.
   Die Rätsel sind Platzhalter, nicht vor Ort geprüft. */

const TEAM = {
  name: "Fuchs", emoji: "🦊", code: "FUCHS-4821", farbe: "#7B3FA0",
  leitung: "Anna Berger",
  mitglieder: ["Anna Berger", "Jonas Weber", "Leonie Hartmann", "Mehmet Kaya", "Sophie Braun", "Tim Schulz", "Clara Vogel", "Felix Neumann"]
};
const STATIONEN = [
  { n: 1, name: "Planetarium Praha", hinweis: "Im Park Stromovka steht ein weißer Kuppelbau. Sucht den Haupteingang.",
    raetsel: "Über dem Haupteingang steht das Eröffnungsjahr. Welches Jahr ist es?", antwort: "1960", ziffer: 3, tipp: "Die Zahl steht in Metall über der Glastür." },
  { n: 2, name: "Rudolfstollen", hinweis: "Unter dem Park läuft ein Wasserstollen aus dem 16. Jahrhundert. Sucht den gemauerten Einstieg am Hang.",
    raetsel: "Wie viele Stufen führen bis zur Gittertür hinab?", antwort: "12", ziffer: 7, tipp: "Zählt nur die Steinstufen, nicht den Absatz oben." },
  { n: 3, name: "Wasserturm Letná", hinweis: "Folgt dem Hang hinauf zum Turm mit dem spitzen Dach.",
    raetsel: "Wie viele Fenster hat die Seite zum Park?", antwort: "8", ziffer: 1, tipp: "Auch die kleinen Luken zählen." },
  { n: 4, name: "Aussicht Letná", hinweis: "Die ehemalige Bergstation der Standseilbahn, gebaut 1891 von František Křižík.",
    raetsel: "Nach wem ist die Bahn benannt? Der Nachname genügt.", antwort: "Křižík|Krizik", ziffer: 9, tipp: "Der Name steht auf der Tafel neben dem Tor." },
  { n: 5, name: "Metronom", hinweis: "Das große Pendel über der Moldau. Ihr seht es schon von weitem.",
    raetsel: "Welche Farbe hat der Sockel?", antwort: "rot", ziffer: 4, tipp: "Schaut von der Treppe aus." }
];
const PRUEF = STATIONEN.reduce((a, s) => a + s.ziffer, 0) % 10;
const CODE = STATIONEN.map(s => s.ziffer).join("") + PRUEF;
const WEG = [620, 410, 190, 60, 14];          // Entfernungen beim Näherkommen, zuletzt im Radius
const RADIUS = 30;
const FEED_BASIS = [
  { zeit: "14:02", text: "Start am Hotel Mama Shelter" }
];
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const vorname = n => String(n || "").split(" ")[0];
const norm = s => String(s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().replace(/[^a-z0-9]/g, "");
const fmtM = m => m >= 1000 ? (m / 1000).toFixed(1).replace(".", ",") + " km" : Math.round(m) + " m";

const S = {
  screen: "anmeldung", rolle: "leitung",
  registriert: false, name: "", hoch: false, sheet: false,
  station: 1, schritt: 0, eingecheckt: false, ziffern: [], versuche: 0, tipp: false, fehler: null, geloest: null,
  pause: 0, codeFehler: null, platz: null, nadel: 38, feed: FEED_BASIS.slice(), uhr: 102
};
const stn = () => STATIONEN[S.station - 1];
const dist = () => WEG[Math.min(S.schritt, WEG.length - 1)];
const imRadius = () => dist() <= RADIUS;
const leitung = () => S.rolle === "leitung";
const uhrText = () => `Noch ${Math.floor(S.uhr / 60)}:${String(S.uhr % 60).padStart(2, "0")} h`;
const jetzt = (() => { let m = 14 * 60 + 2; return () => { m += 7; return `${Math.floor(m / 60)}:${String(m % 60).padStart(2, "0")}`; }; })();
const uhrzeit = min => `${Math.floor(min / 60)}:${String(min % 60).padStart(2, "0")}`;
const zeitStation = k => uhrzeit(14 * 60 + 19 + k * 17);   // Beispielzeiten der gelösten Stationen
const log = text => S.feed.unshift({ zeit: jetzt(), text });

// Sprungmarken: jeder Bildschirm lässt sich direkt ansehen, mit plausiblem Stand davor
function springe(screen) {
  Object.assign(S, { screen, hoch: false, sheet: false, fehler: null, codeFehler: null, geloest: null, versuche: 0, tipp: false, pause: 0 });
  if (screen === "anmeldung") Object.assign(S, { registriert: false });
  if (screen === "team") Object.assign(S, { registriert: true, name: "Jonas Weber" });
  if (screen === "weg") Object.assign(S, { registriert: true, station: 2, schritt: 1, eingecheckt: false, ziffern: [3] });
  if (screen === "raetsel") Object.assign(S, { registriert: true, station: 2, schritt: 4, eingecheckt: true, ziffern: [3] });
  if (screen === "koffer") Object.assign(S, { registriert: true, station: 5, eingecheckt: true, ziffern: STATIONEN.map(s => s.ziffer) });
  if (screen === "ziel") Object.assign(S, { registriert: true, ziffern: STATIONEN.map(s => s.ziffer), platz: 2 });
  S.feed = FEED_BASIS.slice();
  for (let k = 0; k < S.ziffern.length; k++) S.feed.unshift({ zeit: zeitStation(k), text: `Station ${k + 1} gelöst, Ziffer ${STATIONEN[k].ziffer}` });
  if (screen === "raetsel") S.feed.unshift({ zeit: "14:44", text: `${vorname(TEAM.leitung)} hat an Station 2 eingecheckt` });
}

const ACT = {
  anmelden() { S.name = (document.getElementById("name")?.value || "").trim() || "Jonas Weber"; S.registriert = true; },
  auslosen() { S.screen = "team"; },
  hoch() { S.hoch = true; },
  "hoch-zu"() { S.hoch = false; },
  sheet() { S.sheet = !S.sheet; },
  start() { S.screen = "weg"; S.station = 1; S.schritt = 0; S.eingecheckt = false; S.ziffern = []; log("Das Spiel läuft"); },
  naeher() { S.schritt = Math.min(S.schritt + 1, WEG.length - 1); S.nadel = [38, 24, -12, 8, 2][S.schritt]; },
  da() {
    if (!imRadius()) { S.fehler = `Noch ${fmtM(dist())} bis zur Station. Eingecheckt wird erst im Umkreis von ${RADIUS} m.`; return; }
    S.eingecheckt = true; S.screen = "raetsel"; S.fehler = null; log(`${vorname(TEAM.leitung)} hat an Station ${S.station} eingecheckt`);
  },
  antwort() {
    const v = document.getElementById("antwort")?.value || "";
    if (stn().antwort.split("|").some(a => norm(a) === norm(v)) || norm(v) === "") {
      // leeres Feld zählt im Mockup als richtig, damit man schnell durchklicken kann
      S.ziffern.push(stn().ziffer); S.geloest = stn().ziffer; S.fehler = null; S.versuche = 0; S.tipp = false;
      log(`Station ${S.station} gelöst, Ziffer ${stn().ziffer}`);
    } else {
      S.versuche++;
      S.fehler = S.versuche >= 3 ? "Leider falsch. Jetzt 2 Minuten Denkpause, danach habt ihr wieder drei Versuche."
        : `Leider falsch. Noch ${3 - S.versuche} ${3 - S.versuche === 1 ? "Versuch" : "Versuche"} vor der Denkpause.`;
      if (S.versuche >= 3) S.pause = 120;
    }
  },
  tipp() { S.tipp = true; },
  weiter() {
    S.geloest = null;
    if (S.station >= STATIONEN.length) { S.screen = "koffer"; return; }
    S.station++; S.schritt = 0; S.eingecheckt = false; S.screen = "weg"; S.nadel = 38;
  },
  koffer() {
    const v = (document.getElementById("code")?.value || "").replace(/\D/g, "");
    if (v && v !== CODE) { S.codeFehler = "Der Code stimmt nicht. Prüft die sechste Ziffer: die Einerstelle der Summe."; return; }
    S.platz = 2; S.screen = "ziel"; log("Koffer-Code eingegeben, Platz 2");
  },
  neu() { springe("anmeldung"); },
  rolle(d) { S.rolle = d.rolle; }
};

function zeichne() {
  document.getElementById("app").innerHTML = window.ZEICHNE(S);
  document.querySelectorAll("[data-nadel]").forEach(n => n.style.setProperty("--nadel", S.nadel + "deg"));
  const w = document.querySelector("[data-schalter]");
  if (w) w.innerHTML = schalterHTML();
}
function melden() { if (window.parent !== window) window.parent.postMessage({ typ: "stand", screen: S.screen, rolle: S.rolle }, "*"); }

document.addEventListener("click", e => {
  const b = e.target.closest("[data-act]");
  if (!b) return;
  const d = b.dataset, vorher = S.screen;
  if (d.act === "springe") { springe(d.screen); zeichne(); melden(); return; }
  ACT[d.act]?.(d);
  zeichne();
  if (S.screen !== vorher || d.act === "rolle") melden();
});
document.addEventListener("keydown", e => {
  if (e.key !== "Enter" || e.target.tagName !== "INPUT") return;
  const b = e.target.closest("form, .feld")?.querySelector("[data-enter]") || document.querySelector("[data-enter]");
  b?.click();
});
// Die Übersicht steuert alle drei Handys gleichzeitig
window.addEventListener("message", e => {
  const m = e.data || {};
  if (m.typ !== "setze") return;
  if (m.rolle) S.rolle = m.rolle;
  if (m.screen && m.screen !== S.screen) springe(m.screen);
  zeichne();
});
// Nadel zittert leicht wie ein echter Kompass, Uhr und Denkpause laufen
setInterval(() => {
  const n = S.nadel + (Math.random() - .5) * 5;
  document.querySelectorAll("[data-nadel]").forEach(x => x.style.setProperty("--nadel", n + "deg"));
}, 900);
setInterval(() => {
  if (S.pause > 0) { S.pause = Math.max(0, S.pause - 10); if (!S.pause) { S.versuche = 0; S.fehler = null; } zeichne(); }
}, 1000);

const SCREENS = [["anmeldung", "Anmeldung"], ["team", "Team"], ["weg", "Unterwegs"], ["raetsel", "Rätsel"], ["koffer", "Koffer"], ["ziel", "Ziel"]];
// Schalter nur, wenn die Variante allein geöffnet ist (in der Übersicht steuert die Übersicht)
function schalterHTML() {
  return SCREENS.map(([k, t]) => `<button data-act="springe" data-screen="${k}" aria-pressed="${S.screen === k}">${t}</button>`).join("")
    + `<span class="trenn"></span>`
    + [["leitung", "Teamleitung"], ["mitglied", "Mitglied"]].map(([k, t]) => `<button data-act="rolle" data-rolle="${k}" aria-pressed="${S.rolle === k}">${t}</button>`).join("");
}
const SCHALTER_CSS = `
html.eingebettet .schalter{display:none}
.schalter{position:fixed;top:0;left:0;right:0;z-index:30;display:flex;gap:4px;overflow-x:auto;scrollbar-width:none;padding:6px 8px;background:#1F1F1F}
.schalter::-webkit-scrollbar{display:none}
.schalter button{flex:none;background:none;border:1px solid #555;color:#eee;border-radius:4px;padding:0 10px;font:600 13px system-ui,sans-serif;min-height:34px;cursor:pointer}
.schalter button[aria-pressed="true"]{background:#fff;border-color:#fff;color:#1F1F1F}
.schalter .trenn{flex:none;width:8px}
html:not(.eingebettet) #app{padding-top:46px}
html:not(.eingebettet) .kopf{top:46px}`;
function starten() {
  const st = document.createElement("style"); st.textContent = SCHALTER_CSS; document.head.appendChild(st);
  if (window.parent !== window) document.documentElement.classList.add("eingebettet");
  const q = new URLSearchParams(location.search);
  if (q.get("rolle")) S.rolle = q.get("rolle");
  springe(q.get("screen") || "anmeldung");
  zeichne();
}
