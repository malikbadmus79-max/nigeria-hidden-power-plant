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
