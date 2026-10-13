import httpx
import pytest

from app.services import stock_service
from app.services.stock_service import StockService


def test_key_is_sent_as_a_header_and_never_appears_in_errors(monkeypatch):
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(403, json={"error": "no access"})

    real_client = httpx.Client
    monkeypatch.setattr(stock_service.httpx, "Client", lambda: real_client(transport=httpx.MockTransport(handler)))

    with pytest.raises(httpx.HTTPStatusError) as err:
        StockService("secret-key")._request("https://finnhub.io/api/v1/stock/candle", {"symbol": "X", "token": "secret-key"})

    assert seen[0].headers["X-Finnhub-Token"] == "secret-key"
    assert "secret-key" not in str(seen[0].url)
    assert "secret-key" not in str(err.value)
