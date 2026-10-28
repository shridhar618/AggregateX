"""Facial-trait catalog: the single source of truth for trait keys, options,
labels, and whether the offline renderer can actually draw each trait.

The frontend fetches this catalog, so editors, guided questions and the
renderer can never drift apart.
"""

from __future__ import annotations

# rendered:
#   "full"     – the offline renderer draws this trait
#   "tone"     – drawn as a monochrome tone only
#   "recorded" – kept in the profile/report but NOT drawn (honestly reported)
TRAITS: list[dict] = [
    {
        "key": "presentation", "label": "Presentation", "group": "General",
        "options": ["masculine", "feminine"], "rendered": "full",
        "note": "Slightly adjusts jaw and brow proportions only.",
    },
    {
        "key": "age_range", "label": "Approximate age", "group": "General",
        "options": ["child", "teen", "young_adult", "adult", "middle_aged", "senior"],
        "option_labels": {
            "child": "Child", "teen": "Teen", "young_adult": "Young adult (18–30)",
            "adult": "Adult (30–45)", "middle_aged": "Middle-aged (45–60)", "senior": "Senior (60+)",
        },
        "rendered": "full", "note": "Drawn as age lines and proportion changes.",
    },
    {
        "key": "face_shape", "label": "Face shape", "group": "Face",
        "options": ["oval", "round", "square", "long", "heart", "diamond", "triangular"], "rendered": "full",
    },
    {
        "key": "jawline", "label": "Jawline", "group": "Face",
        "options": ["narrow", "average", "wide", "angular"], "rendered": "full",
    },
    {
        "key": "chin", "label": "Chin", "group": "Face",
        "options": ["pointed", "rounded", "square", "cleft", "receding", "prominent"], "rendered": "full",
    },
    {
        "key": "hair_length", "label": "Hair length", "group": "Hair",
        "options": ["bald", "shaved", "short", "medium", "long"], "rendered": "full",
    },
    {
        "key": "hair_style", "label": "Hair style", "group": "Hair",
        "options": ["straight", "wavy", "curly", "spiky", "slicked_back", "side_part"], "rendered": "full",
    },
    {
        "key": "hair_color", "label": "Hair colour", "group": "Hair",
        "options": ["black", "dark", "brown", "red", "blonde", "light", "gray", "white"], "rendered": "tone",
        "note": "Monochrome composite: colour is drawn as a tone (darker or lighter).",
    },
    {
        "key": "hairline", "label": "Hairline", "group": "Hair",
        "options": ["normal", "receding", "widows_peak", "high", "low"],
        "option_labels": {"widows_peak": "Widow's peak"}, "rendered": "full",
    },
    {
        "key": "eyebrow_thickness", "label": "Eyebrow thickness", "group": "Eyes & brows",
        "options": ["thin", "medium", "thick", "bushy"], "rendered": "full",
    },
    {
        "key": "eyebrow_shape", "label": "Eyebrow shape", "group": "Eyes & brows",
        "options": ["straight", "arched", "angled", "curved", "unibrow"], "rendered": "full",
    },
    {
        "key": "eye_shape", "label": "Eye shape", "group": "Eyes & brows",
        "options": ["almond", "round", "narrow", "hooded", "downturned", "upturned", "deep_set"], "rendered": "full",
    },
    {
        "key": "eye_spacing", "label": "Eye spacing", "group": "Eyes & brows",
        "options": ["close", "average", "wide"], "rendered": "full",
    },
    {
        "key": "eye_color", "label": "Eye colour", "group": "Eyes & brows",
        "options": ["brown", "dark", "blue", "green", "hazel", "gray", "light"], "rendered": "recorded",
        "note": "Recorded only. The monochrome composite does not show eye colour.",
    },
    {
        "key": "eyewear", "label": "Eyewear", "group": "Eyes & brows",
        "options": ["none", "glasses", "round_glasses", "rectangular_glasses", "sunglasses"],
        "option_labels": {
            "glasses": "Glasses (style unspecified)", "round_glasses": "Round glasses",
            "rectangular_glasses": "Rectangular glasses",
        },
        "rendered": "full",
    },
    {
        "key": "nose_shape", "label": "Nose shape", "group": "Nose & mouth",
        "options": ["straight", "narrow", "wide", "broad", "hooked", "button", "crooked", "pointed", "flat"],
        "rendered": "full",
    },
    {
        "key": "mouth_shape", "label": "Mouth / lips", "group": "Nose & mouth",
        "options": ["thin", "full", "wide", "small", "downturned"], "rendered": "full",
    },
    {
        "key": "facial_hair", "label": "Facial hair", "group": "Nose & mouth",
        "options": ["none", "stubble", "mustache", "goatee", "full_beard"], "rendered": "full",
    },
    {
        "key": "ears", "label": "Ears", "group": "Face",
        "options": ["small", "average", "large", "protruding"], "rendered": "full",
    },
    {
        "key": "skin_tone", "label": "Skin tone", "group": "General",
        "options": ["very_light", "light", "medium", "olive", "tan", "brown", "dark"], "rendered": "recorded",
        "note": "Recorded only. The monochrome composite does not show skin tone.",
    },
]

