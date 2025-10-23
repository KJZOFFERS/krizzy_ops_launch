from __future__ import annotations

import datetime

from govcon_subtrap_engine import _filter_opps


def test_filter_opps_basic():
    now = datetime.datetime.utcnow()
    within = (now + datetime.timedelta(days=3)).isoformat()
    far = (now + datetime.timedelta(days=30)).isoformat()

    opps = [
        {
            "title": "Combined Synopsis/Solicitation ABC",
            "type": "Combined Synopsis/Solicitation",
            "naicsCode": "541611",
            "responseDate": within,
            "solicitationNumber": "ABC-1",
            "officers": [{"email": "ko@agency.gov", "fullName": "KO"}],
        },
        {  # outside window
            "title": "Combined",
            "type": "Combined",
            "naicsCode": "541611",
            "responseDate": far,
            "solicitationNumber": "ABC-2",
            "officers": [{"email": "ko@agency.gov", "fullName": "KO"}],
        },
        {  # wrong type
            "title": "Sources Sought",
            "type": "Sources Sought",
            "naicsCode": "541611",
            "responseDate": within,
            "solicitationNumber": "ABC-3",
            "officers": [{"email": "ko@agency.gov", "fullName": "KO"}],
        },
    ]

    out = _filter_opps(opps)
    ids = {x["solicitationNumber"] for x in out}
    assert "ABC-1" in ids
    assert "ABC-2" not in ids
    assert "ABC-3" not in ids
