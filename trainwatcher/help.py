"""Help text for TrainWatcher."""

from __future__ import annotations


def help() -> str:
    text = """
TrainWatcher quick help
Developed and managed by Sambit Mahapatra.

Setup (cloud email):
  1) Run: trainwatcher add-email you@example.com
  2) If you self-host, set TRAINWATCHER_BASE_URL to your Worker URL

Basic usage:
  from trainwatcher import monitor
  monitor.start()
  # training...
  monitor.end()

Single-call wrapper:
  from trainwatcher import watch
  watch(train, interpretation="rule")

Zero-config hosted interpretation:
  from trainwatcher import watch
  watch(train, interpretation="hybrid")

Interpretation modes:
  rule   -> deterministic local interpretation only
  hybrid -> local rules + hosted TrainWatcher LLM (no user LLM key needed)
  llm    -> hosted TrainWatcher LLM with rule fallback

Minimal notebook pattern:
  from trainwatcher import monitor
  monitor.start()
  try:
      train()
      monitor.end()
  except Exception as exc:
      monitor.fail(exc)
      raise

Or, context manager:
  from trainwatcher import monitor
  with monitor.watch():
      train()

Context manager:
  from trainwatcher import monitor
  with monitor.watch():
      ...

Failure path:
  try:
      ...
  except Exception as exc:
      monitor.fail(exc)

Manual notifications:
  monitor.notify("Model loaded on GPU")

Heartbeat (time-based):
  monitor.heartbeat(interval_seconds=900)
  monitor.stop_heartbeat()

Step-based pings:
  monitor.step(notify_every=10)  # call in your loop

Configure defaults once:
  monitor.configure(heartbeat_interval=900, step_notify_every=10)

CLI:
  trainwatcher add-email you@example.com
  trainwatcher delete-email
  trainwatcher help

Environment:
  TRAINWATCHER_BASE_URL, TRAINWATCHER_API_KEY, TRAINWATCHER_DISABLE_PROXY
  TRAINWATCHER_INTERPRETATION_MODE
  TRAINWATCHER_INTERPRETATION_FALLBACK
  TRAINWATCHER_LLM_API_KEY, TRAINWATCHER_LLM_BASE_URL, TRAINWATCHER_LLM_MODEL  # optional BYOK fallback
  (Legacy TRAINWATCH_* env vars are still supported.)
""".strip()
    print(text)
    return text
