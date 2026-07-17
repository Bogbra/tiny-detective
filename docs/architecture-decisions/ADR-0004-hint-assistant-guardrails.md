# ADR-0004: AI Hint Assistant Guardrails

## Status

Accepted

## Context

The project spec's "AI Hint Flow" requires: generate → evaluate against guardrails → return a safe hint, with a deterministic fallback if the AI hint fails guardrails. The hint assistant must never reveal the culprit, reveal the full solution, invent facts, or discuss anything not grounded in the actual case. Unlike Phase 5's case generation (an offline, admin-triggered batch process), a hint request happens live, synchronously, inside a player's real-time API call — so this AI integration belongs in `services/api`, not `tools/ai-content`.

## Decision

**Where it lives**: `services/api/app/infrastructure/ai/` (`ai_hint_assistant.py`, `openai_client.py`, `prompt_loader.py`, `prompts/generate_hint_v1.md`) — matching the exact file names the project spec's monorepo structure names for this. `services/api` now depends on the `openai` SDK directly, which is a deliberate departure from ADR-0003's original framing ("the backend never needs the OpenAI SDK") — that statement was true for the offline generation pipeline; it isn't true for a live in-game assistant, which can only run inside the service handling the request.

**Prompts stay backend-local**, not shared with `tools/ai-content/prompts/` even though the project spec's monorepo listing groups `generate_hint_v1.md` under `tools/ai-content/prompts/`. `services/api` is an independently deployed, containerized service (`Dockerfile` copies only `app/`) — depending on a sibling project's directory for a file needed at runtime would couple two projects that are supposed to be independently deployable. Backend-local prompts keep that boundary intact; the divergence from the literal file listing is intentional.

**Guardrail design — grounded by construction, not just checked after the fact**:

1. The AI is given `case.public_view()` only — the same `PublicDetectiveCase` type Phase 2 built to structurally omit the solution and private suspect fields. It cannot leak what it was never told. This is stronger than "tell the AI the solution but instruct it not to reveal it," which is vulnerable to prompt injection / jailbreak-style leaks.
2. The AI must respond with `{clueId, commentary}` — it points at ONE of the case's real clues by id and writes commentary about it. The backend looks up that `clueId` against the actual case; an unknown/invented id is rejected outright (satisfies "does not invent facts" / "is grounded in case clues" structurally, not through after-the-fact fact-checking, which would need another AI call).
3. The final hint text always embeds the clue's real, server-controlled text — the AI's only unconstrained output is the short commentary sentence.
4. `HintGuardrailPolicy` (`app/domain/policies/hint_guardrail_policy.py`) scans the **commentary only** (not the combined hint text) for any suspect's **name** (unconditional) or **role** (unless that exact role word is grounded in the specific clue this hint is about). See the "Addendum" below for why the role check is scoped this way and not simpler.
5. **Any failure at any point** — no API key, network error, malformed JSON, missing keys, unknown `clueId`, or a guardrail violation — returns the Phase 3 deterministic fallback hint. The hint endpoint never errors because of the AI; it degrades.

`temperature=0.0` by default, consistent with ADR-0003's Phase 5 finding that a judge/assistant used as a gate should not be flipping behavior between calls.

## Consequences

- Culprit/solution leakage is prevented at three independent layers (never sent to the model; clue-grounding requirement; name/role scrub on the commentary) rather than relying on a single check — if one layer has a gap, the others still catch it.
- `services/api` and `tools/ai-content` now both depend on the OpenAI SDK and both read `OPENAI_API_KEY`, with separate `.env` files — a small duplication (two OpenAI client wrapper modules, near-identical) accepted for the same reason ADR-0003 accepted rule-check duplication: the two projects must stay independently deployable, and the duplication is a few dozen lines, not a shared subsystem.
- The commentary-only guardrail scope means a sufficiently adversarial commentary could still reference a suspect indirectly without using their literal name or a role word (e.g. a physical description). Not addressed — the project spec's own allowed-hint examples are generic enough ("one statement," "a suspect") that the prompt already steers away from this, and the structural grounding (AI never knows the culprit) limits how much damage an indirect reference could even do.

## Addendum: role-checking was dropped, then correctly re-scoped (not just re-added)

First live test against the real API returned the deterministic fallback instead of an AI hint. Diagnosis: the guardrail (checking name-or-role unconditionally) rejected a correctly-grounded commentary — "Take another look at the **visitor** wristband found near the display case" — because "visitor" is also a suspect's role, even though the AI was just quoting the clue's own wording ("a visitor wristband"), not identifying anyone.

**First fix (wrong): drop role-checking entirely, names only.** This "fixed" the false positive but reopened a real gap: this project's own suspect roles (Curator, Night Guard, Visitor) are each unique per case, so a role is exactly as identifying as a name. A hint like "the curator's statement doesn't fit the sensor evidence" names no one and still fully identifies Mara — and the names-only guardrail let it straight through. The project spec's forbidden-hint examples are all name/id-based, but those are *examples*, not an exhaustive definition of the rule ("must not reveal the culprit").

**Second fix (correct): re-add role-checking, scoped by clue grounding.** A role mention is only excused if that exact role word appears in the text of the *specific clue this hint is about* (`referenced_clue_text`, threaded through from `request_hint.py`'s `matching_clue.text`) — i.e. the AI is quoting already-public clue vocabulary for the clue it's pointing at, not using a role to point at a suspect. "The visitor wristband..." paired with the clue "A visitor wristband was found..." is grounded → accepted. "The curator's statement..." paired with a sensor clue that never mentions "curator" is not grounded → rejected. Verified both directions: reverted to the names-only version locally, confirmed `tests/fixtures/hint_guardrail_cases.json`'s two role-based cases failed red, restored the scoped fix, confirmed the same cases pass green, then re-verified live against the real API (3 consecutive real hint requests, including the original "visitor wristband" case, all correctly grounded and accepted).

**The pattern worth naming**: the first reflex to a guardrail producing an inconvenient false positive was to make the check *weaker* (drop a whole category), not to make it *more precise*. That's the cheapest fix and the one most likely to reopen exactly the gap the check existed for. The correct fix took the same amount of code (`referenced_clue_text` parameter, one extra condition) but requires noticing that the check was conflating two different things (a role used as ordinary descriptive vocabulary vs. a role used to identify a person) instead of reacting to "it's too strict" by removing strictness.

No test exercises the real OpenAI-backed `generate_hint` automatically in CI yet (same gap Phase 5 had before a key was provided) — the three manual live checks in this phase (initial verification, the false-positive discovery, and the re-verification after the fix) are the only real-API testing this feature has had.
