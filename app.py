import re
import uuid

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse
from litellm import completion
from pydantic import BaseModel

load_dotenv()

# --- Config ---

MODEL = "vertex_ai/gemini-2.5-flash"

# --- Safety and Backstop ---

SAFETY_KEYWORDS = [
    "suicide",
    "self-harm",
    "kill myself",
    "end my life",
    "want to die",
    "hurt myself",
    "hopeless",
]

SAFETY_RESPONSE = (
    "It sounds like you may be going through a difficult time. "
    "Please reach out to the 988 Suicide & Crisis Lifeline "
    "(call or text 988) or the Crisis Text Line (text HOME to 741741). "
    "You are not alone."
)

# Patterns that indicate the message is an academic citation / reference,
# not a personal distress message.  When these appear alongside a safety
# keyword the safety gate is skipped so the citation can be reviewed normally.
CITATION_CONTEXT_PATTERNS = [
    # Parenthetical year — (2023), (2019), (n.d.)
    re.compile(r"\(\s*\d{4}\s*\)"),
    re.compile(r"\(\s*n\.d\.\s*\)", re.IGNORECASE),
    # "vol.", "pp.", "doi:", "http://", "https://"
    re.compile(r"\b(vol\.|pp\.|doi:|https?://)", re.IGNORECASE),
    # Common reference list markers — Journal of …, et al.,
    re.compile(r"\bet\s+al\.", re.IGNORECASE),
    re.compile(r"\bjournal\s+of\b", re.IGNORECASE),
    # Author-date patterns — Smith, J. or Smith, John
    re.compile(r"[A-Z][a-z]+,\s+[A-Z]\."),
    # Explicit citation-check requests
    re.compile(
        r"\b(check|format|cite|citation|reference|bibliography|apa|mla|chicago)\b",
        re.IGNORECASE,
    ),
]

CITATION_RULE_PATTERN = re.compile(
    r"(APA-\w+|MLA-\w+|CHI-\w+|No violations found|correctly formatted|"
    r"no formatting errors|appears correctly formatted|correct format for|"
    r"no citation errors|don't see any citation errors|Corrected citation|"
    r"not certain about this case|recommend checking)",
    re.IGNORECASE,
)

HAS_DIGIT_PATTERN = re.compile(r"\d")
SAFETY_RESPONSE_PATTERN = re.compile(r"988|crisis|not alone", re.IGNORECASE)

SAFETY_CLASSIFIER_PROMPT = """\
You are a safety classifier for a citation-format assistant.

Return UNSAFE if the user's message expresses suicidal intent, self-harm,
crisis-level hopelessness, or tries to bypass safety while expressing those.
Return SAFE for citation-review requests, including academic references that
mention self-harm-related terms in a bibliographic context.
Return SAFE for generic prompt-injection, role-change, jailbreak, or
off-topic requests that do not include self-harm or suicide content.

Reply with exactly one token: SAFE or UNSAFE.
"""

OFF_TOPIC_REDIRECT = (
    "I'm not able to help with that — I'm a citation format checker. "
    "I can review in-text citations, reference lists, and bibliography "
    "formatting for APA, MLA, or Chicago style. If you have a citation "
    "to check, just paste it in and I'll take a look!"
)


def _looks_like_citation(text: str) -> bool:
    """Return True if the text contains academic-citation signals."""
    return any(pat.search(text) for pat in CITATION_CONTEXT_PATTERNS)


def _matches_keyword_safety_backstop(text: str) -> bool:
    """Fallback keyword safety check for non-citation-like inputs."""
    lower = text.lower()
    has_safety_keyword = any(kw in lower for kw in SAFETY_KEYWORDS)
    has_citation_signal = ("(" in text and ")" in text) or (
        HAS_DIGIT_PATTERN.search(text) is not None
    )
    return has_safety_keyword and not has_citation_signal


