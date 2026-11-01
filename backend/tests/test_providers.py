import json

import httpx
import pytest

from trustdesk import providers
from trustdesk.jobs import TransientError


def test_live_schema_repair_is_bounded_and_no_expected_labels(monkeypatch):
    monkeypatch.setattr(providers.settings, "ai_api_key", "test-provider-key")
    calls = []

    def post(url, **kwargs):
        calls.append(kwargs["json"])
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": json.dumps({"text": "x", "triage": {"category": "invented"}})}}
                ]
            },
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(providers.httpx, "post", post)
    with pytest.raises(ValueError):
        providers.CompatibleProvider().generate({"task": "triage", "ticket": {"body": "Unsupported request"}})
    assert len(calls) == 2
    assert "expected_" not in json.dumps(calls)


def test_provider_transient_failure_is_classified(monkeypatch):
    monkeypatch.setattr(providers.settings, "ai_api_key", "test-provider-key")
    monkeypatch.setattr(
        providers.httpx, "post", lambda url, **kw: httpx.Response(429, request=httpx.Request("POST", url))
    )
    with pytest.raises(TransientError):
        providers.CompatibleProvider().generate({"task": "draft"})
