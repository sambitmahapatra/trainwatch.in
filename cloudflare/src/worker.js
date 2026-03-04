const JSON_HEADERS = {
  "content-type": "application/json; charset=utf-8",
};

const CODE_TTL_SECONDS = 10 * 60;
const MAX_VERIFY_ATTEMPTS = 5;
const RATE_LIMITS = {
  register_ip: { limit: 5, window: 3600 },
  register_email: { limit: 3, window: 3600 },
  verify_ip: { limit: 10, window: 3600 },
  notify_user: { limit: 10, window: 86400 },
  delete_key: { limit: 10, window: 3600 },
};

export default {
  async fetch(request, env) {
    try {
      const url = new URL(request.url);
      if (request.method === "POST" && url.pathname === "/register") {
        return await handleRegister(request, env);
      }
      if (request.method === "POST" && url.pathname === "/verify") {
        return await handleVerify(request, env);
      }
      if (request.method === "POST" && url.pathname === "/notify") {
        return await handleNotify(request, env);
      }
      if (request.method === "POST" && url.pathname === "/delete") {
        return await handleDelete(request, env);
      }
      return jsonResponse({ error: "Not found" }, 404);
    } catch (err) {
      return jsonResponse({ error: "Server error" }, 500);
    }
  },
};

async function handleRegister(request, env) {
  const body = await readJson(request);
  const email = normalizeEmail(body.email);
  if (!email) {
    return jsonResponse({ error: "Valid email is required" }, 400);
  }

  const ip = getClientIp(request);
  if (
    ip &&
    !(await checkRateLimit(
      env,
      `register:ip:${ip}`,
      RATE_LIMITS.register_ip.limit,
      RATE_LIMITS.register_ip.window
    ))
  ) {
    return jsonResponse({ error: "Too many requests" }, 429);
  }
  if (
    !(await checkRateLimit(
      env,
      `register:email:${email}`,
      RATE_LIMITS.register_email.limit,
      RATE_LIMITS.register_email.window
    ))
  ) {
    return jsonResponse({ error: "Too many requests" }, 429);
  }

  const code = generateCode();
  const codeHash = await hashHex(code + getSalt(env));
  const now = Date.now();
  const expiresAt = now + CODE_TTL_SECONDS * 1000;

  await env.DB.prepare(
    "INSERT INTO verifications (email, code_hash, expires_at, created_at, attempts) VALUES (?1, ?2, ?3, ?4, 0) " +
      "ON CONFLICT(email) DO UPDATE SET code_hash=excluded.code_hash, expires_at=excluded.expires_at, created_at=excluded.created_at, attempts=0"
  )
    .bind(email, codeHash, expiresAt, now)
    .run();

  await sendEmail(env, {
    to: email,
    subject: "Your TrainWatch verification code",
    text: `Your TrainWatch verification code is ${code}. It expires in 10 minutes.`,
  });

  return jsonResponse({ ok: true });
}

async function handleVerify(request, env) {
  const body = await readJson(request);
  const email = normalizeEmail(body.email);
  const code = (body.code || "").trim();

  if (!email || !code) {
    return jsonResponse({ error: "Email and code are required" }, 400);
  }

  const ip = getClientIp(request);
  if (
    ip &&
    !(await checkRateLimit(
      env,
      `verify:ip:${ip}`,
      RATE_LIMITS.verify_ip.limit,
      RATE_LIMITS.verify_ip.window
    ))
  ) {
    return jsonResponse({ error: "Too many requests" }, 429);
  }

  const verification = await env.DB.prepare(
    "SELECT email, code_hash, expires_at, attempts FROM verifications WHERE email = ?1"
  )
    .bind(email)
    .first();

  if (!verification) {
    return jsonResponse({ error: "Verification not found" }, 404);
  }

  if (verification.expires_at < Date.now()) {
    return jsonResponse({ error: "Verification code expired" }, 400);
  }

  if (verification.attempts >= MAX_VERIFY_ATTEMPTS) {
    return jsonResponse({ error: "Too many attempts" }, 429);
  }

  const codeHash = await hashHex(code + getSalt(env));
  if (codeHash !== verification.code_hash) {
    await env.DB.prepare(
      "UPDATE verifications SET attempts = attempts + 1 WHERE email = ?1"
    )
      .bind(email)
      .run();
    return jsonResponse({ error: "Invalid verification code" }, 400);
  }

  let user = await env.DB.prepare("SELECT id FROM users WHERE email = ?1")
    .bind(email)
    .first();

  if (!user) {
    const userId = crypto.randomUUID();
    await env.DB.prepare(
      "INSERT INTO users (id, email, created_at) VALUES (?1, ?2, ?3)"
    )
      .bind(userId, email, new Date().toISOString())
      .run();
    user = { id: userId };
  }

  const apiKey = generateApiKey();
  const keyHash = await hashHex(apiKey + getSalt(env));
  const keyId = crypto.randomUUID();

  await env.DB.prepare(
    "INSERT INTO api_keys (id, user_id, key_hash, created_at) VALUES (?1, ?2, ?3, ?4)"
  )
    .bind(keyId, user.id, keyHash, new Date().toISOString())
    .run();

  await env.DB.prepare("DELETE FROM verifications WHERE email = ?1")
    .bind(email)
    .run();

  return jsonResponse({ api_key: apiKey });
}

