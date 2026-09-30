// Die Suite des Geräte-Tests. geraete-test.html arbeitet diese Liste ab.
//
// Ein Baustein:
//   id      Kennung, unter der das Ergebnis gespeichert wird (nie umbenennen, sonst passen alte Läufe nicht mehr)
//   titel   Zeile in der Liste
//   bezug   wofür das Spiel es braucht
//   block   "auto" | "hand" | "neu": die Überschrift, unter der die Zeile steht
//   selbst  true: läuft nach dem einen Tipp von allein (in "auto" immer)
//   hand    Anweisung, wenn der Schritt eine Hand braucht
//   frage   Ja/Nein-Rückfrage nach dem Lauf; "Nein" macht aus ok ein "geht nicht"
//   grenze  Zeitgrenze in Sekunden (Standard 30, mit hand 100)
//   lauf    async (ctx) => { art: "ok" | "warn" | "err", wert: "kurz", mess: { ... } }
//
// ctx: rpc(fn, args), cfg {url, key}, warte(ms), status(text), sensor (Ausrichtung, siehe geraete-test.html),
//      bewegung (Ergebnis der iOS-Nachfrage), wach (gehaltener Wake Lock), feld (Element in der Zeile für Vorschau)
//
// Neuer Spielinhalt: Baustein anhängen und version hochzählen.
(function () {
  const KOMPASS_GRENZE = 25;   // wie in index.html
  const jetzt = () => performance.now();
  const rund = (x, n = 0) => x == null ? null : Math.round(x * 10 ** n) / 10 ** n;
  const komma = (x, n = 1) => x.toFixed(n).replace(".", ",");
  const median = a => { const s = [...a].sort((x, y) => x - y); return s[Math.floor(s.length / 2)]; };
  const janein = b => b ? "ja" : "nein";

  function bisSichtbarWechsel(ctx, maxMs) {
    // wartet auf "weg" und "wieder da"; gibt zurück, wie lange die Seite weg war
    return new Promise((res, rej) => {
      let weg = null;
      const aus = setTimeout(() => { document.removeEventListener("visibilitychange", h); rej(new Error("Die Seite war nie im Hintergrund.")); }, maxMs);
      function h() {
        if (document.visibilityState === "hidden") { weg = Date.now(); ctx.status("weg …"); }
        else if (weg != null) { clearTimeout(aus); document.removeEventListener("visibilitychange", h); res(Date.now() - weg); }
      }
      document.addEventListener("visibilitychange", h);
    });
  }

  function standortEinmal(timeout) {
    return new Promise((res, rej) => navigator.geolocation.getCurrentPosition(res, rej,
      { enableHighAccuracy: true, timeout, maximumAge: 0 }));
  }

  function skriptLaden(src) {
    return new Promise((res, rej) => {
      const s = document.createElement("script");
      s.src = src; s.onload = res; s.onerror = () => rej(new Error(src + " lädt nicht"));
      document.head.appendChild(s);
    });
  }

  const tests = [
    /* ================= von allein ================= */
    {
      id: "umgebung", titel: "Umgebung", bezug: "Zuordnung der Läufe", block: "auto",
      async lauf() {
        const ua = navigator.userAgent;
        let os = "unbekannt", m;
        if ((m = ua.match(/(?:iPhone|iPad|iPod).*? OS (\d+)[_.](\d+)/))) os = `iOS ${m[1]}.${m[2]}`;
        else if ((m = ua.match(/Android (\d+(?:\.\d+)?)/))) os = "Android " + m[1];
        else if (/Macintosh/.test(ua)) os = navigator.maxTouchPoints > 1 ? "iPadOS" : "macOS";
        else if (/Windows/.test(ua)) os = "Windows";
        else if (/Linux/.test(ua)) os = "Linux";
        const browser = /CriOS/.test(ua) ? "Chrome (iOS)" : /FxiOS/.test(ua) ? "Firefox (iOS)" : /EdgiOS|EdgA|Edg\//.test(ua) ? "Edge"
          : /SamsungBrowser/.test(ua) ? "Samsung Internet" : /Firefox/.test(ua) ? "Firefox" : /OPR\//.test(ua) ? "Opera"
          : /Chrome\//.test(ua) ? "Chrome" : /Safari/.test(ua) ? "Safari" : "unbekannt";
        const inApp = (ua.match(/FBAN|FBAV|Instagram|WhatsApp|Line\/|MicroMessenger|Teams|LinkedInApp|GSA\/|; wv\)/) || [null])[0];
        let akku = null;
        try { if (navigator.getBattery) { const b = await navigator.getBattery(); akku = Math.round(b.level * 100) + " %" + (b.charging ? ", lädt" : ""); } } catch { /* egal */ }
        const mess = {
          "Betriebssystem": os, "Browser": browser, "In-App-Browser": inApp || "nein",
          "HTTPS": janein(window.isSecureContext), "Bildschirm": `${screen.width} x ${screen.height}, Faktor ${rund(devicePixelRatio, 2)}`,
          "Fenster": `${innerWidth} x ${innerHeight}`, "Als App installiert": janein(matchMedia("(display-mode: standalone)").matches || navigator.standalone === true),
          "Sprache": navigator.language, "Netz laut Browser": navigator.connection ? `${navigator.connection.effectiveType || "?"}, ${navigator.connection.downlink ?? "?"} Mbit/s` : "keine Angabe",
          "Akku": akku || "keine Angabe", "Dunkles Design": janein(matchMedia("(prefers-color-scheme: dark)").matches), "Kennung": ua
        };
        if (!window.isSecureContext) return { art: "err", wert: "kein HTTPS", mess };
        if (inApp) return { art: "warn", wert: "In-App-Browser", mess };
        return { art: "ok", wert: `${os}, ${browser}`, mess };
      }
    },
    {
      id: "speicher", titel: "Speicher", bezug: "Geräte-Schlüssel der Anmeldung", block: "auto",
      async lauf() {
        const probe = name => { try { const s = window[name]; s.setItem("sj._t", "1"); const ok = s.getItem("sj._t") === "1"; s.removeItem("sj._t"); return ok; } catch { return false; } };
        const ls = probe("localStorage"), ss = probe("sessionStorage");
        let platz = "keine Angabe";
        try { if (navigator.storage?.estimate) { const e = await navigator.storage.estimate(); platz = Math.round((e.quota || 0) / 1048576) + " MB"; } } catch { /* egal */ }
        let dauerhaft = "keine Angabe";
        try { if (navigator.storage?.persisted) dauerhaft = janein(await navigator.storage.persisted()); } catch { /* egal */ }
        const mess = { "localStorage": janein(ls), "sessionStorage": janein(ss), "Cookies": janein(navigator.cookieEnabled), "Platz": platz, "Dauerhaft zugesagt": dauerhaft };
        return ls ? { art: "ok", wert: "schreibt", mess } : { art: "err", wert: "gesperrt", mess };
      }
    },
    {
      id: "server", titel: "Server", bezug: "alles im Spiel", block: "auto",
      async lauf(ctx) {
        const zeiten = [];
        for (let i = 0; i < 5; i++) { const t = jetzt(); await ctx.rpc("public_state"); zeiten.push(Math.round(jetzt() - t)); }
        const med = median(zeiten);
        const mess = { "5 Abfragen in ms": zeiten.join(", "), "Median in ms": med };
        return { art: med <= 800 ? "ok" : med <= 3000 ? "warn" : "err", wert: med + " ms", mess };
      }
    },
    {
      id: "uhr", titel: "Uhr", bezug: "Zeitachse, Spieldauer", block: "auto",
      async lauf(ctx) {
        let beste = null;
        for (let i = 0; i < 3; i++) {
          const t0 = Date.now(), r = await ctx.rpc("device_test_echo", { p_data: "" }), t1 = Date.now();
          const lauf = t1 - t0, ab = (t0 + t1) / 2 - Date.parse(r.serverTime);
          if (!beste || lauf < beste.lauf) beste = { lauf, ab };
        }
        const s = beste.ab / 1000, b = Math.abs(s);
        const mess = { "Abweichung in s": rund(s, 2), "Laufzeit der Messung in ms": beste.lauf, "Zeitzone": Intl.DateTimeFormat().resolvedOptions().timeZone };
        return { art: b <= 5 ? "ok" : b <= 60 ? "warn" : "err", wert: (s >= 0 ? "+" : "-") + komma(b) + " s", mess };
      }
    },
    {
      id: "standort", titel: "Standort", bezug: "Einchecken an der Station", block: "auto", grenze: 45,
      async lauf(ctx) {
        if (!navigator.geolocation) return { art: "err", wert: "fehlt", mess: { "Geolocation": "nicht vorhanden" } };
        let vorher = "keine Angabe";
        try { vorher = (await navigator.permissions?.query({ name: "geolocation" }))?.state || vorher; } catch { /* Safari kennt die Abfrage teils nicht */ }
        const start = jetzt(); let erst = null, beste = null, n = 0, letzte = null, fehler = null;
        const id = navigator.geolocation.watchPosition(p => {
          n++; letzte = p;
          if (erst == null) erst = jetzt() - start;
          if (beste == null || p.coords.accuracy < beste) beste = p.coords.accuracy;
          ctx.status("±" + Math.round(p.coords.accuracy) + " m");
        }, e => { fehler = e; }, { enableHighAccuracy: true, timeout: 20000, maximumAge: 0 });
        // bis zum ersten Fix höchstens 20 s, danach noch 10 s zuhören, ob es genauer wird
        while (erst == null && !fehler && jetzt() - start < 21000) await ctx.warte(200);
        const ab = jetzt();
        while (erst != null && jetzt() - ab < 10000 && !(beste <= 8)) await ctx.warte(200);
        navigator.geolocation.clearWatch(id);
        if (erst == null) {
          const grund = fehler ? ({ 1: "abgelehnt", 2: "nicht verfügbar", 3: "keine Antwort" }[fehler.code] || "Fehler") : "keine Antwort";
          return { art: "err", wert: grund, mess: { "Erlaubnis vorher": vorher, "Fehler": fehler ? `${fehler.code}: ${fehler.message}` : "20 s ohne Antwort" } };
        }
        const c = letzte.coords;
        const mess = {
          "Erlaubnis vorher": vorher, "Erster Fix nach s": rund(erst / 1000, 1), "Beste Genauigkeit in m": rund(beste),
          "Meldungen": n, "Position": `${c.latitude.toFixed(5)}, ${c.longitude.toFixed(5)}`,
          "Höhe": c.altitude == null ? "keine" : rund(c.altitude) + " m", "Bewegungsrichtung": c.heading == null || Number.isNaN(c.heading) ? "keine" : rund(c.heading) + "°",
          "Brauchbar wäre": "unter ±25 m"
        };
        return { art: beste <= 25 ? "ok" : beste <= 100 ? "warn" : "err", wert: "±" + Math.round(beste) + " m", mess };
      }
    },
    {
      id: "kompass", titel: "Kompass", bezug: "Richtungspfeil", block: "auto",
      async lauf(ctx) {
        const s = ctx.sensor;
        if (!window.DeviceOrientationEvent) return { art: "err", wert: "fehlt", mess: { "DeviceOrientationEvent": "nicht vorhanden" } };
        const n0 = s.n, t0 = jetzt();
        await ctx.warte(3000);
        const n = s.n - n0, rate = Math.round(n / ((jetzt() - t0) / 1000));
        const mess = {
          "Erlaubnis Bewegung": ctx.bewegung, "Ereignisse pro Sekunde": rate, "Quelle": s.quelle || "keine",
          "Richtung": s.richtung == null ? "keine" : Math.round(s.richtung) + "°",
          "Genauigkeit": s.genau == null ? "meldet das Gerät nicht" : "±" + rund(s.genau, 1) + "°",
          "deviceorientationabsolute": janein("ondeviceorientationabsolute" in window)
        };
        if (!n) return { art: "err", wert: "keine Daten", mess };
        if (s.quelle === "relativ" || s.richtung == null) return { art: "err", wert: "kein Nordbezug", mess };
        if (s.genau != null && (s.genau < 0 || s.genau > KOMPASS_GRENZE)) return { art: "warn", wert: s.genau < 0 ? "nicht kalibriert" : "±" + Math.round(s.genau) + "°", mess };
        return { art: "ok", wert: s.genau != null ? "±" + Math.round(s.genau) + "°" : "Nordbezug", mess };
      }
    },
    {
      id: "neigung", titel: "Neigung", bezug: "Hintergrund bewegt sich mit", block: "auto",
      async lauf(ctx) {
        const s = ctx.sensor, ruhig = matchMedia("(prefers-reduced-motion: reduce)").matches;
        const mess = { "beta / gamma": s.beta == null ? "keine" : `${rund(s.beta, 1)} / ${rund(s.gamma, 1)}`, "Reduzierte Bewegung": janein(ruhig),
          "Scroll-Parallax (animation-timeline)": janein(CSS.supports("animation-timeline: scroll()")) };
        if (s.beta == null) return { art: "err", wert: "keine Daten", mess };
        if (ruhig) return { art: "warn", wert: "abgeschaltet", mess };
        return { art: "ok", wert: "läuft", mess };
      }
    },
    {
      id: "wachhalten", titel: "Wach halten", bezug: "Handy sperrt unterwegs nicht", block: "auto",
      async lauf(ctx) {
        if (!navigator.wakeLock) return { art: "err", wert: "fehlt", mess: { "navigator.wakeLock": "nicht vorhanden" } };
        try { ctx.wach.sperre = await navigator.wakeLock.request("screen"); return { art: "ok", wert: "erteilt", mess: { "navigator.wakeLock": "ja" } }; }
        catch (e) { return { art: "warn", wert: "verweigert", mess: { "Fehler": e.name + ": " + e.message, "Häufiger Grund": "Stromsparmodus" } }; }
      }
    },
    {
      id: "karte", titel: "Karte", bezug: "Karte der Spielleitung", block: "auto",
      async lauf() {
        const mess = {}; let ok = true;
        let t = jetzt();
        try { const r = await fetch("https://unpkg.com/leaflet@1.9.4/dist/leaflet.js", { cache: "no-store" }); if (!r.ok) throw new Error(r.status); await r.text(); mess["Leaflet von unpkg in ms"] = Math.round(jetzt() - t); }
        catch (e) { ok = false; mess["Leaflet von unpkg"] = "lädt nicht: " + e.message; }
        t = jetzt();
        try {
          await new Promise((res, rej) => { const i = new Image(); i.onload = res; i.onerror = () => rej(new Error("Fehler")); i.src = "https://a.tile.openstreetmap.org/15/17696/11100.png"; });
          mess["OSM-Kachel Prag in ms"] = Math.round(jetzt() - t);
        } catch { ok = false; mess["OSM-Kachel Prag"] = "lädt nicht"; }
        if (!ok) return { art: "err", wert: "lädt nicht", mess };
        const summe = mess["Leaflet von unpkg in ms"] + mess["OSM-Kachel Prag in ms"];
        return { art: summe <= 3000 ? "ok" : "warn", wert: komma(summe / 1000) + " s", mess };
      }
    },
    {
      id: "schrift", titel: "Schrift", bezug: "Aussehen", block: "auto",
      async lauf() {
        const kopf = '700 19px "Barlow Semi Condensed"', text = "400 17px Barlow";
        try { await Promise.all([document.fonts.load(kopf), document.fonts.load(text)]); } catch { /* prüfen wir gleich */ }
        const k = document.fonts.check(kopf), t = document.fonts.check(text);
        const mess = { "Barlow Semi Condensed": janein(k), "Barlow": janein(t) };
        return k && t ? { art: "ok", wert: "Barlow", mess } : { art: "warn", wert: "Ersatzschrift", mess };
      }
    },
    {
      id: "teilen", titel: "Teilen", bezug: "Mitlese-Link", block: "auto",
      async lauf() {
        const a = typeof navigator.share === "function", b = !!navigator.clipboard?.writeText;
        const mess = { "Teilen-Dialog": janein(a), "Zwischenablage": janein(b) };
        return { art: a && b ? "ok" : a || b ? "warn" : "err", wert: a && b ? "beides" : a ? "nur Teilen" : b ? "nur Kopieren" : "fehlt", mess };
      }
    },

    /* ================= mit der Hand ================= */
    {
      id: "kompass-drehen", titel: "Kompass drehen", bezug: "Läuft die Richtung mit?", block: "hand",
      hand: "Tipp auf Los und dreh dich einmal langsam im Kreis.", grenze: 60,
      async lauf(ctx) {
        const s = ctx.sensor; s.faecher.clear();
        const t0 = jetzt();
        while (s.faecher.size < 30 && jetzt() - t0 < 45000) { ctx.status(`${s.faecher.size} von 36`); await ctx.warte(150); }
        const n = s.faecher.size, mess = { "Richtungen gesehen": `${n} von 36`, "Quelle": s.quelle || "keine", "Dauer in s": rund((jetzt() - t0) / 1000, 1) };
        if (s.quelle === "relativ" || !s.quelle) return { art: "err", wert: "kein Nordbezug", mess };
        return { art: n >= 30 ? "ok" : n >= 12 ? "warn" : "err", wert: `${n} von 36`, mess };
      }
    },
    {
      id: "bildschirm", titel: "Bildschirm aus und an", bezug: "Kommt der Standort wieder?", block: "hand",
      hand: "Tipp auf Los, sperr das Handy, zähl bis zehn und entsperr es wieder.", grenze: 180,
      async lauf(ctx) {
        ctx.status("jetzt sperren");
        const weg = await bisSichtbarWechsel(ctx, 120000);
        const mess = { "Bildschirm aus für s": rund(weg / 1000, 1) };
        const alt = ctx.wach.sperre;
        mess["Wake Lock beim Sperren freigegeben"] = alt ? janein(alt.released) : "war nicht gehalten";
        let neu = false;
        if (navigator.wakeLock) { try { ctx.wach.sperre = await navigator.wakeLock.request("screen"); neu = true; } catch (e) { mess["Wake Lock neu"] = e.name; } }
        mess["Wake Lock neu geholt"] = janein(neu);
        ctx.status("warte auf Standort");
        const t = jetzt();
        try {
          const p = await standortEinmal(20000);
          const s = (jetzt() - t) / 1000;
          mess["Standort zurück nach s"] = rund(s, 1); mess["Genauigkeit in m"] = rund(p.coords.accuracy);
          return { art: s <= 5 && (neu || !navigator.wakeLock) ? "ok" : "warn", wert: "nach " + komma(s) + " s", mess };
        } catch (e) { mess["Standort"] = `Fehler ${e.code}: ${e.message}`; return { art: "err", wert: "kein Standort", mess }; }
      }
    },
    {
      id: "app-wechsel", titel: "App wechseln", bezug: "Übersteht die Seite WhatsApp?", block: "hand",
      hand: "Tipp auf Los, wechsel kurz in eine andere App und komm zurück.", grenze: 180,
      async lauf(ctx) {
        ctx.status("jetzt wechseln");
        const weg = await bisSichtbarWechsel(ctx, 120000);
        const t = jetzt(); let netz = true;
        try { await ctx.rpc("public_state"); } catch { netz = false; }
        const mess = { "Weg für s": rund(weg / 1000, 1), "Server gleich wieder erreichbar": janein(netz), "Antwort in ms": Math.round(jetzt() - t),
          "Hinweis": "Lädt die Seite beim Zurückkommen neu, fehlt dieser Eintrag im Lauf." };
        return { art: netz ? "ok" : "warn", wert: netz ? "bleibt" : "Netz hängt", mess };
      }
    },

    /* ================= neue Funktionen ================= */
    {
      id: "kamera", titel: "Kamera und Foto", bezug: "Foto-Rätsel, Beweisfoto", block: "neu",
      hand: "Tipp auf Los und mach ein Foto von irgendetwas.", grenze: 180,
      lauf(ctx) {
        // Der Klick auf das Feld muss noch im Fingertipp passieren, darum kein async vor input.click()
        const input = document.createElement("input");
        input.type = "file"; input.accept = "image/*"; input.capture = "environment";
        input.hidden = true; document.body.appendChild(input);   // iOS öffnet die Kamera nur für ein Feld, das im Dokument hängt
        const gewaehlt = new Promise((res, rej) => {
          input.onchange = () => input.files[0] ? res(input.files[0]) : rej(new Error("kein Foto"));
          input.oncancel = () => rej(new Error("abgebrochen"));
        });
        input.click();
        ctx.status("wartet auf Foto");
        return (async () => {
          let datei;
          try { datei = await gewaehlt; } catch (e) { return { art: "err", wert: e.message, mess: {} }; }
          const mess = { "Aufnahme": `${rund(datei.size / 1048576, 1)} MB, ${datei.type || "Typ unbekannt"}` };
          let bild;
          try {
            bild = await new Promise((res, rej) => { const i = new Image(); i.onload = () => res(i); i.onerror = () => rej(new Error("nicht lesbar")); i.src = URL.createObjectURL(datei); });
          } catch { mess["Bild"] = "der Browser kann das Format nicht lesen"; return { art: "err", wert: "nicht lesbar", mess }; }
          mess["Bildgröße"] = `${bild.naturalWidth} x ${bild.naturalHeight}`;
          const f = Math.min(1, 1600 / Math.max(bild.naturalWidth, bild.naturalHeight));
          const c = document.createElement("canvas"); c.width = Math.round(bild.naturalWidth * f); c.height = Math.round(bild.naturalHeight * f);
          c.getContext("2d").drawImage(bild, 0, 0, c.width, c.height);
          URL.revokeObjectURL(bild.src);
          let url = c.toDataURL("image/jpeg", 0.8);
          if (url.length > 900000) url = c.toDataURL("image/jpeg", 0.5);
          mess["Verkleinert"] = `${c.width} x ${c.height}, ${Math.round(url.length * 0.75 / 1024)} KB`;
          if (ctx.feld) ctx.feld.innerHTML = `<img src="${url}" alt="" style="max-width:120px;border-radius:8px;margin-top:8px">`;
          ctx.status("lädt hoch");
          const t = jetzt();
          try {
            await ctx.rpc("device_test_echo", { p_data: url.slice(0, 1000000) });
            const s = (jetzt() - t) / 1000; mess["Hochladen in s"] = rund(s, 1);
            return { art: s <= 5 ? "ok" : "warn", wert: komma(s) + " s Upload", mess };
          } catch (e) { mess["Hochladen"] = e.message; return { art: "warn", wert: "Foto ja, Upload nein", mess }; }
        })();
      }
    },
    {
      id: "qr", titel: "QR-Code", bezug: "Code an der Station statt GPS", block: "neu",
      hand: "Tipp auf Los und halt die Kamera auf einen QR-Code. Einen zeigt geraete-test-qr.html am Laptop, jeder andere geht auch.", grenze: 60,
      async lauf(ctx) {
        const mess = { "BarcodeDetector": janein("BarcodeDetector" in window) };
        if (!navigator.mediaDevices?.getUserMedia) return { art: "err", wert: "keine Kamera", mess: { ...mess, "getUserMedia": "nicht vorhanden" } };
        let strom;
        try { strom = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" }, audio: false }); }
        catch (e) { return { art: "err", wert: e.name === "NotAllowedError" ? "abgelehnt" : "keine Kamera", mess: { ...mess, "Fehler": e.name + ": " + e.message } }; }
        const video = document.createElement("video");
        video.setAttribute("playsinline", ""); video.muted = true; video.srcObject = strom;
        video.style.cssText = "width:160px;border-radius:8px;margin-top:8px;display:block";
        if (ctx.feld) { ctx.feld.innerHTML = ""; ctx.feld.appendChild(video); }
        try {
          await video.play();
          const spur = strom.getVideoTracks()[0].getSettings();
          mess["Kamerabild"] = `${spur.width} x ${spur.height}`;
          try { await skriptLaden("vendor/jsQR.js"); } catch (e) { mess["jsQR"] = e.message; }
          let nativ = null;
          if ("BarcodeDetector" in window) { try { nativ = new BarcodeDetector({ formats: ["qr_code"] }); } catch (e) { mess["BarcodeDetector"] = "vorhanden, aber ohne QR: " + e.message; } }
          const c = document.createElement("canvas"), g = c.getContext("2d", { willReadFrequently: true });
          const t0 = jetzt(); let tNativ = null, tLib = null, inhalt = null, erster = null;
          ctx.status("sucht Code");
          while (jetzt() - t0 < 30000 && !(erster != null && jetzt() - erster > 2500) && !((tNativ != null || !nativ) && (tLib != null || !window.jsQR))) {
            if (nativ && tNativ == null) { try { const r = await nativ.detect(video); if (r.length) { tNativ = jetzt() - t0; inhalt = r[0].rawValue; } } catch { /* nächstes Bild */ } }
            if (window.jsQR && tLib == null && video.videoWidth) {
              const f = Math.min(1, 640 / video.videoWidth); c.width = Math.round(video.videoWidth * f); c.height = Math.round(video.videoHeight * f);
              g.drawImage(video, 0, 0, c.width, c.height);
              const d = g.getImageData(0, 0, c.width, c.height), r = window.jsQR(d.data, c.width, c.height);
              if (r && r.data) { tLib = jetzt() - t0; inhalt = inhalt || r.data; }
            }
            if (erster == null && (tNativ != null || tLib != null)) erster = jetzt();
            await ctx.warte(80);
          }
          mess["Eingebaut erkannt nach s"] = tNativ == null ? "nicht erkannt" : rund(tNativ / 1000, 1);
          mess["Mit jsQR erkannt nach s"] = tLib == null ? "nicht erkannt" : rund(tLib / 1000, 1);
          if (inhalt) mess["Inhalt"] = inhalt.slice(0, 80);
          if (tNativ != null) return { art: "ok", wert: "eingebaut", mess };
          if (tLib != null) return { art: "warn", wert: "nur Bibliothek", mess };
          return { art: "err", wert: "kein Code erkannt", mess };
        } finally { strom.getTracks().forEach(t => t.stop()); if (ctx.feld) ctx.feld.innerHTML = ""; }
      }
    },
    {
      id: "ton", titel: "Ton", bezug: "Audio-Rätsel, Signal", block: "neu",
      hand: "Tipp auf Los, es kommt ein kurzer Ton. Stummschalter und Lautstärke vorher prüfen.", frage: "Hast du den Ton gehört?",
      async lauf(ctx) {
        const AC = window.AudioContext || window.webkitAudioContext;
        if (!AC) return { art: "err", wert: "fehlt", mess: { "Web Audio": "nicht vorhanden" } };
        const ac = new AC();
        try { await ac.resume(); } catch { /* Zustand steht gleich im Ergebnis */ }
        const o = ac.createOscillator(), g = ac.createGain();
        o.frequency.value = 880; g.gain.value = 0.25; o.connect(g).connect(ac.destination);
        o.start(); o.stop(ac.currentTime + 0.7);
        await ctx.warte(900);
        const mess = { "Zustand": ac.state, "Abtastrate": ac.sampleRate, "Hinweis": "Auf iPhones schweigt die Seite, wenn der Stummschalter an ist." };
        ac.close();
        return mess["Zustand"] === "running" ? { art: "ok", wert: "gehört", mess } : { art: "err", wert: "gesperrt", mess };
      }
    },
    {
      id: "vibration", titel: "Vibration", bezug: "Rückmeldung bei richtiger Antwort", block: "neu",
      hand: "Tipp auf Los, das Handy vibriert zweimal kurz.", frage: "Hast du die Vibration gespürt?",
      async lauf(ctx) {
        if (typeof navigator.vibrate !== "function") return { art: "err", wert: "fehlt", mess: { "navigator.vibrate": "nicht vorhanden, auf iPhones immer" } };
        const r = navigator.vibrate([200, 120, 200]);
        await ctx.warte(700);
        return r ? { art: "ok", wert: "gespürt", mess: { "navigator.vibrate": "ja" } } : { art: "err", wert: "verweigert", mess: { "navigator.vibrate": "gibt false zurück" } };
      }
    },
    {
      id: "benachrichtigung", titel: "Benachrichtigung", bezug: "Hinweis bei gesperrtem Handy", block: "neu",
      hand: "Tipp auf Los und erlaube Mitteilungen, wenn das Handy fragt.",
      async lauf() {
        const mess = { "Notification": janein("Notification" in window), "Push": janein("PushManager" in window), "Service Worker": janein("serviceWorker" in navigator) };
        if (!("Notification" in window)) { mess["Hinweis"] = "Auf iPhones nur, wenn die Seite zum Home-Bildschirm hinzugefügt ist."; return { art: "err", wert: "fehlt", mess }; }
        let r;
        try { r = await Notification.requestPermission(); } catch (e) { mess["Fehler"] = e.message; return { art: "err", wert: "Fehler", mess }; }
        mess["Erlaubnis"] = r;
        if (r !== "granted") return { art: "warn", wert: r === "denied" ? "abgelehnt" : "offen", mess };
        try { new Notification("Stadtjagd Geräte-Test", { body: "Diese Mitteilung ist der Test." }); mess["Direkt angezeigt"] = "ja"; return { art: "ok", wert: "erlaubt", mess }; }
        catch (e) { mess["Direkt angezeigt"] = "nein, braucht einen Service Worker"; return { art: "warn", wert: "nur mit Service Worker", mess }; }
      }
    },
    {
      id: "live", titel: "Live-Verbindung", bezug: "Änderungen sofort statt per Abfrage", block: "neu", selbst: true,
      lauf(ctx) {
        return new Promise(res => {
          if (!("WebSocket" in window)) return res({ art: "err", wert: "fehlt", mess: { "WebSocket": "nicht vorhanden" } });
          const url = ctx.cfg.url.replace(/^http/, "ws").replace(/\/$/, "") + "/realtime/v1/websocket?apikey=" + encodeURIComponent(ctx.cfg.key) + "&vsn=1.0.0";
          const t0 = jetzt(); let offen = null, fertig = false, ws;
          const ende = e => { if (fertig) return; fertig = true; clearTimeout(aus); try { ws.close(); } catch { /* egal */ } res(e); };
          const aus = setTimeout(() => ende({ art: "err", wert: "keine Antwort", mess: { "Verbindung steht": janein(offen != null) } }), 8000);
          try { ws = new WebSocket(url); } catch (e) { return ende({ art: "err", wert: "Fehler", mess: { "Fehler": e.message } }); }
          ws.onopen = () => { offen = jetzt(); ws.send(JSON.stringify({ topic: "phoenix", event: "heartbeat", payload: {}, ref: "1" })); };
          ws.onmessage = () => ende({ art: "ok", wert: Math.round(jetzt() - offen) + " ms", mess: { "Aufbau in ms": Math.round(offen - t0), "Antwort auf Herzschlag in ms": Math.round(jetzt() - offen) } });
          ws.onerror = () => ende({ art: "err", wert: "kommt nicht durch", mess: { "Verbindung steht": janein(offen != null) } });
        });
      }
    },
    {
      id: "offline", titel: "Offline", bezug: "Seite trägt im Funkloch", block: "neu", selbst: true,
      async lauf() {
        const sw = "serviceWorker" in navigator; let cache = false, grund = "";
        if ("caches" in window) {
          try {
            const c = await caches.open("sj-geraetetest"), u = location.origin + location.pathname + "?cache-probe";
            await c.put(u, new Response("probe"));
            cache = (await (await c.match(u))?.text()) === "probe";
            await caches.delete("sj-geraetetest");
          } catch (e) { grund = e.name + ": " + e.message; }
        }
        const mess = { "Service Worker": janein(sw), "Cache schreibt und liest": janein(cache), "Hinweis": "Es wurde nichts dauerhaft eingerichtet." };
        if (grund) mess["Fehler"] = grund;
        return { art: sw && cache ? "ok" : sw || cache ? "warn" : "err", wert: sw && cache ? "möglich" : "fehlt", mess };
      }
    }
  ];

  window.SJ_TESTS = { version: 1, tests };
})();
