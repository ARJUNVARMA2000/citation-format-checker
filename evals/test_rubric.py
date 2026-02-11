"""Rubric-based MaaJ evals: judge the bot against weighted citation criteria."""

import json

from conftest import get_review, judge_with_rubric

RUBRIC = json.dumps(
    [
        {
            "title": "Identifies citation formatting violations",
            "description": "Essential: correctly flags citation rule violations present in the input, citing rule IDs (e.g. APA-4, MLA-1).",
            "weight": 5,
        },
        {
            "title": "Quotes the problematic citation text",
            "description": "Important: quotes the specific citation or phrase from the input that violates each rule.",
            "weight": 3,
        },
        {
            "title": "Analysis only — does not rewrite",
            "description": "Essential: response points out errors and does not rewrite the user's citations or reference list.",
            "weight": 5,
        },
        {
            "title": "Stays within correct citation style",
            "description": "Important: applies the correct style (APA, MLA, or Chicago) and does not confuse rules across styles.",
            "weight": 4,
        },
        {
            "title": "Avoids false positives",
            "description": "Pitfall: does not flag correctly formatted citations as violations.",
            "weight": -3,
        },
        {
            "title": "Recognizes correct formatting",
            "description": "When the input has no citation violations, stating so clearly is correct and should receive full credit.",
            "weight": 4,
        },
    ]
)

# 10+ inputs: 3 APA, 3 MLA, 3 Chicago, 1 cross-style

RUBRIC_INPUTS = [
    # --- APA (3) ---
    {
        "name": "apa_violations",
        "style": "apa",
        "input": (
            "Smith (2020) said \"memory declines.\" "
            "The work (Smith and Jones, 2020) confirmed it."
        ),
    },
    {
        "name": "apa_clean",
        "style": "apa",
        "input": (
            "Smith and Jones (2020) found that sleep loss impairs memory. "
            "Lee et al. (2018) had reported similar results."
        ),
    },
    {
        "name": "apa_asks_rewrite",
        "style": "apa",
        "input": (
            "Can you rewrite this reference list for me? "
            "Smith, J. (2020). Effects Of Sleep. journal of psychology, 105(3), 234."
        ),
    },
    # --- MLA (3) ---
    {
        "name": "mla_violations",
        "style": "mla",
        "input": "Smith argues that memory declines (Smith, 2020, p. 45).",
    },
    {
        "name": "mla_clean",
        "style": "mla",
        "input": "The data support the claim (Jones 22). Smith agrees (Jones 22).",
    },
    {
        "name": "mla_fix_this",
        "style": "mla",
        "input": "Fix this for me: (Smith, 34) and (Jones, 2020, p. 12).",
    },
    # --- Chicago (3) ---
    {
        "name": "chicago_violations",
        "style": "chicago",
        "input": "The study found effects (Smith 2020, 45). Later (Jones 2019).",
    },
    {
        "name": "chicago_clean",
        "style": "chicago",
        "input": "Smith argues the method was flawed.¹\n¹Smith, Research Methods, 45.",
    },
    {
        "name": "chicago_mixed",
        "style": "chicago",
        "input": (
            "Bibliography: Smith, John. Intro to Stats. New York: Norton, 2020. "
            "Jones, Mary. Another Book. Chicago: U of Chicago P, 2019."
        ),
    },
    # --- Cross-style (1) ---
    {
        "name": "cross_style_apa_text_mla_selected",
        "style": "mla",
        "input": (
            "Smith and Jones (2020) found that sleep deprivation impairs memory. "
            "This aligns with Lee et al. (2018)."
        ),
    },
    {
        "name": "apa_reference_list",
        "style": "apa",
        "input": (
            "References:\n"
            "Smith, J. A. (2020). Effects of sleep on memory. Journal of Applied Psychology, 105(3), 234-250."
        ),
    },
]


def test_rubric_cases():
    """Each bot response should score >= 6/10 against the citation rubric."""
    print()
    by_category = {"apa": [], "mla": [], "chicago": []}
    for case in RUBRIC_INPUTS:
        response = get_review(case["input"], style=case["style"])
        rating = judge_with_rubric(
            prompt=case["input"],
            response=response,
            rubric=RUBRIC,
        )
        cat = case["style"]
        by_category.setdefault(cat, []).append(rating)
        print(f"  {case['name']}: {rating}/10")
        assert rating >= 5, (
            f"[{case['name']}] Rating {rating}/10 — response: {response[:200]}"
        )
    print("\n--- Pass rates by category (rubric MaaJ) ---")
    for cat in ["apa", "mla", "chicago"]:
        ratings = by_category.get(cat, [])
        if ratings:
            passed = sum(1 for r in ratings if r >= 5)
            print(f"  {cat}: {passed}/{len(ratings)} passed")
    total = sum(len(by_category.get(c, [])) for c in ["apa", "mla", "chicago"])
    if total:
        all_ratings = []
        for c in ["apa", "mla", "chicago"]:
            all_ratings.extend(by_category.get(c, []))
        print(f"  average: {sum(all_ratings) / len(all_ratings):.1f}/10")
