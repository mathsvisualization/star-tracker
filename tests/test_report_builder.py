
from datetime import date, timedelta
from decimal import Decimal

import pytest

import reports.report_builder as report


# ==================================================
# TEST DATA
# ==================================================

@pytest.fixture
def sample_data():
    return {
        "rate": Decimal("104"),
        "earnings": {
            "2026-01-01": 1000,
            "2026-01-10": 500,
            "2026-02-05": 2000,
        },
        "withdrawals": [
            {
                "date": "2026-01-20",
                "stars": 500,
                "rate": Decimal("104"),
            },
            {
                "date": "2026-02-01",
                "stars": 300,
                "rate": Decimal("105"),
            },
        ],
        "locked": False,
    }


# ==================================================
# TITLE LINES
# ==================================================

def test_title_lines():
    lines = report.title_lines("TEST REPORT")

    assert len(lines) == 3
    assert lines[0] == "=" * report.WIDTH
    assert lines[1] == "TEST REPORT".center(report.WIDTH)
    assert lines[2] == "=" * report.WIDTH


# ==================================================
# ENTRY FORMATTING
# ==================================================

def test_format_entry_contains_expected_information():
    lines = report.format_entry(
        "2026-01-01",
        1000,
        Decimal("104"),
    )

    text = "\n".join(lines)

    assert "Date" in text
    assert "Stars       : 1,000" in text
    assert "Buyer paid" in text
    assert "Buyer USD" in text
    assert "Payout" in text
    assert "Payout INR" in text
    assert "Payment on" in text


def test_format_entry_uses_correct_date():
    lines = report.format_entry(
        "2026-01-01",
        1000,
        Decimal("104"),
    )

    assert "01 January 2026" in "\n".join(lines)


def test_format_entry_rejects_invalid_date():
    with pytest.raises(ValueError):
        report.format_entry(
            "invalid-date",
            1000,
            Decimal("104"),
        )


# ==================================================
# WITHDRAWAL FORMATTING
# ==================================================

def test_format_withdrawal_completed(monkeypatch):
    class FakeDateTime:
        @classmethod
        def now(cls):
            class Result:
                date = staticmethod(lambda: date(2026, 11, 8))

            return Result()

    monkeypatch.setattr(
        report,
        "__import__",
        __import__,
        raising=False,
    )

    withdrawal = {
        "date": "2026-01-20",
        "stars": 500,
        "rate": Decimal("104"),
    }

    lines = report.format_withdrawal(withdrawal)

    assert "Completed" in "\n".join(lines)


def test_format_withdrawal_scheduled():
    future_date = date.today() + timedelta(days=10)

    withdrawal = {
        "date": future_date.isoformat(),
        "stars": 500,
        "rate": Decimal("104"),
    }

    lines = report.format_withdrawal(withdrawal)

    assert "Scheduled" in "\n".join(lines)


def test_format_withdrawal_contains_expected_information():
    withdrawal = {
        "date": "2026-01-20",
        "stars": 500,
        "rate": Decimal("104"),
    }

    text = "\n".join(
        report.format_withdrawal(withdrawal)
    )

    assert "Stars       : 500" in text
    assert "Rate        : Rs. 104/USD" in text
    assert "Payout USD" in text
    assert "Payout INR" in text


# ==================================================
# WITHDRAWAL TOTALS
# ==================================================

def test_withdrawal_total_lines():
    withdrawals = [
        {
            "date": "2026-01-20",
            "stars": 500,
            "rate": Decimal("104"),
        },
        {
            "date": "2026-02-01",
            "stars": 300,
            "rate": Decimal("105"),
        },
    ]

    lines = report.withdrawal_total_lines(withdrawals)
    text = "\n".join(lines)

    assert "Total withdrawn : 800 Stars" in text
    assert "Total payout    :" in text
    assert "Total payout INR:" in text


def test_withdrawal_total_lines_empty():
    lines = report.withdrawal_total_lines([])

    assert "Total withdrawn : 0 Stars" in lines[0]


