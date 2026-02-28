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
            "title": "Provides a corrected citation at the end",
            "description": "Essential: when violations are found, the response includes a final corrected version of the citation that the user can copy-paste directly.",
            "weight": 5,
        },
        {
            "title": "Corrected citation is accurate",
            "description": "Important: the corrected version actually fixes all identified violations and follows the rules of the selected style.",
            "weight": 4,
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
            "description": "When the input has no citation violations, stating so clearly is correct and should receive full credit. No corrected citation block needed.",
            "weight": 4,
        },
    ]
)

# Mirrored to the golden eval inputs so both suites cover the same scenarios.

RUBRIC_INPUTS = [
    # --- APA (4) ---
    {
        "name": "apa_direct_quote_no_page",
        "style": "apa",
        "input": (
            'According to Smith (2020), "the results were significant" and '
            "the study confirmed earlier findings (Jones & Lee, 2019)."
        ),
    },
    {
        "name": "apa_clean",
        "style": "apa",
        "input": (
            "Smith and Jones (2020) found that sleep deprivation impairs "
            "memory. This aligns with earlier work (Lee et al., 2018)."
        ),
    },
    {
        "name": "apa_et_al_violation",
        "style": "apa",
        "input": (
            "The research (Smith, Jones, Lee, & Park, 2021) showed that "
            "cognitive load matters. Smith, Jones, Lee, and Park (2021) agreed."
        ),
    },
    {
        "name": "apa_reference_list_errors",
        "style": "apa",
        "input": (
            "References: Smith, J. (2020). Effects Of Sleep. "
            "Journal of applied psychology, 105(3), 234-250."
        ),
    },
    # --- MLA (3) ---
    {
        "name": "mla_author_page_only",
        "style": "mla",
        "input": "Smith argues that memory declines with age (Smith, 2020, p. 45).",
    },
    {
        "name": "mla_clean",
        "style": "mla",
        "input": "Recent studies confirm this (Jones 22). The data show a trend (Jones 22).",
    },
    {
        "name": "mla_works_cited_author",
        "style": "mla",
        "input": "Works Cited: John Smith. How to Cite. Penguin, 2020.",
    },
    # --- Chicago (3) ---
    {
        "name": "chicago_footnote_not_parenthetical",
        "style": "chicago",
        "input": "The study found strong effects (Smith 2020, 45).",
    },
    {
        "name": "chicago_clean_note",
        "style": "chicago",
        "input": (
            "Smith argues that the method was flawed.¹\n"
            "¹John Smith, Research Methods (New York: Norton, 2020), 45."
        ),
    },
    {
        "name": "chicago_bibliography",
        "style": "chicago",
        "input": (
            "Bibliography: John Smith. Introduction to Statistics. "
            "New York: Norton, 2020."
        ),
    },
]


def test_rubric_cases():
    """Each bot response should score >= 8/10 against the citation rubric."""
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
        assert rating >= 8, (
            f"[{case['name']}] Rating {rating}/10 — response: {response[:200]}"
        )
    print("\n--- Pass rates by category (rubric MaaJ) ---")
    for cat in ["apa", "mla", "chicago"]:
        ratings = by_category.get(cat, [])
        if ratings:
            passed = sum(1 for r in ratings if r >= 8)
            print(f"  {cat}: {passed}/{len(ratings)} passed")
    total = sum(len(by_category.get(c, [])) for c in ["apa", "mla", "chicago"])
    if total:
        all_ratings = []
        for c in ["apa", "mla", "chicago"]:
            all_ratings.extend(by_category.get(c, []))
        print(f"  average: {sum(all_ratings) / len(all_ratings):.1f}/10")
