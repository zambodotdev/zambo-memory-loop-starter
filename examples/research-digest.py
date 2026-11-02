#!/usr/bin/env python3
"""Research digest: the daily-loop recipe for a one-line market brief.

The loop, run once per day by a scheduler:

    pickup -> recall -> work -> remember -> wrap

The work step checks each watched asset once with live_price. The
remember step saves a single takeaway line, the prices and the 24
hour moves, so tomorrow's digest opens by recalling yesterday's
line and only has to report the change. A digest that remembers
itself never repeats a story it already sent.

Cost of one run with the default two assets: pickup (1) + recall
(1) + two price checks (2) + remember (1) = 5 of the day's 20 free
calls, plus the free wrap-up. No API key, no signup. Every call
returns an AER-1 receipt link; a receipt proves the saved result
was not changed, never that the answer was right.

Run it:  python3 research-digest.py
Set ZAMBO_DIGEST_SYMBOLS to watch your own list, for example
ZAMBO_DIGEST_SYMBOLS=SOL,DOGE.
"""

import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

MCP_URL = os.environ.get("ZAMBO_MCP_URL", "https://zambo.dev/mcp")
AGENT_ID = os.environ.get("ZAMBO_AGENT_ID", "research-digest-agent")
AGENT_NAME = os.environ.get("ZAMBO_AGENT_NAME", "Research Digest Agent")
SESSION_ID = os.environ.get("ZAMBO_SESSION_ID", "research-digest-daily")
SYMBOLS = [
    s.strip().upper()
    for s in os.environ.get("ZAMBO_DIGEST_SYMBOLS", "BTC,ETH").split(",")
    if s.strip()
]

# The caller handle is your agent's continuity identity. The server
# says to keep it private, so it lives in a local state file, never
# in git. Each example keeps its own state file so the recipes run
# as separate agents side by side.
STATE_FILE = Path(__file__).with_name(".zambo-state-research-digest.json")

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


def result_text(result):
    parts = []
    for block in result.get("content") or []:
        if block.get("type") == "text":
            parts.append(block.get("text", ""))
    return "\n".join(parts)


def headline(result):
    # The digest line for one asset: its first result line, without
    # the market-cap tail. "BTC . $76,711.00 USD, down 1.31% (24h)".
    for line in result_text(result).splitlines():
        line = line.strip()
        if line:
            return line.split(" · Market cap")[0].strip()
    return "no result"


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

    # 2. Recall: yesterday's takeaway, so today's digest reports the
    # change instead of repeating the story.
    show(
        "recall",
        client.call_tool(
            "memory_recall",
            {
                "query": "research digest topics, watched assets, "
                "last takeaway",
                "_session_id": SESSION_ID,
            },
        ),
    )

    # 3. Work: one live price per watched asset.
    lines = []
    for symbol in SYMBOLS:
        result = show(
            f"work {symbol}",
            client.call_tool("live_price", {"symbol": symbol}),
        )
        lines.append(headline(result))

    # 4. Remember: the whole digest as one takeaway line, saved for
    # tomorrow's recall.
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    takeaway = f"Research digest takeaway {stamp}: " + "; ".join(lines)
    show(
        "remember",
        client.call_tool(
            "memory_remember",
            {
                "fact": takeaway,
                "agent_name": AGENT_NAME,
                "_session_id": SESSION_ID,
            },
        ),
    )

    # 5. Wrap: seal the run as a verifiable handover. The wrap-up is
    # the day's free one; the next run picks it up for free.
    show(
        "wrap",
        client.call_tool(
            "handover",
            {
                "recipient_type": "agent",
                "recipient": "Research Digest (next run)",
                "goal": "A daily asset digest whose takeaway line is "
                "remembered and compared tomorrow.",
                "summary": f"Research digest run {stamp}: picked "
                f"up, recalled, checked {', '.join(SYMBOLS)}, "
                "remembered the takeaway, wrapped.",
                "next_steps": [
                    "Pick up this handover tomorrow, recall the "
                    "last takeaway, recheck the same assets, and "
                    "remember the new takeaway with the change."
                ],
                "_session_id": SESSION_ID,
            },
        ),
    )
    print("loop complete: pickup, recall, work, remember, wrap.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
