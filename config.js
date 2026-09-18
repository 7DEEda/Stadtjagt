// Verbindung zu Supabase. Beides steht in Supabase unter Project Settings > API.
// Der Publishable key (sb_publishable_...) ist zur Veröffentlichung gedacht und darf hier stehen.
// Der Secret key (sb_secret_...) gehört NIEMALS in diese Datei.
window.SJ_CONFIG = {
  url: "https://lwdmwklyydhcvnhpjudk.supabase.co",
  key: "sb_publishable_7uEQEkFwi27XJdGLSoso5w_TMxHJYUq",

  // Hilfe bei Problemen. Der Knopf öffnet WhatsApp mit einer vorbereiteten
  // Nachricht. Nummer international ohne Pluszeichen und ohne Leerzeichen,
  // deutsche Handynummer 0151 2345678 wird also zu "491512345678".
  //
  // Solange die Nummer leer ist, erscheint kein Hilfe-Knopf.
  //
  // ACHTUNG: Diese Nummer wird öffentlich. Sie steht im Quelltext der Seite,
  // die jede und jeder aufrufen kann, und das Repo ist ebenfalls öffentlich.
  // Nimm eine Nummer, bei der das in Ordnung ist, etwa ein Diensthandy.
  support: {
    name: "der Spielleitung",
    phone: "491720000000"   // TESTNUMMER 0172 0000000, vor dem Event durch die echte ersetzen
  }
};
