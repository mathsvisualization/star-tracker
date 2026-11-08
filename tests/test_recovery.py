import pytest

import storage.recovery as recovery


def write_valid_file(path):
    """Create a syntactically and accountingly valid report."""

    path.write_text(
        "RATE|104\n"
        "ENTRY|2026-01-01|500\n"
        "\n",
        encoding="utf-8",
    )


def setup_recovery_files(tmp_path, monkeypatch):
    """Redirect recovery operations to temporary files."""

    main_file = tmp_path / "stars_payment_report.txt"
    backup_file = tmp_path / "stars_payment_report.txt.bak"

    monkeypatch.setattr(
        recovery,
        "FILE_NAME",
        str(main_file),
    )

    monkeypatch.setattr(
        recovery,
        "BACKUP_NAME",
        str(backup_file),
    )

    return main_file, backup_file


# ==================================================
# TEST 1: SUCCESSFUL BACKUP RESTORE
# ==================================================

def test_restore_valid_backup(tmp_path, monkeypatch):

    main_file, backup_file = setup_recovery_files(
        tmp_path,
        monkeypatch,
    )

    main_file.write_text(
        "INVALID DATA\n",
        encoding="utf-8",
    )

    write_valid_file(backup_file)

    result = recovery.restore_backup()

    assert result is True
    assert main_file.exists()

    assert main_file.read_text(
        encoding="utf-8"
    ) == backup_file.read_text(
        encoding="utf-8"
    )

    # Original corrupt file must be preserved.
    corrupt_files = list(
        tmp_path.glob("stars_payment_report.txt.corrupt-*")
    )

    assert len(corrupt_files) == 1

    assert corrupt_files[0].read_text(
        encoding="utf-8"
    ) == "INVALID DATA\n"


# ==================================================
# TEST 2: INVALID BACKUP MUST BE REJECTED
# ==================================================

def test_invalid_backup_is_rejected(tmp_path, monkeypatch):

    main_file, backup_file = setup_recovery_files(
        tmp_path,
        monkeypatch,
    )

    main_file.write_text(
        "ORIGINAL MAIN FILE\n",
        encoding="utf-8",
    )

    backup_file.write_text(
        "INVALID RECORD\n",
        encoding="utf-8",
    )

    result = recovery.restore_backup()

    assert result is False

    # Main file must remain unchanged.
    assert main_file.read_text(
        encoding="utf-8"
    ) == "ORIGINAL MAIN FILE\n"


# ==================================================
# TEST 3: FAILED FINAL VALIDATION MUST ROLL BACK
# ==================================================

def test_failed_restore_rolls_back_main_file(
    tmp_path,
    monkeypatch,
):

    main_file, backup_file = setup_recovery_files(
        tmp_path,
        monkeypatch,
    )

    original_content = "CORRUPTED ORIGINAL FILE\n"

    main_file.write_text(
        original_content,
        encoding="utf-8",
    )

    write_valid_file(backup_file)

    original_inspector = recovery.inspect_recovery_file

    calls = 0

    def fake_inspector(path):

        nonlocal calls
        calls += 1

        # Backup validation and staged validation pass.
        if calls <= 2:
            return original_inspector(path)

        # Final validation fails.
        return None, ["Simulated validation failure."], []

    monkeypatch.setattr(
        recovery,
        "inspect_recovery_file",
        fake_inspector,
    )

    result = recovery.restore_backup()

    assert result is False

    # Original main file must be restored.
    assert main_file.read_text(
        encoding="utf-8"
    ) == original_content


# ==================================================
# TEST 4: LOAD DATA AFTER SUCCESSFUL RECOVERY
# ==================================================

def test_load_data_reloads_restored_backup(
    tmp_path,
    monkeypatch,
):

    main_file, backup_file = setup_recovery_files(
        tmp_path,
        monkeypatch,
    )

    main_file.write_text(
        "INVALID MAIN RECORD\n",
        encoding="utf-8",
    )

    write_valid_file(backup_file)

    monkeypatch.setattr(
        "builtins.input",
        lambda _: "y",
    )

    data = recovery.load_data()

    assert data["locked"] is False
    assert data["issues"] == []

    assert data["rate"] == 104
    assert data["earnings"] == {
        "2026-01-01": 500
    }


# ==================================================
# TEST 5: DECLINED RECOVERY MUST KEEP EDITING LOCKED
# ==================================================

def test_declined_recovery_keeps_data_locked(
    tmp_path,
    monkeypatch,
):

    main_file, backup_file = setup_recovery_files(
        tmp_path,
        monkeypatch,
    )

    main_file.write_text(
        "INVALID MAIN RECORD\n",
        encoding="utf-8",
    )

    write_valid_file(backup_file)

    monkeypatch.setattr(
        "builtins.input",
        lambda _: "n",
    )

    data = recovery.load_data()

    assert data["locked"] is True

    assert data["issues"]

    # Original main file must not be overwritten.
    assert main_file.read_text(
        encoding="utf-8"
    ) == "INVALID MAIN RECORD\n"


# ==================================================
# TEST 6: MISSING MAIN FILE WITH VALID BACKUP
# ==================================================

def test_restore_when_main_file_is_missing(
    tmp_path,
    monkeypatch,
):

    main_file, backup_file = setup_recovery_files(
        tmp_path,
        monkeypatch,
    )

    write_valid_file(backup_file)

    monkeypatch.setattr(
        "builtins.input",
        lambda _: "y",
    )

    data = recovery.load_data()

    assert main_file.exists()

    assert data["locked"] is False
    assert data["issues"] == []

    assert data["earnings"] == {
        "2026-01-01": 500
    }


# ==================================================
# TEST 7: TEMPORARY FILE MUST BE CLEANED UP
# ==================================================

def test_restore_removes_temporary_file(
    tmp_path,
    monkeypatch,
):

    main_file, backup_file = setup_recovery_files(
        tmp_path,
        monkeypatch,
    )

    write_valid_file(backup_file)

    result = recovery.restore_backup()

    temp_file = tmp_path / (
        "stars_payment_report.txt.restore.tmp"
    )

    assert result is True
    assert not temp_file.exists()
