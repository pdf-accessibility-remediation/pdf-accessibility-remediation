---
title: Models
nav_order: 6
---

# Models

## Choosing the model

The default is one line near the top of `decide.py`: `DEFAULT_MODEL = 'anthropic/claude-sonnet-5.5'`. Change it to any id from https://openrouter.ai/models. For one run or one batch, put `MODEL=` in front instead:

```bash
# default model (DEFAULT_MODEL in decide.py), with the y/N question
bash run_api.sh ../samples/group1/clans.pdf clans api-run3
# another model for one book, no question
MODEL=openai/gpt-5 AUTO=1 bash run_api.sh ../samples/group1/clans.pdf clans gpt-run1
# the cost estimate only, to see what a model would cost (free)
MODEL=google/gemini-3.8-flash ESTIMATE=1 bash run_api.sh ../samples/group1/clans.pdf clans gem-run1
# the same group with two models, to compare
AUTO=1 bash batch_api.sh g1-sonnet ../samples/group1
MODEL=anthropic/claude-opus-5.5 AUTO=1 bash batch_api.sh g1-opus ../samples/group1
# a bigger output limit as well
MODEL=openai/gpt-5 MAX_TOKENS=32000 AUTO=1 bash batch_api.sh g3-gpt ../samples/group3
# finish the books a batch couldn't (keep the same MODEL as the first try; the summary prints this command)
RETRY=1 MODEL=openai/gpt-5 AUTO=1 bash batch_api.sh g3-gpt ../samples/group3
# the model was rate-limited (429): wait a few minutes, then one book at a time
RETRY=1 JOBS=1 MODEL=openai/gpt-6.1-sol AUTO=1 bash batch_api.sh group1SOL ../samples/group1
# re-apply saved replies for free; each keeps the model that wrote it, so no MODEL= needed
FROM=g1-opus AUTO=1 bash batch_api.sh g1-opus-rerun ../samples/group1
```

Ids that exist on OpenRouter and take images: `anthropic/claude-sonnet-5.5`, `anthropic/claude-opus-5.5`, `google/gemini-3.8-flash`, `openai/gpt-5`.

Before anything is sent, `decide.py` looks the model up on OpenRouter and refuses it if:

- the id is not on OpenRouter
- it cannot take images (the figure crops are part of every request)
- its output limit is under `MAX_TOKENS`
- the request (input estimate + `MAX_TOKENS`) does not fit its context window

**Costs with other models.** The cost estimate uses Claude's token math (calibrated on Sonnet bills), so for any non-Claude model it is marked approximate. The $2 per-book cap, the batch cap and the credit check are not applied to it; the estimate is printed and the request is sent. If your credit is too low, OpenRouter refuses the request (HTTP 402) and nothing is charged. The OpenRouter bill, shown in the review and the summary, is the real cost. With `AUTO=1`, the line printed before sending says which case applies:

```
AUTO=1: sending without asking (decide.py still refuses a Claude estimate over the $2 cap or your credit)
AUTO=1: sending without asking. The $2 cap applies to Claude models only: the openai/gpt-5 estimate is approximate and not capped; the OpenRouter bill is the real cost
```

**Where the model shows:** `review.md` (top line), `record.json` (`run.model`), the batch header and the top of `summary.md`, with the batch start time and the prompt file. `FROM=` and `REPLY=` re-runs keep the model that wrote the saved reply.

If no provider of a model accepts the "don't keep or train on the data" setting, OpenRouter refuses the request before anything is charged, and `decide.py` says so.

## Temperature

One line near the top of `decide.py` sets it for every run: `TEMPERATURE = 0`. There is no command-line override; changing the number changes every run that sends a temperature.

No temperature is sent when the model's maker says to leave it at the default, or the model rejects other values. That is the case when:

- the model id starts with an entry in `OMIT_TEMPERATURE` (in `decide.py`): Opus 4.7 and later, OpenAI reasoning models (`openai/o1`, `o3`, `o4`, `gpt-5`), and `google/gemini-3` (every Gemini 3 model). Add a line there for any other model
- or OpenRouter lists the model as not accepting a temperature setting

Sonnet matches neither, so it gets `0`.

Every new run writes `run.temperature` in `record.json`: the number sent, or `"omitted: …"` with the reason. `FROM=` and `REPLY=` re-runs send nothing, so they keep the original run's value, and add none where the original had none. Records written before this setting existed are not changed (those runs were sent with temperature 0).

If a model that is not on the list, and not flagged by OpenRouter, still rejects the setting, the run stops: OpenRouter charges nothing for the refused request, nothing is retried, and the message says to add the model to `OMIT_TEMPERATURE`.

**Settings recorded in each run:** temperature (`TEMPERATURE`, or omitted as above), `data_collection: deny` (OpenRouter routes only to providers that don't keep or train on the data), at most 48,000 output tokens unless `MAX_TOKENS` says otherwise (a 30-minute wait for the reply); the output tokens are recorded as reasoning and visible (`run.usage.reasoning_tokens`, `visible_tokens`) when OpenRouter reports the split, $2 spending cap per book (Claude models).
