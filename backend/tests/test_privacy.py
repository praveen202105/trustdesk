from trustdesk.privacy import redact, sanitized


def test_sensitive_values_are_masked_before_provider_input():
    text = "Email jane@example.com card 4111 1111 1111 1111 otp: 123456 password: secret"
    safe = redact(text)
    assert "jane@example.com" not in safe
    assert "4111" not in safe
    assert "123456" not in safe
    assert "secret" not in safe
    data = sanitized(
        {"customer": {"name": "Private Person", "tier": "gold"}, "order": {"tracking_number": "private"}}
    )
    assert data["customer"] == {"tier": "gold"}
    assert data["order"] == {}


def test_live_provider_receives_masked_context_and_stores_only_token_counts(monkeypatch):
    import json

    import httpx

    from trustdesk import providers

    monkeypatch.setattr(providers.settings, "ai_api_key", "unit-provider-credential")
    captured = []

    def post(url, **kwargs):
        captured.append(json.dumps(kwargs["json"]))
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": '{"text":"safe"}'}}],
                "usage": {"total_tokens": 7, "secret": "private-value"},
            },
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(providers.httpx, "post", post)
    result = providers.CompatibleProvider().generate(
        {
            "task": "draft",
            "customer": {"name": "Private Person"},
            "ticket": {"body": "Contact jane@example.com card 4111 1111 1111 1111"},
        }
    )
    assert all(value not in captured[0] for value in ["Private Person", "jane@example.com", "4111"])
    assert result["usage"] == {"total_tokens": 7}
