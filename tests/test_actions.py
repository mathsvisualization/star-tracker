
from datetime import date, timedelta
from decimal import Decimal

import pytest

import ui.actions as actions


@pytest.fixture
def sample_data():
    return {
        "rate": Decimal("104"),
        "earnings": {
            "2026-01-01": 1000,
            "2026-01-10": 500,
        },
        "withdrawals": [],
        "locked": False,
        "issues": [],
    }


@pytest.fixture
def locked_data(sample_data):
    sample_data["locked"] = True
    return sample_data


# ==================================================
# INPUT HELPERS
# ==================================================

def test_get_date_valid(monkeypatch):
    monkeypatch.setattr(
        "builtins.input",
        lambda _: "2026-01-15",
    )

    assert actions.get_date() == "2026-01-15"


def test_get_date_retries_invalid_input(monkeypatch, capsys):
    values = iter(["invalid", "2026-01-15"])

    monkeypatch.setattr(
        "builtins.input",
        lambda _: next(values),
    )

    assert actions.get_date() == "2026-01-15"
    assert "Invalid date" in capsys.readouterr().out


def test_get_date_rejects_past_date(monkeypatch, capsys):
    values = iter(["2020-01-01", "2026-01-15"])

    monkeypatch.setattr(
        "builtins.input",
        lambda _: next(values),
    )

    monkeypatch.setattr(
        actions,
        "today",
        lambda: date(2026, 1, 10),
    )

    assert actions.get_date(check_future=True) == "2026-01-15"
    assert "Date cannot be in the past." in capsys.readouterr().out


def test_get_date_accepts_today(monkeypatch):
    monkeypatch.setattr(
        actions,
        "today",
        lambda: date(2026, 1, 10),
    )

    monkeypatch.setattr(
        "builtins.input",
        lambda _: "2026-01-10",
    )

    assert actions.get_date(check_future=True) == "2026-01-10"


def test_get_stars_valid(monkeypatch):
    monkeypatch.setattr(
        "builtins.input",
        lambda _: "500",
    )

    assert actions.get_stars() == 500


def test_get_stars_retries_invalid(monkeypatch, capsys):
    values = iter(["abc", "0", "500"])

    monkeypatch.setattr(
        "builtins.input",
        lambda _: next(values),
    )

    assert actions.get_stars() == 500
    assert "Enter a valid positive whole number." in capsys.readouterr().out


def test_get_rate_default(monkeypatch):
    monkeypatch.setattr(
        "builtins.input",
        lambda _: "",
    )

    assert actions.get_rate() == Decimal("104")


def test_get_rate_custom_default(monkeypatch):
    monkeypatch.setattr(
        "builtins.input",
        lambda _: "",
    )

    assert actions.get_rate(Decimal("105")) == Decimal("105")


def test_get_rate_custom_value(monkeypatch):
    monkeypatch.setattr(
        "builtins.input",
        lambda _: "110.50",
    )

    assert actions.get_rate() == Decimal("110.50")


def test_get_rate_retries_invalid(monkeypatch, capsys):
    values = iter(["abc", "-10", "105"])

    monkeypatch.setattr(
        "builtins.input",
        lambda _: next(values),
    )

    assert actions.get_rate() == Decimal("105")
    assert "Enter a valid positive exchange rate." in capsys.readouterr().out


# ==================================================
# EDITING LOCK
# ==================================================

def test_check_editing_unlocked(sample_data):
    assert actions.check_editing(sample_data) is True


def test_check_editing_locked(locked_data, capsys):
    assert actions.check_editing(locked_data) is False
    assert "Editing is locked." in capsys.readouterr().out


# ==================================================
# WITHDRAWAL SELECTION
# ==================================================

def test_pick_withdrawal_empty(sample_data, capsys):
    assert actions.pick_withdrawal(sample_data) is None
    assert "No withdrawals found." in capsys.readouterr().out


