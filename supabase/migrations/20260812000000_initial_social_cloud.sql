-- CraftLife Supabase staging: Auth/Profile/Friends/Couple/Love Gallery
-- Run through Supabase migrations. Never execute with a secret key from the desktop app.

create extension if not exists pgcrypto;
create extension if not exists citext;

create or replace function public.set_updated_at()
returns trigger language plpgsql as $$
begin new.updated_at = now(); return new; end; $$;

create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  username citext not null unique,
  display_name text not null default '',
  bio text not null default '',
  avatar_path text,
  avatar_class text not null default 'warrior',
  avatar_color text not null default '#5a8a2e',
  avatar_emoji text not null default '⚔️',
  deleted_at timestamptz,
  scheduled_purge_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint username_shape check (username ~ '^[a-zA-Z0-9_-]{3,32}$')
);
create trigger profiles_updated_at before update on public.profiles
for each row execute function public.set_updated_at();

create table if not exists public.friendships (
  id uuid primary key default gen_random_uuid(),
  requester_id uuid not null references public.profiles(id) on delete cascade,
  addressee_id uuid not null references public.profiles(id) on delete cascade,
  status text not null default 'pending' check (status in ('pending','accepted','rejected','cancelled')),
  created_at timestamptz not null default now(),
  responded_at timestamptz,
  updated_at timestamptz not null default now(),
  check (requester_id <> addressee_id)
);
create unique index if not exists friendships_pair_unique
on public.friendships (least(requester_id,addressee_id),greatest(requester_id,addressee_id));
create index if not exists friendships_requester_status on public.friendships(requester_id,status);
create index if not exists friendships_addressee_status on public.friendships(addressee_id,status);
create trigger friendships_updated_at before update on public.friendships
for each row execute function public.set_updated_at();

create table if not exists public.couple_relationships (
  id uuid primary key default gen_random_uuid(),
  user_a_id uuid not null references public.profiles(id) on delete cascade,
  user_b_id uuid not null references public.profiles(id) on delete cascade,
  requested_by uuid not null references public.profiles(id) on delete cascade,
  status text not null default 'pending' check (status in ('pending','accepted','rejected','cancelled','ended')),
  created_at timestamptz not null default now(),
  responded_at timestamptz,
  ended_at timestamptz,
  grace_ends_at timestamptz,
  updated_at timestamptz not null default now(),
  unique(user_a_id,user_b_id),
  check(user_a_id < user_b_id),
  check(requested_by in (user_a_id,user_b_id))
);
create index if not exists couples_a_status on public.couple_relationships(user_a_id,status);
create index if not exists couples_b_status on public.couple_relationships(user_b_id,status);
create trigger couple_updated_at before update on public.couple_relationships
for each row execute function public.set_updated_at();

create table if not exists public.love_spaces (
  id uuid primary key default gen_random_uuid(),
  couple_relationship_id uuid not null unique references public.couple_relationships(id) on delete cascade,
  created_at timestamptz not null default now()
);

create table if not exists public.love_space_members (
  love_space_id uuid not null references public.love_spaces(id) on delete cascade,
  user_id uuid not null references public.profiles(id) on delete cascade,
  role text not null default 'member',
  joined_at timestamptz not null default now(),
  primary key(love_space_id,user_id)
);
create index if not exists love_members_user on public.love_space_members(user_id,love_space_id);

create table if not exists public.love_space_photos (
  id uuid primary key default gen_random_uuid(),
  love_space_id uuid references public.love_spaces(id) on delete cascade,
  uploader_id uuid not null references public.profiles(id) on delete cascade,
  visibility text not null default 'private' check (visibility in ('private','shared')),
  storage_path text not null unique,
  mime_type text not null default 'image/webp' check (mime_type in ('image/webp','image/jpeg','image/png')),
  width integer not null check (width between 32 and 4096),
  height integer not null check (height between 32 and 4096),
  size_bytes bigint not null check (size_bytes between 1 and 5242880),
  caption text not null default '' check (char_length(caption) <= 140),
  photo_date date,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check ((visibility='private' and love_space_id is null) or
         (visibility='shared' and love_space_id is not null))
);
create index if not exists love_photos_space_date on public.love_space_photos(love_space_id,photo_date desc);
create index if not exists love_photos_uploader on public.love_space_photos(uploader_id,created_at desc);
create trigger love_photos_updated_at before update on public.love_space_photos
for each row execute function public.set_updated_at();