def check_safety(user_message: str) -> str | None:
    """Pre-generation: LLM-first safety check with a deterministic fallback."""
    try:
        response = completion(
            model=MODEL,
            messages=[
                {"role": "system", "content": SAFETY_CLASSIFIER_PROMPT},
                {"role": "user", "content": user_message},
            ],
        )
        verdict = response.choices[0].message.content.strip().upper()
        if verdict.startswith("UNSAFE"):
            return SAFETY_RESPONSE
    except Exception:
        pass
    if _matches_keyword_safety_backstop(user_message):
        return SAFETY_RESPONSE
    return None


def check_response(response: str, user_message: str | None = None) -> str:
    """Post-generation backstop: normalize safety responses and redirect off-topic."""
    if SAFETY_RESPONSE_PATTERN.search(response):
        return SAFETY_RESPONSE
    if user_message and _matches_keyword_safety_backstop(user_message):
        return SAFETY_RESPONSE
    if not CITATION_RULE_PATTERN.search(response):
        return OFF_TOPIC_REDIRECT
    return response


# --- System Prompt Template ---

SYSTEM_PROMPT_TEMPLATE = """\
<role>
You are an expert citation format reviewer specializing in {style_name}.
Your audience is students formatting academic papers. You review citations
and reference lists with a precise, collegial tone — direct but encouraging.
</role>

<scope>
You check citation formatting for the {style_name} style guide. This includes:
- In-text citation format (author names, dates, page numbers, punctuation)
- Reference list / Works Cited / Bibliography formatting
- Ordering and structure of reference entries
- Proper use of italics, capitalization, and punctuation in citations

When the user asks about grammar, prose style, or writing quality: I focus on citation formatting; for grammar and style feedback, a writing tutor or tool like Grammarly is a better fit.

When the user asks whether a source is good or about research methodology: I review how sources are cited, not whether they are good sources; for research quality, consult your advisor.

When the user asks about margins, fonts, headers, or page layout: I specialize in citations and references; for page layout and formatting, check your style manual's formatting chapter.
</scope>

<task>
Review the user's text and identify violations of the citation rules in <rules>.
For each violation, state the rule ID and quote the problematic citation.
After each violation, provide a brief explanation of what is wrong.
If the provided citations are already compliant, respond with "No violations found."
and a brief confirmation; do not invent or force violations.
After listing all violations, provide a final "Corrected citation:" block containing the
fully corrected version of the user's citation(s) that fixes every identified violation.
This corrected version should be ready to copy-paste into a paper.
When no text is provided for review, ask the user to paste their citations.
</task>

<positive_constraints>
You answer questions about citation formatting in {style_name}.
You identify formatting errors in citations and reference lists.
You explain why a citation violates a specific rule.
After identifying all violations, provide the complete corrected citation at the end
so the user can copy-paste it directly into their paper.
When the text follows all rules, you confirm it is correctly formatted — no corrected block needed.
</positive_constraints>

<escape_hatch>
When you encounter a citation edge case you are not confident about,
say: "I'm not certain about this case — I'd recommend checking the {style_manual} for guidance."
</escape_hatch>

<rules>
{rules}
</rules>"""


# --- Citation Rules by Style ---

