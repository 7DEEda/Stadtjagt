-- ============================================================
--  STADTJAGD – fünf Stationen in Prag, Route Holešovice und Letná
--
--  Stand 18.09.2026: Orte und Koordinaten stehen, Rätsel und
--  Ortshinweise noch nicht. Die alte Altstadt-Route (Pulverturm bis
--  Petřín) steht in der Git-Historie, zuletzt in Commit 3569356.
--
--  Start: Hotel Mama Shelter Praha, Veletržní 1502/20, Praha 7-Holešovice
--         50.102458, 14.431681 (kein Datensatz, nur Treffpunkt)
--
--    1 Planetarium Prag        Planetárium Praha, Stromovka
--    2 Rudolfstollen           Rudolfova štola, Stromovka
--    3 Wasserturm Letná        Vodárenská věž Letná
--    4 Křižík-Seilbahn, oben   Horní stanice lanové dráhy Františka Křižíka
--    5 Metronom                Pražský metronom, Letná
--
--  Luftlinie: Start 440 m, 1 bis 2 570 m, 2 bis 3 470 m, 3 bis 4 620 m,
--  4 bis 5 680 m, zusammen rund 2,8 km. Zu Fuß eher 3,5 km, dazu der
--  Anstieg aus der Stromovka auf die Letná.
--
--  Ziffern wie bisher 3, 7, 1, 9, 5. Summe 25, Einerstelle 5,
--  Koffer-Code 371955.
--
--  PLATZHALTER: Rätsel "Rätsel folgt" mit leerer Lösung. Eine leere
--  Lösung zählt in submit_answer nie als richtig, eine Station ohne
--  Rätsel lässt sich also nicht aus Versehen lösen. Der Ortshinweis
--  der Station 5 erscheint am Ende als Hinweis auf den Koffer.
--
--  Im SQL-Editor ausführen oder mit tools/sql.py. Überschreibt die fünf
--  Stationen, lässt Teams, Personen und Fortschritt unberührt.
-- ============================================================

update stations set
  name = 'Planetarium Prag',
  lat = 50.105286, lng = 14.427406, radius_m = 50,
  location_hint = 'Ortshinweis folgt',
  riddle = 'Rätsel folgt', answer = '', digit = 3
where position = 1;

update stations set
  name = 'Rudolfstollen',
  -- Eingang im Park unter Bäumen, GPS dort schwächer: etwas großzügiger
  lat = 50.104441, lng = 14.419553, radius_m = 60,
  location_hint = 'Ortshinweis folgt',
  riddle = 'Rätsel folgt', answer = '', digit = 7
where position = 2;

update stations set
  name = 'Wasserturm Letná',
  lat = 50.100195, lng = 14.420089, radius_m = 50,
  location_hint = 'Ortshinweis folgt',
  riddle = 'Rätsel folgt', answer = '', digit = 1
where position = 3;

update stations set
  name = 'Křižík-Seilbahn, Bergstation',
  lat = 50.095789, lng = 14.425346, radius_m = 50,
  location_hint = 'Ortshinweis folgt',
  riddle = 'Rätsel folgt', answer = '', digit = 9
where position = 4;

update stations set
  name = 'Metronom',
  lat = 50.094775, lng = 14.415938, radius_m = 50,
  location_hint = 'Ortshinweis folgt',
  riddle = 'Rätsel folgt', answer = '', digit = 5
where position = 5;

-- Kontrolle
select position, name, lat, lng, digit,
       case when lat is null then 'Koordinaten fehlen'
            when answer = '' then 'Rätsel fehlt'
            else 'bereit' end as stand
from stations order by position;