# ==================================================
# BALANCE LINES
# ==================================================

def test_balance_lines(sample_data):
    lines = report.balance_lines(sample_data)
    text = "\n".join(lines)

    assert "Total earned" in text
    assert "Total withdrawn" in text
    assert "Scheduled" in text
    assert "Available" in text
    assert "Pending maturity" in text


def test_balance_lines_empty():
    data = {
        "rate": Decimal("104"),
        "earnings": {},
        "withdrawals": [],
        "locked": False,
    }

    lines = report.balance_lines(data)

    assert "Total earned     : 0 Stars" in lines[0]
    assert "Total withdrawn  : 0 Stars" in lines[1]


# ==================================================
# UPCOMING PAYOUTS
# ==================================================

def test_upcoming_lines_empty(monkeypatch):
    monkeypatch.setattr(
        report,
        "upcoming_payouts",
        lambda data: [],
    )

    lines = report.upcoming_lines({})

    assert lines == ["No upcoming payouts."]


def test_upcoming_lines_with_payouts(monkeypatch):
    payouts = [
        (date(2026, 11, 10), 1000),
        (date(2026, 11, 15), 500),
    ]

    monkeypatch.setattr(
        report,
        "upcoming_payouts",
        lambda data: payouts,
    )

    lines = report.upcoming_lines({})

    assert len(lines) == 2
    assert "1,000 Stars" in lines[0]
    assert "500 Stars" in lines[1]


# ==================================================
# MONTHLY SUMMARY
# ==================================================

def test_monthly_lines_empty():
    data = {
        "rate": Decimal("104"),
        "earnings": {},
        "withdrawals": [],
        "locked": False,
    }

    assert report.monthly_lines(data) == [
        "No earning records available."
    ]


def test_monthly_lines_groups_same_month(sample_data):
    lines = report.monthly_lines(sample_data)
    text = "\n".join(lines)

    assert "January 2026" in text
    assert "February 2026" in text

    assert "Stars earned : 1,500" in text
    assert "Stars earned : 2,000" in text


def test_monthly_lines_contains_financial_totals(sample_data):
    text = "\n".join(
        report.monthly_lines(sample_data)
    )

    assert "Buyer paid" in text
    assert "Payout USD" in text
    assert "Payout INR" in text
    assert "Price gap" in text


def test_monthly_lines_sorts_months(sample_data):
    lines = report.monthly_lines(sample_data)

    january_index = lines.index("January 2026")
    february_index = lines.index("February 2026")

    assert january_index < february_index


# ==================================================
# COMPLETE REPORT
# ==================================================

def test_build_report_contains_all_sections(sample_data):
    text = report.build_report(sample_data)

    sections = [
        "TELEGRAM STARS TRACKER",
        "EARNINGS",
        "WITHDRAWALS",
        "CURRENT BALANCE",
        "UPCOMING PAYOUTS",
        "MONTHLY SUMMARY",
        "END OF REPORT",
    ]

    for section in sections:
        assert section in text


def test_build_report_contains_all_earning_entries(sample_data):
    text = report.build_report(sample_data)

    assert "ENTRY #1" in text
    assert "ENTRY #2" in text
    assert "ENTRY #3" in text


def test_build_report_contains_all_withdrawals(sample_data):
    text = report.build_report(sample_data)

    assert "WITHDRAWAL #1" in text
    assert "WITHDRAWAL #2" in text


def test_build_report_empty_data():
    data = {
        "rate": Decimal("104"),
        "earnings": {},
        "withdrawals": [],
        "locked": False,
    }

    text = report.build_report(data)

    assert "No earnings recorded." in text
    assert "No withdrawals recorded." in text
    assert "No upcoming payouts." in text
    assert "No earning records available." in text


def test_build_report_ends_with_newline(sample_data):
    text = report.build_report(sample_data)

    assert text.endswith("\n")


def test_build_report_has_equal_width_separators(sample_data):
    text = report.build_report(sample_data)

    for line in text.splitlines():
        if line and set(line) == {"="}:
            assert len(line) == report.WIDTH
