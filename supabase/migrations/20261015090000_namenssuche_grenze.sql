-- Namenssuche mit Längengrenze (Code-Review 15.10.2026, Befund 3). Probelauf: tools/pruefstand/namenssuche_grenze_db.py.
-- Mehrfach ausführbar, löscht keine Daten. Vorlage: lookup_participant aus 20261005120000_namenssuche.sql.
-- lookup_participant ist für anon offen. name_abstand ist ein Levenshtein in plpgsql, der je Zeile ein Array
-- anhängt: bei langer Eingabe wächst der Aufwand mit dem Quadrat der Länge, je Person und Wort. Eine Eingabe
-- mit ein paar tausend Zeichen band so die Datenbank für Sekunden.
--   1. Eingaben über 60 Zeichen (nach norm) suchen nur genau, ohne Namensteile und ohne Tippfehler-Suche.
--      Kein echter Name ist so lang; die genaue Suche läuft über den Index auf name_key.
--   2. Tippfehler-Suche: Kandidaten (ganzer Name, vertauschte Wortfolge, einzelnes Wort), deren Länge sich
--      um mehr als die erlaubte Distanz (1 bzw. 2) von der Eingabe unterscheidet, überspringen ohne
--      name_abstand. Ihr Abstand wäre ohnehin größer als die Grenze, das Ergebnis bleibt gleich.
-- Signatur unverändert (create or replace behält die Rechte); nach SPIEL.md §9 trotzdem ausdrücklich gesetzt.

create or replace function lookup_participant(p_name text) returns json
language plpgsql security definer set search_path = public as $$
declare v participants; t teams; v_key text := norm(p_name); v_treffer int; v_namen json;
        v_lang int := length(norm(p_name));
        v_grenze int := case when length(norm(p_name)) >= 8 then 2 else 1 end;
begin
  select * into v from participants where name_key = v_key;
  if not found and v_lang >= 3 and v_lang <= 60 then
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
      -- nichts enthalten: ähnliche Namen vorschlagen (Tippfehler, vertauschte Wortfolge). Was in der Länge
      -- schon weiter abweicht als die Grenze, bekommt keinen Abstand (null zählt in least() nicht).
      select json_agg(name order by abstand, name) into v_namen from (
        select name, abstand from (
        select p.name, least(
                 case when abs(length(p.name_key) - v_lang) <= v_grenze then name_abstand(p.name_key, v_key) end,
                 (select case when abs(length(r.k) - v_lang) <= v_grenze then name_abstand(r.k, v_key) end
                    from (select norm(array_to_string(array(select w from regexp_split_to_table(p.name, '\s+') with ordinality as x(w, n) order by n desc), ' ')) as k) r),
                 (select min(name_abstand(norm(w), v_key)) from regexp_split_to_table(p.name, '[\s-]+') w
                   where norm(w) <> '' and abs(length(norm(w)) - v_lang) <= v_grenze)
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