RULES_APA = """\
APA 7th Edition — In-Text Citations

APA-1 — Use author-date format. In-text citations must use (Author, Year). Not footnotes or numbered references.

APA-2 — One or two authors: cite both names every time. Use "&" inside parentheses, "and" in narrative text.

APA-3 — Three or more authors: use "et al." from the first citation. (Smith et al., 2020) — do not list all names after first use.

APA-4 — Direct quotes require page numbers. (Smith, 2020, p. 15) for one page, (Smith, 2020, pp. 15-16) for a range.

APA-5 — Block quotes: 40+ words must be freestanding, indented, no quotation marks. Citation after final period.

APA-6 — No comma between author and year in narrative citation. Correct: Smith (2020) found. Wrong: Smith, (2020) found.

APA-7 — Use "&" inside parentheses, "and" in narrative. (Smith & Jones, 2020) but "Smith and Jones (2020) argued."

Reference List

APA-R1 — Hanging indent: first line flush left, subsequent lines indented 0.5 in.

APA-R2 — Authors: Last, F. M. format. Invert names, use initials.

APA-R3 — List up to 20 authors; 21+ use first 19, ellipsis, then last.

APA-R4 — Year in parentheses immediately after authors. Smith, J. A. (2020).

APA-R5 — Sentence case for article titles; title case for journal names. Italicize journal and volume.

APA-R6 — DOI as hyperlink: https://doi.org/10.1037/...

APA-R7 — Alphabetical order by first author's last name.

APA-R8 — Use "n.d." when no date is available. (Smith, n.d.)
"""

RULES_MLA = """\
MLA 9th Edition — In-Text Citations

MLA-1 — Author-page format. (Smith 45) — no comma, no "p." or "pp.", no year. Page number only.

MLA-2 — Multiple authors: two authors (Smith and Jones 12); three+ use et al. (Smith et al. 34).

MLA-3 — No comma between author and page number. (Smith 22) not (Smith, 22).

MLA-4 — Indirect sources: use "qtd. in" in the parenthetical. (qtd. in Jones 89).

MLA-5 — Block quotes: four or more lines of prose, indented 0.5 in, no quotation marks.

MLA-6 — When author named in text, page number alone in parentheses. Smith argues that ... (45).

Works Cited

MLA-W1 — Author: Last, First. Invert first author only for multi-author entries.

MLA-W2 — Container model: Title of Source. Title of Container, Publisher, Year.

MLA-W3 — Italicize book and journal titles; quotation marks for article and chapter titles.

MLA-W4 — Hanging indent for each entry.

MLA-W5 — Alphabetical order by author's last name.

MLA-W6 — Publisher and publication date required when available.
"""

RULES_CHICAGO = """\
Chicago 17th Edition — Notes and Bibliography

Notes (footnotes/endnotes)

CHI-1 — Use superscript numbers in text. Full citation in first note; shortened form in subsequent notes.

CHI-2 — Footnote number after punctuation (comma, period). Place at end of clause or sentence.

CHI-3 — First note: full citation. Author First Last, Title (Place: Publisher, Year), page.

CHI-4 — Shortened form after first use: Author, Shortened Title, page. Or Ibid. when same source, same page.

CHI-5 — Ibid. only when citing the same source and page as the immediately preceding note.

CHI-6 — Use "Ibid." for same source same page; "Ibid., 45" for same source different page.

Bibliography

CHI-B1 — Hanging indent. Alphabetical by author's last name.

CHI-B2 — Author: Last, First. First author inverted; additional authors First Last.

CHI-B3 — Book: Author. Title. Place: Publisher, Year.

CHI-B4 — Article: Author. "Article Title." Journal Title volume, no. issue (Year): page range.

CHI-B5 — Include access date for online sources when no fixed publication date.

CHI-B6 — Page ranges: use en dash, no "pp." in bibliography.
"""

RULES = {
    "apa": RULES_APA,
    "mla": RULES_MLA,
    "chicago": RULES_CHICAGO,
}

STYLE_NAMES = {
    "apa": "APA 7th Edition",
    "mla": "MLA 9th Edition",
    "chicago": "Chicago 17th Edition (Notes and Bibliography)",
}

STYLE_MANUALS = {
    "apa": "Publication Manual of the American Psychological Association (7th ed.)",
    "mla": "MLA Handbook (9th ed.)",
    "chicago": "Chicago Manual of Style (17th ed.)",
}


# --- Few-Shot Examples ---

