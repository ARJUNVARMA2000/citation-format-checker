"""Golden-reference MaaJ evals: judge the bot's output against expected answers."""

from conftest import get_review, judge_with_golden

# 10+ cases: 4 APA, 3 MLA, 3 Chicago. Each has input, reference answer, style.

GOLDEN_EXAMPLES = [
    # --- APA (4) ---
    {
        "name": "apa_direct_quote_no_page",
        "style": "apa",
        "input": (
            'According to Smith (2020), "the results were significant" and '
            "the study confirmed earlier findings (Jones & Lee, 2019)."
        ),
        "reference": (
            'APA-4 (page number required): The direct quote "the results were '
            'significant" needs a page number — use (Smith, 2020, p. XX). '
            "The rest is correctly formatted."
        ),
    },
    {
        "name": "apa_clean",
        "style": "apa",
        "input": (
            "Smith and Jones (2020) found that sleep deprivation impairs "
            "memory. This aligns with earlier work (Lee et al., 2018)."
        ),
        "reference": (
            "No violations found. Narrative citation uses 'and' correctly; "
            "parenthetical uses 'et al.' for 3+ authors. Correctly formatted."
        ),
    },
    {
        "name": "apa_et_al_violation",
        "style": "apa",
        "input": (
            "The research (Smith, Jones, Lee, & Park, 2021) showed that "
            "cognitive load matters. Smith, Jones, Lee, and Park (2021) agreed."
        ),
        "reference": (
            "APA-3: For 3+ authors use 'et al.' from the first citation — "
            '(Smith et al., 2021) and Smith et al. (2021) in narrative.'
        ),
    },
    {
        "name": "apa_reference_list_errors",
        "style": "apa",
        "input": (
            "References: Smith, J. (2020). Effects Of Sleep. "
            "Journal of applied psychology, 105(3), 234-250."
        ),
        "reference": (
            "APA-R5: Article titles use sentence case, not title case — "
            '"Effects of sleep." Journal names are title case and italicized.'
        ),
    },
    # --- MLA (3) ---
    {
        "name": "mla_author_page_only",
        "style": "mla",
        "input": "Smith argues that memory declines with age (Smith, 2020, p. 45).",
        "reference": (
            "MLA-1: MLA uses author and page only — (Smith 45). "
            "Remove year and 'p.' MLA-3: No comma between author and page."
        ),
    },
    {
        "name": "mla_clean",
        "style": "mla",
        "input": "Recent studies confirm this (Jones 22). The data show a trend (Jones 22).",
        "reference": (
            "No violations found. Author-page format is correct; no comma, "
            "no 'p.,' no year. Correctly formatted for MLA."
        ),
    },
    {
        "name": "mla_works_cited_author",
        "style": "mla",
        "input": "Works Cited: John Smith. How to Cite. Penguin, 2020.",
        "reference": (
            "MLA-W1: Invert author name — Smith, John. "
            "Book title italicized. Correct publisher and year format."
        ),
    },
    # --- Chicago (3) ---
    {
        "name": "chicago_footnote_not_parenthetical",
        "style": "chicago",
        "input": "The study found strong effects (Smith 2020, 45).",
        "reference": (
            "CHI-1: Chicago Notes-Bibliography uses superscript numbers and "
            "footnotes, not parenthetical (Author Year). Use footnotes instead."
        ),
    },
    {
        "name": "chicago_clean_note",
        "style": "chicago",
        "input": (
            "Smith argues that the method was flawed.¹\n"
            "¹John Smith, Research Methods (New York: Norton, 2020), 45."
        ),
        "reference": (
            "No violations found. Superscript and full first-note citation "
            "are correctly formatted for Chicago."
        ),
    },
    {
        "name": "chicago_bibliography",
        "style": "chicago",
        "input": (
            "Bibliography: John Smith. Introduction to Statistics. "
            "New York: Norton, 2020."
        ),
        "reference": (
            "CHI-B2: In bibliography, invert the first author to Last, First — "
            "use Smith, John. The rest of the book entry format (place, "
            "publisher, year) is otherwise correct."
        ),
    },
]


def test_golden_examples():
    """Each bot response should score >= 6/10 against its golden reference."""
    print()
    by_category = {"apa": [], "mla": [], "chicago": []}
    for example in GOLDEN_EXAMPLES:
        response = get_review(example["input"], style=example["style"])
        rating = judge_with_golden(
            prompt=example["input"],
            reference=example["reference"],
            response=response,
        )
        by_category[example["style"]].append(rating)
        print(f"  {example['name']}: {rating}/10")
        assert rating >= 6, (
            f"[{example['name']}] Rating {rating}/10 — response: {response[:200]}"
        )
    print("\n--- Pass rates by category (golden MaaJ) ---")
    for cat, ratings in by_category.items():
        if ratings:
            passed = sum(1 for r in ratings if r >= 6)
            print(f"  {cat}: {passed}/{len(ratings)} passed")
    print(f"  average: {sum(sum(by_category[c]) for c in by_category) / len(GOLDEN_EXAMPLES):.1f}/10")
