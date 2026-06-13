# [Target Name] — Vision & Design Philosophy

**Date:** YYYY-MM-DD

<!-- Replace all bracketed placeholders and overwrite all HTML comments when
     using this template. Comments explain each section's purpose. -->

## 1. Theme & Design Philosophy

<!-- What the product IS and the principles that govern design decisions.
     This is the authoritative reference when a proposed change conflicts
     with the vision. -->

### Vision Statement

<!-- One paragraph — the one-sentence-or-two answer to "what is this?". State
     the product type (desktop app, web service, CLI tool, library, etc.),
     what it does, for whom, and the core differentiator. This is the most
     quoted part of the document; keep it crisp. Foundational definitional
     choices (desktop vs. web, local vs. cloud) often surface here and do
     not need to be restated in Foundations. -->

### Design Principles

<!-- List the principles that guide implementation. Order by importance —
     put the most critical or most easily violated principle first.

     For each principle, a brief violation example helps anchor the intent.
     Principles that fight common tendencies (e.g., silent fallbacks,
     over-abstraction) benefit from stronger framing: state the desired behavior,
     the motivation, and a concrete example together. -->

### Litmus Test

<!-- A single question that determines whether a proposed behavior belongs in
     scope. Follow with examples of each answer. -->


## 2. Purpose

<!-- Who is this for, what pain does it address, and why does it matter? -->

### Audience

<!-- Primary user today. If the audience will broaden over time, note the
     trajectory separately from current scope. -->

### Pain Points

<!-- Real problems this solves — frame as what was painful and why. -->

### Value Proposition

<!-- The core benefit. What does this enable that wasn't possible or practical before? -->

### Killer Use Case

<!-- The single scenario that best demonstrates the value. If someone only sees
     one demo, this is it. -->


## 3. North Star

<!-- The core metric(s) or measurement of progress toward the vision.
     How do you know you're getting closer? Preferably expressed mathematically. -->


## 4. Non-Goals

<!-- Things that are plausibly in scope but deliberately excluded.
     Keep this short — don't list architectural consequences (those belong in
     Foundations) or "not yet" items (note trajectory in the relevant section). -->


## 5. Foundations

<!-- Architectural commitments that are constitutive of what this product IS —
     not implementation choices to be revisited per feature. These are
     technical decisions (how modules are decoupled, which storage boundary is
     inviolable, what is and isn't swappable) that function as product-defining
     constraints. Any task that touches the repo inherits them.

     Distinct from both:
       - the Vision Statement, which names what the product IS in one paragraph
         and typically absorbs the single most definitional choice (e.g.
         "Windows desktop application"); and
       - Design Principles, which govern how features behave once built.
     Foundations define the load-bearing architectural structure that both the
     Vision Statement and the Principles assume. If a commitment is already
     stated in the Vision Statement, it does not need to be repeated here.

     When entries share a theme (e.g., multiple commitments about module
     decoupling), a brief lead-in sentence can frame them. For each entry:
     one bold sentence stating the commitment, then 2-3 sentences on what it
     rules out and why it is load-bearing. Keep the list short — if everything
     is foundational, nothing is. -->

## 6. Anti-Patterns

<!-- Optional — often more accurate after the vision has been used in practice.
     Document observed deviations from the vision, especially patterns that
     coding models tend to produce.

     For each entry:
     **Pattern:** What the failure looks like
     **Why it's wrong:** The consequence
     **What to do instead:** The positive redirect -->

*No anti-patterns documented yet — add entries here as they are discovered empirically.*
