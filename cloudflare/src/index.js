const json = (data, status = 200) => new Response(JSON.stringify(data), { status, headers: { "content-type": "application/json" } });

function safeText(value) {
  return String(value || "").trim().slice(0, 4000);
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (request.method === "GET" && url.pathname === "/health") {
      return json({ service: "falcon-cloudflare-gateway", status: "HEALTHY" });
    }
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