create table if not exists public.account_deletion_requests (
  user_id uuid primary key references public.profiles(id) on delete cascade,
  requested_at timestamptz not null default now(),
  scheduled_purge_at timestamptz not null default (now()+interval '30 days'),
  cancelled_at timestamptz,
  purged_at timestamptz
);

-- Auth bootstrap. A username may be supplied in user metadata; otherwise use a stable UUID-based value.
create or replace function public.handle_new_auth_user()
returns trigger language plpgsql security definer set search_path=public as $$
begin
  insert into public.profiles(id,username,display_name)
  values(new.id,
    coalesce(nullif(new.raw_user_meta_data->>'username',''),'user_'||substr(new.id::text,1,8)),
    coalesce(nullif(new.raw_user_meta_data->>'display_name',''),split_part(coalesce(new.email,''),'@',1)))
  on conflict(id) do nothing;
  return new;
end; $$;
drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created after insert on auth.users
for each row execute function public.handle_new_auth_user();

-- Backfill accounts created before this migration/trigger was installed.
insert into public.profiles(id,username,display_name)
select u.id,
  coalesce(nullif(u.raw_user_meta_data->>'username',''),'user_'||substr(u.id::text,1,8)),
  coalesce(nullif(u.raw_user_meta_data->>'display_name',''),split_part(coalesce(u.email,''),'@',1))
from auth.users u
on conflict(id) do nothing;

create or replace function public.current_email_verified()
returns boolean language sql stable security definer set search_path=public,auth as $$
  select exists(select 1 from auth.users where id=auth.uid() and email_confirmed_at is not null)
$$;

create or replace function public.current_profile_active()
returns boolean language sql stable security definer set search_path=public as $$
  select public.current_email_verified() and exists(
    select 1 from public.profiles where id=auth.uid() and deleted_at is null
  )
$$;

create or replace function public.is_accepted_friend(other_id uuid)
returns boolean language sql stable security definer set search_path=public as $$
  select exists(select 1 from public.friendships f where f.status='accepted'
    and ((f.requester_id=auth.uid() and f.addressee_id=other_id)
      or (f.addressee_id=auth.uid() and f.requester_id=other_id)))
$$;

create or replace function public.can_read_love_space(space_id uuid)
returns boolean language sql stable security definer set search_path=public as $$
  select exists(
    select 1 from public.love_space_members m
    join public.love_spaces s on s.id=m.love_space_id
    join public.couple_relationships c on c.id=s.couple_relationship_id
    where m.love_space_id=space_id and m.user_id=auth.uid()
      and (c.status='accepted' or (c.status='ended' and c.grace_ends_at>now()))
  )
$$;

create or replace function public.can_write_love_space(space_id uuid)
returns boolean language sql stable security definer set search_path=public as $$
  select exists(
    select 1 from public.love_space_members m
    join public.love_spaces s on s.id=m.love_space_id
    join public.couple_relationships c on c.id=s.couple_relationship_id
    where m.love_space_id=space_id and m.user_id=auth.uid() and c.status='accepted'
  )
$$;

create or replace function public.safe_uuid(value text)
returns uuid language plpgsql immutable as $$
begin return value::uuid; exception when others then return null; end; $$;

-- Atomic social RPCs. Desktop clients cannot directly forge relationship state.
create or replace function public.send_friend_request(target_username text)
returns public.friendships language plpgsql security definer set search_path=public as $$
declare target_id uuid; result public.friendships;
begin
  if not public.current_profile_active() then raise exception 'email_not_verified'; end if;
  select id into target_id from public.profiles where username=target_username and deleted_at is null;
  if target_id is null then raise exception 'user_not_found'; end if;
  if target_id=auth.uid() then raise exception 'self_request'; end if;
  insert into public.friendships(requester_id,addressee_id,status)
  values(auth.uid(),target_id,'pending') returning * into result;
  return result;
exception when unique_violation then raise exception 'friendship_exists';
end; $$;

create or replace function public.respond_friend_request(friendship_id uuid,accept_request boolean)
returns public.friendships language plpgsql security definer set search_path=public as $$
declare result public.friendships;
begin
  if not public.current_profile_active() then raise exception 'email_not_verified'; end if;
  update public.friendships set status=case when accept_request then 'accepted' else 'rejected' end,
    responded_at=now() where id=friendship_id and addressee_id=auth.uid() and status='pending'
    returning * into result;
  if result.id is null then raise exception 'invalid_request'; end if;
  return result;
