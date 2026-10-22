from decimal import Decimal

import pytest

from app.ton_validation import validate_ton_amount


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (12, Decimal("12.0000")),
        (12.3, Decimal("12.3000")),
        (12.3456, Decimal("12.3456")),
        (28.919999999999998, Decimal("28.9200")),
    ],
)
def test_valid_ton_precision(value, expected):
    assert validate_ton_amount(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        12.34567,
        -1,
        float("nan"),
        float("inf"),
        float("-inf"),
    ],
)
def test_invalid_ton_precision_is_rejected(value):
    with pytest.raises(ValueError):
        validate_ton_amount(value)


def test_numeric_string_is_supported():
    assert validate_ton_amount("12.3456") == Decimal("12.3456")


def test_invalid_string_is_rejected():
    with pytest.raises(ValueError):
        validate_ton_amount("bukan-angka")


def test_maximum_numeric_14_4_is_accepted():
    assert validate_ton_amount("9999999999.9999") == Decimal("9999999999.9999")


def test_value_above_maximum_numeric_14_4_is_rejected():
    with pytest.raises(ValueError):
        validate_ton_amount("10000000000.0000")
