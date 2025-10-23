from __future__ import annotations

import time

from discord_utils import _jitter_delay as discord_delay
from twilio_utils import _jitter_delay as twilio_delay
from airtable_utils import _jitter_delay as airtable_delay


def test_jitter_monotonic_nonzero():
    # Not strictly monotonic, but delay grows roughly with attempts
    d1 = airtable_delay(1)
    d2 = airtable_delay(2)
    d3 = airtable_delay(3)
    assert d1 > 0
    assert d2 > d1 or d2 > 1
    assert d3 > d2 or d3 > 2


def test_jitter_variation():
    vals = {discord_delay(2) for _ in range(5)}
    assert len(vals) > 1

    vals2 = {twilio_delay(2) for _ in range(5)}
    assert len(vals2) > 1
