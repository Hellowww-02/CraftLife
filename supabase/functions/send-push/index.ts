// Phase M10 — send-push: "kantor pos" Supabase untuk notifikasi push.
//
// Alur: pemanggil (Database Webhook / fungsi lain / pemicu manual) POST
// { userId, title, body, data? } ke fungsi ini → fungsi membaca token FCM
// pengguna dari public.device_push_tokens memakai service role → token
// ditukar menjadi akses FCM HTTP v1 → FCM membangunkan perangkat Android
// yang tertutup. Supabase tidak bisa membangunkan aplikasi sendiri; FCM
// adalah satu-satunya kurir yang diizinkan Android untuk itu.
//
// Secret yang dibutuhkan (Supabase Dashboard → Edge Functions → Secrets):
//   FCM_SERVICE_ACCOUNT  isi file JSON service account Firebase (satu baris)
// SUPABASE_URL & SUPABASE_SERVICE_ROLE_KEY disediakan otomatis oleh runtime.
//
// Deploy: `supabase functions deploy send-push` lalu arahkan Database
// Webhook (mis. insert ke social_notifications) ke fungsi ini. Fungsi ini
// TIDAK dipanggil langsung oleh client dan tidak mengekspos token ke client.

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...corsHeaders, "Content-Type": "application/json" },
  });
}

function base64url(input: ArrayBuffer | string): string {
  const bytes = typeof input === "string" ? new TextEncoder().encode(input) : new Uint8Array(input);
  let bin = "";
  for (const b of bytes) bin += String.fromCharCode(b);
  return btoa(bin).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

async function fcmAccessToken(sa: {
  client_email: string;
  private_key: string;
}): Promise<string> {
  const now = Math.floor(Date.now() / 1000);
  const header = base64url(JSON.stringify({ alg: "RS256", typ: "JWT" }));
  const claim = base64url(JSON.stringify({
    iss: sa.client_email,
    scope: "https://www.googleapis.com/auth/firebase.messaging",
    aud: "https://oauth2.googleapis.com/token",
    iat: now,
    exp: now + 3600,
  }));
  const key = await crypto.subtle.importKey(
    "pkcs8",
    pemToBytes(sa.private_key),
    { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const sig = await crypto.subtle.sign(
    "RSASSA-PKCS1-v1_5",
    key,
    new TextEncoder().encode(`${header}.${claim}`),
  );
  const jwt = `${header}.${claim}.${base64url(sig)}`;
  const res = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: `grant_type=urn:ietf:params:oauth:grant-type:jwt-bearer&assertion=${jwt}`,
  });
  const data = await res.json();
  if (!res.ok || !data.access_token) {
    throw new Error(`fcm_token_failed:${res.status}`);
  }
  return data.access_token as string;
}

function pemToBytes(pem: string): ArrayBuffer {
  const b64 = pem
    .replace("-----BEGIN PRIVATE KEY-----", "")
    .replace("-----END PRIVATE KEY-----", "")
    .replace(/\s/g, "");
  const bin = atob(b64);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return bytes.buffer;
}

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: corsHeaders });
  if (req.method !== "POST") return json({ ok: false, error: "method" }, 405);

  const supabaseUrl = Deno.env.get("SUPABASE_URL") ?? "";
  const serviceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ?? "";
  const saRaw = Deno.env.get("FCM_SERVICE_ACCOUNT") ?? "";
  if (!supabaseUrl || !serviceKey || !saRaw) {
    return json({ ok: false, error: "not_configured" }, 503);
  }

  const payload = await req.json().catch(() => ({}));
  const record = payload.record ?? payload;
  const userId = String(record.userId ?? record.user_id ?? "");
  const title = String(record.title ?? "CraftLife");
  const body = String(record.body ?? record.message ?? "");
  if (!userId) return json({ ok: false, error: "user_required" }, 400);

  const tokenRes = await fetch(
    `${supabaseUrl}/rest/v1/device_push_tokens?user_id=eq.${encodeURIComponent(userId)}&select=token,platform`,
    { headers: { apikey: serviceKey, Authorization: `Bearer ${serviceKey}` } },
  );
  if (!tokenRes.ok) return json({ ok: false, error: "token_lookup_failed" }, 502);
  const rows = (await tokenRes.json()) as Array<{ token: string; platform: string }>;
  const tokens = rows.filter((r) => r.platform === "android" && r.token);
  if (tokens.length === 0) return json({ ok: true, sent: 0, reason: "no_tokens" });

  const sa = JSON.parse(saRaw) as {
    project_id: string;
    client_email: string;
    private_key: string;
  };
  const access = await fcmAccessToken(sa);
  let sent = 0;
  for (const row of tokens) {
    const res = await fetch(
      `https://fcm.googleapis.com/v1/projects/${sa.project_id}/messages:send`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${access}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: {
            token: row.token,
            notification: { title, body },
            data: { kind: String(record.type ?? "social") },
            android: { priority: "HIGH" },
          },
        }),
      },
    );
    if (res.ok) sent += 1;
  }
  return json({ ok: true, sent, total: tokens.length });
});
