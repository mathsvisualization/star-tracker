from datetime import datetime
from decimal import Decimal, InvalidOperation

from config import DATE_INPUT_FMT, DEFAULT_USD_TO_INR

from core.calculations import (
    today,
    parse_date,
    calculate,
    available_stars,
    pending_stars,
    total_earned,
    total_withdrawn,
    scheduled_stars,
    sorted_withdrawals,
    done_withdrawals,
    scheduled_withdrawals,
)

from core.validation import parse_stars, parse_rate
from reports.report_builder import build_report
from storage.file_manager import save_data
from storage.recovery import load_data, restore_backup


def get_date(check_future=False):
    while True:
        raw = input("Date (YYYY-MM-DD): ").strip()

        try:
            date = datetime.strptime(
                raw, DATE_INPUT_FMT
            ).date()

            if check_future and date < today():
                print("Date cannot be in the past.")
                continue

            return raw

        except ValueError:
            print("Invalid date. Use YYYY-MM-DD.")


def get_stars():
    while True:
        try:
            return parse_stars(
                input("Enter Stars: ").strip()
            )
        except (ValueError, InvalidOperation):
            print("Enter a valid positive whole number.")


def get_rate(default=None):
    if default is None:
        default = DEFAULT_USD_TO_INR

    while True:
        raw = input(
            f"USD to INR rate [{default}]: "
        ).strip()

        if not raw:
            return Decimal(str(default))

        try:
            return parse_rate(raw)
        except (ValueError, InvalidOperation):
            print("Enter a valid positive exchange rate.")


def check_editing(data):
    if data.get("locked", False):
        print("\nEditing is locked.")
        print("Fix invalid records or unlock editing first.")
        return False

    return True


def pick_withdrawal(data):
    withdrawals = sorted_withdrawals(data)

    if not withdrawals:
        print("\nNo withdrawals found.")
        return None

    for index, withdrawal in enumerate(withdrawals, 1):
        status = (
            "Done"
            if parse_date(withdrawal["date"]) <= today()
            else "Scheduled"
        )

        print(
            f"{index}. {withdrawal['date']} | "
            f"{withdrawal['stars']:,} Stars | {status}"
        )

    while True:
        choice = input(
            "\nSelect withdrawal number (0 to cancel): "
        ).strip()

        if choice == "0":
            return None

        try:
            index = int(choice)

            if 1 <= index <= len(withdrawals):
                return withdrawals[index - 1]

        except ValueError:
            pass

        print("Invalid selection.")


# ==================================================
# EARNINGS
# ==================================================

def add_entry(data):
    if not check_editing(data):
        return

    date = get_date()
    stars = get_stars()

    if date in data["earnings"]:
        print("\nAn entry already exists for this date.")
        print("Use Update Earning to change it.")
        return

    data["earnings"][date] = stars

    save_data(data)
    print("\nNew earning entry added.")


def update_entry(data):
    if not check_editing(data):
        return

    date = get_date()

    if date not in data["earnings"]:
        print("\nEntry not found.")
        return

    print(f"Current Stars: {data['earnings'][date]:,}")

    data["earnings"][date] = get_stars()

    save_data(data)
    print("\nEntry updated.")


def delete_entry(data):
    if not check_editing(data):
        return

    date = get_date()

    if date not in data["earnings"]:
        print("\nEntry not found.")
        return

    confirm = input(
        "Delete this entry? (y/n): "
    ).strip().lower()

    if confirm == "y":
        del data["earnings"][date]

        save_data(data)
        print("\nEntry deleted.")


def view_data(data):
    print("\n========== EARNINGS ==========")

    if not data["earnings"]:
        print("No earnings recorded.")
        return

    for date, stars in sorted(data["earnings"].items()):
        result = calculate(stars, data["rate"])

        print(
            f"{date} | {stars:,} Stars | "
            f"Buyer: Rs. {result['buyer']:,.2f} | "
            f"Payout: ${result['usd']:,.2f} "
            f"(Rs. {result['inr']:,.2f})"
        )


# ==================================================
# WITHDRAWALS
# ==================================================

def add_withdrawal(data):
    if not check_editing(data):
        return

    date = get_date(check_future=True)
    stars = get_stars()

    if stars > available_stars(data):
        print("\nNot enough available Stars.")
        return

    data["withdrawals"].append({
        "date": date,
        "stars": stars,
        "rate": data["rate"],
    })

    save_data(data)
    print("\nWithdrawal added.")


def edit_withdrawal_rate(data):
    if not check_editing(data):
        return

    withdrawal = pick_withdrawal(data)

    if withdrawal is None:
        return

    withdrawal["rate"] = get_rate(
        withdrawal["rate"]
    )

    save_data(data)
    print("\nWithdrawal rate updated.")


def delete_withdrawal(data):
    if not check_editing(data):
        return

    withdrawal = pick_withdrawal(data)

    if withdrawal is None:
        return

    confirm = input(
        "Delete this withdrawal? (y/n): "
    ).strip().lower()

    if confirm == "y":
        data["withdrawals"].remove(withdrawal)

        save_data(data)
        print("\nWithdrawal deleted.")


def view_withdrawals(data):
    print("\n========== WITHDRAWALS ==========")

    withdrawals = sorted_withdrawals(data)

    if not withdrawals:
        print("No withdrawals recorded.")
        return

    for withdrawal in withdrawals:
        status = (
            "Done"
            if parse_date(withdrawal["date"]) <= today()
            else "Scheduled"
        )

        result = calculate(
            withdrawal["stars"],
            withdrawal["rate"],
        )

        print(
            f"{withdrawal['date']} | "
            f"{withdrawal['stars']:,} Stars | "
            f"{status} | "
            f"${result['usd']:,.2f}"
        )


# ==================================================
# REPORTS AND SETTINGS
# ==================================================

def view_monthly(data):
    print(build_report(data))


def change_rate(data):
    if not check_editing(data):
        return

    data["rate"] = get_rate(data["rate"])

    save_data(data)
    print(f"\nDefault exchange rate changed to {data['rate']}.")


def show_report(data):
    print(build_report(data))


# ==================================================
# FILE OPERATIONS
# ==================================================

def reload_data():
    confirm = input(
        "Reload data from disk? Unsaved changes will be lost. (y/n): "
    ).strip().lower()

    if confirm == "y":
        return load_data()

    return None


def unlock_editing(data):
    if not data.get("locked", False):
        print("\nEditing is already unlocked.")
        return

    print("\nUnlocking means continuing without invalid records.")

    confirm = input(
        "Continue with valid records only? (y/n): "
    ).strip().lower()

    if confirm == "y":
        data["locked"] = False
        data["issues"] = []

        print("\nEditing unlocked.")
        print("Save your data to replace the current report.")
