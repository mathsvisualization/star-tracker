from datetime import date
from decimal import Decimal

import pytest

import core.validation as validation


# ==================================================
# FIXTURES
# ==================================================

@pytest.fixture
def fixed_today(monkeypatch):
    monkeypatch.setattr(
        validation,
        "today",
        lambda: date(2026, 2, 1),
    )


# ==================================================
# DATA STRUCTURE
# ==================================================

def test_new_data():
    data = validation.new_data()

    assert data["rate"] == validation.DEFAULT_USD_TO_INR
    assert data["earnings"] == {}
    assert data["withdrawals"] == []
    assert data["locked"] is False
    assert data["issues"] == []


# ==================================================
# DATE VALIDATION
# ==================================================

def test_check_date_valid():
    assert validation.check_date("2026-01-15") is None


@pytest.mark.parametrize(
    "value",
    [
        "2026-02-30",
        "15-01-2026",
        "2026/01/15",
        "invalid",
        "",
        "2026-1-5",
    ],
)
def test_check_date_invalid(value):
    with pytest.raises(ValueError):
        validation.check_date(value)


# ==================================================
# STARS VALIDATION
# ==================================================

@pytest.mark.parametrize(
    "value, expected",
    [
        ("1", 1),
        ("500", 500),
        ("1000", 1000),
    ],
)
def test_parse_stars_valid(value, expected):
    assert validation.parse_stars(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        "0",
        "-1",
        "-500",
        "abc",
        "",
        "1.5",
    ],
)
def test_parse_stars_invalid(value):
    with pytest.raises(ValueError):
        validation.parse_stars(value)


# ==================================================
# RATE VALIDATION
# ==================================================

@pytest.mark.parametrize(
    "value, expected",
    [
        ("104", Decimal("104")),
        ("100.50", Decimal("100.50")),
        ("0.01", Decimal("0.01")),
    ],
)
def test_parse_rate_valid(value, expected):
    assert validation.parse_rate(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        "0",
        "-1",
        "NaN",
        "Infinity",
        "-Infinity",
        "abc",
        "",
    ],
)
def test_parse_rate_invalid(value):
    with pytest.raises((ValueError, ArithmeticError)):
        validation.parse_rate(value)


# ==================================================
# RECORD APPLICATION
# ==================================================

def test_apply_rate_record():
    data = validation.new_data()

    validation.apply_record(
        data,
        "RATE",
        ["105"],
    )

    assert data["rate"] == Decimal("105")


def test_apply_entry_record():
    data = validation.new_data()

    validation.apply_record(
        data,
        "ENTRY",
        ["2026-01-15", "500"],
    )

    assert data["earnings"] == {
        "2026-01-15": 500,
    }


def test_apply_withdraw_record_with_rate():
    data = validation.new_data()

    validation.apply_record(
        data,
        "WITHDRAW",
        ["2026-01-20", "500", "105"],
    )

    assert data["withdrawals"] == [
        {
            "date": "2026-01-20",
            "stars": 500,
            "rate": Decimal("105"),
            "fee": Decimal("0"),
        }
    ]


def test_apply_withdraw_record_default_rate():
    data = validation.new_data()
    data["rate"] = Decimal("104")

    validation.apply_record(
        data,
        "WITHDRAW",
        ["2026-01-20", "500"],
    )

    assert data["withdrawals"] == [
        {
            "date": "2026-01-20",
            "stars": 500,
            "rate": Decimal("104"),
            "fee": Decimal("0"),
        }
    ]

def test_apply_withdraw_record_with_fee():
    data = validation.new_data()

    validation.apply_record(
        data,
        "WITHDRAW",
        ["2026-01-20", "500", "105", "1.25"],
    )

    assert data["withdrawals"] == [
        {
            "date": "2026-01-20",
            "stars": 500,
            "rate": Decimal("105"),
            "fee": Decimal("1.25"),
        }
    ]

