import httpx

from scripts.railway_live_smoke import build_endpoints, create_parser, run_smoke


def test_parser_defaults_pack() -> None:
    parser = create_parser()
    args = parser.parse_args(["--base-url", "http://example.com"])
    assert args.pack == "general"


def test_run_smoke_constructs_endpoints(monkeypatch) -> None:
    requested: list[tuple[str, str]] = []

    def fake_request(self, method: str, url: str, **kwargs) -> httpx.Response:  # type: ignore[override]
        requested.append((method, url))
        request = httpx.Request(method, url)
        if url.endswith("/v1/health"):
            return httpx.Response(200, json={"status": "ok"}, request=request)
        if url.endswith("/v1/packs"):
            return httpx.Response(200, json={"packs": ["general"]}, request=request)
        if url.endswith("/v1/verify"):
            return httpx.Response(200, json={"status": "verified"}, request=request)
        return httpx.Response(404, json={}, request=request)

    monkeypatch.setattr(httpx.Client, "request", fake_request)

    exit_code = run_smoke("http://example.com/", "general", llm_mode="fixture")
    assert exit_code == 0

    endpoints = build_endpoints("http://example.com/")
    urls = {url for _, url in requested}
    assert endpoints["health"] in urls
    assert endpoints["packs"] in urls
    assert endpoints["verify"] in urls
