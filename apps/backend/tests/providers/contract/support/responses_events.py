"""SSE event builders for the fake Responses upstream.

CANDIDATE VOCABULARY. The repository has no recorded evidence of a *successful* stream
from the fixed CLI: the 2026-09-17 probe's fake service deliberately answered 401, so
it only proved that the request was routed and shaped correctly (research section
6.1). The event names and payload keys below follow the documented Responses streaming
shape and must be confirmed against the fixed CLI in the contract layer before
anything depends on them.

Keeping every name in this one module is deliberate: if the fixed CLI disagrees, this
file is the only place to change, and the contract test pins the sequence the proxy
must handle."""

from __future__ import annotations

import json
from collections.abc import Iterator

SSE_PREFIX = "event: "
SSE_DATA = "data: "


def _frame(event: str, payload: dict) -> bytes:
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    return f"{SSE_PREFIX}{event}\n{SSE_DATA}{body}\n\n".encode()


def _created(response_id: str, model: str) -> bytes:
    return _frame(
        "response.created",
        {"type": "response.created", "response": {"id": response_id, "model": model}},
    )


def completed(
    response_id: str, model: str, text: str, usage: dict | None
) -> list[bytes]:
    """A plain text answer: created, one message item, a delta, completed."""
    return [
        _created(response_id, model),
        _frame(
            "response.output_item.added",
            {
                "type": "response.output_item.added",
                "output_index": 0,
                "item": {"type": "message", "role": "assistant", "content": []},
            },
        ),
        _frame(
            "response.output_text.delta",
            {"type": "response.output_text.delta", "output_index": 0, "delta": text},
        ),
        _frame(
            "response.output_item.done",
            {
                "type": "response.output_item.done",
                "output_index": 0,
                "item": {
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": text}],
                },
            },
        ),
        _frame(
            "response.completed",
            {
                "type": "response.completed",
                "response": {
                    "id": response_id,
                    "model": model,
                    "status": "completed",
                    "usage": usage,
                },
            },
        ),
    ]


def tool_call(
    response_id: str, model: str, name: str, arguments: str, usage: dict | None = None
) -> list[bytes]:
    """One function call, so the CLI can run a tool and send the result back."""
    call_id = f"call_{response_id}"
    return [
        _created(response_id, model),
        _frame(
            "response.output_item.added",
            {
                "type": "response.output_item.added",
                "output_index": 0,
                "item": {
                    "type": "function_call",
                    "call_id": call_id,
                    "name": name,
                    "arguments": arguments,
                },
            },
        ),
        _frame(
            "response.output_item.done",
            {
                "type": "response.output_item.done",
                "output_index": 0,
                "item": {
                    "type": "function_call",
                    "call_id": call_id,
                    "name": name,
                    "arguments": arguments,
                    "status": "completed",
                },
            },
        ),
        _frame(
            "response.completed",
            {
                "type": "response.completed",
                "response": {
                    "id": response_id,
                    "model": model,
                    "status": "completed",
                    "usage": usage,
                },
            },
        ),
    ]


def incomplete(response_id: str, model: str, reason: str) -> list[bytes]:
    """A truncated answer: ends on an incomplete event, never on completed."""
    return [
        _frame(
            "response.incomplete",
            {
                "type": "response.incomplete",
                "response": {
                    "id": response_id,
                    "model": model,
                    "status": "incomplete",
                    "incomplete_details": {"reason": reason},
                },
            },
        )
    ]


def as_bytes(events: list[bytes]) -> Iterator[bytes]:
    yield from events