end; $$;

create or replace function public.remove_friendship(friendship_id uuid)
returns boolean language plpgsql security definer set search_path=public as $$
begin
  delete from public.friendships where id=friendship_id and auth.uid() in (requester_id,addressee_id);
  return found;
end; $$;

create or replace function public.send_couple_request(target_user_id uuid)
returns public.couple_relationships language plpgsql security definer set search_path=public as $$
declare a uuid; b uuid; existing public.couple_relationships; result public.couple_relationships;
begin
  if not public.current_profile_active() then raise exception 'email_not_verified'; end if;
  if target_user_id=auth.uid() then raise exception 'self_request'; end if;
  if not public.is_accepted_friend(target_user_id) then raise exception 'not_friends'; end if;
  a=least(auth.uid(),target_user_id); b=greatest(auth.uid(),target_user_id);
  perform pg_advisory_xact_lock(hashtextextended(a::text,0));
  perform pg_advisory_xact_lock(hashtextextended(b::text,0));
  if exists(select 1 from public.couple_relationships where status='accepted'
      and (user_a_id in (a,b) or user_b_id in (a,b))) then raise exception 'partner_exists'; end if;
  select * into existing from public.couple_relationships where user_a_id=a and user_b_id=b for update;
  if existing.status in ('pending','accepted') then raise exception 'request_exists'; end if;
  if existing.id is not null then
    update public.couple_relationships set requested_by=auth.uid(),status='pending',created_at=now(),
      responded_at=null,ended_at=null,grace_ends_at=null where id=existing.id returning * into result;
  else
    insert into public.couple_relationships(user_a_id,user_b_id,requested_by)
      values(a,b,auth.uid()) returning * into result;
  end if;
  return result;
end; $$;

create or replace function public.respond_couple_request(relationship_id uuid,accept_request boolean)
returns jsonb language plpgsql security definer set search_path=public as $$
declare rel public.couple_relationships; space_id uuid;
begin
  if not public.current_profile_active() then raise exception 'email_not_verified'; end if;
  select * into rel from public.couple_relationships where id=relationship_id and status='pending' for update;
  if rel.id is null or auth.uid() not in (rel.user_a_id,rel.user_b_id) or rel.requested_by=auth.uid()
    then raise exception 'invalid_request'; end if;
  if not accept_request then
    update public.couple_relationships set status='rejected',responded_at=now() where id=rel.id;
    return jsonb_build_object('status','rejected','relationship_id',rel.id);
  end if;
  perform pg_advisory_xact_lock(hashtextextended(rel.user_a_id::text,0));
  perform pg_advisory_xact_lock(hashtextextended(rel.user_b_id::text,0));
  if not public.is_accepted_friend(case when auth.uid()=rel.user_a_id then rel.user_b_id else rel.user_a_id end)
    then raise exception 'not_friends'; end if;
  if exists(select 1 from public.couple_relationships where id<>rel.id and status='accepted'
      and (user_a_id in (rel.user_a_id,rel.user_b_id) or user_b_id in (rel.user_a_id,rel.user_b_id)))
    then raise exception 'partner_exists'; end if;
  update public.couple_relationships set status='accepted',responded_at=now() where id=rel.id;
  insert into public.love_spaces(couple_relationship_id) values(rel.id)
    on conflict(couple_relationship_id) do update set couple_relationship_id=excluded.couple_relationship_id
    returning id into space_id;
  insert into public.love_space_members(love_space_id,user_id) values
    (space_id,rel.user_a_id),(space_id,rel.user_b_id) on conflict do nothing;
  return jsonb_build_object('status','accepted','relationship_id',rel.id,'love_space_id',space_id);
end; $$;

create or replace function public.cancel_couple_request(relationship_id uuid)
returns boolean language plpgsql security definer set search_path=public as $$
begin
  update public.couple_relationships set status='cancelled',responded_at=now()
    where id=relationship_id and requested_by=auth.uid() and status='pending';
  return found;
end; $$;

create or replace function public.end_couple_relationship(relationship_id uuid)
returns jsonb language plpgsql security definer set search_path=public as $$
declare rel public.couple_relationships;
begin
  update public.couple_relationships set status='ended',ended_at=now(),grace_ends_at=now()+interval '30 days'
    where id=relationship_id and status='accepted' and auth.uid() in (user_a_id,user_b_id)
    returning * into rel;
  if rel.id is null then raise exception 'invalid_relationship'; end if;
  return jsonb_build_object('status','ended','grace_ends_at',rel.grace_ends_at);
