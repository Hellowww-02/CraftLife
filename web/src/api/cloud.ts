import { apiGet, apiPost } from './client';

export type CloudStatus = {
  ok: boolean;
  configured?: boolean;
  sdk_available?: boolean;
  keyring_available?: boolean;
  authenticated?: boolean;
  linked?: boolean;
  email?: string;
  last_error?: string;
  realtime_connected?: boolean;
  queue?: { pending?: number; retry?: number; done?: number; failed?: number };
  queue_failed_samples?: { last_error?: string; retry_count?: number; entity_type?: string }[];
  device?: { device_id?: string; device_name?: string; platform?: string };
  personal?: { conflict_status?: string; remote_revision?: number };
  link?: { email?: string; last_sync_at?: string | null; status?: string };
};

export type CloudDevice = {
  id: string;
  device_name?: string;
  platform?: string;
  revoked_at?: string | null;
  last_seen_at?: string | null;
  current?: boolean;
};

export async function cloudStatus(): Promise<CloudStatus> {
  return apiGet('/api/cloud/status');
}

export async function cloudRegister(email: string, password: string) {
  return apiPost<{ ok: boolean; verification_required?: boolean; error?: string }>(
    '/api/cloud/register',
    { email, password },
  );
}

export async function cloudLogin(email: string, password: string) {
  return apiPost<{ ok: boolean; error?: string; status?: CloudStatus }>(
    '/api/cloud/login',
    { email, password },
  );
}

export async function cloudLogout() {
  return apiPost<{ ok: boolean; status?: CloudStatus }>('/api/cloud/logout', {});
}

export async function cloudSyncNow() {
  return apiPost<{ ok: boolean; pushed?: { done?: number; failed?: number }; error?: string; code?: string; status?: CloudStatus }>(
    '/api/cloud/sync-now',
    {},
  );
}

export async function cloudMigrateLocal() {
  return apiPost<{ ok: boolean; preview?: Record<string, unknown>; error?: string; status?: CloudStatus }>(
    '/api/cloud/migrate-local',
    {},
  );
}

export async function cloudConflict(choice: 'local' | 'cloud') {
  return apiPost<{ ok: boolean; error?: string; status?: CloudStatus }>('/api/cloud/conflict', { choice });
}

export async function cloudDevices() {
  return apiGet<{ ok: boolean; devices: CloudDevice[]; register_error?: string | null; error?: string }>(
    '/api/cloud/devices',
  );
}

export async function cloudRevokeDevice(deviceId: string) {
  return apiPost<{ ok: boolean; error?: string }>('/api/cloud/devices/revoke', { device_id: deviceId });
}

export async function cloudQueueRetry() {
  return apiPost<{ ok: boolean; error?: string; status?: CloudStatus }>('/api/cloud/queue/retry', {});
}
