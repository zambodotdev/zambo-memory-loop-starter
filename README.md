# Zambo Memory Loop Starter

A daily-loop agent starter with [Zambo](https://zambo.dev) pre-wired as
its memory and continuity layer. Clone it, run it, and your agent starts
every session by picking up where the last one stopped, recalls what it
saved, does its work, remembers what matters, and wraps the session as a
verifiable handover for the next run.

No API key. No signup. Nothing to configure.

## The loop

```
 +---------+    +---------+    +---------+    +-----------+    +---------+
 | PICKUP  |--->| RECALL  |--->|  WORK   |--->| REMEMBER  |--->|  WRAP   |
 +---------+    +---------+    +---------+    +-----------+    +---------+
      ^                                                              |
      +------------ the next session picks up the wrap ------------+
```

1. **Pickup**: `continuity_get_recent` reads the latest continuity
   state. Picking up is always free.
2. **Recall**: `memory_recall` pulls the facts this agent saved in
   earlier sessions.
3. **Work**: real tool calls. The starter runs one example,
   `live_price`, in place of your agent's actual job.
4. **Remember**: `memory_remember` saves one durable fact, so tomorrow's
   session starts smarter than today's.
5. **Wrap**: `handover` seals the session as a verifiable handover. The
   next session, or a different AI entirely, picks it up for free.

Run the loop daily and the memory compounds: the cost of leaving grows
with every day of saved history. That compounding is the point.

## Quickstart

```bash
git clone https://github.com/zambodotdev/zambo-memory-loop-starter.git
cd zambo-memory-loop-starter
python3 starter.py
```

That is the whole setup. The script speaks plain HTTPS JSON-RPC to the
Zambo MCP endpoint, standard library only, and prints the AER-1 receipt
link for every step as it runs.

Optional environment variables:

- `ZAMBO_AGENT_ID` and `ZAMBO_AGENT_NAME`: your agent's identity
  (defaults: `memory-loop-agent` / `Memory Loop Agent`).
- `ZAMBO_SESSION_ID`: a stable job ID that binds the loop's calls into
  one ledger (default: `memory-loop-daily`).
- `ZAMBO_MCP_URL`: override the endpoint (default:
  `https://zambo.dev/mcp`).

On first run the starter saves the server-issued caller handle to
`.zambo-state.json` and reuses it on every later run. That handle is
your agent's continuity identity: it keeps one daily free-call counter
and one memory store per agent. Keep it private; it is gitignored by
default and is not a payment credential.

## Pick your use case

The loop is one shape; only the work step changes. Each recipe below
is pre-built for an everyday job: a runnable file with the loop
already wired, its standing instruction ready to paste, and its
free-tier cost counted. Copy one file, run it, change nothing
structural. Every recipe was run live before it was listed here;
the receipts are on the use-case page:
https://rambozambodotdev.gitlab.io/aer1-hub/the-loop-by-use-case.html

### Watch monitor: [examples/watch-monitor.py](examples/watch-monitor.py)

A scheduled agent checks BTC and ETH once a day and remembers the
baseline, so an alert means a real move against remembered numbers.
One run: 5 of the 20 free calls, plus the free wrap-up.

Standing instruction:

```
1. Connect to https://zambo.dev/mcp and present your saved caller handle.
2. Pick up the job with continuity_get_recent, then memory_recall for the watch rule and the last baseline.
3. Check the watched assets with live_price.
4. Compare against the baseline and flag any move of 3 percent or more.
5. memory_remember the new baseline and whether an alert fired, then wrap with handover.
```

### Lead watch: [examples/lead-watch.py](examples/lead-watch.py)

A daily scan for public demand signals in one trade and one city,
with the criteria remembered so a quiet day and a busy day are both
on the record. One run: 4 of the 20 free calls, plus the free
wrap-up, and one of leadsignal's own 3 free daily scans.

Standing instruction:

```
1. Connect to https://zambo.dev/mcp and present your saved caller handle.
2. Pick up the job with continuity_get_recent, then memory_recall for the watch criteria.
3. Run leadsignal for the watched trade and city.
4. memory_remember the criteria and what the scan found, including an empty result, then wrap with handover.
```

### Research digest: [examples/research-digest.py](examples/research-digest.py)

A one-line daily brief on the assets you follow: prices checked,
the takeaway remembered, and tomorrow's digest written against
yesterday's line instead of repeating it. One run with two assets:
5 of the 20 free calls, plus the free wrap-up.

Standing instruction:

```
1. Connect to https://zambo.dev/mcp and present your saved caller handle.
2. Pick up the job with continuity_get_recent, then memory_recall for the last takeaway.
3. Check each watched asset with live_price.
4. Write the one-line takeaway and memory_remember it with the prices, then wrap with handover.
```

### Client delivery log: [examples/client-delivery-log.py](examples/client-delivery-log.py)

Every delivery gets a written note, a remembered job reference, and
a wrapped handover the client can open, so delivery is a link, not
an argument. Defaults are a fictional sample, marked as a sample.
One run: 4 of the 20 free calls, plus the free wrap-up.

Standing instruction:

```
1. Connect to https://zambo.dev/mcp?full=true and present your saved caller handle.
2. Pick up the job with continuity_get_recent, then memory_recall for past deliveries on it.
3. Write the delivery note with the write tool.
4. memory_remember the client, the job reference, and what was delivered, then wrap with handover and send the client the link.
```

### Cross-AI daily driver: [examples/cross-ai-daily-driver.md](examples/cross-ai-daily-driver.md)

No code: the loop split across two AIs for people who switch models
daily. Wrap in the first AI, pick up free in the second, keep
working. The file carries the standing instruction for both sides
and the per-side accounting.

## Run a small swarm: [examples/swarm-scan/](examples/swarm-scan/)

One job, several agents, every contribution proven. A coordinator
opens one shared job; each worker runs under its own caller handle,
does one piece, remembers the finding with its receipt, and wraps the
contribution into a handover. The coordinator picks each handover up
for free, reads the worker's actual steps and receipts from the
record instead of trusting summaries, and wraps the swarm into one
handover that names every worker and its receipts. Zambo is the work
layer under the swarm, not the orchestrator: your scripts run the
agents, Zambo is where their work lands and gets proven.

```bash
# 1. The coordinator opens the shared job
python3 examples/swarm-scan/coordinator.py open

# 2. Each worker contributes, in its own terminal, under its own identity
ZAMBO_AGENT_ID=worker-btc ZAMBO_SYMBOL=BTC python3 examples/swarm-scan/worker.py
ZAMBO_AGENT_ID=worker-eth ZAMBO_SYMBOL=ETH python3 examples/swarm-scan/worker.py
ZAMBO_AGENT_ID=worker-sol ZAMBO_SYMBOL=SOL python3 examples/swarm-scan/worker.py

# 3. The coordinator picks every contribution up, verifies, and wraps
python3 examples/swarm-scan/coordinator.py wrap
```

Each agent keeps its own state file (`.zambo-state-<agent>.json`,
never committed): one handle per agent is what keeps each agent's
memory and free allowance its own. The cost of the whole pattern is
2 counted calls per agent (the work and the memory save); pickups and
wrap-ups are free, so this swarm runs inside the free tier. When one
agent outgrows it, the scaling line is per agent: a Day Pass is $0.99
for that agent, unlimited for 24 hours, and the Zambo Pass is $29 for
that agent for 30 days, both one-time payments. The same pattern as
an installable skill file: [skills/swarm-coordination/SKILL.md](skills/swarm-coordination/SKILL.md).
The full guide, with a real four-agent run and every receipt:
https://rambozambodotdev.gitlab.io/aer1-hub/swarm-coordination-on-zambo.html
Start free: https://zambo.dev/add/

## Using an MCP client instead

This repo ships a `.mcp.json` with the Zambo server already entered:

```json
{
  "mcpServers": {
    "zambo": {
      "type": "http",
      "url": "https://zambo.dev/mcp"
    }
  }
}
```

Point any MCP client at the same endpoint and give your agent the loop
as a standing instruction: session start is pickup plus recall, session
end is remember plus wrap. Two-minute setup walkthrough:
https://zambo.dev/add/

## The facts

- MCP endpoint: https://zambo.dev/mcp (153 tools, 36 on the default
  surface, no key required).
