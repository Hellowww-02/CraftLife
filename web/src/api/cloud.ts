import { apiGet, apiPost } from '@craftlife/core';

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
  /** Kuota egress habis / project dibatasi: sync berhenti sendiri (M05). */
  suspended?: boolean;
  suspended_reason?: string;
  suspended_at?: string;
  retry_after_seconds?: number;
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

/**
 * M04c — sync status and the recoverable conflict surface.
 *
 * These three calls exist because the previous UI could only show a binary
 * "keep local / use cloud" prompt. The merge already keeps the losing value
 * (K11); without a way to list and restore it, that guarantee is invisible to
 * the person whose data was overwritten.
 */

export interface SyncFailedJob {
  entity_type: string;
  operation: string;
  retry_count: number;
  last_error: string;
  next_retry_at: string | null;
}

export interface SyncStatusSummary {
  ok: boolean;
  pending: number;
  failed: number;
  failed_jobs: SyncFailedJob[];
  unresolved_conflicts: number;
  pending_tombstones: number;
  last_synced_at: string | null;
  error?: string;
}

export interface SyncConflict {
  id: number;
  table_name: string;
  entity_uuid: string;
  field: string;
  kept_value: string | null;
  lost_value: string | null;
  kept_side: 'cloud' | 'local';
  detected_at: string | null;
}

export async function cloudSyncStatus() {
  return apiGet<SyncStatusSummary>('/api/cloud/sync-status');
}

export async function cloudConflicts() {
  return apiGet<{ ok: boolean; conflicts: SyncConflict[]; error?: string }>('/api/cloud/conflicts');
}

export async function cloudRestoreConflict(conflictId: number) {
  return apiPost<{ ok: boolean; error?: string; code?: string }>('/api/cloud/conflicts/restore', {
    conflict_id: conflictId,
  });
}
