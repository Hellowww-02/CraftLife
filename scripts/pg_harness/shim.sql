-- Local Supabase shim — TEST HARNESS ONLY. NEVER APPLY TO A REAL SUPABASE PROJECT.
--
-- Purpose: let the real migrations in supabase/migrations/ and the real pgTAP
-- tests in supabase/tests/ run on vanilla PostgreSQL, so server-side SQL can be
-- verified without a live project.
--
-- Everything here reproduces only the surface the CraftLife migrations actually
-- touch, measured not guessed:
--   auth.uid()            215 references
--   storage.objects        14 references
--   storage.foldername      8 references
--   auth.users              6 references
--   storage.buckets         3 references
-- plus the roles (anon/authenticated/service_role) the RLS grants name, and the
-- `supabase_realtime` publication the realtime migrations alter.
--
-- Anything else Supabase provides is deliberately absent: if a migration starts
-- needing it, that is a signal to extend this file rather than to stub around it.

create extension if not exists citext;
create extension if not exists pgcrypto;

create schema if not exists auth;
create schema if not exists storage;
create schema if not exists extensions;

do $shim$
declare
    r text;
begin
    foreach r in array array['anon','authenticated','service_role','supabase_admin','authenticator']
    loop
        if not exists (select 1 from pg_roles where rolname = r) then
            execute format('create role %I nologin', r);
        end if;
    end loop;
end $shim$;

-- Supabase grants these roles USAGE on the schemas it manages. Without it a
-- test that drops to `set role authenticated` cannot even see pgTAP's own
-- functions in `extensions`, which reads as a mysterious "function does not
-- exist" rather than a permissions problem.
grant usage on schema public, auth, storage, extensions
  to anon, authenticated, service_role;

-- Supabase grants these roles table privileges broadly and then relies on RLS to
-- restrict what is actually visible. The migrations here follow that design:
-- they enable RLS and revoke writes, but never grant SELECT, because on
-- Supabase it is already granted. Reproducing the default (including for tables
-- created later, which is what the migrations do) is what makes an RLS-only
-- migration behave here the way it does in production.
grant all on all tables in schema public to anon, authenticated, service_role;
alter default privileges in schema public
  grant all on tables to anon, authenticated, service_role;
alter default privileges in schema public
  grant execute on functions to anon, authenticated, service_role;

-- Supabase resolves the signed-in user from the JWT claims GUC. Tests set this
-- with `set local request.jwt.claim.sub = '<uuid>'` to act as a user.
create or replace function auth.uid() returns uuid
language sql stable as
$$
    select nullif(current_setting('request.jwt.claim.sub', true), '')::uuid
$$;

create or replace function auth.role() returns text
language sql stable as
$$
    select coalesce(nullif(current_setting('request.jwt.claim.role', true), ''), 'anon')
$$;

create table if not exists auth.users (
    id uuid primary key default gen_random_uuid(),
    email citext unique,
    encrypted_password text not null default '',
    email_confirmed_at timestamptz,
    raw_app_meta_data jsonb default '{}'::jsonb,
    raw_user_meta_data jsonb default '{}'::jsonb,
    is_sso_user boolean not null default false,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists auth.identities (
    id uuid primary key default gen_random_uuid(),
    user_id uuid references auth.users(id) on delete cascade
);

create table if not exists auth.refresh_tokens (
    id bigserial primary key,
    user_id uuid references auth.users(id) on delete cascade,
    token text
);

create table if not exists storage.buckets (
    id text primary key,
    name text not null,
    owner uuid,
    owner_id text,
    public boolean not null default false,
    file_size_limit bigint,
    allowed_mime_types text[],
    avif_autodetection boolean not null default false,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists storage.objects (
    id uuid primary key default gen_random_uuid(),
    bucket_id text references storage.buckets(id),
    name text,
    owner uuid,
    owner_id text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    last_accessed_at timestamptz not null default now(),
    metadata jsonb,
    path_tokens text[] generated always as (regexp_split_to_array(name, '/')) stored
);

create or replace function storage.foldername(name text) returns text[]
language sql immutable as
$$
    select regexp_split_to_array(name, '/')
$$;

create or replace function storage.extension(name text) returns text
language sql immutable as
$$
    select lower(substring(name from '\.([^.]+)$'))
$$;

create or replace function storage.filename(name text) returns text
language sql immutable as
$$
    select (regexp_split_to_array(name, '/'))[array_length(regexp_split_to_array(name, '/'), 1)]
$$;

-- Supabase Realtime subscribes through this publication; several migrations
-- `alter publication supabase_realtime add table ...`.
do $pub$
begin
    if not exists (select 1 from pg_publication where pubname = 'supabase_realtime') then
        create publication supabase_realtime;
    end if;
end $pub$;
