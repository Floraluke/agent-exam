"""Read the terminal event out of an upstream SSE answer, within a fixed budget.

Only one thing in the stream is interpreted: the event that says the answer ended, and
the usage it reports. Everything else is passed through untouched, so a mismatch between
this parser and the fixed CLI cannot corrupt what the task container sees.

The bytes are upstream input, so parsing is defensive and total: a malformed frame, an
odd type or a negative count means "no usage", never an exception into the request path.
A stream that never ends leaves the scanner at its byte cap; the caller then treats the
usage as unknown, which errs toward charging the whole hold instead of nothing.

Event names are the candidate vocabulary recorded in the contract layer and are
reconciled against the fixed CLI there.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from eval_platform.domain.result import UsageSummary

TERMINAL_EVENTS = ("response.completed", "response.incomplete")
MAX_SCAN_BYTES = 256 * 1024
FRAME_SEPARATOR = b"\n\n"
EVENT_PREFIX = b"event:"
DATA_PREFIX = b"data:"


@dataclass(frozen=True, slots=True)
class Terminal:
    """The terminal event's name and the usage it carried, if any."""

    event: str
    usage: UsageSummary | None


class TerminalScanner:
    """Accumulates frames until the terminal event appears; never grows unbounded."""

    def __init__(self, max_bytes: int = MAX_SCAN_BYTES) -> None:
        self._max_bytes = max_bytes
        self._buffer = bytearray()
        self._terminal: Terminal | None = None
        self._overflowed = False

    @property
    def terminal(self) -> Terminal | None:
        return self._terminal

    @property
    def overflowed(self) -> bool:
        """True once the cap was hit with no terminal event: usage stays unknown."""

        return self._overflowed

    def feed(self, chunk: bytes) -> None:
        """Take one relayed chunk; stop buffering once decided or over budget."""

        if self._terminal is not None or self._overflowed:
            return
        self._buffer.extend(chunk)
        while True:
            index = self._buffer.find(FRAME_SEPARATOR)
            if index < 0:
                break
            frame = bytes(self._buffer[:index])
            del self._buffer[: index + len(FRAME_SEPARATOR)]
            found = _terminal_of(frame)
            if found is not None:
                self._terminal = found
                self._buffer.clear()
                return
        if len(self._buffer) > self._max_bytes:
            self._overflowed = True
            self._buffer.clear()


def _terminal_of(frame: bytes) -> Terminal | None:
    name: bytes | None = None
    data = bytearray()
    for line in frame.split(b"\n"):
        if line.startswith(EVENT_PREFIX):
            name = line[len(EVENT_PREFIX) :].strip()
        elif line.startswith(DATA_PREFIX):
            # Single-line JSON in practice; joining without a separator keeps a
            # hypothetical split payload from turning into two invalid halves.
            data.extend(line[len(DATA_PREFIX) :].strip())
    if name is None or not data:
        return None
    event = name.decode("utf-8", "replace")
    if event not in TERMINAL_EVENTS:
        return None
    return Terminal(event, _usage_of(_response_of(bytes(data))))


def _response_of(raw: bytes) -> Mapping[str, Any] | None:
    try:
        parsed = json.loads(raw)
    except (UnicodeDecodeError, ValueError):
        return None
    if not isinstance(parsed, dict):
        return None
    response = parsed.get("response")
    return response if isinstance(response, dict) else None


def _usage_of(response: Mapping[str, Any] | None) -> UsageSummary | None:
    """Map the upstream usage report, or answer None so the caller charges the hold."""

    if response is None:
        return None
    raw = response.get("usage")
    if not isinstance(raw, Mapping):
        # A completion that reports no usage is not a completion that cost nothing.
        return None
    input_tokens = _count(raw.get("input_tokens"))
    output_tokens = _count(raw.get("output_tokens"))
    if input_tokens is None or output_tokens is None:
        return None
    return UsageSummary(
        n_input_tokens=input_tokens,
        n_cache_tokens=_cached_tokens(raw),
        n_output_tokens=output_tokens,
    )


def _cached_tokens(raw: Mapping[str, Any]) -> int | None:
    details = raw.get("input_tokens_details")
    if not isinstance(details, Mapping):
        return None
    return _count(details.get("cached_tokens"))


def _count(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    counted: int = value
    return counted
