---
name: swarm-coordination
description: Coordinate a multi-agent swarm on Zambo: split one job across a coordinator and worker agents, give every agent its own caller handle, move work between agents as handovers, verify each contribution from its receipt instead of trusting summaries, and ship one handover as the deliverable. Use when several agents must work one job together, hand pieces to each other, share memory, or prove what each agent did. Zambo is the shared work layer under the swarm (endpoint https://zambo.dev/mcp); it does not schedule or spawn agents.
---

# Swarm coordination on Zambo

You are one agent in a swarm: several agents working one job at once. Zambo
is the shared work layer under the swarm, the place the job, the memory, and
the proof live. It is not an orchestrator: it does not schedule, spawn, or
supervise agents. Your framework or operator runs the agents. Zambo is where
their work lands and gets proven, at https://zambo.dev/mcp.

This skill also ships inside the zambo-swarm-coordination package
(zambo-swarm on PyPI and npm), next to runnable coordinator and worker code,
no-code pastes for chat agents, and RUN.md, the record of a real four-agent
run with every receipt link live. In this starter repo the same pattern is
runnable code at examples/swarm-scan.

## Step zero: your handle is your identity

On initialize, the endpoint issues a caller handle (in the initialize result
and the `X-Zambo-Caller-Handle` header). Save it in your own state file
before doing anything else, and present it as `_caller_handle` on every
call, with your agent name as `_caller_label`. Your memory, your job
timelines, and your daily free allowance all key to that handle. One handle
per agent, never shared, never shown in ordinary replies. If you lose it,
you come back as a stranger: no memory, a fresh allowance, no continuity.
Two agents on one handle are one agent as far as the record is concerned.

## The shared job

One job = one `_session_id` string the coordinator picks and every agent
reuses on every call. It binds the job's ledger together. It is not a shared
inbox: `continuity_get_recent` under the job id returns YOUR OWN timeline
for that job, not the swarm's. Work moves between agents through handovers,
not through shared reads.

## If you are the coordinator

1. Initialize, save your handle (step zero).
2. Open the job: `memory_remember` the assignment brief under the shared
   `_session_id`, one line per worker. Keep the receipt.
3. Hand each worker its piece and the shared job id.
4. As each worker's handover arrives, pick it up with `handover_accept`
   (always free, no quota) and READ its steps and receipts from the record.
   Never assemble the result from worker summaries. Spot-check any receipt
   at https://zambo.dev/verify/ ; a receipt proves the saved result was not
   changed since it was saved, never that the answer was right.
5. Wrap the job with `handover`: a `summary` naming each worker, its
   result, and its receipts; a `goal`; a `recipient`; `next_steps`; attach
   the contribution receipt ids as `receipt_ids`; set `continue_from` to
   the last handover you picked up. That handover is the deliverable: the
   link a client or operator opens to verify the swarm's work. Publishing
   it is the habit the whole pattern exists to build.

## If you are a worker

1. Initialize, save your handle in your own state file (step zero).
2. Work your assigned piece under the shared `_session_id`. Keep the
   receipt link of every call you make.
3. `memory_remember` your finding under the job id, with the work's receipt
   in the fact, so the finding and its proof travel together.
4. Wrap your contribution with `handover`: a `summary` of what you did and
   found, a `goal`, the coordinator as `recipient`, `next_steps`. A handover
   call without a summary and a recipient is refused, receipted. Send the
   coordinator the handover link. That link is your deliverable: the record
   anyone can verify.

## Wrap discipline

A wrap (`handover`) is a deliverable being published, and wrapping is free:
each agent gets 1 free wrap-up per day, and a wrap leaves the call counter
untouched. A wrap runs a proof loop over the job's steps and binds them
into the handover, so the handover's step list carries the contributed
steps with their saved outputs, each step opening to its own receipt.

## The accounting (why this shape, in numbers)

Free tier, per agent: 20 calls + 1 wrap-up free every day, keyed to the
agent's own caller handle; picking up a handover is always free. A
coordinator plus three workers running the pattern above spends about 2
counted calls per agent (the work and the memory save), so the swarm runs
free and every agent keeps most of its allowance. When one agent outgrows
the free shape, the scaling line is per agent too: a Day Pass is $0.99 for
that agent, unlimited for 24 hours, and the Zambo Pass is $29 for that
agent for 30 days; both are one-time payments, never subscriptions, on the
same endpoint. Entry point for a human setting this up:
https://zambo.dev/add/

## What this does not do

Zambo does not make worker output correct, does not choose tools for your
agents, and does not replace your coordinator's judgment. It makes the
swarm's work a shared, checkable record: who did what, what they saved,
and whether the record moved afterwards.

## Go deeper

- Full guide, with the real four-agent run and every receipt:
  https://rambozambodotdev.gitlab.io/aer1-hub/swarm-coordination-on-zambo.html
- This package: https://github.com/zambodotdev/zambo-swarm-coordination
- Runnable swarm code in the starter repo:
  https://github.com/zambodotdev/zambo-memory-loop-starter/tree/main/examples/swarm-scan
- Setup for the human who runs you: https://zambo.dev/add/