async function handleNotify(request, env) {
  const apiKey = extractApiKey(request);
  if (!apiKey) {
    return jsonResponse({ error: "Missing API key" }, 401);
  }

  const keyHash = await hashHex(apiKey + getSalt(env));
  const keyRow = await env.DB.prepare(
    "SELECT api_keys.id as key_id, users.id as user_id, users.email as email FROM api_keys " +
      "JOIN users ON users.id = api_keys.user_id " +
      "WHERE api_keys.key_hash = ?1 AND api_keys.revoked_at IS NULL"
  )
    .bind(keyHash)
    .first();

  if (!keyRow) {
    return jsonResponse({ error: "Invalid API key" }, 401);
  }

  if (
    !(await checkRateLimit(
      env,
      `notify:user:${keyRow.user_id}`,
      RATE_LIMITS.notify_user.limit,
      RATE_LIMITS.notify_user.window
    ))
  ) {
    return jsonResponse({ error: "Rate limit exceeded" }, 429);
  }

  const body = await readJson(request);
  const message = (body.message || body.summary || body.text || "").toString().trim();
  const subject = (body.subject || "TrainWatch Notification").toString().trim();

  if (!message) {
    return jsonResponse({ error: "Message is required" }, 400);
  }

  await sendEmail(env, {
    to: keyRow.email,
    subject,
    text: message,
  });

  await env.DB.prepare(
    "UPDATE api_keys SET last_used_at = ?1 WHERE id = ?2"
  )
    .bind(new Date().toISOString(), keyRow.key_id)
    .run();

  return jsonResponse({ ok: true });
}

async function handleDelete(request, env) {
  const apiKey = extractApiKey(request);
  if (!apiKey) {
    return jsonResponse({ error: "Missing API key" }, 401);
  }

  const keyHash = await hashHex(apiKey + getSalt(env));
  const keyRow = await env.DB.prepare(
    "SELECT api_keys.id as key_id, users.id as user_id FROM api_keys " +
      "JOIN users ON users.id = api_keys.user_id " +
      "WHERE api_keys.key_hash = ?1 AND api_keys.revoked_at IS NULL"
  )
    .bind(keyHash)
    .first();

  if (!keyRow) {
    return jsonResponse({ error: "Invalid API key" }, 401);
  }

  if (
    !(await checkRateLimit(
      env,
      `delete:key:${keyRow.key_id}`,
      RATE_LIMITS.delete_key.limit,
      RATE_LIMITS.delete_key.window
    ))
  ) {
    return jsonResponse({ error: "Rate limit exceeded" }, 429);
  }

  await env.DB.prepare("DELETE FROM api_keys WHERE user_id = ?1")
    .bind(keyRow.user_id)
    .run();
  await env.DB.prepare("DELETE FROM users WHERE id = ?1")
    .bind(keyRow.user_id)
    .run();

  return jsonResponse({ ok: true });
}

function normalizeEmail(value) {
  if (!value || typeof value !== "string") {
    return null;
  }
  const email = value.trim().toLowerCase();
  if (!email.includes("@")) {
    return null;
  }
  return email;
}

function generateCode() {
  return Math.floor(100000 + Math.random() * 900000).toString();
}

function generateApiKey() {
  const bytes = new Uint8Array(32);
  crypto.getRandomValues(bytes);
  return "tw_" + base64Url(bytes);
}

function base64Url(bytes) {
  let binary = "";
  for (const b of bytes) {
    binary += String.fromCharCode(b);
  }
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}

async function readJson(request) {
  try {
    return await request.json();
  } catch (_) {
    return {};
  }
}

async function hashHex(value) {
  const data = new TextEncoder().encode(value);
  const digest = await crypto.subtle.digest("SHA-256", data);
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

function getSalt(env) {
  if (!env.HASH_SALT || env.HASH_SALT === "CHANGE_ME") {
    throw new Error("HASH_SALT not configured");
  }
  return env.HASH_SALT;
}

function extractApiKey(request) {
  const header = request.headers.get("authorization") || "";
  if (header.toLowerCase().startsWith("bearer ")) {
    return header.slice(7).trim();
  }
  return request.headers.get("x-api-key");
}

function getClientIp(request) {
  const cfIp = request.headers.get("cf-connecting-ip");
  if (cfIp) {
    return cfIp;
  }
  const forwarded = request.headers.get("x-forwarded-for");
  if (forwarded) {
    return forwarded.split(",")[0].trim();
  }
  return null;
}

async function checkRateLimit(env, key, limit, windowSeconds) {
  if (!key) {
    return true;
  }

  const now = Date.now();
  const row = await env.DB.prepare(
    "SELECT key, window_start, count FROM rate_limits WHERE key = ?1"
  )
    .bind(key)
    .first();

  if (!row) {
    await env.DB.prepare(
      "INSERT INTO rate_limits (key, window_start, count) VALUES (?1, ?2, 1)"
    )
      .bind(key, now)
      .run();
    return true;
  }

  const windowMs = windowSeconds * 1000;
  if (now - row.window_start >= windowMs) {
    await env.DB.prepare(
      "UPDATE rate_limits SET window_start = ?2, count = 1 WHERE key = ?1"
    )
      .bind(key, now)
      .run();
    return true;
  }

  if (row.count >= limit) {
    return false;
  }

  await env.DB.prepare(
    "UPDATE rate_limits SET count = count + 1 WHERE key = ?1"
  )
    .bind(key)
    .run();
  return true;
}

async function sendEmail(env, { to, subject, text }) {
  const apiKey = env.RESEND_API_KEY;
  if (!apiKey) {
    throw new Error("Missing RESEND_API_KEY");
  }

  const payload = {
    from: env.RESEND_FROM,
    to,
    subject,
    text,
  };

  const response = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const details = await response.text();
    throw new Error(`Resend error: ${response.status} ${details}`);
  }
}

function jsonResponse(payload, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: JSON_HEADERS,
  });
}
