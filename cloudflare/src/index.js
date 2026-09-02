const json = (data, status = 200) => new Response(JSON.stringify(data), { status, headers: { "content-type": "application/json" } });

function safeText(value) {
  return String(value || "").trim().slice(0, 4000);
}

let schemaPromise;
async function stateDb(env) {
  if (!env.FALCON_STATE_DB) throw new Error("falcon_state_db_not_configured");
  if (!schemaPromise) {
    schemaPromise = env.FALCON_STATE_DB.batch([
      env.FALCON_STATE_DB.prepare("CREATE TABLE IF NOT EXISTS missions (mission_id TEXT PRIMARY KEY, payload TEXT NOT NULL, updated_at TEXT NOT NULL)"),
      env.FALCON_STATE_DB.prepare("CREATE TABLE IF NOT EXISTS source_claims (source_key TEXT PRIMARY KEY, mission_id TEXT NOT NULL, created_at TEXT NOT NULL)"),
      env.FALCON_STATE_DB.prepare("CREATE TABLE IF NOT EXISTS operations (operation_key TEXT PRIMARY KEY, status TEXT NOT NULL, metadata TEXT, result TEXT, updated_at TEXT NOT NULL)"),
      env.FALCON_STATE_DB.prepare("CREATE TABLE IF NOT EXISTS memory_events (seq INTEGER PRIMARY KEY AUTOINCREMENT, event_id TEXT UNIQUE NOT NULL, payload TEXT NOT NULL, created_at TEXT NOT NULL)"),
    ]);
  }
  await schemaPromise;
  return env.FALCON_STATE_DB;
}

function stateAuthorized(request, env) {
  const configured = String(env.FALCON_STATE_TOKEN || "");
  const supplied = request.headers.get("Authorization") || "";
  return configured.length >= 24 && supplied === `Bearer ${configured}`;
}

async function requestJson(request) {
  try { return await request.json(); } catch { return null; }
}

