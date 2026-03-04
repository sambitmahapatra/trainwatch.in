"""Help text for TrainWatch."""

from __future__ import annotations


def help() -> str:
    text = """
TrainWatch quick help

Setup (cloud email):
  1) Set TRAINWATCH_BASE_URL to your Cloudflare Worker URL
  2) Run: trainwatch add-email you@example.com

Basic usage:
  from trainwatch import monitor
  monitor.start()
  # training...
  monitor.end()

Context manager:
  from trainwatch import monitor
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
  trainwatch add-email you@example.com
  trainwatch delete-email
  trainwatch help

Environment:
  TRAINWATCH_BASE_URL, TRAINWATCH_API_KEY, TRAINWATCH_DISABLE_PROXY
""".strip()
    print(text)
    return text
