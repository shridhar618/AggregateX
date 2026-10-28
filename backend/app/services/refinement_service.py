"""Deterministic natural-language refinement.

"Make the eyebrows thicker", "add a small scar on the left cheek",
"change the face shape to oval", "remove the glasses" ...

The service only *proposes* changes. The operator confirms them, and only then
is the profile updated and a new revision rendered.
"""

from __future__ import annotations

import copy
import re
import secrets

from ..catalog import ADJUSTMENTS, ORDINAL, TRAIT_BY_KEY, option_label
from ..schemas import Mark, Profile, TraitValue
from .trait_extractor import extract_traits

ADJ_LABEL = {a["key"]: a["label"] for a in ADJUSTMENTS}
STEP = 0.35

# (regex, kind, key, delta)  kind: "ordinal" (trait step) | "adjust" (slider delta)
COMPARATIVES: list[tuple[str, str, str, float]] = [
    (r"\b(?:thicker|bushier|heavier|fuller|denser)\s+(?:eye)?brows?\b|\b(?:eye)?brows?\b.*\b(?:thicker|bushier|heavier|fuller)\b", "ordinal", "eyebrow_thickness", 1),
    (r"\b(?:thinner|sparser|lighter|finer)\s+(?:eye)?brows?\b|\b(?:eye)?brows?\b.*\b(?:thinner|sparser|finer)\b", "ordinal", "eyebrow_thickness", -1),
    (r"\b(?:raise|lift)\b.*\b(?:eye)?brows?\b|\b(?:eye)?brows?\b.*\b(?:higher|raised)\b|\bhigher\s+(?:eye)?brows?\b", "adjust", "eyebrow_height", STEP),
    (r"\b(?:lower)\s+(?:the\s+)?(?:eye)?brows?\b|\b(?:eye)?brows?\b.*\b(?:lower)\b", "adjust", "eyebrow_height", -STEP),
    (r"\b(?:narrower|thinner|slimmer|smaller|weaker|softer)\s+jaw(?:line)?\b|\bjaw(?:line)?\b.*\b(?:narrower|thinner|slimmer|smaller)\b", "adjust", "jaw_width", -STEP),
    (r"\b(?:wider|broader|stronger|bigger|heavier)\s+jaw(?:line)?\b|\bjaw(?:line)?\b.*\b(?:wider|broader|stronger|bigger)\b", "adjust", "jaw_width", STEP),
    (r"\b(?:wider|broader|fuller)\s+face\b|\bface\b.*\b(?:wider|broader)\b", "adjust", "face_width", STEP),
    (r"\b(?:narrower|thinner|slimmer)\s+face\b|\bface\b.*\b(?:narrower|thinner|slimmer)\b", "adjust", "face_width", -STEP),
    (r"\blonger\s+face\b|\bface\b.*\blonger\b", "adjust", "face_length", STEP),
    (r"\bshorter\s+face\b|\bface\b.*\bshorter\b", "adjust", "face_length", -STEP),
    (r"\b(?:wider|broader|bigger|larger)\s+nose\b|\bnose\b.*\b(?:wider|broader|bigger|larger)\b", "adjust", "nose_width", STEP),
    (r"\b(?:narrower|thinner|slimmer|smaller)\s+nose\b|\bnose\b.*\b(?:narrower|thinner|slimmer|smaller)\b", "adjust", "nose_width", -STEP),
    (r"\blonger\s+nose\b|\bnose\b.*\blonger\b", "adjust", "nose_length", STEP),
    (r"\bshorter\s+nose\b|\bnose\b.*\bshorter\b", "adjust", "nose_length", -STEP),
    (r"\b(?:wider|bigger|larger)\s+mouth\b|\bmouth\b.*\b(?:wider|bigger|larger)\b", "adjust", "mouth_width", STEP),
    (r"\b(?:narrower|smaller)\s+mouth\b|\bmouth\b.*\b(?:narrower|smaller)\b", "adjust", "mouth_width", -STEP),
    (r"\b(?:fuller|thicker|bigger|plumper)\s+lips\b|\blips\b.*\b(?:fuller|thicker|bigger|plumper)\b", "adjust", "lip_fullness", STEP),
    (r"\bthinner\s+lips\b|\blips\b.*\bthinner\b", "adjust", "lip_fullness", -STEP),
    (r"\beyes\b.*\b(?:closer|nearer)\b|\bcloser[- ]set\b", "adjust", "eye_spacing", -STEP),
    (r"\beyes\b.*\b(?:further|farther|wider)\s+apart\b|\bwider[- ]set\b", "adjust", "eye_spacing", STEP),
    (r"\b(?:bigger|larger|rounder)\s+eyes\b|\beyes\b.*\b(?:bigger|larger)\b", "adjust", "eye_size", STEP),
    (r"\bsmaller\s+eyes\b|\beyes\b.*\bsmaller\b", "adjust", "eye_size", -STEP),
    (r"\b(?:move|place|set)\b.*\beyes\b.*\b(?:up|higher)\b|\beyes\b.*\bhigher\b", "adjust", "eye_height", -STEP),
    (r"\b(?:move|place|set)\b.*\beyes\b.*\b(?:down|lower)\b|\beyes\b.*\blower\b", "adjust", "eye_height", STEP),
    (r"\blonger\s+chin\b|\bchin\b.*\blonger\b", "adjust", "chin_length", STEP),
    (r"\bshorter\s+chin\b|\bchin\b.*\bshorter\b", "adjust", "chin_length", -STEP),
    (r"\b(?:bigger|larger)\s+ears\b|\bears\b.*\b(?:bigger|larger)\b", "adjust", "ear_size", STEP),
    (r"\bsmaller\s+ears\b|\bears\b.*\bsmaller\b", "adjust", "ear_size", -STEP),
    (r"\blonger\s+hair\b|\bhair\b.*\blonger\b", "ordinal", "hair_length", 1),
    (r"\bshorter\s+hair\b|\bhair\b.*\bshorter\b", "ordinal", "hair_length", -1),
    (r"\b(?:more|fuller|thicker|bigger)\s+(?:volume|hair)\b|\bhair\b.*\b(?:fuller|thicker|bigger|more volume)\b", "adjust", "hair_volume", STEP),
    (r"\b(?:flatter|less volume)\b", "adjust", "hair_volume", -STEP),
]

