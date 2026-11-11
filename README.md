# langchain-enigmagent

[![CI](https://github.com/Agnuxo1/langchain-enigmagent/actions/workflows/ci.yml/badge.svg)](https://github.com/Agnuxo1/langchain-enigmagent/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/langchain-enigmagent?label=pypi&color=blue)](https://pypi.org/project/langchain-enigmagent/)
[![PyPI downloads](https://img.shields.io/pypi/dm/langchain-enigmagent.svg)](https://pypi.org/project/langchain-enigmagent/)
[![Python](https://img.shields.io/pypi/pyversions/langchain-enigmagent.svg)](https://pypi.org/project/langchain-enigmagent/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![LangChain](https://img.shields.io/badge/LangChain-0.3+-green.svg)](https://github.com/langchain-ai/langchain)
[![EnigmAgent](https://img.shields.io/badge/EnigmAgent-MCP-purple.svg)](https://github.com/Agnuxo1/EnigmAgent)
[![GitHub stars](https://img.shields.io/github/stars/Agnuxo1/langchain-enigmagent?style=social)](https://github.com/Agnuxo1/langchain-enigmagent)

> **Last week I asked a LangChain agent to push a fix to a private GitHub repo. To do that, the agent needed my personal access token. I had three options, and all three were terrible: paste the token into the prompt (and into the provider's logs forever), give the agent a long-lived token it could reuse on its own at 3 a.m., or give up and do it by hand.**

`langchain-enigmagent` is option four.

Your LangChain chain emits `{{GITHUB_TOKEN}}`. The placeholder leaves the model and travels through the prompt, the chain, the tool inputs, the LangSmith trace — and only at the moment your tool actually needs the credential does EnigmAgent intercept the call, decrypt the real token locally with AES-256-GCM, and inject it. The plaintext exists for one event-loop tick. The model never sees it. The provider never sees it. Your LangSmith run never sees it.

```bash
pip install langchain-enigmagent
```

In another terminal, next to your app:

```bash
npx enigmagent-mcp --mode rest --port 3737
```

That's the entire install. The Python package talks to the local EnigmAgent REST server over loopback; secrets stay in the encrypted vault on disk.

> ⭐ **Star [the main project](https://github.com/Agnuxo1/EnigmAgent) if you've ever pasted a token you regretted.**

---

<!-- impact-note:start -->
<sub><strong>Efficiency and practical value.</strong> Runnable, callback and SecretStr helpers offer several ways to reuse one local vault connection across LangChain workflows. This can reduce repeated integration work and hard-coded credential configuration. The advantage depends on resolving values only within trusted tool code; the <a href="https://github.com/Agnuxo1/EnigmAgent/blob/main/docs/THREAT_MODEL.md">threat model</a> defines the limits of the approach.</sub>
<!-- impact-note:end -->

## The problem (in LangChain terms)

When you build a LangChain agent that needs to authenticate against a real API — GitHub, OpenAI, Stripe, your own backend — you face the same impossible choice every framework faces:

| Option | What happens |
|---|---|
| Put the secret into the prompt | It lands in LangSmith, in the model's context, possibly in provider logs |
| Bake the token into the tool at construction time | The model can call the tool with arbitrary inputs and exfiltrate the secret indirectly |
| Use a separate HSM / vault per tool | Works but every tool has to be rewritten |

**`langchain-enigmagent` is option D.** Your prompt, your chain, your trace all carry only `{{PLACEHOLDER}}` strings. The real value is resolved at the boundary, by a process the model cannot see, against a vault on the user's machine.

---

## How it works

```
┌──────────────────┐  emits {{GITHUB_TOKEN}}  ┌─────────────────────┐
│ LangChain agent  │ ───────────────────────▶ │  Tool input / call  │
│  (any LLM)       │                          │  (github.com / …)   │
└──────────────────┘                          └──────────┬──────────┘
                                                         │ before invoke (intercepted)
                                                         ▼
                                          ┌─────────────────────────┐
                                          │      EnigmAgent         │
                                          │  detects placeholder,   │
                                          │  checks origin match,   │
                                          │  decrypts → ghp_xxx     │
                                          └──────────┬──────────────┘
                                                     │ real value
                                                     ▼
                                          ┌─────────────────────────┐
                                          │  HTTP request to the    │
                                          │  upstream API           │
                                          └─────────────────────────┘
```

The model emits a placeholder. The placeholder lives in the prompt, the chain, and the trace. A `Runnable` (or `Callback`) in your chain sees the placeholder right before the request leaves your process and asks the local EnigmAgent REST server to swap it for the real value — but only if the request's `origin` matches the domain that secret was bound to. Wrong domain → the resolver refuses.

---

## Three usage patterns

### 1. `EnigmAgentSubstitute` — Runnable prefix (recommended)

Wrap any chain so every string passing through gets `{{PLACEHOLDER}}` resolved before the LLM call:

```python
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_enigmagent import EnigmAgentClient, EnigmAgentSubstitute

# Resolve any {{...}} in the input dict against the GitHub origin
sub = EnigmAgentSubstitute(
    client=EnigmAgentClient(),
    origin="https://api.github.com",
)

prompt = ChatPromptTemplate.from_template(
    "Make an HTTP request with header 'Authorization: Bearer {token}' to {url}"
)

chain = sub | prompt | ChatOpenAI()

# The agent sees {{GITHUB_TOKEN}} go in. The real ghp_... is resolved
# right before ChatOpenAI is invoked. The model NEVER sees the value.
chain.invoke({"token": "{{GITHUB_TOKEN}}", "url": "https://api.github.com/user"})
```

### 2. `EnigmAgentSecretCallback` — at-call-site resolution

Attach as a callback to any LLM or chain. The callback exposes `resolve_text()` for tools that emit text-with-placeholders:

```python
from langchain_openai import ChatOpenAI
from langchain_enigmagent import EnigmAgentClient, EnigmAgentSecretCallback

cb = EnigmAgentSecretCallback(
    client=EnigmAgentClient(),
    default_origin="https://api.openai.com",
)

llm = ChatOpenAI(callbacks=[cb])

# Inside a custom tool:
def http_post(body: str) -> str:
    body = cb.resolve_text(body, origin="https://api.openai.com")
    # ... actually send the request ...
```

### 3. `enigma_secret` — drop-in `SecretStr` replacement

For LangChain components that take a `SecretStr` API key directly (e.g. `ChatOpenAI(api_key=...)`), resolve once at construction time:

```python
from langchain_openai import ChatOpenAI
from langchain_enigmagent import enigma_secret

# Resolves OPENAI_KEY from the local vault and wraps in pydantic SecretStr
api_key = enigma_secret("OPENAI_KEY", origin="https://api.openai.com")

llm = ChatOpenAI(api_key=api_key)
```

The plaintext lives only inside the `SecretStr` and only inside the `ChatOpenAI` instance — never in your source, never in your env, never in the prompt.

---

## Configuration

`EnigmAgentClient` defaults to `http://localhost:3737`. Override:

```python
client = EnigmAgentClient(
    base_url="http://127.0.0.1:9999",      # custom port
    timeout=5.0,                            # in seconds
    shared_secret="my-loopback-token",      # sent as X-EnigmAgent-Auth header
)
```

To run the EnigmAgent REST server with a shared secret:

```bash
npx enigmagent-mcp --mode rest --port 3737 --auth my-loopback-token
```

---

## The vault

This package is a thin client. The real work — Argon2id key derivation, AES-256-GCM encryption, origin binding, audit logging — lives in **[EnigmAgent](https://github.com/Agnuxo1/EnigmAgent)**, the npm package that backs it. To create or edit your vault, see the main README. A typical workflow:

```bash
# Create a vault interactively (one-time)
npx enigmagent-mcp --new-vault ./my.vault.json

# Add a secret bound to a domain
npx enigmagent-mcp --vault ./my.vault.json --add GITHUB_TOKEN ghp_xxx --origin https://api.github.com

# Run as REST server next to your LangChain app
npx enigmagent-mcp --mode rest --port 3737 --vault ./my.vault.json
```

---

## Security model

- **Loopback only.** The REST server binds to `127.0.0.1`. Only processes on the same machine can reach it.
- **Origin binding.** Every secret is bound to one or more origins (e.g. `https://api.github.com`). Resolving a secret for a different origin is refused.
- **Argon2id + AES-256-GCM.** The vault file is encrypted at rest with a passphrase-derived key.
- **No plaintext in logs.** Resolved values exist only in the memory of the process making the upstream HTTP call, for the duration of that call.
- **Optional shared secret.** Pass `--auth` to require an `X-EnigmAgent-Auth` header on every REST call, so unauthorised local processes can't query the vault.

Full threat model: [EnigmAgent THREAT_MODEL.md](https://github.com/Agnuxo1/EnigmAgent/blob/main/docs/THREAT_MODEL.md)

---

## Compatibility

- Python: 3.9, 3.10, 3.11, 3.12
- `langchain-core >= 0.3.0` (works with current LangChain 0.3+ and 0.4+)
- `pydantic >= 2`
- Any LLM provider (OpenAI, Anthropic, Mistral, local), any tool

---

## Roadmap

- [ ] Auto-detect tool-call arguments and rewrite them in `on_tool_start` (currently the callback exposes `resolve_text()` and you call it manually inside the tool body — fully automatic interception requires LangChain's tool input mutation API to land)
- [ ] LangGraph node helper (drop-in node that resolves placeholders flowing through state)
- [ ] LangSmith integration (mark resolved spans so traces remain redacted)
- [ ] Upstream proposal to `langchain-community` once this package has real users

PRs welcome.

---

## License

MIT © 2026 Francisco Angulo de Lafuente

## Links

- Main project: [github.com/Agnuxo1/EnigmAgent](https://github.com/Agnuxo1/EnigmAgent)
- npm package: [enigmagent-mcp](https://www.npmjs.com/package/enigmagent-mcp)
- Issues: [github.com/Agnuxo1/langchain-enigmagent/issues](https://github.com/Agnuxo1/langchain-enigmagent/issues)
