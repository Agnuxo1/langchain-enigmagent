import pytest
from unittest.mock import patch, MagicMock
from langchain_enigmagent import EnigmAgentClient, PLACEHOLDER_RE


def test_placeholder_regex():
    assert PLACEHOLDER_RE.findall("Bearer {{TOKEN}} for {{user.id}}") == ["TOKEN", "user.id"]


def test_substitute():
    client = EnigmAgentClient()
    with patch.object(EnigmAgentClient, "resolve", lambda self, p, o: f"<{p}>"):
        out = client.substitute("Authorization: Bearer {{GH_TOKEN}}", origin="https://api.github.com")
    assert out == "Authorization: Bearer <GH_TOKEN>"


def test_list_placeholders():
    client = EnigmAgentClient()
    assert client.list_placeholders("a {{X}} b {{Y}}") == ["X", "Y"]
