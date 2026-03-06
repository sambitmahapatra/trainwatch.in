# Phase-02 Work Breakdown Structure (WBS)

## Product Direction

Phase-02 extends TrainWatcher from a training notifier into a lightweight training interpretation layer.

Non-negotiables:

- minimal friction
- lightweight dependencies
- framework-agnostic operation
- rule-based reliability first
- hosted intelligence second
- no workflow replacement

## Locked Phase-02 Decisions

- The rule engine always runs.
- The rule engine is the minimum reliable interpretation path.
- Notifications must still send even if every LLM path fails.
- Interpretation modes are:
  - `rule`
  - `hybrid`
  - `llm`
- `hybrid` and `llm` use the TrainWatcher hosted backend by default.
- Users do not need their own LLM API key for normal usage.
- Optional BYOK fallback is only for advanced users after hosted quota is exhausted.
- Hosted LLM quota target: `10 interpretations per user per day`.
- Only aggregated metrics and rule output are sent to the hosted LLM backend.

## Phase-02 Deliverables

- normalized metrics extraction
- rule-based training interpretation
- next-step suggestions
- hosted LLM explanation
- optional BYOK fallback
- best-model summary extraction
- extended notification summaries
- optional markdown report generation

## Sub-Phases

1. Phase 02-A: Analysis contract and data schema
2. Phase 02-B: Metrics extraction and normalization
3. Phase 02-C: Rule engine
4. Phase 02-D: Suggestion engine
5. Phase 02-E: Best-model summary
6. Phase 02-F: Summary and notification expansion
7. Phase 02-G: Hosted interpretation backend
8. Phase 02-H: Optional BYOK fallback
9. Phase 02-I: Report generation
10. Phase 02-J: Public API and ergonomics
11. Phase 02-K: Testing
12. Phase 02-L: Documentation and examples

## WBS

### 1.0 Analysis Contract

1.1 Define normalized metric aliases for:
- `loss`
- `val_loss`
- `accuracy`
- `val_accuracy`
- `epoch`
- `runtime`

1.2 Define analysis output schema:

```python
analysis = {
    "status": "overfitting",
    "confidence": 0.82,
    "reason": "validation loss increased while training loss decreased"
}
```

1.3 Define interpretation output schema:

```python
interpretation = {
    "mode": "hybrid",
    "text": "The model appears to overfit after epoch 5.",
    "provider": "hosted",
    "model": "llama-3.1-8b-instant",
    "error": None
}
```

1.4 Define final report payload schema:

```python
report = {
    "metrics": {},
    "analysis": {},
    "suggestions": [],
    "best_model": {},
    "interpretation": {}
}
```

### 2.0 Metrics Extraction

2.1 Create or extend [`trainwatcher/metrics.py`](E:/Train_Watch/trainwatcher/metrics.py)  
2.2 Extract runtime, epoch count, final metrics, best metrics  
2.3 Normalize metric aliases from user logs  
2.4 Handle partial or missing metrics safely  
2.5 Keep the runtime payload internal by default  

### 3.0 Rule Engine

3.1 Create or extend [`trainwatcher/rules.py`](E:/Train_Watch/trainwatcher/rules.py)  
3.2 Implement overfitting detection  
3.3 Implement plateau detection  
3.4 Implement divergence detection  
3.5 Implement normal convergence detection  
3.6 Add thresholds and patience defaults  
3.7 Add config overrides for thresholds  
3.8 Return deterministic `status`, `confidence`, and `reason`

### 4.0 Suggestion Engine

4.1 Create or extend [`trainwatcher/suggestions.py`](E:/Train_Watch/trainwatcher/suggestions.py)  
4.2 Map rule states to actionable suggestions  
4.3 Keep suggestions short and implementation-oriented  
4.4 Return empty list if analysis is inconclusive

### 5.0 Best Model Summary

5.1 Create or extend [`trainwatcher/best_model.py`](E:/Train_Watch/trainwatcher/best_model.py)  
5.2 Support duck-typed sklearn-like objects:
- `best_params_`
- `best_score_`
- `best_estimator_`

5.3 Extract best-model summary without adding sklearn as a dependency  
5.4 Return `None` if best-model info is unavailable

### 6.0 Summary and Notification Expansion

6.1 Extend summary builder to include:
- metrics summary
- rule observation
- suggestions
- best-model summary
- optional hosted interpretation

6.2 `rule` mode shows deterministic rule output only  
6.3 `hybrid` mode shows rule output plus hosted interpretation  
6.4 `llm` mode prefers hosted interpretation but falls back to rules  
6.5 Keep notification messages concise enough for email and Telegram  

