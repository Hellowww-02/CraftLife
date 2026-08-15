-- CraftLife Phase 4D-4E finalization: notification center, device manager,
-- chat rate hardening and retirement of legacy bypass RPCs.

create table if not exists public.notification_preferences(
  user_id uuid primary key references public.profiles(id) on delete cascade,
  direct_message boolean not null default true,
  social_requests boolean not null default true,
  love_space boolean not null default true,
  pvp boolean not null default true,
  guild boolean not null default true,
  security boolean not null default true,
  updated_at timestamptz not null default now()
);
create trigger notification_preferences_updated before update on public.notification_preferences
for each row execute function public.set_updated_at();

create or replace function public.get_social_notifications_page(
  p_limit integer default 50,p_before timestamptz default null,p_type text default null
)
returns setof public.social_notifications language sql stable security definer set search_path=public as $$
  select n.* from public.social_notifications n
  where n.user_id=auth.uid() and (p_before is null or n.created_at<p_before)
    and (p_type is null or p_type='' or n.notification_type=p_type or n.entity_type=p_type)
  order by n.created_at desc,n.id desc limit greatest(1,least(100,p_limit))
$$;

create or replace function public.mark_social_notification_read(p_notification_id uuid)
returns boolean language plpgsql security definer set search_path=public as $$
begin
 update public.social_notifications set is_read=true where id=p_notification_id and user_id=auth.uid();return found;
end; $$;

create or replace function public.set_notification_preferences(p_values jsonb)
returns public.notification_preferences language plpgsql security definer set search_path=public as $$
declare result public.notification_preferences;
begin
 insert into public.notification_preferences(user_id,direct_message,social_requests,love_space,pvp,guild,security)
 values(auth.uid(),coalesce((p_values->>'direct_message')::boolean,true),
   coalesce((p_values->>'social_requests')::boolean,true),coalesce((p_values->>'love_space')::boolean,true),
   coalesce((p_values->>'pvp')::boolean,true),coalesce((p_values->>'guild')::boolean,true),
   coalesce((p_values->>'security')::boolean,true))
 on conflict(user_id) do update set direct_message=excluded.direct_message,
   social_requests=excluded.social_requests,love_space=excluded.love_space,pvp=excluded.pvp,
   guild=excluded.guild,security=excluded.security returning * into result;
 return result;
end; $$;

create or replace function public.rename_cloud_device(p_device_id uuid,p_device_name text)
returns public.cloud_devices language plpgsql security definer set search_path=public as $$
declare result public.cloud_devices;
begin
 if char_length(trim(coalesce(p_device_name,'')))<1 then raise exception 'device_name_required'; end if;
 update public.cloud_devices set device_name=left(trim(p_device_name),120)
 where id=p_device_id and user_id=auth.uid() and revoked_at is null returning * into result;
 if result.id is null then raise exception 'device_not_found'; end if;return result;
end; $$;

create or replace function public.revoke_other_cloud_devices(p_current_device_id uuid)
returns integer language plpgsql security definer set search_path=public as $$
declare changed integer;
begin
 if not exists(select 1 from public.cloud_devices where id=p_current_device_id and user_id=auth.uid() and revoked_at is null) then raise exception 'current_device_invalid'; end if;
 update public.cloud_devices set revoked_at=coalesce(revoked_at,now())
 where user_id=auth.uid() and id<>p_current_device_id and revoked_at is null;
 get diagnostics changed=row_count;return changed;
end; $$;

create or replace function public.notify_cloud_device_security_event()
returns trigger language plpgsql security definer set search_path=public as $$
begin
 if tg_op='INSERT' then
   insert into public.social_notifications(user_id,notification_type,entity_type,entity_id,payload)
   values(new.user_id,'new_device','device',new.id,jsonb_build_object('device_name',new.device_name,'platform',new.platform));
 elsif old.revoked_at is null and new.revoked_at is not null then
   insert into public.social_notifications(user_id,notification_type,entity_type,entity_id,payload)
   values(new.user_id,'device_revoked','device',new.id,jsonb_build_object('device_name',new.device_name));
 end if;return new;
