---
license: mit
task_categories:
- question-answering
- text-generation
language:
- en
tags:
- performance-marketing
- meta-ads
- google-ads
- benchmark
- evaluation
- llm-evaluation
- advertising
pretty_name: PM-AGI Benchmark
size_categories:
- n<1K
---

# PM-AGI Benchmark 🎯

**The first open-source LLM benchmark for Performance Marketing.**

Developed by [hawky.ai](https://hawky.ai) — evaluating how well LLMs reason, plan, and act in real-world **Meta Ads** and **Google Ads** scenarios.

## Dataset Summary

PM-AGI contains **100 expert-crafted questions** across 4 categories of performance marketing knowledge:

| Category | Questions | Focus |
|---|---|---|
| Meta Ads | 30 | Campaign structure, targeting, bidding, creative, CAPI, measurement |
| Google Ads | 30 | Search, Smart Bidding, PMax, Quality Score, attribution |
| Critical Thinking | 20 | Data interpretation, budget decisions, competitive analysis |
| Action-Based | 20 | Scenario troubleshooting, optimization, scaling |

## Question Types

- **MCQ** (63 questions) — Single correct answer, scored 1.0 or 0.0
- **Action-Based** (37 questions) — Open scenario evaluated by LLM judge (0.0–1.0)

## Difficulty Distribution

- Easy: 9 questions
- Medium: 50 questions
- Hard: 41 questions

## Usage

```python
from datasets import load_dataset

ds = load_dataset("Hawky-ai/pm-agi-benchmark")
print(ds["test"][0])
```

## Evaluate a Model

```bash
git clone https://github.com/Hawky-ai/pm-AGI
cd pm-agi-benchmark
pip install -r requirements.txt
python evaluate.py --model gpt-4o --provider openai --api-key YOUR_KEY
```

## Leaderboard

🏆 [Live Leaderboard](https://huggingface.co/spaces/Hawky-ai/pm-agi-leaderboard)

## Citation

```bibtex
@misc{pmagi2025,
  title={PM-AGI: A Performance Marketing Benchmark for Large Language Models},
  author={hawky.ai},
  year={2025},
  url={https://huggingface.co/datasets/Hawky-ai/pm-agi-benchmark}
}
```

## License

MIT — see [LICENSE](https://github.com/Hawky-ai/pm-AGI/blob/main/LICENSE)
