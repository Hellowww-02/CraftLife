-- CraftLife Phase 4F: profil couple DUA sisi (kamu + pasangan) dengan gender terintegrasi.
-- Melengkapi Phase 4A (love_space_shared_profiles) tanpa mengubah fungsi lama.
-- Menambah kolom sisi "kamu" (my_*) dan tanggal lahir kedua sisi, serta memperluas
-- RPC save_love_space_shared_profile (backward compatible: parameter baru punya default).

alter table public.love_space_shared_profiles
  add column if not exists my_name text not null default '' check(char_length(my_name)<=120);
alter table public.love_space_shared_profiles
  add column if not exists my_gender text not null default 'male' check(my_gender in('male','female','other'));
alter table public.love_space_shared_profiles
  add column if not exists my_age integer not null default 25 check(my_age between 15 and 120);
alter table public.love_space_shared_profiles
  add column if not exists my_birthdate date;
alter table public.love_space_shared_profiles
  add column if not exists partner_birthdate date;

-- Ganti fungsi lama dengan versi diperluas (client lama tetap jalan: default diterapkan).
create or replace function public.save_love_space_shared_profile(
  p_love_space_id uuid, p_partner_name text, p_partner_gender text, p_partner_age integer,
  p_relationship_type text, p_start_date date,
  p_my_name text default '',
  p_my_gender text default 'male',
  p_my_age integer default 25,
  p_my_birthdate date default null,
  p_partner_birthdate date default null
)
returns jsonb language plpgsql security definer set search_path=public as $$
declare result jsonb;
begin
  if not public.can_write_love_space(p_love_space_id) then raise exception 'love_space_write_forbidden'; end if;
  if char_length(trim(coalesce(p_partner_name,'')))<1 then raise exception 'partner_name_required'; end if;
  insert into public.love_space_shared_profiles as p(
    love_space_id, partner_name, partner_gender, partner_age, relationship_type, start_date,
    my_name, my_gender, my_age, my_birthdate, partner_birthdate, updated_by
  ) values(
    p_love_space_id, left(trim(p_partner_name),120), p_partner_gender, p_partner_age,
    p_relationship_type, p_start_date,
    left(trim(coalesce(p_my_name,'')),120), coalesce(p_my_gender,'male'), p_my_age,
    p_my_birthdate, p_partner_birthdate, auth.uid()
  ) on conflict(love_space_id) do update set
    partner_name=excluded.partner_name, partner_gender=excluded.partner_gender,
    partner_age=excluded.partner_age, relationship_type=excluded.relationship_type,
    start_date=excluded.start_date,
    my_name=excluded.my_name, my_gender=excluded.my_gender, my_age=excluded.my_age,
    my_birthdate=excluded.my_birthdate, partner_birthdate=excluded.partner_birthdate,
    updated_by=auth.uid()
  returning to_jsonb(p) into result;
  return result;
end; $$;

revoke execute on function public.save_love_space_shared_profile(uuid,text,text,integer,text,date,text,text,integer,date,date) from public, anon;
grant execute on function public.save_love_space_shared_profile(uuid,text,text,integer,text,date,text,text,integer,date,date) to authenticated;
