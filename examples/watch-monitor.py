#!/usr/bin/env python3
"""Watch monitor: the daily-loop recipe for a scheduled price watch.

The loop, run once per day by a scheduler:

    pickup -> recall -> work -> remember -> wrap

The work step checks BTC and ETH with live_price. The remember step
saves the day's prices as the new baseline together with the watch
rule, so tomorrow's run compares against remembered numbers instead
of re-deriving them, and flags any move of 3 percent or more.

Cost of one run: pickup (1) + recall (1) + two price checks (2) +
remember (1) = 5 of the day's 20 free calls, plus the free wrap-up.
No API key, no signup. Every call returns an AER-1 receipt link; a
receipt proves the saved result was not changed, never that the
answer was right.

Run it:  python3 watch-monitor.py
First live run of this pattern, with its receipts:
https://rambozambodotdev.gitlab.io/aer1-hub/scheduled-agent-heartbeat.html
"""

import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

MCP_URL = os.environ.get("ZAMBO_MCP_URL", "https://zambo.dev/mcp")
AGENT_ID = os.environ.get("ZAMBO_AGENT_ID", "watch-monitor-agent")
AGENT_NAME = os.environ.get("ZAMBO_AGENT_NAME", "Watch Monitor Agent")
SESSION_ID = os.environ.get("ZAMBO_SESSION_ID", "watch-monitor-daily")
SYMBOLS = [
    s.strip().upper()
    for s in os.environ.get("ZAMBO_WATCH_SYMBOLS", "BTC,ETH").split(",")
    if s.strip()
]
ALERT_PERCENT = os.environ.get("ZAMBO_ALERT_PERCENT", "3")

# The caller handle is your agent's continuity identity. The server
# says to keep it private, so it lives in a local state file, never
# in git. Each example keeps its own state file so the recipes run
# as separate agents side by side.
STATE_FILE = Path(__file__).with_name(".zambo-state-watch-monitor.json")

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


def spot_price(result):
    # The live_price text leads with the spot price: "BTC . $76,711.00".
    match = re.search(r"\$([0-9,]+\.[0-9]{2})", result_text(result))
    return match.group(1) if match else "unknown"


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

    # 2. Recall: the watch rule and the last baseline this agent saved.
    show(
        "recall",
        client.call_tool(
            "memory_recall",
            {
                "query": "watch rule, alert threshold, last baseline",
                "_session_id": SESSION_ID,
            },
        ),
    )

    # 3. Work: check each watched asset once.
    prices = {}
    for symbol in SYMBOLS:
        result = show(
            f"work {symbol}",
            client.call_tool("live_price", {"symbol": symbol}),
        )
        prices[symbol] = spot_price(result)

    # 4. Remember: today's prices become tomorrow's baseline, saved
    # together with the rule so the comparison survives the night.
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    baseline = ", ".join(f"{s} ${p}" for s, p in prices.items())
    show(
        "remember",
        client.call_tool(
            "memory_remember",
            {
                "fact": f"Watch baseline {stamp}: {baseline} via "
                f"live_price. Watch rule: flag any move of "
                f"{ALERT_PERCENT} percent or more against this "
                "baseline on the next run.",
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
                "recipient": "Watch Monitor (next run)",
                "goal": "Keep a daily price watch whose baseline and "
                "rule live in memory, not in the prompt.",
                "summary": f"Watch run {stamp}: picked up, recalled, "
                f"checked {baseline}, saved the new baseline and the "
                f"{ALERT_PERCENT} percent rule, wrapped.",
                "next_steps": [
                    "Pick up this handover tomorrow, recall the "
                    "baseline, recheck the same assets, and remember "
                    "the new baseline."
                ],
                "_session_id": SESSION_ID,
            },
        ),
    )
    print("loop complete: pickup, recall, work, remember, wrap.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