end; $$;
drop trigger if exists cloud_device_security_notification on public.cloud_devices;
create trigger cloud_device_security_notification after insert or update of revoked_at on public.cloud_devices
for each row execute function public.notify_cloud_device_security_event();

-- Rate-limited direct send. Phase 2 legacy RPC is revoked below.
create or replace function public.send_direct_message_v2(
  p_conversation_id uuid,p_body text,p_client_message_id uuid,p_reply_to_id uuid default null
)
returns public.messages language plpgsql security definer set search_path=public as $$
declare result public.messages;
begin
 if not public.current_profile_active() or not public.is_conversation_member(p_conversation_id) then raise exception 'forbidden'; end if;
 if char_length(trim(coalesce(p_body,'')))<1 then raise exception 'message_empty'; end if;
 if (select count(*) from public.messages where sender_id=auth.uid() and created_at>now()-interval '1 minute')>=30 then raise exception 'message_rate_limit'; end if;
 if p_reply_to_id is not null and not exists(select 1 from public.messages where id=p_reply_to_id and conversation_id=p_conversation_id) then raise exception 'invalid_reply_target'; end if;
 insert into public.messages as existing(conversation_id,sender_id,body,client_message_id,reply_to_id)
 values(p_conversation_id,auth.uid(),left(trim(p_body),4000),p_client_message_id,p_reply_to_id)
 on conflict(sender_id,client_message_id) do update set body=existing.body returning * into result;
 update public.conversations set updated_at=now() where id=p_conversation_id;return result;
end; $$;

create or replace function public.send_online_guild_message_v2(
  p_guild_id uuid,p_body text,p_client_message_id uuid,p_reply_to_id uuid default null
)
returns public.online_guild_messages language plpgsql security definer set search_path=public as $$
declare result public.online_guild_messages;
begin
 if not public.is_online_guild_member(p_guild_id) or char_length(trim(coalesce(p_body,'')))<1 then raise exception 'forbidden'; end if;
 if (select count(*) from public.online_guild_messages where sender_id=auth.uid() and created_at>now()-interval '1 minute')>=30 then raise exception 'message_rate_limit'; end if;
 if p_reply_to_id is not null and not exists(select 1 from public.online_guild_messages where id=p_reply_to_id and guild_id=p_guild_id) then raise exception 'invalid_reply_target'; end if;
 insert into public.online_guild_messages as existing(guild_id,sender_id,body,client_message_id,reply_to_id)
 values(p_guild_id,auth.uid(),left(trim(p_body),4000),p_client_message_id,p_reply_to_id)
 on conflict(sender_id,client_message_id) do update set body=existing.body returning * into result;return result;
end; $$;

alter table public.notification_preferences enable row level security;
create policy notification_preferences_owner_read on public.notification_preferences for select to authenticated using(user_id=auth.uid());
revoke all on public.notification_preferences from anon;
revoke insert,update,delete on public.notification_preferences from authenticated;
grant select on public.notification_preferences to authenticated;

revoke execute on function public.get_social_notifications_page(integer,timestamptz,text) from public,anon;
revoke execute on function public.mark_social_notification_read(uuid) from public,anon;
revoke execute on function public.set_notification_preferences(jsonb) from public,anon;
revoke execute on function public.rename_cloud_device(uuid,text) from public,anon;
revoke execute on function public.revoke_other_cloud_devices(uuid) from public,anon;
grant execute on function public.get_social_notifications_page(integer,timestamptz,text),
 public.mark_social_notification_read(uuid),public.set_notification_preferences(jsonb),
 public.rename_cloud_device(uuid,text),public.revoke_other_cloud_devices(uuid) to authenticated;

-- Final Phase 4 clients use the validated v2 RPCs only.
revoke execute on function public.send_direct_message(uuid,text,uuid) from authenticated;
revoke execute on function public.send_online_guild_message(uuid,text,uuid) from authenticated;

notify pgrst,'reload schema';
