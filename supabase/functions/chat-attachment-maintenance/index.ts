import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

Deno.serve(async (request) => {
  const expected = Deno.env.get("CHAT_MAINTENANCE_SECRET") ?? "";
  const supplied = request.headers.get("x-craftlife-maintenance-secret") ?? "";
  if (!expected || supplied !== expected) {
    return new Response(JSON.stringify({ error: "unauthorized" }), {
      status: 401,
      headers: { "content-type": "application/json" },
    });
  }

  const admin = createClient(
    Deno.env.get("SUPABASE_URL")!,
    Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!,
    { auth: { persistSession: false, autoRefreshToken: false } },
  );
  const bucket = admin.storage.from("chat-attachments");

  const { data: cleanupRows, error: cleanupError } = await admin.rpc(
    "chat_attachment_cleanup_candidates",
  );
  if (cleanupError) throw cleanupError;
  const { data: registered, error: registeredError } = await admin
    .from("message_attachments")
    .select("storage_path")
    .limit(10000);
  if (registeredError) throw registeredError;
  const registeredPaths = new Set((registered ?? []).map((row) => row.storage_path));

  // Storage objects use conversation/user/attachment/file (four levels).
  const objects: Array<{ path: string; created_at?: string }> = [];
  const walk = async (prefix = "", depth = 0): Promise<void> => {
    if (depth > 4 || objects.length >= 2000) return;
    const { data, error } = await bucket.list(prefix, { limit: 1000, sortBy: { column: "name", order: "asc" } });
    if (error) throw error;
    for (const item of data ?? []) {
      const path = prefix ? `${prefix}/${item.name}` : item.name;
      if (item.id) objects.push({ path, created_at: item.created_at });
      else await walk(path, depth + 1);
      if (objects.length >= 2000) break;
    }
  };
  await walk();

  const cutoff = Date.now() - 24 * 60 * 60 * 1000;
  const paths = new Set<string>();
  for (const row of cleanupRows ?? []) paths.add(row.storage_path);
  for (const object of objects) {
    const oldEnough = !object.created_at || new Date(object.created_at).getTime() < cutoff;
    if (oldEnough && !registeredPaths.has(object.path)) paths.add(object.path);
  }

  const removePaths = [...paths].slice(0, 500);
  if (removePaths.length) {
    const { error: removeError } = await bucket.remove(removePaths);
    if (removeError) throw removeError;
    const { error: metadataError } = await admin.from("message_attachments").delete().in("storage_path", removePaths);
    if (metadataError) throw metadataError;
    const { error: slotsError } = await admin.from("chat_attachment_upload_slots").delete().in("storage_path", removePaths);
    if (slotsError) throw slotsError;
  }

  return new Response(JSON.stringify({ ok: true, scanned: objects.length, removed: removePaths.length }), {
    headers: { "content-type": "application/json" },
  });
});
