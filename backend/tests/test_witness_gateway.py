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

@pytest.mark.parametrize('path,method', [
    ('api/lab-schema','GET'), ('api/enhance-schema','GET'),
    ('api/cases/'+'a'*32,'PUT'),
    *[('api/cases/'+'a'*32+'/'+operation,'POST') for operation in ['selection','refinement-preview','refine','local-edits','imports','enhancements','multiview-preview','multiview','reports']],
    ('api/cases/'+'a'*32+'/versions/'+'b'*32+'/pixels','GET'),
    ('api/cases/'+'a'*32+'/reports/'+'b'*32+'/pdf','GET'),
    ('api/cases/'+'a'*32+'/views/'+'b'*32+'/layouts/'+'c'*32+'/three_quarter.png','GET'),
])
def test_complete_gateway_routes(client, anon_client, monkeypatch, path, method):
    from app.api import witness_gateway as gateway
    original = httpx.AsyncClient
    monkeypatch.setenv('WITNESSTRACE_GATEWAY_TARGET','http://127.0.0.1:8022')
    def handle(request):
        assert 'cookie' not in request.headers
        assert request.method == method
        return httpx.Response(200,json={'forwarded':True})
    monkeypatch.setattr(gateway.httpx,'AsyncClient',lambda **kw: original(transport=httpx.MockTransport(handle),**kw))
    cookies = dict(client.cookies)
    client.cookies.clear()
    assert anon_client.request(method,'/wt-api/'+path,json={} if method!='GET' else None).status_code==401
    client.cookies.update(cookies)
    result=client.request(method,'/wt-api/'+path,json={} if method!='GET' else None)
    assert result.status_code==200 and result.json()['forwarded']


def test_tool_assets_are_authenticated_and_scoped(client, anon_client, monkeypatch):
    monkeypatch.setenv('WITNESSTRACE_GATEWAY_TARGET','http://127.0.0.1:8022')
    cookies = dict(client.cookies)
    client.cookies.clear()
    assert anon_client.get('/wt-api/tools/index.html').status_code==401
    client.cookies.update(cookies)
    document=client.get('/wt-api/tools/index.html')
    assert document.status_code==200 and '/wt-api/tools/react-bridge.js' in document.text
    assert "frame-ancestors 'self'" in document.headers['content-security-policy']
    assert client.get('/wt-api/tools/sketchpad.js').status_code==200
    assert client.get('/wt-api/tools/../app.py').status_code==404
    assert client.get('/wt-api/tools/icons/../../app.py').status_code==404
    assert client.get('/wt-api/tools/auth.json').status_code==404
    assert client.put('/wt-api/api/cases/'+'a'*32,json={},headers={'origin':'https://evil.test'}).status_code==403
