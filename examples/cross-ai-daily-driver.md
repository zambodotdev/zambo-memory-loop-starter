# Cross-AI daily driver: the loop split across two AIs

For people and agents who switch AIs every day: start the work in one
AI, wrap it, pick it up in the other AI, keep going. No code in this
file: the pattern, the two standing instructions, and the accounting.

## How the bridge works

The handover is the bridge. When the first AI wraps, the job's steps,
their receipts, a plain summary, and written next steps are sealed
into one record with a link. Picking that record up in the second AI
is always free, whichever AI wrapped it.

Each AI keeps its own caller handle: the handle the endpoint issues
when that AI connects, kept in that AI's own notes and presented on
every call. Memory is keyed to a handle, so the second AI does not
automatically share the first AI's memory store. The handover
carries the facts across instead: its summary and next steps are
written to be read by the next AI, and the second standing
instruction below has the receiving AI save those facts into its own
memory on pickup. The job's record travels whole; each side keeps
its own key to it.

## Standing instruction for the AI you start in

Paste this into the first AI, with the endpoint added
(https://zambo.dev/mcp; the two-minute setup is
https://zambo.dev/add/):

```
Standing instructions for work done in this AI:
1. Connect to https://zambo.dev/mcp and present the caller handle saved in this conversation; if none is saved, take the one the endpoint issues and save it here.
2. Pick up the job with continuity_get_recent, then memory_recall for the standing facts.
3. Do the work. Keep the receipt link of every call in your notes.
4. Before we switch AIs, memory_remember what the other AI must know, then wrap with handover: a plain summary, the receipts, and the next steps written for the receiving AI.
5. Give me the handover link. That link is the whole handoff; nothing else needs to move.
```

## Standing instruction for the AI you pick up in

```
Standing instructions for picking up work from another AI:
1. Connect to https://zambo.dev/mcp and present the caller handle saved in this conversation; if none is saved, take the one the endpoint issues and save it here.
2. Pick up the handover I give you. Picking up is always free.
3. memory_recall for your own standing facts, then memory_remember the facts the handover carries, so your memory holds them too.
4. Continue the work from the handover's next steps. Keep every receipt link.
5. When we switch back, wrap again with handover and give me the new link.
```

## What one day costs

Counted per AI, against that AI's own daily free allowance:

- Wrapping in the first AI: the wrap-up is that AI's free one for
  the day (0 of its 20 calls).
- Picking up in the second AI: free, always (0 calls).
- Recall and remember on each side: 1 call each on that side.
- The work itself: as many calls as the job takes, spent on
  whichever side does the work.

A normal switch day lands between 4 and 10 calls per side, inside
the free tier on both: 20 calls + 1 wrap-up free every day. Picking
up in another AI is always free.

## See a handover before you trust the pattern

Two public handovers from the Zambo team's own work, openable by
anyone:

- An open handover, 5 steps:
  https://zambo.dev/handover/bd7e5325-33fd-4c5e-b029-76b781fa2f51
- An accepted handover, 4 steps, with its chain root:
  https://zambo.dev/handover/45434a17-4afc-486a-9646-e689bcee4297

Each step carries its receipt, and a receipt proves the saved result
was not changed since it was saved. It never proves the answer was
right; the receiving AI still reads the work before it builds on it.

The fuller treatment, with the pickup mechanics step by step:
https://rambozambodotdev.gitlab.io/aer1-hub/pick-up-your-work-in-another-ai.html
