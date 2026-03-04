from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Tuple

from openai import OpenAI
from openai.types.chat import ChatCompletionUserMessageParam

from voice_demo.domain.constants import Route, ROUTE_VALUES
from voice_demo.ports.llm import LLMProviderPort


@dataclass(frozen=True)
class _LLMJsonResult:
    data: dict[str, Any]


class OpenAILLMProvider(LLMProviderPort):
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self._client = OpenAI(api_key=api_key)
        self._model = model

    def _chat_json(self, prompt: str, *, temperature: float) -> dict[str, Any]:
        # Fixes the type warning by using the SDK’s ChatCompletionMessageParam
        messages: list[ChatCompletionUserMessageParam] = [
            ChatCompletionUserMessageParam(
                role="user",
                content=prompt,
            )
        ]

        r = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=temperature,
        )

        text = (r.choices[0].message.content or "").strip()

        # Robust JSON parse: if it isn’t valid JSON, return empty dict
        try:
            parsed = json.loads(text)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}

    def classify_intent(self, transcript: str) -> Tuple[str, float]:
        prompt = (
            "Classify the customer's intent into exactly one of: SUPPORT, SALES, BILLING, HUMAN_AGENT, UNKNOWN.\n"
            'Return ONLY a JSON object like: {"intent": "BILLING", "confidence": 0.0}\n'
            f"Transcript:\n{transcript}\n"
        )

        data = self._chat_json(prompt, temperature=0.0)

        intent_raw = str(data.get("intent", Route.UNKNOWN)).upper()
        conf = float(data.get("confidence", 0.5))

        # Clamp confidence
        conf = max(0.0, min(1.0, conf))

        # Validate intent against centralized set
        if intent_raw not in ROUTE_VALUES:
            intent_raw = Route.UNKNOWN

        return intent_raw, conf

    def generate_suggestion(self, transcript: str) -> Tuple[str, float]:
        prompt = (
            "You are an agent-assist system helping a phone support agent.\n"
            "Write ONE short helpful next sentence the agent could say.\n"
            'Return ONLY JSON: {"suggestion": "...", "confidence": 0.0}\n'
            f"Transcript:\n{transcript}\n"
        )

        data = self._chat_json(prompt, temperature=0.2)

        suggestion = str(
            data.get("suggestion", "Could you tell me a bit more about what you need help with?")
        )
        conf = float(data.get("confidence", 0.6))
        conf = max(0.0, min(1.0, conf))

        return suggestion, conf
