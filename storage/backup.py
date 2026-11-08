import os
import shutil
from datetime import datetime

from config import FILE_NAME, BACKUP_NAME, SaveError


def backup_file(disk):
    """
    Create or update the backup of the current main file.

    Rules:
    1. If the main file doesn't exist, do nothing.
    2. If the main file contains invalid records or accounting
       problems, preserve it as an unverified copy.
    3. Never replace a known-good backup with invalid data.
    4. Create valid backups atomically.
    """

    if disk is None:
        return

    data, issues, accounting = disk

    # Check whether the current main file is valid.
    if issues or accounting:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        unverified_name = (
            FILE_NAME + f".unverified-{timestamp}"
        )

        try:
            shutil.copy2(FILE_NAME, unverified_name)

        except OSError as exc:
            raise SaveError(
                "Could not preserve the invalid main file "
                f"as an unverified copy: {exc}"
            ) from exc

        # Existing .bak remains untouched.
        return

    temp_name = BACKUP_NAME + ".tmp"

    try:
        # Copy the current main file into a temporary backup.
        with open(FILE_NAME, "rb") as source:
            with open(temp_name, "wb") as destination:
                shutil.copyfileobj(source, destination)

                destination.flush()
                os.fsync(destination.fileno())

        # Atomically replace the previous backup.
        os.replace(temp_name, BACKUP_NAME)

    except OSError as exc:
        # Remove incomplete temporary backup.
        try:
            if os.path.exists(temp_name):
                os.remove(temp_name)
        except OSError:
            pass

        raise SaveError(
            f"Could not create a safe backup: {exc}"
        ) from exc