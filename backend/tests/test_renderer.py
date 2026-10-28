import io

from PIL import Image

from app.schemas import Profile, TraitValue
from app.services.procedural_renderer import render_profile


def _with(profile: Profile, **traits) -> Profile:
    p = profile.model_copy(deep=True)
    for k, v in traits.items():
        p.traits[k] = TraitValue(value=v, source="manual")
    return p


def test_renders_real_png(spec_profile):
    r = render_profile(spec_profile, caption="RV-TEST")
    assert r.png.startswith(b"\x89PNG\r\n\x1a\n")
    img = Image.open(io.BytesIO(r.png))
    assert img.size == (900, 1125)
    # not a blank/static image: plenty of distinct grey levels
    assert len(set(img.convert("L").getdata())) > 50
    assert r.svg.startswith("<svg") and "NOT A PHOTOGRAPH" in r.svg


def test_rendering_is_deterministic(spec_profile):
    assert render_profile(spec_profile).png == render_profile(spec_profile).png


def test_feature_changes_change_output(spec_profile):
    base = render_profile(spec_profile)
    for key, value in [("face_shape", "square"), ("nose_shape", "hooked"), ("eyebrow_thickness", "thin"),
                       ("hair_style", "curly"), ("facial_hair", "full_beard"), ("eyewear", "round_glasses"),
                       ("hairline", "receding"), ("chin", "cleft"), ("ears", "protruding"), ("eye_shape", "round")]:
        changed = render_profile(_with(spec_profile, **{key: value}))
        assert changed.svg != base.svg, key
        assert changed.png != base.png, key


def test_adjustments_change_output(spec_profile):
    base = render_profile(spec_profile).svg
    for key in ("jaw_width", "eye_spacing", "nose_width", "nose_length", "mouth_width", "eyebrow_thickness", "face_width"):
        p = spec_profile.model_copy(deep=True)
        p.adjustments[key] = 0.8
        assert render_profile(p).svg != base, key


def test_mark_position_changes_output(spec_profile):
    p = spec_profile.model_copy(deep=True)
    p.marks[0].dx = 0.6
    assert render_profile(p).svg != render_profile(spec_profile).svg


def test_unknown_traits_reported_as_defaults(spec_profile):
    notes = render_profile(spec_profile).notes
    defaulted = {n["trait"] for n in notes if n["kind"] == "default"}
    assert "eye_shape" in defaulted and "ears" in defaulted


def test_undescribed_hair_is_unspecified_not_invented():
    notes = render_profile(Profile()).notes
    assert any(n["kind"] == "unspecified" and n["trait"] == "hair_length" for n in notes)


def test_recorded_only_traits_are_reported(spec_profile):
    p = _with(spec_profile, eye_color="blue", skin_tone="olive")
    kinds = {(n["trait"], n["kind"]) for n in render_profile(p).notes}
    assert ("eye_color", "not_rendered") in kinds and ("skin_tone", "not_rendered") in kinds


def test_conflict_is_reported():
    p = Profile(traits={"face_shape": TraitValue(value=None, source="extracted", alternatives=["round", "long"])})
    assert any(n["kind"] == "conflict" for n in render_profile(p).notes)
