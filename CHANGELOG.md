# Changelog

## 0.1.0 (2026-03-04)

- Phase-01 core monitoring (start/end/fail)
- Runtime tracking, metrics logging, summary generation
- Email (SMTP) and Telegram notifications
- Cloud notifications via Cloudflare Worker + Resend
- CLI commands: `add-email`, `delete-email`, `verify-email`, `help`
- Manual notifications, heartbeat, and step-based pings
- Rate limiting (cloud backend) and per-channel throttling