def test_pick_withdrawal_cancel(sample_data, monkeypatch):
    sample_data["withdrawals"] = [
        {
            "date": "2026-01-01",
            "stars": 500,
            "rate": Decimal("104"),
        }
    ]

    monkeypatch.setattr(
        "builtins.input",
        lambda _: "0",
    )

    assert actions.pick_withdrawal(sample_data) is None


def test_pick_withdrawal_valid_selection(sample_data, monkeypatch):
    withdrawal = {
        "date": "2026-01-01",
        "stars": 500,
        "rate": Decimal("104"),
    }

    sample_data["withdrawals"] = [withdrawal]

    monkeypatch.setattr(
        "builtins.input",
        lambda _: "1",
    )

    assert actions.pick_withdrawal(sample_data) == withdrawal


def test_pick_withdrawal_retries_invalid_selection(sample_data, monkeypatch, capsys):
    withdrawal = {
        "date": "2026-01-01",
        "stars": 500,
        "rate": Decimal("104"),
    }

    sample_data["withdrawals"] = [withdrawal]

    values = iter(["abc", "5", "1"])

    monkeypatch.setattr(
        "builtins.input",
        lambda _: next(values),
    )

    assert actions.pick_withdrawal(sample_data) == withdrawal
    assert "Invalid selection." in capsys.readouterr().out


# ==================================================
# EARNINGS
# ==================================================

def test_add_entry_success(sample_data, monkeypatch):
    values = iter(["2026-01-20", "700"])

    monkeypatch.setattr(
        "builtins.input",
        lambda _: next(values),
    )

    monkeypatch.setattr(actions, "save_data", lambda data: None)

    actions.add_entry(sample_data)

    assert sample_data["earnings"]["2026-01-20"] == 700


def test_add_entry_locked(locked_data, monkeypatch):
    monkeypatch.setattr(
        "builtins.input",
        lambda _: pytest.fail("Input should not be requested"),
    )

    actions.add_entry(locked_data)

    assert locked_data["earnings"] == {
        "2026-01-01": 1000,
        "2026-01-10": 500,
    }


def test_add_entry_duplicate_date(sample_data, monkeypatch, capsys):
    values = iter(["2026-01-01", "700"])

    monkeypatch.setattr(
        "builtins.input",
        lambda _: next(values),
    )

    actions.add_entry(sample_data)

    output = capsys.readouterr().out

    assert "An entry already exists for this date." in output
    assert "Use Update Earning" in output

    assert sample_data["earnings"]["2026-01-01"] == 1000


def test_update_entry_success(sample_data, monkeypatch):
    values = iter(["2026-01-01", "900"])

    monkeypatch.setattr(
        "builtins.input",
        lambda _: next(values),
    )

    monkeypatch.setattr(actions, "save_data", lambda data: None)

    actions.update_entry(sample_data)

    assert sample_data["earnings"]["2026-01-01"] == 900


def test_update_entry_not_found(sample_data, monkeypatch, capsys):
    monkeypatch.setattr(
        "builtins.input",
        lambda _: "2026-01-20",
    )

    actions.update_entry(sample_data)

    assert "Entry not found." in capsys.readouterr().out


def test_delete_entry_confirmed(sample_data, monkeypatch):
    values = iter(["2026-01-01", "y"])

    monkeypatch.setattr(
        "builtins.input",
        lambda _: next(values),
    )

    monkeypatch.setattr(actions, "save_data", lambda data: None)

    actions.delete_entry(sample_data)

    assert "2026-01-01" not in sample_data["earnings"]


def test_delete_entry_cancelled(sample_data, monkeypatch):
    values = iter(["2026-01-01", "n"])

    monkeypatch.setattr(
        "builtins.input",
        lambda _: next(values),
    )

    monkeypatch.setattr(
        actions,
        "save_data",
        lambda data: pytest.fail("Should not save"),
    )

    actions.delete_entry(sample_data)

    assert "2026-01-01" in sample_data["earnings"]