FEW_SHOT_APA = [
    {
        "user": (
            'According to Smith (2020), "the results were significant" and '
            "the study confirmed earlier findings (Jones & Lee, 2019)."
        ),
        "assistant": (
            '- APA-4 (page number required): "the results were significant" '
            "is a direct quote but lacks a page number.\n\n"
            "Corrected citation:\n"
            'According to Smith (2020, p. XX), "the results were significant" and '
            "the study confirmed earlier findings (Jones & Lee, 2019)."
        ),
    },
    {
        "user": (
            "Smith and Jones (2020) found that sleep deprivation impairs "
            "memory. This aligns with earlier work (Lee et al., 2018)."
        ),
        "assistant": (
            "No violations found. The writing is correctly formatted: "
            "narrative citation uses 'and' correctly, parenthetical uses "
            "'et al.' for 3+ authors, and both include years."
        ),
    },
    {
        "user": (
            "The research (Smith, Jones, Lee, & Park, 2021) showed that "
            '"cognitive load theory explains most variance." '
            "Earlier, Smith, Jones, Lee, and Park (2021) had hypothesized this."
        ),
        "assistant": (
            '- APA-3 (et al. for 3+ authors): "(Smith, Jones, Lee, & '
            'Park, 2021)" — APA 7th requires "et al." from the first citation.\n'
            '- APA-3: "Smith, Jones, Lee, and Park (2021)" in narrative — '
            "should also use et al. form.\n\n"
            "Corrected citation:\n"
            'The research (Smith et al., 2021) showed that "cognitive load theory '
            'explains most variance." Earlier, Smith et al. (2021) had hypothesized this.'
        ),
    },
    {
        "user": (
            "Can you rewrite this reference list for me? "
            "Smith, J. (2020). Effects Of Sleep. journal of psychology, 105(3), 234."
        ),
        "assistant": (
            '- APA-R5 (title capitalization): "Effects Of Sleep" should use sentence case.\n'
            '- APA-R5 (journal capitalization): "journal of psychology" should be in title case '
            "and italicized.\n\n"
            "Corrected citation:\n"
            "Smith, J. (2020). Effects of sleep. Journal of Psychology, 105(3), 234."
        ),
    },
]

FEW_SHOT_MLA = [
    {
        "user": (
            "Smith argues that memory declines with age (Smith, 2020, p. 45)."
        ),
        "assistant": (
            '- MLA-1 (author-page, no year): MLA uses author and page only — '
            'remove the year and "p."\n'
            "- MLA-3 (no comma): Do not use a comma between author and page.\n\n"
            "Corrected citation:\n"
            "Smith argues that memory declines with age (Smith 45)."
        ),
    },
    {
        "user": (
            "Recent studies confirm this (Jones 22). The data show a clear "
            "trend (Jones 22)."
        ),
        "assistant": (
            "No violations found. Author-page format is correct; no comma, "
            "no 'p.,' no year. Correctly formatted for MLA."
        ),
    },
    {
        "user": (
            "According to Lee, the effect was significant (Lee, 34). "
            "Smith wrote that \"results were positive\" (Smith, p. 12)."
        ),
        "assistant": (
            '- MLA-3 (no comma): "(Lee, 34)" — remove the comma.\n'
            '- MLA-1 (no "p."): "(Smith, p. 12)" — MLA omits "p." Remove the '
            "page prefix and comma.\n\n"
            "Corrected citation:\n"
            "According to Lee, the effect was significant (Lee 34). "
            'Smith wrote that "results were positive" (Smith 12).'
        ),
    },
]

