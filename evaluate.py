#!/usr/bin/env python3
"""
PM-AGI Benchmark Evaluator
Evaluate any LLM on the Performance Marketing benchmark.

Usage:
  python evaluate.py --model gpt-4o --provider openai --api-key YOUR_KEY
  python evaluate.py --model claude-opus-4-6 --provider anthropic --api-key YOUR_KEY
  python evaluate.py --model llama-3.3-70b --provider openai-compatible --base-url URL --api-key KEY
"""

import argparse
import json
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

# ─── Argument Parser ──────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(description="PM-AGI Benchmark Evaluator")
    parser.add_argument("--model", required=True, help="Model name/ID to evaluate")
    parser.add_argument("--provider", required=True,
                        choices=["openai", "anthropic", "openai-compatible"],
                        help="API provider")
    parser.add_argument("--api-key", default=None, help="API key (or set env var)")
    parser.add_argument("--base-url", default=None, help="Base URL for openai-compatible endpoints")
    parser.add_argument("--category", default=None,
                        choices=["meta_ads", "google_ads", "critical_thinking", "action_based"],
                        help="Run only a specific category")
    parser.add_argument("--difficulty", default=None,
                        choices=["easy", "medium", "hard"],
                        help="Filter by difficulty")
    parser.add_argument("--type", default=None,
                        choices=["mcq", "open_ended", "action_based"],
                        help="Filter by question type")
    parser.add_argument("--judge-model", default=None,
                        help="Model to use as judge for open-ended questions (defaults to same model)")
    parser.add_argument("--judge-provider", default=None,
                        help="Provider for judge model (defaults to same provider)")
    parser.add_argument("--output-dir", default="results",
                        help="Directory to save results (default: results/)")
    parser.add_argument("--dataset", default="benchmark/dataset.json",
                        help="Path to dataset file")
    parser.add_argument("--max-questions", type=int, default=None,
                        help="Limit number of questions (for testing)")
    parser.add_argument("--verbose", action="store_true",
                        help="Print each question and answer during evaluation")
    return parser.parse_args()


# ─── LLM Client ───────────────────────────────────────────────────────────────

class LLMClient:
    def __init__(self, model: str, provider: str, api_key: str, base_url: str = None):
        self.model = model
        self.provider = provider
        self.api_key = api_key
        self.base_url = base_url
        self._client = None
        self._init_client()

    def _init_client(self):
        if self.provider == "anthropic":
            try:
                import anthropic
                self._client = anthropic.Anthropic(api_key=self.api_key)
            except ImportError:
                raise ImportError("Install anthropic: pip install anthropic")
        elif self.provider in ("openai", "openai-compatible"):
            try:
                import openai
                kwargs = {"api_key": self.api_key}
                if self.base_url:
                    kwargs["base_url"] = self.base_url
                self._client = openai.OpenAI(**kwargs)
            except ImportError:
                raise ImportError("Install openai: pip install openai")

    def complete(self, prompt: str, system: str = None, max_tokens: int = 1024) -> str:
        for attempt in range(3):
            try:
                if self.provider == "anthropic":
                    kwargs = {
                        "model": self.model,
                        "max_tokens": max_tokens,
                        "messages": [{"role": "user", "content": prompt}]
                    }
                    if system:
                        kwargs["system"] = system
                    response = self._client.messages.create(**kwargs)
                    return response.content[0].text.strip()
                else:
                    messages = []
                    if system:
                        messages.append({"role": "system", "content": system})
                    messages.append({"role": "user", "content": prompt})
                    response = self._client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        max_tokens=max_tokens,
                        temperature=0
                    )
                    return response.choices[0].message.content.strip()
            except Exception as e:
                if attempt < 2:
                    print(f"  Retry {attempt + 1}/3 due to: {e}")
                    time.sleep(2 ** attempt)
                else:
                    print(f"  Failed after 3 attempts: {e}")
                    return ""
        return ""


# ─── Prompt Templates ─────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an expert performance marketer with deep knowledge of Meta Ads (Facebook/Instagram) and Google Ads.
Answer questions accurately and concisely based on current platform best practices."""

MCQ_PROMPT = """Answer the following multiple choice question about performance marketing.

Question: {question}

Options:
A) {option_a}
B) {option_b}
C) {option_c}
D) {option_d}

Respond with ONLY the letter of the correct answer (A, B, C, or D). Do not explain."""

OPEN_ENDED_PROMPT = """Answer the following performance marketing question thoroughly and accurately.

