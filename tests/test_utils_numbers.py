from fmsv2.utils.numbers import MAX_AMOUNT, to_valid_amount


def test_valid_amount_passthrough():
    assert to_valid_amount(1000) == 1000
    assert to_valid_amount("1000") == 1000
    assert to_valid_amount(1000.9) == 1000


def test_negative_amount_rejected():
    assert to_valid_amount(-1) is None


def test_non_numeric_amount_rejected():
    assert to_valid_amount("abc") is None
    assert to_valid_amount(None) is None


def test_nan_and_infinity_rejected():
    assert to_valid_amount(float("nan")) is None
    assert to_valid_amount(float("inf")) is None
    assert to_valid_amount("inf") is None


def test_amount_at_max_boundary_accepted():
    assert to_valid_amount(MAX_AMOUNT) == MAX_AMOUNT


def test_amount_over_max_boundary_rejected():
    assert to_valid_amount(MAX_AMOUNT + 1) is None
    assert to_valid_amount(1e20) is None
