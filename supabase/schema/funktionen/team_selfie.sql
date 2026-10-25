-- Erzeugt von tools/schema_abzug.py aus der Live-Datenbank. Nicht von Hand ändern.

-- Ausführen: public=ja, anon=ja, authenticated=ja
CREATE OR REPLACE FUNCTION public.team_selfie(p_code text, p_position integer, p_photo text, p_thumb text)
 RETURNS json
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare t teams; s stations; pr progress; v_photo bytea; v_thumb bytea;
begin
  t := team_by_code(p_code);
  if not (select selfie_on from game_state where id = 1) then
    raise exception 'Gruppenfotos sind ausgeschaltet.' using errcode='P0001';
  end if;
  select * into s from stations where position = p_position;
  if not found then raise exception 'Diese Station gibt es nicht.' using errcode='P0001'; end if;
  select * into pr from progress where team_id = t.id and station_id = s.id for update;
  if not found or pr.solved_at is null then
    raise exception 'Erst das Rätsel lösen, dann das Foto.' using errcode='P0001';
  end if;
  begin
    v_photo := decode(p_photo, 'base64'); v_thumb := decode(p_thumb, 'base64');
  exception when others then
    raise exception 'Das Foto ist beschädigt angekommen.' using errcode='P0001';
  end;
  if v_photo is null or v_thumb is null
     or substring(v_photo from 1 for 3) <> '\xffd8ff'::bytea
     or substring(v_thumb from 1 for 3) <> '\xffd8ff'::bytea then
    raise exception 'Das ist kein JPEG-Foto.' using errcode='P0001';
  end if;
  if octet_length(v_photo) > 716800 or octet_length(v_thumb) > 61440 then
    raise exception 'Das Foto ist zu groß.' using errcode='P0001';
  end if;
  -- Ersetzen nur, bis das Team an einer späteren Station eingecheckt hat. Nachreichen geht immer.
  if exists (select 1 from station_photos where team_id = t.id and station_id = s.id)
     and exists (select 1 from progress p2 join stations s2 on s2.id = p2.station_id
                 where p2.team_id = t.id and s2.position > s.position and p2.checked_in_at is not null) then
    raise exception 'Dieses Foto lässt sich nicht mehr ersetzen, ihr seid schon an der nächsten Station.' using errcode='P0001';
  end if;
  insert into station_photos (team_id, station_id, photo, thumb) values (t.id, s.id, v_photo, v_thumb)
    on conflict (team_id, station_id) do update
      set photo = excluded.photo, thumb = excluded.thumb, taken_at = now();
  update progress set selfie_at = coalesce(selfie_at, now()) where team_id = t.id and station_id = s.id;
  return team_state(p_code);
end $function$;
revoke all on function public.team_selfie(p_code text, p_position integer, p_photo text, p_thumb text) from public, anon, authenticated;
grant execute on function public.team_selfie(p_code text, p_position integer, p_photo text, p_thumb text) to public, anon, authenticated;
