"""Deterministic facial-trait extraction from a free-text witness description.

Design rules
------------
* Never invent: a trait that is not mentioned stays ``unknown``.
* Never silently resolve: if the description states two incompatible values for
  the same trait, the trait keeps ``value=None`` and lists the alternatives.
* Hedged statements ("maybe", "I think") are kept but flagged ``uncertain``.
* "I don't remember the eyes" is recorded as an explicit unknown, not a negative.
* Mark locations use the *subject's* left/right, as a witness would describe them.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from ..catalog import TRAIT_KEYS
from ..schemas import Mark, Profile, TraitValue

W = r"[a-z'-]+"  # a single word
GAP = rf"(?:[ ,-]+(?!and\b|with\b|eyes?\b|skin\b|beard\b|nose\b){W}){{0,2}}"  # up to 2 filler adjectives


def _before(adj: str, noun: str) -> str:
    """adjective … noun, allowing up to two other adjectives in between."""
    return rf"\b(?:{adj})\b{GAP}[ ,-]+(?:{noun})\b"


def _after(noun: str, adj: str) -> str:
    """noun was/is … adjective."""
    return rf"\b(?:{noun})\s+(?:was|were|is|are|looked|appeared|seemed)\s+(?:{W}\s+){{0,2}}?(?:{adj})\b"


def _either(adj: str, noun: str) -> list[str]:
    return [_before(adj, noun), _after(noun, adj)]


HAIR = r"(?<!facial )(?<!body )(?<!chest )hair|haircut|curls|locks"
BROWS = r"eyebrows?|brows?"
EYES = r"eyes?"
NOSE = r"nose"
LIPS = r"lips|mouth"
FACE = r"face|faced|head"
SKIN = r"skin|complexion|skinned"

# trait -> list of (value, [regex, ...]); first listed value wins only when
# values are compatible (see COMPATIBLE).
PATTERNS: dict[str, list[tuple[str, list[str]]]] = {
    "presentation": [
        ("masculine", [r"\b(?:man|male|guy|gentleman|boy|men)\b"]),
        ("feminine", [r"\b(?:woman|female|lady|girl|women)\b"]),
    ],
    "hair_color": [
        ("black", _either(r"jet[- ]black|black", HAIR) + [r"\bblack[- ]haired\b"]),
        ("brown", _either(r"dark[- ]brown|brown|brunette|chestnut", HAIR) + [r"\bbrunette\b", r"\bbrown[- ]haired\b"]),
        ("red", _either(r"red|ginger|auburn", HAIR) + [r"\bredhead\b", r"\bginger\b"]),
        ("blonde", _either(r"blonde?|fair|golden|light[- ]blonde?", HAIR) + [r"\bblonde?\b"]),
        ("gray", _either(r"gr[ae]y|graying|greying|silver|salt[- ]and[- ]pepper", HAIR) + [r"\bgr[ae]y[- ]haired\b"]),
        ("white", _either(r"white", HAIR) + [r"\bwhite[- ]haired\b"]),
        ("light", _either(r"light|light[- ]brown", HAIR)),
        ("dark", _either(r"dark", HAIR) + [r"\bdark[- ]haired\b"]),
    ],
    "hair_length": [
        ("bald", [r"\bbald\b(?!ing)", r"\bno hair\b"]),
        ("shaved", [r"\bshaved?\s+(?:head|hair)\b", r"\bbuzz[- ]?cut\b", r"\bhead was shaved\b", r"\bskinhead\b"]),
        ("short", _either(r"short|cropped|close[- ]cropped", HAIR) + [r"\bcrew[- ]?cut\b"]),
        ("medium", _either(r"medium[- ]length|medium|chin[- ]length|shoulder[- ]length", HAIR)),
        ("long", _either(r"long", HAIR) + [r"\bponytail\b", r"\bhair\s+(?:down\s+)?(?:to|past)\s+(?:his|her|their|the)\s+shoulders\b"]),
    ],
    "hair_style": [
        ("curly", _either(r"curly|frizzy|kinky|coily", HAIR) + [r"\bcurls\b", r"\bringlets\b", r"\bafro\b"]),
        ("wavy", _either(r"wavy", HAIR) + [r"\bwavy\b"]),
        ("straight", _either(r"straight|flat|sleek", HAIR)),
        ("spiky", [r"\bspik(?:y|ed)\b"]),
        ("slicked_back", [r"\b(?:slicked|greased|gelled|combed)[- ]back\b"]),
        ("side_part", [r"\bside[- ]part(?:ed)?\b", r"\bparted (?:on|to) the (?:left|right|side)\b", r"\bcombed to the side\b"]),
    ],
    "hairline": [
        ("receding", [r"\breceding\b(?:[ -]+\w+){0,1}[ -]+hairline\b", r"\bhairline\s+(?:was\s+|is\s+)?receding\b", r"\bbalding\b", r"\bthinning (?:on top|hair)\b"]),
        ("widows_peak", [r"\bwidow'?s[- ]peak\b"]),
        ("high", [r"\bhigh hairline\b", r"\b(?:high|big|large|tall) forehead\b"]),
        ("low", [r"\blow hairline\b", r"\b(?:low|small|narrow) forehead\b"]),
    ],
    "face_shape": [
        ("oval", _either(r"oval", FACE)),
        ("round", _either(r"round|rounded|chubby|full", FACE) + [r"\bround[- ]faced\b"]),
        ("square", _either(r"square|boxy", FACE)),
        ("long", _either(r"long|elongated|narrow|thin|gaunt", FACE)),
        ("heart", _either(r"heart[- ]shaped|heart", FACE)),
        ("diamond", _either(r"diamond[- ]shaped|diamond", FACE)),
        ("triangular", _either(r"triangular|triangle", FACE)),
    ],
    "jawline": [
        ("angular", _either(r"square|strong|chiseled|chiselled|angular|sharp|defined", r"jaw|jawline")),
        ("wide", _either(r"wide|broad|heavy", r"jaw|jawline")),
        ("narrow", _either(r"narrow|slim|thin|weak|soft", r"jaw|jawline")),
    ],
    "chin": [
        ("cleft", [r"\bcleft(?:ed)? chin\b", r"\bchin dimple\b", r"\bdimpled? chin\b"]),
        ("receding", _either(r"receding|weak", r"chin")),
        ("prominent", _either(r"prominent|jutting|strong|big|large", r"chin")),
        ("pointed", _either(r"pointed|pointy|sharp", r"chin")),
        ("square", _either(r"square", r"chin")),
        ("rounded", _either(r"round|rounded|soft", r"chin")),
    ],
    "eyebrow_thickness": [
        ("bushy", _either(r"bushy|very thick|shaggy", BROWS)),
        ("thick", _either(r"thick|heavy|dark thick|full", BROWS)),
        ("thin", _either(r"thin|sparse|light|pencil[- ]thin|plucked", BROWS)),
        ("medium", _either(r"medium|average|normal", BROWS)),
    ],
    "eyebrow_shape": [
        ("unibrow", [r"\b(?:uni|mono)[- ]?brow\b", r"\b(?:joined|connected|meeting) (?:eye)?brows\b", r"\b(?:eye)?brows (?:that )?(?:met|meet|joined)\b"]),
        ("arched", _either(r"arched|high[- ]arched", BROWS)),
        ("angled", _either(r"angled|angular|sharp|pointed", BROWS)),
        ("curved", _either(r"curved|rounded", BROWS)),
        ("straight", _either(r"straight|flat", BROWS)),
    ],
    "eye_shape": [
        ("almond", _either(r"almond[- ]shaped|almond", EYES)),
        ("round", _either(r"round|big round", EYES)),
        ("narrow", _either(r"narrow|squinty|small|squinting", EYES)),
        ("hooded", _either(r"hooded|heavy[- ]lidded", EYES)),
        ("downturned", _either(r"downturned|droopy|drooping|sad", EYES)),
        ("upturned", _either(r"upturned|cat[- ]like", EYES)),
        ("deep_set", _either(r"deep[- ]set|sunken|deep", EYES)),
    ],
    "eye_spacing": [
        ("close", [r"\bclose[- ]set\b", r"\beyes\s+(?:were\s+|are\s+)?(?:set\s+)?close together\b", r"\bclose together\b"]),
        ("wide", [r"\bwide[- ]set\b", r"\beyes\s+(?:were\s+|are\s+)?(?:set\s+)?(?:far|wide) apart\b", r"\bfar apart\b"]),
    ],
    "eye_color": [
        ("blue", _either(r"blue|pale blue|light blue", EYES) + [r"\bblue[- ]eyed\b"]),
        ("green", _either(r"green", EYES) + [r"\bgreen[- ]eyed\b"]),
        ("hazel", _either(r"hazel", EYES)),
        ("gray", _either(r"gr[ae]y", EYES)),
        ("brown", _either(r"brown|dark brown", EYES) + [r"\bbrown[- ]eyed\b"]),
        ("dark", _either(r"dark|black", EYES) + [r"\bdark[- ]eyed\b"]),
        ("light", _either(r"light|pale", EYES)),
    ],
    "eyewear": [
        ("none", [r"\bno (?:glasses|spectacles|eyewear)\b", r"\bwithout (?:any )?(?:glasses|spectacles)\b",
                  r"\b(?:not|wasn'?t|isn'?t|never) wearing (?:any )?(?:glasses|spectacles|eyewear)\b"]),
        ("sunglasses", [r"\bsunglasses\b", r"\bshades\b", r"\bsun[- ]glasses\b"]),
        ("round_glasses", [r"\b(?:round|circular)(?:[ -]+\w+){0,1}[ -]+(?:glasses|spectacles|frames)\b"]),
        ("rectangular_glasses", [r"\b(?:rectangular|square|narrow|thick[- ]rimmed|black[- ]rimmed)(?:[ -]+\w+){0,1}[ -]+(?:glasses|spectacles|frames)\b"]),
        ("glasses", [r"(?<!sun)\b(?:glasses|spectacles|eyeglasses)\b"]),
    ],
    "nose_shape": [
        ("hooked", _either(r"hooked|aquiline|roman|beaked|curved", NOSE)),
        ("crooked", _either(r"crooked|broken|bent|twisted", NOSE)),
        ("button", _either(r"button|snub|small|little|upturned|turned[- ]up", NOSE)),
        ("broad", _either(r"broad|big|large|bulbous|fat", NOSE)),
        ("wide", _either(r"wide|flared", NOSE)),
        ("narrow", _either(r"narrow|thin|slim|slender", NOSE)),
        ("pointed", _either(r"pointed|pointy|sharp", NOSE)),
        ("flat", _either(r"flat|flattened", NOSE)),
        ("straight", _either(r"straight", NOSE)),
    ],
    "mouth_shape": [
        ("full", _either(r"full|thick|plump|big", r"lips")),
        ("thin", _either(r"thin", r"lips") + [r"\bthin[- ]lipped\b"]),
        ("wide", _either(r"wide|big|large", r"mouth")),
        ("small", _either(r"small|little", r"mouth")),
        ("downturned", _either(r"downturned|frowning", r"mouth") + [r"\bfrown(?:ed|ing)?\b"]),
    ],
    "facial_hair": [
        ("none", [r"\bclean[- ]shaven\b", r"\bno (?:beard|facial hair|mustache|moustache)\b", r"\bbeardless\b", r"\bwithout (?:a )?(?:beard|facial hair)\b"]),
        ("full_beard", [r"\b(?:full|thick|bushy|big|long|heavy|short|trimmed|dark|grey|gray)\s+beard\b", r"\bbearded\b", r"(?<!no )\bbeard\b"]),
        ("goatee", [r"\bgoatee\b", r"\bchin beard\b", r"\bvan dyke\b"]),
        ("mustache", [r"\bmoustache\b", r"\bmustache\b", r"\bmustached\b"]),
        ("stubble", [r"\bstubble\b", r"\bstubbly\b", r"\bfive[- ]o'?clock shadow\b", r"\bunshaven\b", r"\bscruff(?:y)?\b", r"\blight facial hair\b"]),
    ],
    "ears": [
        ("protruding", [r"\b(?:protruding|sticking[- ]out|jug|prominent)(?:[ -]+\w+){0,1}[ -]+ears\b", r"\bears\s+(?:that\s+)?(?:stuck|stick|stuck out|sticking) out\b"]),
        ("large", _either(r"large|big", r"ears")),
        ("small", _either(r"small|tiny|little", r"ears")),
    ],
    "skin_tone": [
        ("very_light", _either(r"very pale|very fair|pale", SKIN) + [r"\bpale\b(?=[ -]+(?:skin|complexion))"]),
        ("light", _either(r"fair|light|white", SKIN) + [r"\blight[- ]skinned\b"]),
        ("olive", _either(r"olive", SKIN)),
        ("tan", _either(r"tan|tanned|bronzed", SKIN)),
        ("medium", _either(r"medium", SKIN)),
        ("brown", _either(r"brown", SKIN) + [r"\bbrown[- ]skinned\b"]),
        ("dark", _either(r"dark|black", SKIN) + [r"\bdark[- ]skinned\b"]),
    ],
}

# Pairs of values that are refinements of each other, not conflicts.
# Maps a group of values to the preferred (most specific) value.
COMPATIBLE: dict[str, list[tuple[set[str], str]]] = {
    "hair_color": [({"dark", "black"}, "black"), ({"dark", "brown"}, "brown"), ({"light", "blonde"}, "blonde"),
                   ({"light", "gray"}, "gray"), ({"light", "white"}, "white"), ({"gray", "white"}, "gray")],
    "facial_hair": [({"mustache", "goatee"}, "goatee"), ({"stubble", "mustache"}, "mustache"),
                    ({"stubble", "goatee"}, "goatee"), ({"stubble", "full_beard"}, "full_beard"),
                    ({"mustache", "full_beard"}, "full_beard"), ({"goatee", "full_beard"}, "full_beard")],
    "eyewear": [({"glasses", "round_glasses"}, "round_glasses"), ({"glasses", "rectangular_glasses"}, "rectangular_glasses"),
                ({"glasses", "sunglasses"}, "sunglasses")],
    "hair_length": [({"bald", "shaved"}, "shaved")],
    "eye_color": [({"dark", "brown"}, "brown")],
    "nose_shape": [({"broad", "wide"}, "broad"), ({"narrow", "pointed"}, "pointed"), ({"straight", "narrow"}, "narrow")],
    "mouth_shape": [({"full", "wide"}, "full")],
    "eyebrow_thickness": [({"thick", "bushy"}, "bushy")],
    "skin_tone": [({"very_light", "light"}, "very_light")],
    "hairline": [({"receding", "high"}, "receding")],
}

HEDGES = re.compile(
    r"\b(?:maybe|possibly|probably|perhaps|i think|i believe|might|may have|not sure|not certain|"
    r"kind of|sort of|could have|could be|looked like|seemed|i guess|unsure|-ish)\b|ish\b"
)

UNKNOWN_SUBJECTS = {
    "eye_color": r"eye colou?r|colou?r of (?:his|her|their|the) eyes",
    "eye_shape": r"(?:his|her|their|the) eyes",
    "hair_color": r"hair colou?r|colou?r of (?:his|her|their|the) hair",
    "nose_shape": r"(?:his|her|their|the) nose",
    "mouth_shape": r"(?:his|her|their|the) (?:mouth|lips)",
    "ears": r"(?:his|her|their|the) ears",
    "facial_hair": r"(?:whether|if) (?:he|she|they) had (?:a )?(?:beard|facial hair)",
    "chin": r"(?:his|her|their|the) chin",
}
UNKNOWN_VERB = r"(?:don'?t|do not|didn'?t|did not|can'?t|cannot|couldn'?t|could not|wasn'?t able to|not sure (?:about|of))\s+(?:really\s+)?(?:remember|recall|see|tell|make out|notice|say)?\s*"

# --- age --------------------------------------------------------------------
DECADES = {"teens": 15, "twenties": 25, "thirties": 35, "forties": 45, "fifties": 55,
           "sixties": 65, "seventies": 75, "eighties": 85}
DECADE_OFFSET = {"early": -3, "mid": 0, "late": 3}


def _age_bucket(age: int) -> str:
    if age < 13:
        return "child"
    if age < 18:
        return "teen"
    if age < 30:
        return "young_adult"
    if age < 45:
        return "adult"
    if age < 60:
        return "middle_aged"
    return "senior"


def _find_ages(clause: str) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for m in re.finditer(r"\b(\d{1,2})\s*(?:-|to|–)\s*(\d{1,2})\s*(?:years?|yrs?)?(?:[- ]old)?\b", clause):
        a, b = int(m.group(1)), int(m.group(2))
        if 1 < a < 100 and 1 < b < 100 and b >= a:
            found.append((_age_bucket((a + b) // 2), m.group(0)))
    if not found:
        for m in re.finditer(r"\b(\d{1,2})\s*(?:years?|yrs?)(?:[- ]old)?\b|\b(?:aged?|about|around|approximately|roughly|maybe|age)\s+(\d{1,2})\b|\b(\d{1,2})[- ]?ish\b", clause):
            n = int(next(g for g in m.groups() if g))
            if 1 < n < 100:
                found.append((_age_bucket(n), m.group(0)))
    for m in re.finditer(r"\b(?:(early|mid|late)[- ])?(teens|twenties|thirties|forties|fifties|sixties|seventies|eighties)\b", clause):
        n = DECADES[m.group(2)] + DECADE_OFFSET.get(m.group(1) or "mid", 0)
        found.append((_age_bucket(n), m.group(0)))
    for m in re.finditer(r"\b(?:(early|mid|late)[- ])?(\d)0'?s\b", clause):
        n = int(m.group(2)) * 10 + 5 + DECADE_OFFSET.get(m.group(1) or "mid", 0)
        if 10 <= n < 100:
            found.append((_age_bucket(n), m.group(0)))
    words = [
        ("senior", r"\b(?:elderly|old man|old woman|old lady|older man|older woman|pensioner|senior citizen)\b"),
        ("middle_aged", r"\bmiddle[- ]aged\b"),
        ("young_adult", r"\b(?:young man|young woman|young adult|young guy|young lady|college[- ]aged?)\b"),
        ("teen", r"\b(?:teenager|teenage|teen|adolescent)\b"),
        ("child", r"\b(?:child|kid|little boy|little girl|toddler)\b"),
    ]
    for value, rx in words:
        for m in re.finditer(rx, clause):
            found.append((value, m.group(0)))
    return found


# --- distinctive marks -----------------------------------------------------
MARK_TYPE_RX = (
    r"(?P<type>scars?|moles?|beauty (?:mark|spot)|birth ?marks?|tattoos?|piercings?|nose ring|lip ring|"
    r"eyebrow ring|earrings?|freckles|freckled)"
)
MARK_SIZE_RX = r"(?:(?P<size>small|tiny|little|faint|thin|short|large|big|long|prominent|deep|noticeable)\s+)?"
PART_RX = (
    r"(?:(?P<side>left|right)\s+)?(?P<part>cheek(?:bone)?|eyebrow|brow|eye|forehead|chin|jaw(?:line)?|nose|"
    r"upper lip|lower lip|lip|ear|neck|temple)"
)
MARK_TYPE_MAP = {
    "scar": "scar", "scars": "scar", "mole": "mole", "moles": "mole", "beauty mark": "mole", "beauty spot": "mole",
    "birthmark": "birthmark", "birth mark": "birthmark", "birthmarks": "birthmark", "birth marks": "birthmark",
    "tattoo": "tattoo", "tattoos": "tattoo", "piercing": "piercing", "piercings": "piercing",
    "nose ring": "piercing", "lip ring": "piercing", "eyebrow ring": "piercing", "earring": "piercing",
    "earrings": "piercing", "freckles": "freckles", "freckled": "freckles",
}
PAIRED = {"cheek": "cheek", "cheekbone": "cheek", "eyebrow": "eyebrow", "brow": "eyebrow", "eye": "eye",
          "jaw": "jaw", "jawline": "jaw", "ear": "ear", "temple": "eyebrow"}
SINGLE = {"forehead": "forehead", "chin": "chin", "nose": "nose", "upper lip": "upper_lip",
          "lower lip": "lower_lip", "lip": "upper_lip", "neck": "neck"}
SIZE_MAP = {"tiny": "small", "little": "small", "faint": "small", "thin": "small", "short": "small", "small": "small",
            "large": "large", "big": "large", "long": "large", "prominent": "medium", "deep": "medium", "noticeable": "medium"}
DEFAULT_MARK_LOCATION = {"freckles": "nose", "piercing": "left_ear"}


def _mark_location(part: str | None, side: str | None, mtype: str, raw_type: str) -> tuple[str | None, bool]:
    if raw_type == "nose ring":
        return "nose", True
    if raw_type == "lip ring":
        return "lower_lip", True
    if raw_type == "eyebrow ring":
        part = part or "eyebrow"
    if raw_type.startswith("earring"):
        part = part or "ear"
    if part is None:
        default = DEFAULT_MARK_LOCATION.get(mtype)
        return (default, mtype != "piercing") if default else (None, False)
    if part in SINGLE:
        return SINGLE[part], True
    base = PAIRED.get(part)
    if base is None:
        return None, False
    if side:
        return f"{side}_{base}", True
    return f"left_{base}", False  # side unknown: drawn on the subject's left and flagged


@dataclass
class _Hit:
    value: str
    evidence: str
    uncertain: bool


@dataclass
class Extraction:
    profile: Profile
    conflicts: list[dict] = field(default_factory=list)
    unknown_traits: list[str] = field(default_factory=list)
    explicit_unknowns: list[str] = field(default_factory=list)
    uncertain_traits: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "profile": self.profile.model_dump(),
            "conflicts": self.conflicts,
            "unknown_traits": self.unknown_traits,
            "explicit_unknowns": self.explicit_unknowns,
            "uncertain_traits": self.uncertain_traits,
            "warnings": self.warnings,
            "recognized_count": sum(1 for t in self.profile.traits.values() if t.value is not None or t.alternatives)
            + len(self.profile.marks),
        }


def _normalize(text: str) -> str:
    text = text.lower().replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    return re.sub(r"\s+", " ", text)


def _clauses(text: str) -> list[str]:
    parts = re.split(r"[.;!?\n]+|,\s*(?:but|although|though|however)\b|\bbut\b", text)
    return [p.strip() for p in parts if p and p.strip()]


NEGATION_BEFORE = re.compile(
    r"\b(?:no|without|never|not wearing|wasn'?t wearing|isn'?t wearing|didn'?t have|did not have|"
    r"doesn'?t have|does not have|not)\s+(?:(?:a|an|any|the|his|her|their)\s+)?(?:[a-z'-]+\s+){0,1}$"
)


def _negated(clause: str, m: re.Match) -> bool:
    """True when a positive mention is directly negated ("no glasses", "not wearing a cap")."""
    prefix = clause[max(0, m.start() - 32): m.start()]
    if re.search(r"\bnot (?:sure|certain)\b", prefix):
        return False
    return bool(NEGATION_BEFORE.search(prefix))


def _hedged(clause: str, m: re.Match) -> bool:
    """A hedge applies to the comma-separated phrase containing the match,
    plus a short trailing aside such as ", I think"."""
    start = clause.rfind(",", 0, m.start()) + 1
    end = clause.find(",", m.end())
    end = len(clause) if end == -1 else end
    window = clause[start:end]
    if end < len(clause):
        nxt_end = clause.find(",", end + 1)
        nxt = clause[end + 1: len(clause) if nxt_end == -1 else nxt_end]
        if len(nxt.split()) <= 4:
            window += "," + nxt
    return bool(HEDGES.search(window))


def _snippet(clause: str, m: re.Match) -> str:
    start = max(0, m.start() - 12)
    end = min(len(clause), m.end() + 12)
    s = clause[start:end].strip()
    return s[:120]


def _resolve(key: str, hits: list[_Hit]) -> tuple[str | None, list[str]]:
    values = []
    for h in hits:
        if h.value not in values:
            values.append(h.value)
    if len(values) == 1:
        return values[0], []
    # collapse compatible refinements (e.g. "dark" + "black" -> "black")
    remaining = set(values)
    changed = True
    while changed and len(remaining) > 1:
        changed = False
        for group, preferred in COMPATIBLE.get(key, []):
            if group <= remaining:
                remaining -= group
                remaining.add(preferred)
                changed = True
                break
    if len(remaining) == 1:
        return next(iter(remaining)), []
    return None, [v for v in values if v in remaining]


def extract_traits(description: str) -> Extraction:
    text = _normalize(description)
    clauses = _clauses(text)
    hits: dict[str, list[_Hit]] = {k: [] for k in TRAIT_KEYS}
    marks: list[Mark] = []
    explicit_unknowns: list[str] = []
    warnings: list[str] = []

    for clause in clauses:

        # explicit "I don't remember …" statements
        for key, subject in UNKNOWN_SUBJECTS.items():
            if re.search(UNKNOWN_VERB + rf"(?:\w+\s+){{0,2}}?(?:{subject})", clause):
                if key not in explicit_unknowns:
                    explicit_unknowns.append(key)

        for key, options in PATTERNS.items():
            if key == "presentation":
                continue
            for value, regexes in options:
                for rx in regexes:
                    for m in re.finditer(rx, clause):
                        if value != "none" and _negated(clause, m):
                            continue
                        hits[key].append(_Hit(value, _snippet(clause, m), _hedged(clause, m)))
                        break

        for value, ev in _find_ages(clause):
            idx = clause.find(ev)
            window_match = re.search(re.escape(ev), clause) if idx >= 0 else None
            hits["age_range"].append(_Hit(value, ev, _hedged(clause, window_match) if window_match else False))

        for m in re.finditer(rf"{MARK_SIZE_RX}{MARK_TYPE_RX}", clause):
            raw_type = m.group("type")
            mtype = MARK_TYPE_MAP.get(raw_type) or MARK_TYPE_MAP.get(raw_type.rstrip("s"))
            if not mtype:
                continue
            window = clause[m.end(): m.end() + 45]
            before = clause[max(0, m.start() - 35): m.start()]
            loc = re.search(rf"(?:on|near|above|below|under|across|over|in|at|by)\s+(?:(?:his|her|their|the|its)\s+)?{PART_RX}", window)
            if not loc:
                loc = re.search(rf"{PART_RX}\s*$", before.strip())
            if not loc:
                loc = re.search(PART_RX, window)
            part = loc.group("part") if loc else None
            side = loc.group("side") if loc else None
            location, side_specified = _mark_location(part, side, mtype, raw_type)
            if location is None:
                warnings.append(f"A {mtype} was mentioned without a location. Add its position in the profile editor.")
                location, side_specified = "left_cheek", False
            size = SIZE_MAP.get(m.group("size") or "", "small")
            if any(mk.type == mtype and mk.location == location for mk in marks):
                continue
            marks.append(Mark(
                id=f"m{len(marks) + 1}", type=mtype, location=location, size=size,
                side_specified=side_specified, source="extracted", evidence=_snippet(clause, m),
            ))

    # presentation: nouns win over pronouns (a pronoun may refer to the witness)
    for clause in clauses:
        for value, regexes in PATTERNS["presentation"]:
            for rx in regexes:
                m = re.search(rx, clause)
                if m:
                    hits["presentation"].append(_Hit(value, _snippet(clause, m), _hedged(clause, m)))
    if not hits["presentation"]:
        for clause in clauses:
            m_he = re.search(r"\b(?:he|his|him)\b", clause)
            m_she = re.search(r"\b(?:she|her|hers)\b", clause)
            if m_he:
                hits["presentation"].append(_Hit("masculine", _snippet(clause, m_he), True))
            if m_she:
                hits["presentation"].append(_Hit("feminine", _snippet(clause, m_she), True))

    traits: dict[str, TraitValue] = {}
    conflicts: list[dict] = []
    uncertain: list[str] = []
    for key in TRAIT_KEYS:
        key_hits = hits.get(key, [])
        if not key_hits:
            traits[key] = TraitValue(value=None, source="unknown")
            continue
        value, alternatives = _resolve(key, key_hits)
        evidence = "; ".join(dict.fromkeys(h.evidence for h in key_hits))[:300]
        is_uncertain = all(h.uncertain for h in key_hits)
        if alternatives:
            traits[key] = TraitValue(value=None, source="extracted", evidence=evidence,
                                     certainty="uncertain" if is_uncertain else "stated", alternatives=alternatives)
            conflicts.append({"key": key, "values": alternatives, "evidence": evidence})
        else:
            traits[key] = TraitValue(value=value, source="extracted", evidence=evidence,
                                     certainty="uncertain" if is_uncertain else "stated")
        if is_uncertain:
            uncertain.append(key)

    # Explicit unknowns override weak inferences only when nothing was stated.
    for key in explicit_unknowns:
        if traits[key].value is None and not traits[key].alternatives:
            traits[key] = TraitValue(value=None, source="unknown", evidence="Witness stated they do not remember.")

    profile = Profile(traits=traits, marks=marks)
    unknown = [k for k, t in traits.items() if t.value is None and not t.alternatives]
    if not any(t.value for t in traits.values()) and not marks:
        warnings.append("No facial characteristics were recognised. Try the guided questions, or describe specific features.")
    return Extraction(
        profile=profile, conflicts=conflicts, unknown_traits=unknown,
        explicit_unknowns=explicit_unknowns, uncertain_traits=uncertain, warnings=warnings,
    )
