/** The demo-token backend for the TRY IT LIVE section on noisy-studio.dev.
 *
 *  DELIBERATELY SEPARATE from the application: the daemon/app backend must
 *  never be entangled with the website. This service exists for exactly one
 *  thing - minting short-lived xAI ephemeral tokens so a visitor's browser
 *  can open a Grok realtime voice session without ever seeing our API key.
 *
 *  One route: POST /api/demo-token.
 *  Everything else is the abuse package from
 *  website/src/demo/live-demo-architecture.md: origin allowlist, per-IP
 *  limits, a global daily budget with a kill switch, and a Turnstile hook
 *  stubbed for later. Plain node:http on purpose - one file, no deps.
 *
 *  The XAI_DEMO_API_KEY env var is read once and used only in the upstream
 *  Authorization header. It is never logged, echoed, or included in any
 *  response - including error responses.
 */
import { createServer, type IncomingMessage, type ServerResponse } from "node:http";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

/* --- configuration -------------------------------------------------------- */

const PORT = Number(process.env.DEMO_BACKEND_PORT ?? 8788);

/** Ephemeral token lifetime. Single-use in spirit: long enough to open the
 *  websocket, short enough that a leaked one is worthless in minutes. */
const TOKEN_TTL_SECONDS = 120;
/** What the frontend should enforce as the session ceiling; also returned
 *  to the client so the agent can wrap up gracefully. The mint API only
 *  caps the TOKEN lifetime, so the hard stop lives in the driver. */
const MAX_SESSION_SECONDS = 180;

const REALTIME_MODEL = "grok-voice-latest";
const REALTIME_WS_URL = "wss://api.x.ai/v1/realtime";
const MINT_URL = "https://api.x.ai/v1/realtime/client_secrets";

/** Per IP: one live session at a time, and a small daily allowance.
 *  Overridable so local testing is not blocked by the 3-minute hold a mint
 *  puts on the IP - production leaves the defaults alone. */
const PER_IP_CONCURRENT = Number(process.env.DEMO_PER_IP_CONCURRENT ?? 1);
const PER_IP_DAILY = Number(process.env.DEMO_PER_IP_DAILY ?? 10);
/** Global circuit breaker: a viral day degrades to the scripted demo
 *  instead of burning the budget. */
const GLOBAL_DAILY_SESSIONS = 200;

const ALLOWED_ORIGINS = (process.env.DEMO_ALLOWED_ORIGINS ?? "http://localhost:5199")
  .split(",")
  .map((o) => o.trim())
  .filter(Boolean);

/** The demo agent's persona - server-side single source. Shipped to the
 *  client in the mint response; the driver injects it via session.update.
 *  (True server-side injection needs xAI's session binding on the mint
 *  call - see the README's "known gaps".) */
const AGENT_BRIEF = readFileSync(
  fileURLToPath(new URL("../../website/src/demo/demo-agent-brief.md", import.meta.url)),
  "utf8",
);

/* --- in-memory limiter state (v1: resets on restart, one process) --------- */

const utcDay = () => new Date().toISOString().slice(0, 10);

interface IpState {
  day: string;
  count: number;
  /** Epoch ms until which this IP is considered "in a session". */
  activeUntil: number;
}
const perIp = new Map<string, IpState>();
let global = { day: utcDay(), count: 0 };

function ipOf(req: IncomingMessage): string {
  // Behind a proxy in prod; direct in dev. First hop of XFF is fine for a
  // rate limiter that only guards a demo budget.
  const xff = req.headers["x-forwarded-for"];
  const first = Array.isArray(xff) ? xff[0] : xff?.split(",")[0];
  return (first ?? req.socket.remoteAddress ?? "unknown").trim();
}

type Denial = "ip-concurrent" | "ip-daily" | "budget";

function checkLimits(req: IncomingMessage): Denial | null {
  const day = utcDay();
  if (global.day !== day) global = { day, count: 0 };
  if (global.count >= GLOBAL_DAILY_SESSIONS) return "budget";

  const ip = ipOf(req);
  let s = perIp.get(ip);
  if (!s || s.day !== day) {
    s = { day, count: 0, activeUntil: 0 };
    perIp.set(ip, s);
  }
  if (s.activeUntil > Date.now() && PER_IP_CONCURRENT <= 1) return "ip-concurrent";
  if (s.count >= PER_IP_DAILY) return "ip-daily";
  return null;
}

