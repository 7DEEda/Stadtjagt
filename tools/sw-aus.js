/* Notausgang für den Service Worker der Stadtjagd (Ausfallsicherheit, Abschnitt 1.3). Wird NICHT ausgeliefert.

   Macht der Service Worker am Eventtag Ärger: diese Datei nach sw.js im Repo-Wurzelordner kopieren und pushen.
   Jedes Handy holt beim nächsten Laden mit Netz die neue sw.js (updateViaCache: "none"), sie löscht die Caches der
   Stadtjagd und meldet sich ab. Danach läuft die App wie ohne Service Worker. Kein Neuladen von selbst.

   Nur die eigenen Caches ("sj-*") und nur die eigene Registrierung: CacheStorage gilt für den ganzen Origin
   7deeda.github.io, also auch für den Geräte-Test und andere Pages-Projekte. */
"use strict";
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", e => {
  e.waitUntil((async () => {
    const namen = await caches.keys();
    await Promise.all(namen.filter(n => n.startsWith("sj-")).map(n => caches.delete(n)));
    await self.registration.unregister();
  })());
});
// Kein fetch-Handler: alles geht ans Netz wie ohne Service Worker.
