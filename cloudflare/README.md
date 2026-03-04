# TrainWatch Cloud (Cloudflare Worker + D1 + Resend)

This backend powers email verification and notification sending for TrainWatch.

## Prerequisites

- Cloudflare account with Workers and D1 enabled
- Resend account with verified domain
- Wrangler CLI installed (`npm i -g wrangler`)

## Setup

1. Create a D1 database:

```
wrangler d1 create trainwatch
```

2. Update `wrangler.toml` with your `account_id` and `database_id`.

3. Apply the schema:

```
wrangler d1 execute trainwatch --file=./schema.sql --remote
```

4. Set secrets:

```
wrangler secret put RESEND_API_KEY
wrangler secret put HASH_SALT
```

5. Update `wrangler.toml` vars:

- `RESEND_FROM` (e.g., `notify@trainwatch.in`)

6. Deploy:

```
wrangler deploy
```

## API Endpoints

- `POST /register` `{ "email": "you@example.com" }`
- `POST /verify` `{ "email": "you@example.com", "code": "123456" }`
- `POST /notify` (Authorization: `Bearer <api_key>`) `{ "message": "...", "subject": "optional" }`
- `POST /delete` (Authorization: `Bearer <api_key>`) `{}`

## Notes

- DNS records in Cloudflare must be **DNS only** (gray cloud) for Resend verification.
- Store `RESEND_API_KEY` in Cloudflare secrets, not in source files.
- Basic rate limiting is enforced in the Worker (per IP/email/user). You can tune limits in `src/worker.js`.
- Default email limit: 10 notifications per user per day.
