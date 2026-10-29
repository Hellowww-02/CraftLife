-- ---------------------------------------------------------------------------
-- Patch M04b: terbitkan ulang public.upsert_entities dengan badan finalnya.
--
-- MENGAPA MIGRASI INI ADA
-- Migrasi 20261008000000_phase_m04b_entity_channel_b.sql pernah diedit DI
-- TEMPAT (commit b682bf6) setelah pertama kali dibuat. Edit itu menambah dua
-- hal pada nilai balik upsert_entities:
--
--   'rows'      -> [{uuid, rev}] untuk setiap baris yang dikirim
--   'unchanged' -> jumlah replay identik yang tidak menggantikan apa pun
--
-- Supabase mencatat migrasi yang sudah diterapkan berdasarkan VERSI TIMESTAMP
-- SAJA, bukan checksum. Artinya instance yang menerapkan migrasi M04b sebelum
-- edit itu tidak akan pernah menjalankannya ulang: fungsinya tetap versi lama,
-- dan tidak ada error apa pun yang menandainya.
--
-- Akibatnya nyata, bukan kosmetik. Klien butuh 'rows' untuk mencatat base_rev.
-- Tanpa itu sync_entity_state tidak pernah maju, setiap push berikutnya tetap
-- mengklaim base_rev 0, dan 3-way merge terdegradasi diam-diam menjadi
-- 2-way last-writer-wins - persis bug yang diperbaiki b682bf6, hidup kembali
-- di produksi.
--
-- MIGRASI INI AMAN DI KEDUA KONDISI. CREATE OR REPLACE bersifat idempoten:
-- pada instance yang sudah punya badan final, ini tidak mengubah apa pun; pada
-- instance yang masih punya badan lama, ini memperbaikinya. Daftar argumen dan
-- tipe balik tidak berubah, jadi CREATE OR REPLACE diizinkan, dan GRANT yang
-- sudah ada tetap melekat.
--
-- Tidak ada perubahan tabel, kolom, policy, atau grant.
-- ---------------------------------------------------------------------------

create or replace function public.upsert_entities(
  p_table_name text,
  p_rows jsonb,
  p_device_id uuid,
  p_client_updated_at timestamptz default now()
)
returns jsonb
language plpgsql security definer set search_path=public as $$
declare
  v_row jsonb;
  v_uuid uuid;
  v_payload jsonb;
  v_base_rev bigint;
  v_row_time timestamptz;
  v_deleted timestamptz;
  v_client_time timestamptz;
  v_current public.sync_entities;
  v_base jsonb;
  v_key text;
  v_merged jsonb;
  v_ours_value jsonb;
  v_theirs_value jsonb;
  v_base_value jsonb;
  v_inserted integer := 0;
  v_updated integer := 0;
  v_conflicted integer := 0;
  v_deleted_count integer := 0;
  v_unchanged integer := 0;
  v_rows jsonb := '[]'::jsonb;