function recordMint(req: IncomingMessage) {
  const s = perIp.get(ipOf(req));
  if (s) {
    s.count += 1;
    s.activeUntil = Date.now() + MAX_SESSION_SECONDS * 1000;
  }
  global.count += 1;
}

/** Turnstile hook - NOT integrated yet. When abuse shows up: verify the
 *  cf-turnstile-response token from the request body against Cloudflare's
 *  siteverify endpoint here and return false on failure. */
async function verifyHuman(_req: IncomingMessage, _body: unknown): Promise<boolean> {
  return true;
}

/* --- the one route --------------------------------------------------------- */

function send(res: ServerResponse, status: number, body: object, origin?: string) {
  const headers: Record<string, string> = { "content-type": "application/json" };
  if (origin && ALLOWED_ORIGINS.includes(origin)) {
    headers["access-control-allow-origin"] = origin;
    headers["access-control-allow-methods"] = "POST, OPTIONS";
    headers["access-control-allow-headers"] = "content-type";
  }
  res.writeHead(status, headers);
  res.end(JSON.stringify(body));
}

/** Everything the frontend treats identically: silently stay on the
 *  scripted demo. The reason is for our own debugging, never shown to
 *  visitors. */
function demoPaused(res: ServerResponse, reason: string, origin?: string) {
  send(res, 503, { error: "demo-paused", reason }, origin);
}

async function mintToken(req: IncomingMessage, res: ServerResponse) {
  const origin = req.headers.origin;
  const apiKey = process.env.XAI_DEMO_API_KEY;

  // Origin gate first: a disallowed caller learns nothing about our state.
  if (!origin || !ALLOWED_ORIGINS.includes(origin)) {
    return send(res, 403, { error: "forbidden" }, origin);
  }

  if (process.env.DEMO_PAUSED === "1") return demoPaused(res, "kill-switch", origin);
  if (!apiKey) return demoPaused(res, "not-configured", origin);

  const denial = checkLimits(req);
  if (denial === "budget") return demoPaused(res, "daily-budget", origin);
  if (denial) return send(res, 429, { error: "rate-limited", reason: denial }, origin);

  if (!(await verifyHuman(req, null))) return send(res, 403, { error: "forbidden" }, origin);

  let upstream: Response;
  try {
    upstream = await fetch(MINT_URL, {
      method: "POST",
      headers: {
        authorization: `Bearer ${apiKey}`,
        "content-type": "application/json",
      },
      body: JSON.stringify({ expires_after: { seconds: TOKEN_TTL_SECONDS } }),
    });
  } catch {
    return demoPaused(res, "upstream-unreachable", origin);
  }
  if (!upstream.ok) {
    // Never forward upstream bodies: they can echo request details.
    return demoPaused(res, `upstream-${upstream.status}`, origin);
  }

  const minted = (await upstream.json()) as { value?: string; expires_at?: number };
  if (!minted.value) return demoPaused(res, "upstream-shape", origin);

  recordMint(req);
  send(
    res,
    200,
    {
      token: minted.value,
      expires_at: minted.expires_at ?? null,
      session: {
        ws_url: REALTIME_WS_URL,
        model: REALTIME_MODEL,
        max_seconds: MAX_SESSION_SECONDS,
        instructions: AGENT_BRIEF,
      },
    },
    origin,
  );
}

const server = createServer((req, res) => {
  const origin = req.headers.origin;
  if (req.method === "OPTIONS") {
    send(res, 204, {}, origin);
    return;
  }
  if (req.method === "POST" && req.url === "/api/demo-token") {
    void mintToken(req, res);
    return;
  }
  send(res, 404, { error: "not-found" }, origin);
});

server.listen(PORT, () => {
  // Log config presence as booleans only - the value must never appear.
  console.log(
    `demo-token backend on :${PORT} | key configured: ${Boolean(
      process.env.XAI_DEMO_API_KEY,
    )} | origins: ${ALLOWED_ORIGINS.join(", ")}`,
  );
});
