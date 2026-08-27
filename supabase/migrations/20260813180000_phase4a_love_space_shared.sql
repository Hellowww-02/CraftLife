-- CraftLife Cloud Phase 4A: cloud-native shared Love Space data.
-- All writes are RPC-only and require an active accepted couple. During the
-- 30-day relationship grace period these rows remain readable but read-only.

create table if not exists public.love_space_shared_profiles (
  love_space_id uuid primary key references public.love_spaces(id) on delete cascade,
  partner_name text not null default '' check(char_length(partner_name)<=120),
  partner_gender text not null default 'female' check(partner_gender in('male','female','other')),
  partner_age integer not null default 25 check(partner_age between 15 and 120),
  relationship_type text not null default 'dating'
    check(relationship_type in('dating','engaged','married','long_distance')),
  start_date date,
  updated_by uuid not null references public.profiles(id) on delete restrict,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create trigger love_shared_profile_updated before update on public.love_space_shared_profiles
for each row execute function public.set_updated_at();

create table if not exists public.love_space_events (
  id uuid primary key default gen_random_uuid(),
  love_space_id uuid not null references public.love_spaces(id) on delete cascade,
  created_by uuid not null references public.profiles(id) on delete restrict,
  title text not null check(char_length(trim(title)) between 1 and 160),
  event_date date not null,
  category text not null default 'date' check(char_length(category)<=60),
  notes text not null default '' check(char_length(notes)<=4000),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists love_events_space_date on public.love_space_events(love_space_id,event_date,id);
create trigger love_events_updated before update on public.love_space_events
for each row execute function public.set_updated_at();

create table if not exists public.love_space_memories (
  id uuid primary key default gen_random_uuid(),
  love_space_id uuid not null references public.love_spaces(id) on delete cascade,
  created_by uuid not null references public.profiles(id) on delete restrict,
  title text not null check(char_length(trim(title)) between 1 and 160),
  memory_date date not null,
  notes text not null default '' check(char_length(notes)<=4000),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists love_memories_space_date on public.love_space_memories(love_space_id,memory_date desc,id);
create trigger love_memories_updated before update on public.love_space_memories
for each row execute function public.set_updated_at();

create table if not exists public.love_space_checkins (
  id uuid primary key default gen_random_uuid(),
  love_space_id uuid not null references public.love_spaces(id) on delete cascade,
  created_by uuid not null references public.profiles(id) on delete restrict,
  checkin_date date not null,
  my_mood integer not null default 3 check(my_mood between 1 and 5),
  partner_mood integer not null default 3 check(partner_mood between 1 and 5),
  connection_score integer not null default 3 check(connection_score between 1 and 5),
  note text not null default '' check(char_length(note)<=2000),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(love_space_id,created_by,checkin_date)
);
create index if not exists love_checkins_space_date on public.love_space_checkins(love_space_id,checkin_date desc);
create trigger love_checkins_updated before update on public.love_space_checkins
for each row execute function public.set_updated_at();

create table if not exists public.love_space_prompt_responses (
  id uuid primary key default gen_random_uuid(),
  love_space_id uuid not null references public.love_spaces(id) on delete cascade,
  created_by uuid not null references public.profiles(id) on delete restrict,
  prompt_key text not null check(char_length(prompt_key) between 1 and 120),
  category text not null default 'connection' check(char_length(category)<=60),
  prompt_text text not null check(char_length(prompt_text) between 1 and 1000),
  my_answer text not null default '' check(char_length(my_answer)<=4000),
  partner_answer text not null default '' check(char_length(partner_answer)<=4000),
  response_date date not null default current_date,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists love_prompts_space_date on public.love_space_prompt_responses(love_space_id,response_date desc,id);
create trigger love_prompts_updated before update on public.love_space_prompt_responses
for each row execute function public.set_updated_at();

create table if not exists public.love_space_prompt_favorites (
  id uuid primary key default gen_random_uuid(),
  love_space_id uuid not null references public.love_spaces(id) on delete cascade,
  created_by uuid not null references public.profiles(id) on delete cascade,
  prompt_key text not null check(char_length(prompt_key) between 1 and 120),
  created_at timestamptz not null default now(),
  unique(love_space_id,created_by,prompt_key)
);

create table if not exists public.love_space_weekly_reviews (
  id uuid primary key default gen_random_uuid(),
  love_space_id uuid not null references public.love_spaces(id) on delete cascade,
  created_by uuid not null references public.profiles(id) on delete restrict,
  week_start date not null,
  appreciation text not null default '' check(char_length(appreciation)<=4000),
  wins text not null default '' check(char_length(wins)<=4000),
  support_needed text not null default '' check(char_length(support_needed)<=4000),
  shared_intention text not null default '' check(char_length(shared_intention)<=4000),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(love_space_id,created_by,week_start)
);
create index if not exists love_reviews_space_week on public.love_space_weekly_reviews(love_space_id,week_start desc);
create trigger love_reviews_updated before update on public.love_space_weekly_reviews
for each row execute function public.set_updated_at();

create table if not exists public.love_space_bucket_items (
  id uuid primary key default gen_random_uuid(),
  love_space_id uuid not null references public.love_spaces(id) on delete cascade,
  created_by uuid not null references public.profiles(id) on delete restrict,
  title text not null check(char_length(trim(title)) between 1 and 200),
  category text not null default 'dream' check(char_length(category)<=60),
  target_date date,
  is_done boolean not null default false,
  completed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists love_bucket_space_state on public.love_space_bucket_items(love_space_id,is_done,target_date,id);
create trigger love_bucket_updated before update on public.love_space_bucket_items
for each row execute function public.set_updated_at();

create table if not exists public.love_space_cycle_settings (
  love_space_id uuid primary key references public.love_spaces(id) on delete cascade,
  tracked_person text not null default 'partner' check(tracked_person in('self','partner')),
  last_period_start date,
  cycle_length integer not null default 28 check(cycle_length between 20 and 45),
  period_length integer not null default 5 check(period_length between 2 and 10),
  updated_by uuid not null references public.profiles(id) on delete restrict,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create trigger love_cycle_settings_updated before update on public.love_space_cycle_settings
for each row execute function public.set_updated_at();

create table if not exists public.love_space_cycles (
  id uuid primary key default gen_random_uuid(),
  love_space_id uuid not null references public.love_spaces(id) on delete cascade,
  created_by uuid not null references public.profiles(id) on delete restrict,
  start_date date not null,
  end_date date,
  notes text not null default '' check(char_length(notes)<=2000),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check(end_date is null or end_date>=start_date)
);
create index if not exists love_cycles_space_start on public.love_space_cycles(love_space_id,start_date desc,id);
create trigger love_cycles_updated before update on public.love_space_cycles
for each row execute function public.set_updated_at();

-- Shared profile/settings have one canonical row per Love Space.
create or replace function public.save_love_space_shared_profile(
  p_love_space_id uuid,p_partner_name text,p_partner_gender text,p_partner_age integer,
  p_relationship_type text,p_start_date date
)
returns jsonb language plpgsql security definer set search_path=public as $$
declare result jsonb;
begin
  if not public.can_write_love_space(p_love_space_id) then raise exception 'love_space_write_forbidden'; end if;
  if char_length(trim(coalesce(p_partner_name,'')))<1 then raise exception 'partner_name_required'; end if;
  insert into public.love_space_shared_profiles as p(
    love_space_id,partner_name,partner_gender,partner_age,relationship_type,start_date,updated_by
  ) values(
    p_love_space_id,left(trim(p_partner_name),120),p_partner_gender,p_partner_age,p_relationship_type,p_start_date,auth.uid()
  ) on conflict(love_space_id) do update set
    partner_name=excluded.partner_name,partner_gender=excluded.partner_gender,
    partner_age=excluded.partner_age,relationship_type=excluded.relationship_type,
    start_date=excluded.start_date,updated_by=auth.uid()
  returning to_jsonb(p) into result;
  return result;
end; $$;

create or replace function public.save_love_space_cycle_settings(
  p_love_space_id uuid,p_tracked_person text,p_last_period_start date,
  p_cycle_length integer,p_period_length integer
)
returns jsonb language plpgsql security definer set search_path=public as $$
declare result jsonb;
begin
  if not public.can_write_love_space(p_love_space_id) then raise exception 'love_space_write_forbidden'; end if;
  insert into public.love_space_cycle_settings as s(
    love_space_id,tracked_person,last_period_start,cycle_length,period_length,updated_by
  ) values(
    p_love_space_id,p_tracked_person,p_last_period_start,p_cycle_length,p_period_length,auth.uid()
  ) on conflict(love_space_id) do update set
    tracked_person=excluded.tracked_person,last_period_start=excluded.last_period_start,
    cycle_length=excluded.cycle_length,period_length=excluded.period_length,updated_by=auth.uid()
  returning to_jsonb(s) into result;
  return result;
end; $$;

-- One validated RPC handles the repeated shared record shape while keeping all
-- underlying tables typed, constrained, and independently protected by RLS.
create or replace function public.upsert_love_space_record(
  p_love_space_id uuid,p_record_type text,p_record_id uuid,p_payload jsonb
)
returns jsonb language plpgsql security definer set search_path=public as $$
declare result jsonb;
begin
  if not public.can_write_love_space(p_love_space_id) then raise exception 'love_space_write_forbidden'; end if;
  if p_record_id is null then raise exception 'record_id_required'; end if;
  if p_payload is null or jsonb_typeof(p_payload)<>'object' then raise exception 'invalid_payload'; end if;
  if octet_length(p_payload::text)>32768 then raise exception 'payload_too_large'; end if;

  case p_record_type
    when 'event' then
      insert into public.love_space_events as e(id,love_space_id,created_by,title,event_date,category,notes)
      values(p_record_id,p_love_space_id,auth.uid(),left(trim(p_payload->>'title'),160),
             (p_payload->>'event_date')::date,left(coalesce(p_payload->>'category','date'),60),
             left(coalesce(p_payload->>'notes',''),4000))
      on conflict(id) do update set title=excluded.title,event_date=excluded.event_date,
        category=excluded.category,notes=excluded.notes
      where e.love_space_id=p_love_space_id returning to_jsonb(e) into result;
    when 'memory' then
      insert into public.love_space_memories as m(id,love_space_id,created_by,title,memory_date,notes)
      values(p_record_id,p_love_space_id,auth.uid(),left(trim(p_payload->>'title'),160),
             (p_payload->>'memory_date')::date,left(coalesce(p_payload->>'notes',''),4000))
      on conflict(id) do update set title=excluded.title,memory_date=excluded.memory_date,notes=excluded.notes
      where m.love_space_id=p_love_space_id returning to_jsonb(m) into result;
    when 'checkin' then
      insert into public.love_space_checkins as c(
        id,love_space_id,created_by,checkin_date,my_mood,partner_mood,connection_score,note
      ) values(
        p_record_id,p_love_space_id,auth.uid(),(p_payload->>'checkin_date')::date,
        (p_payload->>'my_mood')::integer,(p_payload->>'partner_mood')::integer,
        (p_payload->>'connection_score')::integer,left(coalesce(p_payload->>'note',''),2000)
      ) on conflict(love_space_id,created_by,checkin_date) do update set
        my_mood=excluded.my_mood,partner_mood=excluded.partner_mood,
        connection_score=excluded.connection_score,note=excluded.note
      returning to_jsonb(c) into result;
    when 'prompt_response' then
      insert into public.love_space_prompt_responses as r(
        id,love_space_id,created_by,prompt_key,category,prompt_text,my_answer,partner_answer,response_date
      ) values(
        p_record_id,p_love_space_id,auth.uid(),left(p_payload->>'prompt_key',120),
        left(coalesce(p_payload->>'category','connection'),60),left(p_payload->>'prompt_text',1000),
        left(coalesce(p_payload->>'my_answer',''),4000),left(coalesce(p_payload->>'partner_answer',''),4000),
        coalesce(nullif(p_payload->>'response_date','')::date,current_date)
      ) on conflict(id) do update set prompt_key=excluded.prompt_key,category=excluded.category,
        prompt_text=excluded.prompt_text,my_answer=excluded.my_answer,
        partner_answer=excluded.partner_answer,response_date=excluded.response_date
      where r.love_space_id=p_love_space_id returning to_jsonb(r) into result;
    when 'weekly_review' then
      insert into public.love_space_weekly_reviews as w(
        id,love_space_id,created_by,week_start,appreciation,wins,support_needed,shared_intention
      ) values(
        p_record_id,p_love_space_id,auth.uid(),(p_payload->>'week_start')::date,
        left(coalesce(p_payload->>'appreciation',''),4000),left(coalesce(p_payload->>'wins',''),4000),
        left(coalesce(p_payload->>'support_needed',''),4000),left(coalesce(p_payload->>'shared_intention',''),4000)
      ) on conflict(love_space_id,created_by,week_start) do update set
        appreciation=excluded.appreciation,wins=excluded.wins,support_needed=excluded.support_needed,
        shared_intention=excluded.shared_intention returning to_jsonb(w) into result;
    when 'bucket_item' then
      insert into public.love_space_bucket_items as b(
        id,love_space_id,created_by,title,category,target_date,is_done,completed_at
      ) values(
        p_record_id,p_love_space_id,auth.uid(),left(trim(p_payload->>'title'),200),
        left(coalesce(p_payload->>'category','dream'),60),nullif(p_payload->>'target_date','')::date,
        coalesce((p_payload->>'is_done')::boolean,false),
        case when coalesce((p_payload->>'is_done')::boolean,false) then now() else null end
      ) on conflict(id) do update set title=excluded.title,category=excluded.category,
        target_date=excluded.target_date,is_done=excluded.is_done,
        completed_at=case when excluded.is_done then coalesce(b.completed_at,now()) else null end
      where b.love_space_id=p_love_space_id returning to_jsonb(b) into result;
    when 'cycle' then
      insert into public.love_space_cycles as y(id,love_space_id,created_by,start_date,end_date,notes)
      values(p_record_id,p_love_space_id,auth.uid(),(p_payload->>'start_date')::date,
             nullif(p_payload->>'end_date','')::date,left(coalesce(p_payload->>'notes',''),2000))
      on conflict(id) do update set start_date=excluded.start_date,end_date=excluded.end_date,notes=excluded.notes
      where y.love_space_id=p_love_space_id returning to_jsonb(y) into result;
    else raise exception 'unsupported_love_record_type';
  end case;
  if result is null then raise exception 'love_record_conflict'; end if;
  return jsonb_build_object('record_type',p_record_type,'row',result);
end; $$;

create or replace function public.delete_love_space_record(
  p_love_space_id uuid,p_record_type text,p_record_id uuid
)
returns boolean language plpgsql security definer set search_path=public as $$
begin
  if not public.can_write_love_space(p_love_space_id) then raise exception 'love_space_write_forbidden'; end if;
  case p_record_type
    when 'event' then delete from public.love_space_events where id=p_record_id and love_space_id=p_love_space_id;
    when 'memory' then delete from public.love_space_memories where id=p_record_id and love_space_id=p_love_space_id;
    when 'prompt_response' then delete from public.love_space_prompt_responses where id=p_record_id and love_space_id=p_love_space_id;
    when 'weekly_review' then delete from public.love_space_weekly_reviews where id=p_record_id and love_space_id=p_love_space_id;
    when 'bucket_item' then delete from public.love_space_bucket_items where id=p_record_id and love_space_id=p_love_space_id;
    when 'cycle' then delete from public.love_space_cycles where id=p_record_id and love_space_id=p_love_space_id;
    else raise exception 'unsupported_love_record_type';
  end case;
  return found;
end; $$;

create or replace function public.toggle_love_space_bucket_item(
  p_love_space_id uuid,p_record_id uuid,p_is_done boolean
)
returns jsonb language plpgsql security definer set search_path=public as $$
declare result jsonb;
begin
  if not public.can_write_love_space(p_love_space_id) then raise exception 'love_space_write_forbidden'; end if;
  update public.love_space_bucket_items as b set is_done=p_is_done,
    completed_at=case when p_is_done then coalesce(completed_at,now()) else null end
  where id=p_record_id and love_space_id=p_love_space_id returning to_jsonb(b) into result;
  if result is null then raise exception 'love_record_not_found'; end if;
  return result;
end; $$;

create or replace function public.set_love_space_prompt_favorite(
  p_love_space_id uuid,p_prompt_key text,p_favorite boolean
)
returns jsonb language plpgsql security definer set search_path=public as $$
declare result jsonb;
begin
  if not public.can_write_love_space(p_love_space_id) then raise exception 'love_space_write_forbidden'; end if;
  if p_favorite then
    insert into public.love_space_prompt_favorites as f(love_space_id,created_by,prompt_key)
    values(p_love_space_id,auth.uid(),left(p_prompt_key,120))
    on conflict(love_space_id,created_by,prompt_key) do update set prompt_key=excluded.prompt_key
    returning to_jsonb(f) into result;
    return jsonb_build_object('favorite',true,'row',result);
  end if;
  delete from public.love_space_prompt_favorites
  where love_space_id=p_love_space_id and created_by=auth.uid() and prompt_key=p_prompt_key;
  return jsonb_build_object('favorite',false,'prompt_key',p_prompt_key);
end; $$;

create or replace function public.toggle_love_space_prompt_favorite(
  p_love_space_id uuid,p_prompt_key text
)
returns jsonb language plpgsql security definer set search_path=public as $$
declare
  existing_id uuid;
  result jsonb;
begin
  if not public.can_write_love_space(p_love_space_id) then raise exception 'love_space_write_forbidden'; end if;
  select id into existing_id from public.love_space_prompt_favorites
  where love_space_id=p_love_space_id and created_by=auth.uid() and prompt_key=p_prompt_key for update;
  if existing_id is not null then
    delete from public.love_space_prompt_favorites where id=existing_id;
    return jsonb_build_object('favorite',false,'prompt_key',p_prompt_key,'id',existing_id);
  end if;
  insert into public.love_space_prompt_favorites as f(love_space_id,created_by,prompt_key)
  values(p_love_space_id,auth.uid(),left(p_prompt_key,120)) returning to_jsonb(f) into result;
  return jsonb_build_object('favorite',true,'row',result);
end; $$;

-- RLS owner/member reads. There are no direct client writes.
alter table public.love_space_shared_profiles enable row level security;
alter table public.love_space_events enable row level security;
alter table public.love_space_memories enable row level security;
alter table public.love_space_checkins enable row level security;
alter table public.love_space_prompt_responses enable row level security;
alter table public.love_space_prompt_favorites enable row level security;
alter table public.love_space_weekly_reviews enable row level security;
alter table public.love_space_bucket_items enable row level security;
alter table public.love_space_cycle_settings enable row level security;
alter table public.love_space_cycles enable row level security;

create policy love_shared_profiles_member_read on public.love_space_shared_profiles for select to authenticated
using(public.can_read_love_space(love_space_id));
create policy love_events_member_read on public.love_space_events for select to authenticated
using(public.can_read_love_space(love_space_id));
create policy love_memories_member_read on public.love_space_memories for select to authenticated
using(public.can_read_love_space(love_space_id));
create policy love_checkins_member_read on public.love_space_checkins for select to authenticated
using(public.can_read_love_space(love_space_id));
create policy love_prompt_responses_member_read on public.love_space_prompt_responses for select to authenticated
using(public.can_read_love_space(love_space_id));
create policy love_prompt_favorites_member_read on public.love_space_prompt_favorites for select to authenticated
using(public.can_read_love_space(love_space_id));
create policy love_weekly_reviews_member_read on public.love_space_weekly_reviews for select to authenticated
using(public.can_read_love_space(love_space_id));
create policy love_bucket_member_read on public.love_space_bucket_items for select to authenticated
using(public.can_read_love_space(love_space_id));
create policy love_cycle_settings_member_read on public.love_space_cycle_settings for select to authenticated
using(public.can_read_love_space(love_space_id));
create policy love_cycles_member_read on public.love_space_cycles for select to authenticated
using(public.can_read_love_space(love_space_id));

revoke all on public.love_space_shared_profiles,public.love_space_events,public.love_space_memories,
  public.love_space_checkins,public.love_space_prompt_responses,public.love_space_prompt_favorites,
  public.love_space_weekly_reviews,public.love_space_bucket_items,public.love_space_cycle_settings,
  public.love_space_cycles from anon;
revoke insert,update,delete on public.love_space_shared_profiles,public.love_space_events,public.love_space_memories,
  public.love_space_checkins,public.love_space_prompt_responses,public.love_space_prompt_favorites,
  public.love_space_weekly_reviews,public.love_space_bucket_items,public.love_space_cycle_settings,
  public.love_space_cycles from authenticated;
grant select on public.love_space_shared_profiles,public.love_space_events,public.love_space_memories,
  public.love_space_checkins,public.love_space_prompt_responses,public.love_space_prompt_favorites,
  public.love_space_weekly_reviews,public.love_space_bucket_items,public.love_space_cycle_settings,
  public.love_space_cycles to authenticated;

revoke execute on function public.save_love_space_shared_profile(uuid,text,text,integer,text,date) from public,anon;
revoke execute on function public.save_love_space_cycle_settings(uuid,text,date,integer,integer) from public,anon;
revoke execute on function public.upsert_love_space_record(uuid,text,uuid,jsonb) from public,anon;
revoke execute on function public.delete_love_space_record(uuid,text,uuid) from public,anon;
revoke execute on function public.toggle_love_space_bucket_item(uuid,uuid,boolean) from public,anon;
revoke execute on function public.set_love_space_prompt_favorite(uuid,text,boolean) from public,anon;
revoke execute on function public.toggle_love_space_prompt_favorite(uuid,text) from public,anon;
grant execute on function public.save_love_space_shared_profile(uuid,text,text,integer,text,date) to authenticated;
grant execute on function public.save_love_space_cycle_settings(uuid,text,date,integer,integer) to authenticated;
grant execute on function public.upsert_love_space_record(uuid,text,uuid,jsonb) to authenticated;
grant execute on function public.delete_love_space_record(uuid,text,uuid) to authenticated;
grant execute on function public.toggle_love_space_bucket_item(uuid,uuid,boolean) to authenticated;
grant execute on function public.set_love_space_prompt_favorite(uuid,text,boolean) to authenticated;
grant execute on function public.toggle_love_space_prompt_favorite(uuid,text) to authenticated;

-- Each shared table is independently subscribed so partner devices update without polling.
do $$ begin alter publication supabase_realtime add table public.love_space_shared_profiles; exception when duplicate_object then null; end $$;
do $$ begin alter publication supabase_realtime add table public.love_space_events; exception when duplicate_object then null; end $$;
do $$ begin alter publication supabase_realtime add table public.love_space_memories; exception when duplicate_object then null; end $$;
do $$ begin alter publication supabase_realtime add table public.love_space_checkins; exception when duplicate_object then null; end $$;
do $$ begin alter publication supabase_realtime add table public.love_space_prompt_responses; exception when duplicate_object then null; end $$;
do $$ begin alter publication supabase_realtime add table public.love_space_prompt_favorites; exception when duplicate_object then null; end $$;
do $$ begin alter publication supabase_realtime add table public.love_space_weekly_reviews; exception when duplicate_object then null; end $$;
do $$ begin alter publication supabase_realtime add table public.love_space_bucket_items; exception when duplicate_object then null; end $$;
do $$ begin alter publication supabase_realtime add table public.love_space_cycle_settings; exception when duplicate_object then null; end $$;
do $$ begin alter publication supabase_realtime add table public.love_space_cycles; exception when duplicate_object then null; end $$;

notify pgrst,'reload schema';
