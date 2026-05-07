# MedHorizon Evaluation

This repository provides a minimal evaluation script for MedHorizon multiple-choice predictions.
It is intended for anonymous NeurIPS review and contains only lightweight evaluation code.

## Files

- `evaluate_medhorizon.py`: computes overall, task-wise, and dataset-wise accuracy.
- `examples/predictions_example.jsonl`: example prediction format.
- `requirements.txt`: minimal Python dependency note.

## Prediction Format

The evaluator expects one JSON object per question:

```json
{"uid": 0, "prediction": "A"}
{"uid": 1, "prediction": "C"}
```

The prediction key can be one of `prediction`, `pred`, or `answer`. The value is normalized to a single `A`/`B`/`C`/`D` option when possible.

## Usage

```bash
python evaluate_medhorizon.py \
  --benchmark /path/to/medhorizon_test.jsonl \
  --predictions /path/to/predictions.jsonl \
  --out results/per_question.csv
```

The benchmark JSONL should follow the released MedHorizon schema: one video record per line with a nested `qa` list. Each QA item must include at least `uid` and `answer`.

## Metrics

The script reports:

- overall accuracy
- accuracy by `task_id`
- accuracy by source `dataset`
- missing prediction count

Accuracy is computed as exact match between the normalized predicted option and the gold answer option.

## Notes

This repository does not contain model code or clinical data. It only provides a simple scoring utility for reproducing the benchmark accuracy calculation from released predictions.
