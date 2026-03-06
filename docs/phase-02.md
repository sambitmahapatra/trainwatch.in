# TrainWatcher Phase-02

## Scope

Phase-02 extends TrainWatcher from a notifier into a lightweight interpretation layer.

Current implemented scope:

- normalized runtime payload generation
- deterministic rule-based analysis
- suggestion mapping
- duck-typed best-model extraction
- hosted LLM interpretation with rule fallback
- optional BYOK fallback using OpenAI-compatible providers
- enriched summary text
- Markdown report rendering
- public `trainwatcher.watch(...)` convenience wrapper

Not yet implemented:

- public convenience wrappers for summary/report access

## Design Rules

- No heavy ML framework dependencies
- No dedicated analytics database
- Internal runtime payload only; persisted JSON is optional
- Rule engine first, LLM second
- Hosted LLM by default, BYOK only as fallback
- If analysis cannot be computed, notifications still send

## Normalized Metric Aliases

TrainWatcher currently normalizes these common aliases:

| Canonical key | Accepted aliases |
| --- | --- |
| `epoch` | `epoch`, `epochs`, `current_epoch` |
| `step` | `step`, `steps`, `global_step` |
| `train_loss` | `train_loss`, `loss`, `training_loss` |
| `val_loss` | `val_loss`, `validation_loss`, `valid_loss`, `eval_loss` |
| `train_accuracy` | `train_accuracy`, `accuracy`, `acc`, `train_acc` |
| `val_accuracy` | `val_accuracy`, `val_acc`, `validation_accuracy`, `valid_accuracy`, `eval_accuracy`, `eval_acc` |
| `learning_rate` | `learning_rate`, `lr` |

## Rule Statuses

The rule engine currently emits:

- `overfitting`
- `plateau`
- `diverging`
- `normal_convergence`
- `mixed_signal`
- `insufficient_data`

Each analysis result follows this contract:

```python
{
    "status": "overfitting",
    "confidence": 0.82,
    "reason": "Training loss improved while validation loss worsened.",
    "source": "rule",
    "suggestions": [],
    "signals": {}
}
```

## Current Internal Modules

### `trainwatcher.metrics`

Builds the normalized runtime payload used by later Phase-02 modules.

### `trainwatcher.rules`

Consumes the normalized payload and detects common training patterns.

### `trainwatcher.suggestions`

Maps a rule status to concise next-step suggestions.

### `trainwatcher.report`

Renders a Markdown report from a normalized payload.

### `trainwatcher.best_model`

Extracts best-model details from sklearn-like search objects without importing sklearn.

### `trainwatcher.llm` and `trainwatcher.prompts`

Provide optional BYOK interpretation using:

- Groq + `llama-3.1-8b-instant`
- OpenRouter + `openai/gpt-oss-20b`

### `trainwatcher.cloud`

Provides hosted interpretation requests against the TrainWatcher backend.

## Example

```python
from trainwatcher import watch

def train():
    from trainwatcher import monitor
    for epoch in range(1, 5):
        monitor.log(
            epoch=epoch,
            loss=1.0 / epoch,
            val_loss=0.7 + (epoch * 0.05),
        )

watch(train, interpretation="rule")
```

If the logged metrics show a strong pattern, the completion summary now includes:

- an observation line
- up to three suggestions

If `interpretation.mode` is `hybrid` or `llm`, the client also requests a hosted interpretation from the TrainWatcher backend using the same API key already stored for notifications.

## Next Phase-02 Work

- public helper APIs for summaries, suggestions, and reports
