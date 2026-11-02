#!/usr/bin/env python3
"""Client delivery log: the daily-loop recipe for logging deliveries.

The loop, run once per delivery (or once per day over the day's jobs):

    pickup -> recall -> work -> remember -> wrap

The work step writes the delivery note with the write tool. The
remember step saves the client, the job reference, and what was
delivered. The wrap seals the note and its receipts into a handover
the client can open, so "did you actually deliver that?" is answered
with a link instead of an argument. A receipt proves the saved
result was not changed; it never proves the work was good, and this
recipe does not pretend otherwise.

The write tool lives on the full tool surface, so this recipe talks
to https://zambo.dev/mcp?full=true by default. The loop tools behave
identically there.

The defaults are a fictional sample, marked as a sample in the note
itself: client "Harbor Lane Bakery (sample client)", job reference
SAMPLE-1042. Set ZAMBO_CLIENT_NAME, ZAMBO_JOB_REF, and
ZAMBO_DELIVERABLE to log a real job.

Cost of one run: pickup (1) + recall (1) + one note written (1) +
remember (1) = 4 of the day's 20 free calls, plus the free wrap-up.
No API key, no signup.

Run it:  python3 client-delivery-log.py
"""

import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# The write tool is on the full surface; the default URL says so.
MCP_URL = os.environ.get("ZAMBO_MCP_URL", "https://zambo.dev/mcp?full=true")
AGENT_ID = os.environ.get("ZAMBO_AGENT_ID", "delivery-log-agent")
AGENT_NAME = os.environ.get("ZAMBO_AGENT_NAME", "Delivery Log Agent")
CLIENT_NAME = os.environ.get(
    "ZAMBO_CLIENT_NAME", "Harbor Lane Bakery (sample client)"
)
JOB_REF = os.environ.get("ZAMBO_JOB_REF", "SAMPLE-1042")
DELIVERABLE = os.environ.get(
    "ZAMBO_DELIVERABLE",
    "a one-page website refresh summary and three social post "
    "drafts, all samples",
)
NOTE_DETAILS = os.environ.get(
    "ZAMBO_NOTE_DETAILS",
    "Fictional sample for a delivery-log demonstration. Mark the "
    "note as a sample.",
)
SESSION_ID = os.environ.get(
    "ZAMBO_SESSION_ID", f"delivery-log-{JOB_REF.lower()}"
)

# The caller handle is your agent's continuity identity. The server
# says to keep it private, so it lives in a local state file, never
# in git. Each example keeps its own state file so the recipes run
# as separate agents side by side.
STATE_FILE = Path(__file__).with_name(".zambo-state-delivery-log.json")

RUN_URL_RE = re.compile(r"https://zambo\.dev/run/[0-9a-f-]{36}")


class ZamboClient:
    """Minimal MCP client over streamable HTTP, standard library only."""

    def __init__(self):
        self.session_id = None
        self.caller_handle = self._load_saved_handle()
        self.quota_handle = None
        self._next_id = 0

    # -- state ---------------------------------------------------------
    def _load_saved_handle(self):
        # Reuse yesterday's handle so memory and continuity stay bound
        # to the same agent identity across daily runs.
        try:
            data = json.loads(STATE_FILE.read_text())
            return data.get("caller_handle")
        except Exception:
            return None

    def _save_handle(self):
        if self.caller_handle:
            STATE_FILE.write_text(
                json.dumps({"caller_handle": self.caller_handle}, indent=2)
            )

    # -- transport -----------------------------------------------------
    def _post(self, payload, expect_response=True):
        body = json.dumps(payload).encode()
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "X-Agent-Id": AGENT_ID,
            "X-Agent-Name": AGENT_NAME,
        }
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        req = urllib.request.Request(MCP_URL, data=body, headers=headers)
        with urllib.request.urlopen(req, timeout=60) as resp:
            if self.session_id is None:
                self.session_id = resp.headers.get("Mcp-Session-Id")
            header_handle = resp.headers.get("X-Zambo-Caller-Handle")
            raw = resp.read().decode()
        if header_handle and not self.caller_handle:
            self.caller_handle = header_handle
        if not expect_response:
            return None
        return self._parse_rpc(raw)

    @staticmethod
    def _parse_rpc(raw):
        # The endpoint answers plain JSON or an SSE stream; take the
        # last JSON-RPC message either way.
        message = None
        for line in raw.splitlines():
            line = line.strip()
            if line.startswith("data:"):
                try:
                    message = json.loads(line[5:])
                except Exception:
                    pass
        if message is None:
            message = json.loads(raw)
        if "error" in message:
            raise RuntimeError(f"MCP error: {message['error']}")
        return message.get("result", {})

    # -- protocol ------------------------------------------------------
    def initialize(self):
        # Step zero: open a session and capture the server-issued
        # caller handle. Presenting it on every later call keeps one
        # daily free-call counter and one memory store per agent.
        result = self._post(
            {
                "jsonrpc": "2.0",
                "id": self._id(),
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": AGENT_NAME, "version": "0.1.0"},
                },
            }
        )
        meta = result.get("_meta", {})
        if not self.caller_handle:
            self.caller_handle = meta.get("caller_handle")
        self.quota_handle = meta.get("quota_handle")
        self._save_handle()
        self._post(
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            expect_response=False,
        )
        return result

    def call_tool(self, name, arguments):
        # One tool call. The caller handle rides in the arguments, the
        # quota handle in _meta, exactly as the server instructs.
        args = dict(arguments)
        if self.caller_handle:
            args["_caller_handle"] = self.caller_handle
        params = {"name": name, "arguments": args}
        if self.quota_handle:
            params["_meta"] = {"quota_handle": self.quota_handle}
        result = self._post(
            {
                "jsonrpc": "2.0",
                "id": self._id(),
                "method": "tools/call",
                "params": params,
            }
        )
        handle = (result.get("structuredContent") or {}).get("caller_handle")
        if handle and not self.caller_handle:
            self.caller_handle = handle
            self._save_handle()
        return result

    def _id(self):
        self._next_id += 1
        return self._next_id


