"""boc.mcq -- BOC Step 2: Systematic MCQ interview.

Multi-turn interactive step walking through tariff Categories A-I.
Each iteration generates MCQ questions for the current category using
the ask_user sub-loop. The harness enforces a ceiling of 50 iterations.

Categories and their items (from workflow.md):
  A - Commencement (Items 1, 5, 6)
  B - Defence/Counterclaim (Items 7-9)
  C - Discovery (Items 10-16)
  D - Expert Evidence and Witnesses (Items 17-18)
  E - Examinations for Discovery (Items 19-20)
  F - Applications, Hearings, Conferences (Items 21-32)
  G - Trial (Items 34-38)
  H - Registry Steps (Items 39-42)
  I - Miscellaneous (Items 43-48)
"""
from __future__ import annotations

import json

max_retries = 2

# Category order for the interview
CATEGORIES = [
    {"id": "A", "name": "Commencement", "items": "1, 5, 6"},
    {"id": "B", "name": "Defence / Counterclaim", "items": "7-9"},
    {"id": "C", "name": "Discovery", "items": "10-16"},
    {"id": "D", "name": "Expert Evidence and Witnesses", "items": "17-18"},
    {"id": "E", "name": "Examinations for Discovery", "items": "19-20"},
    {"id": "F", "name": "Applications, Hearings, Conferences", "items": "21-32"},
    {"id": "G", "name": "Trial", "items": "34-38"},
    {"id": "H", "name": "Registry Steps", "items": "39-42"},
    {"id": "I", "name": "Miscellaneous", "items": "43-48"},
]

# MCQ questions per category, drawn from workflow.md
CATEGORY_QUESTIONS = {
    "A": [
        {
            "q": "Were pre-litigation investigations or correspondence conducted? (Items 1-5)",
            "options": ["Yes", "No"],
        },
        {
            "q": "Was a Notice of Civil Claim (or other originating pleading) filed? (Item 6)",
            "options": ["Yes", "No"],
        },
        {
            "q": "Were any amendments to pleadings filed after service?",
            "options": ["Yes", "No"],
        },
    ],
    "B": [
        {
            "q": "Did your client file a Response to Civil Claim? (Item 7)",
            "options": ["Yes", "No", "N/A - client is plaintiff"],
        },
        {
            "q": "Did your client also file a Counterclaim? (still Item 7)",
            "options": ["Yes", "No", "N/A"],
        },
        {
            "q": "Did your client receive a Counterclaim from the defendant and have to respond to it? (Item 9)",
            "options": ["Yes", "No"],
        },
        {
            "q": "Was a Third Party Notice filed in the proceeding? (Item 8)",
            "options": ["Yes", "No"],
        },
    ],
    "C": [
        {
            "q": "Was a List of Documents prepared and/or received?",
            "options": ["Yes", "No"],
        },
        {
            "q": "If yes, approximately how many documents were listed?",
            "options": ["Under 100", "100-500", "Over 500", "N/A - no list prepared"],
        },
        {
            "q": "Were there document demands, inspection requests, or production disputes? (Items 13-15)",
            "options": ["Yes", "No"],
        },
        {
            "q": "Was there electronic discovery? (Item 16)",
            "options": ["Yes", "No"],
        },
    ],
    "D": [
        {
            "q": "Were expert reports obtained and served? (Item 17)",
            "options": ["Yes", "No"],
        },
        {
            "q": "Were lay witnesses required to attend? (Item 18)",
            "options": ["Yes", "No"],
        },
    ],
    "E": [
        {
            "q": "Were examinations for discovery conducted?",
            "options": ["Yes", "No"],
        },
        {
            "q": "If yes, how many days total?",
            "options": ["1 day", "2-3 days", "4-5 days", "More than 5 days", "N/A"],
        },
        {
            "q": "Was your client conducting (Item 19) or being examined (Item 20)?",
            "options": ["Conducting", "Being examined", "Both", "N/A"],
        },
    ],
    "F": [
        {
            "q": "How many interlocutory applications did your client bring?",
            "options": ["None", "1", "2-3", "4 or more"],
        },
        {
            "q": "For applications brought, were they opposed or unopposed? How long?",
            "options": ["Unopposed, under 2 hours", "Opposed, under 2 hours",
                        "Opposed, 2+ hours (full day)", "Mixed", "N/A"],
        },
        {
            "q": "How many applications did the other side bring that your client responded to?",
            "options": ["None", "1", "2-3", "4 or more"],
        },
        {
            "q": "Were any applications heard in writing only? (Item 25)",
            "options": ["Yes", "No"],
        },
        {
            "q": "Were there any appeals of an associate judge's order? (Item 28)",
            "options": ["Yes", "No"],
        },
        {
            "q": "Which conferences were held? (select all that apply)",
            "options": ["Case Planning Conference (Item 29)",
                        "Trial Management Conference (Item 30)",
                        "Settlement Conference (Item 31)",
                        "Judicial Case Conference (Item 32)", "None"],
        },
    ],
    "G": [
        {
            "q": "Was a trial completed?",
            "options": ["Yes", "No"],
        },
        {
            "q": "If yes, how many trial days?",
            "options": ["1-2 days", "3-5 days", "6-10 days",
                        "More than 10 days", "N/A - no trial"],
        },
        {
            "q": "Was written argument submitted after trial? (Items 37-38)",
            "options": ["Yes - written and oral", "Yes - written only", "No", "N/A"],
        },
        {
            "q": "If no trial, how was the matter resolved?",
            "options": ["Settlement", "Summary judgment", "Dismissal",
                        "Other", "N/A - trial was held"],
        },
    ],
    "H": [
        {
            "q": "Was a Notice of Trial filed? (Item 39: 1 unit flat)",
            "options": ["Yes", "No"],
        },
        {
            "q": "Was a jury notice filed? (Item 40: 1 unit flat)",
            "options": ["Yes", "No"],
        },
        {
            "q": "Were other registry attendances required? (Items 41-42)",
            "options": ["Yes", "No"],
        },
    ],
    "I": [
        {
            "q": "Was mediation conducted? If yes, how many days? (Item 43)",
            "options": ["No mediation", "1 day", "2 days", "3+ days"],
        },
        {
            "q": "Were there formal settlement negotiations or Rule 9-1 offers? (Item 44)",
            "options": ["Yes", "No"],
        },
        {
            "q": "Was travel required for any step? (Items 45-48)",
            "options": ["Yes", "No"],
        },
        {
            "q": "Any other significant steps not yet covered?",
            "options": ["Yes - I will describe", "No - that covers everything"],
        },
    ],
}

