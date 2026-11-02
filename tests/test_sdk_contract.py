"""Isolated native-SDK wire contract; no request reaches the Gemini service."""

import json
from pathlib import Path

import httpx
from google import genai
from google.genai import types

from emporio_music.agent import ChatSession
from emporio_music.config import ModelSettings, Settings
from emporio_music.data import import_data


def test_native_gemini_sdk_serializes_tool_round_trip_without_network(tmp_path):
    fixtures = Path(__file__).parent / "fixtures"
    settings = Settings(fixtures / "raw", tmp_path / "catalog.sqlite3", fixtures / "policies.pdf")
    import_data(settings.raw_dir, settings.database_path)
    requests = []

    def respond(request):
        assert request.url.host == "offline.invalid"
        assert request.url.path.endswith("/interactions")
        requests.append(json.loads(request.content))
        if len(requests) == 1:
            body = {
                "status": "completed", "id": "isolated_1",
                "steps": [{"type": "function_call", "id": "call_1", "name": "get_product", "arguments": {"product_id": 1}}],
            }
        else:
            text = "The synthetic product's base price is BRL 599.90."
            body = {
                "status": "completed", "id": "isolated_2", "output_text": text,
                "steps": [{"type": "model_output", "content": [{"type": "text", "text": text}]}],
            }
        return httpx.Response(200, json=body)

    http_client = httpx.Client(transport=httpx.MockTransport(respond))
    client = genai.Client(
        api_key="isolated-placeholder-not-a-credential",
        http_options=types.HttpOptions(base_url="http://offline.invalid", httpx_client=http_client),
    )
    session = ChatSession(settings, client=client, model_settings=ModelSettings(), language="en")
    try:
        reply = session.send("What is the base price of synthetic product one?")
        assert len(requests) == 2
        assert requests[0]["generation_config"]["tool_choice"] == "any"
        assert requests[1]["generation_config"]["tool_choice"] == "auto"
        assert all(request["store"] is False for request in requests)
        result_step = requests[1]["input"][-1]
        assert result_step["type"] == "function_result"
        assert result_step["call_id"] == "call_1"
        actual_result = json.loads(result_step["result"][0]["text"])["data"]
        assert actual_result["product"]["price_brl"] == "599.90"
        assert reply.tool_calls[0]["result"] == actual_result
        assert reply.text == "The synthetic product's base price is BRL 599.90."
    finally:
        session.close()
