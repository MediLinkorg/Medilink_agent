from __future__ import annotations

import json
import requests
from typing import Any

from .config import ANTHROPIC_API_KEY, CLAUDE_MODEL, AUTOREC_SERVICE_URL

TOOLS = [
    {
        "name": "recommend_doctors",
        "description": "Recommend doctors from the local Alexandria database using cold-start ranking plus AutoRec if available.",
        "input_schema": {
            "type": "object",
            "properties": {
                "user_query": {"type": "string"},
                "user_id": {"type": "string"},
                "specialty_slug": {"type": "string"},
                "area": {"type": "string"},
                "max_fee_egp": {"type": "integer"},
                "max_wait_minutes": {"type": "integer"},
                "top_k": {"type": "integer", "minimum": 1, "maximum": 10},
                "use_autorec": {"type": "boolean"}
            },
            "required": ["user_query"]
        }
    },
    {
        "name": "log_interaction",
        "description": "Log user behavior so AutoRec can learn from clicks, booking intents, bookings, cancellations, and ratings.",
        "input_schema": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
                "doctor_cache_id": {"type": "integer"},
                "event_type": {"type": "string", "enum": ["impression", "shortlist", "click", "view_profile", "book_intent", "booked", "cancelled", "rating"]},
                "rating_value": {"type": "number", "minimum": 1, "maximum": 5},
                "source": {"type": "string"}
            },
            "required": ["user_id", "doctor_cache_id", "event_type"]
        }
    }
]

SYSTEM_PROMPT = """
You are a medical appointment recommendation agent for Alexandria, Egypt.

Rules:
- Always call recommend_doctors before naming doctors.
- Explain results as best database matches, not guaranteed medically best doctors.
- Do not claim live availability. Tell the user that fee/time/availability must be refreshed before booking.
- Before booking, require explicit confirmation of doctor, date, time, fee, patient name, and phone.
- For emergencies or severe symptoms, advise urgent/emergency care instead of routine booking.
- Log useful behavior with log_interaction when the user clicks, shortlists, asks to book, books, cancels, or rates.
""".strip()


def _dispatch_tool(name: str, payload: dict[str, Any]) -> Any:
    if name == "recommend_doctors":
        response = requests.post(f"{AUTOREC_SERVICE_URL}/recommend", json=payload, timeout=15)
        response.raise_for_status()
        return response.json().get("results", [])
    if name == "log_interaction":
        response = requests.post(f"{AUTOREC_SERVICE_URL}/interaction", json=payload, timeout=5)
        response.raise_for_status()
        return response.json()
    return {"error": f"unknown tool: {name}"}


def run_claude_agent(message: str, user_id: str | None = None, max_tool_rounds: int = 5) -> str:
    if not ANTHROPIC_API_KEY:
        raise RuntimeError("Missing ANTHROPIC_API_KEY. Add it to .env or export it in your shell.")
    try:
        from anthropic import Anthropic
    except Exception as exc:
        raise RuntimeError("Install the SDK first: pip install -r requirements.txt") from exc

    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    user_content = message if not user_id else f"user_id={user_id}\n{message}"
    messages: list[dict[str, Any]] = [{"role": "user", "content": user_content}]
    for _ in range(max_tool_rounds):
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1600,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )
        messages.append({"role": "assistant", "content": response.content})
        tool_results = []
        for block in response.content:
            if getattr(block, "type", None) == "tool_use":
                try:
                    result = _dispatch_tool(block.name, dict(block.input))
                except Exception as exc:
                    result = {"error": str(exc)}
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result, ensure_ascii=False),
                })
        if not tool_results:
            return "\n".join(getattr(b, "text", "") for b in response.content if getattr(b, "type", None) == "text").strip()
        messages.append({"role": "user", "content": tool_results})
    return "Tool loop reached the safety limit. Try a more specific request."

