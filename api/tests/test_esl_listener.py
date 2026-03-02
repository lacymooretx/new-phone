"""Unit tests for ESL event listener logic.

Tests the event parsing and CDR/recording creation logic
without requiring a live FreeSWITCH connection.
"""

from new_phone.services.esl_event_listener import (
    HANGUP_CAUSE_MAP,
    ESLEventListener,
    _disposition_from_hangup,
    _epoch_to_datetime,
)


def test_disposition_answered():
    assert _disposition_from_hangup("NORMAL_CLEARING", 60) == "answered"


def test_disposition_answered_zero_billsec():
    assert _disposition_from_hangup("NORMAL_CLEARING", 0) == "no_answer"


def test_disposition_no_answer():
    assert _disposition_from_hangup("NO_ANSWER", 0) == "no_answer"


def test_disposition_busy():
    assert _disposition_from_hangup("USER_BUSY", 0) == "busy"


def test_disposition_cancelled():
    assert _disposition_from_hangup("ORIGINATOR_CANCEL", 0) == "cancelled"


def test_disposition_failed():
    assert _disposition_from_hangup("UNALLOCATED_NUMBER", 0) == "failed"


def test_disposition_unknown_cause():
    assert _disposition_from_hangup("SOME_UNKNOWN_CAUSE", 0) == "failed"


def test_epoch_to_datetime_valid():
    dt = _epoch_to_datetime("1709000000")
    assert dt is not None
    assert dt.year >= 2024


def test_epoch_to_datetime_zero():
    assert _epoch_to_datetime("0") is None


def test_epoch_to_datetime_empty():
    assert _epoch_to_datetime("") is None


def test_epoch_to_datetime_invalid():
    assert _epoch_to_datetime("not-a-number") is None


def test_hangup_cause_map_completeness():
    expected_causes = [
        "NORMAL_CLEARING", "ORIGINATOR_CANCEL", "NO_ANSWER",
        "NO_USER_RESPONSE", "USER_BUSY", "CALL_REJECTED",
    ]
    for cause in expected_causes:
        assert cause in HANGUP_CAUSE_MAP


def test_listener_init():
    listener = ESLEventListener()
    assert listener.host is not None
    assert listener.port > 0
    assert listener._running is False


def test_parse_headers():
    listener = ESLEventListener()
    text = "Event-Name: CHANNEL_HANGUP_COMPLETE\nUnique-ID: abc-123\nvariable_duration: 60"
    headers = listener._parse_headers(text)
    assert headers["Event-Name"] == "CHANNEL_HANGUP_COMPLETE"
    assert headers["Unique-ID"] == "abc-123"
    assert headers["variable_duration"] == "60"


def test_parse_headers_url_encoded():
    listener = ESLEventListener()
    text = "Caller-Caller-ID-Name: John%20Doe"
    headers = listener._parse_headers(text)
    assert headers["Caller-Caller-ID-Name"] == "John Doe"


def test_parse_headers_empty():
    listener = ESLEventListener()
    headers = listener._parse_headers("")
    assert headers == {}