response_schema = {
    "type": "object",
    "properties": {
        "kind": {"type": "string", "enum": ["step_result", "ask_user"]},
        "data": {"type": "object"},
        "question": {"type": "string"},
        "options": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["kind"],
}


def precondition(ctx: dict) -> tuple[bool, str]:
    if not ctx.get("style_of_cause"):
        return False, "boc.mcq requires style_of_cause from boc.setup"
    return True, ""


def _current_question_in_category(answers: list) -> tuple[int, int]:
    """Return (category_index, question_index_within_category)."""
    answered = [a for a in answers if a is not None]
    total_qs = 0
    for i, cat in enumerate(CATEGORIES):
        cat_qs = len(CATEGORY_QUESTIONS.get(cat["id"], []))
        if len(answered) < total_qs + cat_qs:
            return i, len(answered) - total_qs
        total_qs += cat_qs
    return len(CATEGORIES), 0


def build_prompt(ctx: dict) -> str:
    answers = ctx.get("step_answers", [])
    cat_idx, q_idx = _current_question_in_category(answers)

    # All categories complete
    if cat_idx >= len(CATEGORIES):
        # Build structured MCQ answer summary
        answered = [a for a in answers if a is not None]
        mcq_data = []
        total_qs = 0
        for cat in CATEGORIES:
            cat_id = cat["id"]
            questions = CATEGORY_QUESTIONS.get(cat_id, [])
            for j, qdef in enumerate(questions):
                idx = total_qs + j
                ans = answered[idx] if idx < len(answered) else ""
                mcq_data.append({
                    "category": cat_id,
                    "category_name": cat["name"],
                    "question": qdef["q"],
                    "answer": ans,
                })
            total_qs += len(questions)

        return f"""You are a BOC MCQ agent. All 9 categories have been completed.

Here is the complete interview data:

{json.dumps(mcq_data, indent=2)}

Return a step_result with the complete MCQ answers:
{{"kind": "step_result", "data": {{"mcq_answers": {json.dumps(mcq_data)}, "categories_complete": true}}}}

## Constraints
- Return ONLY the JSON object specified above. Do not call Read, Bash, Grep, Glob, or any file-access tools."""

    cat = CATEGORIES[cat_idx]
    cat_id = cat["id"]
    questions = CATEGORY_QUESTIONS.get(cat_id, [])
    q_def = questions[q_idx]

    # Build context of prior answers for this category
    answered = [a for a in answers if a is not None]
    prior_in_cat = []
    cat_start = sum(len(CATEGORY_QUESTIONS.get(c["id"], []))
                    for c in CATEGORIES[:cat_idx])
    for j in range(q_idx):
        prior_idx = cat_start + j
        if prior_idx < len(answered):
            prior_in_cat.append(
                f"  Q: {questions[j]['q']} -> A: {answered[prior_idx]}"
            )
    prior_text = "\n".join(prior_in_cat) if prior_in_cat else "  (first question in category)"

    return f"""You are a BOC MCQ interview agent for a BC Supreme Court Bill of Costs.

## Current Category
Category {cat_id} - {cat["name"]} (Items {cat["items"]})
Question {q_idx + 1} of {len(questions)} in this category.

## Prior answers in this category
{prior_text}

## Question to ask
{q_def["q"]}

Return an ask_user request:
{{"kind": "ask_user", "question": "Category {cat_id} ({cat['name']}): {q_def['q']}", "options": {json.dumps(q_def['options'])}}}

## Constraints
- Return ONLY the JSON object specified above. Do not call Read, Bash, Grep, Glob, or any file-access tools."""


def validate(result: dict, ctx: dict) -> tuple[bool, str]:
    mcq = result.get("mcq_answers")
    if not isinstance(mcq, list):
        return False, "mcq_answers must be a list"
    if len(mcq) == 0:
        return False, "mcq_answers is empty"
    # Check each answer has required fields
    for i, item in enumerate(mcq):
        if "category" not in item:
            return False, f"mcq_answers[{i}] missing 'category'"
        if "answer" not in item:
            return False, f"mcq_answers[{i}] missing 'answer'"
    return True, ""


def apply(ctx: dict, result: dict) -> dict:
    ctx["mcq_answers"] = result["mcq_answers"]
    return ctx
