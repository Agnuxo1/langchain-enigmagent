"""SecretStr wrapper that resolves on first access.

Usage:
    api_key = enigma_secret("OPENAI_KEY", origin="https://api.openai.com")
    # Pass api_key into ChatOpenAI(api_key=api_key); resolution happens at use time.
"""
from __future__ import annotations

from pydantic import SecretStr

from .secret_resolver import EnigmAgentClient


def enigma_secret(
    placeholder: str,
    origin: str,
    client: EnigmAgentClient | None = None,
) -> SecretStr:
    """Resolve a placeholder via EnigmAgent and wrap in pydantic SecretStr."""
    client = client or EnigmAgentClient()
    value = client.resolve(placeholder, origin)
    return SecretStr(value)