Question: {question}

Provide a detailed, actionable answer."""

ACTION_BASED_PROMPT = """You are a senior performance marketer. Answer the following scenario-based question with specific, actionable recommendations.

Scenario: {question}

Provide a comprehensive answer with specific actions, reasoning, and best practices."""

JUDGE_PROMPT = """You are an expert performance marketing evaluator. Score the following answer against the evaluation criteria.

QUESTION: {question}

EVALUATION CRITERIA (key points that should be covered):
{criteria}

CANDIDATE ANSWER:
{answer}

Score the answer from 0.0 to 1.0 based on:
- 1.0: All key criteria addressed correctly and completely
- 0.7-0.9: Most key criteria covered with minor gaps
- 0.4-0.6: Some criteria covered but significant gaps
- 0.1-0.3: Minimal correct content
- 0.0: Incorrect or no relevant content

Respond with ONLY a number between 0.0 and 1.0. No explanation."""


# ─── Evaluation Logic ─────────────────────────────────────────────────────────

def evaluate_mcq(model_answer: str, correct_answer: str) -> float:
    """Score an MCQ answer. Returns 1.0 or 0.0."""
    # Extract just the letter from the model's response
    match = re.search(r'\b([ABCD])\b', model_answer.upper()[:50])
    if match:
        return 1.0 if match.group(1) == correct_answer.upper() else 0.0
    return 0.0


def evaluate_open_ended(question: dict, model_answer: str, judge_client: LLMClient) -> float:
    """Score an open-ended or action_based answer using LLM-as-judge."""
    criteria = question.get("answer_criteria", [])
    if not criteria:
        criteria = [question.get("explanation", "")]

    criteria_text = "\n".join(f"- {c}" for c in criteria)
    prompt = JUDGE_PROMPT.format(
        question=question["question"],
        criteria=criteria_text,
        answer=model_answer
    )
    score_str = judge_client.complete(prompt, max_tokens=10)
    try:
        score = float(re.search(r'[\d.]+', score_str).group())
        return max(0.0, min(1.0, score))
    except (AttributeError, ValueError):
        return 0.0


def get_model_answer(question: dict, client: LLMClient) -> str:
    """Get the model's answer for a question."""
    q_type = question["type"]

    if q_type == "mcq":
        options = question.get("options", {})
        prompt = MCQ_PROMPT.format(
            question=question["question"],
            option_a=options.get("A", ""),
            option_b=options.get("B", ""),
            option_c=options.get("C", ""),
            option_d=options.get("D", "")
        )
    elif q_type == "action_based":
        prompt = ACTION_BASED_PROMPT.format(question=question["question"])
    else:
        prompt = OPEN_ENDED_PROMPT.format(question=question["question"])

    return client.complete(prompt, system=SYSTEM_PROMPT, max_tokens=800)


# ─── Main Evaluator ───────────────────────────────────────────────────────────

def load_dataset(dataset_path: str, filters: dict) -> list:
    """Load and filter the benchmark dataset."""
    with open(dataset_path, "r") as f:
        # Remove JS-style comments before parsing
        content = f.read()
        content = re.sub(r'//.*?\n', '\n', content)
        data = json.loads(content)

    questions = data["questions"]

    if filters.get("category"):
        questions = [q for q in questions if q["category"] == filters["category"]]
    if filters.get("difficulty"):
        questions = [q for q in questions if q["difficulty"] == filters["difficulty"]]
    if filters.get("type"):
        questions = [q for q in questions if q["type"] == filters["type"]]
    if filters.get("max_questions"):
        questions = questions[:filters["max_questions"]]

    return questions


