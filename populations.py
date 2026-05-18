"""Back-compat re-export of population data; prefer importing state_data."""
from state_data import STATES, NAME_TO_USPS, lookup  # noqa: F401

POPULATIONS = {usps: rec["population"] for usps, rec in STATES.items()}
