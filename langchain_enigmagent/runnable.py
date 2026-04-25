"""A Runnable that substitutes {{PLACEHOLDER}} tokens before the chain executes.

Usage:
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_openai import ChatOpenAI
    from langchain_enigmagent import EnigmAgentClient, EnigmAgentSubstitute

    sub = EnigmAgentSubstitute(client=EnigmAgentClient(), origin="https://api.example.com")
    chain = sub | ChatPromptTemplate.from_template("...") | ChatOpenAI()
"""
from __future__ import annotations

from typing import Any
from langchain_core.runnables import RunnableLambda

from .secret_resolver import EnigmAgentClient


def EnigmAgentSubstitute(
    client: EnigmAgentClient | None = None,
    origin: str = "http://localhost",
) -> RunnableLambda:
    client = client or EnigmAgentClient()

    def _walk(value: Any) -> Any:
        if isinstance(value, str):
            return client.substitute(value, origin)
        if isinstance(value, dict):
            return {k: _walk(v) for k, v in value.items()}
        if isinstance(value, list):
            return [_walk(v) for v in value]
        return value

    return RunnableLambda(_walk).with_config(run_name="EnigmAgentSubstitute")
