import hashlib
import pytest
from fastapi.testclient import TestClient
import app
import case_store as store
import integrity_store as integrity
from test_cases import new, freeze
from test_enhance import upload

TX = '0x' + 'a' * 64
BLOCK = '0x' + 'b' * 64
ADDRESS = '0x' + '1' * 40

@pytest.fixture
def saved():
    integrity.initialize()
    c = TestClient(app.app)
    case = freeze(c, new(c))
    result, _ = upload(c, case)
    vid = result['version_id']
    return c, case['id'], vid, f"/api/cases/{case['id']}/versions/{vid}/integrity"


def chain(monkeypatch, value, **overrides):
    tx = dict(chainId='0x14a34', hash=TX, input=value['data'], value='0x0', to=integrity.SINK,
              **{'from': ADDRESS}, blockHash=BLOCK, blockNumber='0x123')
    tx.update(overrides.pop('tx', {}))
    receipt = dict(to=integrity.SINK, **{'from': ADDRESS}, transactionHash=TX, status='0x1', blockHash=BLOCK, blockNumber='0x123')
    receipt.update(overrides.pop('receipt', {}))
    values = {'eth_chainId': '0x14a34', 'eth_getTransactionByHash': tx,
              'eth_getTransactionReceipt': receipt, 'eth_getBlockByNumber': {'hash': BLOCK}}
    values.update(overrides)
    monkeypatch.setattr(integrity, 'rpc', lambda method, params: values[method])


def test_registration_confirmation_reopen_and_tampering(saved, monkeypatch):
    c, cid, vid, path = saved
    value = c.get(path).json()
    assert value['status'] == 'NOT REGISTERED'
    assert value['sha256'] == hashlib.sha256(c.get('/images/' + vid).content).hexdigest()
    assert cid not in bytes.fromhex(value['data'][2:]).decode()
    chain(monkeypatch, value, eth_getTransactionReceipt=None)
    assert c.post(path, json={'tx_hash': TX, 'sender': ADDRESS}).json()['status'] == 'PENDING'
    integrity.initialize()
    assert c.get(path).json()['tx_hash'] == TX
    chain(monkeypatch, value)
    assert c.get(path).json()['status'] == 'VERIFIED'
    with store.connection() as con:
        assert con.execute('SELECT confirmed_at FROM blockchain_integrity').fetchone()[0]
        image = store.DATA / con.execute('SELECT path FROM versions WHERE id=?', (vid,)).fetchone()[0]
    image.write_bytes(image.read_bytes() + b'tamper')
    assert c.get(path).json()['status'] == 'TAMPERED'
    assert c.post(path, json={'tx_hash': TX, 'sender': ADDRESS}).status_code == 409


@pytest.mark.parametrize('override,expected', [
    ({'tx': {'input': '0x00'}}, 'TAMPERED'),
    ({'tx': {'value': '0x1'}}, 'TAMPERED'),
    ({'tx': {'to': ADDRESS}}, 'TAMPERED'),
    ({'tx': {'from': '0x'+'2'*40}}, 'TAMPERED'),
    ({'tx': {'chainId': '0x1'}}, 'ERROR'),
    ({'receipt': {'from': '0x'+'2'*40}}, 'ERROR'),
    ({'receipt': {'to': ADDRESS}}, 'ERROR'),
    ({'receipt': {'status': '0x0'}}, 'ERROR'),
    ({'eth_chainId': '0x1'}, 'ERROR'),
    ({'eth_getTransactionByHash': None}, 'PENDING'),
    ({'eth_getBlockByNumber': {'hash': '0xdead'}}, 'PENDING'),
    ({'receipt': {'transactionHash': '0xdead'}}, 'ERROR'),
])
def test_chain_validation(saved, monkeypatch, override, expected):
    c, _, _, path = saved
    value = c.get(path).json()
    chain(monkeypatch, value, **override)
    assert c.post(path, json={'tx_hash': TX, 'sender': ADDRESS}).json()['status'] == expected


