from app.services.merge_service import merge_descriptions
from app.services.refinement_service import apply_changes, parse_refinement


def _keys(result):
    return {(c["kind"], c["key"]) for c in result["changes"]}


def test_spec_refinements(spec_profile):
    assert ("trait", "eyebrow_thickness") in _keys(parse_refinement("Make the eyebrows thicker.", spec_profile))
    assert ("trait", "face_shape") in _keys(parse_refinement("Change the face shape to square.", spec_profile))
    assert ("trait", "hairline") in _keys(parse_refinement("Make the hairline receding.", spec_profile))
    assert ("adjust", "jaw_width") in _keys(parse_refinement("Make the jaw narrower.", spec_profile))
    r = parse_refinement("Add a mole on the right cheek.", spec_profile)
    assert ("mark_add", "mole") in _keys(r)


def test_noop_refinement_is_reported_not_faked(spec_profile):
    r = parse_refinement("Change the face shape to oval.", spec_profile)
    assert r["changes"] == [] and r["already"]


def test_unrecognised_refinement(spec_profile):
    r = parse_refinement("make him look friendlier", spec_profile)
    assert r["changes"] == [] and r["unrecognized"] and r["message"]


def test_apply_marks_traits_manual_and_preserves_input(spec_profile):
    r = parse_refinement("make the eyebrows thicker and remove the scar", spec_profile)
    new = apply_changes(spec_profile, r["changes"])
    assert new.traits["eyebrow_thickness"].value == "bushy"
    assert new.traits["eyebrow_thickness"].source == "manual"
    assert new.marks == []
    assert spec_profile.traits["eyebrow_thickness"].value == "thick"  # original untouched
    assert len(spec_profile.marks) == 1


def test_merge_classifies_and_never_resolves_conflicts():
    res = merge_descriptions([
        "A man with short dark hair, blue eyes and a scar on his left cheek.",
        "A man with short black hair, brown eyes and a crooked nose.",
    ])
    status = {r["key"]: r["status"] for r in res["traits"]}
    assert status["presentation"] == "shared"
    assert status["hair_length"] == "shared"
    assert status["hair_color"] == "shared"          # dark + black are compatible
    assert status["eye_color"] == "conflicting"
    assert status["nose_shape"] == "single_source"
    assert status["ears"] == "unmentioned"
    combined = res["combined_profile"]["traits"]
    assert combined["eye_color"]["value"] is None
    assert set(combined["eye_color"]["alternatives"]) == {"blue", "brown"}
    assert "eye_color" in res["requires_review"]
