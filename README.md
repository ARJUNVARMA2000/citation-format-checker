# Citation Correction Bot

Paste a citation, get rule-by-rule feedback and a corrected version you can copy straight into your paper.

## How it works

1. **Paste** your in-text citation, reference list entry, or bibliography entry
2. **Select** the style — APA 7th, MLA 9th, or Chicago 17th (Notes & Bibliography)
3. The bot **identifies violations** with specific rule IDs (e.g. APA-4, MLA-1, CHI-B2), quotes the problematic text, and explains what's wrong
4. A final **Corrected citation** block gives you the fixed version, ready to copy-paste

If the citation is already correct, the bot simply confirms: "No violations found."

## Example

**Input** (APA 7th):

> The research (Smith, Jones, Lee, & Park, 2021) showed that cognitive load matters.

**Output**:

> - APA-3 (et al. for 3+ authors): "(Smith, Jones, Lee, & Park, 2021)" — APA 7th requires "et al." from the first citation.
>
> Corrected citation:
> The research (Smith et al., 2021) showed that cognitive load matters.

## Live URL

**https://citation-bot-7pj7nolpla-uc.a.run.app**

## Running locally

```bash
uv run python app.py
```

Open http://localhost:8000, select a citation style, paste your text, and click **Check**.

Requires a `.env` with Vertex AI credentials:

```
VERTEXAI_PROJECT=your-project-id
VERTEXAI_LOCATION=us-central1
```

## Supported styles

| Style | Edition | Coverage |
|-------|---------|----------|
| APA | 7th | In-text citations (APA-1 through APA-7) and reference list (APA-R1 through APA-R8) |
| MLA | 9th | In-text citations (MLA-1 through MLA-6) and Works Cited (MLA-W1 through MLA-W6) |
| Chicago | 17th | Notes/footnotes (CHI-1 through CHI-6) and bibliography (CHI-B1 through CHI-B6) |

## Evaluation

The bot is evaluated with a three-tier harness:

| Tier | Method | What it checks |
|------|--------|----------------|
| **Deterministic rules** (`test_rules.py`) | Regex/keyword matching | Rule IDs appear in responses; out-of-scope inputs get redirected; safety triggers work |
| **Golden reference** (`test_golden.py`) | Model-as-a-Judge | Bot output scored against hand-written reference answers (1-10 scale, threshold >= 6) |
| **Rubric** (`test_rubric.py`) | Model-as-a-Judge | Bot output scored against weighted criteria: violation ID, quoting, corrected citation, style accuracy (1-10 scale, threshold >= 5) |

Run all evals:

```bash
uv run pytest evals/ -v
```

### Eval results

| Eval | Pass rate | Average score |
|------|-----------|---------------|
| Deterministic rules | 20/20 | — |
| Golden reference (MaaJ) | 10/10 | 9.9/10 |
| Rubric (MaaJ) | 11/11 | 9.8/10 |
