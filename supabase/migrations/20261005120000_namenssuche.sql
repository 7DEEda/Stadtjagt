-- Namenssuche verträgt Tippfehler (05.10.2026). Probelauf: tools/pruefstand/namenssuche_db.py.
-- Mehrfach ausführbar, löscht keine Daten.
--   lookup_participant:
--   1. genauer Treffer über norm() wie bisher
--   2. Namensteil ab 3 Zeichen wie bisher; mehrere Treffer kommen jetzt sortiert: erst die, bei denen ein
--      Wort des Namens mit der Eingabe beginnt ("Anna" -> Anna Berger vor Hanna Schulz), dann nach Name
--   3. NEU: kein Treffer und ab 3 Zeichen: ähnliche Namen als Vorschlag ('fuzzy': true), höchstens 5,
--      der nächste zuerst. Ähnlich heißt Editierabstand höchstens 1 (bis 7 Zeichen) bzw. 2 (ab 8 Zeichen)
--      zum ganzen Namen, zum Namen mit vertauschter Wortfolge ("Berger Anna") oder zu einem einzelnen Wort.
--      Ein Vorschlag wird nie von selbst übernommen, auch wenn es nur einer ist: die Person tippt ihn an.
-- Ohne Erweiterung (kein fuzzystrmatch): name_abstand ist ein kleiner Levenshtein in plpgsql; bei 100
-- Personen mit je 2 bis 3 Wörtern ist das billig.
-- Regel (SPIEL.md §9): nach jedem create einer Funktion die Rechte ausdrücklich setzen.

create or replace function name_abstand(a text, b text) returns int
language plpgsql immutable set search_path = public as $$
declare la int := length(a); lb int := length(b); vorher int[]; jetzt int[]; i int; j int; kosten int;
begin
  if la = 0 then return lb; end if;
  if lb = 0 then return la; end if;
  vorher := array(select generate_series(0, lb));
  for i in 1..la loop
    jetzt := array[i];
    for j in 1..lb loop
      kosten := case when substr(a, i, 1) = substr(b, j, 1) then 0 else 1 end;
      jetzt := jetzt || least(jetzt[j] + 1, vorher[j + 1] + 1, vorher[j] + kosten);
    end loop;
    vorher := jetzt;
  end loop;
  return vorher[lb + 1];
end $$;

create or replace function lookup_participant(p_name text) returns json
language plpgsql security definer set search_path = public as $$
declare v participants; t teams; v_key text := norm(p_name); v_treffer int; v_namen json;
        v_grenze int := case when length(norm(p_name)) >= 8 then 2 else 1 end;
begin
  select * into v from participants where name_key = v_key;
  if not found and length(v_key) >= 3 then
    -- kein genauer Treffer: Namensteile, etwa nur der Vorname
    select count(*) into v_treffer from participants where name_key like '%' || v_key || '%';
    if v_treffer = 1 then
      select * into v from participants where name_key like '%' || v_key || '%';
    elsif v_treffer > 1 then
      -- Wortanfang zuerst: "Anna" bringt Anna Berger vor Hanna Schulz
      select json_agg(name order by wortanfang desc, name) into v_namen from (
        select p.name, exists (select 1 from regexp_split_to_table(p.name, '[\s-]+') w where norm(w) like v_key || '%') as wortanfang
        from participants p where p.name_key like '%' || v_key || '%'
        order by 2 desc, 1 limit 8) x;
      return json_build_object('found', false, 'candidates', v_namen, 'more', v_treffer > 8);
    else
      -- nichts enthalten: ähnliche Namen vorschlagen (Tippfehler, vertauschte Wortfolge)
      select json_agg(name order by abstand, name) into v_namen from (
        select name, abstand from (
        select p.name, least(
                 name_abstand(p.name_key, v_key),
                 name_abstand(norm(array_to_string(array(select w from regexp_split_to_table(p.name, '\s+') with ordinality as x(w, n) order by n desc), ' ')), v_key),
                 (select min(name_abstand(norm(w), v_key)) from regexp_split_to_table(p.name, '[\s-]+') w where norm(w) <> '')
               ) as abstand
        from participants p) alle
        where abstand <= v_grenze
        order by abstand, name limit 5) x;
      if v_namen is not null then
        return json_build_object('found', false, 'candidates', v_namen, 'more', false, 'fuzzy', true);
      end if;
    end if;
  end if;
  if v.id is null then return json_build_object('found', false); end if;
  select * into t from teams where id = v.team_id;
  return json_build_object(
    'found', true, 'name', v.name,
    'team', case when t.id is null then null else json_build_object(
      'name', t.name,
      'leaderName', (select p.name from participants p where p.id = t.leader_participant_id),
      'members', coalesce((select json_agg(p2.name order by p2.name)
                           from participants p2 where p2.team_id = t.id), '[]'::json)
    ) end);
end $$;

revoke all on function name_abstand(text, text) from public, anon, authenticated;
grant execute on function lookup_participant(text) to anon, authenticated;