REMOVALS = {
    r"scars?": ("mark", "scar"), r"moles?": ("mark", "mole"), r"tattoos?": ("mark", "tattoo"),
    r"birth ?marks?": ("mark", "birthmark"), r"piercings?|earrings?|nose ring|lip ring": ("mark", "piercing"),
    r"freckles": ("mark", "freckles"),
    r"glasses|spectacles|sunglasses|eyewear": ("trait", "eyewear"),
    r"beard|mustache|moustache|goatee|stubble|facial hair": ("trait", "facial_hair"),
}
REMOVE_VERB = r"\b(?:remove|delete|erase|get rid of|take (?:off|away)|drop)\b"

NOUN_TO_PHRASE = {
    "face shape": "face", "face": "face", "head": "face", "hairline": "hairline", "hair": "hair",
    "hair style": "hair", "hairstyle": "hair", "eyebrows": "eyebrows", "brows": "eyebrows", "eyebrow": "eyebrows",
    "eyes": "eyes", "eye shape": "eyes", "nose": "nose", "lips": "lips", "mouth": "mouth", "chin": "chin",
    "jaw": "jaw", "jawline": "jaw", "ears": "ears", "beard": "beard", "facial hair": "beard",
    "glasses": "glasses", "skin": "skin", "complexion": "skin",
}
SET_PATTERNS = [
    r"\b(?:make|turn)\s+(?:the\s+|his\s+|her\s+|their\s+)?(?P<noun>[a-z ]+?)\s+(?:look\s+)?(?:more\s+)?(?P<val>[a-z'\- ]+)$",
    r"\b(?:change|set|switch|update)\s+(?:the\s+|his\s+|her\s+|their\s+)?(?P<noun>[a-z ]+?)\s+(?:to|into)\s+(?:be\s+)?(?:an?\s+)?(?P<val>[a-z'\- ]+)$",
    r"\b(?:the\s+|his\s+|her\s+|their\s+)?(?P<noun>[a-z ]+?)\s+(?:should be|is|was|must be)\s+(?:more\s+)?(?:an?\s+)?(?P<val>[a-z'\- ]+)$",
]