def test_scope_validation_rpc_error_and_no_overwrite(saved, monkeypatch):
    c, _, vid, path = saved
    other = new(c)
    assert c.get(f"/api/cases/{other['id']}/versions/{vid}/integrity").status_code == 404
    assert c.post(path, json={'tx_hash': 'bad'}).status_code == 422
    def unavailable(*args): raise OSError('offline')
    monkeypatch.setattr(integrity, 'rpc', unavailable)
    assert c.post(path, json={'tx_hash': TX, 'sender': ADDRESS}).json()['status'] == 'ERROR'
    assert c.post(path, json={'tx_hash': '0x'+'c'*64, 'sender': ADDRESS}).status_code == 409


def test_confirmed_legacy_migration_and_sender_pinning(saved, monkeypatch):
    c, _, vid, path = saved
    value = c.get(path).json()
    with store.connection() as con:
        con.execute('DROP TABLE blockchain_integrity')
        con.execute('CREATE TABLE blockchain_integrity(version_id TEXT PRIMARY KEY REFERENCES versions(id), tx_hash TEXT UNIQUE NOT NULL, confirmed_at TEXT)')
        con.execute('INSERT INTO blockchain_integrity VALUES (?,?,?)', (vid, TX, store.now()))
    integrity.initialize()
    integrity.initialize()  # Reopening cannot expand eligibility.
    chain(monkeypatch, value, tx={'to': ADDRESS}, receipt={'to': ADDRESS})
    assert c.get(path).json()['status'] == 'VERIFIED'
    with store.connection() as con:
        row = con.execute('SELECT * FROM blockchain_integrity').fetchone()
        assert row['legacy_confirmed'] == 1 and row['expected_sender'] == ADDRESS
    chain(monkeypatch, value, tx={'to': '0x'+'2'*40, 'from': '0x'+'2'*40})
    assert c.get(path).json()['status'] == 'TAMPERED'


def test_unconfirmed_legacy_cannot_be_grandfathered(saved, monkeypatch):
    c, _, vid, path = saved
    value = c.get(path).json()
    with store.connection() as con:
        con.execute('DROP TABLE blockchain_integrity')
        con.execute('CREATE TABLE blockchain_integrity(version_id TEXT PRIMARY KEY REFERENCES versions(id), tx_hash TEXT UNIQUE NOT NULL, confirmed_at TEXT)')
        con.execute('INSERT INTO blockchain_integrity VALUES (?,?,NULL)', (vid, TX))
    integrity.initialize()
    chain(monkeypatch, value, tx={'to': ADDRESS}, receipt={'to': ADDRESS})
    assert c.get(path).json()['status'] == 'TAMPERED'


def test_sender_is_required_immutable_and_never_sink(saved, monkeypatch):
    c, _, _, path = saved
    value = c.get(path).json()
    assert c.post(path, json={'tx_hash': TX}).status_code == 422
    assert c.post(path, json={'tx_hash': TX, 'sender': integrity.SINK}).status_code == 422
    chain(monkeypatch, value)
    assert c.post(path, json={'tx_hash': TX, 'sender': ADDRESS}).json()['status'] == 'VERIFIED'
    assert c.post(path, json={'tx_hash': TX, 'sender': '0x'+'2'*40}).status_code == 409


def test_cross_revision_commitment_is_rejected(saved, monkeypatch):
    c, _, _, path = saved
    value = c.get(path).json()
    other = freeze(c, new(c)); imported, _ = upload(c, other)
    other_path = f"/api/cases/{other['id']}/versions/{imported['version_id']}/integrity"
    other_value = c.get(other_path).json()
    assert value['sha256'] == other_value['sha256'] and value['data'] != other_value['data']
    chain(monkeypatch, value)
    assert c.post(other_path, json={'tx_hash': TX, 'sender': ADDRESS}).json()['status'] == 'TAMPERED'


