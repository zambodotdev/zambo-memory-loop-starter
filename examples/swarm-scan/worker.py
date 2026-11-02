#!/usr/bin/env python3
"""Swarm scan, worker: one agent's piece of a coordinated swarm job.

A swarm job on Zambo is one shared job id plus one identity per agent.
The worker:

    contribute -> remember -> wrap -> hand the coordinator the link

It checks one asset with live_price under the shared job id, saves the
finding to memory under the same job, then wraps the contribution into
a handover addressed to the coordinator and drops a small JSON note in
contributions/ so the coordinator can pick the handover up.

Cost of one run: the price check (1) + the memory save (1) = 2 of the
day's 20 free calls, plus the free wrap-up. No API key, no signup.
Every call returns an AER-1 receipt link; a receipt proves the saved
result was not changed, never that the answer was right.

Run it (after the coordinator opens the job):
    ZAMBO_AGENT_ID=worker-btc ZAMBO_SYMBOL=BTC python3 worker.py
    ZAMBO_AGENT_ID=worker-eth ZAMBO_SYMBOL=ETH python3 worker.py
    ZAMBO_AGENT_ID=worker-sol ZAMBO_SYMBOL=SOL python3 worker.py

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
AGENT_ID = os.environ.get("ZAMBO_AGENT_ID", "worker-btc")
AGENT_NAME = os.environ.get("ZAMBO_AGENT_NAME", "Worker " + AGENT_ID.rsplit("-", 1)[-1].upper())
JOB_ID = os.environ.get("ZAMBO_SESSION_ID", "swarm-scan-demo")
SYMBOL = os.environ.get("ZAMBO_SYMBOL", "BTC").upper()
COORDINATOR = os.environ.get("ZAMBO_COORDINATOR_NAME", "Swarm Coordinator")

HERE = Path(__file__).parent
# Step zero: the caller handle is this agent's continuity identity.
# One state file per agent, kept private, never in git. Two workers
# sharing one handle are one agent as far as memory and quota go.
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
        # The caller handle rides in the arguments, the quota handle
        # in _meta, and the agent's name as the caller label, so the
        # shared job's record attributes every step to this agent.
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


def result_text(result):
    parts = []
    for block in result.get("content") or []:
        if block.get("type") == "text":
            parts.append(block.get("text", ""))
    return "\n".join(parts)


def main():
    client = ZamboClient()
    client.initialize()
    print(f"session open; caller handle bound for agent '{AGENT_ID}'")

    # 1. Contribute: one real call under the shared job id.
    price_result = client.call_tool(
        "live_price", {"symbol": SYMBOL, "_session_id": JOB_ID}
    )
    price_receipt = receipt_link(price_result)
    headline = result_text(price_result).splitlines()[0] if result_text(price_result) else SYMBOL
    print(f"[contribute] {headline}  receipt: {price_receipt}")

    # 2. Remember: the finding, with the work's receipt inside it, so
    # the finding and its proof travel together.
    remember_result = client.call_tool(
        "memory_remember",
        {
            "fact": f"{AGENT_ID} contribution to job {JOB_ID}: {headline}. "
            f"Price receipt: {price_receipt}.",
            "agent_name": AGENT_NAME,
            "_session_id": JOB_ID,
        },
    )
    remember_receipt = receipt_link(remember_result)
    print(f"[remember] ok  receipt: {remember_receipt}")

    # 3. Wrap the contribution for the coordinator. A handover call
    # without a summary and a recipient is refused, receipted.
    wrap_result = client.call_tool(
        "handover",
        {
            "summary": f"{AGENT_ID} contribution to job {JOB_ID}: {headline}. "
            f"Price receipt: {price_receipt}. Finding saved to memory "
            f"under the shared job (receipt {remember_receipt}).",
            "goal": "One swarm job, every contribution receipted and "
            "verifiable by the coordinator at pickup.",
            "recipient": COORDINATOR,
            "recipient_type": "agent",
            "next_steps": [
                "Coordinator: pick this handover up (free), read the "
                "contribution from the record, and chain it into the "
                "swarm wrap."
            ],
            "_session_id": JOB_ID,
        },
    )
    structured = wrap_result.get("structuredContent") or {}
    handover_id = structured.get("handover_id")
    if not handover_id:
        print("wrap did not return a handover id; see the raw result:")
        print(json.dumps(wrap_result, indent=2)[:1200])
        return 1
    handover_url = f"https://zambo.dev/handover/{handover_id}"
    print(f"[wrap] handover: {handover_url}")

    # 4. Leave the coordinator a rendezvous note (local file; the
    # handover link is the deliverable, this is just the doorbell).
    CONTRIB_DIR.mkdir(exist_ok=True)
    note = {
        "agent_id": AGENT_ID,
        "symbol": SYMBOL,
        "headline": headline,
        "price_receipt": price_receipt,
        "remember_receipt": remember_receipt,
        "handover_id": handover_id,
        "handover_url": handover_url,
    }
    (CONTRIB_DIR / f"{AGENT_ID}.json").write_text(json.dumps(note, indent=2))
    print(f"contribution note written: contributions/{AGENT_ID}.json")
    print("worker done: contribute, remember, wrap.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
