from aire_prime.agents.subprocess_adapter import (
    ResourceObservation,
    parse_time_resource_output,
)


def test_parse_supported_time_output() -> None:
    observation = parse_time_resource_output(
        b"0.012 real\n123456  maximum resident set size\n"
    )

    assert observation == ResourceObservation(
        elapsed_seconds=0.012,
        peak_resident_bytes=123456.0,
    )


def test_parse_time_output_stays_undetermined_when_a_field_is_missing() -> None:
    assert parse_time_resource_output(b"0.012 real\n") is None


def test_parse_time_output_rejects_nonfinite_or_negative_values() -> None:
    assert parse_time_resource_output(b"nan real\n123456  maximum resident set size\n") is None
    assert parse_time_resource_output(b"0.012 real\n-1  maximum resident set size\n") is None
