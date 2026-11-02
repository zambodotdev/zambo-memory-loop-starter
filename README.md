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
