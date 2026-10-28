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
    'GET': [rf'api/cases/{ID}/versions/{ID}/integrity', r'api/lab-schema', r'api/enhance-schema', rf'api/cases/{ID}/multiview', rf'api/cases/{ID}/reports', rf'api/cases/{ID}/reports/{ID}/(?:preview|pdf|json|png)', rf'api/cases/{ID}/versions/{ID}/(?:sketch|enhance|pixels|export.json)', rf'api/cases/{ID}/views/{ID}/layouts/{ID}/(?:front|left|right|back|three_quarter|three_quarter_left|three_quarter_right|left_profile|right_profile).png', r'api/health', r'api/cases', rf'api/cases/{ID}', rf'api/jobs/{ID}', rf'images/{ID}', rf'api/cases/{ID}/versions/{ID}/export.png'],
    'PUT': [rf'api/cases/{ID}'],
    'POST': [rf'api/cases/{ID}/versions/{ID}/integrity', rf'api/cases/{ID}/(?:selection|refinement-preview|refine|local-edits|imports|enhancements|multiview-preview|multiview|reports)', rf'api/cases/{ID}/views/{ID}/layouts', r'api/cases', rf'api/cases/{ID}/freeze', rf'api/cases/{ID}/clarifications', rf'api/cases/{ID}/prompt-preview', r'api/generate'],
}

@router.api_route('/wt-api/{path:path}', methods=['GET', 'POST', 'PUT'], dependencies=[Depends(require_user)])
async def forward(path: str, request: Request):
    target = os.environ.get('WITNESSTRACE_GATEWAY_TARGET', '')
    parsed = urlsplit(target)
    if parsed.scheme != 'http' or parsed.hostname != '127.0.0.1' or parsed.port in (8000, 8001) or parsed.username or parsed.path not in ('', '/') or parsed.query or parsed.fragment:
        raise HTTPException(503, 'Local WitnessTrace gateway is disabled or misconfigured.')
    assets = {'index.html', 'workbench.css', 'workbench-polish.css', 'character-lab.js', 'workbench.js', 'refinement.js', 'sketchpad.js', 'enhance.js', 'enhance-worker.js', 'multiview-reports.js', 'react-bridge.js', 'react-tools.css'}
    if request.method == 'GET' and path.startswith('tools/') and (path[6:] in assets or re.fullmatch(r'icons/[a-z0-9-]+\.svg', path[6:])):
        from pathlib import Path
        asset = Path(__file__).resolve().parents[3] / 'witness-backend' / 'static' / path[6:]
        if not asset.is_file():
            raise HTTPException(404, 'Unknown tool asset')
        content = asset.read_text()
        if asset.suffix == '.html':
            content = content.replace('<head>', '<head><script src="/wt-api/tools/react-bridge.js"></script>').replace('</head>', '<link rel="stylesheet" href="/wt-api/tools/react-tools.css"></head>')
        content = content.replace('/static/', '/wt-api/tools/').replace('/api/', '/wt-api/api/')
        return Response(content, media_type={'.html':'text/html', '.js':'text/javascript', '.css':'text/css', '.svg':'image/svg+xml'}[asset.suffix], headers={'cache-control':'no-store', 'x-content-type-options':'nosniff', 'content-security-policy':"frame-ancestors 'self'; object-src 'none'"})
    if not any(re.fullmatch(p, path) for p in ROUTES.get(request.method, [])):
        raise HTTPException(404, 'Operation is outside the WitnessTrace gateway.')
    if request.method in ('POST', 'PUT'):
        origin = request.headers.get('origin')
        if origin and origin != f'{request.url.scheme}://{request.headers.get("host")}':
            raise HTTPException(403, 'Cross-origin mutation rejected.')
        if not request.headers.get('content-type', '').startswith('application/json'):
            raise HTTPException(415, 'JSON required.')
    body = await request.body()
    if len(body) > 48 * 1024 * 1024:
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
