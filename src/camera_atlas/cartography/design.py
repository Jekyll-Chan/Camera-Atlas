from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    ink: tuple[int, int, int] = (237, 234, 222)
    accent: tuple[int, int, int] = (173, 67, 56)
    line: float = 0.85
    max_labels: int = 4


THEMES = {
    "editorial-minimal": Theme(),
    "topographic-fine": Theme(line=0.6, max_labels=2),
    "coastal-atlas": Theme(ink=(228, 235, 230), line=1.0),
    "urban-documentary": Theme(ink=(238, 238, 233), line=0.65, max_labels=3),
    "monochrome-print": Theme(ink=(224, 224, 218), accent=(160, 160, 155), line=0.85),
}

KINDS = {
    "coastline": {"water", "coastline", "place"},
    "topographic": {"contour", "place"},
    "urban": {"road", "boundary", "place"},
    "trail": {"trail", "contour", "place"},
    "river": {"river", "water", "place"},
    "regional": {"boundary", "water", "coastline", "place"},
    "minimal": {"water", "coastline", "boundary", "place"},
}


def select_mode(features, requested, subject="unknown"):
    kinds = {f.get("properties", {}).get("kind") for f in features}
    if requested != "auto":
        return requested
    preferred = {
        "lake": "coastline",
        "coast": "coastline",
        "mountain": "topographic",
        "city": "urban",
        "trail": "trail",
        "river": "river",
    }.get(subject)
    if preferred and kinds & (KINDS[preferred] - {"place"}):
        return preferred
    for kind, mode in (
        ("water", "coastline"),
        ("contour", "topographic"),
        ("road", "urban"),
        ("trail", "trail"),
        ("river", "river"),
        ("coastline", "coastline"),
    ):
        if kind in kinds:
            return mode
    return "regional" if "boundary" in kinds else "minimal"
