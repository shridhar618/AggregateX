"""Hash-only Base Sepolia commitments. The public RPC is independent of the wallet."""
import hashlib
import json
import re
import time
from contextvars import ContextVar
import urllib.error
import urllib.request

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field
import case_store as store

CHAIN = 84532
RPC = 'https://sepolia.base.org'
RPC_ENDPOINTS = (RPC, 'https://base-sepolia-rpc.publicnode.com', 'https://base-sepolia.drpc.org')
DELEGATION_MANAGER = '0xdb9b1e94b5b69df7e401ddbede43491141047db3'
_deadline = ContextVar('integrity_rpc_deadline', default=None)
SINK = '0x000000000000000000000000000000000000dead'


def initialize():
    with store.connection() as con:
        con.execute('''CREATE TABLE IF NOT EXISTS blockchain_integrity (
            version_id TEXT PRIMARY KEY REFERENCES versions(id),
            tx_hash TEXT UNIQUE NOT NULL, confirmed_at TEXT)''')
        columns = {r['name'] for r in con.execute('PRAGMA table_info(blockchain_integrity)')}
        if 'expected_sender' not in columns:
            con.execute('ALTER TABLE blockchain_integrity ADD COLUMN expected_sender TEXT')
        if 'legacy_confirmed' not in columns:
            con.execute('ALTER TABLE blockchain_integrity ADD COLUMN legacy_confirmed INTEGER NOT NULL DEFAULT 0')
            # Freeze eligibility at migration time; new confirmations never enable self-transfers.
            con.execute('UPDATE blockchain_integrity SET legacy_confirmed=1 WHERE confirmed_at IS NOT NULL')