async function handleState(request, env, url) {
  if (!stateAuthorized(request, env)) return new Response("Forbidden", { status: 403 });
  let db;
  try { db = await stateDb(env); } catch { return json({ ok: false, error: "state_backend_not_configured" }, 503); }
  const now = new Date().toISOString();

  if (request.method === "GET" && url.pathname === "/state/health") {
    return json({ ok: true, backend: "d1" });
  }

  const missionPrefix = "/state/missions/";
  if (url.pathname.startsWith(missionPrefix)) {
    const missionId = decodeURIComponent(url.pathname.slice(missionPrefix.length));
    if (!missionId || missionId.length > 200) return json({ ok: false, error: "invalid_mission_id" }, 400);
    if (request.method === "PUT") {
      const payload = await requestJson(request);
      if (!payload || typeof payload !== "object" || Array.isArray(payload)) return json({ ok: false, error: "invalid_mission" }, 400);
      await db.prepare("INSERT INTO missions (mission_id,payload,updated_at) VALUES (?,?,?) ON CONFLICT(mission_id) DO UPDATE SET payload=excluded.payload, updated_at=excluded.updated_at")
        .bind(missionId, JSON.stringify(payload), now).run();
      return json({ ok: true });
    }
    if (request.method === "GET") {
      const row = await db.prepare("SELECT payload FROM missions WHERE mission_id=?").bind(missionId).first();
      if (!row) return json({ ok: false, error: "mission_not_found" }, 404);
      return json({ ok: true, mission: JSON.parse(row.payload) });
    }
  }

  if (request.method === "POST" && url.pathname === "/state/sources/claim") {
    const body = await requestJson(request);
    const source = safeText(body?.source); const sourceId = safeText(body?.source_id); const missionId = safeText(body?.mission_id);
    if (!source || !sourceId || !missionId) return json({ ok: false, error: "invalid_source_claim" }, 400);
    const sourceKey = `${source}:${sourceId}`;
    await db.prepare("INSERT OR IGNORE INTO source_claims (source_key,mission_id,created_at) VALUES (?,?,?)").bind(sourceKey, missionId, now).run();
    const row = await db.prepare("SELECT mission_id FROM source_claims WHERE source_key=?").bind(sourceKey).first();
    return json({ ok: true, mission_id: row?.mission_id || missionId });
  }

  if (request.method === "POST" && url.pathname === "/state/operations/claim") {
    const body = await requestJson(request); const operationKey = String(body?.operation_key || "");
    if (!operationKey || operationKey.length > 1000) return json({ ok: false, error: "invalid_operation_key" }, 400);
    const inserted = await db.prepare("INSERT OR IGNORE INTO operations (operation_key,status,metadata,result,updated_at) VALUES (?,'running',?,NULL,?)")
      .bind(operationKey, JSON.stringify(body?.metadata || {}), now).run();
    const row = await db.prepare("SELECT status,result FROM operations WHERE operation_key=?").bind(operationKey).first();
    return json({ ok: true, claimed: Number(inserted?.meta?.changes || 0) === 1, status: row?.status || "running", result: row?.result ? JSON.parse(row.result) : null });
  }

  if (request.method === "POST" && url.pathname === "/state/operations/complete") {
    const body = await requestJson(request); const operationKey = String(body?.operation_key || "");
    if (!operationKey || !body?.result || typeof body.result !== "object") return json({ ok: false, error: "invalid_operation_completion" }, 400);
    await db.prepare("INSERT INTO operations (operation_key,status,metadata,result,updated_at) VALUES (?,'completed',NULL,?,?) ON CONFLICT(operation_key) DO UPDATE SET status='completed', result=excluded.result, updated_at=excluded.updated_at")
      .bind(operationKey, JSON.stringify(body.result), now).run();
    return json({ ok: true });
  }

  if (url.pathname === "/state/memory") {
    if (request.method === "POST") {
      const body = await requestJson(request); const event = body?.event;
      if (!event || typeof event !== "object" || Array.isArray(event)) return json({ ok: false, error: "invalid_memory_event" }, 400);
      const eventId = safeText(event.event_id || crypto.randomUUID());
      await db.prepare("INSERT OR IGNORE INTO memory_events (event_id,payload,created_at) VALUES (?,?,?)").bind(eventId, JSON.stringify(event), now).run();
      return json({ ok: true });
    }
    if (request.method === "GET") {
      const limit = Math.min(Math.max(Number(url.searchParams.get("limit") || 20), 1), 250);
      const result = await db.prepare("SELECT payload FROM memory_events ORDER BY seq DESC LIMIT ?").bind(limit).all();
      const events = (result?.results || []).map((row) => JSON.parse(row.payload)).reverse();
      return json({ ok: true, events });
    }
  }

  return new Response("Not found", { status: 404 });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (request.method === "GET" && url.pathname === "/health") {
      return json({ service: "falcon-cloudflare-gateway", status: "HEALTHY" });
    }
    if (url.pathname.startsWith("/state/")) return handleState(request, env, url);
    if (request.method !== "POST" || url.pathname !== "/telegram/webhook") {
      return new Response("Not found", { status: 404 });
    }

    const supplied = request.headers.get("X-Telegram-Bot-Api-Secret-Token") || "";
    if (!env.FALCON_TELEGRAM_WEBHOOK_SECRET || supplied !== env.FALCON_TELEGRAM_WEBHOOK_SECRET) {
      return new Response("Forbidden", { status: 403 });
    }

    let update;
    try { update = await request.json(); } catch { return json({ ok: true, ignored: "invalid_json" }); }
    const message = update?.message || {};
    const userId = Number(message?.from?.id || 0);
    const chatId = Number(message?.chat?.id || 0);
    const text = safeText(message?.text);
    const allowed = Number(env.FALCON_TELEGRAM_ALLOWED_USER_ID || 0);
    if (!chatId || !text || !allowed || userId !== allowed) return json({ ok: true, ignored: true });

    let kind = "mission";
    if (text === "/health") kind = "health";
    if (text === "/start" || text === "/help") kind = "help";

    await env.FALCON_TASKS.send({
      kind,
      objective: text,
      chat_id: String(chatId),
      update_id: String(update?.update_id ?? "unknown"),
    });
    return json({ ok: true, queued: true });
  },

  async queue(batch, env) {
    for (const message of batch.messages) {
      const task = message.body || {};
      const response = await fetch("https://api.github.com/repos/vickykenin-lang/FALCON/actions/workflows/cloudflare-task.yml/dispatches", {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${env.FALCON_GITHUB_TOKEN}`,
          "Accept": "application/vnd.github+json",
          "Content-Type": "application/json",
          "User-Agent": "falcon-cloudflare-gateway",
          "X-GitHub-Api-Version": "2022-11-28",
        },
        body: JSON.stringify({
          ref: "main",
          inputs: {
            kind: safeText(task.kind || "mission"),
            objective: safeText(task.objective),
            chat_id: safeText(task.chat_id),
            update_id: safeText(task.update_id),
          },
        }),
      });
      if (!response.ok) throw new Error(`github_dispatch_failed:${response.status}`);
      message.ack();
    }
  },
};
