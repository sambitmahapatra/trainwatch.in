# TrainWatcher

A lightweight training awareness system for machine learning workflows.

TrainWatcher notifies developers when ML training completes or fails and provides a minimal run summary. It is designed to be easy to integrate, framework-agnostic, and reliable.

Developed and managed by Sambit Mahapatra.

## Install

```
pip install trainwatcher
```

## Quickstart

```python
from trainwatcher import monitor

monitor.start()

try:
    # Your training loop here.
    monitor.log(epoch=1, loss=0.42, val_acc=0.81)
    monitor.end()
except Exception as exc:
    monitor.fail(exc)
    raise
```

Convenience context manager:

```python
from trainwatcher import monitor

with monitor.watch():
    # Your training loop here.
    pass
```

## Configuration

TrainWatcher reads configuration from `trainwatcher_config.yaml` by default. You can also set `TRAINWATCHER_CONFIG` to an absolute path or pass a config dict to `monitor.end(config=...)` and `monitor.fail(config=...)`.

Example config (YAML):

```yaml
notifications:
  email: true
  telegram: false

email:
  host: smtp.example.com
  port: 587
  username: user@example.com
  password: app_password
  sender: user@example.com
  recipient: user@example.com
  use_tls: true
  subject: TrainWatcher Notification

logging:
  enabled: true
  path: trainwatcher_run.json
```

An example config is available at `examples/trainwatcher_config.yaml`.

## Cloud Notifications (Resend + Cloudflare)

If you want users to receive email without SMTP setup, use the TrainWatcher Cloud backend.

1. Deploy the Cloudflare Worker in `cloudflare/` and set `RESEND_API_KEY` and `RESEND_FROM`.
2. If you self-host, set the backend URL locally:

```
export TRAINWATCHER_BASE_URL="https://your-worker.workers.dev"
```

3. Register an email once:

```python
from trainwatcher import add_email

add_email("you@example.com")
```

After that, `monitor.end()` and `monitor.fail()` will send notifications automatically if credentials exist.
If you use the hosted TrainWatcher backend, no base URL is required.
You can inspect the active backend URL with:

```python
from trainwatcher import get_base_url
print(get_base_url())
```
Cloud backend enforces a default limit of 10 emails per user per day.

To remove the email:

```python
from trainwatcher import delete_email

delete_email()
```

### CLI

You can also register/delete emails via the CLI:

```
trainwatcher add-email you@example.com
trainwatcher delete-email
trainwatcher help
```

## Mid-Run Notifications

Manual milestone:

```python
from trainwatcher import monitor

monitor.notify("Model loaded on GPU")
```

Time-based heartbeat:

```python
monitor.heartbeat(interval_seconds=900)  # every 15 minutes
# ...
monitor.stop_heartbeat()
```

Step-based pings:

```python
for epoch in range(100):
    train()
    monitor.step(notify_every=10)
```

Configure defaults once:

```python
monitor.configure(
    heartbeat_interval=900,
    step_notify_every=10,
    heartbeat_message="Training still running",
)
```

Optional per-channel minimum intervals:

```yaml
limits:
  email_min_interval_seconds: 1800
  telegram_min_interval_seconds: 300
  cloud_min_interval_seconds: 1800
```

## Environment Variables

These environment variables override config values when set.

- `TRAINWATCHER_CONFIG`
- `TRAINWATCHER_BASE_URL`
- `TRAINWATCHER_API_KEY`
- `TRAINWATCHER_CREDENTIALS_PATH`
- `TRAINWATCHER_DISABLE_PROXY`
- `TRAINWATCHER_NOTIFICATIONS_EMAIL`
- `TRAINWATCHER_NOTIFICATIONS_TELEGRAM`
- `TRAINWATCHER_EMAIL_HOST`
- `TRAINWATCHER_EMAIL_PORT`
- `TRAINWATCHER_EMAIL_USERNAME`
- `TRAINWATCHER_EMAIL_PASSWORD`
- `TRAINWATCHER_EMAIL_SENDER`
- `TRAINWATCHER_EMAIL_RECIPIENT`
- `TRAINWATCHER_EMAIL_USE_TLS`
- `TRAINWATCHER_EMAIL_SUBJECT`
- `TRAINWATCHER_TELEGRAM_BOT_TOKEN`
- `TRAINWATCHER_TELEGRAM_CHAT_ID`
- `TRAINWATCHER_LOGGING_ENABLED`
- `TRAINWATCHER_LOGGING_PATH`

## Logging

Set `logging.enabled: true` in the config to write a run summary JSON file. The default path is `trainwatcher_run.json` relative to the config file location.

## Testing

Install dev dependencies and run tests:

```
pip install -e .[dev]
pytest
```

## Vision

TrainWatcher aims to become an intelligent training awareness layer that lets developers manage and monitor long-running training processes without constant supervision. The long-term goal is an intelligent training companion that integrates into broader ML tooling ecosystems and improves developer productivity.

## Mission

Provide a lightweight, reliable, easy-to-integrate system that captures training lifecycle events and delivers concise summaries through notification channels such as email or messaging services. The mission prioritizes:

- Simplicity of integration
- Reliability of notifications
- Minimal disruption to existing workflows

## Problem Statement

Long-running ML training jobs often require repeated manual checks for completion or failure. This interrupts workflow and delays awareness of errors. Existing enterprise platforms are too heavy for many developers, and there is a gap for a simple, developer-friendly tool focused on basic training awareness.

## Value Proposition

TrainWatcher allows developers to step away during training without losing awareness of outcomes. Minimal integration and reliable notifications reduce monitoring fatigue and improve experimentation efficiency.

## License

Licensed under the GNU Lesser General Public License v3.0 (LGPL-3.0). See `LICENSE`.
