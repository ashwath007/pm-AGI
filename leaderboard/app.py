"""
PM-AGI Leaderboard — Hugging Face Space
Gradio app showing LLM rankings on the Performance Marketing benchmark.
"""

import json
import os
from pathlib import Path
from datetime import datetime

import gradio as gr
import pandas as pd

# ─── Load Results ─────────────────────────────────────────────────────────────

RESULTS_DIR = Path(__file__).parent / "results"
DATASET_PATH = Path(__file__).parent / "benchmark" / "dataset.json"

CATEGORY_LABELS = {
    "meta_ads": "Meta Ads",
    "google_ads": "Google Ads",
    "critical_thinking": "Critical Thinking",
    "action_based": "Action-Based",
}

DIFFICULTY_EMOJI = {"easy": "🟢", "medium": "🟡", "hard": "🔴"}

MEDAL = {0: "🥇", 1: "🥈", 2: "🥉"}


def load_all_results() -> list[dict]:
    results = []
    if not RESULTS_DIR.exists():
        return results
    for f in sorted(RESULTS_DIR.glob("*.json")):
        try:
            with open(f) as fh:
                data = json.load(fh)
            results.append(data)
        except Exception:
            pass
    return results


def build_leaderboard_df(results: list[dict]) -> pd.DataFrame:
    if not results:
        return pd.DataFrame(columns=["Rank", "Model", "Overall", "Meta Ads", "Google Ads", "Critical Thinking", "Action-Based", "Evaluated"])

    rows = []
    for r in results:
        cat = r.get("category_scores", {})
        row = {
            "Model": r.get("model", "Unknown"),
            "Overall": round(r.get("overall_score", 0) * 100, 1),
            "Meta Ads": round(cat.get("meta_ads", {}).get("score", 0) * 100, 1),
            "Google Ads": round(cat.get("google_ads", {}).get("score", 0) * 100, 1),
            "Critical Thinking": round(cat.get("critical_thinking", {}).get("score", 0) * 100, 1),
            "Action-Based": round(cat.get("action_based", {}).get("score", 0) * 100, 1),
            "Evaluated": r.get("evaluated_at", "")[:10],
            "Questions": r.get("total_questions", 0),
        }
        rows.append(row)

    df = pd.DataFrame(rows).sort_values("Overall", ascending=False).reset_index(drop=True)
    df.insert(0, "Rank", [MEDAL.get(i, f"#{i+1}") for i in range(len(df))])
    df["Overall"] = df["Overall"].apply(lambda x: f"{x}%")
    df["Meta Ads"] = df["Meta Ads"].apply(lambda x: f"{x}%")
    df["Google Ads"] = df["Google Ads"].apply(lambda x: f"{x}%")
    df["Critical Thinking"] = df["Critical Thinking"].apply(lambda x: f"{x}%")
    df["Action-Based"] = df["Action-Based"].apply(lambda x: f"{x}%")
    return df


def build_category_df(results: list[dict], category: str) -> pd.DataFrame:
    if not results:
        return pd.DataFrame()
    rows = []
    for r in results:
        cat_data = r.get("category_scores", {}).get(category, {})
        if cat_data:
            rows.append({
                "Model": r.get("model", "Unknown"),
                "Score": f"{round(cat_data.get('score', 0) * 100, 1)}%",
                "Questions": cat_data.get("count", 0),
            })
    df = pd.DataFrame(rows).sort_values("Score", ascending=False).reset_index(drop=True)
    df.insert(0, "Rank", [MEDAL.get(i, f"#{i+1}") for i in range(len(df))])
    return df


def load_dataset_stats():
    try:
        import re
        with open(DATASET_PATH) as f:
            content = f.read()
        content = re.sub(r'//.*?\n', '\n', content)
        data = json.loads(content)
        questions = data.get("questions", [])
        total = len(questions)
        by_cat = {}
        by_diff = {}
        by_type = {}
        for q in questions:
            by_cat[q["category"]] = by_cat.get(q["category"], 0) + 1
            by_diff[q["difficulty"]] = by_diff.get(q["difficulty"], 0) + 1
            by_type[q["type"]] = by_type.get(q["type"], 0) + 1
        return total, by_cat, by_diff, by_type
    except Exception:
        return 0, {}, {}, {}


# ─── Gradio App ───────────────────────────────────────────────────────────────

DESCRIPTION = """
# 🎯 PM-AGI Leaderboard

**The first open-source LLM benchmark for Performance Marketing.**

Developed by [hawky.ai](https://hawky.ai) — evaluating how well LLMs reason, plan, and act in real-world **Meta Ads** and **Google Ads** scenarios.

📦 [Dataset on Hugging Face](https://huggingface.co/datasets/hawky-ai/pm-agi-benchmark) &nbsp;|&nbsp;
💻 [GitHub](https://github.com/Hawky-ai/pm-AGI) &nbsp;|&nbsp;
📖 [How to Submit](https://github.com/Hawky-ai/pm-AGI#submitting-results-to-the-leaderboard)
"""

