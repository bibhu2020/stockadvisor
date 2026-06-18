"""Base agent: Claude Sonnet 4.6 → GPT-4o → Gemini fallback chain."""
import json
import os
import re
from typing import Any, Callable

import anthropic
from openai import OpenAI

# ── Singletons ────────────────────────────────────────────────────────────────
_anthropic_client: anthropic.Anthropic | None = None
_openai_client: OpenAI | None = None
_gemini_client: OpenAI | None = None

ANTHROPIC_MODEL = "claude-sonnet-4-6"
OPENAI_MODEL    = "gpt-4o"
GEMINI_MODEL    = "gemini-2.0-flash"


def _get_anthropic_client() -> anthropic.Anthropic | None:
    global _anthropic_client
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        return None
    if _anthropic_client is None:
        _anthropic_client = anthropic.Anthropic(api_key=key)
    return _anthropic_client


def _get_openai_client() -> OpenAI | None:
    global _openai_client
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        return None
    if _openai_client is None:
        _openai_client = OpenAI(api_key=key)
    return _openai_client


def _get_gemini_client() -> OpenAI | None:
    global _gemini_client
    key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not key:
        return None
    if _gemini_client is None:
        _gemini_client = OpenAI(
            api_key=key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        )
    return _gemini_client


# ── Tool wrapper ──────────────────────────────────────────────────────────────
class Tool:
    def __init__(self, func: Callable, description: str, parameters: dict):
        self.func = func
        self.name = func.__name__
        self.description = description
        self.parameters = parameters

    def to_openai_schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    def to_anthropic_schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.parameters,
        }

    def call(self, **kwargs) -> Any:
        return self.func(**kwargs)


# ── Base agent ────────────────────────────────────────────────────────────────
class BaseAgent:
    max_tool_rounds = 10

    def __init__(self, role: str, system_prompt: str, tools: list[Tool] | None = None):
        self.role = role
        self.system_prompt = system_prompt
        self.tools = tools or []

    # ── Public entry point ────────────────────────────────────────────────────
    def run(self, user_message: str, context: dict | None = None) -> dict:
        user_content = user_message
        if context:
            user_content = f"Context:\n{json.dumps(context, indent=2, default=str)}\n\n{user_message}"

        tool_map = {t.name: t for t in self.tools}

        # Try providers in order: Anthropic → OpenAI → Gemini
        providers = [
            ("Anthropic",  ANTHROPIC_MODEL, _get_anthropic_client,  self._run_anthropic),
            ("OpenAI",     OPENAI_MODEL,    _get_openai_client,      lambda c, u, m: self._run_openai(c, OPENAI_MODEL, u, m)),
            ("Gemini",     GEMINI_MODEL,    _get_gemini_client,      lambda c, u, m: self._run_openai(c, GEMINI_MODEL, u, m)),
        ]

        last_err: Exception | None = None
        for name, model, get_client, runner in providers:
            client = get_client()
            if client is None:
                print(f"[base_agent] {name} skipped (API key not set)")
                continue
            print(f"[base_agent] [{self.role}] Using {name} ({model})")
            try:
                return runner(client, user_content, tool_map)
            except Exception as exc:
                print(f"[base_agent] {name} failed ({exc}); trying next provider")
                last_err = exc

        raise RuntimeError(f"All AI providers failed. Last error: {last_err}")

    # ── Anthropic loop ────────────────────────────────────────────────────────
    def _run_anthropic(
        self,
        client: anthropic.Anthropic,
        user_content: str,
        tool_map: dict[str, Tool],
    ) -> dict:
        messages: list[dict] = [{"role": "user", "content": user_content}]
        tool_schemas = [t.to_anthropic_schema() for t in self.tools]

        for _ in range(self.max_tool_rounds):
            kwargs: dict = {
                "model": ANTHROPIC_MODEL,
                "max_tokens": 16384,
                "system": self.system_prompt,
                "messages": messages,
            }
            if tool_schemas:
                kwargs["tools"] = tool_schemas

            response = client.messages.create(**kwargs)

            # Collect text and tool-use blocks from the response
            text_blocks = [b for b in response.content if b.type == "text"]
            tool_blocks = [b for b in response.content if b.type == "tool_use"]

            if response.stop_reason == "tool_use" and tool_blocks:
                # Append the assistant's full content block list
                messages.append({"role": "assistant", "content": response.content})

                # Execute each tool and collect results
                tool_results = []
                for tb in tool_blocks:
                    try:
                        result = tool_map[tb.name].call(**tb.input)
                    except Exception as exc:
                        result = {"error": str(exc)}
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tb.id,
                        "content": json.dumps(result, default=str),
                    })
                messages.append({"role": "user", "content": tool_results})
            else:
                if response.stop_reason == "max_tokens":
                    print(
                        f"[base_agent] WARNING: [{self.role}] Anthropic response truncated "
                        f"(stop_reason=max_tokens). JSON will likely be incomplete."
                    )
                # Final text response
                text = text_blocks[0].text if text_blocks else ""
                return self._parse_json(text)

        return {"error": "max tool rounds exceeded"}

    # ── OpenAI-compatible loop (GPT-4o and Gemini) ────────────────────────────
    def _run_openai(
        self,
        client: OpenAI,
        model: str,
        user_content: str,
        tool_map: dict[str, Tool],
    ) -> dict:
        messages: list[dict] = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user",   "content": user_content},
        ]
        tool_schemas = [t.to_openai_schema() for t in self.tools]

        for _ in range(self.max_tool_rounds):
            kwargs: dict = {
                "model": model,
                "messages": messages,
                "temperature": 0,
            }
            # seed is only supported by OpenAI, not Gemini
            if model == OPENAI_MODEL:
                kwargs["seed"] = 42
            if tool_schemas:
                kwargs["tools"] = tool_schemas
                kwargs["tool_choice"] = "auto"

            response = client.chat.completions.create(**kwargs)
            msg = response.choices[0].message

            if msg.tool_calls:
                messages.append(msg)
                for tc in msg.tool_calls:
                    fn_args = json.loads(tc.function.arguments)
                    try:
                        result = tool_map[tc.function.name].call(**fn_args)
                    except Exception as exc:
                        result = {"error": str(exc)}
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(result, default=str),
                    })
            else:
                return self._parse_json(msg.content or "")

        return {"error": "max tool rounds exceeded"}

    # ── JSON parser ───────────────────────────────────────────────────────────
    @staticmethod
    def _parse_json(text: str) -> dict:
        text = text.strip()

        # 1. Direct parse (fastest path — model followed instructions)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 2. Extract from ```json ... ``` or ``` ... ``` fences anywhere in text
        fence_match = re.search(r"```(?:json)?\s*\n([\s\S]*?)\n```", text)
        if fence_match:
            try:
                return json.loads(fence_match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # 3. Find the outermost { ... } block (handles leading/trailing prose)
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                pass

        print(f"[base_agent] WARNING: could not parse JSON from LLM response (len={len(text)})")
        return {"raw": text}
