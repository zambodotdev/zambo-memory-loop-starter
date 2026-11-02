---
name: verify-pass
description: Run a verification pass over another agent's work on Zambo: take a claim plus its receipt link, check the receipt at the v2 verify endpoint (GET https://zambo.dev/api/v2/receipt/{id}/verify), open the saved record, compare the claim against what was actually saved, and record a verdict (verified or mismatch) as its own receipted step. Use when you are handed work, a summary, a number, or a handover from another agent or a tool and need to check it before relying on it, forwarding it, or paying for it. Trust the record, not the retelling.
---

# The verify pass on Zambo

Another agent just handed you a result: a number, a summary, a finished
piece of work. The cheapest failure in multi-agent work is forwarding
that result on faith, because retellings drift: a digit changes, a
qualifier drops, a confident sentence replaces the actual output. The
verify pass is the habit that catches the drift. You take the claim
plus its receipt link, you check the receipt, you open the saved
record, and you compare the claim against what was actually saved.
Then you record your verdict as its own receipted step, so the next
agent can check your checking.

This skill ships inside the zambo-verify-pass package. Next to it you
will find verify.py (a runnable verifier), a no-code paste for chat
agents, and RUN.md, the record of a real two-agent run in which a wrong
retelling was caught by exactly this pass.

## The pass, step by step

1. **Get the receipt link with the claim.** No receipt link, no
   verification: the claim is not checked, and you say so. A claim
   whose receipt cannot be produced is `absent`, not verified.
2. **Check the receipt at the v2 verify endpoint.**
   `GET https://zambo.dev/api/v2/receipt/{id}/verify` returns
   `verification_status` and a `checks` map. The binding checks
   (commitment_matches, canonical_payload_matches, provenance_binding,
   metadata_binding) recompute whether the saved result was changed
   after it was saved. Entries marked `not_checked` were not evaluated;
   never report them as passed.
3. **Open the saved record.** The endpoint response carries the
   receipt's committed output (inside its canonical bytes). Read what
   the work actually saved, not the summary of it you were handed.
4. **Compare the claim against the saved record.** Does the number,
   the name, the outcome in the claim appear in the saved output,
   exactly? A claim that matches a record whose verification_status is
   `verified` earns the verdict **verified**. A claim that does not
   match the saved record earns **mismatch**, even when the record
   itself verifies fine: the record is intact, the retelling is wrong.
   That distinction is the whole lesson. Trust the record, not the
   retelling.
5. **Record the verdict as its own receipted step.** Save the verdict
   with `memory_remember` under your own caller handle: the claim you
   checked, the receipt you checked it against, the endpoint's
   verification_status, what the saved record says, and your verdict.
   Anyone downstream can now audit the pass itself.

## Step zero still applies: your handle is your identity

On initialize, the endpoint issues a caller handle. Save it in your own
state file and present it as `_caller_handle` on every call, with your
agent name as `_caller_label`. Your verdicts are recorded under your
handle; a verifier who loses its handle leaves verdicts nobody can
attribute. Picking up a handover is always free, and the verify
endpoint is a plain HTTPS read that costs no quota at all, so a
verification pass is nearly free: in the run in RUN.md the verifier
spent 2 counted calls (the two verdict records) on the whole pass.

## If the work arrives as a handover

Pick it up with `handover_accept` (always free). The pickup returns the
producer's saved steps and receipts from the record itself. Verify the
load-bearing receipt (the work call, not the summary), compare the
handover's summary against the saved steps, and record the verdict the
same way. `verify.py --handover <link>` in this package walks a
handover's steps and verifies each receipt for you.

## The verdict vocabulary, used exactly

- **verified**: the receipt's verification_status is verified AND the
  claim matches the saved record.
- **mismatch**: the record was opened and the claim does not match
  what was saved (whatever the endpoint status).
- **verification failed**: the endpoint's checks fail on the record
  itself.
- **not checked**: the pass was not run, or a check was not evaluated.
- **absent**: no receipt was produced for the claim.

Never upgrade a verdict: not_checked is not a pass, and a verified
record under a wrong claim is a mismatch, not a verification.

## What a receipt does and does not prove

A receipt proves the saved result was not changed since it was saved.
It never proves the answer was right: a producer can save a wrong
price with a perfectly valid receipt. The verify pass checks fidelity
(the record matches the claim, and the record is intact), not truth.
Judging whether the work was the right work stays with you.

## What it costs

Free tier, per agent, keyed to each agent's own caller handle: 20
calls + 1 wrap-up free every day; picking up a handover is always free
and the verify endpoint read is free. Past free: a Day Pass is $0.99
for one agent, unlimited for 24 hours; the Zambo Pass is $29 for one
agent for 30 days. Both are one-time payments, never subscriptions.
Entry point for a human setting this up: https://zambo.dev/add/

## The package family

This package is one of a family of agent packages that teach a pattern
by doing, with Zambo as the mechanism inside each. Sibling pattern:

- Swarm coordination: split one job across a coordinator and workers,
  each piece verified from its receipt before it is trusted.
  https://pypi.org/project/zambo-swarm/ and
  https://github.com/zambodotdev/zambo-swarm-coordination

(The interconnection pass extends this section as the rest of the
family ships.)

## Go deeper

- Full guide, with the real two-agent run and the caught retelling:
  https://rambozambodotdev.gitlab.io/aer1-hub/verify-pass-package.html
- This package: https://github.com/zambodotdev/zambo-verify-pass
- Verify any receipt in a browser: https://zambo.dev/verify/
- Setup for the human who runs you: https://zambo.dev/add/
