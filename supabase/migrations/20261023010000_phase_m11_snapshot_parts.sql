-- Phase M11 — payload snapshot inkremental (menutup G5).
--
-- RPC upsert_personal_snapshot versi lama hanya menerima document_key
-- 'tracker_v1' dan payload <= 8 MB, sehingga snapshot tracker utuh tidak
-- bisa lewat untuk pengguna berdata besar. Kini dokumen besar dipecah
-- client menjadi part `tracker_v1/part/NNN` (masing-masing <= 3 MB);
-- fungsi di bawah sama persis dengan versi 20260813120000 kecuali
-- validasi document_key yang kini juga menerima key part. Plafon 8 MB
-- per payload TETAP berlaku — yang berubah hanya jumlah dokumennya.
-- Migrasi lama tidak disunting (UPDATE_RULES section 6); fungsi diganti utuh
-- lewat create or replace.

create or replace function public.upsert_personal_snapshot(
  p_document_key text,
  p_base_revision bigint,
  p_content_hash text,
  p_payload jsonb,
  p_device_id uuid,
  p_client_updated_at timestamptz default now()
)
returns jsonb
language plpgsql security definer set search_path=public as $$
declare
  current_row public.personal_snapshots;
  result public.personal_snapshots;
  safe_client_time timestamptz;
begin
  if auth.uid() is null or not public.current_profile_active() then
    raise exception 'account_unavailable';
  end if;
  if p_document_key<>'tracker_v1' and p_document_key not like 'tracker_v1/part/%' then raise exception 'unsupported_document'; end if;
  if p_base_revision is null or p_base_revision<0 then raise exception 'invalid_base_revision'; end if;
  if p_content_hash is null or p_content_hash !~ '^[0-9a-f]{64}$' then raise exception 'invalid_content_hash'; end if;
  if p_payload is null or jsonb_typeof(p_payload)<>'object' then raise exception 'invalid_payload'; end if;
  if octet_length(p_payload::text)>8388608 then raise exception 'payload_too_large'; end if;
  if not exists(
    select 1 from public.cloud_devices
    where id=p_device_id and user_id=auth.uid() and revoked_at is null
  ) then raise exception 'device_not_registered'; end if;

  safe_client_time=least(coalesce(p_client_updated_at,now()),now()+interval '5 minutes');
  select * into current_row from public.personal_snapshots
    where user_id=auth.uid() and document_key=p_document_key for update;

  if current_row.user_id is null then
    if p_base_revision<>0 then
      return jsonb_build_object('ok',false,'conflict',true,'reason','missing_remote_base');
    end if;
    insert into public.personal_snapshots(
      user_id,document_key,revision,content_hash,payload,source_device_id,
      client_updated_at,server_updated_at
    ) values(
      auth.uid(),p_document_key,1,p_content_hash,p_payload,p_device_id,
      safe_client_time,now()
    ) returning * into result;
    return jsonb_build_object('ok',true,'conflict',false,'snapshot',to_jsonb(result));
  end if;

  if current_row.revision<>p_base_revision then
    return jsonb_build_object(
      'ok',false,'conflict',true,'reason','revision_mismatch',
      'snapshot',to_jsonb(current_row)
    );
  end if;

  if current_row.content_hash=p_content_hash then
    update public.cloud_devices set last_seen_at=now() where id=p_device_id;
    return jsonb_build_object('ok',true,'conflict',false,'unchanged',true,
                              'snapshot',to_jsonb(current_row));
  end if;

  update public.personal_snapshots set
    revision=revision+1,
    content_hash=p_content_hash,
    payload=p_payload,
    source_device_id=p_device_id,
    client_updated_at=safe_client_time,
    server_updated_at=now()
  where user_id=auth.uid() and document_key=p_document_key
  returning * into result;
  update public.cloud_devices set last_seen_at=now() where id=p_device_id;
  return jsonb_build_object('ok',true,'conflict',false,'snapshot',to_jsonb(result));
end; $$;