def _parts(text: str) -> list[str]:
    text = text.lower().replace("’", "'")
    parts = re.split(r"[.;\n]+|,|\band then\b|\bthen\b|\balso\b|\band\b(?=\s+(?:make|add|remove|change|set|give|put|move|raise|lower|delete))", text)
    return [p.strip() for p in parts if p and p.strip()]


def _clamp(v: float) -> float:
    return max(-1.0, min(1.0, round(v, 3)))


def _trait_change(key: str, current: TraitValue | None, new_value: str, reason: str) -> dict | None:
    old = current.value if current else None
    if old == new_value and not (current and current.alternatives):
        return None
    return {
        "kind": "trait", "key": key, "label": TRAIT_BY_KEY[key]["label"],
        "from": old, "to": new_value,
        "from_label": option_label(key, old), "to_label": option_label(key, new_value), "reason": reason,
    }


def parse_refinement(instruction: str, profile: Profile) -> dict:
    changes: list[dict] = []
    unrecognized: list[str] = []
    already: list[str] = []
    traits = profile.traits
    adjustments = dict(profile.adjustments)
    pending_adj: dict[str, float] = {}

    def add(change: dict | None):
        if change is None:
            return
        for i, c in enumerate(changes):
            if c["kind"] == change["kind"] and c.get("key") == change.get("key") and change["kind"] != "mark_add":
                changes[i] = change
                return
        changes.append(change)

    for part in _parts(instruction):
        before = len(changes)
        already_before = len(already)

        # 1) removals
        if re.search(REMOVE_VERB, part) or re.search(r"\bno (?:more )?(?:glasses|beard|mustache|moustache|scar|tattoo)\b", part):
            for rx, (kind, target) in REMOVALS.items():
                if re.search(rf"\b(?:{rx})\b", part):
                    if kind == "mark":
                        present = [m for m in profile.marks if m.type == target]
                        if present:
                            changes.append({"kind": "mark_remove", "key": target, "label": f"Remove {target}",
                                            "from": f"{len(present)} {target}(s)", "to": None,
                                            "from_label": f"{len(present)} × {target}", "to_label": "Removed",
                                            "reason": part})
                    else:
                        add(_trait_change(target, traits.get(target), "none", part))
            if len(changes) > before:
                continue

        # 2) comparatives -> ordinal steps or slider deltas
        for rx, kind, key, delta in COMPARATIVES:
            if re.search(rx, part):
                if kind == "ordinal":
                    scale = ORDINAL[key]
                    cur = traits.get(key)
                    base = (cur.value if cur and cur.value in scale else
                            {"eyebrow_thickness": "medium", "hair_length": "short"}.get(key, scale[len(scale) // 2]))
                    idx = max(0, min(len(scale) - 1, scale.index(base) + int(delta)))
                    if scale[idx] != base or (cur and cur.value is None):
                        add(_trait_change(key, cur, scale[idx], part))
                    else:
                        adj_key = key if key in ADJ_LABEL else None
                        if adj_key:
                            pending_adj[adj_key] = pending_adj.get(adj_key, adjustments.get(adj_key, 0.0)) + 0.3 * delta
                else:
                    pending_adj[key] = pending_adj.get(key, adjustments.get(key, 0.0)) + delta
                break

        # 3) "make/change/set the <noun> <value>" -> synthesize "<value> <noun>"
        synthetic = None
        for rx in SET_PATTERNS:
            m = re.search(rx, part)
            if m:
                noun = m.group("noun").strip()
                val = m.group("val").strip()
                noun_key = NOUN_TO_PHRASE.get(noun) or NOUN_TO_PHRASE.get(noun.split()[-1])
                if noun_key:
                    synthetic = f"{val} {noun_key}"
                break

        # 4) run the extractor on the instruction (and the synthetic phrase)
        for text in filter(None, [synthetic, part]):
            ext = extract_traits(text)
            for key, tv in ext.profile.traits.items():
                if key == "presentation":
                    continue
                if tv.value is not None:
                    change = _trait_change(key, traits.get(key), tv.value, part)
                    if change is None:
                        already.append(f"{TRAIT_BY_KEY[key]['label']} is already {option_label(key, tv.value).lower()}.")
                    add(change)
            if re.search(r"\b(?:add|put|give|draw|include|place)\b", part) or not profile.marks:
                for mk in ext.profile.marks:
                    if any(c["kind"] == "mark_add" and c["mark"]["type"] == mk.type and c["mark"]["location"] == mk.location for c in changes):
                        continue
                    if any(m.type == mk.type and m.location == mk.location for m in profile.marks):
                        already.append(f"A {mk.type} on the {mk.location.replace('_', ' ')} is already in the profile.")
                        continue
                    mark = mk.model_dump()
                    mark["source"] = "manual"
                    changes.append({"kind": "mark_add", "key": mk.type, "label": f"Add {mk.type}",
                                    "from": None, "to": mk.location, "from_label": "—",
                                    "to_label": f"{mk.size} {mk.type}, {mk.location.replace('_', ' ')}"
                                                + ("" if mk.side_specified else " (side not stated)"),
                                    "mark": mark, "reason": part})
            if len(changes) > before:
                break

        if len(changes) == before and len(already) == already_before and not any(re.search(rx, part) for rx, *_ in COMPARATIVES):
            unrecognized.append(part)

    for key, val in pending_adj.items():
        new = _clamp(val)
        old = adjustments.get(key, 0.0)
        if new != old:
            changes.append({"kind": "adjust", "key": key, "label": ADJ_LABEL[key], "from": old, "to": new,
                            "from_label": f"{old:+.2f}", "to_label": f"{new:+.2f}", "reason": "proportion"})
        elif abs(new) >= 1.0:
            unrecognized.append(f"{ADJ_LABEL[key]} is already at its limit")

    for i, c in enumerate(changes):
        c["id"] = f"c{i + 1}"
    return {"changes": changes, "unrecognized": unrecognized, "already": list(dict.fromkeys(already)),
            "message": None if changes or already else "No supported change was recognised. Try phrasing like “make the eyebrows thicker” or “add a scar on the left cheek”."}


def apply_changes(profile: Profile, changes: list[dict]) -> Profile:
    """Apply operator-confirmed changes. Every applied trait becomes ``manual``."""
    p = copy.deepcopy(profile)
    for c in changes:
        kind = c.get("kind")
        if kind == "trait":
            key, value = c["key"], c.get("to")
            if key not in TRAIT_BY_KEY or (value is not None and value not in TRAIT_BY_KEY[key]["options"]):
                raise ValueError(f"Invalid change for {key}")
            p.traits[key] = TraitValue(value=value, source="manual" if value else "unknown",
                                       evidence="Operator refinement")
        elif kind == "adjust":
            if c["key"] not in ADJ_LABEL:
                raise ValueError(f"Invalid adjustment {c['key']}")
            p.adjustments[c["key"]] = _clamp(float(c["to"]))
        elif kind == "mark_add":
            mark = Mark(**{**c["mark"], "id": f"m{secrets.token_hex(3)}"})
            p.marks.append(mark)
        elif kind == "mark_remove":
            p.marks = [m for m in p.marks if m.type != c["key"]]
    return Profile.model_validate(p.model_dump())