### 7.0 Hosted Interpretation Backend

7.1 Add backend endpoint:
- `POST /interpret`

7.2 Authenticate using the existing TrainWatcher cloud API key  
7.3 Enforce dedicated hosted-LLM user quota:
- `10 interpretations per user per day`

7.4 Backend stores provider secrets, not the user  
7.5 Initial hosted provider path:
- Groq
- `https://api.groq.com/openai/v1`
- `llama-3.1-8b-instant`

7.6 Optional hosted alternate provider path:
- OpenRouter
- `https://openrouter.ai/api/v1`
- `openai/gpt-oss-20b`

7.7 Send only aggregated metrics and rule output to the backend  
7.8 Add timeout and graceful fallback behavior  

### 8.0 Optional BYOK Fallback

8.1 Allow advanced users to configure their own OpenAI-compatible API key  
8.2 Only use BYOK when:
- hosted quota is exhausted
- hosted interpretation fails
- user explicitly enables fallback

8.3 Keep BYOK optional and out of the default user flow  
8.4 Preserve rule-based fallback even if BYOK also fails

### 9.0 Report Generation

9.1 Create or extend [`trainwatcher/report.py`](E:/Train_Watch/trainwatcher/report.py)  
9.2 Generate `trainwatcher_report.md`  
9.3 Include:
- metrics
- analysis
- suggestions
- best-model summary
- optional hosted/LLM interpretation

9.4 Keep report generation optional

### 10.0 Public API

10.1 Add or extend convenience wrapper:

```python
import trainwatcher as tw
tw.watch(train_fn, interpretation="rule")
```

10.2 Support interpretation modes:
- `rule`
- `hybrid`
- `llm`

10.3 Keep BYOK fallback hidden behind explicit config  
10.4 Preserve existing `monitor.start()` / `monitor.end()` / `monitor.fail()` workflow  

### 11.0 Configuration

11.1 Extend [`trainwatcher/config.py`](E:/Train_Watch/trainwatcher/config.py) for interpretation settings  
11.2 Add interpretation fields:
- `mode`
- `fallback`
- `hosted`
- `byok`

11.3 Default behavior:
- hosted enabled for `hybrid` and `llm`
- fallback = `rule`

11.4 Add env overrides for advanced BYOK use:
- `TRAINWATCHER_LLM_FALLBACK`
- `TRAINWATCHER_LLM_API_KEY`
- `TRAINWATCHER_LLM_BASE_URL`
- `TRAINWATCHER_LLM_MODEL`
- `TRAINWATCHER_LLM_MAX_TOKENS`
- `TRAINWATCHER_LLM_TEMPERATURE`
- `TRAINWATCHER_LLM_TIMEOUT_SECONDS`

11.5 Keep normal users free from LLM configuration

### 12.0 Tests

12.1 Add or extend tests for rules, metrics, best-model, and summaries  
12.2 Add hosted interpretation client tests with mocked backend  
12.3 Add hosted quota-exceeded tests  
12.4 Add BYOK fallback tests  
12.5 Add failure-path tests to confirm fallback behavior  

### 13.0 Documentation

13.1 Update [`README.md`](E:/Train_Watch/README.md) with hosted interpretation flow  
13.2 Add Phase-02 design doc  
13.3 Add examples for:
- `rule` mode
- `hybrid` mode
- `llm` mode
- BYOK fallback
- report generation

13.4 Keep the normal user story simple:
- add email
- run training
- receive interpreted summary

## Execution Order

Recommended execution order:

1. `1.0 Analysis Contract`
2. `2.0 Metrics Extraction`
3. `3.0 Rule Engine`
4. `4.0 Suggestion Engine`
5. `6.0 Summary and Notification Expansion`
6. `5.0 Best Model Summary`
7. `7.0 Hosted Interpretation Backend`
8. `8.0 Optional BYOK Fallback`
9. `9.0 Report Generation`
10. `10.0 Public API`
11. `11.0 Configuration`
12. `12.0 Tests`
13. `13.0 Documentation`

Reason:
- rule-based value ships first
- hosted UX stays simple
- LLM remains an enhancement, not a dependency

## Success Criteria

Phase-02 is successful if TrainWatcher can:

- detect common training patterns using deterministic rules
- suggest next actions without heavy dependencies
- enrich summaries through the hosted TrainWatcher LLM backend
- let advanced users optionally bring their own key only as fallback
- send richer summaries without breaking Phase-01 simplicity
- remain lightweight, pip-installable, and framework-agnostic