SUBMIT_GUIDE = """
## How to Submit Your Model

1. Clone the repo:
```bash
git clone https://github.com/Hawky-ai/pm-AGI
cd pm-agi-benchmark
pip install -r requirements.txt
```

2. Run evaluation:
```bash
python evaluate.py --model YOUR_MODEL --provider openai --api-key YOUR_KEY
```

3. Open a Pull Request adding your `results/YOUR_MODEL_timestamp.json` file to the repo.

Your model will appear on the leaderboard after the PR is merged.

---
**Supported Providers:** OpenAI, Anthropic, any OpenAI-compatible endpoint (Together AI, Fireworks, Ollama, etc.)
"""

ABOUT = """
## About PM-AGI Benchmark

PM-AGI evaluates LLMs across **4 critical dimensions** of performance marketing:

| Category | # Questions | Focus |
|---|---|---|
| 🟦 **Meta Ads** | 30 | Campaign structure, targeting, bidding, creative, measurement, CAPI |
| 🟩 **Google Ads** | 30 | Search, Smart Bidding, PMax, Quality Score, attribution |
| 🟨 **Critical Thinking** | 20 | Data analysis, budget decisions, competitive strategy |
| 🟥 **Action-Based** | 20 | Scenario troubleshooting, optimization, scaling decisions |

### Question Types
- **MCQ** — Single correct answer, scored 1.0/0.0
- **Action-Based** — Open scenario, scored 0.0–1.0 by LLM judge against expert rubric

### Scoring
All scores normalized to 0–100%. Overall = weighted average across all categories.

---
*Built with ❤️ by [hawky.ai](https://hawky.ai). MIT License.*
"""


def create_app():
    total_q, by_cat, by_diff, by_type = load_dataset_stats()

    with gr.Blocks(
        title="PM-AGI Leaderboard | hawky.ai",
        theme=gr.themes.Soft(primary_hue="blue"),
        css="""
        .stat-card { text-align: center; padding: 16px; border-radius: 8px; background: #f8fafc; }
        .stat-number { font-size: 2em; font-weight: bold; color: #1e40af; }
        .stat-label { font-size: 0.9em; color: #64748b; margin-top: 4px; }
        footer { display: none !important; }
        """
    ) as app:

        gr.Markdown(DESCRIPTION)

        # Stats row
        with gr.Row():
            gr.HTML(f"""
            <div class="stat-card">
                <div class="stat-number">{total_q}</div>
                <div class="stat-label">Total Questions</div>
            </div>""")
            gr.HTML(f"""
            <div class="stat-card">
                <div class="stat-number">{by_cat.get('meta_ads', 0) + by_cat.get('google_ads', 0)}</div>
                <div class="stat-label">Platform Questions</div>
            </div>""")
            gr.HTML(f"""
            <div class="stat-card">
                <div class="stat-number">{by_diff.get('hard', 0)}</div>
                <div class="stat-label">Hard Questions</div>
            </div>""")
            gr.HTML(f"""
            <div class="stat-card">
                <div class="stat-number">4</div>
                <div class="stat-label">Categories</div>
            </div>""")

        with gr.Tabs():

            # ── Leaderboard Tab ──
            with gr.Tab("🏆 Leaderboard"):
                gr.Markdown("### Overall Rankings")
                gr.Markdown("*Scores represent percentage of correct/well-answered questions across all categories.*")

                refresh_btn = gr.Button("🔄 Refresh Leaderboard", size="sm", variant="secondary")

                leaderboard_table = gr.DataFrame(
                    value=build_leaderboard_df(load_all_results()),
                    interactive=False,
                    wrap=True
                )

                def refresh_leaderboard():
                    return build_leaderboard_df(load_all_results())

                refresh_btn.click(refresh_leaderboard, outputs=leaderboard_table)

            # ── Category Breakdown Tab ──
            with gr.Tab("📊 Category Breakdown"):
                gr.Markdown("### Performance by Category")

                with gr.Row():
                    with gr.Column():
                        gr.Markdown("#### 🟦 Meta Ads")
                        meta_table = gr.DataFrame(
                            value=build_category_df(load_all_results(), "meta_ads"),
                            interactive=False
                        )
                    with gr.Column():
                        gr.Markdown("#### 🟩 Google Ads")
                        google_table = gr.DataFrame(
                            value=build_category_df(load_all_results(), "google_ads"),
                            interactive=False
                        )

                with gr.Row():
                    with gr.Column():
                        gr.Markdown("#### 🟨 Critical Thinking")
                        ct_table = gr.DataFrame(
                            value=build_category_df(load_all_results(), "critical_thinking"),
                            interactive=False
                        )
                    with gr.Column():
                        gr.Markdown("#### 🟥 Action-Based")
                        ab_table = gr.DataFrame(
                            value=build_category_df(load_all_results(), "action_based"),
                            interactive=False
                        )

            # ── Submit Tab ──
            with gr.Tab("📤 Submit Your Model"):
                gr.Markdown(SUBMIT_GUIDE)

            # ── About Tab ──
            with gr.Tab("ℹ️ About"):
                gr.Markdown(ABOUT)

        gr.HTML("""
        <div style="text-align:center; padding: 16px; color: #94a3b8; font-size: 0.85em;">
            PM-AGI Benchmark by <a href="https://hawky.ai" target="_blank">hawky.ai</a> &nbsp;|&nbsp;
            MIT License &nbsp;|&nbsp;
            <a href="https://github.com/Hawky-ai/pm-AGI" target="_blank">GitHub</a>
        </div>
        """)

    return app


if __name__ == "__main__":
    app = create_app()
    app.launch()
