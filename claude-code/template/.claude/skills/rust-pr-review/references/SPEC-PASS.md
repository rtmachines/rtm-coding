# Spec pass

> Adapted from rewrite-rs/skills `skills/workflow/rust-code-review/REVIEW-PASSES.md`
> (BSD-3-Clause, commit ae0fd62). Changes: severity mapped to P0–P3, request sources
> and status values defined for this kit, run as separate review passes in the current session.

The standards pass asks "is this good Rust?". The spec pass asks "is this the change
that was asked for?". Run it **after** the standards pass, as a separate read, so that
clean-looking code does not hide spec drift.

## Request source (first available wins)

1. User request and acceptance criteria from the conversation.
2. PR title and description retrieved for the exact reviewed PR.
3. Commit messages since the base (`git log --format=%B <BASE_SHA>..HEAD`). These are the
   author's own claims, so the result is at most `PARTIAL`.
4. Nothing → `- spec: NOT RUN (no request available)`. Never invent intent from the diff.

## Procedure

Read the request first, the diff second. Do not apply the smell baseline and do not
comment on craft here. Answer three questions:

1. **Missing:** is everything the request asks for implemented? Name each missing part.
2. **Unrequested:** is anything implemented that the request did not ask for? Unrequested
   scope is a finding, not a bonus. Say whether it belongs here or in a follow-up.
3. **Contradictions:** does any line contradict a stated requirement? Quote the requirement
   and cite the line.

Assess the requested behavior, not where its evidence is stored. A faithful isolated
probe can establish behavior just as a checked-in test can. Missing checked-in tests
may be an actionable coverage recommendation; they do not make a verified requirement
PARTIAL unless the request or project policy explicitly requires those tests in the PR.
Do not invent additional lexical/API restrictions from an undefined word when the
request supplies a concrete type or dependency contract. State the interpretation and
raise a question only when plausible alternatives materially change the requested behavior.

## Severity

- Contradiction of an explicit requirement, or a missing required part → **P1**.
- Unrequested behavior change visible to users or callers → **P1**; unrequested internal
  refactor or extra feature → **P2**.
- Ambiguous request where the diff picks one reading → **P3**, phrased as a question.

Spec findings go into `## Findings` with the same `- [Px] path.rs:LINE - ...` format. When a
finding has no single line (a missing part), anchor it to the file where it should live.

## Status

- `PASS`: request available, no spec findings.
- `FAIL`: at least one P1 spec finding.
- `PARTIAL`: only commit messages were available, or the request is too vague to check all
  three questions.
- `NOT RUN`: no request available.
