
from datetime import date
from decimal import Decimal

import pytest

import core.calculations as calc


# ==================================================
# DATE TESTS
# ==================================================

def test_payment_date_for():
    earned, payment = calc.payment_date_for("2026-01-01")

    assert earned == date(2026, 1, 1)
    assert payment == date(2026, 1, 22)


def test_parse_date():
    assert calc.parse_date("2026-01-01") == date(2026, 1, 1)


def test_parse_invalid_date():
    with pytest.raises(ValueError):
        calc.parse_date("invalid-date")


# ==================================================
# BASIC CALCULATION TESTS
# ==================================================

def test_buyer_price_usd():
    result = calc.buyer_price_usd(Decimal("104"))

    assert result == Decimal("999") / Decimal("104")


def test_payout_inr():
    assert calc.payout_inr(Decimal("104")) == Decimal("676.00")


def test_calculate_500_stars():
    result = calc.calculate(500, Decimal("104"))

    assert result["buyer"] == Decimal("999")
    assert result["buyer_usd"] == Decimal("999") / Decimal("104")
    assert result["usd"] == Decimal("6.50")
    assert result["inr"] == Decimal("676.00")
    assert result["gap"] == Decimal("323.00")
    assert result["gap_usd"] == Decimal("323") / Decimal("104")


def test_calculate_1000_stars():
    result = calc.calculate(1000, Decimal("104"))

    assert result["buyer"] == Decimal("1998")
    assert result["usd"] == Decimal("13.00")
    assert result["inr"] == Decimal("1352.00")
    assert result["gap"] == Decimal("646.00")


# ==================================================
# WITHDRAWAL VALUE TESTS
# ==================================================

def test_value_of_withdrawals():
    withdrawals = [
        {
            "date": "2026-01-01",
            "stars": 500,
            "rate": Decimal("104"),
        },
        {
            "date": "2026-01-02",
            "stars": 1000,
            "rate": Decimal("100"),
        },
    ]

    usd, inr = calc.value_of(withdrawals)

    assert usd == Decimal("19.50")
    assert inr == Decimal("1976.00")


def test_value_of_empty_withdrawals():
    usd, inr = calc.value_of([])

    assert usd == Decimal("0")
    assert inr == Decimal("0")


# ==================================================
# WITHDRAWAL STATUS TESTS
# ==================================================

@pytest.fixture
def fixed_today(monkeypatch):
    monkeypatch.setattr(
        calc,
        "today",
        lambda: date(2026, 2, 1),
    )


@pytest.fixture
def sample_data():
    return {
        "rate": Decimal("104"),
        "earnings": {
            "2026-01-01": 500,
            "2026-01-10": 1000,
        },
        "withdrawals": [
            {
                "date": "2026-01-20",
                "stars": 200,
                "rate": Decimal("104"),
            },
            {
                "date": "2026-02-10",
                "stars": 300,
                "rate": Decimal("104"),
            },
        ],
        "locked": False,
        "issues": [],
    }


def test_sorted_withdrawals(sample_data):
    result = calc.sorted_withdrawals(sample_data)

    assert [w["date"] for w in result] == [
        "2026-01-20",
        "2026-02-10",
    ]


def test_done_withdrawals(sample_data, fixed_today):
    result = calc.done_withdrawals(sample_data)

    assert len(result) == 1
    assert result[0]["stars"] == 200


def test_scheduled_withdrawals(sample_data, fixed_today):
    result = calc.scheduled_withdrawals(sample_data)

    assert len(result) == 1
    assert result[0]["stars"] == 300


def test_withdrawn_so_far(sample_data, fixed_today):
    assert calc.withdrawn_so_far(sample_data) == 200


def test_scheduled_stars(sample_data, fixed_today):
    assert calc.scheduled_stars(sample_data) == 300


def test_total_withdrawn(sample_data):
    assert calc.total_withdrawn(sample_data) == 500


# ==================================================
# BALANCE TESTS
# ==================================================

def test_total_earned(sample_data):
    assert calc.total_earned(sample_data) == 1500


def test_balance_stars(sample_data, fixed_today):
    assert calc.balance_stars(sample_data) == 1300


def test_matured_by():
    earnings = {
        "2026-01-01": 500,
        "2026-01-10": 1000,
    }

    result = calc.matured_by(
        earnings,
        date(2026, 2, 1),
    )

    assert result == 1500


def test_available_stars(sample_data, fixed_today):
    assert calc.available_stars(sample_data) == 1000


def test_pending_stars(sample_data, fixed_today):
    assert calc.pending_stars(sample_data) == 300


# ==================================================
# UPCOMING PAYOUT TEST
# ==================================================

def test_upcoming_payouts(fixed_today):
    data = {
        "earnings": {
            "2026-01-01": 500,
            "2026-01-20": 1000,
        },
        "withdrawals": [],
    }

    result = calc.upcoming_payouts(data)

    assert result == [
        (date(2026, 2, 10), 1000),
    ]
