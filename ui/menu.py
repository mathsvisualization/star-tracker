from ui.actions import (
    add_entry,
    update_entry,
    delete_entry,
    view_data,
    add_withdrawal,
    edit_withdrawal,
    delete_withdrawal,
    view_withdrawals,
    view_monthly,
    change_rate,
    show_report,
    reload_data,
    unlock_editing,
)

from storage.recovery import load_data, restore_backup


MENU = """
========== TELEGRAM STARS TRACKER ==========

1.  Add New Earning
2.  Update Earning
3.  Delete Earning
4.  View Earnings

5.  Add Withdrawal
6.  Edit Withdrawal
7.  Delete Withdrawal
8.  View Withdrawals

9.  View Monthly Summary
10. Change USD to INR Rate
11. Generate Full Report

12. Reload File From Disk
13. Restore Backup
14. Unlock Editing

0.  Exit

============================================
"""


def main():
    data = load_data()

    actions = {
        "1": add_entry,
        "2": update_entry,
        "3": delete_entry,
        "4": view_data,
        "5": add_withdrawal,
        "6": edit_withdrawal,
        "7": delete_withdrawal,
        "8": view_withdrawals,
        "9": view_monthly,
        "10": change_rate,
        "11": show_report,
        "14": unlock_editing,
    }

    while True:
        print(MENU)

        if data.get("locked", False):
            print("STATUS: EDITING LOCKED")
        else:
            print("STATUS: EDITING UNLOCKED")

        choice = input("Select option: ").strip()

        if choice == "0":
            print("\nExiting Stars Tracker.")
            break

        elif choice == "12":
            updated_data = reload_data()

            if updated_data is not None:
                data = updated_data

        elif choice == "13":
            confirm = input(
                "Restore backup? Current main file may be replaced. (y/n): "
            ).strip().lower()

            if confirm == "y" and restore_backup():
                data = load_data()

        elif choice in actions:
            try:
                actions[choice](data)

            except Exception as exc:
                print(f"\nOperation failed: {exc}")

        else:
            print("\nInvalid option. Try again.")


if __name__ == "__main__":
    main()