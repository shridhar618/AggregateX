import httpx
import pytest


def test_gateway_requires_session(anon_client):
    assert anon_client.get('/wt-api/api/health').status_code == 401
    assert anon_client.post('/wt-api/api/generate', json={}).status_code == 401
    assert anon_client.get('/wt-api/images/' + 'a'*32).status_code == 401


@pytest.mark.parametrize('target', ['', 'http://example.com:8022', 'http://127.0.0.1:8001', 'http://127.0.0.1:8000'])
def test_gateway_rejects_unsafe_targets(client, monkeypatch, target):
    monkeypatch.setenv('WITNESSTRACE_GATEWAY_TARGET', target)
    assert client.get('/wt-api/api/health').status_code == 503


def test_gateway_scope_origin_and_content_type(client, monkeypatch):
    monkeypatch.setenv('WITNESSTRACE_GATEWAY_TARGET', 'http://127.0.0.1:8022')
    assert client.get('/wt-api/static/index.html').status_code == 404
    assert client.post('/wt-api/api/cases', json={}, headers={'origin': 'https://evil.test'}).status_code == 403
    assert client.post('/wt-api/api/cases', content='plain').status_code == 415


def test_gateway_forwards_without_credentials(client, monkeypatch):
    from app.api import witness_gateway as gateway
    original = httpx.AsyncClient
    def handle(request):
        assert request.url == 'http://127.0.0.1:8022/api/health'
        assert 'cookie' not in request.headers and 'authorization' not in request.headers
        return httpx.Response(200, json={'codex_installed': True})
    monkeypatch.setenv('WITNESSTRACE_GATEWAY_TARGET', 'http://127.0.0.1:8022')
    monkeypatch.setattr(gateway.httpx, 'AsyncClient', lambda **kw: original(transport=httpx.MockTransport(handle), **kw))
    result = client.get('/wt-api/api/health')
    assert result.json() == {'codex_installed': True}
    assert result.headers['cache-control'] == 'no-store'


def test_gateway_connection_failure(client, monkeypatch):
    from app.api import witness_gateway as gateway
    original = httpx.AsyncClient
    def handle(request):
        raise httpx.ConnectError('refused')
    monkeypatch.setenv('WITNESSTRACE_GATEWAY_TARGET', 'http://127.0.0.1:8022')
    monkeypatch.setattr(gateway.httpx, 'AsyncClient', lambda **kw: original(transport=httpx.MockTransport(handle), **kw))
    assert client.get('/wt-api/api/health').status_code == 503
