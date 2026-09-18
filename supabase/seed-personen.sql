-- ============================================================
--  STADTJAGD – 100 erfundene Teilnehmende zum Testen
--
--  Nur für Proben. Alle Namen sind ausgedacht. Mehrfach ausführbar,
--  vorhandene Namen werden übersprungen.
--
--  Nicht auf einem Stand einspielen, auf dem schon ausgelost wurde:
--  Nachzügler landen sonst in keinem Team. Erst einspielen, dann auslosen.
--  Die Stationen stehen in seed-stationen-prag.sql.
-- ============================================================

-- ---------- Teilnehmende ----------
insert into participants (name, name_key)
select n, norm(n) from unnest(array[
  'Anna Bergmann','Jonas Keller','Lea Hoffmann','Timo Schreiber','Mira Voss',
  'Paul Lindner','Sarah Neumann','David Krüger','Nele Brandt','Felix Wagner',
  'Julia Sommer','Lukas Hartmann','Emma Richter','Noah Winkler','Hanna Zimmermann',
  'Ben Lorenz','Sofia Albrecht','Elias Frank','Marie Kühn','Leon Baumann',
  'Clara Weiß','Finn Jäger','Lina Vogel','Max Ludwig','Greta Seidel',
  'Tom Engel','Ida Roth','Jan Böhm','Nora Pfeiffer','Moritz Haas',
  'Katharina Schäfer','Sebastian Groß','Laura Wenzel','Niklas Ott','Franziska Ebert',
  'Philipp Hummel','Theresa Adler','Simon Kraus','Vanessa Dietrich','Fabian Sauer',
  'Melanie Busch','Christian Hess','Stefanie Kolb','Matthias Brunner','Anja Peters',
  'Daniel Reuter','Sandra Wolff','Oliver Beck','Miriam Thiele','Tobias Lang',
  'Jana Schulz','Marcel Hoppe','Verena Kaiser','Andreas Menzel','Birgit Ullrich',
  'Florian Nowak','Heike Stark','Robert Scholz','Petra Wendt','Markus Hahn',
  'Silke Bauer','Thomas Vogt','Ines Rudolph','Ralf Heinrich','Dagmar Pohl',
  'Uwe Bartels','Claudia Fiedler','Jens Mohr','Ulrike Sander','Karsten Behrens',
  'Lisa Marquardt','Dominik Werner','Sina Reinhardt','Kevin Arndt','Alina Geiger',
  'Patrick Ziegler','Jasmin Krause','Björn Hübner','Svenja Lehmann','Erik Rademacher',
  'Carolin Stein','Malte Voigt','Rebecca Jung','Henrik Paulsen','Tanja Herrmann',
  'Sven Kunze','Antonia Walter','Lars Petersen','Yasmin Schmitt','Aaron Lange',
  'Elena Fischer','Mehmet Yilmaz','Aylin Demir','Piotr Kowalski','Nadia Haddad',
  'Luca Romano','Viktor Petrov','Amira Saleh','Chiara Conti','Ole Jansen'
]) as n
on conflict (name_key) do nothing;

-- Kontrolle
select (select count(*) from participants) as teilnehmende,
       (select count(*) from stations where lat is not null) as stationen_mit_koordinaten,
       (select status from game_state where id = 1) as status;

-- ---------- Aufräumen ----------
-- Entfernt die Beispieldaten wieder und setzt das Spiel auf "registration".
-- Die Stationen bleiben stehen, bis du sie im Admin-Bereich überschreibst.
-- Zum Ausführen die Zeilen auskommentieren:
--
-- delete from progress where true;
-- delete from team_positions where true;
-- update participants set team_id = null where team_id is not null;
-- delete from teams where true;
-- delete from participants where true;
-- update game_state set status = 'registration', started_at = null,
--   finished_at = null, winner_team_id = null where id = 1;
