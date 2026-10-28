"""Opt-in localhost gateway; reuse real Revelio sessions, never forward cookies upstream."""
import os
import re
from urllib.parse import urlsplit

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from .auth import require_user

router = APIRouter()
ID = r'[a-f0-9]{32}'
ROUTES = {
    'GET': [r'api/health', r'api/cases', rf'api/cases/{ID}', rf'api/jobs/{ID}', rf'images/{ID}', rf'api/cases/{ID}/versions/{ID}/export.png'],
    'POST': [r'api/cases', rf'api/cases/{ID}/freeze', rf'api/cases/{ID}/clarifications', rf'api/cases/{ID}/prompt-preview', r'api/generate'],
}

@router.api_route('/wt-api/{path:path}', methods=['GET', 'POST'], dependencies=[Depends(require_user)])
async def forward(path: str, request: Request):
    target = os.environ.get('WITNESSTRACE_GATEWAY_TARGET', '')
    parsed = urlsplit(target)
    if parsed.scheme != 'http' or parsed.hostname != '127.0.0.1' or parsed.port in (8000, 8001) or parsed.username or parsed.path not in ('', '/') or parsed.query or parsed.fragment:
        raise HTTPException(503, 'Local WitnessTrace gateway is disabled or misconfigured.')
    if not any(re.fullmatch(p, path) for p in ROUTES.get(request.method, [])):
        raise HTTPException(404, 'Operation is outside the I3 gateway.')
    if request.method == 'POST':
        origin = request.headers.get('origin')
        if origin and origin != f'{request.url.scheme}://{request.headers.get("host")}':
            raise HTTPException(403, 'Cross-origin mutation rejected.')
        if not request.headers.get('content-type', '').startswith('application/json'):
            raise HTTPException(415, 'JSON required.')
    body = await request.body()
    if len(body) > 65536:
        raise HTTPException(413, 'Request too large.')
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=False, trust_env=False) as client:
            result = await client.request(request.method, target.rstrip('/') + '/' + path,
                                          content=body, headers={'content-type': 'application/json'})
    except httpx.TimeoutException:
        raise HTTPException(504, 'WitnessTrace timed out. Check existing jobs before submitting again.') from None
    except httpx.HTTPError:
        raise HTTPException(503, 'WitnessTrace is unavailable. Reconnect without resubmitting.') from None
    headers = {'cache-control': 'no-store'}
    if 'content-disposition' in result.headers:
        headers['content-disposition'] = result.headers['content-disposition']
    return Response(result.content, status_code=result.status_code,
                    media_type=result.headers.get('content-type'), headers=headers)
