#!/usr/bin/env python3
"""Minimal evaluator for MedHorizon multiple-choice predictions.

The script expects benchmark JSONL records with nested `qa` lists and a prediction
file containing one JSON object per question. A prediction item must include `uid`
and either `prediction`, `pred`, or `answer`.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ANSWER_RE = re.compile(r"\b([A-D])\b", re.IGNORECASE)


def normalize_choice(value: Any) -> str:
    """Normalize model output to a single A-D option when possible."""
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    upper = text.upper()
    if upper in {"A", "B", "C", "D"}:
        return upper
    match = ANSWER_RE.search(upper)
    return match.group(1).upper() if match else upper[:1]


def iter_benchmark_questions(path: Path):
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            video_key = record.get("key", f"line_{line_no}")
            dataset = record.get("dataset", "unknown")
            scene_type = record.get("scene_type", "unknown")
            for qa in record.get("qa", []):
                uid = str(qa.get("uid"))
                yield {
                    "uid": uid,
                    "video_key": video_key,
                    "dataset": dataset,
                    "scene_type": scene_type,
                    "task_id": qa.get("task_id", "unknown"),
                    "task_name": qa.get("task_name", "unknown"),
                    "task_class": qa.get("task_class", "unknown"),
                    "category": qa.get("category", "unknown"),
                    "answer": normalize_choice(qa.get("answer")),
                }


def load_predictions(path: Path) -> dict[str, str]:
    predictions: dict[str, str] = {}
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            if "uid" not in item:
                raise ValueError(f"Missing uid in prediction line {line_no}")
            raw = item.get("prediction", item.get("pred", item.get("answer")))
            predictions[str(item["uid"])] = normalize_choice(raw)
    return predictions


def summarize(rows: list[dict[str, Any]], group_key: str | None = None) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    if group_key is None:
        groups["overall"] = rows
    else:
        for row in rows:
            groups[str(row.get(group_key, "unknown"))].append(row)

    output = []
    for name, items in sorted(groups.items()):
        total = len(items)
        correct = sum(int(item["correct"]) for item in items)
        missing = sum(int(item["missing"]) for item in items)
        acc = correct / total if total else 0.0
        output.append({
            "group": name,
            "total": total,
            "correct": correct,
            "missing": missing,
            "accuracy": acc,
        })
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate MedHorizon MCQ predictions.")
    parser.add_argument("--benchmark", required=True, type=Path, help="Path to medhorizon_test.jsonl")
    parser.add_argument("--predictions", required=True, type=Path, help="Prediction JSONL")
    parser.add_argument("--out", type=Path, default=None, help="Optional CSV output path")
    args = parser.parse_args()

    questions = list(iter_benchmark_questions(args.benchmark))
    predictions = load_predictions(args.predictions)

    rows = []
    for q in questions:
        pred = predictions.get(q["uid"], "")
        row = dict(q)
        row["prediction"] = pred
        row["missing"] = pred == ""
        row["correct"] = pred == q["answer"]
        rows.append(row)

    pred_uids = set(predictions)
    gold_uids = {q["uid"] for q in questions}
    extra_predictions = pred_uids - gold_uids

    print(json.dumps(summarize(rows)[0], indent=2))
    print("\nBy task_id")
    for item in summarize(rows, "task_id"):
        print(f"{item['group']:>12s}  acc={item['accuracy']:.4f}  correct={item['correct']}/{item['total']}  missing={item['missing']}")
    print("\nBy dataset")
    for item in summarize(rows, "dataset"):
        print(f"{item['group']:>12s}  acc={item['accuracy']:.4f}  correct={item['correct']}/{item['total']}  missing={item['missing']}")
    if extra_predictions:
        print(f"\nWarning: {len(extra_predictions)} prediction uid(s) are not in the benchmark.")

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["uid", "video_key", "dataset", "scene_type", "task_id", "task_name", "task_class", "category", "answer", "prediction", "correct", "missing"])
            writer.writeheader()
            writer.writerows(rows)
        print(f"\nWrote per-question results to {args.out}")


if __name__ == "__main__":
    main()
