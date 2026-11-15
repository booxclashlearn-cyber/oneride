"""Illustrative route only: validate order/names with an operator before launch."""
STOPS = [
    {"id": "town", "name": "Town Centre", "aliases": ["TOWN", "CENTRE", "TOWN CENTRE"]},
    {"id": "kamwala", "name": "Kamwala", "aliases": ["KAMWALA"]},
    {"id": "chilenje", "name": "Chilenje", "aliases": ["CHILENJE"]},
    {"id": "woodlands", "name": "Woodlands", "aliases": ["WOODLANDS"]},
]
ROUTES = [
    {"id": "town-woodlands", "name": "Town Centre → Woodlands", "stopIds": [s["id"] for s in STOPS], "demo": True},
    {"id": "woodlands-town", "name": "Woodlands → Town Centre", "stopIds": [s["id"] for s in reversed(STOPS)], "demo": True},
]


def stop_name(stop_id):
    return next(s["name"] for s in STOPS if s["id"] == stop_id)


def resolve_stop(value, choices=None):
    allowed = [s for s in STOPS if choices is None or s["id"] in choices]
    if value.strip().isdigit() and 1 <= int(value) <= len(allowed):
        return allowed[int(value) - 1]["id"]
    matches = [s["id"] for s in allowed if value.strip().upper() in [s["id"].upper(), *s["aliases"]]]
    return matches[0] if len(matches) == 1 else None


def matching(boarding, destination):
    return [r["id"] for r in ROUTES if boarding in r["stopIds"] and destination in r["stopIds"] and r["stopIds"].index(boarding) < r["stopIds"].index(destination)]


def menu(ids=None):
    return "\n".join(f"{i + 1}. {s['name']}" for i, s in enumerate(s for s in STOPS if ids is None or s["id"] in ids))