MARK_TYPES = ["scar", "mole", "birthmark", "tattoo", "piercing", "freckles"]
MARK_LOCATIONS = [
    "forehead", "left_eyebrow", "right_eyebrow", "left_eye", "right_eye", "nose",
    "left_cheek", "right_cheek", "upper_lip", "lower_lip", "chin", "left_jaw", "right_jaw",
    "left_ear", "right_ear", "neck",
]
MARK_SIZES = ["small", "medium", "large"]

# Fine-tuning sliders (range -1..1, 0 = derived from traits).
ADJUSTMENTS: list[dict] = [
    {"key": "face_width", "label": "Face width", "group": "Face"},
    {"key": "face_length", "label": "Face length", "group": "Face"},
    {"key": "jaw_width", "label": "Jaw width", "group": "Face"},
    {"key": "chin_length", "label": "Chin length", "group": "Face"},
    {"key": "ear_size", "label": "Ear size", "group": "Face"},
    {"key": "hair_volume", "label": "Hair volume", "group": "Hair"},
    {"key": "eyebrow_thickness", "label": "Eyebrow thickness", "group": "Eyes & brows"},
    {"key": "eyebrow_height", "label": "Eyebrow height", "group": "Eyes & brows"},
    {"key": "eye_spacing", "label": "Eye spacing", "group": "Eyes & brows"},
    {"key": "eye_size", "label": "Eye size", "group": "Eyes & brows"},
    {"key": "eye_height", "label": "Eye placement (vertical)", "group": "Eyes & brows"},
    {"key": "nose_width", "label": "Nose width", "group": "Nose & mouth"},
    {"key": "nose_length", "label": "Nose length", "group": "Nose & mouth"},
    {"key": "mouth_width", "label": "Mouth width", "group": "Nose & mouth"},
    {"key": "lip_fullness", "label": "Lip fullness", "group": "Nose & mouth"},
    {"key": "mouth_height", "label": "Mouth placement (vertical)", "group": "Nose & mouth"},
]

TRAIT_KEYS = [t["key"] for t in TRAITS]
TRAIT_BY_KEY = {t["key"]: t for t in TRAITS}
ADJUSTMENT_KEYS = [a["key"] for a in ADJUSTMENTS]

# Ordinal scales used by refinement ("thicker", "wider", ...).
ORDINAL = {
    "eyebrow_thickness": ["thin", "medium", "thick", "bushy"],
    "hair_length": ["bald", "shaved", "short", "medium", "long"],
    "eye_spacing": ["close", "average", "wide"],
    "jawline": ["narrow", "average", "wide"],
    "ears": ["small", "average", "large"],
}

SOURCES = ["described", "extracted", "manual", "unknown"]


def humanize(value: str | None) -> str:
    if value is None:
        return "Unknown"
    return str(value).replace("_", " ").capitalize()


def option_label(key: str, value: str | None) -> str:
    if value is None:
        return "Unknown"
    trait = TRAIT_BY_KEY.get(key, {})
    return trait.get("option_labels", {}).get(value, humanize(value))


def catalog_payload() -> dict:
    return {
        "traits": TRAITS,
        "marks": {"types": MARK_TYPES, "locations": MARK_LOCATIONS, "sizes": MARK_SIZES},
        "adjustments": ADJUSTMENTS,
        "sources": SOURCES,
        "limits": {"description_min": 10, "description_max": 2000},
    }
