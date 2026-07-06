import httpx

from document_extractor.infrastructure.llm.openai_compatible_client import (
    OpenAiCompatibleJsonClient,
)


def test_requests_structured_json_from_compatible_api(monkeypatch) -> None:
    invocation = {}

    def post(url, headers, json, timeout):
        invocation.update(
            url=url,
            headers=headers,
            payload=json,
            timeout=timeout,
        )
        return httpx.Response(
            200,
            request=httpx.Request("POST", url),
            json={"choices": [{"message": {"content": '{"fields": []}'}}]},
        )

    monkeypatch.setattr("httpx.post", post)
    client = OpenAiCompatibleJsonClient(
        base_url="https://provider.example/v1/",
        api_key="secret",
        model="example-model",
    )

    result = client.generate_json(
        schema_name="test_response",
        instructions="Return JSON",
        input_text="Invoice text",
        json_schema={"type": "object"},
    )

    assert result == {"fields": []}
    assert invocation["url"] == (
        "https://provider.example/v1/chat/completions"
    )
    assert invocation["payload"]["response_format"]["type"] == ("json_schema")
    assert (
        invocation["payload"]["response_format"]["json_schema"]["name"]
        == "test_response"
    )


def test_returns_none_when_provider_fails(monkeypatch) -> None:
    def post(url, headers, json, timeout):
        raise httpx.ConnectError("offline")

    monkeypatch.setattr("httpx.post", post)
    client = OpenAiCompatibleJsonClient(
        base_url="https://provider.example/v1",
        api_key="secret",
        model="example-model",
    )

    assert client.generate_json("test", "instructions", "input", {}) is None
