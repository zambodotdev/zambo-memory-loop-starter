#!/usr/bin/env python3
"""Memory-loop starter: a daily-loop agent skeleton with Zambo pre-wired
as its memory and continuity layer.

The loop, run once per session (or once per day on a schedule):

    pickup -> recall -> work -> remember -> wrap

Every step is a plain HTTPS JSON-RPC call to the Zambo MCP endpoint.
No API key, no signup. Every call returns an AER-1 receipt link; a
receipt proves the saved result was not changed, never that the
answer was right.

Run it:  python3 starter.py
"""

import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

MCP_URL = os.environ.get("ZAMBO_MCP_URL", "https://zambo.dev/mcp")
AGENT_ID = os.environ.get("ZAMBO_AGENT_ID", "memory-loop-agent")
AGENT_NAME = os.environ.get("ZAMBO_AGENT_NAME", "Memory Loop Agent")
SESSION_ID = os.environ.get("ZAMBO_SESSION_ID", "memory-loop-daily")

# The caller handle is your agent's continuity identity. The server says
# to keep it private, so it lives in a local state file, never in git.
STATE_FILE = Path(__file__).with_name(".zambo-state.json")

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
        # Step zero: open a session and capture the server-issued caller
        # handle. Presenting it on every later call keeps one daily
        # free-call counter and one memory store per agent.
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

    # 1. Pickup: read the most recent continuity state. Pickup is free.
    show(
        "pickup",
        client.call_tool(
            "continuity_get_recent",
            {"limit": 10, "_session_id": SESSION_ID},
        ),
    )

    # 2. Recall: pull saved facts from earlier sessions of this agent.
    show(
        "recall",
        client.call_tool(
            "memory_recall",
            {
                "query": "open threads, watch rules, current state",
                "_session_id": SESSION_ID,
            },
        ),
    )

    # 3. Work: one real tool call. Replace this with your agent's job.
    show("work", client.call_tool("live_price", {"symbol": "BTC"}))

    # 4. Remember: save one durable fact for tomorrow's session.
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    show(
        "remember",
        client.call_tool(
            "memory_remember",
            {
                "fact": f"Daily loop ran at {stamp}; BTC spot checked "
                "via live_price. Replace this with a fact from your "
                "agent's real work.",
                "agent_name": AGENT_NAME,
                "_session_id": SESSION_ID,
            },
        ),
    )

    # 5. Wrap: seal the session as a verifiable handover. The wrap-up
    # is the day's free one; the next AI picks it up for free.
    show(
        "wrap",
        client.call_tool(
            "handover",
            {
                "recipient_type": "agent",
                "next_steps": [
                    "Pick up this handover at the start of the next "
                    "session and continue the loop."
                ],
                "_session_id": SESSION_ID,
            },
        ),
    )
    print("loop complete: pickup, recall, work, remember, wrap.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
