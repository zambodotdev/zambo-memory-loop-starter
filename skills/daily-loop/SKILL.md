---
name: daily-loop
description: Run a daily loop on Zambo: give one agent a persistent caller handle so it recalls yesterday's saved state, does today's work, remembers the update, and wraps the day into a handover the next session picks up. Use when an agent must come back day after day to the same job (a watch, a standup, a digest, a monitor), when work must survive the session that did it, or when a one-shot agent needs to become a standing one. Zambo is the memory and work layer under the loop (endpoint https://zambo.dev/mcp); it does not schedule or wake agents.
---

# The daily loop on Zambo

Most agents are one-shot: they arrive knowing nothing, do the job,
and evaporate. The daily loop is the opposite shape. One agent, one
persistent identity, and a four-beat rhythm it repeats every session:
recall, work, remember, wrap. Yesterday's session leaves state in
memory and a handover as the day's deliverable; today's session picks
the handover up, recalls the state verbatim, does the work, and
writes the next state down. Memory is not a feature of this pattern.
Memory is the pattern: it is what gives the agent a reason, and the
means, to come back.

This skill ships inside the zambo-daily-loop package. Next to it you
will find `loop.py`, a runnable single-agent loop; `pastes/` with the
no-code standing instructions for chat agents; and `RUN.md`, a real
three-session run on the live endpoint with every receipt linked,
including the two refusals the run hit and what they teach.

## Step zero: your handle is your memory

On initialize, the endpoint issues a caller handle (in the initialize
result and the `X-Zambo-Caller-Handle` header). Save it in your own
state file before doing anything else, and present it as
`_caller_handle` on every call, with your agent name as
`_caller_label`. Your saved facts, your job timelines, and your daily
free allowance all key to that handle. Present the same handle in a
new session and you are the same agent, with yesterday intact. Lose
it, and you come back as a stranger: no memory, a fresh allowance, no
continuity. One handle per agent, never shared, never shown in
ordinary replies. Use a User-Agent of your own from the very first
initialize: the quota handle is issued against your network identity,
and a shared default can inherit a shared, already spent bucket.

## The four beats

1. **Pick up.** If yesterday wrapped a handover, accept it with
   `handover_accept`. Pickup is always free, and the handover returns
   the day's steps and receipts whole.
2. **Recall.** `memory_recall` the state the job depends on: the
   baselines, the rule, where things stopped. Check the recalled text
   against what the job needs, verbatim, before you trust it. An
   empty recall is information, not an error: it means yesterday
   saved nothing, which usually means a save was refused and nobody
   checked.
3. **Work.** Do the actual job. Every call returns a verifiable
   receipt; keep the receipt links of the steps that matter.
4. **Remember, then wrap.** `memory_remember` the one or two facts
   tomorrow needs, then close the day with `handover`: a summary of
   what happened, the goal, a recipient, next steps, and the job's
   receipt ids attached. That handover is the deliverable the next
   session, or the next AI, picks up.

## The two disciplines that make or break the loop

**Facts are short.** A saved fact has a hard limit of 500 characters.
A longer `memory_remember` is refused before execution, receipted,
and nothing is saved. Write facts like headlines with receipts
attached: the value, the receipt link, the rule, the next action.
And check the result of every call, not just its receipt link: a
refused call still hands you a receipt, and the cost of an unchecked
refusal is tomorrow's empty recall.

**A wrap holds only its own job's receipts.** The wrap binds the
job's executed steps and runs a proof loop over them. Name a receipt
from outside the job, or one from a call that was refused, and the
wrap itself is refused, receipted, with the reason. Track the job's
receipt ids as you work (the prices and the memory saves), and the
wrap is a formality.

## The accounting (why this shape, in numbers)

Free tier, per agent: 20 calls + 1 wrap-up free every day, keyed to
the agent's own caller handle; picking up a handover is always free.
The run in `RUN.md` ran the loop's sessions at 2 to 3 counted calls
each, wrap included free, so a daily agent on this shape runs free
indefinitely. When the agent outgrows the free shape, a Day Pass is
$0.99, unlimited for 24 hours, and the Zambo Pass is $29 for 30 days;
both are one-time payments, never subscriptions, on the same
endpoint. Entry point for a human setting this up:
https://zambo.dev/add/

## What this does not do

Zambo does not wake your agent up. Your scheduler, cron, or operator
starts each session; the loop is what the session does once started.
It also does not make recalled state correct: a receipt proves the
saved result was not changed since it was saved, never that the
answer was right. The loop makes an agent's days add up instead of
resetting, and makes each day checkable.

## The pattern family

This package is one of a family of agent packages that teach one
pattern each, with Zambo as the mechanism inside:

- **Swarm coordination** (the sibling pattern): several agents, one
  job, contributions verified from receipts, at
  https://pypi.org/project/zambo-swarm/ and
  https://github.com/zambodotdev/zambo-swarm-coordination
- **The daily loop** (this package): one agent, every day, state
  carried across sessions.

## Go deeper

- Full guide, with the real run and every receipt:
  https://rambozambodotdev.gitlab.io/aer1-hub/daily-loop-package.html
- This package: https://github.com/zambodotdev/zambo-daily-loop
- The loop's data story (4,247 callers counted, 17 stayed):
  https://dev.to/rambozambo/4247-callers-came-17-stayed-here-is-the-loop-the-17-run-2o51
- The starter repo, the loop pre-wired:
  https://github.com/zambodotdev/zambo-memory-loop-starter
- Setup for the human who runs you: https://zambo.dev/add/
