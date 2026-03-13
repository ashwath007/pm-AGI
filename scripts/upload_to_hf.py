#!/usr/bin/env python3
"""
Upload PM-AGI benchmark dataset to Hugging Face Hub.

Usage:
  python scripts/upload_to_hf.py --token YOUR_HF_TOKEN --repo hawky-ai/pm-agi-benchmark
"""

import argparse
import json
import re
import os
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(description="Upload PM-AGI dataset to Hugging Face")
    parser.add_argument("--token", default=os.environ.get("HF_TOKEN"), help="Hugging Face API token")
    parser.add_argument("--repo", default="hawky-ai/pm-agi-benchmark", help="HF dataset repo ID")
    parser.add_argument("--dataset", default="benchmark/dataset.json", help="Path to dataset")
    return parser.parse_args()


def load_dataset(path: str) -> dict:
    with open(path) as f:
        content = f.read()
    content = re.sub(r'//.*?\n', '\n', content)
    return json.loads(content)


def upload_dataset(args):
    try:
        from datasets import Dataset, DatasetDict
        from huggingface_hub import HfApi
    except ImportError:
        raise ImportError("Install: pip install datasets huggingface_hub")

    print(f"Loading dataset from {args.dataset}...")
    data = load_dataset(args.dataset)
    questions = data["questions"]

    # Normalize for HF datasets (no nested dicts with variable keys)
    rows = []
    for q in questions:
        row = {
            "id": q["id"],
            "category": q["category"],
            "subcategory": q.get("subcategory", ""),
            "difficulty": q["difficulty"],
            "type": q["type"],
            "question": q["question"],
            "option_a": q.get("options", {}).get("A", ""),
            "option_b": q.get("options", {}).get("B", ""),
            "option_c": q.get("options", {}).get("C", ""),
            "option_d": q.get("options", {}).get("D", ""),
            "answer": q.get("answer", ""),
            "answer_criteria": json.dumps(q.get("answer_criteria", [])),
            "explanation": q.get("explanation", ""),
            "tags": json.dumps(q.get("tags", [])),
        }
        rows.append(row)

    # Create HF Dataset
    hf_dataset = Dataset.from_list(rows)
    dataset_dict = DatasetDict({"test": hf_dataset})

    print(f"Uploading {len(rows)} questions to {args.repo}...")
    dataset_dict.push_to_hub(
        args.repo,
        token=args.token,
        commit_message="Upload PM-AGI benchmark dataset v1.0.0"
    )
    print(f"\n✅ Dataset uploaded: https://huggingface.co/datasets/{args.repo}")


def upload_space(args):
    """Upload the leaderboard Gradio app as a HF Space."""
    try:
        from huggingface_hub import HfApi
    except ImportError:
        raise ImportError("Install: pip install huggingface_hub")

    api = HfApi(token=args.token)
    space_repo = args.repo.replace("datasets/", "").replace(
        "hawky-ai/pm-agi-benchmark", "hawky-ai/pm-agi-leaderboard"
    )

    space_files = [
        ("leaderboard/app.py", "app.py"),
        ("leaderboard/requirements.txt", "requirements.txt"),
        ("README.md", "README.md"),
    ]

    # Create space if not exists
    try:
        api.create_repo(
            repo_id=space_repo,
            repo_type="space",
            space_sdk="gradio",
            exist_ok=True
        )
        print(f"Space repo ready: {space_repo}")
    except Exception as e:
        print(f"Space creation note: {e}")

    for local_path, hf_path in space_files:
        if Path(local_path).exists():
            api.upload_file(
                path_or_fileobj=local_path,
                path_in_repo=hf_path,
                repo_id=space_repo,
                repo_type="space",
                commit_message=f"Upload {hf_path}"
            )
            print(f"  Uploaded: {local_path} → {hf_path}")

    # Upload results directory
    results_dir = Path("results")
    if results_dir.exists():
        for result_file in results_dir.glob("*.json"):
            api.upload_file(
                path_or_fileobj=str(result_file),
                path_in_repo=f"results/{result_file.name}",
                repo_id=space_repo,
                repo_type="space",
                commit_message=f"Upload result: {result_file.name}"
            )
            print(f"  Uploaded result: {result_file.name}")

    print(f"\n✅ Space uploaded: https://huggingface.co/spaces/{space_repo}")


if __name__ == "__main__":
    args = parse_args()
    if not args.token:
        raise ValueError("Provide --token or set HF_TOKEN env var")

    print("=== PM-AGI Hugging Face Upload ===\n")
    upload_dataset(args)
    upload_space(args)
    print("\nDone! Both dataset and leaderboard Space are live on Hugging Face.")