end; $$;

create or replace function public.register_love_photo(
  p_photo_id uuid,p_love_space_id uuid,p_visibility text,p_storage_path text,p_mime_type text,
  p_width integer,p_height integer,p_size_bytes bigint,p_caption text,p_photo_date date)
returns public.love_space_photos language plpgsql security definer set search_path=public as $$
declare total_size bigint; result public.love_space_photos;
begin
  if not public.current_profile_active() then raise exception 'email_not_verified'; end if;
  if p_size_bytes<1 or p_size_bytes>5242880 then raise exception 'invalid_size'; end if;
  if p_visibility='shared' then
    if p_love_space_id is null or not public.can_write_love_space(p_love_space_id) then raise exception 'not_member'; end if;
    perform pg_advisory_xact_lock(hashtextextended(p_love_space_id::text,0));
    select coalesce(sum(p.size_bytes),0) into total_size from public.love_space_photos p where p.love_space_id=p_love_space_id;
  elsif p_visibility='private' then
    p_love_space_id=null;
    perform pg_advisory_xact_lock(hashtextextended(auth.uid()::text,0));
    select coalesce(sum(p.size_bytes),0) into total_size from public.love_space_photos p where p.uploader_id=auth.uid() and p.visibility='private';
  else raise exception 'invalid_visibility'; end if;
  if total_size+p_size_bytes>1073741824 then raise exception 'quota_exceeded'; end if;
  insert into public.love_space_photos(id,love_space_id,uploader_id,visibility,storage_path,mime_type,
    width,height,size_bytes,caption,photo_date)
  values(p_photo_id,p_love_space_id,auth.uid(),p_visibility,p_storage_path,p_mime_type,p_width,p_height,p_size_bytes,
         left(coalesce(p_caption,''),140),p_photo_date) returning * into result;
  return result;
end; $$;

create or replace function public.request_account_deletion()
returns jsonb language plpgsql security definer set search_path=public as $$
declare purge_at timestamptz:=now()+interval '30 days';
begin
  update public.profiles set deleted_at=now(),scheduled_purge_at=purge_at where id=auth.uid();
  insert into public.account_deletion_requests(user_id,requested_at,scheduled_purge_at)
  values(auth.uid(),now(),purge_at) on conflict(user_id) do update set requested_at=now(),
    scheduled_purge_at=purge_at,cancelled_at=null,purged_at=null;
  return jsonb_build_object('scheduled_purge_at',purge_at);
end; $$;

create or replace function public.cancel_account_deletion()
returns boolean language plpgsql security definer set search_path=public as $$
begin
  update public.profiles set deleted_at=null,scheduled_purge_at=null
    where id=auth.uid() and scheduled_purge_at>now();
  update public.account_deletion_requests set cancelled_at=now()
    where user_id=auth.uid() and purged_at is null;
  return found;
end; $$;

-- RLS
alter table public.profiles enable row level security;
alter table public.friendships enable row level security;
alter table public.couple_relationships enable row level security;
alter table public.love_spaces enable row level security;
alter table public.love_space_members enable row level security;
alter table public.love_space_photos enable row level security;
alter table public.account_deletion_requests enable row level security;

create policy profiles_authenticated_read on public.profiles for select to authenticated
using (deleted_at is null or id=auth.uid());
create policy profiles_owner_update on public.profiles for update to authenticated
using (id=auth.uid()) with check (id=auth.uid());

create policy friendships_participant_read on public.friendships for select to authenticated
using (auth.uid() in (requester_id,addressee_id));
-- Inserts/status updates are RPC-only.

create policy couples_participant_read on public.couple_relationships for select to authenticated
using (auth.uid() in (user_a_id,user_b_id));

create policy love_spaces_member_read on public.love_spaces for select to authenticated
using (public.can_read_love_space(id));
create policy love_members_member_read on public.love_space_members for select to authenticated
using (public.can_read_love_space(love_space_id));

create policy love_photos_read on public.love_space_photos for select to authenticated
using ((visibility='private' and uploader_id=auth.uid()) or
       (visibility='shared' and (public.can_read_love_space(love_space_id) or
          (uploader_id=auth.uid() and exists(select 1 from public.couple_relationships c
            join public.love_spaces s on s.couple_relationship_id=c.id
            where s.id=love_space_id and c.status='ended')))));
