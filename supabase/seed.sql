-- ============================================================
--  STADTJAGD – Beispieldaten zum Testen
--
--  Fünf Stationen in Berlin-Mitte (Route ca. 3,5 km, Brandenburger Tor
--  bis Alexanderplatz) und 100 erfundene Teilnehmende, damit die Auslosung
--  zehn Teams ergibt. Alle Namen sind ausgedacht.
--
--  Im Supabase SQL-Editor ausführen, solange der Status "registration"
--  ist. Mehrfach ausführbar: Stationen werden überschrieben, vorhandene
--  Namen übersprungen. Zum Entfernen siehe Abschnitt "Aufräumen" unten.
--
--  Ziffern: 3, 7, 1, 9, 5. Summe 25, Einerstelle 5. Koffer-Code 371955.
-- ============================================================

-- ---------- Stationen ----------
update stations set
  name = 'Brandenburger Tor',
  lat = 52.516275, lng = 13.377704, radius_m = 60,
  location_hint = 'Sucht das Tor, dessen Wagenlenkerin einmal nach Paris entführt wurde und heute wieder nach Osten schaut.',
  riddle = 'Zählt die Säulen auf der Seite zum Pariser Platz.',
  answer = '6', digit = 3
where position = 1;

update stations set
  name = 'Reichstagsgebäude',
  lat = 52.518623, lng = 13.376198, radius_m = 80,
  location_hint = 'Ein Haus mit gläserner Kuppel, in dem seit 1999 wieder das Parlament tagt. Über dem Portal steht, wem es gewidmet ist.',
  riddle = 'Wie viele Wörter stehen über dem Hauptportal?',
  answer = '3', digit = 7
where position = 2;

update stations set
  name = 'Gendarmenmarkt',
  lat = 52.513622, lng = 13.392640, radius_m = 60,
  location_hint = 'Zwei Dome, ein Konzerthaus, dazwischen ein Dichter aus Marbach auf seinem Sockel.',
  riddle = 'Wie viele Frauenfiguren sitzen am Sockel des Dichters?',
  answer = '4', digit = 1
where position = 3;

update stations set
  name = 'Neptunbrunnen',
  lat = 52.519437, lng = 13.406781, radius_m = 60,
  location_hint = 'Ein Meeresgott sitzt auf einer Muschel, vor einem Rathaus, dessen Name seine Farbe verrät.',
  riddle = 'Wie viele Frauenfiguren sitzen am Beckenrand?',
  answer = '4', digit = 9
where position = 4;

update stations set
  name = 'Weltzeituhr (Koffer)',
  lat = 52.521180, lng = 13.413330, radius_m = 60,
  location_hint = 'Auf dem großen Platz, den Fernsehturm im Rücken, zeigt eine Säule die Zeit für die ganze Welt. Hier wartet der Koffer.',
  riddle = 'In wie viele Felder ist der Ring mit den Städtenamen geteilt?',
  answer = '24', digit = 5
where position = 5;

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