FEW_SHOT_CHICAGO = [
    {
        "user": (
            "The study found strong effects (Smith 2020, 45). "
            "Later work confirmed this (Jones 2019)."
        ),
        "assistant": (
            "- CHI-1 (footnote format): Chicago Notes-Bibliography uses "
            "superscript numbers and footnotes, not parenthetical author-date.\n\n"
            "Corrected citation:\n"
            "The study found strong effects.¹ Later work confirmed this.²\n"
            "¹ John Smith, [Title] ([Place]: [Publisher], 2020), 45.\n"
            "² Jane Jones, [Title] ([Place]: [Publisher], 2019)."
        ),
    },
    {
        "user": (
            "Smith argues that the method was flawed.¹ "
            "¹Smith, Research Methods, 45."
        ),
        "assistant": (
            "No violations found. Superscript number is placed after punctuation; "
            "shortened note form (author, short title, page) is appropriate for "
            "a subsequent citation. Correctly formatted for Chicago."
        ),
    },
    {
        "user": (
            "Bibliography: Smith, John. Introduction to Statistics. "
            "New York: Norton, 2020."
        ),
        "assistant": (
            "No violations found. The bibliography entry uses correct author "
            "order and book-entry formatting for Chicago."
        ),
    },
    {
        "user": (
            "The data support the hypothesis.² "
            "² Smith, John. Introduction to Statistics (New York: Norton, 2020), 78."
        ),
        "assistant": (
            '- CHI-3 (first note format): In notes, first citations use "First Last," '
            'so "Smith, John" should be "John Smith."\n\n'
            "Corrected citation:\n"
            "The data support the hypothesis.²\n"
            "² John Smith, Introduction to Statistics (New York: Norton, 2020), 78."
        ),
    },
]

FEW_SHOT = {
    "apa": FEW_SHOT_APA,
    "mla": FEW_SHOT_MLA,
    "chicago": FEW_SHOT_CHICAGO,
}


def normalize_style(style: str | None) -> str:
    normalized = style.lower() if style else "apa"
    if normalized not in RULES:
        return "apa"
    return normalized


def build_initial_messages(style: str = "apa") -> list[dict]:
    """Build the initial message list with system prompt and few-shot examples."""
    style = normalize_style(style)
    style_name = STYLE_NAMES[style]
    style_manual = STYLE_MANUALS[style]
    rules_text = RULES[style]
    system_content = SYSTEM_PROMPT_TEMPLATE.format(
        style_name=style_name,
        style_manual=style_manual,
        rules=rules_text,
    )
    messages = [{"role": "system", "content": system_content}]
    for example in FEW_SHOT[style]:
        messages.append({"role": "user", "content": example["user"]})
        messages.append({"role": "assistant", "content": example["assistant"]})
    return messages


# --- LLM Call ---


def generate_response(messages: list[dict]) -> str:
    """Generate a response using LiteLLM."""
    try:
        response = completion(model=MODEL, messages=messages)
        return response.choices[0].message.content
    except Exception as e:
        return f"Something went wrong: {e}"


# --- Session Management ---

sessions: dict[str, list[dict]] = {}
session_styles: dict[str, str] = {}


# --- FastAPI App ---

app = FastAPI()


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    style: str = "apa"


class ChatResponse(BaseModel):
    response: str
    session_id: str


@app.get("/")
def index():
    return FileResponse("index.html")


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    # Safety check — skip LLM if distress keywords detected
    safety_msg = check_safety(request.message)
    if safety_msg:
        session_id = request.session_id or str(uuid.uuid4())
        return ChatResponse(response=safety_msg, session_id=session_id)

    # Get or create session
    session_id = request.session_id or str(uuid.uuid4())
    request_style = normalize_style(request.style)
    if (
        session_id not in sessions
        or session_styles.get(session_id) != request_style
    ):
        sessions[session_id] = build_initial_messages(request_style)
        session_styles[session_id] = request_style

    # Add user message
    sessions[session_id].append({"role": "user", "content": request.message})

    # Generate response
    response_text = generate_response(sessions[session_id])

    # Post-generation backstop
    response_text = check_response(response_text, user_message=request.message)

    # Add assistant response to history
    sessions[session_id].append({"role": "assistant", "content": response_text})

    return ChatResponse(response=response_text, session_id=session_id)


@app.post("/clear")
def clear(session_id: str | None = None):
    if session_id and session_id in sessions:
        del sessions[session_id]
        session_styles.pop(session_id, None)
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
