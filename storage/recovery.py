import os
import shutil
from datetime import datetime

from config import FILE_NAME, BACKUP_NAME
from core.validation import new_data, accounting_problems
from storage.file_manager import read_records


# ==================================================
# RECOVERY FILE INSPECTION
# ==================================================

def inspect_recovery_file(path):
    """
    Read and validate a recovery file.

    Returns:
        (data, syntax_issues, accounting_problems)
    """

    if not os.path.exists(path):
        return None, ["File does not exist."], []

    try:
        data, issues = read_records(path)

    except OSError as exc:
        return None, [f"Could not read file: {exc}"], []

    if data is None:
        return None, issues, []

    accounting = accounting_problems(data)

    return data, issues, accounting


# ==================================================
# PRESERVE CORRUPT MAIN FILE
# ==================================================

def preserve_corrupt_main():
    """
    Preserve the current main file before recovery.
    """

    if not os.path.exists(FILE_NAME):
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    corrupt_name = (
        FILE_NAME + f".corrupt-{timestamp}"
    )

    shutil.copy2(FILE_NAME, corrupt_name)

    return corrupt_name


# ==================================================
# RESTORE BACKUP
# ==================================================

def restore_backup():
    """
    Restore backup through a temporary file.

    The backup is validated before replacing the main file.
    The existing main file is preserved whenever possible.
    """

    if not os.path.exists(BACKUP_NAME):
        print("\nNo backup file found.")
        return False

    data, issues, accounting = inspect_recovery_file(
        BACKUP_NAME
    )

    if issues or accounting:
        print("\nBackup is invalid and cannot be restored.")

        for issue in issues:
            print(" -", issue)

        for problem in accounting:
            print(" -", problem)

        return False

    temp_name = FILE_NAME + ".restore.tmp"

    corrupt_name = None
    main_replaced = False

    try:
        # 1. Stage backup in a temporary file.
        shutil.copy2(BACKUP_NAME, temp_name)

        # 2. Validate staged copy independently.
        staged, staged_issues, staged_accounting = (
            inspect_recovery_file(temp_name)
        )

        if staged_issues or staged_accounting:
            print(
                "\nTemporary recovery file failed validation."
            )
            return False

        # 3. Preserve current main file.
        corrupt_name = preserve_corrupt_main()

        # 4. Replace main file only after validation.
        os.replace(temp_name, FILE_NAME)
        main_replaced = True

        # 5. Final verification.
        restored, final_issues, final_accounting = (
            inspect_recovery_file(FILE_NAME)
        )

        if (
            restored is None
            or final_issues
            or final_accounting
        ):
            raise OSError(
                "Restored file failed final validation."
            )

        print("\nBackup restored successfully!")
        return True

    except Exception as exc:
        print(f"\nRecovery failed: {exc}")

        # Roll back only if the main file was replaced.
        if main_replaced:
            try:
                if (
                    corrupt_name
                    and os.path.exists(corrupt_name)
                ):
                    shutil.copy2(
                        corrupt_name,
                        FILE_NAME,
                    )

                elif os.path.exists(FILE_NAME):
                    os.remove(FILE_NAME)

            except OSError as rollback_error:
                print(
                    "Rollback also failed: "
                    f"{rollback_error}"
                )

        return False

    finally:
        # Remove leftover temporary recovery file.
        try:
            if os.path.exists(temp_name):
                os.remove(temp_name)

        except OSError:
            pass


# ==================================================
# OFFER BACKUP RECOVERY
# ==================================================

def offer_backup_recovery():
    """
    Ask the user whether to restore a valid backup.
    """

    if not os.path.exists(BACKUP_NAME):
        return False

    data, issues, accounting = inspect_recovery_file(
        BACKUP_NAME
    )

    if issues or accounting:
        print("\nBackup exists but is invalid.")
        return False

    choice = input(
        "\nA valid backup was found. Restore it? (y/n): "
    ).strip().lower()

    if choice != "y":
        return False

    return restore_backup()


# ==================================================
# LOAD DATA
# ==================================================

def load_data():
    """
    Load the main report.

    If the main file is missing, attempt backup recovery.

    Never silently create an editable blank report when
    a backup exists but recovery was declined or failed.
    """

    # --------------------------------------------------
    # CASE 1: Main file exists.
    # --------------------------------------------------

    if os.path.exists(FILE_NAME):

        data, issues, accounting = inspect_recovery_file(
            FILE_NAME
        )

        if data is None:
            data = new_data()

        # Main file contains syntax errors.
        if issues:

            data["locked"] = True
            data["issues"] = issues

            print(
                "\nMain file contains invalid records."
            )

            for issue in issues:
                print(" -", issue)

            # Try restoring a valid backup.
            if offer_backup_recovery():

                restored, restored_issues, restored_accounting = (
                    inspect_recovery_file(FILE_NAME)
                )

                if (
                    restored is not None
                    and not restored_issues
                    and not restored_accounting
                ):
                    restored["locked"] = False
                    restored["issues"] = []

                    return restored

            return data

        # Main file is syntactically valid.
        data["locked"] = False
        data["issues"] = []

        if accounting:
            print("\nAccounting warnings:")

            for problem in accounting:
                print(" -", problem)

        return data

    # --------------------------------------------------
    # CASE 2: Main file is missing, backup exists.
    # --------------------------------------------------

    if os.path.exists(BACKUP_NAME):

        print("\nMain report is missing.")

        if offer_backup_recovery():

            data, issues, accounting = (
                inspect_recovery_file(FILE_NAME)
            )

            if (
                data is not None
                and not issues
                and not accounting
            ):
                data["locked"] = False
                data["issues"] = []

                return data

        # Recovery declined or failed.
        data = new_data()

        data["locked"] = True
        data["issues"] = [
            "Main file is missing. "
            "Backup recovery was not completed."
        ]

        return data

    # --------------------------------------------------
    # CASE 3: Neither main file nor backup exists.
    # --------------------------------------------------

    return new_data()
