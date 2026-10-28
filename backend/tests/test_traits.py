import pytest

from app.schemas import validate_description
from app.services.trait_extractor import extract_traits
from tests.conftest import SPEC_DESCRIPTION


@pytest.mark.parametrize("text", ["", "   ", "short", "1234567890 !!!", "x" * 2001])
def test_description_validation_rejects_bad_input(text):
    with pytest.raises(ValueError):
        validate_description(text)


def test_description_validation_accepts_and_trims():
    assert validate_description("  A tall man with dark hair  ") == "A tall man with dark hair"


def test_extracts_spec_example():
    ex = extract_traits(SPEC_DESCRIPTION)
    t = ex.profile.traits
    assert t["presentation"].value == "masculine"
    assert t["face_shape"].value == "oval"
    assert t["hair_length"].value == "short"
    assert t["hair_color"].value == "dark"
    assert t["eyebrow_thickness"].value == "thick"
    assert t["nose_shape"].value == "narrow"
    assert t["facial_hair"].value == "stubble"
    assert [(m.type, m.location, m.size) for m in ex.profile.marks] == [("scar", "left_cheek", "small")]
    assert all(v.source == "extracted" for v in t.values() if v.value)


def test_unmentioned_traits_stay_unknown():
    ex = extract_traits(SPEC_DESCRIPTION)
    for key in ("eye_color", "eye_shape", "ears", "mouth_shape", "skin_tone", "age_range"):
        assert ex.profile.traits[key].value is None
        assert ex.profile.traits[key].source == "unknown"
        assert key in ex.unknown_traits


def test_missing_info_is_not_turned_into_a_negative():
    ex = extract_traits("A woman with long curly red hair and green eyes.")
    assert ex.profile.traits["eyewear"].value is None      # not "none"
    assert ex.profile.traits["facial_hair"].value is None  # not "none"


def test_explicit_negative_is_recorded():
    ex = extract_traits("He was clean-shaven and was not wearing glasses, no glasses at all.")
    assert ex.profile.traits["facial_hair"].value == "none"
    assert ex.profile.traits["eyewear"].value == "none"


def test_conflicting_statements_are_not_silently_resolved():
    ex = extract_traits("He had blue eyes. Actually, I think he had brown eyes.")
    tv = ex.profile.traits["eye_color"]
    assert tv.value is None
    assert set(tv.alternatives) == {"blue", "brown"}
    assert ex.conflicts and ex.conflicts[0]["key"] == "eye_color"


def test_compatible_refinements_are_not_conflicts():
    ex = extract_traits("dark hair, jet black hair, a mustache and a goatee")
    assert ex.profile.traits["hair_color"].value == "black"
    assert ex.profile.traits["facial_hair"].value == "goatee"
    assert not ex.conflicts


def test_hedged_statement_marked_uncertain():
    ex = extract_traits("Maybe a hooked nose, short hair.")
    assert ex.profile.traits["nose_shape"].certainty == "uncertain"
    assert ex.profile.traits["hair_length"].certainty == "stated"


def test_dont_remember_is_explicit_unknown():
    ex = extract_traits("A man with a beard. I don't remember his eye colour.")
    assert "eye_color" in ex.explicit_unknowns
    assert ex.profile.traits["eye_color"].value is None


def test_mark_without_side_is_flagged():
    ex = extract_traits("There was a scar on his cheek.")
    assert ex.profile.marks[0].side_specified is False


def test_ages_are_bucketed():
    assert extract_traits("a man about 35 years old").profile.traits["age_range"].value == "adult"
    assert extract_traits("she was in her late twenties").profile.traits["age_range"].value == "young_adult"
    assert extract_traits("an elderly man with gray hair").profile.traits["age_range"].value == "senior"


def test_nothing_recognised_warns():
    ex = extract_traits("I only saw them briefly from far away.")
    assert ex.warnings


def test_negated_mentions_do_not_create_traits():
    ex = extract_traits("A man with short hair, not wearing glasses, and without a beard.")
    assert ex.profile.traits["eyewear"].value == "none"
    assert ex.profile.traits["facial_hair"].value == "none"
    assert not ex.conflicts


def test_not_sure_is_a_hedge_not_a_negation():
    ex = extract_traits("I'm not sure, but a beard I think.")
    assert ex.profile.traits["facial_hair"].value == "full_beard"
    assert ex.profile.traits["facial_hair"].certainty == "uncertain"
