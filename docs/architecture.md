# TrainWatch Phase-01 Architecture

**Project:** TrainWatch (working name)

**Purpose:** Notify developers when ML training completes or fails, with a minimal run summary.

## System Overview

Phase-01 is intentionally simple.

```
User Training Script
        |
        v
TrainWatch Monitor
        |
        |-- Runtime Tracker
        |-- Metric Logger (optional)
        |-- Error Capture
        |
        v
Summary Generator
        |
        v
Notification Engine
        |
        |-- Email
        `-- Telegram
```

The system answers one question: **Did training finish or fail?** It then sends a short summary.

## Core Design Principles

- Simplicity: Integrate in two lines of code.
- Framework-agnostic: Works with PyTorch, TensorFlow, scikit-learn, and custom loops.
- Minimal dependencies: Avoid heavy libraries.
- Reliability: Notifications must be sent when training finishes or crashes.

## Package Structure

```
trainwatch/

├── __init__.py
├── monitor.py
├── logger.py
├── runtime.py
├── summary.py
├── notifier.py
│
├── notifications/
│   ├── email_notifier.py
│   └── telegram_notifier.py
│
├── utils/
│   ├── time_utils.py
│   └── error_utils.py
│
├── config.py
└── exceptions.py
```

## Core Modules

### Monitor Module

Entry point responsible for starting monitoring, stopping monitoring, and capturing exceptions.

Example usage:

```python
from trainwatch import monitor

monitor.start()

train_model()

monitor.end()
```

Internal behavior:

```
start()
   |
record start_time
   |
execute training
   |
capture status
   |
generate summary
   |
send notification
```

### Runtime Tracker

Tracks execution time.

Example output:

```
Training runtime: 2h 13m
```

Implementation logic:

```
start_time = time.now()
end_time = time.now()

runtime = end_time - start_time
```

### Metric Logger (Optional)

Allows users to log metrics manually.

Example:

```python
monitor.log(epoch=10, loss=0.23, val_acc=0.91)
```

Internally stored as:

```
metrics = [
 {epoch:1, loss:0.72},
 {epoch:2, loss:0.61}
]
```

Used later for the summary.

### Error Capture System

Detects training failures.

Implementation:

```
try:
   train_model()
except Exception as e:
   monitor.fail(e)
```

Captured data includes error type, error message, last epoch, and runtime.

### Summary Generator

Produces a 4-5 line report.

Example success summary:

```
Training Completed

Runtime: 2h 13m
Best Validation Accuracy: 0.93
Epoch of Best Model: 16
Final Loss: 0.28
```

Example failure summary:

```
Training Failed

Runtime: 32m
Error: CUDA Out Of Memory
Last Epoch: 5
```

### Notification Engine

Sends alerts via supported channels.

Interface:

```
send(message)
```

Supported channels include email and Telegram.

## Notification Channel Architecture

```
Notifier
   |
   |-- EmailNotifier
   `-- TelegramNotifier
```

Each notifier implements `send(message)`.

## Configuration System

Users configure notification settings via a config file (example: `trainwatch_config.yaml`).

Example:

```
notifications:
  telegram: true
  email: false

telegram:
  bot_token: XXXXX
  chat_id: XXXXX
```

The config loader reads these settings at runtime.

## Cloud Notifications (Optional)

TrainWatch can also send notifications through a hosted backend (Cloudflare Worker + Resend).
This avoids SMTP setup for end users. See `cloudflare/README.md` for deployment details.

## Data Flow

```
Training Script
      |
      v
Monitor.start()
      |
      v
Training Execution
      |
      v
Metrics Logged
      |
      v
Monitor.end()
      |
      v
Summary Generator
      |
      v
Notification Engine
      |
      v
User receives alert
```

## Example User Workflow

Installation:

```
pip install trainwatch
```

Training script:

```python
from trainwatch import monitor

monitor.start()

for epoch in range(20):
    train()

monitor.end()
```

Notification received:

```
Training Completed

Runtime: 1h 48m
Final Loss: 0.32
Epochs: 20
```

## Error Scenario Workflow

```
Training starts
      |
      v
Error occurs
      |
      v
Monitor.fail()
      |
      v
Summary generated
      |
      v
Failure notification sent
```

Example alert:

```
Training Failed

Runtime: 27m
Error: CUDA Out Of Memory
Epoch: 6
```

## Logging System

Optional logs can be saved locally (example file: `trainwatch_run.json`).

Example contents:

```
{
  runtime: "2h 13m",
  epochs: 20,
  final_loss: 0.28,
  status: "completed"
}
```

## Extensibility (Future Phases)

Potential future modules:

- analyzer.py
- training_health_model.py
- remote_terminal.py
- gpu_monitor.py

## Estimated Code Size

Phase-01 estimate: 400-700 lines.

| Module   | Lines |
| -------- | ----- |
| monitor  | 120   |
| notifier | 150   |
| summary  | 80    |
| logger   | 80    |
| utils    | 50    |

## Deployment Plan

Open-source release includes:

- GitHub repository
- PyPI package
- Documentation
- Example notebooks

## Phase-01 Success Criteria

Success means:

- Developers install the package.
- Notifications work reliably.
- Integration is easy.
- GitHub repository gains attention.

## Summary

Phase-01 delivers a lightweight ML training awareness tool with monitoring, runtime tracking, failure detection, minimal summaries, and reliable notifications.
