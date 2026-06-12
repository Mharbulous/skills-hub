---
name: draft-bcsc-form
description: >
  Fill BC Supreme Court .dotx templates using zipfile + lxml. Single entry point for
  generating blank forms (proceedings info only), assembling substance into final .docx,
  converting LEAP-exported templates, and amending filed pleadings. Use whenever the user
  asks to generate a blank BCSC form, fill out Form 32 / Form 1 / Form 66, assemble a
  form from a draft subfolder, amend a pleading, or convert a raw LEAP template.
  Trigger on: blank form, generate form, assemble form, amend a pleading, amended pleading,
  Rule 6-1 amendment, convert template, notice of application, petition, affidavit.
  For substance drafting (Orders Sought, Legal Basis, Relevant Facts), use /solver,
  /researcher, /narrator. For bill of costs (Form 62), use /fill-boc.
  For holistic review before assembly, use /polish-substance.
---

# fill-bcsc-form

You are a **content-blind shuttle**. You do not draft substance, classify legal content, or make routing decisions. You move opaque payloads between the harness (via Bash) and subagents (via Task). Follow this protocol exactly.

## Operations

| Operation | What it does | Invoked by |
|-----------|-------------|------------|
| **Generate** | Fill blank form with proceedings/party info, create draft subfolder | Practitioner |
| **Assemble** | Merge substance `.txt` files into final `.docx` | `/polish-substance` or practitioner |
| **Amend** | Amend a filed pleading per Rule 6-1 | Practitioner |
| **New Template** | Convert LEAP-exported `.dotx` to canonical bracket-placeholder format | Practitioner |

**Not handled here:**
- Substance drafting (Orders, Facts, Law) -> use `/solver`, `/researcher`, `/narrator`
- Bill of Costs (Form 62) -> use `/fill-boc`

## Shuttle Protocol

```
HARNESS = "python .agents/skills/draft-bcsc-form/scripts/harness.py"

# --- Session discovery ---
sessions = BASH("{HARNESS} list")
if sessions match user_request:
    response = BASH("{HARNESS} resume <session_id>")
else:
    response = BASH("{HARNESS} init '<user_request>'")

# --- Classification loop ---
# After init, harness returns spawn_subagent for classification.
# Shuttle the result back via: BASH("{HARNESS} classify <session_id> '<result>'")
# Repeat until harness returns a step (not classify) action.

# --- Standard shuttle loop ---
while response.action != "done":
    if response.action == "spawn_subagent":
        subagent_result = TASK(prompt=response.prompt, schema=response.schema)
        if response.route_to == "classify":
            response = BASH("{HARNESS} classify <session_id> '<subagent_result>'")
        else:
            response = BASH("{HARNESS} step <session_id> '<subagent_result>'")

    elif response.action == "retry":
        subagent_result = TASK_CONTINUE(error=response.error)
        response = BASH("{HARNESS} step <session_id> '<subagent_result>'")

    elif response.action == "ask_user":
        answer = ASK_USER(question=response.question, options=response.options)

        # Detection priority (check in order):
        # 1. Re-classification: user wants a different form/mode entirely
        if IS_RECLASS(answer):
            response = BASH("{HARNESS} reset <session_id> '<answer>'")

        # 2. Backtracking: user wants to revise a prior step
        elif IS_BACKTRACK(answer):
            target = IDENTIFY_STEP(answer)
            response = BASH("{HARNESS} rewind <session_id> '<target>'")

        # 3. Normal answer
        else:
            response = BASH("{HARNESS} step <session_id> '{\"user_answer\": \"<answer>\"}'")

    elif response.action == "oow":
        handle_side_conversation(response.lawyer_question, response.context)
        response = BASH("{HARNESS} step <session_id> '{\"kind\": \"oow_resolved\"}'")

    elif response.action == "halt":
        TELL_USER(response.error)
        break
```

## Generate Handoff

After Generate completes (blank form produced), end with:

> "Blank form saved to `{subfolder_path}`. Start a new session and run `/solver` to draft the orders sought."

## User Communication

**Rule:** All reasoning, file-inspection findings, and "let me check X" narration stays inside `<thinking>` blocks or tool-call description text. It never appears as plain response prose visible to the user.

**Between tool calls, emit only:** outcome of the last step + what's next -- one or two sentences max.

Format: `[Outcome -- success/failure + one-line result]. [Next action, named concisely].`

If a step fails, say what failed and what you'll try instead. Do not narrate "I noticed that..." or "Let me now..." or "Got the inventory."

## Draft Existence Check

After classification resolves and the form type is known, if the matter workspace path is available, check `{workspace}/0. DRAFT/` for current standard draft folders named `YYYY-MM-DD AI`. If a matching draft file is found:

```
choice = ASK_USER(
    question="A draft [form name] already exists in 0. DRAFT. Create a new [form name] or amend the existing draft?",
    options=["Create a new [form name]", "Amend the existing draft"]
)
if choice == "Amend the existing draft":
    response = BASH("{HARNESS} reset <session_id> 'amend the [form name] in 0. DRAFT'")
```

