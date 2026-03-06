# TrainWatcher Phase-02.1

## Telegram Alert System WBS

## 1. Objective

Extend TrainWatcher's notification layer with optional Telegram delivery while preserving:

- lightweight installation
- minimal setup
- non-blocking behavior
- email as the stable baseline

Phase-02.1 adds:

```text
severity-aware routing
telegram delivery
urgent failure alerts
optional repeat-on-critical
```

Telegram remains a notification channel, not a monitoring engine.

---

## 2. Product Principles

- Telegram is optional.
- Completion defaults to email only.
- Failure can route to Telegram if enabled.
- Rule-based diagnosis remains the core message content.
- Telegram failures must never block email delivery.
- Urgent alerts mean stronger formatting and optional repeat, not guaranteed wake-up behavior.

---

## 3. Architecture Overview

```text
Training Event
      ↓
Summary Builder
      ↓
Severity Classifier
      ↓
Notification Router
      ├── Email Notifier
      └── Telegram Notifier
```

---

## 4. Event and Severity Model

### Event Types

- `training_completed`
- `training_failed`
- `best_model_found` (optional)
- `manual_event` (future-compatible)

### Severity Mapping

- `training_completed` → `info`
- `best_model_found` → `info`
- `training_failed` → `critical`

---

## 5. Routing Rules

### Default Behavior

- `info` → email
- `critical` → email + Telegram if enabled

### Optional Urgent Behavior

If enabled:

- `critical` → immediate Telegram urgent alert
- optional one follow-up repeat after cooldown

### Fault Tolerance Rule

If Telegram fails:

- email still sends
- training flow is never blocked

---

## 6. Configuration Design

Users should only need:

- Telegram bot token
- Telegram chat ID

### Proposed Config Shape

```yaml
notifications:
  email:
    enabled: true

  telegram:
    enabled: false
    bot_token: "..."
    chat_id: "..."
    on_success: false
    on_failure: true
    urgent_on_failure: true
    repeat_on_critical: false
    repeat_after_minutes: 5
    max_repeats: 1
    timeout_seconds: 10
```

### Environment Variable Support

```text
TRAINWATCHER_TELEGRAM_BOT_TOKEN
TRAINWATCHER_TELEGRAM_CHAT_ID
```

---

## 7. Module Breakdown

### 7.1 Notification Router

**Objective**

Centralize channel and severity decisions.

**Tasks**

- define event-to-severity mapping
- decide which channels receive each event
- support urgent and repeat logic
- preserve backward compatibility with existing email flow

**Files**

```text
trainwatcher/notifications/router.py
```

---

### 7.2 Telegram Notifier

**Objective**

Send formatted Telegram messages via the Bot API.

**Tasks**

- implement Telegram send helper
- support standard and urgent message variants
- implement timeout and error handling
- optionally support one repeat for critical alerts

**Files**

```text
trainwatcher/notifications/telegram_notifier.py
```

---

### 7.3 Message Formatting

**Objective**

Generate short, structured Telegram messages.

**Tasks**

- create completion format
- create failure format
- create short urgent format
- keep messages concise and scannable

**Files**

```text
trainwatcher/notifications/message_formats.py
trainwatcher/summary.py
```

---

### 7.4 Config Integration

**Objective**

Expose Telegram settings cleanly without increasing friction.

**Tasks**

- extend config loader for Telegram settings
- add env var support
- define sensible defaults
- validate required token/chat fields only when Telegram is enabled

**Files**

```text
trainwatcher/config.py
```

---

### 7.5 Monitor Integration

**Objective**

Plug routing into current monitor lifecycle.

**Tasks**

- route success notifications through router
- route failure notifications through router
- preserve existing `monitor.end()` and `monitor.fail()` UX

**Files**

```text
trainwatcher/monitor.py
trainwatcher/notifier.py
```

---

## 8. Message Design

### Completion Message

```text
Training Completed

Script: train_notebook.ipynb
Runtime: 1h 12m
Best Validation Accuracy: 0.91
Epoch of Best Model: 14
Observation: Validation improved steadily.
```

### Failure Message

```text
Training Failed

Script: train_notebook.ipynb
Runtime: 12m
Error: CUDA out of memory

Likely Cause:
The batch or model exceeded available GPU memory.

Suggestions:
- Reduce batch size
- Enable mixed precision
- Retry from checkpoint
```

### Urgent Failure Message

```text
URGENT: Training Failed

Script: train_notebook.ipynb
Runtime: 12m
Error: CUDA out of memory

Immediate action recommended.
```

---

## 9. Reliability Requirements

The Telegram channel must gracefully handle:

- invalid bot token
- invalid chat ID
- network timeout
- Telegram API failure
- repeat-send failure

Failure handling rules:

- never crash the main training flow
- never suppress email because Telegram failed
- log/send fallback diagnostics locally if possible

---

## 10. Testing Tasks

### Unit Tests

- routing for success event
- routing for failure event
- urgent mode selection
- repeat-on-critical logic
- disabled Telegram path
- env var config loading

### Integration-style Tests

- successful training with email only
- successful training with optional Telegram enabled
- failure with Telegram enabled
- invalid Telegram credentials
- simulated network failure

**Files**

```text
tests/test_router.py
tests/test_telegram_notifier.py
tests/test_notification_routing.py
```

---

## 11. Documentation Tasks

Update:

- `README.md`
- `docs/phase-02.md`
- `trainwatcher.help()`

Add examples for:

- email-only default flow
- Telegram on failure only
- urgent failure alert with repeat disabled
- urgent failure alert with one repeat

---

## 12. Execution Order

### 12.1 Routing Contract

- define event model
- define severity model
- define route decision interface

### 12.2 Telegram Notifier

- implement Bot API sender
- add timeout and error handling

### 12.3 Config Layer

- parse Telegram config
- parse env vars
- validate only when enabled

### 12.4 Message Variants

- completion
- failure
- urgent failure

### 12.5 Monitor Wiring

- route success/failure through router
- preserve current email behavior

### 12.6 Tests

- unit
- integration-style

### 12.7 Docs

- README
- help
- examples

---

## 13. Success Criteria

Phase-02.1 succeeds if:

- Telegram remains optional
- failures can alert the user quickly
- completion does not become noisy by default
- email remains reliable baseline delivery
- Telegram issues never block TrainWatcher
- user setup remains limited to bot token + chat ID

---

## 14. Strategic Outcome

With Phase-02.1, TrainWatcher evolves from:

```text
training awareness + interpretation
```

to:

```text
training awareness + interpretation + failure-first real-time intervention
```

without sacrificing its lightweight design.
