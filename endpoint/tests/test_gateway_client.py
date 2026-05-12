from wake_word_endpoint.gateway_client import GatewayHeaders


def test_gateway_headers_include_endpoint_id_and_bearer_token():
    headers = GatewayHeaders(endpoint_id="mac-studio-01", token="dev-token").to_headers()

    assert headers["Authorization"] == "Bearer dev-token"
    assert headers["X-Endpoint-Id"] == "mac-studio-01"
