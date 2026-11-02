#!/usr/bin/env python3
"""Swarm scan, coordinator: opens the shared job, then verifies and
wraps what the workers contributed.

Two phases, because the workers run between them:

    python3 coordinator.py open    # open the job, save the brief
    # ... each worker runs worker.py in its own terminal ...
    python3 coordinator.py wrap    # pick every contribution up, read
                                   # it from the record, wrap the swarm

The coordinator never assembles from worker summaries. Each pickup
(handover_accept, always free) returns the worker's saved steps and
receipts, and the final wrap names each worker, its result, and its
receipts, with the contribution receipt ids attached as evidence.

Cost across both phases: the opening remember (1) = 1 of the day's 20
free calls, plus the free wrap-up. Pickups are free. No API key, no
signup. Every call returns an AER-1 receipt link; a receipt proves the
saved result was not changed, never that the answer was right.

The pattern, taught end to end with a real run and its receipts:
https://rambozambodotdev.gitlab.io/aer1-hub/swarm-coordination-on-zambo.html
"""

import json
import os
import re
import sys
import urllib.request
from pathlib import Path

MCP_URL = os.environ.get("ZAMBO_MCP_URL", "https://zambo.dev/mcp")
AGENT_ID = os.environ.get("ZAMBO_AGENT_ID", "swarm-coordinator")
AGENT_NAME = os.environ.get("ZAMBO_AGENT_NAME", "Swarm Coordinator")
JOB_ID = os.environ.get("ZAMBO_SESSION_ID", "swarm-scan-demo")
WORKERS = [
    w.strip()
    for w in os.environ.get("ZAMBO_WORKERS", "worker-btc,worker-eth,worker-sol").split(",")
    if w.strip()
]

HERE = Path(__file__).parent
# Step zero: one state file for the coordinator's own caller handle,
# separate from every worker's. Handles are identities; never share.
STATE_FILE = HERE / f".zambo-state-{AGENT_ID}.json"
CONTRIB_DIR = HERE / "contributions"

RUN_URL_RE = re.compile(r"https://zambo\.dev/run/[0-9a-f-]{36}")


class ZamboClient:
    """Minimal MCP client over streamable HTTP, standard library only."""

    def __init__(self):
        self.session_id = None
        self.caller_handle = self._load_saved_handle()
        self.quota_handle = None
        self._next_id = 0

    def _load_saved_handle(self):
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

    def initialize(self):
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
        args = dict(arguments)
        if self.caller_handle:
            args["_caller_handle"] = self.caller_handle
        args.setdefault("_caller_label", AGENT_ID)
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
    structured = result.get("structuredContent") or {}
    for key in ("receipt_url", "run_url", "url"):
        value = structured.get(key)
        if isinstance(value, str) and "/run/" in value:
            return value
    match = RUN_URL_RE.search(json.dumps(result))
    return match.group(0) if match else None


def open_job(client):
    # Open the shared job: the assignment brief, saved to memory under
    # the job id, receipted like every other step of the swarm.
    brief = (
        f"Swarm job {JOB_ID} opened. One shared job, one identity per "
        f"agent. Workers: {', '.join(WORKERS)}. Each worker checks its "
        "asset with live_price under this job id, remembers the finding "
        "with its receipt, and wraps the contribution for the "
        "coordinator. Coordinator picks each handover up, reads the "
        "record, and wraps the swarm."
    )
    result = client.call_tool(
        "memory_remember",
        {"fact": brief, "agent_name": AGENT_NAME, "_session_id": JOB_ID},
    )
    print(f"[open] job {JOB_ID}  receipt: {receipt_link(result)}")
    print("now run each worker, then: python3 coordinator.py wrap")
    return 0


def wrap_job(client):
    notes = []
    for worker in WORKERS:
        note_file = CONTRIB_DIR / f"{worker}.json"
        if not note_file.exists():
            print(f"missing contribution note for {worker}: run worker.py first")
            return 1
        notes.append(json.loads(note_file.read_text()))

    # Pick every contribution up and read it from the record. Pickup
    # is always free; the accept returns the worker's saved steps and
    # receipts, which is the verification, not the worker's summary.
    last_handover_id = None
    for note in notes:
        result = client.call_tool(
            "handover_accept",
            {
                "handover_id": note["handover_id"],
                "agent_name": AGENT_NAME,
                "_session_id": JOB_ID,
            },
        )
        seen = note["price_receipt"] in json.dumps(result)
        print(
            f"[pickup] {note['agent_id']}: accepted; contribution "
            f"receipt in the record: {seen}"
        )
        last_handover_id = note["handover_id"]

    # Wrap the swarm: one handover whose summary names each worker,
    # its result, and its receipts, evidence attached, chained off
    # the last pickup. This handover is the deliverable.
    summary_lines = [
        f"Swarm job {JOB_ID} complete: {len(notes)} workers under one "
        "shared job, every contribution receipted."
    ]
    receipt_ids = []
    for note in notes:
        summary_lines.append(
            f"{note['agent_id']}: {note['headline']} "
            f"(price receipt {note['price_receipt']}; finding "
            f"remembered, receipt {note['remember_receipt']})."
        )
        for url in (note["price_receipt"], note["remember_receipt"]):
            if url:
                receipt_ids.append(url.rsplit("/", 1)[-1])
    result = client.call_tool(
        "handover",
        {
            "summary": " ".join(summary_lines),
            "goal": "One swarm job, every contribution receipted and "
            "verifiable by anyone holding the link.",
            "recipient": "Swarm Operator",
            "recipient_type": "human",
            "next_steps": [
                "Open any step's receipt and check it at "
                "https://zambo.dev/verify/. A receipt proves the saved "
                "result was not changed."
            ],
            "receipt_ids": receipt_ids,
            "continue_from": last_handover_id,
            "_session_id": JOB_ID,
        },
    )
    structured = result.get("structuredContent") or {}
    handover_id = structured.get("handover_id")
    print(f"[wrap] swarm handover: https://zambo.dev/handover/{handover_id}")
    print(f"[wrap] wrap receipt: {receipt_link(result)}")
    print("coordinator done: open, verify at pickup, wrap.")
    return 0


def main():
    phase = sys.argv[1] if len(sys.argv) > 1 else ""
    if phase not in ("open", "wrap"):
        print("usage: python3 coordinator.py open|wrap")
        return 2
    client = ZamboClient()
    client.initialize()
    print(f"session open; caller handle bound for agent '{AGENT_ID}'")
    return open_job(client) if phase == "open" else wrap_job(client)


if __name__ == "__main__":
    sys.exit(main())
