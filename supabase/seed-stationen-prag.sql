-- ============================================================
--  STADTJAGD – fünf Stationen in Prag
--
--  Route durch die Altstadt und über die Moldau auf den Petřín,
--  rund 2,4 km plus Anstieg. Reihenfolge wie nummeriert:
--
--    1 Pulverturm            Prašná brána
--    2 Astronomische Uhr     Staroměstský orloj
--    3 Karlsbrücke           Karlův most, Altstädter Brückenturm
--    4 Lennon-Mauer          Lennonova zeď auf der Kampa
--    5 Aussichtsturm Petřín  Petřínská rozhledna, dort steht der Koffer
--
--  Ziffern 3, 7, 1, 9, 5. Summe 25, Einerstelle 5, Koffer-Code 371955.
--
--  ACHTUNG, vor dem Event prüfen: Die Rätsel und ihre Lösungen sind nach
--  bestem Wissen gesetzt, aber niemand von uns stand mit dem Zollstock
--  davor. Lauf die Route einmal ab, prüfe jede Antwort vor Ort und
--  korrigiere sie im Reiter Stationen. Dasselbe gilt für die Koordinaten:
--  sie zeigen auf den Ort, nicht auf den Meter genau auf das Detail.
--
--  Im SQL-Editor ausführen oder mit tools/sql.py. Überschreibt die fünf
--  Stationen, lässt Teams, Personen und Fortschritt unberührt.
-- ============================================================

update stations set
  name = 'Pulverturm',
  lat = 50.087500, lng = 14.428060, radius_m = 50,
  location_hint = 'Ein schwarzes gotisches Tor am Rand der Altstadt. Früher lagerte hier das Schießpulver, das ihm den Namen gab. Von hier begannen die Krönungszüge.',
  riddle = 'Am Turm steht die Jahreszahl, in der der Grundstein gelegt wurde. Welche ist es?',
  answer = '1475', digit = 3
where position = 1;

update stations set
  name = 'Astronomische Uhr',
  lat = 50.087000, lng = 14.420440, radius_m = 50,
  location_hint = 'Am Rathaus des großen Platzes zeigt eine Uhr nicht nur die Stunde, sondern auch den Lauf von Sonne und Mond. Zur vollen Stunde wird es dort voll.',
  riddle = 'Wie viele Apostel ziehen zur vollen Stunde an den beiden Fenstern vorbei?',
  answer = '12', digit = 7
where position = 2;

update stations set
  name = 'Karlsbrücke',
  lat = 50.086360, lng = 14.413740, radius_m = 60,
  location_hint = 'Die steinerne Brücke mit den Heiligenfiguren, benannt nach dem Kaiser, der sie bauen ließ. Stellt euch an den Turm auf der Altstadtseite.',
  riddle = 'Wie viele Statuengruppen säumen die Brücke insgesamt?',
  answer = '30', digit = 1
where position = 3;

update stations set
  name = 'Lennon-Mauer',
  lat = 50.086330, lng = 14.406830, radius_m = 45,
  location_hint = 'Auf der Kleinseite, hinter dem Kanal: eine Wand voller Farbe, seit 1980 immer wieder neu übermalt. Benannt nach einem Musiker aus Liverpool.',
  riddle = 'Gegenüber der Mauer weht die Flagge einer Botschaft. Zu welchem Land gehört sie?',
  answer = 'Frankreich', digit = 9
where position = 4;

update stations set
  name = 'Aussichtsturm Petřín',
  lat = 50.083440, lng = 14.395000, radius_m = 60,
  location_hint = 'Der kleine eiserne Bruder eines berühmten Pariser Turms, oben auf dem bewaldeten Hügel über der Kleinseite. Hier wartet der Koffer.',
  riddle = 'Wie viele Stufen führen hinauf auf die obere Aussichtsplattform?',
  answer = '299', digit = 5
where position = 5;

-- Kontrolle
select position, name, lat, lng, digit,
       case when lat is null then 'Koordinaten fehlen' else 'bereit' end as stand
from stations order by position;
