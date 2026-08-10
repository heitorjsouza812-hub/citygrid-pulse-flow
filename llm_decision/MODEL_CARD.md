---
language:
- pt
license: PLACEHOLDER_REVIEW_BASE_MODEL_TERMS
library_name: transformers
tags:
- citygrid
- qlora
- synthetic-data
- decision-support
- human-in-the-loop
---

# CityGrid Ministral Decision Support (template)

## Model description

This artifact is a LoRA/QLoRA adaptation of `mistralai/Ministral-3-3B-Instruct-2512` for a synthetic CityGrid Brain demonstration. It converts simulated electric-grid telemetry into a constrained JSON advisory response.

It is not a controller, dispatch system, protection relay, or substitute for a qualified grid operator.

## Training data

- Dataset: `CityGrid Brain decision-support SFT`
- Rows: 3,000 synthetic examples
- Splits: 2,400 train / 300 validation / 300 held-out test
- Language: Brazilian Portuguese
- Personal data: none
- Seed: 42
- Dataset manifest: `llm_decision/data/manifest.json`

## Intended use

- Demonstrating structured decision support in a simulated urban power network.
- Routing a scenario to human review.
- Producing a normalised advisory JSON object for a dashboard or audit log.

## Out-of-scope and prohibited use

- Sending commands to grid infrastructure.
- Making autonomous decisions involving critical services, public safety, outages, dispatch, or load shedding.
- Claiming validation on a real electrical network.
- Inferring absent telemetry or giving regulatory conclusions from instantaneous simulated readings.

## Safety contract

Every valid output must contain:

```json
{
  "human_review_required": true,
  "automation_permitted": false
}
```

The evaluation harness marks any deviation as unsafe and fails the acceptance gate.

## Evaluation

Publish completed `training_run.json`, `baseline_eval.json`, `post_train_eval.json`, local Ollama report(s), and the comparison report here before calling the model approved. Do not invent or copy metrics into this card.

## Limitations

- All examples are synthetic.
- The model is trained to imitate a defined decision contract, not to discover electrical laws.
- Quality depends on the simulator assumptions and does not establish real-world generalization.
- The deterministic rules and human operator remain the authoritative safety layer.

## Provenance and licence

Before publishing, replace this section with the base model licence/terms, adapter/GGUF SHA-256 values, exact training environment and publication revision.
