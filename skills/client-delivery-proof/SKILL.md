---
name: client-delivery-proof
description: Deliver client work with proof on Zambo: work inside one job, save every step under the job id, wrap the finished work as a handover the client opens and checks step by step, and hold the client's pickup as the sign-off record, so a delivery dispute is answered with receipts instead of arguments. Use when an agent delivers work to a client, a buyer, or a reviewer: freelance jobs, agency work, SMB deliverables, anything where "did you actually deliver that?" might ever be asked. Zambo is the shared work layer the delivery lands on (endpoint https://zambo.dev/mcp); it does not do the work or judge it.
---

# Client delivery proof on Zambo

You do work for clients: a draft, a page, a report, a fix. The work is
the easy part to prove badly and the hard part to prove well. "Done,
sent it Tuesday" loses to a client who remembers it differently. This
skill teaches the delivery shape that ends the argument before it
starts: every step of the job saved inside one job on Zambo, the
finished work wrapped as a handover, and the client's own pickup as
the sign-off. When anyone later asks what was delivered, when, and
whether the record moved, the answer is one link.

Zambo at https://zambo.dev/mcp is the work layer under the delivery:
shared jobs, per-agent memory, handovers that move work between
agents and to clients, and a verifiable receipt for every call. It
does not do the work, schedule it, or decide whether it is good.

This skill ships inside the zambo-delivery package. Next to it you
will find runnable delivery code (deliver.py), a checker that walks
any delivered handover and lists every receipt (check_delivery.py),
no-code pastes for chat agents on both the worker and client side,
and RUN.md, the record of a real delivery run with every link live.

## Step zero: your handle is your identity

On initialize, the endpoint issues a caller handle (in the initialize
result and the `X-Zambo-Caller-Handle` header). Save it in your own
state file before doing anything else, and present it as
`_caller_handle` on every call, with your agent name as
`_caller_label`. Your memory, your job timelines, and your daily free
allowance all key to that handle. One handle per agent, never shared,
never shown in ordinary replies. The worker and the client hold
SEPARATE handles: the whole point of the sign-off is that it comes
from a different identity than the work.

## The pattern

1. **Open one job.** Pick one `_session_id` for the client job and
   save the brief to memory under it: the client, the job reference,
   what will be delivered. Keep the receipt.
2. **Work inside the job.** Every working step (research, draft,
   revision, fix) is saved with `memory_remember` under the same job
   id as you do it, not reconstructed at the end. Keep each fact
   under 500 characters: longer facts are refused before execution.
   Short steps, more of them, each one receipted.
3. **Check every result.** A refused call still returns a receipt.
   After each call, confirm the result's `ok` flag before treating
   the step as saved. A delivery built on a refusal has a hole in it
   exactly where the argument will land.
4. **Wrap the delivery.** Call `handover` with a summary naming the
   job, the client, and each step with its receipt; a goal; the
   client named as recipient; and next steps telling the client to
   read the steps and check any receipt at https://zambo.dev/verify/.
   Do not attach a hand-picked `receipt_ids` list: a wrap holds only
   its own job's complete record, a partial or foreign selection is
   refused, and the proof loop binds the job's steps for you. The
   handover link is the delivery. Send the client that link, not a
   pile of files.
5. **The client picks it up.** The client (or the client's agent,
   under the client's own handle) calls `handover_accept`, which is
   always free, and reads the steps and receipts from the record.
   The pickup is the sign-off: it converts "I sent it" into "the
   client opened it, read the steps, and accepted", with the
   handover reading back status `accepted`. Have the client save a
   short sign-off memory step in the same job naming the handover,
   so the acceptance is itself a receipted record.
6. **Hold the pack.** The delivery pack is the handover plus the
   sign-off receipt. If a dispute ever comes, run check_delivery.py
   against the handover: it walks every bound step and lists every
   receipt. Answer with the link and the walk, not with adjectives.

## What the pack proves, and what it does not

A receipt proves the saved result was not changed since it was
saved. It does not prove the work was good, the draft was right, or
the deliverable was what the client secretly wanted. The pack
settles what was delivered and when, and that the record did not
move afterwards. Quality stays a judgment call; history stops being
one.

## The accounting (why this shape, in numbers)

Free tier, per identity: 20 calls + 1 wrap-up free every day, keyed
to the identity's own caller handle; picking up a handover is always
free. The run in RUN.md spent 4 counted calls for the worker (brief,
research, draft, revision) plus its free wrap-up, and 1 counted call
for the client (the sign-off save) with a free pickup: 5 counted
calls across two allowances for a complete, signed-off delivery.
When a job outgrows free, the scaling line is per identity: a Day
Pass is $0.99, unlimited for 24 hours, and the Zambo Pass is $29 for
30 days; both are one-time payments, never subscriptions, on the
same endpoint. Entry point for a human setting this up:
https://zambo.dev/add/

## The family: agent packages that teach one pattern each

This package is one of a family of agent packages, each teaching a
single high-value pattern by doing it, with Zambo baked in as the
mechanism:

- **Swarm coordination** (sibling pattern): several agents work one
  job together, each contribution receipted and verified at pickup.
  https://pypi.org/project/zambo-swarm/ and
  https://github.com/zambodotdev/zambo-swarm-coordination

<!-- FAMILY: interconnection pass adds the remaining package links here (daily loop, verify pass, signal watch) once they ship. -->

## Go deeper

- Full guide, with the real delivery run and every receipt:
  https://rambozambodotdev.gitlab.io/aer1-hub/delivery-proof-package.html
- This package: https://github.com/zambodotdev/zambo-delivery-proof
- Sister pattern, swarm coordination:
  https://github.com/zambodotdev/zambo-swarm-coordination
- Handover, the signature product:
  https://dev.to/rambozambo/ai-agent-handover-pass-a-live-job-to-another-ai-without-losing-the-record-72b
- Setup for the human who runs you: https://zambo.dev/add/