def test_view_data_empty(sample_data, capsys):
    sample_data["earnings"] = {}

    actions.view_data(sample_data)

    assert "No earnings recorded." in capsys.readouterr().out


def test_view_data_displays_entries(sample_data, capsys):
    actions.view_data(sample_data)

    output = capsys.readouterr().out

    assert "2026-01-01" in output
    assert "1,000 Stars" in output
    assert "Buyer:" in output
    assert "Payout:" in output


# ==================================================
# WITHDRAWALS
# ==================================================

def test_add_withdrawal_success(sample_data, monkeypatch):
    monkeypatch.setattr(
        actions,
        "today",
        lambda: date(2026, 1, 15),
    )

    values = iter(["2026-01-15", "500", ""])

    monkeypatch.setattr(
        "builtins.input",
        lambda _: next(values),
    )

    monkeypatch.setattr(actions, "save_data", lambda data: None)

    actions.add_withdrawal(sample_data)

    assert len(sample_data["withdrawals"]) == 1
    assert sample_data["withdrawals"][0]["stars"] == 500
    assert sample_data["withdrawals"][0]["rate"] == Decimal("104")


def test_add_withdrawal_insufficient_balance(sample_data, monkeypatch, capsys):
    monkeypatch.setattr(
        actions,
        "today",
        lambda: date(2026, 1, 15),
    )

    values = iter(["2026-01-15", "999999"])

    monkeypatch.setattr(
        "builtins.input",
        lambda _: next(values),
    )

    monkeypatch.setattr(
        actions,
        "save_data",
        lambda data: pytest.fail("Should not save"),
    )

    actions.add_withdrawal(sample_data)

    assert sample_data["withdrawals"] == []
    assert "Not enough available Stars." in capsys.readouterr().out


def test_add_withdrawal_locked(locked_data, monkeypatch):
    monkeypatch.setattr(
        "builtins.input",
        lambda _: pytest.fail("Input should not be requested"),
    )

    actions.add_withdrawal(locked_data)


def test_edit_withdrawal_success(sample_data, monkeypatch):
    sample_data["withdrawals"] = [
        {
            "date": "2026-01-01",
            "stars": 500,
            "rate": Decimal("104"),
            "fee": Decimal("0"),
        }
    ]

    values = iter([
        "1",             # Select withdrawal
        "2026-01-02",    # New date
        "600",           # New Stars
        "110",           # New rate
        "1.25",          # New fee
    ])

    monkeypatch.setattr(
        "builtins.input",
        lambda _: next(values),
    )

    monkeypatch.setattr(
        actions,
        "save_data",
        lambda data: None,
    )

    actions.edit_withdrawal(sample_data)

    assert sample_data["withdrawals"][0] == {
        "date": "2026-01-02",
        "stars": 600,
        "rate": Decimal("110"),
        "fee": Decimal("1.25"),
    }


def test_edit_withdrawal_cancel(sample_data, monkeypatch):
    sample_data["withdrawals"] = [
        {
            "date": "2026-01-01",
            "stars": 500,
            "rate": Decimal("104"),
            "fee": Decimal("0"),
        }
    ]

    monkeypatch.setattr(
        "builtins.input",
        lambda _: "0",
    )

    monkeypatch.setattr(
        actions,
        "save_data",
        lambda data: pytest.fail("Should not save"),
    )

    actions.edit_withdrawal(sample_data)


def test_delete_withdrawal_confirmed(sample_data, monkeypatch):
    withdrawal = {
        "date": "2026-01-01",
        "stars": 500,
        "rate": Decimal("104"),
    }

    sample_data["withdrawals"] = [withdrawal]

    values = iter(["1", "y"])

    monkeypatch.setattr(
        "builtins.input",
        lambda _: next(values),
    )

    monkeypatch.setattr(actions, "save_data", lambda data: None)

    actions.delete_withdrawal(sample_data)

    assert sample_data["withdrawals"] == []


