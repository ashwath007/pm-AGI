# Contributing to PM-AGI Benchmark

Thank you for helping make PM-AGI better! Here's how to contribute.

---

## Adding New Questions

1. Fork the repository
2. Open `benchmark/dataset.json`
3. Add your question following the schema below
4. Submit a Pull Request

### Question Schema

```json
{
  "id": "meta_031",
  "category": "meta_ads",
  "subcategory": "bidding_strategy",
  "difficulty": "medium",
  "type": "mcq",
  "question": "Your question text here?",
  "options": {
    "A": "Option A",
    "B": "Option B",
    "C": "Option C",
    "D": "Option D"
  },
  "answer": "B",
  "explanation": "Why B is correct and others are wrong.",
  "tags": ["relevant", "tags"]
}
```

For action-based questions:

```json
{
  "id": "ab_021",
  "category": "action_based",
  "subcategory": "campaign_optimization",
  "difficulty": "hard",
  "type": "action_based",
  "question": "Scenario description here...",
  "answer_criteria": [
    "Key point 1 that a correct answer should include",
    "Key point 2",
    "Key point 3"
  ],
  "explanation": "Overall explanation of the correct approach.",
  "tags": ["relevant", "tags"]
}
```

---

## ID Convention

- Meta Ads: `meta_031`, `meta_032`, ...
- Google Ads: `google_031`, `google_032`, ...
- Critical Thinking: `ct_021`, `ct_022`, ...
- Action-Based: `ab_021`, `ab_022`, ...

---

## Quality Guidelines

- Questions must reflect **current platform best practices** (2024–2025)
- MCQ options must have exactly one clearly correct answer
- Explanations should be educational and cite the reasoning
- Action-based `answer_criteria` should have 5–10 specific, measurable points
- Avoid ambiguous wording — questions should have a clear right/wrong answer
- Tag questions with 2–5 relevant lowercase tags

---

## Submitting Model Results

1. Run: `python evaluate.py --model YOUR_MODEL --provider YOUR_PROVIDER --api-key KEY`
2. Find your result in `results/YOUR_MODEL_timestamp.json`
3. Open a PR adding only your result file
4. Title: `[Result] ModelName vX.X`

---

## Expanding to New Platforms

Future benchmark expansions planned:
- TikTok Ads
- LinkedIn Ads
- Amazon Ads
- Programmatic / DSP

If you want to lead a new platform expansion, open an Issue to discuss.

---

## Code of Conduct

Be respectful. Questions and results should be submitted in good faith.
Do not submit fabricated results.
