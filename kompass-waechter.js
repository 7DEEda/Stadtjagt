// Kompass-Wächter (Nachtrag 30): vergleicht Kompass und Gyroskop und urteilt, ob dem Kompass zu trauen ist.
// Reine Logik ohne DOM, damit sie im Prüfstand mit erfundenen Sensorfolgen geprüft werden kann.
// Schwellen aus docs/superpowers/specs/2026-10-02-teststation-kompass-waechter-design.md, Teil 2.
(function () {
  const DREH_START = 8, RUHE = 3, RUHE_MS = 1000, DREH_MAX_MS = 10000, DREH_MIN = 90;
  const GUT = 20, SCHLECHT = 45, STILL_MS = 3000, WANDERN = 30;
  const kurz = d => ((d % 360) + 540) % 360 - 180;

  window.KompassWaechter = function (opt) {
    opt = opt || {};
    let urteil = opt.vorbelastet ? "unzuverlaessig" : null, vorbelastet = !!opt.vorbelastet, streng = !!opt.vorbelastet, versuche = opt.versuche || 0;
    let ergebnisse = [], gutInFolge = 0, nachEinmessen = -1;   // -1: nicht nach Einmessen, sonst Zahl der Ergebnisse seither
    let gyroWinkel = 0, gyroT = null, gyroDa = false, rate = 0, letzteBewegung = 0;
    let kompassAlt = null, kompassWeg = 0;
    let dreh = null, still = null;

    const melden = () => { if (opt.onWechsel) opt.onWechsel({ urteil, vorbelastet, versuche, prueft: nachEinmessen >= 0 }); };
    function ergebnis(e) {
      ergebnisse.push(e); if (ergebnisse.length > 4) ergebnisse.shift();
      const vorher = urteil, prueftVorher = nachEinmessen >= 0;
      if (nachEinmessen >= 0) {
        nachEinmessen++;
        if (e === "schlecht" && urteil === "unzuverlaessig") { versuche++; nachEinmessen = -1; }
        else if (nachEinmessen >= (streng ? 5 : 3)) nachEinmessen = -1;   // so viele Abschnitte, wie die Rückkehr braucht
      }
      if (e === "gut") {
        gutInFolge++;
        if (urteil !== "unzuverlaessig") urteil = "ok";
        else if (gutInFolge >= (streng ? 5 : 3)) { urteil = "ok"; vorbelastet = false; streng = false; versuche = 0; ergebnisse = []; }
      } else {
        gutInFolge = 0;
        if (ergebnisse.filter(x => x === "schlecht").length >= 3 && urteil !== "unzuverlaessig") { urteil = "unzuverlaessig"; vorbelastet = true; }
        else if (urteil == null) urteil = "ok";
      }
      if (urteil !== vorher || e === "schlecht" || (nachEinmessen >= 0) !== prueftVorher) melden();
    }
    function schritt(t) {
      if (!gyroDa) return;
      const a = Math.abs(rate);
      if (a > RUHE) letzteBewegung = t;
      if (!dreh && a > DREH_START) { dreh = { t0: t, g0: gyroWinkel, k0: kompassWeg }; still = null; }
      if (dreh && (t - letzteBewegung > RUHE_MS || t - dreh.t0 > DREH_MAX_MS)) {
        const gw = gyroWinkel - dreh.g0, kw = kompassWeg - dreh.k0;
        dreh = null;
        if (Math.abs(gw) >= DREH_MIN) {
          const d = Math.abs(kw - gw);
          if (d <= GUT) ergebnis("gut"); else if (d > SCHLECHT) ergebnis("schlecht");
        }
      }
      if (!dreh) {
        if (a >= RUHE) still = null;
        else if (!still) still = { t0: t, w0: kompassWeg };
        else if (t - still.t0 >= STILL_MS) {
          // Stillstand zählt nur als schlecht (Wandern), nie als gut: ein eingefrorener Kompass wandert nicht
          if (Math.abs(kompassWeg - still.w0) > WANDERN) ergebnis("schlecht");
          still = { t0: t, w0: kompassWeg };
        }
      }
    }
    return {
      gyro(r, t) {
        if (gyroT != null) gyroWinkel += r * Math.min(0.1, Math.max(0, (t - gyroT) / 1000));
        gyroT = t; rate = r; gyroDa = true; schritt(t);
      },
      kompass(g, t) {
        if (kompassAlt != null) { const d = kurz(g - kompassAlt); kompassWeg += d; }
        kompassAlt = g; schritt(t);
      },
      pause() { dreh = null; still = null; kompassAlt = null; gyroT = null; },
      einmessen() { ergebnisse = []; gutInFolge = 0; nachEinmessen = 0; dreh = null; still = null; melden(); },
      get urteil() { return urteil; },
      get versuche() { return versuche; },
      get prueft() { return nachEinmessen >= 0; },
      get vorbelastet() { return vorbelastet; },
      get ergebnisse() { return ergebnisse.slice(); }
    };
  };
})();
