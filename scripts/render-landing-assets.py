"""Pre-render the landing-page hero composites with the real procedural renderer.

Run:  backend/.venv/bin/python scripts/render-landing-assets.py
The profile is fictional demo data. Revision 2 applies refinements through the
same refinement service the workspace uses.
"""
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from PIL import Image  # noqa: E402

from app.services.procedural_renderer import render_profile  # noqa: E402
from app.services.refinement_service import apply_changes, parse_refinement  # noqa: E402
from app.services.trait_extractor import extract_traits  # noqa: E402

DEMO = ("An adult with an oval face, short dark hair, thick eyebrows, a narrow nose, "
        "and a small scar on the left cheek.")
OUT = ROOT / "public" / "landing"
OUT.mkdir(parents=True, exist_ok=True)

r1 = extract_traits(DEMO).profile
proposal = parse_refinement("make the eyebrows thicker, add a goatee, add rectangular glasses, make the jaw wider", r1)
r2 = apply_changes(r1, proposal["changes"])

for name, profile in (("demo-r1", r1), ("demo-r2", r2)):
    png = render_profile(profile, caption="DEMO · FICTIONAL").png
    img = Image.open(io.BytesIO(png)).convert("RGB")
    img.save(OUT / f"{name}.webp", "WEBP", quality=88, method=6)
    print(name, img.size, (OUT / f"{name}.webp").stat().st_size // 1024, "KB")
print("refinements:", [c["label"] for c in proposal["changes"]])