@pytest.fixture
def live_wrapped():
    """Public RPC capture of the reported successful type-4 wallet transaction."""
    import json
    from pathlib import Path
    return json.loads((Path(__file__).parent / 'fixtures/base_sepolia_wrapped.json').read_text())


def wrapped_chain(monkeypatch, value, live):
    # Swap only the commitment for the synthetic test revision. The original ABI envelope,
    # trace identities and executed path come from the actual reported transaction.
    import copy
    live = copy.deepcopy(live)
    expected = next(t['action']['input'] for t in live['traces'] if t['action'].get('to') == integrity.SINK)
    for obj in [live['tx'], *(t['action'] for t in live['traces'])]:
        for key in ['input']:
            if key in obj:
                obj[key] = obj[key].replace(expected[2:], value['data'][2:])
    values = {'eth_chainId': '0x14a34', 'eth_getTransactionByHash': live['tx'],
              'eth_getTransactionReceipt': live['receipt'], 'eth_getBlockByNumber': live['block'],
              'trace_transaction': live['traces']}
    monkeypatch.setattr(integrity, 'rpc', lambda method, params: values[method])
    return live


def test_reported_live_wrapper_verifies_executed_commitment(saved, monkeypatch, live_wrapped):
    c, _, _, path = saved
    value = c.get(path).json()
    live = wrapped_chain(monkeypatch, value, live_wrapped)
    response = c.post(path, json={'tx_hash': live['tx']['hash'], 'sender': live['tx']['from']}).json()
    assert response['status'] == 'VERIFIED' and response['verification_mode'] == 'wallet_delegation_trace'
    assert response['execution_sender'] != response['expected_sender']
    assert response['code'] == 'VERIFIED' and response['retryable'] is False


@pytest.mark.parametrize('fault', ['failed_sink', 'failed_parent', 'wrong_commitment', 'missing_parent',
                                   'wrong_trace_block', 'wrong_trace_hash', 'static_sink', 'nonzero_sink', 'wrong_root'])
def test_wallet_wrapper_never_accepts_calldata_substring_alone(saved, monkeypatch, live_wrapped, fault):
    c, _, _, path = saved
    value = c.get(path).json()
    live = wrapped_chain(monkeypatch, value, live_wrapped)
    sink = next(t for t in live['traces'] if t['action'].get('to') == integrity.SINK)
    parent = next(t for t in live['traces'] if t['traceAddress'] == sink['traceAddress'][:-1])
    if fault == 'failed_sink': sink['error'] = 'Reverted'
    if fault == 'failed_parent': parent['error'] = 'Reverted'
    if fault == 'wrong_commitment': sink['action']['input'] = '0x1234'
    if fault == 'missing_parent': live['traces'].remove(parent)
    if fault == 'wrong_trace_block': sink['blockHash'] = '0x'+'0'*64
    if fault == 'wrong_trace_hash': sink['transactionHash'] = TX
    if fault == 'static_sink': sink['action']['callType'] = 'staticcall'
    if fault == 'nonzero_sink': sink['action']['value'] = '0x1'
    if fault == 'wrong_root': live['traces'][0]['action']['to'] = integrity.SINK
    response = c.post(path, json={'tx_hash': live['tx']['hash'], 'sender': live['tx']['from']}).json()
    assert response['status'] in ('TAMPERED', 'ERROR')
    assert response['code'] in ('EXECUTED_COMMITMENT_MISMATCH', 'RPC_INVALID_RESPONSE')


@pytest.mark.parametrize('code', ['RPC_RATE_LIMITED', 'RPC_UNAVAILABLE', 'RPC_ACCESS_DENIED', 'RPC_TIMEOUT', 'RPC_METHOD_UNSUPPORTED'])
def test_rpc_failures_are_retryable_not_hash_mismatches(saved, monkeypatch, code):
    c, _, _, path = saved
    def unavailable(*args): raise integrity.RPCFailure(code)
    monkeypatch.setattr(integrity, 'rpc', unavailable)
    result = c.post(path, json={'tx_hash': TX, 'sender': ADDRESS}).json()
    assert result['status'] == 'ERROR' and result['code'] == code and result['retryable']
    assert c.get(path).json()['tx_hash'] == TX