def test_delete_withdrawal_cancelled(sample_data, monkeypatch):
    withdrawal = {
        "date": "2026-01-01",
        "stars": 500,
        "rate": Decimal("104"),
    }

    sample_data["withdrawals"] = [withdrawal]

    values = iter(["1", "n"])

    monkeypatch.setattr(
        "builtins.input",
        lambda _: next(values),
    )

    monkeypatch.setattr(
        actions,
        "save_data",
        lambda data: pytest.fail("Should not save"),
    )

    actions.delete_withdrawal(sample_data)

    assert sample_data["withdrawals"] == [withdrawal]


def test_view_withdrawals_empty(sample_data, capsys):
    actions.view_withdrawals(sample_data)

    assert "No withdrawals recorded." in capsys.readouterr().out


def test_view_withdrawals_displays_records(sample_data, capsys):
    sample_data["withdrawals"] = [
        {
            "date": "2026-01-01",
            "stars": 500,
            "rate": Decimal("104"),
        }
    ]

    actions.view_withdrawals(sample_data)

    output = capsys.readouterr().out

    assert "2026-01-01" in output
    assert "500 Stars" in output
    assert "Done" in output


# ==================================================
# REPORTS AND SETTINGS
# ==================================================

def test_view_monthly(sample_data, monkeypatch, capsys):
    monkeypatch.setattr(
        actions,
        "build_report",
        lambda data: "MONTHLY REPORT",
    )

    actions.view_monthly(sample_data)

    assert "MONTHLY REPORT" in capsys.readouterr().out


def test_change_rate_success(sample_data, monkeypatch):
    monkeypatch.setattr(
        "builtins.input",
        lambda _: "110",
    )

    monkeypatch.setattr(actions, "save_data", lambda data: None)

    actions.change_rate(sample_data)

    assert sample_data["rate"] == Decimal("110")


def test_change_rate_locked(locked_data, monkeypatch):
    monkeypatch.setattr(
        "builtins.input",
        lambda _: pytest.fail("Input should not be requested"),
    )

    actions.change_rate(locked_data)


def test_show_report(sample_data, monkeypatch, capsys):
    monkeypatch.setattr(
        actions,
        "build_report",
        lambda data: "FULL REPORT",
    )

    actions.show_report(sample_data)

    assert "FULL REPORT" in capsys.readouterr().out


# ==================================================
# FILE OPERATIONS
# ==================================================

def test_reload_data_confirmed(monkeypatch):
    monkeypatch.setattr(
        "builtins.input",
        lambda _: "y",
    )

    expected = {"rate": Decimal("104")}

    monkeypatch.setattr(
        actions,
        "load_data",
        lambda: expected,
    )

    assert actions.reload_data() == expected


def test_reload_data_cancelled(monkeypatch):
    monkeypatch.setattr(
        "builtins.input",
        lambda _: "n",
    )

    monkeypatch.setattr(
        actions,
        "load_data",
        lambda: pytest.fail("Should not load"),
    )

    assert actions.reload_data() is None


def test_unlock_editing_already_unlocked(sample_data, capsys):
    actions.unlock_editing(sample_data)

    assert "already unlocked" in capsys.readouterr().out


def test_unlock_editing_confirmed(locked_data, monkeypatch, capsys):
    monkeypatch.setattr(
        "builtins.input",
        lambda _: "y",
    )

    locked_data["issues"] = ["Invalid record"]

    actions.unlock_editing(locked_data)

    assert locked_data["locked"] is False
    assert locked_data["issues"] == []
    assert "Editing unlocked." in capsys.readouterr().out


def test_unlock_editing_cancelled(locked_data, monkeypatch):
    monkeypatch.setattr(
        "builtins.input",
        lambda _: "n",
    )

    locked_data["issues"] = ["Invalid record"]

    actions.unlock_editing(locked_data)

    assert locked_data["locked"] is True
    assert locked_data["issues"] == ["Invalid record"]
