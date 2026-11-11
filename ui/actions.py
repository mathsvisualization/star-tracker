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

from core.validation import (
    parse_stars,
    parse_rate,
    parse_fee,
)
from reports.report_builder import build_report
from storage.file_manager import save_data
from storage.recovery import load_data, restore_backup

class CancelOperation(Exception):
    """Raised when the user cancels the current operation."""
    pass


def get_input(prompt):
    raw = input(prompt).strip()

    if raw.lower() == "cancel":
        raise CancelOperation

    return raw

def get_date(check_future=False):
    while True:
        raw = get_input("Date (YYYY-MM-DD): ")

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
                get_input("Enter Stars: ")
            )
        except (ValueError, InvalidOperation):
            print("Enter a valid positive whole number.")


def get_rate(default=None):
    if default is None:
        default = DEFAULT_USD_TO_INR

    while True:
        raw = get_input(
            f"USD to INR rate [{default}]: "
        )

        if not raw:
            return Decimal(str(default))

        try:
            return parse_rate(raw)
        except (ValueError, InvalidOperation):
            print("Enter a valid positive exchange rate.")


def get_fee(default=Decimal("0")):
    while True:
        raw = get_input(
            f"Withdrawal fee in USD [{default}]: "
        )

        if not raw:
            return Decimal(str(default))

        try:
            return parse_fee(raw)
        except (ValueError, InvalidOperation):
            print("Enter a valid non-negative fee.")


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

    confirm = get_input(
        "Delete this entry? (y/n): "
    ).lower()

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

    date = get_date()
    stars = get_stars()

    if stars > available_stars(data):
        print("\nNot enough available Stars.")
        return

    fee = get_fee()

    data["withdrawals"].append({
        "date": date,
        "stars": stars,
        "rate": data["rate"],
        "fee": fee,
    })

    save_data(data)
    print("\nWithdrawal added.")


def edit_withdrawal(data):
    if not check_editing(data):
        return

    withdrawal = pick_withdrawal(data)

    if withdrawal is None:
        return

    print("\nPress Enter to keep the existing value.")
    print("Type cancel to cancel the operation.")

    try:
        # Collect and validate without mutating
        # the original withdrawal.

        raw_date = get_input(
            f"Date [{withdrawal['date']}]: "
        )

        new_date = raw_date or withdrawal["date"]

        if raw_date:
            datetime.strptime(
                new_date, DATE_INPUT_FMT
            )

        raw_stars = get_input(
            f"Stars [{withdrawal['stars']}]: "
        )

        new_stars = (
            parse_stars(raw_stars)
            if raw_stars
            else withdrawal["stars"]
        )

        new_rate = get_rate(
            withdrawal["rate"]
        )

        new_fee = get_fee(
            withdrawal.get("fee", Decimal("0"))
        )

        # Prepare replacement.
        updated = {
            **withdrawal,
            "date": new_date,
            "stars": new_stars,
            "rate": new_rate,
            "fee": new_fee,
        }

        # Replace only after all inputs are valid.
        index = data["withdrawals"].index(withdrawal)
        data["withdrawals"][index] = updated

        try:
            save_data(data)
        except Exception:
            data["withdrawals"][index] = withdrawal
            raise

        print("\nWithdrawal updated.")

    except CancelOperation:
        print("\nOperation cancelled.")

    except ValueError:
        print("\nInvalid date. Use YYYY-MM-DD.")

    except Exception as err:
        print(f"\nCould not update withdrawal: {err}")


def delete_withdrawal(data):
    if not check_editing(data):
        return

    withdrawal = pick_withdrawal(data)

    if withdrawal is None:
        return

    confirm = get_input(
        "Delete this withdrawal? (y/n): "
    ).lower()

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