@pytest.mark.parametrize('field', ['from', 'to', 'status', 'transactionHash'])
def test_incomplete_receipt_is_safe_retryable_error(saved, monkeypatch, field):
    c, _, _, path = saved
    value = c.get(path).json()
    chain(monkeypatch, value, receipt={field: None})
    result = c.post(path, json={'tx_hash': TX, 'sender': ADDRESS}).json()
    assert result['status'] == 'ERROR' and result['code'] in ('RPC_INVALID_RESPONSE', 'RECEIPT_IDENTITY_MISMATCH')


def test_pending_receipt_recovery_and_reverted_diagnostic(saved, monkeypatch):
    c, _, _, path = saved
    value = c.get(path).json()
    chain(monkeypatch, value, eth_getTransactionReceipt=None)
    assert c.post(path, json={'tx_hash': TX, 'sender': ADDRESS}).json()['code'] == 'RECEIPT_PENDING'
    chain(monkeypatch, value, receipt={'status': '0x0'})
    result = c.get(path).json()
    assert result['code'] == 'TRANSACTION_REVERTED' and result['retryable'] is False
    chain(monkeypatch, value)
    assert c.get(path).json()['status'] == 'VERIFIED'


def test_rpc_sets_user_agent_and_falls_back_after_live_403(monkeypatch):
    import io, json, urllib.error
    seen = []
    def urlopen(request, timeout):
        seen.append(request)
        assert request.get_header('User-agent') == 'revelio-integrity/1.0'
        assert 0 < timeout <= 2
        if len(seen) == 1:
            raise urllib.error.HTTPError(request.full_url, 403, 'error code: 1010', {}, None)
        return io.BytesIO(json.dumps({'jsonrpc': '2.0', 'id': 1, 'result': '0x14a34'}).encode())
    monkeypatch.setattr(integrity.urllib.request, 'urlopen', urlopen)
    assert integrity.rpc('eth_chainId', []) == '0x14a34'
    assert [r.full_url for r in seen] == list(integrity.RPC_ENDPOINTS[:2])


def test_rpc_rate_limit_and_json_error_are_safe(monkeypatch):
    import io, json, urllib.error
    def limited(request, timeout):
        raise urllib.error.HTTPError(request.full_url, 429, 'secret upstream message', {}, None)
    monkeypatch.setattr(integrity.urllib.request, 'urlopen', limited)
    with pytest.raises(integrity.RPCFailure, match='^RPC_RATE_LIMITED$'):
        integrity.rpc('eth_chainId', [])
    monkeypatch.setattr(integrity.urllib.request, 'urlopen', lambda *a, **k: io.BytesIO(json.dumps(
        {'jsonrpc': '2.0', 'id': 1, 'error': {'code': -32601, 'message': 'secret upstream detail'}}).encode()))
    with pytest.raises(integrity.RPCFailure, match='^RPC_METHOD_UNSUPPORTED$'):
        integrity.rpc('trace_transaction', [TX])


def test_rpc_null_and_deadline_are_distinct_from_transport_failure(monkeypatch):
    import io, time
    monkeypatch.setattr(integrity.urllib.request, 'urlopen', lambda *a, **k: io.BytesIO(b'{"jsonrpc":"2.0","id":1,"result":null}'))
    assert integrity.rpc('eth_getTransactionByHash', [TX]) is None
    token = integrity._deadline.set(time.monotonic() - 1)
    try:
        with pytest.raises(integrity.RPCFailure, match='^RPC_TIMEOUT$'):
            integrity.rpc('eth_chainId', [])
    finally:
        integrity._deadline.reset(token)