Run this check once, immediately after the classification loop exits. Skip if the matter workspace path is not yet known.

## Detection Rules

**IS_RECLASS(answer):** The answer contains language naming a different form or mode than the one in progress -- e.g. "actually let's do an NOCC", "switch to an amendment instead." If uncertain, use ASK_USER to clarify before calling reset.

**IS_BACKTRACK(answer):** The answer contains revision language referencing a prior step -- e.g. "I got the party name wrong." Map natural language to a step_id. If ambiguous, use ASK_USER to clarify: "Which step would you like to revise?"

## Key Rules

1. **Never read subagent prompts.** Copy `response.prompt` into the Task tool's prompt field verbatim.
2. **Never parse subagent results.** Copy the subagent's return text into the harness step command verbatim.
3. **Task tool = fresh subagent.** Every `TASK(...)` is a Task-tool spawn with a fresh context window, not an inline LLM turn.
4. **Session ID tracking.** The harness returns `session_id` in its init response. Pass it to all subsequent commands.

## Form Registry

| Form | Rule | Asset | Fill script | Notes |
|------|------|-------|-------------|-------|
| Notice of Application (Form 32) | Rule 8-1 | `templates/032-noa.dotx` | `fill_plain.py` | Generate + Assemble |
| Petition (Form 66) | Rule 16-1 | `templates/066-petition.dotx` | `fill_plain.py --form petition` | Generate + Assemble |
| Notice of Civil Claim (Form 1) | Rule 3-1 | `templates/001-nocc.dotx` | `fill_plain.py --form nocc` | Generate + Assemble |
| Response to Counterclaim (Form 4) | Rule 3-4 | `templates/004-rtc.dotx` | `fill_plain.py --form rtc` | Generate + Assemble |
| Offer to Settle Costs (Form 123) | Rule 9-1(6) | `templates/123-otsc.dotx` | `fill_plain.py --form otsc` | Generate only |
| Affidavit | Rule 22-2 | `templates/affidavit.dotx` | `fill_plain.py --form affidavit` | Generate only |

**Not listed:** Bill of Costs (Form 62) -- use `/fill-boc`.

## Affidavit-specific rules

The following rules apply whenever `form == "affidavit"`. Rules 1–3 govern content drafted by subagents; rules 4–7 are enforced automatically by `fill_plain.py`.

### Content drafting (subagent rules)

1. **No section headings.** Body content uses numbered paragraphs only. Do not insert heading paragraphs (e.g. "The Promissory Note", "Payments Received"). Affidavits are numbered-paragraph documents.

2. **Standard preamble.** The first numbered paragraph must be the standard BC opening verbatim:
   > "I am the [role] in this action and as such I have direct knowledge of the facts herein deposed, except where stated to be based on information and belief, in which case I verily believe those facts to be true."

3. **Facts only — no argument.** Each paragraph must recount a fact, exhibit, or observation the deponent personally witnessed or can speak to. Omit any paragraph that argues a legal position, characterises the opposing party's conduct, or draws a legal conclusion (e.g. "The defendants' set-off defence is based entirely on unparticularized allegations…").

4. **Exhibit references must be bolded.** Whenever an exhibit is referenced in a body paragraph, the phrase "Exhibit [Letter]" must appear in bold — for example: "Attached hereto and marked as **Exhibit A** is a true copy of…". This applies to every occurrence in every paragraph.

5. **Exhibits lettered sequentially by first appearance.** Assign exhibit letters A, B, C… in the order each exhibit is first introduced in the affidavit body paragraphs. The first exhibit mentioned receives the letter "A", the second receives "B", and so on. Do not use a letter that skips ahead of the sequence or that reflects document importance rather than document order.

### Template post-processing (fill_plain.py — Phase 4)

6. **Interpreter endorsement off by default.** The affidavit template includes an interpreter endorsement section (Rule 22-2(7)) after the jurat. `fill_plain.py` removes it unless `context["interpreter_required"]` is `"yes"`. The `gen.scalars` step asks: *"Does the deponent require an interpreter? (yes/no, default: no)"* and stores the answer as `interpreter_required`.

7. **No "last updated" footer text.** `fill_plain.py` clears all `<w:r>` runs from every `word/footer*.xml` member, stripping the LEAP "Last updated [date]" text.

8. **No page numbers in footer.** Page-number `fldChar`/`instrText` field codes are removed as part of footer clearing (same operation as rule 7 — removing all runs from footers).

9. **keepNext on last paragraph before jurat.** `fill_plain.py` adds `<w:keepNext/>` to the `<w:pPr>` of the last `LEAPBCParaNumL*` paragraph before the jurat table, ensuring at least one numbered paragraph appears on the signature page.

## Constraints

- Uses `lxml` only (not stdlib `xml.etree`) -- required to preserve `mc:Ignorable` namespace declarations.
- No script named `inspect.py` inside any sub-package -- shadows stdlib `inspect`, breaking `lxml` imports.
- Leave-blank placeholders `[mmmm d, yyyy]`, `[number]`, and `[judge-date]` are never substituted.
- Parts 2 and 3 share `numId=2`: sequential numbering is automatic.
