"""Canonical list of Nigeria's 36 states + FCT, with name aliases used in sources."""

from __future__ import annotations

import re

STATES = [
    "Abia", "Adamawa", "Akwa Ibom", "Anambra", "Bauchi", "Bayelsa", "Benue", "Borno",
    "Cross River", "Delta", "Ebonyi", "Edo", "Ekiti", "Enugu", "FCT", "Gombe", "Imo",
    "Jigawa", "Kaduna", "Kano", "Katsina", "Kebbi", "Kogi", "Kwara", "Lagos", "Nasarawa",
    "Niger", "Ogun", "Ondo", "Osun", "Oyo", "Plateau", "Rivers", "Sokoto", "Taraba",
    "Yobe", "Zamfara",
]

_ALIASES = {
    "abuja": "FCT", "fct": "FCT", "fct abuja": "FCT", "federal capital territory": "FCT",
    "abuja fct": "FCT", "fct-abuja": "FCT",
    "akwa-ibom": "Akwa Ibom", "akwaibom": "Akwa Ibom",
    "cross-river": "Cross River", "crossriver": "Cross River",
    "nassarawa": "Nasarawa",
}


def canonical_state(name) -> str | None:
    """Map a source label to a canonical state name, or None if it is not a state."""
    if not isinstance(name, str):
        return None
    s = re.sub(r"\s+", " ", name.replace("\xa0", " ")).strip().lower()
    s = re.sub(r"\s*state$", "", s)
    if s in _ALIASES:
        return _ALIASES[s]
    for st in STATES:
        if s == st.lower():
            return st
    return None

# Geopolitical zones. Checked 2026-11-26 against the zone grouping in the NBS AGO
# Price Watch table for September 2023 (all 37 states match).
ZONES = {
    "North Central": ["Benue", "FCT", "Kogi", "Kwara", "Nasarawa", "Niger", "Plateau"],
    "North East": ["Adamawa", "Bauchi", "Borno", "Gombe", "Taraba", "Yobe"],
    "North West": ["Jigawa", "Kaduna", "Kano", "Katsina", "Kebbi", "Sokoto", "Zamfara"],
    "South East": ["Abia", "Anambra", "Ebonyi", "Enugu", "Imo"],
    "South South": ["Akwa Ibom", "Bayelsa", "Cross River", "Delta", "Edo", "Rivers"],
    "South West": ["Ekiti", "Lagos", "Ogun", "Ondo", "Osun", "Oyo"],
}
ZONE_OF = {s: z for z, ss in ZONES.items() for s in ss}