class RPCFailure(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def rpc(method, params):
    # Explicit User-Agent avoids the live RPC edge's Python-urllib 403 / 1010 rejection.
    # Only fixed public endpoints and read methods are allowed; never broadcast here.
    allowed = {'eth_chainId', 'eth_getTransactionByHash', 'eth_getTransactionReceipt',
               'eth_getBlockByNumber', 'trace_transaction'}
    if method not in allowed:
        raise RPCFailure('RPC_METHOD_UNSUPPORTED')
    endpoints = RPC_ENDPOINTS[1:] if method == 'trace_transaction' else RPC_ENDPOINTS
    failure = 'RPC_UNAVAILABLE'
    deadline = _deadline.get() or time.monotonic() + 8
    for endpoint in endpoints:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise RPCFailure('RPC_TIMEOUT')
        request = urllib.request.Request(endpoint, data=json.dumps({
            'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params
        }).encode(), headers={'Content-Type': 'application/json',
                             'Accept': 'application/json', 'User-Agent': 'revelio-integrity/1.0'})
        try:
            with urllib.request.urlopen(request, timeout=min(2, remaining)) as response:
                value = json.load(response)
            if not isinstance(value, dict) or value.get('id') != 1 or value.get('jsonrpc') != '2.0':
                failure = 'RPC_INVALID_RESPONSE'
                continue
            if 'error' in value:
                code = value['error'].get('code') if isinstance(value['error'], dict) else None
                failure = ('RPC_RATE_LIMITED' if code in (429, -32005, -32016) else
                           'RPC_METHOD_UNSUPPORTED' if code in (-32601, -32611) else 'RPC_UNAVAILABLE')
                continue
            if 'result' not in value:
                failure = 'RPC_INVALID_RESPONSE'
                continue
            return value['result']  # JSON null is pending/not visible, not a transport error.
        except urllib.error.HTTPError as exc:
            failure = 'RPC_RATE_LIMITED' if exc.code == 429 else 'RPC_ACCESS_DENIED' if exc.code in (401, 403) else 'RPC_UNAVAILABLE'
        except (TimeoutError, urllib.error.URLError, OSError):
            failure = 'RPC_UNAVAILABLE'
        except (ValueError, TypeError):
            failure = 'RPC_INVALID_RESPONSE'
    raise RPCFailure(failure)


def quantity(value):
    if not isinstance(value, str) or not re.fullmatch(r'0x[0-9a-fA-F]+', value):
        raise ValueError('Invalid RPC quantity')
    return int(value, 16)


def same_hex(a, b):
    return isinstance(a, str) and isinstance(b, str) and a.lower() == b.lower()


def executed_commitment(value, tx, receipt):
    """Validate executed calls, never a substring in a wallet wrapper or an event."""
    traces = rpc('trace_transaction', [value['tx_hash']])
    if not isinstance(traces, list) or not traces:
        raise RPCFailure('RPC_TRACE_UNAVAILABLE')
    by_path = {}
    for trace in traces:
        path = trace['traceAddress']
        if not isinstance(path, list) or any(type(i) is not int or i < 0 for i in path):
            raise ValueError('Invalid trace path')
        key = tuple(path)
        if key in by_path:
            raise ValueError('Duplicate trace path')
        by_path[key] = trace
        if (not same_hex(trace['transactionHash'], tx['hash'])
                or not same_hex(trace['blockHash'], receipt['blockHash'])
                or type(trace['blockNumber']) is not int
                or trace['blockNumber'] != quantity(receipt['blockNumber'])):
            raise ValueError('Trace transaction/block mismatch')
    root = by_path.get(())
    if not root or root.get('error') or 'result' not in root:
        raise ValueError('Missing successful root trace')
    action = root['action']
    if (root['type'] != 'call' or action['callType'] != 'call'
            or not same_hex(action['from'], tx['from']) or not same_hex(action['to'], tx['to'])
            or not same_hex(action['input'], tx['input']) or quantity(action['value']) != 0):
        raise ValueError('Root trace does not match transaction')
    for path, trace in by_path.items():
        action = trace.get('action', {})
        if (not path or trace.get('type') != 'call' or action.get('callType') != 'call'
                or not same_hex(action.get('to'), SINK) or not same_hex(action.get('input'), value['data'])
                or quantity(action['value']) != 0 or trace.get('error') or 'result' not in trace):
            continue
        # Every ancestor must have executed successfully, and caller addresses must link.
        valid = True
        for depth in range(1, len(path) + 1):
            child = by_path.get(path[:depth])
            parent = by_path.get(path[:depth - 1])
            if (not child or not parent or child.get('error') or parent.get('error')
                    or 'result' not in child or 'result' not in parent
                    or parent.get('type') != 'call' or parent['action'].get('callType') != 'call'
                    or not same_hex(child['action'].get('from'), parent['action'].get('to'))):
                valid = False
                break
        if valid:
            return action['from'].lower()
    return None


def snapshot(case_id, version_id):
    store.identifier(case_id)
    store.identifier(version_id)
    with store.connection() as con:
        version = con.execute('SELECT * FROM versions WHERE id=? AND case_id=?', (version_id, case_id)).fetchone()
        if not version:
            raise HTTPException(404, 'Unknown case image revision')
        registration = con.execute('SELECT * FROM blockchain_integrity WHERE version_id=?', (version_id,)).fetchone()
    path = store.DATA / version['path']
    safe = store.safe_path(case_id, version_id, path.suffix)
    if path.resolve() != safe.resolve() or path.is_symlink() or not path.is_file():
        raise HTTPException(404, 'Saved image unavailable')
    with path.open('rb') as image:
        current = hashlib.file_digest(image, 'sha256').hexdigest()
    # Revision identity is domain-separated and hashed too; no case ID or testimony is public.
    commitment = hashlib.sha256(('revelio:witnesstrace:image:v1:' + version_id + ':' + version['sha256']).encode()).hexdigest()
    data = '0x' + ('revelio:image:v1:sha256:' + commitment).encode().hex()
    return {'chain_id': CHAIN, 'sha256': version['sha256'], 'current_sha256': current,
            'data': data, 'tx_hash': registration['tx_hash'] if registration else None,
            'expected_sender': registration['expected_sender'] if registration else None,
            'legacy_confirmed': bool(registration and registration['legacy_confirmed'])}


def check(value):
    value = dict(value)
    def outcome(status, code, message, retryable=False, **extra):
        return dict(value, status=status, code=code, message=message, retryable=retryable, **extra)
    if value['current_sha256'] != value['sha256']:
        return outcome('TAMPERED', 'IMAGE_HASH_MISMATCH', 'Saved image bytes differ from the original revision digest.')
    if not value['tx_hash']:
        return outcome('NOT REGISTERED', 'NOT_REGISTERED', 'No blockchain registration for this revision.')
    token = _deadline.set(time.monotonic() + 10)
    try:
        if quantity(rpc('eth_chainId', [])) != CHAIN:
            return outcome('ERROR', 'RPC_WRONG_CHAIN', 'RPC returned a different network. Verification was not completed.', True)
        tx = rpc('eth_getTransactionByHash', [value['tx_hash']])
        if tx is None:
            return outcome('PENDING', 'TRANSACTION_NOT_VISIBLE', 'Transaction is not visible to the public RPC yet. Retry verification; do not register again.', True)
        if quantity(tx['chainId']) != CHAIN or not same_hex(tx['hash'], value['tx_hash']):
            return outcome('ERROR', 'TRANSACTION_IDENTITY_MISMATCH', 'Transaction network or hash does not match the registration.')
        sender = tx['from'].lower()
        if not re.fullmatch(r'0x[0-9a-f]{40}', sender):
            raise ValueError('Invalid sender')
        legacy = value['legacy_confirmed'] and same_hex(tx.get('to'), sender)
        expected_sender = value['expected_sender']
        if (not expected_sender and not legacy) or (expected_sender and not same_hex(sender, expected_sender)):
            return outcome('TAMPERED', 'SENDER_MISMATCH', 'Transaction sender differs from the registered wallet.')
        if quantity(tx['value']) != 0:
            return outcome('TAMPERED', 'NONZERO_VALUE', 'Registration transaction must have zero transfer value.')
        direct = same_hex(tx.get('to'), SINK) or legacy
        wrapped = (same_hex(tx.get('to'), DELEGATION_MANAGER) and quantity(tx.get('type')) == 4
                   and tx['input'].lower().startswith('0xcef6d209'))
        if not direct and not wrapped:
            return outcome('TAMPERED', 'RECIPIENT_MISMATCH', 'Transaction recipient is not the expected sink or supported wallet wrapper.')
        if sender == SINK:
            return outcome('TAMPERED', 'SENDER_MISMATCH', 'Sender must differ from the sink recipient.')
        if direct and not same_hex(tx['input'], value['data']):
            return outcome('TAMPERED', 'COMMITMENT_MISMATCH', 'Transaction does not match this image revision commitment.')
        receipt = rpc('eth_getTransactionReceipt', [value['tx_hash']])
        if receipt is None:
            return outcome('PENDING', 'RECEIPT_PENDING', 'Transaction is awaiting a mined receipt.', True)
        if (not same_hex(receipt['transactionHash'], value['tx_hash'])
                or not same_hex(receipt['from'], sender) or not same_hex(receipt['to'], tx['to'])):
            return outcome('ERROR', 'RECEIPT_IDENTITY_MISMATCH', 'Receipt identity does not match the transaction.')
        status = quantity(receipt['status'])
        if status == 0:
            return outcome('ERROR', 'TRANSACTION_REVERTED', 'The on-chain transaction failed. This registration is not verified.')
        if status != 1:
            raise ValueError('Invalid receipt status')
        if tx.get('blockHash') is None or tx.get('blockNumber') is None or receipt.get('blockHash') is None or receipt.get('blockNumber') is None:
            return outcome('PENDING', 'BLOCK_PENDING', 'Waiting for transaction and receipt block information.', True)
        block = rpc('eth_getBlockByNumber', [receipt['blockNumber'], False])
        if (not block or not same_hex(block['hash'], receipt['blockHash'])
                or not same_hex(tx['blockHash'], receipt['blockHash'])
                or quantity(tx['blockNumber']) != quantity(receipt['blockNumber'])):
            return outcome('PENDING', 'BLOCK_NOT_CANONICAL', 'Waiting for canonical block confirmation.', True)
        extra = {'verification_mode': 'legacy_direct' if legacy else 'direct'}
        if wrapped:
            execution_sender = executed_commitment(value, tx, receipt)
            if not execution_sender:
                return outcome('TAMPERED', 'EXECUTED_COMMITMENT_MISMATCH', 'No successful executed zero-value call matches the sink and image revision commitment.')
            extra = {'verification_mode': 'wallet_delegation_trace', 'execution_sender': execution_sender}
        return outcome('VERIFIED', 'VERIFIED', 'Current image digest and successful canonical transaction match.', expected_sender=sender, **extra)
    except RPCFailure as exc:
        messages = {
            'RPC_RATE_LIMITED': 'Public RPC is rate limited. Retry verification later; the transaction has not been declared invalid.',
            'RPC_ACCESS_DENIED': 'Public RPC access was denied. Retry verification later; the transaction has not been declared invalid.',
            'RPC_METHOD_UNSUPPORTED': 'Public RPC cannot provide the execution trace needed to verify this wallet transaction.',
            'RPC_TRACE_UNAVAILABLE': 'Execution trace is not available yet. Retry verification later.',
            'RPC_TIMEOUT': 'Public RPC verification timed out. Retry verification; do not register again.',
        }
        return outcome('ERROR', exc.code, messages.get(exc.code, 'Public RPC is unavailable or returned an invalid response. Retry verification; do not register again.'), True)
    except (KeyError, TypeError, ValueError, AttributeError, IndexError):
        return outcome('ERROR', 'RPC_INVALID_RESPONSE', 'Public RPC returned incomplete or malformed transaction data. Verification was not completed.', True)
    except OSError:
        return outcome('ERROR', 'RPC_UNAVAILABLE', 'Public RPC connection failed. Retry verification; do not register again.', True)
    finally:
        _deadline.reset(token)


class Registration(BaseModel):
    model_config = ConfigDict(extra='forbid')
    sender: str = Field(pattern=r'^0x[a-fA-F0-9]{40}$')
    tx_hash: str = Field(pattern=r'^0x[a-fA-F0-9]{64}$')


def verify(case_id, version_id):
    result = check(snapshot(case_id, version_id))
    if result['status'] == 'VERIFIED':
        with store.connection() as con:
            con.execute('UPDATE blockchain_integrity SET confirmed_at=COALESCE(confirmed_at,?),expected_sender=COALESCE(expected_sender,?) WHERE version_id=? AND tx_hash=?',
                        (store.now(), result['expected_sender'], version_id, result['tx_hash']))
    return result


def register(case_id, version_id, request):
    value = snapshot(case_id, version_id)
    tx_hash = request.tx_hash.lower()
    sender = request.sender.lower()
    if sender == SINK:
        raise HTTPException(422, 'Sender must differ from the fixed sink recipient')
    if value['expected_sender'] and value['expected_sender'].lower() != sender:
        raise HTTPException(409, 'Registration wallet cannot be changed')
    if value['current_sha256'] != value['sha256']:
        raise HTTPException(409, 'Image integrity check failed; registration blocked')
    # A pending reference is durable, but never treated as proof. Every verification queries the chain.
    if value['tx_hash'] and value['tx_hash'] != tx_hash:
        previous = check(value)
        if previous['status'] != 'ERROR':
            raise HTTPException(409, 'This revision already has a transaction; verify it before retrying')
        raise HTTPException(409, 'Existing transaction requires investigation; it cannot be overwritten')
    with store.connection() as con:
        con.execute('INSERT OR IGNORE INTO blockchain_integrity(version_id,tx_hash,expected_sender) VALUES (?,?,?)', (version_id, tx_hash, sender))
        saved = con.execute('SELECT tx_hash FROM blockchain_integrity WHERE version_id=?', (version_id,)).fetchone()
        if not saved or saved['tx_hash'] != tx_hash:
            raise HTTPException(409, 'Transaction is already assigned to another revision')
    return verify(case_id, version_id)