begin
  if auth.uid() is null or not public.current_profile_active() then
    raise exception 'account_unavailable';
  end if;
  perform public.assert_mutable_entity_table(p_table_name);
  if p_rows is null or jsonb_typeof(p_rows) <> 'array' then
    raise exception 'invalid_rows';
  end if;
  if jsonb_array_length(p_rows) > 5000 then
    raise exception 'too_many_rows';
  end if;
  if octet_length(p_rows::text) > 8388608 then
    raise exception 'payload_too_large';
  end if;
  if not exists(
    select 1 from public.cloud_devices
    where id = p_device_id and user_id = auth.uid() and revoked_at is null
  ) then
    raise exception 'device_not_registered';
  end if;

  v_client_time := least(coalesce(p_client_updated_at, now()), now() + interval '5 minutes');

  for v_row in select * from jsonb_array_elements(p_rows)
  loop
    if jsonb_typeof(v_row) <> 'object' then
      raise exception 'invalid_row';
    end if;
    begin
      v_uuid := (v_row ->> 'uuid')::uuid;
    exception when others then
      raise exception 'invalid_entity_uuid';
    end;

    v_payload := coalesce(v_row -> 'payload', v_row) - 'uuid' - 'payload';
    v_base_rev := coalesce((v_row ->> 'base_rev')::bigint, 0);
    v_row_time := coalesce((v_row ->> 'updated_at')::timestamptz, v_client_time);
    v_deleted := (v_row ->> 'deleted_at')::timestamptz;

    select * into v_current from public.sync_entities
      where user_id = auth.uid() and table_name = p_table_name and entity_uuid = v_uuid
      for update;

    if v_current.user_id is null then
      insert into public.sync_entities(
        user_id, table_name, entity_uuid, payload, rev,
        client_updated_at, server_updated_at, deleted_at, origin_device_id
      ) values (
        auth.uid(), p_table_name, v_uuid, v_payload, 1,
        v_row_time, now(), v_deleted, p_device_id
      );
      if v_deleted is not null then
        insert into public.sync_tombstones(user_id, table_name, entity_uuid, deleted_at, origin_device_id)
        values (auth.uid(), p_table_name, v_uuid, v_deleted, p_device_id)
        on conflict (user_id, table_name, entity_uuid)
        do update set deleted_at = excluded.deleted_at;
        v_deleted_count := v_deleted_count + 1;
      end if;
      v_inserted := v_inserted + 1;
      v_rows := v_rows || jsonb_build_array(jsonb_build_object('uuid', v_uuid, 'rev', 1));
      continue;
    end if;

    -- A replay: the device never received the acknowledgement and resent the
    -- identical row. Nothing here is superseded, so nothing may be archived -
    -- otherwise every redundant send grows the loser archive with another copy
    -- of a payload that was never actually replaced.
    if v_payload = v_current.payload
       and v_row_time = v_current.client_updated_at
       and v_deleted is not distinct from v_current.deleted_at then
      v_unchanged := v_unchanged + 1;
      v_rows := v_rows || jsonb_build_array(
        jsonb_build_object('uuid', v_uuid, 'rev', v_current.rev));
      continue;
    end if;

    -- Archive the version we are about to supersede, so nothing is unrecoverable.
    insert into public.sync_entity_revisions(
      user_id, table_name, entity_uuid, rev, payload, client_updated_at, origin_device_id
    ) values (
      auth.uid(), p_table_name, v_uuid, v_current.rev, v_current.payload,
      v_current.client_updated_at, v_current.origin_device_id
    );

    -- The version the client started from, when we still have it.
    select payload into v_base from public.sync_entity_revisions
      where user_id = auth.uid() and table_name = p_table_name
        and entity_uuid = v_uuid and rev = v_base_rev
      order by superseded_at desc limit 1;

    v_merged := v_current.payload;
    for v_key in select key from jsonb_object_keys(v_payload) as key
    loop
      v_ours_value := v_current.payload -> v_key;
      v_theirs_value := v_payload -> v_key;
      v_base_value := v_base -> v_key;

      if v_base is not null and v_theirs_value = v_base_value then
        -- The client never touched this field; whatever the server has is newer.
        continue;
      end if;
      if v_base is not null and v_ours_value = v_base_value then
        v_merged := jsonb_set(v_merged, array[v_key], v_theirs_value, true);
        continue;
      end if;
      if v_ours_value is distinct from v_theirs_value then
        -- Genuine conflict on this field.
        v_conflicted := v_conflicted + 1;
        if v_row_time > v_current.client_updated_at then
          v_merged := jsonb_set(v_merged, array[v_key], v_theirs_value, true);
        end if;
        -- Either way the pre-merge value is already archived above.
      end if;
    end loop;

    update public.sync_entities set
      payload = v_merged,
      rev = v_current.rev + 1,
      client_updated_at = greatest(v_current.client_updated_at, v_row_time),
      server_updated_at = now(),
      deleted_at = coalesce(v_deleted, v_current.deleted_at),
      origin_device_id = p_device_id
    where user_id = auth.uid() and table_name = p_table_name and entity_uuid = v_uuid;

    if v_deleted is not null then
      insert into public.sync_tombstones(user_id, table_name, entity_uuid, deleted_at, origin_device_id)
      values (auth.uid(), p_table_name, v_uuid, v_deleted, p_device_id)
      on conflict (user_id, table_name, entity_uuid)
      do update set deleted_at = excluded.deleted_at;
      v_deleted_count := v_deleted_count + 1;
    end if;
    v_updated := v_updated + 1;
    v_rows := v_rows || jsonb_build_array(
      jsonb_build_object('uuid', v_uuid, 'rev', v_current.rev + 1));
  end loop;

  update public.cloud_devices set last_seen_at = now() where id = p_device_id;

  return jsonb_build_object(
    'ok', true, 'table', p_table_name,
    'inserted', v_inserted, 'updated', v_updated,
    'field_conflicts', v_conflicted, 'deleted', v_deleted_count,
    'unchanged', v_unchanged,
    -- The client needs these to record base_rev. Without them sync_entity_state
    -- never advances, every later push still claims base_rev 0, and the 3-way
    -- merge silently degrades to 2-way last-writer-wins forever.
    'rows', v_rows
  );
end; $$;
