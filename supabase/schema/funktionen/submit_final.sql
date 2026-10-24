-- Erzeugt von tools/schema_abzug.py aus der Live-Datenbank. Nicht von Hand ändern.

-- Ausführen: public=ja, anon=ja, authenticated=ja
CREATE OR REPLACE FUNCTION public.submit_final(p_code text, p_value text, p_lat double precision DEFAULT NULL::double precision, p_lng double precision DEFAULT NULL::double precision, p_acc double precision DEFAULT NULL::double precision)
 RETURNS json
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare t teams; g game_state; v_total int; v_solved int; v_expected text; v_place int;
        ziel stations; d double precision; tol double precision;
begin
  t := team_by_code(p_code);
  select place into v_place from finishes where team_id = t.id;

  if v_place is null then
    select * into g from game_state where id = 1;
    if g.status <> 'running' then
      return json_build_object('ok', false, 'won', false, 'message', 'Das Spiel läuft gerade nicht.',
        'state', team_state(p_code));
    end if;
    select count(*) into v_total from stations;
    select count(*) into v_solved from progress pr join stations s on s.id = pr.station_id where pr.team_id = t.id and pr.solved_at is not null;
    if v_total = 0 or v_solved <> v_total then
      return json_build_object('ok', false, 'won', false, 'message', 'Ihr habt noch nicht alle Ziffern.',
        'state', team_state(p_code));
    end if;

    -- Am Koffer stehen: gleiche Regel wie beim Check-in, im Testmodus nicht
    if not g.test_mode then
      select * into ziel from stations order by position desc limit 1;
      if ziel.lat is not null and ziel.lng is not null then
        if p_lat is null or p_lng is null then
          return json_build_object('ok', false, 'won', false,
            'message', 'Ohne Standort kein Koffer. Bitte GPS freigeben.', 'state', team_state(p_code));
        end if;
        d := dist_m(p_lat, p_lng, ziel.lat, ziel.lng);
        tol := ziel.radius_m + least(greatest(coalesce(p_acc,0),0), 25);
        if d > tol then
          return json_build_object('ok', false, 'won', false, 'distance', round(d::numeric,0),
            'message', 'Den Code gebt ihr am Koffer ein: noch ' || round(d::numeric,0) || ' m bis dahin.',
            'state', team_state(p_code));
        end if;
      end if;
    end if;

    select string_agg(s.digit::text, '' order by s.position) into v_expected from stations s;
    v_expected := v_expected || ((select sum(digit) from stations) % 10)::text;
    if regexp_replace(coalesce(p_value,''), '[^0-9]', '', 'g') <> v_expected then
      return json_build_object('ok', false, 'won', false,
        'message', 'Der Koffer bleibt zu. Prüft die letzte Ziffer.', 'state', team_state(p_code));
    end if;

    -- Platz vergeben. Die Sperre lässt gleichzeitige Eingaben warten, bis die
    -- vorige fertig ist; danach sieht die nächste deren Platz schon.
    perform 1 from game_state where id = 1 for update;
    select place into v_place from finishes where team_id = t.id;   -- doppelt abgeschickt?
    if v_place is null then
      select coalesce(max(place), 0) + 1 into v_place from finishes;
      insert into finishes(team_id, place) values (t.id, v_place);
      if v_place = 1 then
        update game_state set winner_team_id = t.id where id = 1;
      end if;
    end if;
  end if;

  select * into g from game_state where id = 1;
  return json_build_object('ok', true, 'won', v_place <= g.prize_count, 'place', v_place,
    'message', case when v_place <= g.prize_count
                    then 'Der Koffer ist offen. Platz ' || v_place || '!'
                    else 'Richtig, aber die Koffer sind vergeben. Ihr seid auf Platz ' || v_place || '.' end,
    'state', team_state(p_code));
end $function$;
revoke all on function public.submit_final(p_code text, p_value text, p_lat double precision, p_lng double precision, p_acc double precision) from public, anon, authenticated;
grant execute on function public.submit_final(p_code text, p_value text, p_lat double precision, p_lng double precision, p_acc double precision) to public, anon, authenticated;