def test_duplicate_entry_rejected():
    data = validation.new_data()

    validation.apply_record(
        data,
        "ENTRY",
        ["2026-01-15", "500"],
    )

    with pytest.raises(ValueError, match="duplicate ENTRY"):
        validation.apply_record(
            data,
            "ENTRY",
            ["2026-01-15", "1000"],
        )


@pytest.mark.parametrize(
    "tag, fields",
    [
        ("RATE", []),
        ("RATE", ["104", "105"]),
        ("ENTRY", ["2026-01-15"]),
        ("ENTRY", ["2026-01-15", "500", "extra"]),
        ("WITHDRAW", ["2026-01-15"]),
        ("WITHDRAW", ["2026-01-15", "500", "104", "extra"]),
    ],
)
def test_invalid_record_field_count(tag, fields):
    data = validation.new_data()

    with pytest.raises(ValueError):
        validation.apply_record(data, tag, fields)


# ==================================================
# RECORD PARSING
# ==================================================

def test_parse_lines_valid_records():
    lines = [
        "RATE|105",
        "ENTRY|2026-01-01|1000",
        "WITHDRAW|2026-01-25|500|104",
    ]

    data, issues = validation.parse_lines(lines)

    assert issues == []
    assert data["rate"] == Decimal("105")

    assert data["earnings"] == {
        "2026-01-01": 1000,
    }

    assert data["withdrawals"] == [
        {
            "date": "2026-01-25",
            "stars": 500,
            "rate": Decimal("104"),
            "fee": Decimal("0"),
        }
    ]


def test_parse_lines_unknown_tag():
    lines = [
        "UNKNOWN|something",
    ]

    data, issues = validation.parse_lines(lines)

    assert len(issues) == 1
    assert "unknown record tag" in issues[0]


def test_parse_lines_invalid_number():
    lines = [
        "ENTRY|2026-01-01|abc",
    ]

    data, issues = validation.parse_lines(lines)

    assert len(issues) == 1
    assert "invalid literal" in issues[0]


def test_parse_lines_invalid_decimal():
    lines = [
        "RATE|not-a-number",
    ]

    data, issues = validation.parse_lines(lines)

    assert len(issues) == 1
    assert "invalid number" in issues[0]


def test_parse_lines_duplicate_entry():
    lines = [
        "ENTRY|2026-01-01|500",
        "ENTRY|2026-01-01|1000",
    ]

    data, issues = validation.parse_lines(lines)

    assert data["earnings"]["2026-01-01"] == 500
    assert len(issues) == 1
    assert "duplicate ENTRY" in issues[0]


def test_parse_lines_ignores_generated_report():
    lines = [
        "RATE|104",
        "ENTRY|2026-01-01|500",
        "",
        "This is generated report text",
        "Some other report content",
    ]

    data, issues = validation.parse_lines(lines)

    assert issues == []
    assert data["rate"] == Decimal("104")
    assert data["earnings"] == {
        "2026-01-01": 500,
    }


def test_parse_lines_reports_correct_line_number():
    lines = [
        "RATE|104",
        "UNKNOWN|value",
    ]

    data, issues = validation.parse_lines(lines)

    assert len(issues) == 1
    assert "line 2" in issues[0]


# ==================================================
# SHORTFALL VALIDATION
# ==================================================

def test_shortfalls_no_problem(fixed_today):
    earnings = {
        "2026-01-01": 1000,
    }

    withdrawals = [
        {
            "date": "2026-02-01",
            "stars": 500,
            "rate": Decimal("104"),
        }
    ]

    problems = validation.shortfalls(
        earnings,
        withdrawals,
    )

    assert problems == {}


