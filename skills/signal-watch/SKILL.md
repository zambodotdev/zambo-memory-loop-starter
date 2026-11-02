---
name: signal-watch
description: Run a recurring signal watch on Zambo: save a baseline to memory under your own caller handle, check the signal against it on a schedule, apply a stated threshold rule, save every reading either way, and wrap a digest handover when the rule fires (and a quiet-day digest when it does not). Use when you watch prices, leads, mentions, or any signal that must be checked again tomorrow: a watch that recurs, remembers, and reports only on real movement. The memory and the record live on Zambo (endpoint https://zambo.dev/mcp); your own scheduler runs the passes.
---

# Signal watch on Zambo

You are a watcher: an agent that checks the same signal again and
again, on a schedule, and speaks only when something real moved. The
failure mode of watchers is not missing the move; it is crying wolf on
noise, forgetting yesterday's baseline, and leaving no record that the
quiet days were checked at all. This pattern fixes all three. The
baseline lives in memory under your own handle. The rule is stated in
the same fact, in plain words. Every reading is saved either way. And
every pass ends in a digest handover: an alert when the rule fires, a
quiet-day digest when it does not.

Zambo is where the watch's memory and record live, at
https://zambo.dev/mcp. It does not run your schedule: your cron, your
agent loop, or your operator's runner starts each pass. Zambo is where
the baseline, the readings, and the proof sit between passes.

This skill ships inside the zambo-watch package. Next to it you will
find `watch.py`, the runnable watcher (baseline mode and check mode),
a no-code paste for a chat agent, and RUN.md, the record of a real
watch run on the live endpoint with every receipt live.

## Step zero: your handle is your memory

On initialize, the endpoint issues a caller handle (in the initialize
result and the `X-Zambo-Caller-Handle` header). Save it in your own
state file before doing anything else, and present it as
`_caller_handle` on every call, with your agent name as
`_caller_label`. Your memory keys to that handle: the baseline you save
today is recallable tomorrow only under the same handle. Lose it and
you come back as a stranger with no baseline and a fresh allowance.
One handle per watch, never shared.

## The pattern

One watch = one job id (a `_session_id` string you pick once and reuse
on every pass). Three moves, repeated:

1. Baseline (first pass only). Read the signal. Save ONE fact with
   `memory_remember`: the values, the source receipts, and the rule in
   plain words (for example: alert when any watched asset moves 3
   percent or more from its baseline). Keep the remember receipt; it
   is the anchor every later move is measured from.
2. Check (every later pass). `memory_recall` the baseline and read the
   values back out of the recalled fact. Read the signal again.
   Compute the move for each watched item and apply the rule exactly
   as stated: no rounding a 2.9 into a 3, no alerting on a hunch. Save
   the reading with `memory_remember` either way, alert or quiet.
3. Wrap the digest. `handover` with a summary, a goal, a recipient,
   and next steps. When the rule fires, the summary leads with the
   alert and the size of the move. When it does not, use the quiet
   format: the prices, the moves, and the words "no alert", so a
   reader can tell a checked quiet day from a day the watch never
   ran. Wrapping is the day's free wrap-up and leaves the call counter
   untouched.

A wrap needs its inputs: a `handover` call without a summary and a
recipient is refused, receipted. That refusal is a feature: a digest
is a deliverable being published, and it is held to that standard.

## What to watch

Anything with a readable signal and a baseline worth remembering:

- Prices: `live_price` on assets, as in RUN.md (BTC, ETH, SOL against
  a 3 percent rule).
- Leads: a repeating scan whose hits are the signal; the baseline is
  the last run's source set, and new sources are the movement.
- Mentions and coverage: the baseline is what was already on the
  record; the alert is a new mention that was not there yesterday.
- Your own numbers: receipts, downloads, callers. The baseline is last
  week's saved total; the rule is the change you actually care about.

In each case the discipline is identical: the baseline is a remembered
fact with its receipts inside it, the rule is stated inside the same
fact, and the reading is saved whether or not the rule fires.

## The accounting (why this shape, in numbers)

Free tier, per agent: 20 calls + 1 wrap-up free every day, keyed to
your own caller handle; picking up a handover is always free. The run
in RUN.md cost 4 counted calls for the baseline pass (3 prices + the
baseline save) and 5 per check pass (the recall, 3 prices, the reading
save); the digest wrap was free. Run once a day, a three-signal watch
costs 5 counted calls a day after day one, well inside the free tier.
When a watch outgrows free, the line is per agent: a Day Pass is $0.99
for that agent, unlimited for 24 hours; the Zambo Pass is $29 for that
agent for 30 days. Both are one-time payments, never subscriptions.
Entry point for a human setting this up: https://zambo.dev/add/

## Scheduling note

Zambo does not start your passes. Wire `watch.py check` (or the paste
below, handed to a chat agent on a loop) to whatever already wakes
you: a cron line, your framework's scheduler, a daily standup job. One
caution from the record: one check per scheduled pass. A watch that
checks five times an hour spends its allowance proving nothing moved;
a watch that checks once a day and saves every reading builds the
record that makes the alert believable when it finally fires.

## The family

This package is one of five agent patterns that run on Zambo. Its
sibling, shipped first, is the swarm package: many agents on one job,
each contribution verified from its receipt before the coordinator
trusts it. A watch is often the signal a swarm then works.

- Swarm package (PyPI): https://pypi.org/project/zambo-swarm/
- Swarm package (GitHub): https://github.com/zambodotdev/zambo-swarm-coordination

(Family section: the remaining sibling packages join this list in the
interconnection pass, when all five are live.)

## What this does not do

A receipt proves the saved result was not changed since it was saved;
it does not prove the price was right or the signal was read well.
Zambo does not pick your threshold: a 3 percent rule on prices is the
worked example, and the right number for your signal is yours to set
and to state in the baseline fact, where a reader can argue with it.

## Go deeper

- Full guide, with this run and the accounting:
  https://rambozambodotdev.gitlab.io/aer1-hub/signal-watch-package.html
- This package: https://github.com/zambodotdev/zambo-signal-watch
- The heartbeat recipe (the loop family this watch grows from):
  https://rambozambodotdev.gitlab.io/aer1-hub/scheduled-agent-heartbeat.html
- Setup for the human who runs you: https://zambo.dev/add/
