# Citation Correction Bot

**Agentic AI for Analytics — Assignment 1**
Prof. Devon Peticolas | Arjun Varma, Oranich Jamkachornkiat

**Live:** https://citation-bot-7pj7nolpla-uc.a.run.app

---

Paste a citation, get rule-by-rule feedback and a corrected version you can copy straight into your paper.

## How it works

1. **Paste** your in-text citation, reference list entry, or bibliography entry
2. **Select** the style — APA 7th, MLA 9th, or Chicago 17th (Notes & Bibliography)
3. The bot **identifies violations** with specific rule IDs (e.g. APA-4, MLA-1, CHI-B2), quotes the problematic text, and explains what's wrong
4. A final **Corrected citation** block gives you the fixed version, ready to copy-paste

If the citation is already correct, the bot simply confirms: "No violations found."

## Architecture

```
                         ┌─────────────────────────────┐
                         │      Browser (index.html)    │
                         │  Style picker + text input   │
                         └──────────┬──────────────────┘
                                    │ POST /chat
                                    ▼
                         ┌──────────────────────────────┐
                         │        FastAPI (app.py)       │
                         │                              │
                         │  1. check_safety()           │
                         │     ┌──────────────────────┐ │
                         │     │ Rule backstop first  │ │
                         │     │  distress phrase +   │ │
                         │     │  not citation-like   │ │
                         │     │     ──► 988 msg      │ │
                         │     │ else LLM classify    │ │
                         │     │  UNSAFE ──► 988 msg  │ │
                         │     │  SAFE   ──► continue │ │
                         │     └──────────────────────┘ │
                         │                              │
                         │  2. build_initial_messages()  │
                         │     ┌──────────────────────┐ │
                         │     │ System prompt (XML)  │ │
                         │     │  + role/persona      │ │
                         │     │  + scope & rules     │ │
                         │     │  + positive constr.  │ │
                         │     │  + escape hatch      │ │
                         │     │ Few-shot examples    │ │
                         │     │  (3-4 per style)     │ │
                         │     │ Session history      │ │
                         │     └──────────────────────┘ │
                         │               │              │
                         │               ▼              │
                         │     ┌──────────────────────┐ │
                         │     │   LiteLLM → Gemini   │ │
                         │     │   2.5 Flash Lite     │ │
                         │     └──────────┬───────────┘ │
                         │               │              │
                         │               ▼              │
                         │  3. check_response()         │
                         │     ┌──────────────────────┐ │
                         │     │ Contains rule IDs /  │ │
                         │     │ citation language?   │ │
                         │     │  YES ──► return      │ │
                         │     │  NO  ──► redirect    │ │
                         │     │          message     │ │
                         │     └──────────────────────┘ │
                         └──────────┬───────────────────┘
                                    │ JSON response
                                    ▼
                         ┌─────────────────────────────┐
                         │      Browser renders         │
                         │      formatted feedback      │
                         └─────────────────────────────┘
```

## Example

**Input** (APA 7th):

> The research (Smith, Jones, Lee, & Park, 2021) showed that cognitive load matters.

**Output**:

> - APA-3 (et al. for 3+ authors): "(Smith, Jones, Lee, & Park, 2021)" — APA 7th requires "et al." from the first citation.
>
> Corrected citation:
> The research (Smith et al., 2021) showed that cognitive load matters.

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

## Prompting strategy

The system prompt is built dynamically per style and uses structured XML tags for clarity.

- **Role / persona**: The bot is an "expert citation format reviewer" with a precise, collegial tone aimed at students formatting academic papers.
- **Few-shot examples**: 3-4 examples per style (APA, MLA, Chicago) covering violation detection, correct-citation confirmation, and corrected-citation output. Examples are statically defined and injected into the conversation as user/assistant turns.
- **Positive constraints**: The `<positive_constraints>` block defines what the bot *can* do — identify formatting errors, explain rule violations, and provide corrected citations. Scope is limited to citation formatting only.
- **Escape hatch**: When the bot encounters an ambiguous edge case, it says: *"I'm not certain about this case — I'd recommend checking the [style manual] for guidance."*

## Out-of-scope handling

Three out-of-scope categories are defined using positive framing in the `<scope>` block:

1. **Grammar / writing quality** — "I focus on citation formatting; for grammar and style feedback, a writing tutor or tool like Grammarly is a better fit."
2. **Source quality / research methodology** — "I review how sources are cited, not whether they are good sources; for research quality, consult your advisor."
3. **Page layout (margins, fonts, headers)** — "I specialize in citations and references; for page layout and formatting, check your style manual's formatting chapter."

**Python backstop (post-generation):** After every LLM response, a regex check (`check_response`) verifies the output contains citation-related content (rule IDs, "No violations found", "Corrected citation", etc.). If the LLM went off-topic, the response is replaced with a redirect message.

**Safety handling (pre-generation):** Before citation review, `check_safety` runs a deterministic backstop first for high-confidence crisis language such as `kill myself`, `want to die`, `end it all`, and `not worth living`. That backstop is skipped when the message looks like a citation request (for example APA/MLA keywords, author-date patterns, `doi:`, `vol.`, `pp.`, or URLs) so bibliography text that mentions self-harm terms is not blocked accidentally. If the rule layer does not trigger, an LLM safety classifier runs next; `UNSAFE` returns the same crisis-resource message immediately.

## Supported styles

| Style | Edition | Coverage |
|-------|---------|----------|
| APA | 7th | In-text citations (APA-1 through APA-7) and reference list (APA-R1 through APA-R8) |
| MLA | 9th | In-text citations (MLA-1 through MLA-6) and Works Cited (MLA-W1 through MLA-W6) |
| Chicago | 17th | Notes/footnotes (CHI-1 through CHI-6) and bibliography (CHI-B1 through CHI-B6) |

## Evaluation

### Golden dataset (20+ cases)

| Category | Count | What's tested |
|----------|-------|---------------|
| **In-domain** | 10 | Citations with known violations across APA, MLA, and Chicago — each paired with an expected answer |
| **Out-of-scope** | 5 | Grammar help, source evaluation, page layout, essay requests, font questions — expect redirect/refusal |
| **Safety-only** | 8 | Two direct suicidal-intent prompts, two manipulative bypass attempts, two wording variants, and two edge cases with more natural phrasing; all must return the crisis response |

### Three-tier harness

| Tier | Method | What it checks |
|------|--------|----------------|
| **Deterministic rules** (`test_rules.py`) | Regex/keyword matching | Rule IDs appear in responses; out-of-scope inputs get redirected; all 8 safety prompts must return the crisis response |
| **Golden reference** (`test_golden.py`) | Model-as-a-Judge | Bot output scored against hand-written reference answers (1-10 scale, threshold >= 6) |
| **Rubric** (`test_rubric.py`) | Model-as-a-Judge | Bot output scored against weighted criteria: violation ID, quoting, corrected citation, style accuracy (1-10 scale, threshold >= 8) |

Run all evals:

```bash
uv run pytest evals/ -v
```

### Eval results

| Eval | Pass rate | Average score |
|------|-----------|---------------|
| Deterministic rules | 23/23 | — |
| Golden reference (MaaJ) | 10/10 | 9.4/10 |
| Rubric (MaaJ) | 10/10 | 9.7/10 |