create policy love_photos_owner_delete on public.love_space_photos for delete to authenticated
using (uploader_id=auth.uid());
-- Metadata inserts are register_love_photo RPC-only.

create policy deletion_owner_read on public.account_deletion_requests for select to authenticated
using (user_id=auth.uid());

-- Private Storage buckets are idempotently enforced by migration.
insert into storage.buckets(id,name,public,file_size_limit,allowed_mime_types)
values
 ('profile-photos','profile-photos',false,5242880,array['image/webp','image/jpeg','image/png']),
 ('love-space-photos','love-space-photos',false,5242880,array['image/webp','image/jpeg','image/png'])
on conflict(id) do update set public=false,file_size_limit=excluded.file_size_limit,
  allowed_mime_types=excluded.allowed_mime_types;

-- Private Storage policies.
create policy profile_storage_authenticated_read on storage.objects for select to authenticated
using (bucket_id='profile-photos');
create policy profile_storage_owner_insert on storage.objects for insert to authenticated
with check (bucket_id='profile-photos' and (storage.foldername(name))[1]=auth.uid()::text);
create policy profile_storage_owner_update on storage.objects for update to authenticated
using (bucket_id='profile-photos' and owner_id=auth.uid()::text)
with check (bucket_id='profile-photos' and owner_id=auth.uid()::text);
create policy profile_storage_owner_delete on storage.objects for delete to authenticated
using (bucket_id='profile-photos' and owner_id=auth.uid()::text);

create policy love_storage_member_read on storage.objects for select to authenticated
using (bucket_id='love-space-photos' and (
  ((storage.foldername(name))[1]='private' and (storage.foldername(name))[2]=auth.uid()::text)
  or public.can_read_love_space(public.safe_uuid((storage.foldername(name))[1]))
));
create policy love_storage_member_insert on storage.objects for insert to authenticated
with check (bucket_id='love-space-photos' and (storage.foldername(name))[2]=auth.uid()::text and (
  ((storage.foldername(name))[1]='private')
  or public.can_write_love_space(public.safe_uuid((storage.foldername(name))[1]))
));
create policy love_storage_owner_delete on storage.objects for delete to authenticated
using (bucket_id='love-space-photos' and owner_id=auth.uid()::text);

-- Explicit API grants. Security-definer mutation RPCs are not callable by anon/public.
revoke execute on function public.send_friend_request(text) from public,anon;
revoke execute on function public.respond_friend_request(uuid,boolean) from public,anon;
revoke execute on function public.remove_friendship(uuid) from public,anon;
revoke execute on function public.send_couple_request(uuid) from public,anon;
revoke execute on function public.respond_couple_request(uuid,boolean) from public,anon;
revoke execute on function public.cancel_couple_request(uuid) from public,anon;
revoke execute on function public.end_couple_relationship(uuid) from public,anon;
revoke execute on function public.register_love_photo(uuid,uuid,text,text,text,integer,integer,bigint,text,date) from public,anon;
revoke execute on function public.request_account_deletion() from public,anon;
revoke execute on function public.cancel_account_deletion() from public,anon;

grant select,update on public.profiles to authenticated;
grant select on public.friendships,public.couple_relationships,public.love_spaces,
  public.love_space_members,public.love_space_photos,public.account_deletion_requests to authenticated;
grant execute on function public.send_friend_request(text) to authenticated;
grant execute on function public.respond_friend_request(uuid,boolean) to authenticated;
grant execute on function public.remove_friendship(uuid) to authenticated;
grant execute on function public.send_couple_request(uuid) to authenticated;
grant execute on function public.respond_couple_request(uuid,boolean) to authenticated;
grant execute on function public.cancel_couple_request(uuid) to authenticated;
grant execute on function public.end_couple_relationship(uuid) to authenticated;
grant execute on function public.register_love_photo(uuid,uuid,text,text,text,integer,integer,bigint,text,date) to authenticated;
grant execute on function public.request_account_deletion() to authenticated;
grant execute on function public.cancel_account_deletion() to authenticated;

-- Realtime for request state and gallery metadata.
do $$ begin
  alter publication supabase_realtime add table public.friendships;
exception when duplicate_object then null; end $$;
do $$ begin
  alter publication supabase_realtime add table public.couple_relationships;
exception when duplicate_object then null; end $$;
do $$ begin
  alter publication supabase_realtime add table public.love_space_photos;
exception when duplicate_object then null; end $$;