def run_evaluation(args) -> dict:
    """Run the full benchmark evaluation."""
    print(f"\n{'='*60}")
    print(f"  PM-AGI Benchmark Evaluation")
    print(f"  Model: {args.model}")
    print(f"  Provider: {args.provider}")
    print(f"{'='*60}\n")

    # Resolve API key
    api_key = args.api_key or os.environ.get("OPENAI_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("Provide --api-key or set OPENAI_API_KEY / ANTHROPIC_API_KEY env var")

    # Init model client
    client = LLMClient(
        model=args.model,
        provider=args.provider,
        api_key=api_key,
        base_url=args.base_url
    )

    # Init judge client (defaults to same model)
    judge_model = args.judge_model or args.model
    judge_provider = args.judge_provider or args.provider
    judge_key = api_key  # simplification: use same key
    judge_client = LLMClient(
        model=judge_model,
        provider=judge_provider,
        api_key=judge_key,
        base_url=args.base_url
    )

    # Load dataset
    filters = {
        "category": args.category,
        "difficulty": args.difficulty,
        "type": getattr(args, "type", None),
        "max_questions": args.max_questions
    }
    questions = load_dataset(args.dataset, filters)
    print(f"Loaded {len(questions)} questions\n")

    # Run evaluation
    results = []
    category_scores = {}
    total_score = 0.0

    for i, question in enumerate(questions):
        q_id = question["id"]
        q_type = question["type"]
        category = question["category"]
        difficulty = question["difficulty"]

        print(f"[{i+1:3d}/{len(questions)}] {q_id} ({q_type}, {difficulty})...", end=" ", flush=True)

        # Get model answer
        model_answer = get_model_answer(question, client)

        # Score
        if q_type == "mcq":
            score = evaluate_mcq(model_answer, question["answer"])
        else:
            score = evaluate_open_ended(question, model_answer, judge_client)

        # Track
        total_score += score
        if category not in category_scores:
            category_scores[category] = {"total": 0.0, "count": 0}
        category_scores[category]["total"] += score
        category_scores[category]["count"] += 1

        result = {
            "id": q_id,
            "category": category,
            "subcategory": question.get("subcategory"),
            "difficulty": difficulty,
            "type": q_type,
            "score": score,
            "model_answer": model_answer,
            "correct_answer": question.get("answer") or "See answer_criteria",
            "explanation": question.get("explanation", "")
        }
        results.append(result)

        status = "✓" if score >= 0.7 else ("~" if score >= 0.4 else "✗")
        print(f"{status} {score:.2f}")

        if args.verbose:
            print(f"  Q: {question['question'][:100]}...")
            print(f"  A: {model_answer[:200]}...")
            print()

    # Compute summary
    overall_score = total_score / len(questions) if questions else 0.0
    category_summary = {
        cat: {
            "score": v["total"] / v["count"],
            "count": v["count"],
            "percentage": f"{(v['total'] / v['count']) * 100:.1f}%"
        }
        for cat, v in category_scores.items()
    }

    # Difficulty breakdown
    difficulty_scores = {}
    for r in results:
        d = r["difficulty"]
        if d not in difficulty_scores:
            difficulty_scores[d] = {"total": 0.0, "count": 0}
        difficulty_scores[d]["total"] += r["score"]
        difficulty_scores[d]["count"] += 1
    difficulty_summary = {
        d: {
            "score": v["total"] / v["count"],
            "percentage": f"{(v['total'] / v['count']) * 100:.1f}%"
        }
        for d, v in difficulty_scores.items()
    }

    # Final report object
    report = {
        "benchmark": "PM-AGI Benchmark v1.0.0",
        "model": args.model,
        "provider": args.provider,
        "evaluated_at": datetime.utcnow().isoformat() + "Z",
        "total_questions": len(questions),
        "overall_score": round(overall_score, 4),
        "overall_percentage": f"{overall_score * 100:.1f}%",
        "category_scores": category_summary,
        "difficulty_scores": difficulty_summary,
        "results": results
    }

    # Print summary
    print(f"\n{'='*60}")
    print(f"  RESULTS: {args.model}")
    print(f"{'='*60}")
    print(f"  Overall Score: {overall_score * 100:.1f}%")
    print()
    print("  By Category:")
    for cat, info in category_summary.items():
        print(f"    {cat:<25} {info['percentage']:>6}  ({info['count']} questions)")
    print()
    print("  By Difficulty:")
    for diff, info in difficulty_summary.items():
        print(f"    {diff:<15} {info['percentage']:>6}")
    print(f"{'='*60}\n")

    return report


def save_results(report: dict, output_dir: str, model_name: str):
    """Save results to JSON file."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', model_name)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"{safe_name}_{timestamp}.json"
    filepath = Path(output_dir) / filename

    with open(filepath, "w") as f:
        json.dump(report, f, indent=2)

    print(f"Results saved to: {filepath}")
    print(f"\nTo submit to the leaderboard, open a PR adding this file to the results/ directory.")
    return filepath


# ─── Entry Point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    args = parse_args()
    report = run_evaluation(args)
    save_results(report, args.output_dir, args.model)