def receipt_link(result):
    # Pull the AER-1 receipt URL out of a tool result, if one came back.
    structured = result.get("structuredContent") or {}
    for key in ("receipt_url", "run_url", "url"):
        value = structured.get(key)
        if isinstance(value, str) and "/run/" in value:
            return value
    text = json.dumps(result)
    match = RUN_URL_RE.search(text)
    return match.group(0) if match else None


def show(step, result):
    link = receipt_link(result)
    print(f"[{step}] ok" + (f"  receipt: {link}" if link else ""))
    return result


def main():
    client = ZamboClient()
    client.initialize()
    print(f"session open; caller handle bound for agent '{AGENT_ID}'")

    # 1. Pickup: read the job's continuity state. Pickup is free.
    show(
        "pickup",
        client.call_tool(
            "continuity_get_recent",
            {"limit": 10, "_session_id": SESSION_ID},
        ),
    )

    # 2. Recall: what was already delivered on this job, so the log
    # extends the record instead of restarting it.
    show(
        "recall",
        client.call_tool(
            "memory_recall",
            {
                "query": "client delivery log, open jobs, last "
                "delivery note",
                "_session_id": SESSION_ID,
            },
        ),
    )

    # 3. Work: write the delivery note for this job.
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    show(
        "work",
        client.call_tool(
            "write",
            {
                "topic": f"Delivery note to a sample client: "
                f"{CLIENT_NAME}. Job ref {JOB_REF}. Delivered "
                f"today: {DELIVERABLE}. State what was delivered, "
                "give the job ref, and name the next step: client "
                "review.",
                "task": "email",
                "length": "short",
                "tone": "professional",
                "audience": "small business owner",
                "details": NOTE_DETAILS,
                "_session_id": SESSION_ID,
            },
        ),
    )

    # 4. Remember: the client, the job reference, and what went out,
    # so the next session recalls the delivery without reopening it.
    show(
        "remember",
        client.call_tool(
            "memory_remember",
            {
                "fact": f"Client delivery log: {CLIENT_NAME}, job "
                f"ref {JOB_REF}. A delivery note was written via "
                f"the write tool and this job was wrapped on "
                f"{stamp}. Delivered: {DELIVERABLE}. Next step on "
                "the job: client review.",
                "agent_name": AGENT_NAME,
                "_session_id": SESSION_ID,
            },
        ),
    )

    # 5. Wrap: seal the note and its receipts into a handover the
    # client can open. The wrap-up is the day's free one.
    show(
        "wrap",
        client.call_tool(
            "handover",
            {
                "recipient_type": "human",
                "recipient": CLIENT_NAME,
                "goal": f"Log each delivery for job {JOB_REF} so the "
                "client and the next session share one record.",
                "summary": f"Delivery log run {stamp}: picked up, "
                f"recalled, wrote the delivery note for job "
                f"{JOB_REF}, remembered the job reference, wrapped "
                "the note and its receipts into this handover.",
                "next_steps": [
                    "Client reviews the delivery; the next session "
                    "picks up this handover and logs the follow-up "
                    "delivery the same way."
                ],
                "_session_id": SESSION_ID,
            },
        ),
    )
    print("loop complete: pickup, recall, work, remember, wrap.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
