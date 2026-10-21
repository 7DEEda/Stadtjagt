// Gemeinsame Beispieldaten für alle Design-Varianten (Stand des laufenden Spiels, 1:12 h nach Start).
// Alle Varianten zeigen denselben Moment, damit man nur das Design vergleicht.
window.SJ = {
  spiel: { status: "Läuft", rest: "1:47 h", start: "22:54", laeuftSeit: "1:12 h", testMode: false, stationen: 5 },

  // Das Handy von Team Fuchs (Teamleitung Anna Berger)
  team: {
    name: "Fuchs", tier: "🦊", farbe: "#0E7C86", leitung: "Anna Berger", code: "FUCHS-4821",
    mitglieder: ["Anna Berger", "Emre Demir", "Jonas Keller", "Julia Krüger", "Lea Hoffmann", "Maximilian Schröder", "Sophie Wagner", "Tobias Neumann"],
    ziffern: [3, null, null, null, null], // letzte Stelle (Schlussziffer) kommt dazu, ergibt sich aus der Summe
    station: {
      nr: 2, name: "Rudolfstollen",
      hinweis: "Geht in den Park hinein Richtung Westen. Der Eingang zum alten Wasserstollen liegt unter Bäumen am Hang.",
      raetsel: "Kaiser Rudolf II. ließ diesen Stollen graben, um Wasser in seinen Park zu leiten. Wie viele Meter ist er lang? Die Zahl steht auf der Tafel neben dem Tor.",
      loesungIstZahl: true, loesung: "527", ziffer: 7, // richtige Antwort gibt Ziffer 7 frei
    },
    entfernung: 245, checkinAb: 60, gpsGenau: 8, richtungGrad: 58, // Pfeil zeigt 58° nach rechts von "oben"
    fehlversuche: 0, maxFehlversuche: 3, pauseMin: 2,
    hilfe: { whatsapp: true, telefon: true },
  },

  stationen: [
    { nr: 1, name: "Markthalle Holešovice", lat: 50.1005, lng: 14.4395 },
    { nr: 2, name: "Rudolfstollen", lat: 50.1046, lng: 14.4166 },
    { nr: 3, name: "Metronom Letná", lat: 50.0955, lng: 14.4153 },
    { nr: 4, name: "Chotek-Park", lat: 50.0938, lng: 14.4075 },
    { nr: 5, name: "Löwenhof der Burg", lat: 50.0925, lng: 14.3995 },
  ],
  startpunkt: { name: "Mama Shelter Prague", lat: 50.1025, lng: 14.4317 },

  // Alle 12 Teams aus Sicht der Spielleitung
  // problem (optional): { stufe: "fehler" | "warnung", text }, gilt in allen Varianten gleich:
  // Delfin und Igel = Fehler, Otter = Warnung. Wer es löst (werten), verliert die Fehlversuch-Warnung.
  // ort: "unterwegs" (zu Station nr) | "station" (an Station nr, Rätsel offen) | "ziel" (fertig)
  teams: [
    { name: "Adler",    tier: "🦅", farbe: "#2F6E9E", leitung: "Clara Schulz",    code: "ADLER-8593",    geloest: 5, ort: "ziel",      nr: 5, seit: "31 min", gps: "vor 31 min", platz: 1, zeit: "23:47" },
    { name: "Eule",     tier: "🦉", farbe: "#C62828", leitung: "Moritz Hofmann",  code: "EULE-3398",     geloest: 4, ort: "unterwegs", nr: 5, seit: "8 min",  gps: "vor 1 min" },
    { name: "Panda",    tier: "🐼", farbe: "#E65100", leitung: "Merle Franke",    code: "PANDA-9534",    geloest: 3, ort: "unterwegs", nr: 4, seit: "9 min",  gps: "vor 1 min" },
    { name: "Tiger",    tier: "🐯", farbe: "#00695C", leitung: "Birgit Martin",   code: "TIGER-1090",    geloest: 3, ort: "station",   nr: 4, seit: "4 min",  gps: "vor 2 min" },
    { name: "Einhorn",  tier: "🦄", farbe: "#7B3FA0", leitung: "Sami Hofmann",    code: "EINHORN-5486",  geloest: 2, ort: "unterwegs", nr: 3, seit: "11 min", gps: "vor 2 min" },
    { name: "Otter",    tier: "🦦", farbe: "#4E6B1E", leitung: "Pia Peters",      code: "OTTER-7033",    geloest: 2, ort: "station",   nr: 3, seit: "5 min",  gps: "vor 3 min", fehlversuche: 2, problem: { stufe: "warnung", text: "2 Fehlversuche" } },
    { name: "Pinguin",  tier: "🐧", farbe: "#3949AB", leitung: "Dennis Martin",   code: "PINGUIN-2783",  geloest: 2, ort: "unterwegs", nr: 3, seit: "10 min", gps: "vor 20 s" },
    { name: "Wolf",     tier: "🐺", farbe: "#795548", leitung: "Ute Müller",      code: "WOLF-4877",     geloest: 2, ort: "unterwegs", nr: 3, seit: "11 min", gps: "vor 1 min" },
    { name: "Flamingo", tier: "🦩", farbe: "#F9A825", leitung: "Leon Lehmann",    code: "FLAMINGO-5967", geloest: 1, ort: "station",   nr: 2, seit: "7 min",  gps: "vor 4 min" },
    { name: "Fuchs",    tier: "🦊", farbe: "#0E7C86", leitung: "Anna Berger",     code: "FUCHS-4821",    geloest: 1, ort: "unterwegs", nr: 2, seit: "21 min", gps: "vor 20 s", entfernung: 245 },
    { name: "Igel",     tier: "🦔", farbe: "#AD1457", leitung: "Niklas Peters",   code: "IGEL-1678",     geloest: 1, ort: "unterwegs", nr: 2, seit: "27 min", gps: "vor 7 min", problem: { stufe: "fehler", text: "GPS vor 7 min" } },
    { name: "Delfin",   tier: "🐬", farbe: "#2E7D32", leitung: "Jan Schulz",      code: "DELFIN-1547",   geloest: 0, ort: "unterwegs", nr: 1, seit: "1:12 h", gps: null, problem: { stufe: "fehler", text: "kein GPS" } },
  ],

  // Was zuletzt passiert ist (neueste zuerst), für Ticker/Verlauf der Spielleitung
  ereignisse: [
    { zeit: "00:06", team: "Fuchs",    text: "Standort wieder da" },
    { zeit: "00:05", team: "Otter",    text: "2. Fehlversuch an Station 3", art: "warn" },
    { zeit: "00:04", team: "Tiger",    text: "eingecheckt an Station 4" },
    { zeit: "00:03", team: "Panda",    text: "Ziffer 3 erhalten", art: "ok" },
    { zeit: "00:01", team: "Igel",     text: "kein Standort seit 7 min", art: "err" },
    { zeit: "23:59", team: "Flamingo", text: "eingecheckt an Station 2" },
    { zeit: "23:58", team: "Eule",     text: "Ziffer 4 erhalten", art: "ok" },
    { zeit: "23:47", team: "Adler",    text: "Ziel erreicht, Platz 1", art: "ok" },
  ],
};
