"""Printable, self-contained HTML report for a sketch."""

from __future__ import annotations

import base64
from html import escape

from pathlib import Path

from ..database import connect, log_activity
from .sketch_service import DISCLAIMER, _split_traits, get_sketch, image_path


_LOGO = Path(__file__).resolve().parent.parent / "assets" / "logo-wordmark.png"


def _logo_html() -> str:
    try:
        data = base64.b64encode(_LOGO.read_bytes()).decode()
    except OSError:
        return ""
    return f"<img class='logo' src='data:image/png;base64,{data}' alt='Revelio' height='44'/>"


def _fmt(ts: str | None) -> str:
    return escape((ts or "").replace("T", " ").split(".")[0] + (" UTC" if ts else ""))


def build_report(sketch_id: str) -> str:
    s = get_sketch(sketch_id)
    cur = s["current"]
    img_html = "<div class='noimg'>No image</div>"
    if cur:
        data = base64.b64encode(image_path(sketch_id, cur["number"], "png").read_bytes()).decode()
        img_html = f"<img src='data:image/png;base64,{data}' alt='Composite {escape(s['id'])} revision {cur['number']}'/>"
    confirmed, unknown, conflicts = _split_traits(cur["profile"] if cur else {})
    marks = (cur["profile"].get("marks") if cur else []) or []

    trait_rows = "".join(
        f"<tr><td>{escape(t['label'])}</td><td>{escape(t['value_label'])}</td><td>{escape(t['source'] or '')}"
        f"{' · uncertain' if t['certainty'] == 'uncertain' else ''}</td>"
        f"<td>{'Drawn' if t['rendered'] == 'full' else 'Tone only' if t['rendered'] == 'tone' else 'Recorded only'}</td></tr>"
        for t in confirmed) or "<tr><td colspan='4'>No confirmed traits.</td></tr>"
    mark_rows = "".join(
        f"<li>{escape(m['size'])} {escape(m['type'])} — {escape(m['location'].replace('_', ' '))}"
        f"{'' if m.get('side_specified', True) else ' (side not stated)'}</li>" for m in marks) or "<li>None recorded</li>"
    conflict_html = "".join(f"<li>{escape(c['label'])}: {escape(' / '.join(c['alternatives']))}</li>" for c in conflicts)
    rev_rows = "".join(
        f"<tr><td>{r['number']}</td><td>{_fmt(r['created_at'])}</td><td>{escape(r['method_label'])}</td>"
        f"<td>{escape(r['change_note'] or '')}</td></tr>" for r in s["revisions"])
    notes = escape(s["notes"] or "—").replace("\n", "<br/>")
    with connect() as conn:
        log_activity(conn, "exported", f"Generated printable report for {sketch_id}", sketch_id)

    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Revelio — {escape(s['id'])}</title>
<style>
 *{{box-sizing:border-box}} body{{font-family:Inter,system-ui,-apple-system,Segoe UI,sans-serif;color:#111827;margin:0;padding:32px;background:#fff}}
 .wrap{{max-width:860px;margin:0 auto}} .mono{{font-family:'IBM Plex Mono',ui-monospace,Menlo,monospace}}
 header{{display:flex;justify-content:space-between;align-items:flex-end;border-bottom:2px solid #111827;padding-bottom:14px;margin-bottom:18px}}
 .head-left{{display:flex;align-items:center;gap:12px}} .logo{{height:44px;width:auto;border:0;border-radius:0}}
 .brand{{font-size:12px;letter-spacing:.16em;text-transform:uppercase;color:#0e7490;font-weight:700}}
 h1{{font-size:26px;margin:6px 0 0;letter-spacing:-.02em}} .meta{{text-align:right;font-size:12px;color:#4b5563;line-height:1.6}}
 .disclaimer{{border:1px solid #f59e0b;background:#fffbeb;color:#78350f;padding:12px 14px;border-radius:8px;font-size:13px;font-weight:600;margin-bottom:18px}}
 .grid{{display:grid;grid-template-columns:300px 1fr;gap:24px;align-items:start}}
 img{{width:100%;border:1px solid #d1d5db;border-radius:8px}} .noimg{{border:1px dashed #9ca3af;padding:80px 0;text-align:center;color:#6b7280}}
 .method{{font-size:12px;color:#374151;margin-top:8px}} h2{{font-size:13px;letter-spacing:.12em;text-transform:uppercase;color:#4b5563;margin:20px 0 8px}}
 table{{width:100%;border-collapse:collapse;font-size:13px}} td,th{{text-align:left;padding:7px 8px;border-bottom:1px solid #e5e7eb;vertical-align:top}}
 th{{font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:#6b7280;background:#f9fafb}}
 ul{{margin:0;padding-left:18px;font-size:13px;line-height:1.7}} .toolbar{{display:flex;gap:8px;justify-content:flex-end;margin-top:24px}}
 button{{font:inherit;border:1px solid #111827;background:#fff;border-radius:6px;padding:8px 14px;cursor:pointer}}
 @media print{{body{{padding:0}} .toolbar{{display:none}}}}
</style></head><body><div class="wrap">
<header><div class="head-left">{_logo_html()}<div><div class="brand">Forensic composite report</div><h1>{escape(s['title'])}</h1></div></div>
<div class="meta mono">{escape(s['id'])}<br/>Created {_fmt(s['created_at'])}<br/>Modified {_fmt(s['updated_at'])}<br/>Status: {escape(s['status'])}</div></header>
<div class="disclaimer">{escape(DISCLAIMER)}</div>
<div class="grid"><div>{img_html}<div class="method"><b>Generation method:</b> {escape(cur['method_label'] if cur else '—')}<br/>
<b>Revision:</b> {cur['number'] if cur else '—'} of {s['revision_count']}</div></div>
<div><h2>Confirmed facial traits</h2><table><thead><tr><th>Trait</th><th>Value</th><th>Source</th><th>In image</th></tr></thead><tbody>{trait_rows}</tbody></table>
<h2>Distinctive marks</h2><ul>{mark_rows}</ul>
<h2>Unknown traits</h2><p style="font-size:13px;color:#374151;margin:0">{escape(', '.join(unknown) or 'None')}</p>
{f'<h2>Unresolved conflicts</h2><ul>{conflict_html}</ul>' if conflicts else ''}
</div></div>
<h2>Witness description</h2><p style="font-size:13px;line-height:1.6;white-space:pre-wrap;margin:0">{escape(s['description'] or '—')}</p>
<h2>Revision history</h2><table><thead><tr><th>#</th><th>Created</th><th>Method</th><th>Change</th></tr></thead><tbody>{rev_rows}</tbody></table>
<h2>Operator notes</h2><p style="font-size:13px;line-height:1.6;margin:0">{notes}</p>
<div class="toolbar"><button onclick="window.print()">Print / Save as PDF</button></div>
</div></body></html>"""