def test_shortfalls_detect_problem(fixed_today):
    earnings = {
        "2026-01-01": 500,
    }

    withdrawals = [
        {
            "date": "2026-01-20",
            "stars": 1000,
            "rate": Decimal("104"),
        }
    ]

    problems = validation.shortfalls(
        earnings,
        withdrawals,
    )

    assert date(2026, 1, 20) in problems

    matured, needed = problems[date(2026, 1, 20)]

    assert matured == 0
    assert needed == 1000


# ==================================================
# SHORTFALL DESCRIPTION
# ==================================================

def test_describe_shortfall():
    result = validation.describe_shortfall(
        date(2026, 2, 1),
        500,
        1000,
    )

    assert result == (
        "by 01 February 2026: "
        "1,000 Stars withdrawn but only 500 matured"
    )


# ==================================================
# ACCOUNTING PROBLEMS
# ==================================================

def test_accounting_problems_no_problem(fixed_today):
    data = {
        "earnings": {
            "2026-01-01": 1000,
        },
        "withdrawals": [
            {
                "date": "2026-02-01",
                "stars": 500,
                "rate": Decimal("104"),
            }
        ],
    }

    problems = validation.accounting_problems(data)

    assert problems == []


def test_accounting_problems_detect_problem(fixed_today):
    data = {
        "earnings": {
            "2026-01-01": 500,
        },
        "withdrawals": [
            {
                "date": "2026-01-20",
                "stars": 1000,
                "rate": Decimal("104"),
            }
        ],
    }

    problems = validation.accounting_problems(data)

    # Problem exists on both January 20 and February 1.
    assert len(problems) == 2

    assert "1,000 Stars withdrawn" in problems[0]
    assert "only 0 matured" in problems[0]

    assert "1,000 Stars withdrawn" in problems[1]
    assert "only 500 matured" in problems[1]


# ==================================================
# NEW SHORTFALL DETECTION
# ==================================================

def test_new_shortfall_detects_new_problem(fixed_today):
    old_earnings = {
        "2026-01-01": 1000,
    }

    old_withdrawals = []

    new_earnings = {
        "2026-01-01": 1000,
    }

    new_withdrawals = [
        {
            "date": "2026-01-20",
            "stars": 1500,
            "rate": Decimal("104"),
        }
    ]

    problem = validation.new_shortfall(
        old_earnings,
        old_withdrawals,
        new_earnings,
        new_withdrawals,
    )

    assert problem == (
        date(2026, 1, 20),
        0,
        1500,
    )


def test_new_shortfall_no_new_problem(fixed_today):
    old_earnings = {
        "2026-01-01": 1000,
    }

    old_withdrawals = []

    new_earnings = {
        "2026-01-01": 1000,
    }

    new_withdrawals = [
        {
            "date": "2026-02-01",
            "stars": 500,
            "rate": Decimal("104"),
        }
    ]

    problem = validation.new_shortfall(
        old_earnings,
        old_withdrawals,
        new_earnings,
        new_withdrawals,
    )

    assert problem is None


def test_new_shortfall_detects_worsening_problem(fixed_today):
    old_earnings = {
        "2026-01-01": 1000,
    }

    old_withdrawals = [
        {
            "date": "2026-01-20",
            "stars": 600,
            "rate": Decimal("104"),
        }
    ]

    new_earnings = {
        "2026-01-01": 1000,
    }

    new_withdrawals = [
        {
            "date": "2026-01-20",
            "stars": 800,
            "rate": Decimal("104"),
        }
    ]

    problem = validation.new_shortfall(
        old_earnings,
        old_withdrawals,
        new_earnings,
        new_withdrawals,
    )

    assert problem == (
        date(2026, 1, 20),
        0,
        800,
    )


# ==================================================
# SHORTFALL REPORT
# ==================================================

def test_report_shortfall(capsys):
    validation.report_shortfall(
        (
            date(2026, 2, 1),
            500,
            1000,
        )
    )

    output = capsys.readouterr().out

    assert "Not enough matured Stars" in output
    assert "500 Stars" in output
    assert "1,000 Stars" in output
