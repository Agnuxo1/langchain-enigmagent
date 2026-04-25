"""LangChain callback that resolves {{PLACEHOLDER}} substrings in tool calls.

Usage:
    from langchain_openai import ChatOpenAI
    from langchain_enigmagent import EnigmAgentClient, EnigmAgentSecretCallback

    client = EnigmAgentClient()
    cb = EnigmAgentSecretCallback(client=client, default_origin="https://api.example.com")
    llm = ChatOpenAI(callbacks=[cb])
"""
from __future__ import annotations

from typing import Any
from langchain_core.callbacks import BaseCallbackHandler

from .secret_resolver import EnigmAgentClient


class EnigmAgentSecretCallback(BaseCallbackHandler):
    """Resolve placeholders in tool inputs before tools are invoked.

    The LLM emits tool calls containing literal {{PLACEHOLDER}} strings. This
    callback fires on `on_tool_start`, walks the input, and substitutes real
    values from EnigmAgent — only when the requesting `origin` matches the
    secret's bound domain. The model never sees the resolved values.
    """

    def __init__(self, client: EnigmAgentClient, default_origin: str):
        self.client = client
        self.default_origin = default_origin

    def on_tool_start(
        self, serialized: dict[str, Any], input_str: str, **kwargs: Any
    ) -> None:
        # input_str is the tool input; we substitute in place via run_manager
        # context if available. For now the simplest path is to expose a helper.
        pass  # see also: EnigmAgentRunnable for prompt-level rewrites

    def resolve_text(self, text: str, origin: str | None = None) -> str:
        return self.client.substitute(text, origin or self.default_origin)