- Free tier: 20 calls + 1 wrap-up free every day. Picking up in another
  AI is always free.
- Day Pass: $0.99 for unlimited calls for 24 hours. Zambo Pass: $29 for
  30 days, one payment.
- Every call returns an AER-1 receipt (IETF Internet-Draft
  draft-zambo-aer1-26). A receipt proves the saved result was not
  changed. It never proves the answer was right, and the starter does
  not pretend otherwise: check any receipt yourself at
  https://zambo.dev/verify/.

## Go deeper

- The scheduled-agent version of this loop, with a real worked run and
  its receipts: the heartbeat recipe at
  https://rambozambodotdev.gitlab.io/aer1-hub/scheduled-agent-heartbeat.html
- The morning shape of the same loop, a standup that reads what your
  agents did overnight, with receipts:
  https://rambozambodotdev.gitlab.io/aer1-hub/morning-standup-continuity.html
- The switching shape: start in one AI, pick the work up in another,
  free:
  https://rambozambodotdev.gitlab.io/aer1-hub/pick-up-your-work-in-another-ai.html
- The data behind the loop, counted from the public receipt stream:
  4,247 callers came, 17 stayed:
  https://dev.to/rambozambo/4247-callers-came-17-stayed-here-is-the-loop-the-17-run-2o51
- Add Zambo to any AI in two minutes: https://zambo.dev/add/

## License

MIT, Copyright (c) 2026 Brennan Zambo. See LICENSE.
