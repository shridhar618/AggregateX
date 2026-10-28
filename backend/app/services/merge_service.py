"""Multi-witness comparison.

Each description is extracted independently. Traits are then classified as
shared, conflicting, single-source or unmentioned. Conflicts are NEVER resolved
automatically: the combined profile leaves them unknown with the alternatives
listed, and the operator must choose before applying the profile.

Agreement between witnesses is not proof of identity.
"""

from __future__ import annotations

from ..catalog import TRAIT_KEYS, TRAIT_BY_KEY, option_label
from ..schemas import Mark, Profile, TraitValue
from .trait_extractor import COMPATIBLE, extract_traits


def _collapse(key: str, values: set[str]) -> set[str]:
    remaining = set(values)
    changed = True
    while changed and len(remaining) > 1:
        changed = False
        for group, preferred in COMPATIBLE.get(key, []):
            if group <= remaining:
                remaining = (remaining - group) | {preferred}
                changed = True
                break
    return remaining


def merge_descriptions(descriptions: list[str]) -> dict:
    extractions = [extract_traits(d) for d in descriptions]
    rows = []
    combined: dict[str, TraitValue] = {}
    review: list[str] = []

    for key in TRAIT_KEYS:
        mentions = []
        for i, ex in enumerate(extractions):
            tv = ex.profile.traits[key]
            if tv.value is not None:
                mentions.append({"witness": i + 1, "value": tv.value, "label": option_label(key, tv.value),
                                 "certainty": tv.certainty, "evidence": tv.evidence})
            elif tv.alternatives:
                for alt in tv.alternatives:
                    mentions.append({"witness": i + 1, "value": alt, "label": option_label(key, alt),
                                     "certainty": "uncertain", "evidence": tv.evidence, "internal_conflict": True})
        witnesses = sorted({m["witness"] for m in mentions})
        distinct = _collapse(key, {m["value"] for m in mentions})
        internal = any(m.get("internal_conflict") for m in mentions)

        if not mentions:
            status = "unmentioned"
            combined[key] = TraitValue(value=None, source="unknown")
        elif len(distinct) > 1 or internal:
            status = "conflicting"
            alts = sorted(distinct)
            combined[key] = TraitValue(value=None, source="extracted", alternatives=alts,
                                       evidence="Witnesses disagree; operator review required.")
            review.append(key)
        elif len(witnesses) == 1:
            status = "single_source"
            value = next(iter(distinct))
            combined[key] = TraitValue(value=value, source="extracted",
                                       evidence=f"Mentioned by witness {witnesses[0]} only.",
                                       certainty="uncertain" if all(m["certainty"] == "uncertain" for m in mentions) else "stated")
        else:
            status = "shared"
            value = next(iter(distinct))
            combined[key] = TraitValue(value=value, source="extracted",
                                       evidence=f"Stated by witnesses {', '.join(map(str, witnesses))}.")
        rows.append({"key": key, "label": TRAIT_BY_KEY[key]["label"], "status": status,
                     "mentions": mentions, "combined": combined[key].model_dump()})

    marks_out, combined_marks = [], []
    seen: dict[tuple[str, str], dict] = {}
    for i, ex in enumerate(extractions):
        for mk in ex.profile.marks:
            k = (mk.type, mk.location)
            if k in seen:
                seen[k]["witnesses"].append(i + 1)
            else:
                seen[k] = {"type": mk.type, "location": mk.location, "size": mk.size, "witnesses": [i + 1],
                           "side_specified": mk.side_specified, "evidence": mk.evidence}
    for idx, (k, info) in enumerate(seen.items()):
        info["status"] = "shared" if len(info["witnesses"]) > 1 else "single_source"
        marks_out.append(info)
        combined_marks.append(Mark(id=f"m{idx + 1}", type=info["type"], location=info["location"], size=info["size"],
                                   side_specified=info["side_specified"], source="extracted",
                                   evidence=f"Witness {', '.join(map(str, info['witnesses']))}"))

    profile = Profile(traits=combined, marks=combined_marks)
    counts = {s: sum(1 for r in rows if r["status"] == s) for s in ("shared", "conflicting", "single_source", "unmentioned")}
    return {
        "witnesses": [{"index": i + 1, "description": d,
                       "recognized": ex.to_dict()["recognized_count"]} for i, (d, ex) in enumerate(zip(descriptions, extractions))],
        "traits": rows,
        "marks": marks_out,
        "combined_profile": profile.model_dump(),
        "requires_review": review,
        "counts": counts,
        "disclaimer": "Agreement between witnesses does not establish identity. Conflicting traits are left unresolved until an operator decides.",
    }
