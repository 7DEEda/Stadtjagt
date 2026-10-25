-- Erzeugt von tools/schema_abzug.py aus der Live-Datenbank. Nicht von Hand ändern.

-- Ausführen: public=nein, anon=nein, authenticated=nein
CREATE OR REPLACE FUNCTION public.norm(t text)
 RETURNS text
 LANGUAGE sql
 IMMUTABLE
AS $function$
  select regexp_replace(
    translate(
      replace(replace(replace(replace(
        lower(translate(coalesce(t,''),
          'ÄÖÜÀÁÂÃÅĀĂĄÇĆČĎĐÈÉÊËĒĖĘĚÌÍÎÏĪĮĹĽŁÑŃŇÒÓÔÕØŌŐŔŘŚŠŞȘŤŢȚÙÚÛŮŪŰŲÝŸŹŻŽ',
          'äöüàáâãåāăąçćčďđèéêëēėęěìíîïīįĺľłñńňòóôõøōőŕřśšşșťţțùúûůūűųýÿźżž')),
        'ä','ae'),'ö','oe'),'ü','ue'),'ß','ss'),
      'àáâãåāăąçćčďđèéêëēėęěìíîïīįıĺľłñńňòóôõøōőŕřśšşșťţțùúûůūűųýÿźżž',
      'aaaaaaaacccddeeeeeeeeiiiiiiilllnnnooooooorrsssstttuuuuuuuyyzzz'),
    '[^a-z0-9]+', '', 'g');
$function$;
revoke all on function public.norm(t text) from public, anon, authenticated;
