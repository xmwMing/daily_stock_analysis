# -*- coding: utf-8 -*-
"""
Multi-provider LLM Tool-Calling Adapter.

Normalizes function-calling / tool-use across Gemini, OpenAI, and Anthropic
into a unified interface consumed by the AgentExecutor.
"""

import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.config import get_config

logger = logging.getLogger(__name__)


# ============================================================
# Unified response types
# ============================================================

@dataclass
class ToolCall:
    """A single tool call requested by the LLM."""
    id: str
    name: str
    arguments: Dict[str, Any]


@dataclass
class LLMResponse:
    """Normalized response from any LLM provider."""
    content: Optional[str] = None          # text response (final answer)
    tool_calls: List[ToolCall] = field(default_factory=list)  # tool calls to execute
    usage: Dict[str, Any] = field(default_factory=dict)       # token usage info
    provider: str = ""                     # which provider handled this call
    raw: Any = None                        # raw provider response for debugging


# ============================================================
# LLM Tool Adapter
# ============================================================

class LLMToolAdapter:
    """Unified adapter for tool-calling across Gemini / OpenAI / Anthropic.

    Initialization follows the priority order from GeminiAnalyzer:
    Gemini > Anthropic > OpenAI, but all available providers are
    initialized for failover.
    """

    def __init__(self, config=None):
        config = config or get_config()

        # Provider clients (lazy-initialized)
        self._gemini_model = None
        self._anthropic_client = None
        self._openai_client = None

        # Provider availability flags
        self._gemini_available = False
        self._anthropic_available = False
        self._openai_available = False

        # Config
        self._config = config

        # Initialize providers
        self._init_providers()

    def _init_providers(self):
        """Initialize all available LLM providers."""
        config = self._config

        # Gemini
        gemini_key = config.gemini_api_key
        if gemini_key and not gemini_key.startswith("your_") and len(gemini_key) > 10:
            try:
                import google.generativeai as genai
                genai.configure(api_key=gemini_key)
                model_name = config.gemini_model or "gemini-2.5-flash"
                self._gemini_model = genai.GenerativeModel(model_name=model_name)
                self._gemini_available = True
                logger.info(f"Agent LLM: Gemini initialized (model={model_name})")
            except Exception as e:
                logger.warning(f"Agent LLM: Gemini init failed: {e}")

        # Anthropic
        anthropic_key = config.anthropic_api_key
        if anthropic_key and not anthropic_key.startswith("your_") and len(anthropic_key) > 10:
            try:
                from anthropic import Anthropic
                self._anthropic_client = Anthropic(api_key=anthropic_key)
                self._anthropic_available = True
                logger.info("Agent LLM: Anthropic initialized")
            except Exception as e:
                logger.warning(f"Agent LLM: Anthropic init failed: {e}")

        # OpenAI
        openai_key = config.openai_api_key
        if openai_key and not openai_key.startswith("your_") and len(openai_key) > 10:
            try:
                from openai import OpenAI
                client_kwargs = {"api_key": openai_key}
                if config.openai_base_url:
                    client_kwargs["base_url"] = config.openai_base_url
                if config.openai_base_url and "aihubmix.com" in config.openai_base_url:
                    client_kwargs["default_headers"] = {"APP-Code": "GPIJ3886"}
                self._openai_client = OpenAI(**client_kwargs)
                self._openai_available = True
                logger.info("Agent LLM: OpenAI initialized")
            except Exception as e:
                logger.warning(f"Agent LLM: OpenAI init failed: {e}")

    @property
    def is_available(self) -> bool:
        """True if at least one provider is ready."""
        return self._gemini_available or self._anthropic_available or self._openai_available

    @property
    def primary_provider(self) -> str:
        """Name of the highest-priority available provider."""
        if self._gemini_available:
            return "gemini"
        if self._anthropic_available:
            return "anthropic"
        if self._openai_available:
            return "openai"
        return "none"

    # ============================================================
    # Unified call
    # ============================================================

    def call_with_tools(
        self,
        messages: List[Dict[str, Any]],
        tool_declarations: Dict[str, Any],
        provider: Optional[str] = None,
    ) -> LLMResponse:
        """Send messages + tool declarations to LLM, return normalized response.

        Args:
            messages: Conversation messages in a provider-neutral format:
                      [{"role": "system"/"user"/"assistant"/"tool", "content": ...}, ...]
            tool_declarations: Dict with keys "gemini", "openai", "anthropic"
                               containing provider-specific tool schemas.
            provider: Force a specific provider. If None, use priority order.

        Returns:
            LLMResponse with either content (final answer) or tool_calls.
        """
        providers_to_try = self._get_provider_order(provider)

        last_error = None
        for p in providers_to_try:
            try:
                if p == "gemini" and self._gemini_available:
                    return self._call_gemini(messages, tool_declarations.get("gemini", []))
                elif p == "anthropic" and self._anthropic_available:
                    return self._call_anthropic(messages, tool_declarations.get("anthropic", []))
                elif p == "openai" and self._openai_available:
                    return self._call_openai(messages, tool_declarations.get("openai", []))
            except Exception as e:
                logger.warning(f"Agent LLM call failed with {p}: {e}")
                last_error = e
                continue

        error_msg = f"All LLM providers failed. Last error: {last_error}"
        logger.error(error_msg)
        return LLMResponse(content=error_msg, provider="error")

    def _get_provider_order(self, forced: Optional[str] = None) -> List[str]:
        """Get provider try order."""
        if forced:
            return [forced]
        order = []
        if self._gemini_available:
            order.append("gemini")
        if self._anthropic_available:
            order.append("anthropic")
        if self._openai_available:
            order.append("openai")
        return order

    # ============================================================
    # Gemini
    # ============================================================

    def _call_gemini(
        self,
        messages: List[Dict[str, Any]],
        tools: List[dict],
    ) -> LLMResponse:
        """Call Gemini with function-calling support."""
        import google.generativeai as genai
        from google.generativeai.types import content_types

        config = self._config
        model_name = config.gemini_model or "gemini-2.5-flash"

        # Extract system instruction
        system_instruction = None
        chat_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_instruction = msg["content"]
            elif msg["role"] == "user":
                chat_messages.append({"role": "user", "parts": [msg["content"]]})
            elif msg["role"] == "assistant":
                parts = []
                if msg.get("content"):
                    parts.append(msg["content"])
                # Handle assistant tool_calls in history
                if msg.get("tool_calls"):
                    for tc in msg["tool_calls"]:
                        parts.append(genai.protos.Part(
                            function_call=genai.protos.FunctionCall(
                                name=tc["name"],
                                args=tc["arguments"]
                            )
                        ))
                chat_messages.append({"role": "model", "parts": parts})
            elif msg["role"] == "tool":
                # Tool result message
                chat_messages.append({
                    "role": "user",
                    "parts": [genai.protos.Part(
                        function_response=genai.protos.FunctionResponse(
                            name=msg["name"],
                            response={"result": msg["content"]}
                        )
                    )]
                })

        # Build tool declarations
        gemini_tools = None
        if tools:
            function_declarations = []
            for t in tools:
                function_declarations.append(
                    genai.protos.FunctionDeclaration(
                        name=t["name"],
                        description=t["description"],
                        parameters=t.get("parameters")
                    )
                )
            gemini_tools = [genai.protos.Tool(function_declarations=function_declarations)]

        # Create model with system instruction
        model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=system_instruction,
            tools=gemini_tools,
        )

        # Build contents
        contents = []
        for cm in chat_messages:
            contents.append(genai.protos.Content(
                role=cm["role"],
                parts=[genai.protos.Part(text=p) if isinstance(p, str) else p for p in cm["parts"]]
            ))

        generation_config = genai.types.GenerationConfig(
            temperature=config.gemini_temperature,
        )

        response = model.generate_content(
            contents=contents,
            generation_config=generation_config,
        )

        # Parse response
        tool_calls = []
        text_content = None

        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'function_call') and part.function_call.name:
                    fc = part.function_call
                    args = dict(fc.args) if fc.args else {}
                    tool_calls.append(ToolCall(
                        id=str(uuid.uuid4())[:8],
                        name=fc.name,
                        arguments=args,
                    ))
                elif hasattr(part, 'text') and part.text:
                    text_content = (text_content or "") + part.text

        # Extract usage
        usage = {}
        if hasattr(response, 'usage_metadata') and response.usage_metadata:
            usage = {
                "prompt_tokens": getattr(response.usage_metadata, 'prompt_token_count', 0),
                "completion_tokens": getattr(response.usage_metadata, 'candidates_token_count', 0),
                "total_tokens": getattr(response.usage_metadata, 'total_token_count', 0),
            }

        return LLMResponse(
            content=text_content,
            tool_calls=tool_calls,
            usage=usage,
            provider="gemini",
            raw=response,
        )

    # ============================================================
    # OpenAI
    # ============================================================

    def _call_openai(
        self,
        messages: List[Dict[str, Any]],
        tools: List[dict],
    ) -> LLMResponse:
        """Call OpenAI-compatible API with function-calling support."""
        config = self._config

        # Convert messages to OpenAI format
        openai_messages = []
        for msg in messages:
            if msg["role"] == "tool":
                openai_messages.append({
                    "role": "tool",
                    "tool_call_id": msg.get("tool_call_id", ""),
                    "content": msg["content"] if isinstance(msg["content"], str) else json.dumps(msg["content"]),
                })
            elif msg["role"] == "assistant" and msg.get("tool_calls"):
                # Reconstruct assistant message with tool_calls
                openai_tc = []
                for tc in msg["tool_calls"]:
                    openai_tc.append({
                        "id": tc.get("id", str(uuid.uuid4())[:8]),
                        "type": "function",
                        "function": {
                            "name": tc["name"],
                            "arguments": json.dumps(tc["arguments"]),
                        }
                    })
                openai_messages.append({
                    "role": "assistant",
                    "content": msg.get("content"),
                    "tool_calls": openai_tc,
                })
            else:
                openai_messages.append({
                    "role": msg["role"],
                    "content": msg["content"],
                })

        call_kwargs = {
            "model": config.openai_model or "gpt-4o-mini",
            "messages": openai_messages,
            "temperature": config.openai_temperature,
        }
        if tools:
            call_kwargs["tools"] = tools

        response = self._openai_client.chat.completions.create(**call_kwargs)

        # Parse response
        choice = response.choices[0]
        tool_calls = []
        text_content = choice.message.content

        if choice.message.tool_calls:
            for tc in choice.message.tool_calls:
                args = {}
                if tc.function.arguments:
                    try:
                        args = json.loads(tc.function.arguments)
                    except json.JSONDecodeError:
                        args = {"raw": tc.function.arguments}
                tool_calls.append(ToolCall(
                    id=tc.id,
                    name=tc.function.name,
                    arguments=args,
                ))

        usage = {}
        if response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }

        return LLMResponse(
            content=text_content,
            tool_calls=tool_calls,
            usage=usage,
            provider="openai",
            raw=response,
        )

    # ============================================================
    # Anthropic
    # ============================================================

    def _call_anthropic(
        self,
        messages: List[Dict[str, Any]],
        tools: List[dict],
    ) -> LLMResponse:
        """Call Anthropic Claude with tool-use support."""
        config = self._config

        # Extract system
        system_text = ""
        anthropic_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_text = msg["content"]
            elif msg["role"] == "user":
                anthropic_messages.append({"role": "user", "content": msg["content"]})
            elif msg["role"] == "assistant":
                content_blocks = []
                if msg.get("content"):
                    content_blocks.append({"type": "text", "text": msg["content"]})
                if msg.get("tool_calls"):
                    for tc in msg["tool_calls"]:
                        content_blocks.append({
                            "type": "tool_use",
                            "id": tc.get("id", str(uuid.uuid4())[:8]),
                            "name": tc["name"],
                            "input": tc["arguments"],
                        })
                anthropic_messages.append({"role": "assistant", "content": content_blocks})
            elif msg["role"] == "tool":
                anthropic_messages.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": msg.get("tool_call_id", ""),
                        "content": msg["content"] if isinstance(msg["content"], str) else json.dumps(msg["content"]),
                    }],
                })

        call_kwargs = {
            "model": config.anthropic_model or "claude-sonnet-4-20250514",
            "max_tokens": config.anthropic_max_tokens or 8192,
            "messages": anthropic_messages,
            "temperature": config.anthropic_temperature,
        }
        if system_text:
            call_kwargs["system"] = system_text
        if tools:
            call_kwargs["tools"] = tools

        response = self._anthropic_client.messages.create(**call_kwargs)

        # Parse response
        tool_calls = []
        text_content = None

        for block in response.content:
            if block.type == "text":
                text_content = (text_content or "") + block.text
            elif block.type == "tool_use":
                tool_calls.append(ToolCall(
                    id=block.id,
                    name=block.name,
                    arguments=block.input if isinstance(block.input, dict) else {},
                ))

        usage = {}
        if hasattr(response, 'usage') and response.usage:
            usage = {
                "prompt_tokens": getattr(response.usage, 'input_tokens', 0),
                "completion_tokens": getattr(response.usage, 'output_tokens', 0),
            }

        return LLMResponse(
            content=text_content,
            tool_calls=tool_calls,
            usage=usage,
            provider="anthropic",
            raw=response,
        )
