import os

from config import (
    FILE_NAME,
    BACKUP_NAME,
    SaveError,
)

from core.validation import (
    parse_lines,
    accounting_problems,
    new_shortfall,
)

from core.calculations import sorted_withdrawals

from storage.backup import backup_file
from reports.report_builder import build_report


# ==================================================
# FILE READING
# ==================================================

def read_records(path):
    """Read and parse records from a report file."""

    with open(
        path,
        "r",
        encoding="utf-8",
        errors="replace",
    ) as file:

        return parse_lines(file)


def inspect_disk_file():
    """
    Return None if no main file exists.

    Otherwise return:
        (data, syntax_issues, accounting_problems)
    """

    if not os.path.exists(FILE_NAME):
        return None

    data, issues = read_records(FILE_NAME)

    accounting = (
        []
        if issues
        else accounting_problems(data)
    )

    return data, issues, accounting


# ==================================================
# ATOMIC WRITING
# ==================================================

def write_atomic(path, text):
    """
    Write to a temporary file and atomically
    replace the target file.
    """

    tmp = path + ".tmp"

    try:

        with open(
            tmp,
            "w",
            encoding="utf-8",
        ) as file:

            file.write(text)
            file.flush()
            os.fsync(file.fileno())

        os.replace(tmp, path)

    except OSError:

        try:
            os.remove(tmp)

        except OSError:
            pass

        raise


# ==================================================
# RECORD SERIALIZATION
# ==================================================

def serialize_records(data):
    """Convert in-memory data into file records."""

    records = [
        f"RATE|{data['rate']}"
    ]

    records += [
        f"ENTRY|{date}|{stars}"
        for date, stars in sorted(
            data["earnings"].items()
        )
    ]

    records += [
        (
            f"WITHDRAW|{w['date']}|"
            f"{w['stars']}|{w['rate']}"
        )
        for w in sorted_withdrawals(data)
    ]

    return records


# ==================================================
# ROUND-TRIP VALIDATION
# ==================================================

def validate_serialized_data(data, records):
    """
    Serialize -> Parse -> Compare.

    Ensures saved records can reconstruct
    the same data.
    """

    checked, issues = parse_lines(records)

    if (
        issues
        or checked["rate"] != data["rate"]
        or checked["earnings"] != data["earnings"]
        or checked["withdrawals"] != sorted_withdrawals(data)
    ):

        details = (
            "; ".join(issues[:3])
            or "records do not match"
        )

        raise SaveError(
            f"data failed validation ({details})"
        )


# ==================================================
# SAFE SAVING
# ==================================================

def save_data(data):
    """Validate, backup and safely save the report."""

    if data["locked"]:
        raise SaveError("editing is locked")

    # 1. Convert data into records.
    records = serialize_records(data)

    # 2. Validate serialized records.
    validate_serialized_data(data, records)

    # 3. Inspect existing disk file.
    try:

        disk = inspect_disk_file()

    except OSError as err:

        raise SaveError(
            f"could not read the current file ({err})"
        ) from err

    # 4. Prevent worsening existing accounting problems.
    if disk is not None and not disk[1]:

        old = disk[0]

        problem = new_shortfall(
            old["earnings"],
            old["withdrawals"],
            data["earnings"],
            data["withdrawals"],
        )

        if problem:

            from core.validation import describe_shortfall

            raise SaveError(
                "accounting check failed, "
                + describe_shortfall(*problem)
            )

    # 5. Build report before modifying files.
    text = (
        "\n".join(records)
        + "\n\n"
        + build_report(data)
    )

    # 6. Preserve existing file.
    backup_file(disk)

    # 7. Atomically replace main report.
    try:

        write_atomic(FILE_NAME, text)

    except OSError as err:

        raise SaveError(
            f"could not write the main report ({err})"
        ) from err

    print("\nReport updated successfully!")