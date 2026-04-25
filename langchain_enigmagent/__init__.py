"""langchain-enigmagent — LangChain integration for the EnigmAgent vault."""
from .secret_resolver import EnigmAgentClient, EnigmAgentResolveError, PLACEHOLDER_RE
from .callback import EnigmAgentSecretCallback
from .runnable import EnigmAgentSubstitute
from .secret_str import enigma_secret

__all__ = [
    "EnigmAgentClient",
    "EnigmAgentResolveError",
    "EnigmAgentSecretCallback",
    "EnigmAgentSubstitute",
    "enigma_secret",
    "PLACEHOLDER_RE",
]
__version__ = "0.1.0"
